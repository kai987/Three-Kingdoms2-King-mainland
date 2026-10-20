"""Readable, bounded bank12/13 battle scene controller.

Offline control-flow structuring produced named procedures and phase handlers.
Production reads immutable game data, never opcodes, control IR or PC->operation
tables. Services retain their real caller stack and explicit pending boundary.
CPU-register form is retained where flags/scratch/aliasing are observable.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import ServiceCall, ServiceWait
from .mapped_memory import UnsupportedHardware

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
STATE,PHASE,COMMAND,SIDE,AP=0x500,0x501,0x502,0x504,0x505
ROUND,RULERS,SELECTED_SLOT,ACTOR_SLOT,CITY,CONTROLLER=0x506,0x507,0x509,0x50A,0x50E,0x50F
TACTIC,TACTIC_FAILED,ANIMATION=0x543,0x544,0x4C8
NEW_BUTTONS,REPEAT_BUTTONS,GLOBAL,NMI_SCENE,PPU_JOBS=0x81,0x87,0x7A,0x78,0x7E

@dataclass
class BattleRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA028

class BattleSceneController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned battle ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=BattleRegisters();self.events=[];self.pending=None;self._program=None
        self._blocks=0;self._limit=200000
    def _nz(self,value):
        value&=255;self.registers.p=(self.registers.p&~(N|Z))|(N if value&128 else 0)|(Z if value==0 else 0)
        return value
    def _a(self,value):self.registers.a=self._nz(value)
    def _x(self,value):self.registers.x=self._nz(value)
    def _y(self,value):self.registers.y=self._nz(value)
    def _flag(self,bit,value):self.registers.p=(self.registers.p&~bit)|(bit if value else 0)
    def _compare(self,left,right):self._flag(C,left>=right);self._nz(left-right)
    def _add(self,value,subtract=False):
        r=self.registers;old=r.a;carry=bool(r.p&C)
        total=old-value-(1-carry)if subtract else old+value+carry
        self._flag(C,total>=0 if subtract else total>255)
        self._flag(V, bool(((old^value)&(old^total)&128)if subtract else (~(old^value)&(old^total)&128)))
        self._a(total)
    def _shift(self,value,left,rotate=False):
        carry=bool(self.registers.p&C);self._flag(C,value&128 if left else value&1)
        return self._nz(((value<<1)|(carry if rotate else 0))if left else ((value>>1)|(128 if rotate and carry else 0)))
    def _push(self,value):
        r=self.registers;self.memory[0x100+r.sp]=value&255;r.sp=(r.sp-1)&255
    def _pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]
    def _rts(self):self.registers.pc=((self._pop()|self._pop()<<8)+1)&65535
    def _local_call(self,method,pc,return_pc):
        self._push((pc+2)>>8);self._push(pc+2)
        yield from method()
        return self.registers.pc==return_pc
    def _mark(self,pc):
        self.registers.pc=pc;self._blocks+=1
        if self._blocks>self._limit:raise RuntimeError('Source control-block budget reached')
    def _dispatch(self,pc,targets):
        r=self.registers;m=self.memory;index=r.a
        if index>=len(targets):raise ValueError(f'Original bounded dispatch index {index} at ${pc:04X}')
        self._push((pc+2)>>8);self._push(pc+2)
        original_y=r.y;m[0]=original_y;base=self._pop()|self._pop()<<8
        m[1],m[2]=base&255,base>>8;target=targets[index];m[3],m[4]=target&255,target>>8
        r.a=target>>8;r.y=original_y;r.pc=target
        r.p=(r.p&~(C|N|Z))|(C if index&128 else 0)|(N if original_y&128 else 0)|(Z if original_y==0 else 0)
        return index
    def _external(self,pc,target,return_pc,kind,inline_target=None):
        r=self.registers;caller_sp=r.sp
        if kind!='tail':self._push((pc+2)>>8);self._push(pc+2)
        else:caller_sp=(r.sp+2)&255
        r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        event=dict(call_pc=pc,target=target,return_pc=return_pc,kind=kind,inline_target=inline_target)
        self.events.append(event)
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),caller_sp)
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
                if self.registers.pc!=self._return_pc:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA028,*,registers=None,seed_return=False,return_pc=0x0200,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        self.registers=registers or BattleRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc!=0x0200:raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=return_pc;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def _entry(self,entry):
        if entry==0xA000:return self.scene_entry()
        elif entry==0xA003:return self.battle_initialize_entry()
        elif entry==0xA006:return self.duel_outcome_entry()
        elif entry==0xA009:return self.scene_tick()
        elif entry==0xA028:return self.battle_tick()
        elif entry==0xA04E:return self.unit_selection()
        elif entry==0xA05E:return self.choose_actor_control()
        elif entry==0xA08D:return self.await_cursor_refresh()
        elif entry==0xA0BB:return self.select_unit()
        elif entry==0xA118:return self.action_menu()
        elif entry==0xA1B8:return self.confirm_action_menu()
        elif entry==0xA1DE:return self.blink_command_cursor()
        elif entry==0xA1F7:return self.return_command_cursor()
        elif entry==0xA21B:return self.unit_information()
        elif entry==0xA227:return self.open_unit_information()
        elif entry==0xA244:return self.navigate_unit_information()
        elif entry==0xA27B:return self.close_unit_information()
        elif entry==0xA293:return self.attack_confirmation()
        elif entry==0xA2A7:return self.request_attack_target()
        elif entry==0xA2BB:return self.choose_adjacent_target()
        elif entry==0xA30C:return self.acknowledge_attack_target()
        elif entry==0xA325:return self.launch_attack_scene()
        elif entry==0xA368:return self.orthogonal_attack_target()
        elif entry==0xA3D2:return self.prepare_attack_parameters()
        elif entry==0xA433:return self.save_attack_attributes()
        elif entry==0xA44D:return self.movement()
        elif entry==0xA470:return self.request_move_target()
        elif entry==0xA47E:return self.advance_move_cursor()
        elif entry==0xA4B5:return self.check_destination_event()
        elif entry==0xA51F:return self.request_ambush_scan()
        elif entry==0xA535:return self.consume_ambush_result()
        elif entry==0xA5CE:return self.acknowledge_ambush_damage()
        elif entry==0xA617:return self.acknowledge_move_result()
        elif entry==0xA64A:return self.local_a64a()
        elif entry==0xA7E7:return self.local_a7e7()
        elif entry==0xA85B:return self.local_a85b()
        elif entry==0xA87C:return self.tactics()
        elif entry==0xA89E:return self.initialize_tactic_list()
        elif entry==0xA8C1:return self.build_tactic_list()
        elif entry==0xA8D8:return self.request_tactic_menu()
        elif entry==0xA917:return self.select_tactic()
        elif entry==0xA9DD:return self.choose_tactic_target()
        elif entry==0xAA2E:return self.confirm_tactic()
        elif entry==0xAA6C:return self.wait_animation_apply_tactic()
        elif entry==0xAAA7:return self.scan_tactic_result()
        elif entry==0xAB2A:return self.acknowledge_tactic_result()
        elif entry==0xAB52:return self.acknowledge_upgrade_notice()
        elif entry==0xAB90:return self.acknowledge_invalid_target()
        elif entry==0xABD9:return self.local_abd9()
        elif entry==0xAD80:return self.local_ad80()
        elif entry==0xADCC:return self.local_adcc()
        elif entry==0xADD8:return self.local_add8()
        elif entry==0xADE4:return self.local_ade4()
        elif entry==0xADEE:return self.local_adee()
        elif entry==0xADFB:return self.local_adfb()
        elif entry==0xAE2D:return self.local_ae2d()
        elif entry==0xAE42:return self.local_ae42()
        elif entry==0xAE68:return self.local_ae68()
        elif entry==0xAEA4:return self.local_aea4()
        elif entry==0xAEC4:return self.local_aec4()
        elif entry==0xAECE:return self.local_aece()
        elif entry==0xAF0A:return self.local_af0a()
        elif entry==0xAF44:return self.local_af44()
        elif entry==0xAF73:return self.local_af73()
        elif entry==0xAFA1:return self.local_afa1()
        elif entry==0xAFD3:return self.local_afd3()
        elif entry==0xB01D:return self.local_b01d()
        elif entry==0xB02B:return self.apply_tactic()
        elif entry==0xB062:return self.local_b062()
        elif entry==0xB070:return self.local_b070()
        elif entry==0xB0DD:return self.local_b0dd()
        elif entry==0xB0EB:return self.local_b0eb()
        elif entry==0xB155:return self.local_b155()
        elif entry==0xB17A:return self.local_b17a()
        elif entry==0xB188:return self.local_b188()
        elif entry==0xB1D5:return self.local_b1d5()
        elif entry==0xB1E3:return self.local_b1e3()
        elif entry==0xB243:return self.local_b243()
        elif entry==0xB2CD:return self.local_b2cd()
        elif entry==0xB304:return self.local_b304()
        elif entry==0xB31C:return self.local_b31c()
        elif entry==0xB3B6:return self.local_b3b6()
        elif entry==0xB3D0:return self.local_b3d0()
        elif entry==0xB3FE:return self.local_b3fe()
        elif entry==0xB42A:return self.local_b42a()
        elif entry==0xB466:return self.local_b466()
        elif entry==0xB494:return self.local_b494()
        elif entry==0xB4B8:return self.local_b4b8()
        elif entry==0xB50C:return self.local_b50c()
        elif entry==0xB538:return self.local_b538()
        elif entry==0xB55C:return self.local_b55c()
        elif entry==0xB5A6:return self.local_b5a6()
        elif entry==0xB5D8:return self.health_loss()
        elif entry==0xB643:return self.local_b643()
        elif entry==0xB67B:return self.local_b67b()
        elif entry==0xB68B:return self.troop_loss()
        elif entry==0xB6F0:return self.local_b6f0()
        elif entry==0xB72B:return self.local_b72b()
        elif entry==0xB7BE:return self.local_b7be()
        elif entry==0xB860:return self.local_b860()
        elif entry==0xB8A1:return self.local_b8a1()
        elif entry==0xB8CE:return self.local_b8ce()
        elif entry==0xB8FA:return self.local_b8fa()
        elif entry==0xB94A:return self.withdrawal()
        elif entry==0xB964:return self.request_retreat()
        elif entry==0xB96D:return self.select_retreat_answer()
        elif entry==0xB9B6:return self.open_retreat_destination()
        elif entry==0xBA30:return self.select_retreat_destination()
        elif entry==0xBA64:return self.commit_retreat()
        elif entry==0xBA83:return self.acknowledge_retreat()
        elif entry==0xBB84:return self.local_bb84()
        elif entry==0xBC11:return self.local_bc11()
        elif entry==0xBC14:return self.local_bc14()
        elif entry==0xBC2A:return self.local_bc2a()
        elif entry==0xBC93:return self.wait_action()
        elif entry==0xBCB3:return self.request_wait_action()
        elif entry==0xBCC1:return self.confirm_wait_action()
        elif entry==0xBCED:return self.wait_text_then_change_side()
        elif entry==0xBCF6:return self.prepare_side_notice()
        elif entry==0xBD13:return self.acknowledge_side_notice()
        elif entry==0xBD2C:return self.refresh_units_for_side()
        elif entry==0xBD41:return self.inspect_strategy_notice()
        elif entry==0xBD6F:return self.acknowledge_strategy_notice()
        elif entry==0xBDC0:return self.finish_side_turn()
        elif entry==0xBE7E:return self.computer_action()
        elif entry==0xBEA6:return self.request_AI_scan()
        elif entry==0xBEBA:return self.await_AI_proposal()
        elif entry==0xBF01:return self.route_AI_proposal()
        elif entry==0xBF19:return self.prepare_AI_movement()
        elif entry==0xBF7C:return self.commit_AI_movement()
        elif entry==0xBF98:return self.prepare_AI_attack()
        elif entry==0xBFB8:return self.show_AI_attack_target()
        elif entry==0xBFDC:return self.launch_AI_attack()
        elif entry==0xC004:return self.prepare_AI_tactic()
        elif entry==0xC054:return self.show_AI_tactic_notice()
        elif entry==0xC07D:return self.apply_AI_tactic()
        elif entry==0xC110:return self.show_AI_tactic_actor()
        elif entry==0xC13B:return self.finish_AI_side()
        elif entry==0xC149:return self.prepare_AI_withdrawal()
        elif entry==0xC178:return self.show_AI_withdrawal()
        elif entry==0xC1D1:return self.confirm_AI_withdrawal()
        elif entry==0xC1EB:return self.return_from_AI()
        elif entry==0xC1FC:return self.village_service()
        elif entry==0xC204:return self.next_side()
        elif entry==0xC218:return self.prepare_next_side()
        elif entry==0xC24F:return self.prepare_first_side_control()
        elif entry==0xC28A:return self.prepare_second_side_control()
        elif entry==0xC2CD:return self.enter_unit_selection()
        elif entry==0xC2F7:return self.acknowledge_next_side_notice()
        elif entry==0xC30E:return self.scan_next_officer()
        elif entry==0xC350:return self.draw_next_officer_notice()
        elif entry==0xC3CB:return self.local_c3cb()
        elif entry==0xC447:return self.local_c447()
        elif entry==0xC4B1:return self.local_c4b1()
        elif entry==0xC5A0:return self.local_c5a0()
        elif entry==0xC620:return self.round_resource_update()
        elif entry==0xC691:return self.duel_result()
        elif entry==0xC69F:return self.prepare_first_duel_result()
        elif entry==0xC6AC:return self.prepare_second_duel_result()
        elif entry==0xC6B9:return self.finish_duel_result()
        elif entry==0xC6BC:return self.acknowledge_duel_upgrade()
        elif entry==0xC75B:return self.find_duel_officer_slot()
        elif entry==0xC766:return self.apply_duel_outcomes()
        elif entry==0xC782:return self.dispatch_duel_outcome()
        elif entry==0xC797:return self.local_c797()
        elif entry==0xC798:return self.local_c798()
        elif entry==0xC799:return self.remove_duel_defeated_unit()
        elif entry==0xC7DB:return self.collect_duel_captive()
        elif entry==0xC81F:return self.local_c81f()
        elif entry==0xC886:return self.local_c886()
        elif entry==0xC91E:return self.local_c91e()
        elif entry==0xC98C:return self.battle_result()
        elif entry==0xC99E:return self.prepare_result_summary()
        elif entry==0xC9AD:return self.await_result_text()
        elif entry==0xC9C3:return self.prepare_result_panel()
        elif entry==0xC9FE:return self.confirm_result_panel()
        elif entry==0xCA13:return self.select_result_resolution()
        elif entry==0xCA2F:return self.acknowledge_result_exit()
        elif entry==0xCA41:return self.local_ca41()
        elif entry==0xCA51:return self.result_yes_flag()
        elif entry==0xCA53:return self.local_ca53()
        elif entry==0xCAF8:return self.prepare_postbattle_summary()
        elif entry==0xCB6E:return self.local_cb6e()
        elif entry==0xCC29:return self.draw_postbattle_units()
        elif entry==0xCC45:return self.local_cc45()
        elif entry==0xCC5A:return self.local_cc5a()
        elif entry==0xCC6D:return self.local_cc6d()
        elif entry==0xCCAA:return self.local_ccaa()
        elif entry==0xCCDF:return self.local_ccdf()
        elif entry==0xCD16:return self.defeated_roster()
        elif entry==0xCD2A:return self.prepare_defeated_roster()
        elif entry==0xCD52:return self.select_defeated_roster_destination()
        elif entry==0xCDF2:return self.open_defeated_roster_selection()
        elif entry==0xCE56:return self.choose_defeated_roster_officer()
        elif entry==0xCE76:return self.exclude_defeated_roster_officer()
        elif entry==0xCE9E:return self.prepare_defeated_roster_confirmation()
        elif entry==0xCF09:return self.confirm_defeated_roster_transfer()
        elif entry==0xD0C3:return self.local_d0c3()
        elif entry==0xD0E1:return self.postbattle_roster()
        elif entry==0xD167:return self.local_d167()
        elif entry==0xD1BC:return self.local_d1bc()
        elif entry==0xD1DF:return self.local_d1df()
        elif entry==0xD1F9:return self.local_d1f9()
        elif entry==0xD20D:return self.local_d20d()
        elif entry==0xD2CD:return self.victor_roster()
        elif entry==0xD2E1:return self.prepare_victor_roster()
        elif entry==0xD310:return self.select_victor_roster_destination()
        elif entry==0xD34B:return self.open_victor_roster_selection()
        elif entry==0xD3AF:return self.choose_victor_roster_officer()
        elif entry==0xD3D7:return self.exclude_victor_roster_officer()
        elif entry==0xD3F7:return self.prepare_victor_roster_confirmation()
        elif entry==0xD462:return self.confirm_victor_roster_transfer()
        elif entry==0xD48D:return self.remove_postbattle_officer()
        elif entry==0xD4A3:return self.local_d4a3()
        elif entry==0xD4F0:return self.return_to_city()
        elif entry==0xD4FB:return self.direction_repeat()
        elif entry==0xD5EE:return self.cursor_input()
        elif entry==0xD657:return self.battle_cursor()
        elif entry==0xD68A:return self.unit_at_cursor()
        elif entry==0xD6B6:return self.local_d6b6()
        elif entry==0xD6CC:return self.map_refresh()
        elif entry==0xD88E:return self.local_d88e()
        elif entry==0xD8AC:return self.local_d8ac()
        elif entry==0xDA17:return self.local_da17()
        elif entry==0xDA5A:return self.local_da5a()
        elif entry==0xDA83:return self.local_da83()
        elif entry==0xDAC3:return self.local_dac3()
        elif entry==0xDB03:return self.refresh_hundred_troops()
        elif entry==0xDB46:return self.terrain_at_position()
        elif entry==0xDB50:return self.raw_terrain_at_position()
        elif entry==0xDC1E:return self.local_dc1e()
        elif entry==0xDC33:return self.local_dc33()
        elif entry==0xDC36:return self.local_dc36()
        elif entry==0xDC4B:return self.target_side_filter()
        elif entry==0xDC63:return self.dialog_highlight()
        elif entry==0xDC70:return self.alternate_highlight()
        elif entry==0xDC99:return self.initialize_battle_arrays()
        elif entry==0xDD72:return self.commander_outcome()
        elif entry==0xDE82:return self.local_de82()
        elif entry==0xDE9E:return self.local_de9e()
        elif entry==0xDEBF:return self.local_debf()
        elif entry==0xDEE9:return self.local_dee9()
        elif entry==0xDF27:return self.text_readiness()
        elif entry==0xDF39:return self.select_battle_IRQ_layout()
        elif entry==0xDF88:return self.adjust_battle_IRQ_delay()
        elif entry==0xE850:return self.random_four()
        elif entry==0xE856:return self.random_eight()
        elif entry==0xE862:return self.random_bounded()
        elif entry==0xEA7C:return self.divide_word()
        elif entry==0xEAA5:return self.divide_24bit()
        elif entry==0xEBE9:return self.multiply_24bit()
        elif entry==0xF2AF:return self.city_pointer()
        elif entry==0xF368:return self.ruler_pointer()
        raise ValueError("Entry is outside the proven battle procedure catalog")

    def scene_entry(self):
        """$A000: scene entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA000)
        return (yield from self.scene_tick())

    def battle_initialize_entry(self):
        """$A003: battle initialize entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.initialize_battle_arrays())

    def duel_outcome_entry(self):
        """$A006: duel outcome entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA006)
        return (yield from self.apply_duel_outcomes())

    def scene_tick(self):
        """$A009: scene tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA009)
        if not (yield from self._local_call(self.adjust_battle_IRQ_delay,0xA009,0xA00C)):return
        self._y(0x28)
        yield from self._external(0xA00E,0xEE07,0xA013,"far_call",40978)
        if r.pc!=0xA013:return  # preserve nonlocal stack return
        self._y(0x28)
        yield from self._external(0xA015,0xEE07,0xA01A,"far_call",40993)
        if r.pc!=0xA01A:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.battle_tick,0xA01A,0xA01D)):return
        if not (yield from self._local_call(self.select_battle_IRQ_layout,0xA01D,0xA020)):return
        self._y(0x28)
        yield from self._external(0xA022,0xEE07,0xA027,"far_call",40981)
        if r.pc!=0xA027:return  # preserve nonlocal stack return
        self._mark(0xA027)
        self._rts();return

    def battle_tick(self):
        """$A028: battle tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA028)
        self._a(m[STATE])
        self._mark(0xA02B)
        index=self._dispatch(0xA02B,(41038, 41499, 41619, 41619, 42061, 43132, 47434, 48275, 48766, 49660, 49668, 50833, 51596, 52502, 53965, 54512))
        return (yield from (self.unit_selection,self.unit_information,self.attack_confirmation,self.attack_confirmation,self.movement,self.tactics,self.withdrawal,self.wait_action,self.computer_action,self.village_service,self.next_side,self.duel_result,self.battle_result,self.defeated_roster,self.victor_roster,self.return_to_city,)[index]())

    def unit_selection(self):
        """$A04E: unit selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA04E)
        self._a(m[PHASE])
        self._mark(0xA051)
        index=self._dispatch(0xA051,(41054, 41101, 41147, 41240, 41400))
        return (yield from (self.choose_actor_control,self.await_cursor_refresh,self.select_unit,self.action_menu,self.confirm_action_menu,)[index]())

    def choose_actor_control(self):
        """A05E: inspect commander outcome, AP and real text readiness.

        Controller3 enters the computer proposal path only with positive AP.
        Human control waits for text and then enters unit selection. Exhausted
        or signed-negative AP tail-calls the original side-change procedure.
        """
        r=self.registers;m=self.memory;self._mark(0xA05E)
        if not (yield from self._local_call(self.commander_outcome,0xA05E,0xA061)):return
        self._a(m[CONTROLLER]);self._compare(r.a,3)
        if r.p&Z:
            self._a(m[AP])
            if r.p&(Z|N):return (yield from self.finish_side_turn())
            self._a(8);m[STATE]=r.a
            self._a(0);m[PHASE]=r.a
            self._rts();return
        if not (yield from self._local_call(self.text_readiness,0xA07A,0xA07D)):return
        if not r.p&C:self._rts();return
        self._a(m[AP])
        if r.p&(Z|N):return (yield from self.finish_side_turn())
        m[PHASE]=self._nz(m[PHASE]+1)
        self._rts()

    def await_cursor_refresh(self):
        """$A08D: await cursor refresh; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA08D)
        if not (yield from self._local_call(self.cursor_input,0xA08D,0xA090)):return
        self._a(m[0x0508])
        self._mark(0xA093)
        if not r.p&Z:
            pass
        else:
            self._a(m[PPU_JOBS])
            self._mark(0xA098)
            if not r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xC0)
                yield from self._external(0xA09F,0xF293,0xA0A2,"call",None)
                if r.pc!=0xA0A2:return  # preserve nonlocal stack return
                self._a(m[RULERS])
                self._y(m[SIDE])
                self._mark(0xA0A8)
                if not r.p&N:
                    pass
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    pass
                self._a(r.a & 0x0F)
                if not (yield from self._local_call(self.ruler_pointer,0xA0B0,0xA0B3)):return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x042C]=r.a
                pass
            pass
        self._mark(0xA0BA)
        self._rts();return

    def select_unit(self):
        """$A0BB: select unit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA0BB)
        if not (yield from self._local_call(self.cursor_input,0xA0BB,0xA0BE)):return
        if not (yield from self._local_call(self.battle_cursor,0xA0BE,0xA0C1)):return
        if not (yield from self._local_call(self.text_readiness,0xA0C1,0xA0C4)):return
        self._mark(0xA0C4)
        if r.p&C:
            if not (yield from self._local_call(self.direction_repeat,0xA0C7,0xA0CA)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xA0CE)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x02)
                self._mark(0xA0FF)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.unit_at_cursor,0xA101,0xA104)):return
                    self._a(r.y)
                    self._mark(0xA105)
                    if r.p&N:
                        pass
                    else:
                        m[SELECTED_SLOT]=r.y
                        m[ACTOR_SLOT]=r.y
                        self._a(0x01)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        pass
                    pass
                self._mark(0xA117)
                self._rts();return
            else:
                if not (yield from self._local_call(self.unit_at_cursor,0xA0D0,0xA0D3)):return
                self._a(r.y)
                self._mark(0xA0D4)
                if r.p&N:
                    self._a(m[NEW_BUTTONS])
                    self._a(r.a & 0x02)
                    self._mark(0xA0FF)
                    if r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.unit_at_cursor,0xA101,0xA104)):return
                        self._a(r.y)
                        self._mark(0xA105)
                        if r.p&N:
                            pass
                        else:
                            m[SELECTED_SLOT]=r.y
                            m[ACTOR_SLOT]=r.y
                            self._a(0x01)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            pass
                        pass
                    self._mark(0xA117)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xA0D6,0xA0D9)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xA0DB)
                    if r.p&Z:
                        self._a(m[NEW_BUTTONS])
                        self._a(r.a & 0x02)
                        self._mark(0xA0FF)
                        if r.p&Z:
                            pass
                        else:
                            if not (yield from self._local_call(self.unit_at_cursor,0xA101,0xA104)):return
                            self._a(r.y)
                            self._mark(0xA105)
                            if r.p&N:
                                pass
                            else:
                                m[SELECTED_SLOT]=r.y
                                m[ACTOR_SLOT]=r.y
                                self._a(0x01)
                                m[STATE]=r.a
                                self._a(0x00)
                                m[PHASE]=r.a
                                pass
                            pass
                        self._mark(0xA117)
                        self._rts();return
                    else:
                        m[SELECTED_SLOT]=r.y
                        m[ACTOR_SLOT]=r.y
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._y(0x3D)
                        yield from self._external(0xA0E8,0xEE07,0xA0ED,"far_call",40999)
                        if r.pc!=0xA0ED:return  # preserve nonlocal stack return
                        self._a(0xC1)
                        yield from self._external(0xA0EF,0xF283,0xA0F2,"call",None)
                        if r.pc!=0xA0F2:return  # preserve nonlocal stack return
                        self._a(0x00)
                        m[0x0424]=r.a
                        m[0x0425]=r.a
                        self._mark(0xA0FA)
                        self._rts();return
        else:
            self._mark(0xA0C6)
            self._rts();return

    def action_menu(self):
        """$A118: action menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA118)
        self._a(0x00)
        m[0x00A4]=r.a
        if not (yield from self._local_call(self.local_dc33,0xA11D,0xA120)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xA120,0xA123)):return
        self._a(0x93)
        m[0x0010]=r.a
        self._a(0xA1)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA12F,0xED1E,0xA132,"call",None)
        if r.pc!=0xA132:return  # preserve nonlocal stack return
        self._a(0x9B)
        m[0x0010]=r.a
        self._a(0xA1)
        m[0x0011]=r.a
        self._a(0xA7)
        m[0x0000]=r.a
        self._a(0xA1)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA144,0xEDF5,0xA147,"call",None)
        if r.pc!=0xA147:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xA147,0xA14A)):return
        self._mark(0xA14A)
        if not r.p&C:
            self._mark(0xA117)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xA150)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xA15E)
                if r.p&Z:
                    self._mark(0xA192)
                    self._rts();return
                else:
                    self._y(m[0x0012])
                    self._mark(0xA162)
                    if not r.p&Z:
                        self._compare(r.y,0x01)
                        self._mark(0xA176)
                        if not r.p&Z:
                            self._a(m[(0xA1AC+r.y)&65535])
                            m[STATE]=r.a
                            self._a(m[(0xA1B2+r.y)&65535])
                            m[PHASE]=r.a
                            self._a(0x01)
                            m[0x0012]=r.a
                            if not (yield from self._local_call(self.map_refresh,0xA18F,0xA192)):return
                            pass
                        else:
                            self._a(m[AP])
                            self._compare(r.a,0x02)
                            self._mark(0xA17D)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[(0xA1AC+r.y)&65535])
                                m[STATE]=r.a
                                self._a(m[(0xA1B2+r.y)&65535])
                                m[PHASE]=r.a
                                self._a(0x01)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xA18F,0xA192)):return
                                pass
                            pass
                        self._mark(0xA192)
                        self._rts();return
                    else:
                        self._x(m[SELECTED_SLOT])
                        self._a(m[(0x0650+r.x)&65535])
                        self._mark(0xA16A)
                        if r.p&Z:
                            self._compare(r.y,0x01)
                            self._mark(0xA176)
                            if not r.p&Z:
                                self._a(m[(0xA1AC+r.y)&65535])
                                m[STATE]=r.a
                                self._a(m[(0xA1B2+r.y)&65535])
                                m[PHASE]=r.a
                                self._a(0x01)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xA18F,0xA192)):return
                                pass
                            else:
                                self._a(m[AP])
                                self._compare(r.a,0x02)
                                self._mark(0xA17D)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[(0xA1AC+r.y)&65535])
                                    m[STATE]=r.a
                                    self._a(m[(0xA1B2+r.y)&65535])
                                    m[PHASE]=r.a
                                    self._a(0x01)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xA18F,0xA192)):return
                                    pass
                                pass
                            self._mark(0xA192)
                            self._rts();return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0xBC)
                            self._mark(0xA171)
                            yield from self._external(0xA171,0xF283,None,"tail")
                            return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                return (yield from self.return_command_cursor())

    def confirm_action_menu(self):
        """$A1B8: confirm action menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1B8)
        self._a(0x00)
        m[0x00A4]=r.a
        if not (yield from self._local_call(self.local_dc33,0xA1BD,0xA1C0)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xA1C0,0xA1C3)):return
        if not (yield from self._local_call(self.text_readiness,0xA1C3,0xA1C6)):return
        self._mark(0xA1C6)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xA1C8,0xA1CB)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xA1CF)
            if r.p&Z:
                pass
            else:
                self._a(0x01)
                m[PHASE]=r.a
                self._a(0x01)
                m[0x0012]=r.a
                if not (yield from self._local_call(self.map_refresh,0xA1DA,0xA1DD)):return
                pass
            pass
        self._mark(0xA1DD)
        self._rts();return

    def blink_command_cursor(self):
        """$A1DE: blink command cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1DE)
        self._a(m[0x005E])
        self._a(r.a & 0x07)
        self._mark(0xA1E3)
        if not r.p&Z:
            pass
        else:
            self._a(m[PPU_JOBS])
            self._a(r.a & 0x04)
            self._mark(0xA1EA)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x005E])
                self._a(r.a & 0x10)
                m[0x0012]=r.a
                if not (yield from self._local_call(self.map_refresh,0xA1F3,0xA1F6)):return
                pass
            pass
        self._mark(0xA1F6)
        self._rts();return

    def return_command_cursor(self):
        """$A1F7: return command cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1F7)
        self._a(0x05)
        yield from self._external(0xA1F9,0xF293,0xA1FC,"call",None)
        if r.pc!=0xA1FC:return  # preserve nonlocal stack return
        self._a(0x01)
        m[0x0012]=r.a
        if not (yield from self._local_call(self.map_refresh,0xA200,0xA203)):return
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xA20B)
        self._rts();return

    def unit_information(self):
        """$A21B: unit information; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA21B)
        self._a(m[PHASE])
        self._mark(0xA21E)
        index=self._dispatch(0xA21E,(41511, 41540, 41595))
        return (yield from (self.open_unit_information,self.navigate_unit_information,self.close_unit_information,)[index]())

    def open_unit_information(self):
        """$A227: open unit information; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA227)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x08)
        m[0x00BA]=r.a
        self._a(0x06)
        m[0x00BB]=r.a
        self._a(0x00)
        m[0x040C]=r.a
        m[0x040D]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        m[0x0410]=r.a
        self._mark(0xA243)
        self._rts();return

    def navigate_unit_information(self):
        """$A244: navigate unit information; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA244)
        if not (yield from self._local_call(self.blink_command_cursor,0xA244,0xA247)):return
        self._a(0xA7)
        m[0x000A]=r.a
        self._a(m[0x0410])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x00A4]=r.a
        self._y(0x39)
        yield from self._external(0xA257,0xEE07,0xA25C,"far_call",40960)
        if r.pc!=0xA25C:return  # preserve nonlocal stack return
        self._a(0x06)
        m[0x00BB]=r.a
        self._y(0x39)
        yield from self._external(0xA262,0xEE07,0xA267,"far_call",40978)
        if r.pc!=0xA267:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xA267,0xA26A)):return
        self._mark(0xA26A)
        if not r.p&C:
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xA270)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x05)
                yield from self._external(0xA277,0xF293,0xA27A,"call",None)
                if r.pc!=0xA27A:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xA27A)
        self._rts();return

    def close_unit_information(self):
        """$A27B: close unit information; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA27B)
        if not (yield from self._local_call(self.blink_command_cursor,0xA27B,0xA27E)):return
        if not (yield from self._local_call(self.text_readiness,0xA27E,0xA281)):return
        self._mark(0xA281)
        if not r.p&C:
            pass
        else:
            self._a(0x09)
            m[0x00BB]=r.a
            self._a(0x00)
            m[STATE]=r.a
            m[PHASE]=r.a
            if not (yield from self._local_call(self.return_command_cursor,0xA28F,0xA292)):return
            pass
        self._mark(0xA292)
        self._rts();return

    def attack_confirmation(self):
        """$A293: attack confirmation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA293)
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.local_dc36,0xA296,0xA299)):return
        self._a(m[PHASE])
        self._mark(0xA29C)
        index=self._dispatch(0xA29C,(41639, 41659, 41740, 41765))
        return (yield from (self.request_attack_target,self.choose_adjacent_target,self.acknowledge_attack_target,self.launch_attack_scene,)[index]())

    def request_attack_target(self):
        """$A2A7: request attack target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2A7)
        self._a(0xC3)
        yield from self._external(0xA2A9,0xF283,0xA2AC,"call",None)
        if r.pc!=0xA2AC:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(m[SELECTED_SLOT])
        m[ACTOR_SLOT]=r.a
        self._a(0x00)
        m[0x00A4]=r.a
        self._mark(0xA2BA)
        self._rts();return

    def choose_adjacent_target(self):
        """$A2BB: choose adjacent target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2BB)
        self._a(m[ACTOR_SLOT])
        m[SELECTED_SLOT]=r.a
        if not (yield from self._local_call(self.blink_command_cursor,0xA2C1,0xA2C4)):return
        if not (yield from self._local_call(self.direction_repeat,0xA2C4,0xA2C7)):return
        if not (yield from self._local_call(self.battle_cursor,0xA2C7,0xA2CA)):return
        if not (yield from self._local_call(self.text_readiness,0xA2CA,0xA2CD)):return
        self._mark(0xA2CD)
        if not r.p&C:
            self._mark(0xA30B)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xA2D3)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xA2E6)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.unit_at_cursor,0xA2E8,0xA2EB)):return
                    self._a(r.y)
                    self._mark(0xA2EC)
                    if r.p&N:
                        pass
                    else:
                        if not (yield from self._local_call(self.target_side_filter,0xA2EE,0xA2F1)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xA2F3)
                        if not r.p&Z:
                            pass
                        else:
                            m[SELECTED_SLOT]=r.y
                            if not (yield from self._local_call(self.orthogonal_attack_target,0xA2F8,0xA2FB)):return
                            self._a(r.x)
                            self._mark(0xA2FC)
                            if r.p&N:
                                pass
                            else:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(0x02)
                                m[0x00A4]=r.a
                                self._a(0xCB)
                                yield from self._external(0xA308,0xF283,0xA30B,"call",None)
                                if r.pc!=0xA30B:return  # preserve nonlocal stack return
                                pass
                            pass
                        pass
                    pass
                self._mark(0xA30B)
                self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def acknowledge_attack_target(self):
        """$A30C: acknowledge attack target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA30C)
        if not (yield from self._local_call(self.dialog_highlight,0xA30C,0xA30F)):return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x01)
        self._mark(0xA313)
        if r.p&Z:
            pass
        else:
            yield from self._external(0xA315,0xECEE,0xA318,"call",None)
            if r.pc!=0xA318:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            m[AP]=self._nz(m[AP]-1)
            m[AP]=self._nz(m[AP]-1)
            if not (yield from self._local_call(self.prepare_attack_parameters,0xA321,0xA324)):return
            pass
        self._mark(0xA324)
        self._rts();return

    def launch_attack_scene(self):
        """$A325: launch attack scene; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA325)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xA328)
        if not r.p&N:
            pass
        else:
            self._a(0x05)
            m[GLOBAL]=r.a
            self._a(0x00)
            m[0x0540]=r.a
            m[0x0541]=r.a
            m[0x0542]=r.a
            m[TACTIC]=r.a
            m[0x00A4]=r.a
            self._a(m[0x0090])
            m[0x0510]=r.a
            self._a(m[0x0091])
            m[0x0511]=r.a
            self._a(m[0x008E])
            m[0x0512]=r.a
            self._a(m[0x008F])
            m[0x0513]=r.a
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0600+r.y)&65535])
            m[0x0010]=r.a
            self._a(m[(0x0614+r.y)&65535])
            m[0x0011]=r.a
            if not (yield from self._local_call(self.terrain_at_position,0xA361,0xA364)):return
            m[TACTIC_FAILED]=r.a
            pass
        self._mark(0xA367)
        self._rts();return

    def orthogonal_attack_target(self):
        """$A368: orthogonal attack target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA368)
        self._x(m[ACTOR_SLOT])
        self._a(m[(0x0600+r.x)&65535])
        self._flag(C,True)
        self._add(0x01,subtract=True)
        self._compare(r.a,m[(0x0600+r.y)&65535])
        self._mark(0xA374)
        if not r.p&Z:
            self._x(m[ACTOR_SLOT])
            self._a(m[(0x0600+r.x)&65535])
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,m[(0x0600+r.y)&65535])
            self._mark(0xA38B)
            if not r.p&Z:
                self._x(m[ACTOR_SLOT])
                self._a(m[(0x0600+r.x)&65535])
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xA39E)
                if not r.p&Z:
                    self._x(m[ACTOR_SLOT])
                    self._a(m[(0x0600+r.x)&65535])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xA3BB)
                    if not r.p&Z:
                        self._x(0xFF)
                        self._mark(0xA3D1)
                        self._rts();return
                    else:
                        self._a(m[(0x0614+r.x)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x0F)
                        self._mark(0xA3C5)
                        if not r.p&Z:
                            pass
                        else:
                            self._flag(C,False)
                            self._add(0x01)
                            pass
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xA3CD)
                        if r.p&Z:
                            self._mark(0xA37E)
                            self._rts();return
                        else:
                            self._x(0xFF)
                            self._mark(0xA3D1)
                            self._rts();return
                else:
                    self._a(m[(0x0614+r.x)&65535])
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    self._compare(r.a,0x0F)
                    self._mark(0xA3A8)
                    if not r.p&Z:
                        pass
                    else:
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        pass
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xA3B0)
                    if r.p&Z:
                        self._mark(0xA37E)
                        self._rts();return
                    else:
                        self._x(m[ACTOR_SLOT])
                        self._a(m[(0x0600+r.x)&65535])
                        self._compare(r.a,m[(0x0600+r.y)&65535])
                        self._mark(0xA3BB)
                        if not r.p&Z:
                            self._x(0xFF)
                            self._mark(0xA3D1)
                            self._rts();return
                        else:
                            self._a(m[(0x0614+r.x)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x0F)
                            self._mark(0xA3C5)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            self._compare(r.a,m[(0x0614+r.y)&65535])
                            self._mark(0xA3CD)
                            if r.p&Z:
                                self._mark(0xA37E)
                                self._rts();return
                            else:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
            else:
                self._a(m[(0x0614+r.x)&65535])
                self._compare(r.a,m[(0x0614+r.y)&65535])
                self._mark(0xA393)
                if r.p&Z:
                    self._mark(0xA37E)
                    self._rts();return
                else:
                    self._x(m[ACTOR_SLOT])
                    self._a(m[(0x0600+r.x)&65535])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xA39E)
                    if not r.p&Z:
                        self._x(m[ACTOR_SLOT])
                        self._a(m[(0x0600+r.x)&65535])
                        self._compare(r.a,m[(0x0600+r.y)&65535])
                        self._mark(0xA3BB)
                        if not r.p&Z:
                            self._x(0xFF)
                            self._mark(0xA3D1)
                            self._rts();return
                        else:
                            self._a(m[(0x0614+r.x)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x0F)
                            self._mark(0xA3C5)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            self._compare(r.a,m[(0x0614+r.y)&65535])
                            self._mark(0xA3CD)
                            if r.p&Z:
                                self._mark(0xA37E)
                                self._rts();return
                            else:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
                    else:
                        self._a(m[(0x0614+r.x)&65535])
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        self._compare(r.a,0x0F)
                        self._mark(0xA3A8)
                        if not r.p&Z:
                            pass
                        else:
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            pass
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xA3B0)
                        if r.p&Z:
                            self._mark(0xA37E)
                            self._rts();return
                        else:
                            self._x(m[ACTOR_SLOT])
                            self._a(m[(0x0600+r.x)&65535])
                            self._compare(r.a,m[(0x0600+r.y)&65535])
                            self._mark(0xA3BB)
                            if not r.p&Z:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
                            else:
                                self._a(m[(0x0614+r.x)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x0F)
                                self._mark(0xA3C5)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                self._compare(r.a,m[(0x0614+r.y)&65535])
                                self._mark(0xA3CD)
                                if r.p&Z:
                                    self._mark(0xA37E)
                                    self._rts();return
                                else:
                                    self._x(0xFF)
                                    self._mark(0xA3D1)
                                    self._rts();return
        else:
            self._a(m[(0x0614+r.x)&65535])
            self._compare(r.a,m[(0x0614+r.y)&65535])
            self._mark(0xA37C)
            if not r.p&Z:
                self._x(m[ACTOR_SLOT])
                self._a(m[(0x0600+r.x)&65535])
                self._flag(C,False)
                self._add(0x01)
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xA38B)
                if not r.p&Z:
                    self._x(m[ACTOR_SLOT])
                    self._a(m[(0x0600+r.x)&65535])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xA39E)
                    if not r.p&Z:
                        self._x(m[ACTOR_SLOT])
                        self._a(m[(0x0600+r.x)&65535])
                        self._compare(r.a,m[(0x0600+r.y)&65535])
                        self._mark(0xA3BB)
                        if not r.p&Z:
                            self._x(0xFF)
                            self._mark(0xA3D1)
                            self._rts();return
                        else:
                            self._a(m[(0x0614+r.x)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x0F)
                            self._mark(0xA3C5)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            self._compare(r.a,m[(0x0614+r.y)&65535])
                            self._mark(0xA3CD)
                            if r.p&Z:
                                self._mark(0xA37E)
                                self._rts();return
                            else:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
                    else:
                        self._a(m[(0x0614+r.x)&65535])
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        self._compare(r.a,0x0F)
                        self._mark(0xA3A8)
                        if not r.p&Z:
                            pass
                        else:
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            pass
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xA3B0)
                        if r.p&Z:
                            self._mark(0xA37E)
                            self._rts();return
                        else:
                            self._x(m[ACTOR_SLOT])
                            self._a(m[(0x0600+r.x)&65535])
                            self._compare(r.a,m[(0x0600+r.y)&65535])
                            self._mark(0xA3BB)
                            if not r.p&Z:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
                            else:
                                self._a(m[(0x0614+r.x)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x0F)
                                self._mark(0xA3C5)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                self._compare(r.a,m[(0x0614+r.y)&65535])
                                self._mark(0xA3CD)
                                if r.p&Z:
                                    self._mark(0xA37E)
                                    self._rts();return
                                else:
                                    self._x(0xFF)
                                    self._mark(0xA3D1)
                                    self._rts();return
                else:
                    self._a(m[(0x0614+r.x)&65535])
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xA393)
                    if r.p&Z:
                        self._mark(0xA37E)
                        self._rts();return
                    else:
                        self._x(m[ACTOR_SLOT])
                        self._a(m[(0x0600+r.x)&65535])
                        self._compare(r.a,m[(0x0600+r.y)&65535])
                        self._mark(0xA39E)
                        if not r.p&Z:
                            self._x(m[ACTOR_SLOT])
                            self._a(m[(0x0600+r.x)&65535])
                            self._compare(r.a,m[(0x0600+r.y)&65535])
                            self._mark(0xA3BB)
                            if not r.p&Z:
                                self._x(0xFF)
                                self._mark(0xA3D1)
                                self._rts();return
                            else:
                                self._a(m[(0x0614+r.x)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x0F)
                                self._mark(0xA3C5)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                self._compare(r.a,m[(0x0614+r.y)&65535])
                                self._mark(0xA3CD)
                                if r.p&Z:
                                    self._mark(0xA37E)
                                    self._rts();return
                                else:
                                    self._x(0xFF)
                                    self._mark(0xA3D1)
                                    self._rts();return
                        else:
                            self._a(m[(0x0614+r.x)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._compare(r.a,0x0F)
                            self._mark(0xA3A8)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                pass
                            self._compare(r.a,m[(0x0614+r.y)&65535])
                            self._mark(0xA3B0)
                            if r.p&Z:
                                self._mark(0xA37E)
                                self._rts();return
                            else:
                                self._x(m[ACTOR_SLOT])
                                self._a(m[(0x0600+r.x)&65535])
                                self._compare(r.a,m[(0x0600+r.y)&65535])
                                self._mark(0xA3BB)
                                if not r.p&Z:
                                    self._x(0xFF)
                                    self._mark(0xA3D1)
                                    self._rts();return
                                else:
                                    self._a(m[(0x0614+r.x)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA3C5)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    self._compare(r.a,m[(0x0614+r.y)&65535])
                                    self._mark(0xA3CD)
                                    if r.p&Z:
                                        self._mark(0xA37E)
                                        self._rts();return
                                    else:
                                        self._x(0xFF)
                                        self._mark(0xA3D1)
                                        self._rts();return
            else:
                self._mark(0xA37E)
                self._rts();return

    def prepare_attack_parameters(self):
        """$A3D2: prepare attack parameters; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3D2)
        self._a(0x00)
        m[TACTIC_FAILED]=r.a
        self._y(m[ACTOR_SLOT])
        self._x(0x00)
        if not (yield from self._local_call(self.save_attack_attributes,0xA3DC,0xA3DF)):return
        self._y(m[SELECTED_SLOT])
        self._x(0x01)
        self._a(0x00)
        m[(0x0650+r.y)&65535]=r.a
        if not (yield from self._local_call(self.save_attack_attributes,0xA3E9,0xA3EC)):return
        self._a(m[SIDE])
        self._mark(0xA3EF)
        if r.p&N:
            self._a(m[RULERS])
            self._a(r.a & 0x0F)
            m[0x0565]=r.a
            self._a(m[RULERS])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0564]=r.a
            pass
        else:
            self._a(m[RULERS])
            self._a(r.a & 0x0F)
            m[0x0564]=r.a
            self._a(m[RULERS])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0565]=r.a
            pass
        self._a(m[0x0564])
        if not (yield from self._local_call(self.ruler_pointer,0xA41B,0xA41E)):return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0562]=r.a
        self._a(m[0x0565])
        if not (yield from self._local_call(self.ruler_pointer,0xA428,0xA42B)):return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0563]=r.a
        self._mark(0xA432)
        self._rts();return

    def save_attack_attributes(self):
        """$A433: save attack attributes; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA433)
        self._a(m[(0x0664+r.y)&65535])
        m[(0x0560+r.x)&65535]=r.a
        yield from self._external(0xA439,0xF2D7,0xA43C,"call",None)
        if r.pc!=0xA43C:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0xF0)
        m[(0x052C+r.x)&65535]=r.a
        self._y(0x01)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[(0x052E+r.x)&65535]=r.a
        self._mark(0xA44C)
        self._rts();return

    def movement(self):
        """$A44D: movement; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA44D)
        self._a(m[PHASE])
        self._compare(r.a,0x02)
        self._mark(0xA452)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x00A4]=r.a
            if not (yield from self._local_call(self.local_dc33,0xA459,0xA45C)):return
            pass
        self._a(m[PHASE])
        self._mark(0xA45F)
        index=self._dispatch(0xA45F,(42096, 42110, 42165, 42271, 42293, 42446, 42519))
        return (yield from (self.request_move_target,self.advance_move_cursor,self.check_destination_event,self.request_ambush_scan,self.consume_ambush_result,self.acknowledge_ambush_damage,self.acknowledge_move_result,)[index]())

    def request_move_target(self):
        """$A470: request move target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA470)
        self._a(0xC6)
        yield from self._external(0xA472,0xF283,0xA475,"call",None)
        if r.pc!=0xA475:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[ACTOR_SLOT]=r.a
        self._mark(0xA47D)
        self._rts();return

    def advance_move_cursor(self):
        """$A47E: advance move cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA47E)
        if not (yield from self._local_call(self.blink_command_cursor,0xA47E,0xA481)):return
        if not (yield from self._local_call(self.local_a64a,0xA481,0xA484)):return
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0002]=r.a
        if not (yield from self._local_call(self.local_da5a,0xA491,0xA494)):return
        self._a(m[0x0000])
        m[0x6F3F]=r.a
        self._a(m[0x0001])
        m[0x6F40]=r.a
        self._a(m[0x0002])
        m[0x6F41]=r.a
        self._a(m[0x0003])
        m[0x6F42]=r.a
        if not (yield from self._local_call(self.cursor_input,0xA4A8,0xA4AB)):return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x01)
        self._mark(0xA4AF)
        if r.p&Z:
            pass
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xA4B4)
        self._rts();return

    def check_destination_event(self):
        """$A4B5: check destination event; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4B5)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        self._a(m[SIDE])
        self._mark(0xA4C5)
        if not r.p&N:
            self._a(m[CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xA4DB)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xA507)
                self._rts();return
            else:
                self._y(0x31)
                yield from self._external(0xA4DF,0xF25F,0xA4E2,"call",None)
                if r.pc!=0xA4E2:return  # preserve nonlocal stack return
                self._a(m[CITY])
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0000]=r.a
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(m[0x0000])
                self._y(r.a)
                self._x(0x00)
                while True:  # natural loop $A4EF
                    self._a(m[(0x9BA4+r.y)&65535])
                    self._compare(r.a,m[0x0010])
                    self._mark(0xA4F4)
                    if not r.p&Z:
                        self._y(r.y+1)
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._compare(r.x,0x03)
                        self._mark(0xA502)
                        if not r.p&C:
                            continue
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._mark(0xA507)
                            self._rts();return
                    else:
                        self._a(m[(0x9BA5+r.y)&65535])
                        self._compare(r.a,m[0x0011])
                        self._mark(0xA4FB)
                        if r.p&Z:
                            m[0x0470]=r.x
                            self._a(0x01)
                            m[0x0012]=r.a
                            if not (yield from self._local_call(self.map_refresh,0xA50F,0xA512)):return
                            self._a(0x09)
                            m[STATE]=r.a
                            m[PHASE]=r.a
                            self._a(0xA7)
                            self._mark(0xA51C)
                            yield from self._external(0xA51C,0xF293,None,"tail")
                            return
                        else:
                            self._y(r.y+1)
                            self._y(r.y+1)
                            self._x(r.x+1)
                            self._compare(r.x,0x03)
                            self._mark(0xA502)
                            if not r.p&C:
                                continue
                            else:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._mark(0xA507)
                                self._rts();return
        else:
            if not (yield from self._local_call(self.terrain_at_position,0xA4C7,0xA4CA)):return
            self._compare(r.a,0x05)
            self._mark(0xA4CC)
            if not r.p&Z:
                self._a(m[CONTROLLER])
                self._compare(r.a,0x03)
                self._mark(0xA4DB)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xA507)
                    self._rts();return
                else:
                    self._y(0x31)
                    yield from self._external(0xA4DF,0xF25F,0xA4E2,"call",None)
                    if r.pc!=0xA4E2:return  # preserve nonlocal stack return
                    self._a(m[CITY])
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0000]=r.a
                    r.a=self._shift(r.a,True,rotate=False)
                    self._flag(C,False)
                    self._add(m[0x0000])
                    self._y(r.a)
                    self._x(0x00)
                    while True:  # natural loop $A4EF
                        self._a(m[(0x9BA4+r.y)&65535])
                        self._compare(r.a,m[0x0010])
                        self._mark(0xA4F4)
                        if not r.p&Z:
                            self._y(r.y+1)
                            self._y(r.y+1)
                            self._x(r.x+1)
                            self._compare(r.x,0x03)
                            self._mark(0xA502)
                            if not r.p&C:
                                continue
                            else:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._mark(0xA507)
                                self._rts();return
                        else:
                            self._a(m[(0x9BA5+r.y)&65535])
                            self._compare(r.a,m[0x0011])
                            self._mark(0xA4FB)
                            if r.p&Z:
                                m[0x0470]=r.x
                                self._a(0x01)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xA50F,0xA512)):return
                                self._a(0x09)
                                m[STATE]=r.a
                                m[PHASE]=r.a
                                self._a(0xA7)
                                self._mark(0xA51C)
                                yield from self._external(0xA51C,0xF293,None,"tail")
                                return
                            else:
                                self._y(r.y+1)
                                self._y(r.y+1)
                                self._x(r.x+1)
                                self._compare(r.x,0x03)
                                self._mark(0xA502)
                                if not r.p&C:
                                    continue
                                else:
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._mark(0xA507)
                                    self._rts();return
            else:
                self._y(0x28)
                yield from self._external(0xA4D0,0xEE07,0xA4D5,"far_call",40999)
                if r.pc!=0xA4D5:return  # preserve nonlocal stack return
                self._mark(0xA4D5)
                self._rts();return

    def request_ambush_scan(self):
        """$A51F: request ambush scan; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA51F)
        self._a(m[0x6F8B])
        self._compare(r.a,0xFF)
        self._mark(0xA524)
        if not r.p&Z:
            pass
        else:
            self._a(0x01)
            m[0x6F8B]=r.a
            self._a(m[SELECTED_SLOT])
            m[0x6F8C]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xA534)
        self._rts();return

    def consume_ambush_result(self):
        """$A535: consume ambush result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA535)
        self._a(m[0x6F8B])
        self._compare(r.a,0xFF)
        self._mark(0xA53A)
        if r.p&Z:
            self._a(m[0x6F8F])
            self._mark(0xA540)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[0x042C])
                m[0x000B]=r.a
                self._a(m[0x042D])
                m[0x000C]=r.a
                self._y(0x04)
                self._a(m[SIDE])
                self._mark(0xA557)
                if not r.p&N:
                    pass
                else:
                    self._y(0x00)
                    pass
                self._a(m[(0x04D8+r.y)&65535])
                self._y(r.a)
                self._a(m[(0x0664+r.y)&65535])
                m[0x000A]=r.a
                yield from self._external(0xA564,0xF2D7,0xA567,"call",None)
                if r.pc!=0xA567:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                m[0x052C]=r.a
                self._y(0x01)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x052E]=r.a
                self._y(0x2E)
                yield from self._external(0xA579,0xEE07,0xA57E,"far_call",40966)
                if r.pc!=0xA57E:return  # preserve nonlocal stack return
                if not (yield from self._local_call(self.refresh_hundred_troops,0xA57E,0xA581)):return
                self._a(m[SELECTED_SLOT])
                m[ACTOR_SLOT]=r.a
                self._y(m[0x6F8C])
                self._a(m[(0x6FA1+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA58F)
                if r.p&Z:
                    self._a(0x03)
                    m[0x00A4]=r.a
                    self._a(0x00)
                    m[0x052E]=r.a
                    self._a(0xB8)
                    pass
                else:
                    self._y(0x04)
                    self._a(m[SIDE])
                    self._mark(0xA596)
                    if not r.p&N:
                        pass
                    else:
                        self._y(0x00)
                        pass
                    self._a(m[(0x04D8+r.y)&65535])
                    m[SELECTED_SLOT]=r.a
                    self._a(0x04)
                    m[0x00A4]=r.a
                    self._a(0xB9)
                    pass
                yield from self._external(0xA5B6,0xF283,0xA5B9,"call",None)
                if r.pc!=0xA5B9:return  # preserve nonlocal stack return
                self._y(0x3D)
                yield from self._external(0xA5BB,0xEE07,0xA5C0,"far_call",40999)
                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                self._a(m[SELECTED_SLOT])
                self._x(r.a)
                self._a(m[ACTOR_SLOT])
                m[SELECTED_SLOT]=r.a
                m[ACTOR_SLOT]=r.x
                self._mark(0xA5CD)
                self._rts();return
            else:
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                if not (yield from self._local_call(self.return_command_cursor,0xA63C,0xA63F)):return
                self._mark(0xA63F)
                self._rts();return
        else:
            self._mark(0xA53C)
            self._rts();return

    def acknowledge_ambush_damage(self):
        """$A5CE: acknowledge ambush damage; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5CE)
        self._a(0x03)
        m[0x00A4]=r.a
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.local_dc36,0xA5D6,0xA5D9)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xA5D9,0xA5DC)):return
        if not (yield from self._local_call(self.text_readiness,0xA5DC,0xA5DF)):return
        self._mark(0xA5DF)
        if not r.p&C:
            self._mark(0xA616)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xA5E1,0xA5E4)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xA5E8)
            if r.p&Z:
                self._mark(0xA616)
                self._rts();return
            else:
                self._y(0x04)
                self._a(m[SIDE])
                self._mark(0xA5EF)
                if not r.p&N:
                    pass
                else:
                    self._y(0x00)
                    pass
                self._a(0xFF)
                m[(0x04D8+r.y)&65535]=r.a
                self._a(m[0x052E])
                self._mark(0xA5FB)
                if r.p&Z:
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.return_command_cursor,0xA63C,0xA63F)):return
                    self._mark(0xA63F)
                    self._rts();return
                else:
                    self._y(m[ACTOR_SLOT])
                    self._a(m[(0x0664+r.y)&65535])
                    m[0x042C]=r.a
                    if not (yield from self._local_call(self.local_dee9,0xA606,0xA609)):return
                    self._mark(0xA609)
                    if not r.p&C:
                        self._a(0x00)
                        m[STATE]=r.a
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.return_command_cursor,0xA63C,0xA63F)):return
                        self._mark(0xA63F)
                        self._rts();return
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        yield from self._external(0xA60E,0xE57F,0xA611,"call",None)
                        if r.pc!=0xA611:return  # preserve nonlocal stack return
                        self._a(0x7B)
                        yield from self._external(0xA613,0xE68B,0xA616,"call",None)
                        if r.pc!=0xA616:return  # preserve nonlocal stack return
                        self._mark(0xA616)
                        self._rts();return

    def acknowledge_move_result(self):
        """$A617: acknowledge move result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA617)
        if not (yield from self._local_call(self.text_readiness,0xA617,0xA61A)):return
        self._mark(0xA61A)
        if not r.p&C:
            self._mark(0xA63F)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xA61C,0xA61F)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xA623)
            if r.p&Z:
                self._mark(0xA63F)
                self._rts();return
            else:
                self._a(m[0x042D])
                self._compare(r.a,0xFF)
                self._mark(0xA62A)
                if not r.p&Z:
                    self._a(0xFF)
                    m[0x042D]=r.a
                    self._a(0x4B)
                    self._mark(0xA647)
                    yield from self._external(0xA647,0xF293,None,"tail")
                    return
                else:
                    yield from self._external(0xA62C,0xE57F,0xA62F,"call",None)
                    if r.pc!=0xA62F:return  # preserve nonlocal stack return
                    self._a(0x1D)
                    yield from self._external(0xA631,0xE673,0xA634,"call",None)
                    if r.pc!=0xA634:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.return_command_cursor,0xA63C,0xA63F)):return
                    self._mark(0xA63F)
                    self._rts();return

    def local_a64a(self):
        """$A64A: local a64a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA64A)
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x02)
        self._mark(0xA64E)
        if r.p&Z:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xA685)
            if not r.p&N:
                self._a(m[NEW_BUTTONS])
                self._mark(0xA6D0)
                if not r.p&N:
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._mark(0xA720)
                    if not r.p&N:
                        pass
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        self._mark(0xA730)
                        if r.p&N:
                            pass
                        else:
                            self._compare(r.a,0x0F)
                            self._mark(0xA734)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                pass
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                            self._a(r.y)
                            self._mark(0xA73F)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0010]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._compare(r.a,0x0F)
                                self._mark(0xA751)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0011]=r.a
                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                self._mark(0xA75E)
                                if not r.p&C:
                                    pass
                                else:
                                    m[AP]=r.a
                                    self._a(r.x)
                                    self._push(r.a)
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                    self._a(self._pop())
                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                    self._a(m[(0x0614+r.x)&65535])
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA77B)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._mark(0xA784)
                    if not r.p&N:
                        pass
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x14)
                        self._mark(0xA796)
                        if r.p&C:
                            pass
                        else:
                            self._compare(r.a,0x0F)
                            self._mark(0xA79A)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                            self._a(r.y)
                            self._mark(0xA7A5)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0010]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x0F)
                                self._mark(0xA7B7)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0011]=r.a
                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                self._mark(0xA7C4)
                                if not r.p&C:
                                    pass
                                else:
                                    m[AP]=r.a
                                    self._a(r.x)
                                    self._push(r.a)
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                    self._a(self._pop())
                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                    self._a(m[(0x0614+r.x)&65535])
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA7E1)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    self._mark(0xA7E6)
                    self._rts();return
                else:
                    self._y(m[SELECTED_SLOT])
                    self._a(m[(0x0600+r.y)&65535])
                    self._flag(C,False)
                    self._add(0x01)
                    self._compare(r.a,0x20)
                    self._mark(0xA6DD)
                    if r.p&C:
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA720)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._mark(0xA730)
                            if r.p&N:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA734)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                self._a(r.y)
                                self._mark(0xA73F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA751)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                    self._mark(0xA75E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA77B)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA784)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x14)
                            self._mark(0xA796)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA79A)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                self._a(r.y)
                                self._mark(0xA7A5)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA7B7)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                    self._mark(0xA7C4)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7E1)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xA7E6)
                        self._rts();return
                    else:
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        m[0x0001]=r.a
                        if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                        self._a(r.y)
                        self._mark(0xA6EA)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA720)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xA730)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA734)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                    self._a(r.y)
                                    self._mark(0xA73F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA751)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                        self._mark(0xA75E)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA77B)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA784)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xA796)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA79A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                    self._a(r.y)
                                    self._mark(0xA7A5)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7B7)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                        self._mark(0xA7C4)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7E1)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xA7E6)
                            self._rts();return
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            m[0x0010]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            m[0x0011]=r.a
                            if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                            if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                            self._mark(0xA702)
                            if not r.p&C:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                m[AP]=r.a
                                self._a(r.x)
                                self._push(r.a)
                                self._a(0x00)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                self._a(self._pop())
                                if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                self._x(m[SELECTED_SLOT])
                                m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                self._mark(0xA71A)
                                self._rts();return
            else:
                self._y(m[SELECTED_SLOT])
                self._a(m[(0x0600+r.y)&65535])
                self._flag(C,True)
                self._add(0x01,subtract=True)
                self._mark(0xA690)
                if not r.p&C:
                    self._a(m[NEW_BUTTONS])
                    self._mark(0xA6D0)
                    if not r.p&N:
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA720)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._mark(0xA730)
                            if r.p&N:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA734)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                self._a(r.y)
                                self._mark(0xA73F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA751)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                    self._mark(0xA75E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA77B)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA784)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x14)
                            self._mark(0xA796)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA79A)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                self._a(r.y)
                                self._mark(0xA7A5)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA7B7)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                    self._mark(0xA7C4)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7E1)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xA7E6)
                        self._rts();return
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x20)
                        self._mark(0xA6DD)
                        if r.p&C:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA720)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xA730)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA734)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                    self._a(r.y)
                                    self._mark(0xA73F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA751)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                        self._mark(0xA75E)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA77B)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA784)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xA796)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA79A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                    self._a(r.y)
                                    self._mark(0xA7A5)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7B7)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                        self._mark(0xA7C4)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7E1)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xA7E6)
                            self._rts();return
                        else:
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                            self._a(r.y)
                            self._mark(0xA6EA)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                m[0x0010]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                m[0x0011]=r.a
                                if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                self._mark(0xA702)
                                if not r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    m[AP]=r.a
                                    self._a(r.x)
                                    self._push(r.a)
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                    self._a(self._pop())
                                    if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                    self._mark(0xA71A)
                                    self._rts();return
                else:
                    m[0x0000]=r.a
                    self._a(m[(0x0614+r.y)&65535])
                    m[0x0001]=r.a
                    if not (yield from self._local_call(self.local_d6b6,0xA699,0xA69C)):return
                    self._a(r.y)
                    self._mark(0xA69D)
                    if not r.p&N:
                        self._a(m[NEW_BUTTONS])
                        self._mark(0xA6D0)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA720)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xA730)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA734)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                    self._a(r.y)
                                    self._mark(0xA73F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA751)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                        self._mark(0xA75E)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA77B)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA784)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xA796)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA79A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                    self._a(r.y)
                                    self._mark(0xA7A5)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7B7)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                        self._mark(0xA7C4)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7E1)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xA7E6)
                            self._rts();return
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x20)
                            self._mark(0xA6DD)
                            if r.p&C:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                                self._a(r.y)
                                self._mark(0xA6EA)
                                if not r.p&N:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                    self._mark(0xA702)
                                    if not r.p&C:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA720)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xA730)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA734)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                self._a(r.y)
                                                self._mark(0xA73F)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA751)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                    self._mark(0xA75E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA77B)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA784)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xA796)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA79A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                self._a(r.y)
                                                self._mark(0xA7A5)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7B7)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                    self._mark(0xA7C4)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7E1)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xA7E6)
                                        self._rts();return
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                        self._mark(0xA71A)
                                        self._rts();return
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        m[0x0010]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        m[0x0011]=r.a
                        if not (yield from self._local_call(self.terrain_at_position,0xA6AF,0xA6B2)):return
                        if not (yield from self._local_call(self.local_a7e7,0xA6B2,0xA6B5)):return
                        self._mark(0xA6B5)
                        if not r.p&C:
                            self._a(m[NEW_BUTTONS])
                            self._mark(0xA6D0)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x20)
                                self._mark(0xA6DD)
                                if r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                                    self._a(r.y)
                                    self._mark(0xA6EA)
                                    if not r.p&N:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA720)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xA730)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA734)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                self._a(r.y)
                                                self._mark(0xA73F)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA751)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                    self._mark(0xA75E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA77B)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA784)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xA796)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA79A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                self._a(r.y)
                                                self._mark(0xA7A5)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7B7)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                    self._mark(0xA7C4)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7E1)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xA7E6)
                                        self._rts();return
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                        self._mark(0xA702)
                                        if not r.p&C:
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA720)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._mark(0xA730)
                                                if r.p&N:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA734)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                    self._a(r.y)
                                                    self._mark(0xA73F)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA751)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,True)
                                                            self._add(0x01,subtract=True)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                        self._mark(0xA75E)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA77B)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA784)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x14)
                                                self._mark(0xA796)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA79A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                    self._a(r.y)
                                                    self._mark(0xA7A5)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7B7)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,False)
                                                            self._add(0x01)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                        self._mark(0xA7C4)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA7E1)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._mark(0xA7E6)
                                            self._rts();return
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                            self._mark(0xA71A)
                                            self._rts();return
                        else:
                            m[AP]=r.a
                            self._a(r.x)
                            self._push(r.a)
                            self._a(0x00)
                            m[0x0012]=r.a
                            if not (yield from self._local_call(self.map_refresh,0xA6C0,0xA6C3)):return
                            self._a(self._pop())
                            if not (yield from self._local_call(self.local_a85b,0xA6C4,0xA6C7)):return
                            self._x(m[SELECTED_SLOT])
                            m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]-1)
                            self._mark(0xA6CD)
                            self._rts();return
        else:
            self._y(m[ACTOR_SLOT])
            self._mark(0xA653)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xA685)
                if not r.p&N:
                    self._a(m[NEW_BUTTONS])
                    self._mark(0xA6D0)
                    if not r.p&N:
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA720)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._mark(0xA730)
                            if r.p&N:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA734)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                self._a(r.y)
                                self._mark(0xA73F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA751)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                    self._mark(0xA75E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA77B)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xA784)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x14)
                            self._mark(0xA796)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xA79A)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                self._a(r.y)
                                self._mark(0xA7A5)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA7B7)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                    self._mark(0xA7C4)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7E1)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xA7E6)
                        self._rts();return
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x20)
                        self._mark(0xA6DD)
                        if r.p&C:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA720)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xA730)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA734)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                    self._a(r.y)
                                    self._mark(0xA73F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA751)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                        self._mark(0xA75E)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA77B)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA784)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xA796)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA79A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                    self._a(r.y)
                                    self._mark(0xA7A5)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7B7)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                        self._mark(0xA7C4)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7E1)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xA7E6)
                            self._rts();return
                        else:
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                            self._a(r.y)
                            self._mark(0xA6EA)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                m[0x0010]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                m[0x0011]=r.a
                                if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                self._mark(0xA702)
                                if not r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    m[AP]=r.a
                                    self._a(r.x)
                                    self._push(r.a)
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                    self._a(self._pop())
                                    if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                    self._mark(0xA71A)
                                    self._rts();return
                else:
                    self._y(m[SELECTED_SLOT])
                    self._a(m[(0x0600+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    self._mark(0xA690)
                    if not r.p&C:
                        self._a(m[NEW_BUTTONS])
                        self._mark(0xA6D0)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA720)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xA730)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA734)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                    self._a(r.y)
                                    self._mark(0xA73F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA751)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                        self._mark(0xA75E)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA77B)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xA784)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xA796)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xA79A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                    self._a(r.y)
                                    self._mark(0xA7A5)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA7B7)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                        self._mark(0xA7C4)
                                        if not r.p&C:
                                            pass
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7E1)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xA7E6)
                            self._rts();return
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x20)
                            self._mark(0xA6DD)
                            if r.p&C:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                                self._a(r.y)
                                self._mark(0xA6EA)
                                if not r.p&N:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    m[0x0010]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    m[0x0011]=r.a
                                    if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                    if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                    self._mark(0xA702)
                                    if not r.p&C:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA720)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xA730)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA734)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                self._a(r.y)
                                                self._mark(0xA73F)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA751)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                    self._mark(0xA75E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA77B)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA784)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xA796)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA79A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                self._a(r.y)
                                                self._mark(0xA7A5)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7B7)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                    self._mark(0xA7C4)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7E1)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xA7E6)
                                        self._rts();return
                                    else:
                                        m[AP]=r.a
                                        self._a(r.x)
                                        self._push(r.a)
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                        self._a(self._pop())
                                        if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                        self._mark(0xA71A)
                                        self._rts();return
                    else:
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        m[0x0001]=r.a
                        if not (yield from self._local_call(self.local_d6b6,0xA699,0xA69C)):return
                        self._a(r.y)
                        self._mark(0xA69D)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            self._mark(0xA6D0)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA720)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xA730)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA734)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                        self._a(r.y)
                                        self._mark(0xA73F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA751)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                            self._mark(0xA75E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA77B)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xA784)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xA796)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xA79A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                        self._a(r.y)
                                        self._mark(0xA7A5)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA7B7)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                            self._mark(0xA7C4)
                                            if not r.p&C:
                                                pass
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7E1)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xA7E6)
                                self._rts();return
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x20)
                                self._mark(0xA6DD)
                                if r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                                    self._a(r.y)
                                    self._mark(0xA6EA)
                                    if not r.p&N:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA720)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xA730)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA734)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                self._a(r.y)
                                                self._mark(0xA73F)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA751)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                    self._mark(0xA75E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA77B)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA784)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xA796)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA79A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                self._a(r.y)
                                                self._mark(0xA7A5)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7B7)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                    self._mark(0xA7C4)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7E1)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xA7E6)
                                        self._rts();return
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        m[0x0010]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        m[0x0011]=r.a
                                        if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                        if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                        self._mark(0xA702)
                                        if not r.p&C:
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA720)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._mark(0xA730)
                                                if r.p&N:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA734)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                    self._a(r.y)
                                                    self._mark(0xA73F)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA751)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,True)
                                                            self._add(0x01,subtract=True)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                        self._mark(0xA75E)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA77B)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA784)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x14)
                                                self._mark(0xA796)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA79A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                    self._a(r.y)
                                                    self._mark(0xA7A5)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7B7)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,False)
                                                            self._add(0x01)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                        self._mark(0xA7C4)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA7E1)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._mark(0xA7E6)
                                            self._rts();return
                                        else:
                                            m[AP]=r.a
                                            self._a(r.x)
                                            self._push(r.a)
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                            self._a(self._pop())
                                            if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                            self._mark(0xA71A)
                                            self._rts();return
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            m[0x0010]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            m[0x0011]=r.a
                            if not (yield from self._local_call(self.terrain_at_position,0xA6AF,0xA6B2)):return
                            if not (yield from self._local_call(self.local_a7e7,0xA6B2,0xA6B5)):return
                            self._mark(0xA6B5)
                            if not r.p&C:
                                self._a(m[NEW_BUTTONS])
                                self._mark(0xA6D0)
                                if not r.p&N:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA720)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xA730)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA734)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                            self._a(r.y)
                                            self._mark(0xA73F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA751)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                self._mark(0xA75E)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA77B)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xA784)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xA796)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xA79A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                            self._a(r.y)
                                            self._mark(0xA7A5)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0010]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA7B7)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0011]=r.a
                                                if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                self._mark(0xA7C4)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    m[AP]=r.a
                                                    self._a(r.x)
                                                    self._push(r.a)
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                    self._a(self._pop())
                                                    if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7E1)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xA7E6)
                                    self._rts();return
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x20)
                                    self._mark(0xA6DD)
                                    if r.p&C:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA720)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xA730)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA734)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                self._a(r.y)
                                                self._mark(0xA73F)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA751)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                    self._mark(0xA75E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA77B)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xA784)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xA796)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xA79A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                self._a(r.y)
                                                self._mark(0xA7A5)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0010]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA7B7)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0011]=r.a
                                                    if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                    if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                    self._mark(0xA7C4)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        m[AP]=r.a
                                                        self._a(r.x)
                                                        self._push(r.a)
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                        self._a(self._pop())
                                                        if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7E1)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xA7E6)
                                        self._rts();return
                                    else:
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xA6E6,0xA6E9)):return
                                        self._a(r.y)
                                        self._mark(0xA6EA)
                                        if not r.p&N:
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA720)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._mark(0xA730)
                                                if r.p&N:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA734)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                    self._a(r.y)
                                                    self._mark(0xA73F)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA751)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,True)
                                                            self._add(0x01,subtract=True)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                        self._mark(0xA75E)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA77B)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xA784)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x14)
                                                self._mark(0xA796)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xA79A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                    self._a(r.y)
                                                    self._mark(0xA7A5)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        self._y(m[SELECTED_SLOT])
                                                        self._a(m[(0x0600+r.y)&65535])
                                                        m[0x0010]=r.a
                                                        self._a(m[(0x0614+r.y)&65535])
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA7B7)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,False)
                                                            self._add(0x01)
                                                            pass
                                                        m[0x0011]=r.a
                                                        if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                        if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                        self._mark(0xA7C4)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            m[AP]=r.a
                                                            self._a(r.x)
                                                            self._push(r.a)
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                            self._a(self._pop())
                                                            if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA7E1)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._mark(0xA7E6)
                                            self._rts();return
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            m[0x0010]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            m[0x0011]=r.a
                                            if not (yield from self._local_call(self.terrain_at_position,0xA6FC,0xA6FF)):return
                                            if not (yield from self._local_call(self.local_a7e7,0xA6FF,0xA702)):return
                                            self._mark(0xA702)
                                            if not r.p&C:
                                                self._a(m[NEW_BUTTONS])
                                                r.a=self._shift(r.a,True,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._mark(0xA720)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0000]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    self._mark(0xA730)
                                                    if r.p&N:
                                                        pass
                                                    else:
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA734)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,True)
                                                            self._add(0x01,subtract=True)
                                                            pass
                                                        m[0x0001]=r.a
                                                        if not (yield from self._local_call(self.local_d6b6,0xA73B,0xA73E)):return
                                                        self._a(r.y)
                                                        self._mark(0xA73F)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            self._y(m[SELECTED_SLOT])
                                                            self._a(m[(0x0600+r.y)&65535])
                                                            m[0x0010]=r.a
                                                            self._a(m[(0x0614+r.y)&65535])
                                                            self._flag(C,True)
                                                            self._add(0x01,subtract=True)
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA751)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                self._flag(C,True)
                                                                self._add(0x01,subtract=True)
                                                                pass
                                                            m[0x0011]=r.a
                                                            if not (yield from self._local_call(self.terrain_at_position,0xA758,0xA75B)):return
                                                            if not (yield from self._local_call(self.local_a7e7,0xA75B,0xA75E)):return
                                                            self._mark(0xA75E)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                m[AP]=r.a
                                                                self._a(r.x)
                                                                self._push(r.a)
                                                                self._a(0x00)
                                                                m[0x0012]=r.a
                                                                if not (yield from self._local_call(self.map_refresh,0xA769,0xA76C)):return
                                                                self._a(self._pop())
                                                                if not (yield from self._local_call(self.local_a85b,0xA76D,0xA770)):return
                                                                self._x(m[SELECTED_SLOT])
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                self._a(m[(0x0614+r.x)&65535])
                                                                self._compare(r.a,0x0F)
                                                                self._mark(0xA77B)
                                                                if not r.p&Z:
                                                                    pass
                                                                else:
                                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                    pass
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                self._a(m[NEW_BUTTONS])
                                                r.a=self._shift(r.a,True,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._mark(0xA784)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    self._y(m[SELECTED_SLOT])
                                                    self._a(m[(0x0600+r.y)&65535])
                                                    m[0x0000]=r.a
                                                    self._a(m[(0x0614+r.y)&65535])
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    self._compare(r.a,0x14)
                                                    self._mark(0xA796)
                                                    if r.p&C:
                                                        pass
                                                    else:
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xA79A)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._flag(C,False)
                                                            self._add(0x01)
                                                            pass
                                                        m[0x0001]=r.a
                                                        if not (yield from self._local_call(self.local_d6b6,0xA7A1,0xA7A4)):return
                                                        self._a(r.y)
                                                        self._mark(0xA7A5)
                                                        if not r.p&N:
                                                            pass
                                                        else:
                                                            self._y(m[SELECTED_SLOT])
                                                            self._a(m[(0x0600+r.y)&65535])
                                                            m[0x0010]=r.a
                                                            self._a(m[(0x0614+r.y)&65535])
                                                            self._flag(C,False)
                                                            self._add(0x01)
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xA7B7)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                self._flag(C,False)
                                                                self._add(0x01)
                                                                pass
                                                            m[0x0011]=r.a
                                                            if not (yield from self._local_call(self.terrain_at_position,0xA7BE,0xA7C1)):return
                                                            if not (yield from self._local_call(self.local_a7e7,0xA7C1,0xA7C4)):return
                                                            self._mark(0xA7C4)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                m[AP]=r.a
                                                                self._a(r.x)
                                                                self._push(r.a)
                                                                self._a(0x00)
                                                                m[0x0012]=r.a
                                                                if not (yield from self._local_call(self.map_refresh,0xA7CF,0xA7D2)):return
                                                                self._a(self._pop())
                                                                if not (yield from self._local_call(self.local_a85b,0xA7D3,0xA7D6)):return
                                                                self._x(m[SELECTED_SLOT])
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                self._a(m[(0x0614+r.x)&65535])
                                                                self._compare(r.a,0x0F)
                                                                self._mark(0xA7E1)
                                                                if not r.p&Z:
                                                                    pass
                                                                else:
                                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                    pass
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                self._mark(0xA7E6)
                                                self._rts();return
                                            else:
                                                m[AP]=r.a
                                                self._a(r.x)
                                                self._push(r.a)
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xA70D,0xA710)):return
                                                self._a(self._pop())
                                                if not (yield from self._local_call(self.local_a85b,0xA711,0xA714)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                                self._mark(0xA71A)
                                                self._rts();return
                            else:
                                m[AP]=r.a
                                self._a(r.x)
                                self._push(r.a)
                                self._a(0x00)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xA6C0,0xA6C3)):return
                                self._a(self._pop())
                                if not (yield from self._local_call(self.local_a85b,0xA6C4,0xA6C7)):return
                                self._x(m[SELECTED_SLOT])
                                m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]-1)
                                self._mark(0xA6CD)
                                self._rts();return
            else:
                self._a(0x00)
                m[0x0012]=r.a
                if not (yield from self._local_call(self.map_refresh,0xA659,0xA65C)):return
                self._y(m[ACTOR_SLOT])
                self._x(m[SELECTED_SLOT])
                self._a(m[(0x053D+r.y)&65535])
                m[(0x0600+r.x)&65535]=r.a
                self._a(m[(0x053E+r.y)&65535])
                m[(0x0614+r.x)&65535]=r.a
                self._a(m[(0x053F+r.y)&65535])
                self._flag(C,False)
                self._add(m[AP])
                m[AP]=r.a
                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]-1)
                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]-1)
                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]-1)
                self._mark(0xA681)
                self._rts();return

    def local_a7e7(self):
        """$A7E7: local a7e7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7E7)
        self._push(r.a)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xA7EE,0xF2D7,0xA7F1,"call",None)
        if r.pc!=0xA7F1:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x03)
        m[0x0000]=r.a
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0000])
        self._y(r.a)
        self._x(m[SELECTED_SLOT])
        self._a(m[(0x063C+r.x)&65535])
        self._compare(r.a,0x06)
        self._mark(0xA809)
        if not r.p&C:
            self._a(m[(0xA83F+r.y)&65535])
            self._x(r.a)
            self._a(m[AP])
            self._flag(C,True)
            self._add(m[(0xA83F+r.y)&65535],subtract=True)
            self._mark(0xA822)
            self._rts();return
        else:
            self._a(m[(0xA823+r.y)&65535])
            self._x(r.a)
            self._a(m[AP])
            self._flag(C,True)
            self._add(m[(0xA823+r.y)&65535],subtract=True)
            self._mark(0xA816)
            self._rts();return

    def local_a85b(self):
        """$A85B: local a85b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA85B)
        self._push(r.a)
        self._y(m[ACTOR_SLOT])
        self._x(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.x)&65535])
        m[(0x0540+r.y)&65535]=r.a
        self._a(m[(0x0614+r.x)&65535])
        m[(0x0541+r.y)&65535]=r.a
        self._a(self._pop())
        m[(0x0542+r.y)&65535]=r.a
        m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
        m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
        m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
        self._mark(0xA87B)
        self._rts();return

    def tactics(self):
        """$A87C: tactics; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA87C)
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.local_dc36,0xA87F,0xA882)):return
        self._a(m[PHASE])
        self._mark(0xA885)
        index=self._dispatch(0xA885,(43166, 43201, 43224, 43287, 43485, 43566, 43628, 43687, 43818, 43858, 43920))
        return (yield from (self.initialize_tactic_list,self.build_tactic_list,self.request_tactic_menu,self.select_tactic,self.choose_tactic_target,self.confirm_tactic,self.wait_animation_apply_tactic,self.scan_tactic_result,self.acknowledge_tactic_result,self.acknowledge_upgrade_notice,self.acknowledge_invalid_target,)[index]())

    def initialize_tactic_list(self):
        """$A89E: initialize tactic list; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA89E)
        self._a(0xF3)
        m[0x0310]=r.a
        self._a(0x00)
        m[0x0300]=r.a
        m[0x050B]=r.a
        self._y(0x03)
        while True:  # natural loop $A8AD
            self._a(m[(0x6F3F+r.y)&65535])
            m[(0x046C+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xA8B4)
            if not r.p&N:
                continue
            else:
                pass
            m[PHASE]=self._nz(m[PHASE]+1)
            self._y(0x28)
            yield from self._external(0xA8BB,0xEE07,0xA8C0,"far_call",40987)
            if r.pc!=0xA8C0:return  # preserve nonlocal stack return
            self._mark(0xA8C0)
            self._rts();return

    def build_tactic_list(self):
        """$A8C1: build tactic list; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8C1)
        if not (yield from self._local_call(self.text_readiness,0xA8C1,0xA8C4)):return
        self._mark(0xA8C4)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.local_abd9,0xA8C6,0xA8C9)):return
            self._a(m[0x050B])
            m[0x050B]=self._nz(m[0x050B]+1)
            self._compare(r.a,m[0x0542])
            self._mark(0xA8D2)
            if not r.p&C:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xA8D7)
        self._rts();return

    def request_tactic_menu(self):
        """$A8D8: request tactic menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8D8)
        self._a(0xC7)
        yield from self._external(0xA8DA,0xF283,0xA8DD,"call",None)
        if r.pc!=0xA8DD:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0xE1)
        m[0x00E7]=r.a
        self._a(0xE1)
        m[0x00E9]=r.a
        self._a(0x02)
        m[0x00B4]=r.a
        self._a(0x16)
        m[0x00B3]=r.a
        self._a(0x17)
        m[0x00B5]=r.a
        self._a(0x5B)
        m[0x00B2]=r.a
        self._a(m[0x008E])
        m[0x0540]=r.a
        self._a(m[0x0090])
        m[0x0541]=r.a
        self._a(0x00)
        m[0x008E]=r.a
        self._a(0x50)
        m[0x0090]=r.a
        self._a(0x01)
        m[0x008F]=r.a
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xA916)
        self._rts();return

    def select_tactic(self):
        """$A917: select tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA917)
        self._a(0x5B)
        m[0x00B2]=r.a
        self._a(m[0x0542])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBA9F+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xBAA0+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA92E,0xED1E,0xA931,"call",None)
        if r.pc!=0xA931:return  # preserve nonlocal stack return
        self._a(0xA4)
        m[0x0010]=r.a
        self._a(0xAB)
        m[0x0011]=r.a
        self._a(0xC4)
        m[0x0000]=r.a
        self._a(0xAB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA943,0xEDF5,0xA946,"call",None)
        if r.pc!=0xA946:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xA946,0xA949)):return
        self._mark(0xA949)
        if not r.p&C:
            self._mark(0xA99F)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xA94F)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x02)
                self._mark(0xA96C)
                if r.p&Z:
                    self._mark(0xA99F)
                    self._rts();return
                else:
                    self._a(0xE0)
                    m[0x00E7]=r.a
                    self._a(0xE0)
                    m[0x00E9]=r.a
                    self._a(0x89)
                    m[0x00B3]=r.a
                    self._a(0x8A)
                    m[0x00B4]=r.a
                    self._a(0x88)
                    m[0x00B5]=r.a
                    m[0x00B2]=r.a
                    self._a(m[0x0540])
                    m[0x008E]=r.a
                    self._a(m[0x0541])
                    m[0x0090]=r.a
                    self._a(0x00)
                    m[0x008F]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[STATE]=r.a
                    return (yield from self.return_command_cursor())
            else:
                self._y(m[0x0012])
                self._a(m[(0x0580+r.y)&65535])
                m[TACTIC]=r.a
                self._a(m[AP])
                self._y(m[0x0012])
                self._compare(r.a,m[(0xABC9+r.y)&65535])
                self._mark(0xA961)
                if not r.p&C:
                    self._a(0x00)
                    self._a(m[NEW_BUTTONS])
                    self._a(r.a & 0x02)
                    self._mark(0xA96C)
                    if r.p&Z:
                        self._mark(0xA99F)
                        self._rts();return
                    else:
                        self._a(0xE0)
                        m[0x00E7]=r.a
                        self._a(0xE0)
                        m[0x00E9]=r.a
                        self._a(0x89)
                        m[0x00B3]=r.a
                        self._a(0x8A)
                        m[0x00B4]=r.a
                        self._a(0x88)
                        m[0x00B5]=r.a
                        m[0x00B2]=r.a
                        self._a(m[0x0540])
                        m[0x008E]=r.a
                        self._a(m[0x0541])
                        m[0x0090]=r.a
                        self._a(0x00)
                        m[0x008F]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0x00)
                        m[STATE]=r.a
                        return (yield from self.return_command_cursor())
                else:
                    self._a(0x89)
                    m[0x00B3]=r.a
                    self._a(0x8A)
                    m[0x00B4]=r.a
                    self._a(0x88)
                    m[0x00B5]=r.a
                    m[0x00B2]=r.a
                    self._a(m[0x0540])
                    m[0x008E]=r.a
                    self._a(m[0x0541])
                    m[0x0090]=r.a
                    self._a(0x00)
                    m[0x008F]=r.a
                    self._a(0xE0)
                    m[0x00E7]=r.a
                    self._a(0xE0)
                    m[0x00E9]=r.a
                    self._a(m[TACTIC])
                    self._compare(r.a,0x0B)
                    self._mark(0xA9C9)
                    if not r.p&Z:
                        self._a(0xF4)
                        yield from self._external(0xA9D6,0xF283,0xA9D9,"call",None)
                        if r.pc!=0xA9D9:return  # preserve nonlocal stack return
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._mark(0xA9DC)
                        self._rts();return
                    else:
                        self._y(m[ACTOR_SLOT])
                        m[PHASE]=self._nz(m[PHASE]+1)
                        m[SELECTED_SLOT]=r.y
                        if not (yield from self._local_call(self.local_b860,0xAA06,0xAA09)):return
                        self._compare(r.a,0x06)
                        self._mark(0xAA0B)
                        if r.p&C:
                            self._a(0x4C)
                            self._mark(0xAA2B)
                            yield from self._external(0xAA2B,0xF283,None,"tail")
                            return
                        else:
                            if not (yield from self._local_call(self.local_ad80,0xAA0D,0xAA10)):return
                            self._mark(0xAA10)
                            if r.p&C:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(m[TACTIC])
                                self._a(r.a & 0x0F)
                                self._y(r.a)
                                self._a(m[(0xAD70+r.y)&65535])
                                yield from self._external(0xAD6C,0xF283,0xAD6F,"call",None)
                                if r.pc!=0xAD6F:return  # preserve nonlocal stack return
                                self._mark(0xAD6F)
                                self._rts();return
                            else:
                                self._a(0x0A)
                                m[PHASE]=r.a
                                self._a(0xF7)
                                yield from self._external(0xAA19,0xF283,0xAA1C,"call",None)
                                if r.pc!=0xAA1C:return  # preserve nonlocal stack return
                                self._mark(0xAA1C)
                                self._rts();return

    def choose_tactic_target(self):
        """$A9DD: choose tactic target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9DD)
        if not (yield from self._local_call(self.direction_repeat,0xA9DD,0xA9E0)):return
        if not (yield from self._local_call(self.cursor_input,0xA9E0,0xA9E3)):return
        if not (yield from self._local_call(self.battle_cursor,0xA9E3,0xA9E6)):return
        if not (yield from self._local_call(self.text_readiness,0xA9E6,0xA9E9)):return
        self._mark(0xA9E9)
        if not r.p&C:
            self._mark(0xAA28)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA9EE)
            if r.p&C:
                if not (yield from self._local_call(self.unit_at_cursor,0xA9F6,0xA9F9)):return
                self._a(r.y)
                self._mark(0xA9FA)
                if r.p&N:
                    self._mark(0xAA28)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xA9FC,0xA9FF)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xAA01)
                    if not r.p&Z:
                        self._mark(0xAA28)
                        self._rts();return
                    else:
                        m[SELECTED_SLOT]=r.y
                        if not (yield from self._local_call(self.local_b860,0xAA06,0xAA09)):return
                        self._compare(r.a,0x06)
                        self._mark(0xAA0B)
                        if r.p&C:
                            self._a(0x4C)
                            self._mark(0xAA2B)
                            yield from self._external(0xAA2B,0xF283,None,"tail")
                            return
                        else:
                            if not (yield from self._local_call(self.local_ad80,0xAA0D,0xAA10)):return
                            self._mark(0xAA10)
                            if r.p&C:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(m[TACTIC])
                                self._a(r.a & 0x0F)
                                self._y(r.a)
                                self._a(m[(0xAD70+r.y)&65535])
                                yield from self._external(0xAD6C,0xF283,0xAD6F,"call",None)
                                if r.pc!=0xAD6F:return  # preserve nonlocal stack return
                                self._mark(0xAD6F)
                                self._rts();return
                            else:
                                self._a(0x0A)
                                m[PHASE]=r.a
                                self._a(0xF7)
                                yield from self._external(0xAA19,0xF283,0xAA1C,"call",None)
                                if r.pc!=0xAA1C:return  # preserve nonlocal stack return
                                self._mark(0xAA1C)
                                self._rts();return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA9F1)
                if r.p&C:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                else:
                    pass
                self._mark(0xAA28)
                self._rts();return

    def confirm_tactic(self):
        """$AA2E: confirm tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA2E)
        if not (yield from self._local_call(self.dialog_highlight,0xAA2E,0xAA31)):return
        if not (yield from self._local_call(self.battle_cursor,0xAA31,0xAA34)):return
        if not (yield from self._local_call(self.text_readiness,0xAA34,0xAA37)):return
        self._mark(0xAA37)
        if not r.p&C:
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xAA3D)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x89)
                m[0x00C3]=r.a
                self._a(0x8A)
                m[0x00C4]=r.a
                self._a(0x88)
                m[0x00C5]=r.a
                m[0x00C2]=r.a
                self._y(m[SELECTED_SLOT])
                self._a(0x00)
                m[(0x0650+r.y)&65535]=r.a
                self._a(m[TACTIC])
                self._flag(C,False)
                self._add(0x01)
                m[ANIMATION]=r.a
                self._a(0x05)
                m[0x0310]=r.a
                self._a(0x00)
                m[0x0300]=r.a
                pass
            pass
        self._mark(0xAA6B)
        self._rts();return

    def wait_animation_apply_tactic(self):
        """$AA6C: wait animation apply tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA6C)
        self._a(m[ANIMATION])
        self._mark(0xAA6F)
        if not r.p&Z:
            pass
        else:
            self._y(m[ACTOR_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            yield from self._external(0xAA77,0xF2D7,0xAA7A,"call",None)
            if r.pc!=0xAA7A:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0xF0)
            m[0x052C]=r.a
            self._y(0x01)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x052E]=r.a
            self._y(m[TACTIC])
            self._a(m[(0xABC9+r.y)&65535])
            m[0x0000]=r.a
            self._a(m[AP])
            self._flag(C,True)
            self._add(m[0x0000],subtract=True)
            m[AP]=r.a
            if not (yield from self._local_call(self.apply_tactic,0xAA9B,0xAA9E)):return
            if not (yield from self._local_call(self.refresh_hundred_troops,0xAA9E,0xAAA1)):return
            self._a(0x00)
            m[0x050B]=r.a
            pass
        self._mark(0xAAA6)
        self._rts();return

    def scan_tactic_result(self):
        """$AAA7: scan tactic result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAAA7)
        self._a(m[PPU_JOBS])
        self._mark(0xAAAA)
        if not r.p&Z:
            self._mark(0xAAE2)
            self._rts();return
        else:
            self._a(m[0x050B])
            m[SELECTED_SLOT]=r.a
            self._a(0x01)
            m[0x0012]=r.a
            if not (yield from self._local_call(self.map_refresh,0xAAB6,0xAAB9)):return
            m[0x050B]=self._nz(m[0x050B]+1)
            self._a(m[0x050B])
            self._compare(r.a,0x14)
            self._mark(0xAAC1)
            if not r.p&C:
                self._mark(0xAAE2)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[TACTIC_FAILED])
                self._mark(0xAAC9)
                if r.p&Z:
                    self._a(0x03)
                    m[0x00A4]=r.a
                    self._a(m[TACTIC])
                    self._a(r.a & 0x0F)
                    self._y(r.a)
                    self._compare(r.y,0x01)
                    self._mark(0xAAF0)
                    if r.p&Z:
                        self._a(m[0x0432])
                        self._compare(r.a,0xFF)
                        self._mark(0xAB07)
                        if r.p&Z:
                            self._a(m[(0xAB1A+r.y)&65535])
                            yield from self._external(0xAB14,0xF283,0xAB17,"call",None)
                            if r.pc!=0xAB17:return  # preserve nonlocal stack return
                            self._a(m[ACTOR_SLOT])
                            m[SELECTED_SLOT]=r.a
                            self._y(0x3D)
                            yield from self._external(0xAADD,0xEE07,0xAAE2,"far_call",40999)
                            if r.pc!=0xAAE2:return  # preserve nonlocal stack return
                            self._mark(0xAAE2)
                            self._rts();return
                        else:
                            m[0x042C]=r.a
                            self._a(0x4E)
                            self._mark(0xAB0E)
                            yield from self._external(0xAB0E,0xF293,None,"tail")
                            return
                    else:
                        self._compare(r.y,0x09)
                        self._mark(0xAAF4)
                        if not r.p&Z:
                            self._a(m[(0xAB1A+r.y)&65535])
                            yield from self._external(0xAB14,0xF283,0xAB17,"call",None)
                            if r.pc!=0xAB17:return  # preserve nonlocal stack return
                            self._a(m[ACTOR_SLOT])
                            m[SELECTED_SLOT]=r.a
                            self._y(0x3D)
                            yield from self._external(0xAADD,0xEE07,0xAAE2,"far_call",40999)
                            if r.pc!=0xAAE2:return  # preserve nonlocal stack return
                            self._mark(0xAAE2)
                            self._rts();return
                        else:
                            self._a(m[0x042C])
                            self._mark(0xAAF9)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[0x042D])
                                self._mark(0xAAFE)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._y(0x01)
                                    pass
                                pass
                            self._a(m[0x0432])
                            self._compare(r.a,0xFF)
                            self._mark(0xAB07)
                            if r.p&Z:
                                self._a(m[(0xAB1A+r.y)&65535])
                                yield from self._external(0xAB14,0xF283,0xAB17,"call",None)
                                if r.pc!=0xAB17:return  # preserve nonlocal stack return
                                self._a(m[ACTOR_SLOT])
                                m[SELECTED_SLOT]=r.a
                                self._y(0x3D)
                                yield from self._external(0xAADD,0xEE07,0xAAE2,"far_call",40999)
                                if r.pc!=0xAAE2:return  # preserve nonlocal stack return
                                self._mark(0xAAE2)
                                self._rts();return
                            else:
                                m[0x042C]=r.a
                                self._a(0x4E)
                                self._mark(0xAB0E)
                                yield from self._external(0xAB0E,0xF293,None,"tail")
                                return
                else:
                    self._a(0x04)
                    m[0x00A4]=r.a
                    self._a(0x73)
                    yield from self._external(0xAAD2,0xF283,0xAAD5,"call",None)
                    if r.pc!=0xAAD5:return  # preserve nonlocal stack return
                    self._a(m[ACTOR_SLOT])
                    m[SELECTED_SLOT]=r.a
                    self._y(0x3D)
                    yield from self._external(0xAADD,0xEE07,0xAAE2,"far_call",40999)
                    if r.pc!=0xAAE2:return  # preserve nonlocal stack return
                    self._mark(0xAAE2)
                    self._rts();return

    def acknowledge_tactic_result(self):
        """$AB2A: acknowledge tactic result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB2A)
        if not (yield from self._local_call(self.text_readiness,0xAB2A,0xAB2D)):return
        self._mark(0xAB2D)
        if not r.p&C:
            self._mark(0xAB51)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xAB2F,0xAB32)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xAB36)
            if r.p&Z:
                self._mark(0xAB51)
                self._rts();return
            else:
                self._y(m[ACTOR_SLOT])
                self._a(m[(0x0664+r.y)&65535])
                m[0x042C]=r.a
                if not (yield from self._local_call(self.local_dee9,0xAB41,0xAB44)):return
                self._mark(0xAB44)
                if not r.p&C:
                    self._y(0x03)
                    while True:  # natural loop $AB71
                        self._a(m[(0x046C+r.y)&65535])
                        m[(0x6F3F+r.y)&65535]=r.a
                        self._y(r.y-1)
                        self._mark(0xAB78)
                        if not r.p&N:
                            continue
                        else:
                            pass
                        self._a(0x00)
                        m[PHASE]=r.a
                        m[STATE]=r.a
                        return (yield from self.return_command_cursor())
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    yield from self._external(0xAB49,0xE57F,0xAB4C,"call",None)
                    if r.pc!=0xAB4C:return  # preserve nonlocal stack return
                    self._a(0x7B)
                    yield from self._external(0xAB4E,0xE68B,0xAB51,"call",None)
                    if r.pc!=0xAB51:return  # preserve nonlocal stack return
                    self._mark(0xAB51)
                    self._rts();return

    def acknowledge_upgrade_notice(self):
        """$AB52: acknowledge upgrade notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB52)
        if not (yield from self._local_call(self.text_readiness,0xAB52,0xAB55)):return
        self._mark(0xAB55)
        if not r.p&C:
            self._mark(0xAB85)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xAB57,0xAB5A)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xAB5E)
            if r.p&Z:
                self._mark(0xAB85)
                self._rts();return
            else:
                self._a(m[0x042D])
                self._compare(r.a,0xFF)
                self._mark(0xAB65)
                if not r.p&Z:
                    self._a(0xFF)
                    m[0x042D]=r.a
                    self._a(0x4B)
                    self._mark(0xAB8D)
                    yield from self._external(0xAB8D,0xF293,None,"tail")
                    return
                else:
                    yield from self._external(0xAB67,0xE57F,0xAB6A,"call",None)
                    if r.pc!=0xAB6A:return  # preserve nonlocal stack return
                    self._a(0x1D)
                    yield from self._external(0xAB6C,0xE673,0xAB6F,"call",None)
                    if r.pc!=0xAB6F:return  # preserve nonlocal stack return
                    self._y(0x03)
                    while True:  # natural loop $AB71
                        self._a(m[(0x046C+r.y)&65535])
                        m[(0x6F3F+r.y)&65535]=r.a
                        self._y(r.y-1)
                        self._mark(0xAB78)
                        if not r.p&N:
                            continue
                        else:
                            pass
                        self._a(0x00)
                        m[PHASE]=r.a
                        m[STATE]=r.a
                        return (yield from self.return_command_cursor())

    def acknowledge_invalid_target(self):
        """$AB90: acknowledge invalid target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB90)
        if not (yield from self._local_call(self.text_readiness,0xAB90,0xAB93)):return
        self._mark(0xAB93)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xAB95,0xAB98)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xAB9C)
            if r.p&Z:
                pass
            else:
                self._a(0x00)
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xABA3)
        self._rts();return

    def local_abd9(self):
        """$ABD9: local abd9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABD9)
        self._y(m[0x050B])
        self._a(m[(0x0580+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xAC91+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xAC92+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[0x050B])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0002]=r.a
        self._x(0x00)
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[(0x0380+r.x)&65535]=r.a
        m[0x0003]=r.a
        self._x(r.x+1)
        self._y(m[0x0002])
        self._a(m[(0xAC52+r.y)&65535])
        m[(0x0380+r.x)&65535]=r.a
        self._x(r.x+1)
        self._a(m[(0xAC51+r.y)&65535])
        m[(0x0380+r.x)&65535]=r.a
        self._x(r.x+1)
        self._y(0x01)
        while True:  # natural loop $AC10
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0380+r.x)&65535]=r.a
            self._x(r.x+1)
            self._y(r.y+1)
            m[0x0003]=self._nz(m[0x0003]-1)
            self._mark(0xAC19)
            if not r.p&Z:
                continue
            else:
                pass
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0380+r.x)&65535]=r.a
            m[0x0003]=r.a
            self._y(r.y+1)
            self._a(r.y)
            self._push(r.a)
            self._x(r.x+1)
            self._y(m[0x0002])
            self._a(m[(0xAC54+r.y)&65535])
            m[(0x0380+r.x)&65535]=r.a
            self._x(r.x+1)
            self._a(m[(0xAC53+r.y)&65535])
            m[(0x0380+r.x)&65535]=r.a
            self._x(r.x+1)
            self._a(self._pop())
            self._y(r.a)
            while True:  # natural loop $AC38
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[(0x0380+r.x)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                m[0x0003]=self._nz(m[0x0003]-1)
                self._mark(0xAC41)
                if not r.p&Z:
                    continue
                else:
                    pass
                self._a(0xFF)
                m[(0x0380+r.x)&65535]=r.a
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xAC50)
                self._rts();return

    def local_ad80(self):
        """$AD80: local ad80; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD80)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        if not (yield from self._local_call(self.terrain_at_position,0xAD8D,0xAD90)):return
        m[0x000A]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        if not (yield from self._local_call(self.terrain_at_position,0xAD9F,0xADA2)):return
        m[0x000B]=r.a
        self._a(m[TACTIC])
        self._a(r.a & 0x0F)
        self._mark(0xADA9)
        index=self._dispatch(0xADA9,(44492, 44504, 44504, 44504, 44516, 44526, 44539, 44648, 44740, 44750, 44810, 44915, 44810, 44961, 45011, 45085))
        return (yield from (self.local_adcc,self.local_add8,self.local_add8,self.local_add8,self.local_ade4,self.local_adee,self.local_adfb,self.local_ae68,self.local_aec4,self.local_aece,self.local_af0a,self.local_af73,self.local_af0a,self.local_afa1,self.local_afd3,self.local_b01d,)[index]())

    def local_adcc(self):
        """$ADCC: local adcc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADCC)
        self._a(m[0x000A])
        self._mark(0xADCE)
        if r.p&Z:
            self._flag(C,True)
            self._mark(0xADD7)
            self._rts();return
        else:
            self._compare(r.a,0x02)
            self._mark(0xADD2)
            if r.p&Z:
                self._flag(C,True)
                self._mark(0xADD7)
                self._rts();return
            else:
                self._flag(C,False)
                self._mark(0xADD5)
                self._rts();return

    def local_add8(self):
        """$ADD8: local add8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADD8)
        self._a(m[0x000A])
        self._mark(0xADDA)
        if r.p&Z:
            self._flag(C,True)
            self._mark(0xADE3)
            self._rts();return
        else:
            self._compare(r.a,0x04)
            self._mark(0xADDE)
            if r.p&Z:
                self._flag(C,True)
                self._mark(0xADE3)
                self._rts();return
            else:
                self._flag(C,False)
                self._mark(0xADE1)
                self._rts();return

    def local_ade4(self):
        """$ADE4: local ade4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADE4)
        self._a(m[0x000A])
        self._compare(r.a,0x03)
        self._mark(0xADE8)
        if r.p&Z:
            self._flag(C,True)
            self._mark(0xADED)
            self._rts();return
        else:
            self._flag(C,False)
            self._mark(0xADEB)
            self._rts();return

    def local_adee(self):
        """$ADEE: local adee; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADEE)
        self._y(m[SELECTED_SLOT])
        self._mark(0xADF1)
        if r.p&Z:
            self._flag(C,True)
            self._mark(0xADFA)
            self._rts();return
        else:
            self._compare(r.y,0x0A)
            self._mark(0xADF5)
            if r.p&Z:
                self._flag(C,True)
                self._mark(0xADFA)
                self._rts();return
            else:
                self._flag(C,False)
                self._mark(0xADF8)
                self._rts();return

    def local_adfb(self):
        """$ADFB: local adfb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADFB)
        self._y(m[0x000A])
        self._compare(r.y,0x05)
        self._mark(0xADFF)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xAE2A)
            self._rts();return
        else:
            if not (yield from self._local_call(self.local_ae2d,0xAE01,0xAE04)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_ae42,0xAE06,0xAE09)):return
            self._mark(0xAE09)
            if r.p&C:
                self._flag(C,True)
                self._mark(0xAE2C)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAE0B,0xAE0E)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_ae42,0xAE10,0xAE13)):return
                self._mark(0xAE13)
                if r.p&C:
                    self._flag(C,True)
                    self._mark(0xAE2C)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAE15,0xAE18)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_ae42,0xAE1A,0xAE1D)):return
                    self._mark(0xAE1D)
                    if r.p&C:
                        self._flag(C,True)
                        self._mark(0xAE2C)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAE1F,0xAE22)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_ae42,0xAE24,0xAE27)):return
                        self._mark(0xAE27)
                        if r.p&C:
                            self._flag(C,True)
                            self._mark(0xAE2C)
                            self._rts();return
                        else:
                            self._flag(C,False)
                            self._mark(0xAE2A)
                            self._rts();return

    def local_ae2d(self):
        """$AE2D: local ae2d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE2D)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0x0614+r.y)&65535])
        self._compare(r.a,0x10)
        self._mark(0xAE3A)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            pass
        m[0x0001]=r.a
        self._mark(0xAE41)
        self._rts();return

    def local_ae42(self):
        """$AE42: local ae42; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE42)
        self._a(m[0x0000])
        self._compare(r.a,0x20)
        self._mark(0xAE46)
        if r.p&C:
            self._flag(C,False)
            self._mark(0xAE2A)
            self._rts();return
        else:
            self._a(m[0x0001])
            self._compare(r.a,0x14)
            self._mark(0xAE4C)
            if r.p&C:
                self._flag(C,False)
                self._mark(0xAE2A)
                self._rts();return
            else:
                self._y(m[ACTOR_SLOT])
                self._a(m[(0x0600+r.y)&65535])
                self._compare(r.a,m[0x0000])
                self._mark(0xAE56)
                if not r.p&Z:
                    self._flag(C,False)
                    self._mark(0xAE2A)
                    self._rts();return
                else:
                    self._a(m[(0x0614+r.y)&65535])
                    self._compare(r.a,0x10)
                    self._mark(0xAE5D)
                    if not r.p&C:
                        pass
                    else:
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        pass
                    self._compare(r.a,m[0x0001])
                    self._mark(0xAE64)
                    if not r.p&Z:
                        self._flag(C,False)
                        self._mark(0xAE2A)
                        self._rts();return
                    else:
                        self._flag(C,True)
                        self._mark(0xAE67)
                        self._rts();return

    def local_ae68(self):
        """$AE68: local ae68; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE68)
        self._y(m[0x000A])
        self._mark(0xAE6A)
        if r.p&Z:
            if not (yield from self._local_call(self.local_ae2d,0xAE70,0xAE73)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_aea4,0xAE75,0xAE78)):return
            self._compare(r.a,0xFF)
            self._mark(0xAE7A)
            if r.p&Z:
                self._flag(C,True)
                self._mark(0xAEA1)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAE7C,0xAE7F)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_aea4,0xAE81,0xAE84)):return
                self._compare(r.a,0xFF)
                self._mark(0xAE86)
                if r.p&Z:
                    self._flag(C,True)
                    self._mark(0xAEA1)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAE88,0xAE8B)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_aea4,0xAE8D,0xAE90)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xAE92)
                    if r.p&Z:
                        self._flag(C,True)
                        self._mark(0xAEA1)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAE94,0xAE97)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_aea4,0xAE99,0xAE9C)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xAE9E)
                        if not r.p&Z:
                            self._flag(C,False)
                            self._mark(0xAEA3)
                            self._rts();return
                        else:
                            self._flag(C,True)
                            self._mark(0xAEA1)
                            self._rts();return
        else:
            self._compare(r.y,0x04)
            self._mark(0xAE6E)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xAEA3)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAE70,0xAE73)):return
                m[0x0000]=self._nz(m[0x0000]+1)
                if not (yield from self._local_call(self.local_aea4,0xAE75,0xAE78)):return
                self._compare(r.a,0xFF)
                self._mark(0xAE7A)
                if r.p&Z:
                    self._flag(C,True)
                    self._mark(0xAEA1)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAE7C,0xAE7F)):return
                    m[0x0000]=self._nz(m[0x0000]-1)
                    if not (yield from self._local_call(self.local_aea4,0xAE81,0xAE84)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xAE86)
                    if r.p&Z:
                        self._flag(C,True)
                        self._mark(0xAEA1)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAE88,0xAE8B)):return
                        m[0x0001]=self._nz(m[0x0001]+1)
                        if not (yield from self._local_call(self.local_aea4,0xAE8D,0xAE90)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xAE92)
                        if r.p&Z:
                            self._flag(C,True)
                            self._mark(0xAEA1)
                            self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_ae2d,0xAE94,0xAE97)):return
                            m[0x0001]=self._nz(m[0x0001]-1)
                            if not (yield from self._local_call(self.local_aea4,0xAE99,0xAE9C)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xAE9E)
                            if not r.p&Z:
                                self._flag(C,False)
                                self._mark(0xAEA3)
                                self._rts();return
                            else:
                                self._flag(C,True)
                                self._mark(0xAEA1)
                                self._rts();return

    def local_aea4(self):
        """$AEA4: local aea4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAEA4)
        self._a(m[0x0000])
        self._compare(r.a,0x20)
        self._mark(0xAEA8)
        if r.p&C:
            self._a(0x00)
            self._mark(0xAEC3)
            self._rts();return
        else:
            self._a(m[0x0001])
            self._compare(r.a,0x14)
            self._mark(0xAEAE)
            if r.p&C:
                self._a(0x00)
                self._mark(0xAEC3)
                self._rts();return
            else:
                self._compare(r.a,0x0F)
                self._mark(0xAEB2)
                if not r.p&Z:
                    pass
                else:
                    m[0x0001]=self._nz(m[0x0001]+1)
                    pass
                if not (yield from self._local_call(self.local_d6b6,0xAEB7,0xAEBA)):return
                self._a(r.y)
                self._mark(0xAEBB)
                if r.p&N:
                    self._a(0x00)
                    self._mark(0xAEC3)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xAEBD,0xAEC0)):return
                    self._mark(0xAEC0)
                    self._rts();return

    def local_aec4(self):
        """$AEC4: local aec4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAEC4)
        self._a(m[0x000A])
        self._compare(r.a,0x05)
        self._mark(0xAEC8)
        if not r.p&Z:
            self._flag(C,True)
            self._mark(0xAECD)
            self._rts();return
        else:
            self._flag(C,False)
            self._mark(0xAECB)
            self._rts();return

    def local_aece(self):
        """$AECE: local aece; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAECE)
        self._a(m[0x000B])
        self._compare(r.a,0x04)
        self._mark(0xAED2)
        if r.p&Z:
            if not (yield from self._local_call(self.local_ae2d,0xAED8,0xAEDB)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_ae42,0xAEDD,0xAEE0)):return
            self._mark(0xAEE0)
            if r.p&C:
                self._a(m[0x000A])
                self._compare(r.a,0x05)
                self._mark(0xAF04)
                if r.p&Z:
                    self._flag(C,False)
                    self._mark(0xAF09)
                    self._rts();return
                else:
                    self._flag(C,True)
                    self._mark(0xAF07)
                    self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAEE2,0xAEE5)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_ae42,0xAEE7,0xAEEA)):return
                self._mark(0xAEEA)
                if r.p&C:
                    self._a(m[0x000A])
                    self._compare(r.a,0x05)
                    self._mark(0xAF04)
                    if r.p&Z:
                        self._flag(C,False)
                        self._mark(0xAF09)
                        self._rts();return
                    else:
                        self._flag(C,True)
                        self._mark(0xAF07)
                        self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAEEC,0xAEEF)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_ae42,0xAEF1,0xAEF4)):return
                    self._mark(0xAEF4)
                    if r.p&C:
                        self._a(m[0x000A])
                        self._compare(r.a,0x05)
                        self._mark(0xAF04)
                        if r.p&Z:
                            self._flag(C,False)
                            self._mark(0xAF09)
                            self._rts();return
                        else:
                            self._flag(C,True)
                            self._mark(0xAF07)
                            self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAEF6,0xAEF9)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_ae42,0xAEFB,0xAEFE)):return
                        self._mark(0xAEFE)
                        if not r.p&C:
                            self._flag(C,False)
                            self._mark(0xAF09)
                            self._rts();return
                        else:
                            self._a(m[0x000A])
                            self._compare(r.a,0x05)
                            self._mark(0xAF04)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xAF09)
                                self._rts();return
                            else:
                                self._flag(C,True)
                                self._mark(0xAF07)
                                self._rts();return
        else:
            self._compare(r.a,0x05)
            self._mark(0xAED6)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xAF09)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAED8,0xAEDB)):return
                m[0x0000]=self._nz(m[0x0000]+1)
                if not (yield from self._local_call(self.local_ae42,0xAEDD,0xAEE0)):return
                self._mark(0xAEE0)
                if r.p&C:
                    self._a(m[0x000A])
                    self._compare(r.a,0x05)
                    self._mark(0xAF04)
                    if r.p&Z:
                        self._flag(C,False)
                        self._mark(0xAF09)
                        self._rts();return
                    else:
                        self._flag(C,True)
                        self._mark(0xAF07)
                        self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAEE2,0xAEE5)):return
                    m[0x0000]=self._nz(m[0x0000]-1)
                    if not (yield from self._local_call(self.local_ae42,0xAEE7,0xAEEA)):return
                    self._mark(0xAEEA)
                    if r.p&C:
                        self._a(m[0x000A])
                        self._compare(r.a,0x05)
                        self._mark(0xAF04)
                        if r.p&Z:
                            self._flag(C,False)
                            self._mark(0xAF09)
                            self._rts();return
                        else:
                            self._flag(C,True)
                            self._mark(0xAF07)
                            self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAEEC,0xAEEF)):return
                        m[0x0001]=self._nz(m[0x0001]+1)
                        if not (yield from self._local_call(self.local_ae42,0xAEF1,0xAEF4)):return
                        self._mark(0xAEF4)
                        if r.p&C:
                            self._a(m[0x000A])
                            self._compare(r.a,0x05)
                            self._mark(0xAF04)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xAF09)
                                self._rts();return
                            else:
                                self._flag(C,True)
                                self._mark(0xAF07)
                                self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_ae2d,0xAEF6,0xAEF9)):return
                            m[0x0001]=self._nz(m[0x0001]-1)
                            if not (yield from self._local_call(self.local_ae42,0xAEFB,0xAEFE)):return
                            self._mark(0xAEFE)
                            if not r.p&C:
                                self._flag(C,False)
                                self._mark(0xAF09)
                                self._rts();return
                            else:
                                self._a(m[0x000A])
                                self._compare(r.a,0x05)
                                self._mark(0xAF04)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xAF09)
                                    self._rts();return
                                else:
                                    self._flag(C,True)
                                    self._mark(0xAF07)
                                    self._rts();return

    def local_af0a(self):
        """$AF0A: local af0a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF0A)
        self._y(m[0x000A])
        self._compare(r.y,0x03)
        self._mark(0xAF0E)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xAF43)
            self._rts();return
        else:
            if not (yield from self._local_call(self.local_ae2d,0xAF10,0xAF13)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_af44,0xAF15,0xAF18)):return
            self._compare(r.a,0x03)
            self._mark(0xAF1A)
            if r.p&Z:
                self._flag(C,True)
                self._mark(0xAF41)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAF1C,0xAF1F)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_af44,0xAF21,0xAF24)):return
                self._compare(r.a,0x03)
                self._mark(0xAF26)
                if r.p&Z:
                    self._flag(C,True)
                    self._mark(0xAF41)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAF28,0xAF2B)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_af44,0xAF2D,0xAF30)):return
                    self._compare(r.a,0x03)
                    self._mark(0xAF32)
                    if r.p&Z:
                        self._flag(C,True)
                        self._mark(0xAF41)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAF34,0xAF37)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_af44,0xAF39,0xAF3C)):return
                        self._compare(r.a,0x03)
                        self._mark(0xAF3E)
                        if not r.p&Z:
                            self._flag(C,False)
                            self._mark(0xAF43)
                            self._rts();return
                        else:
                            self._flag(C,True)
                            self._mark(0xAF41)
                            self._rts();return

    def local_af44(self):
        """$AF44: local af44; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF44)
        self._a(m[0x0000])
        self._compare(r.a,0x20)
        self._mark(0xAF48)
        if r.p&C:
            self._a(0xFF)
            self._mark(0xAF72)
            self._rts();return
        else:
            self._a(m[0x0001])
            self._compare(r.a,0x14)
            self._mark(0xAF4E)
            if r.p&C:
                self._a(0xFF)
                self._mark(0xAF72)
                self._rts();return
            else:
                self._compare(r.a,0x0F)
                self._mark(0xAF52)
                if not r.p&Z:
                    pass
                else:
                    m[0x0001]=self._nz(m[0x0001]+1)
                    pass
                if not (yield from self._local_call(self.local_d6b6,0xAF57,0xAF5A)):return
                self._a(r.y)
                self._mark(0xAF5B)
                if r.p&N:
                    self._a(0xFF)
                    self._mark(0xAF72)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xAF5D,0xAF60)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xAF62)
                    if not r.p&Z:
                        self._a(0xFF)
                        self._mark(0xAF72)
                        self._rts();return
                    else:
                        self._a(m[0x0000])
                        m[0x0010]=r.a
                        self._a(m[0x0001])
                        m[0x0011]=r.a
                        if not (yield from self._local_call(self.terrain_at_position,0xAF6C,0xAF6F)):return
                        self._mark(0xAF6F)
                        self._rts();return

    def local_af73(self):
        """$AF73: local af73; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF73)
        self._a(m[0x000B])
        self._mark(0xAF75)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xAF9E)
            self._rts();return
        else:
            self._y(m[ACTOR_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            yield from self._external(0xAF7D,0xF2D7,0xAF80,"call",None)
            if r.pc!=0xAF80:return  # preserve nonlocal stack return
            self._y(0x09)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xAF84)
            if not r.p&Z:
                self._y(0x00)
                self._a(m[SIDE])
                self._mark(0xAF92)
                if not r.p&N:
                    pass
                else:
                    self._y(0x04)
                    pass
                self._a(m[(0x04D8+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xAF9B)
                if r.p&Z:
                    self._flag(C,True)
                    self._mark(0xAFA0)
                    self._rts();return
                else:
                    self._flag(C,False)
                    self._mark(0xAF9E)
                    self._rts();return
            else:
                self._y(r.y-1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x64)
                self._mark(0xAF8B)
                if not r.p&C:
                    self._flag(C,False)
                    self._mark(0xAF9E)
                    self._rts();return
                else:
                    self._y(0x00)
                    self._a(m[SIDE])
                    self._mark(0xAF92)
                    if not r.p&N:
                        pass
                    else:
                        self._y(0x04)
                        pass
                    self._a(m[(0x04D8+r.y)&65535])
                    self._compare(r.a,0xFF)
                    self._mark(0xAF9B)
                    if r.p&Z:
                        self._flag(C,True)
                        self._mark(0xAFA0)
                        self._rts();return
                    else:
                        self._flag(C,False)
                        self._mark(0xAF9E)
                        self._rts();return

    def local_afa1(self):
        """$AFA1: local afa1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFA1)
        self._y(m[0x000B])
        self._compare(r.y,0x05)
        self._mark(0xAFA5)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xAFD2)
            self._rts();return
        else:
            if not (yield from self._local_call(self.local_ae2d,0xAFA7,0xAFAA)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_ae42,0xAFAC,0xAFAF)):return
            self._mark(0xAFAF)
            if r.p&C:
                self._flag(C,True)
                self._mark(0xAFD0)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_ae2d,0xAFB1,0xAFB4)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_ae42,0xAFB6,0xAFB9)):return
                self._mark(0xAFB9)
                if r.p&C:
                    self._flag(C,True)
                    self._mark(0xAFD0)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAFBB,0xAFBE)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_ae42,0xAFC0,0xAFC3)):return
                    self._mark(0xAFC3)
                    if r.p&C:
                        self._flag(C,True)
                        self._mark(0xAFD0)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAFC5,0xAFC8)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_ae42,0xAFCA,0xAFCD)):return
                        self._mark(0xAFCD)
                        if not r.p&C:
                            self._flag(C,False)
                            self._mark(0xAFD2)
                            self._rts();return
                        else:
                            self._flag(C,True)
                            self._mark(0xAFD0)
                            self._rts();return

    def local_afd3(self):
        """$AFD3: local afd3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFD3)
        self._y(m[0x000A])
        self._compare(r.y,0x05)
        self._mark(0xAFD7)
        if r.p&Z:
            self._flag(C,False)
            self._mark(0xB01C)
            self._rts();return
        else:
            if not (yield from self._local_call(self.local_ae2d,0xAFD9,0xAFDC)):return
            m[0x0000]=self._nz(m[0x0000]+1)
            if not (yield from self._local_call(self.local_af44,0xAFDE,0xAFE1)):return
            self._compare(r.a,0xFF)
            self._mark(0xAFE3)
            if r.p&Z:
                if not (yield from self._local_call(self.local_ae2d,0xAFE9,0xAFEC)):return
                m[0x0000]=self._nz(m[0x0000]-1)
                if not (yield from self._local_call(self.local_af44,0xAFEE,0xAFF1)):return
                self._compare(r.a,0xFF)
                self._mark(0xAFF3)
                if r.p&Z:
                    if not (yield from self._local_call(self.local_ae2d,0xAFF9,0xAFFC)):return
                    m[0x0001]=self._nz(m[0x0001]+1)
                    if not (yield from self._local_call(self.local_af44,0xAFFE,0xB001)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xB003)
                    if r.p&Z:
                        if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                        m[0x0001]=self._nz(m[0x0001]-1)
                        if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xB013)
                        if r.p&Z:
                            self._flag(C,False)
                            self._mark(0xB01C)
                            self._rts();return
                        else:
                            self._compare(r.a,0x05)
                            self._mark(0xB017)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xB01C)
                                self._rts();return
                            else:
                                self._flag(C,True)
                                self._mark(0xB01A)
                                self._rts();return
                    else:
                        self._compare(r.a,0x05)
                        self._mark(0xB007)
                        if not r.p&Z:
                            self._flag(C,True)
                            self._mark(0xB01A)
                            self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                            m[0x0001]=self._nz(m[0x0001]-1)
                            if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xB013)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xB01C)
                                self._rts();return
                            else:
                                self._compare(r.a,0x05)
                                self._mark(0xB017)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._flag(C,True)
                                    self._mark(0xB01A)
                                    self._rts();return
                else:
                    self._compare(r.a,0x05)
                    self._mark(0xAFF7)
                    if not r.p&Z:
                        self._flag(C,True)
                        self._mark(0xB01A)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_ae2d,0xAFF9,0xAFFC)):return
                        m[0x0001]=self._nz(m[0x0001]+1)
                        if not (yield from self._local_call(self.local_af44,0xAFFE,0xB001)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xB003)
                        if r.p&Z:
                            if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                            m[0x0001]=self._nz(m[0x0001]-1)
                            if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xB013)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xB01C)
                                self._rts();return
                            else:
                                self._compare(r.a,0x05)
                                self._mark(0xB017)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._flag(C,True)
                                    self._mark(0xB01A)
                                    self._rts();return
                        else:
                            self._compare(r.a,0x05)
                            self._mark(0xB007)
                            if not r.p&Z:
                                self._flag(C,True)
                                self._mark(0xB01A)
                                self._rts();return
                            else:
                                if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                                m[0x0001]=self._nz(m[0x0001]-1)
                                if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                                self._compare(r.a,0xFF)
                                self._mark(0xB013)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._compare(r.a,0x05)
                                    self._mark(0xB017)
                                    if r.p&Z:
                                        self._flag(C,False)
                                        self._mark(0xB01C)
                                        self._rts();return
                                    else:
                                        self._flag(C,True)
                                        self._mark(0xB01A)
                                        self._rts();return
            else:
                self._compare(r.a,0x05)
                self._mark(0xAFE7)
                if not r.p&Z:
                    self._flag(C,True)
                    self._mark(0xB01A)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.local_ae2d,0xAFE9,0xAFEC)):return
                    m[0x0000]=self._nz(m[0x0000]-1)
                    if not (yield from self._local_call(self.local_af44,0xAFEE,0xAFF1)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xAFF3)
                    if r.p&Z:
                        if not (yield from self._local_call(self.local_ae2d,0xAFF9,0xAFFC)):return
                        m[0x0001]=self._nz(m[0x0001]+1)
                        if not (yield from self._local_call(self.local_af44,0xAFFE,0xB001)):return
                        self._compare(r.a,0xFF)
                        self._mark(0xB003)
                        if r.p&Z:
                            if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                            m[0x0001]=self._nz(m[0x0001]-1)
                            if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xB013)
                            if r.p&Z:
                                self._flag(C,False)
                                self._mark(0xB01C)
                                self._rts();return
                            else:
                                self._compare(r.a,0x05)
                                self._mark(0xB017)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._flag(C,True)
                                    self._mark(0xB01A)
                                    self._rts();return
                        else:
                            self._compare(r.a,0x05)
                            self._mark(0xB007)
                            if not r.p&Z:
                                self._flag(C,True)
                                self._mark(0xB01A)
                                self._rts();return
                            else:
                                if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                                m[0x0001]=self._nz(m[0x0001]-1)
                                if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                                self._compare(r.a,0xFF)
                                self._mark(0xB013)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._compare(r.a,0x05)
                                    self._mark(0xB017)
                                    if r.p&Z:
                                        self._flag(C,False)
                                        self._mark(0xB01C)
                                        self._rts();return
                                    else:
                                        self._flag(C,True)
                                        self._mark(0xB01A)
                                        self._rts();return
                    else:
                        self._compare(r.a,0x05)
                        self._mark(0xAFF7)
                        if not r.p&Z:
                            self._flag(C,True)
                            self._mark(0xB01A)
                            self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_ae2d,0xAFF9,0xAFFC)):return
                            m[0x0001]=self._nz(m[0x0001]+1)
                            if not (yield from self._local_call(self.local_af44,0xAFFE,0xB001)):return
                            self._compare(r.a,0xFF)
                            self._mark(0xB003)
                            if r.p&Z:
                                if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                                m[0x0001]=self._nz(m[0x0001]-1)
                                if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                                self._compare(r.a,0xFF)
                                self._mark(0xB013)
                                if r.p&Z:
                                    self._flag(C,False)
                                    self._mark(0xB01C)
                                    self._rts();return
                                else:
                                    self._compare(r.a,0x05)
                                    self._mark(0xB017)
                                    if r.p&Z:
                                        self._flag(C,False)
                                        self._mark(0xB01C)
                                        self._rts();return
                                    else:
                                        self._flag(C,True)
                                        self._mark(0xB01A)
                                        self._rts();return
                            else:
                                self._compare(r.a,0x05)
                                self._mark(0xB007)
                                if not r.p&Z:
                                    self._flag(C,True)
                                    self._mark(0xB01A)
                                    self._rts();return
                                else:
                                    if not (yield from self._local_call(self.local_ae2d,0xB009,0xB00C)):return
                                    m[0x0001]=self._nz(m[0x0001]-1)
                                    if not (yield from self._local_call(self.local_af44,0xB00E,0xB011)):return
                                    self._compare(r.a,0xFF)
                                    self._mark(0xB013)
                                    if r.p&Z:
                                        self._flag(C,False)
                                        self._mark(0xB01C)
                                        self._rts();return
                                    else:
                                        self._compare(r.a,0x05)
                                        self._mark(0xB017)
                                        if r.p&Z:
                                            self._flag(C,False)
                                            self._mark(0xB01C)
                                            self._rts();return
                                        else:
                                            self._flag(C,True)
                                            self._mark(0xB01A)
                                            self._rts();return

    def local_b01d(self):
        """$B01D: local b01d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB01D)
        self._y(m[0x000A])
        self._compare(r.y,0x03)
        self._mark(0xB021)
        if r.p&Z:
            self._flag(C,False)
            self._mark(0xB02A)
            self._rts();return
        else:
            self._compare(r.y,0x05)
            self._mark(0xB025)
            if r.p&Z:
                self._flag(C,False)
                self._mark(0xB02A)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xB028)
                self._rts();return

    def apply_tactic(self):
        """$B02B: apply tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB02B)
        self._y(0x00)
        self._a(0x00)
        while True:  # natural loop $B02F
            m[(0x042C+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x09)
            self._mark(0xB035)
            if not r.p&C:
                continue
            else:
                pass
            m[TACTIC_FAILED]=r.a
            self._a(m[TACTIC])
            self._a(r.a & 0x0F)
            self._mark(0xB03F)
            index=self._dispatch(0xB03F,(45154, 45277, 45397, 45434, 45525, 45635, 45154, 45773, 45852, 46006, 46032, 46122, 46182, 46264, 46348, 46502))
            return (yield from (self.local_b062,self.local_b0dd,self.local_b155,self.local_b17a,self.local_b1d5,self.local_b243,self.local_b062,self.local_b2cd,self.local_b31c,self.local_b3b6,self.local_b3d0,self.local_b42a,self.local_b466,self.local_b4b8,self.local_b50c,self.local_b5a6,)[index]())

    def local_b062(self):
        """$B062: local b062; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB062)
        if not (yield from self._local_call(self.local_b7be,0xB062,0xB065)):return
        self._mark(0xB065)
        if r.p&C:
            return (yield from self.local_b070())
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB06F)
            self._rts();return

    def local_b070(self):
        """$B070: local b070; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB070)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB076,0xF2D7,0xB079,"call",None)
        if r.pc!=0xB079:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0002]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0002])
        self._push(r.a)
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x05)
        if not (yield from self._local_call(self.random_bounded,0xB098,0xB09B)):return
        self._flag(C,False)
        self._add(0x09)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xB0A0,0xB0A3)):return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_word,0xB0B3,0xB0B6)):return
        self._a(self._pop())
        self._flag(C,False)
        self._add(m[0x0001])
        m[0x0002]=r.a
        self._a(0x00)
        m[0x0003]=r.a
        self._a(m[0x0002])
        self._flag(C,False)
        self._add(0x1E)
        m[0x0002]=r.a
        self._a(m[0x0003])
        self._add(0x00)
        m[0x0003]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB0D3,0xF2D7,0xB0D6,"call",None)
        if r.pc!=0xB0D6:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.troop_loss,0xB0D6,0xB0D9)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB0DC)
        self._rts();return

    def local_b0dd(self):
        """$B0DD: local b0dd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB0DD)
        if not (yield from self._local_call(self.local_b7be,0xB0DD,0xB0E0)):return
        self._mark(0xB0E0)
        if r.p&C:
            return (yield from self.local_b0eb())
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB0EA)
            self._rts();return

    def local_b0eb(self):
        """$B0EB: local b0eb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB0EB)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB0F1,0xF2D7,0xB0F4,"call",None)
        if r.pc!=0xB0F4:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._push(r.a)
        self._y(0x01)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._y(0x02)
        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        m[0x0004]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.divide_word,0xB112,0xB115)):return
        self._a(self._pop())
        self._flag(C,False)
        self._add(m[0x0001])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x03)
        if not (yield from self._local_call(self.random_bounded,0xB123,0xB126)):return
        self._flag(C,False)
        self._add(0x05)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xB12B,0xB12E)):return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_word,0xB13E,0xB141)):return
        self._a(m[0x0001])
        m[0x0002]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB14B,0xF2D7,0xB14E,"call",None)
        if r.pc!=0xB14E:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.health_loss,0xB14E,0xB151)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB154)
        self._rts();return

    def local_b155(self):
        """$B155: local b155; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB155)
        if not (yield from self._local_call(self.local_b7be,0xB155,0xB158)):return
        self._mark(0xB158)
        if r.p&C:
            self._a(0x02)
            m[0x0000]=r.a
            self._a(m[SIDE])
            self._mark(0xB16A)
            if not r.p&N:
                pass
            else:
                m[0x0000]=self._nz(m[0x0000]+1)
                pass
            self._y(m[SELECTED_SLOT])
            self._a(m[0x0000])
            m[(0x0650+r.y)&65535]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xB179)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB162)
            self._rts();return

    def local_b17a(self):
        """$B17A: local b17a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB17A)
        if not (yield from self._local_call(self.local_b7be,0xB17A,0xB17D)):return
        self._mark(0xB17D)
        if r.p&C:
            return (yield from self.local_b188())
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB187)
            self._rts();return

    def local_b188(self):
        """$B188: local b188; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB188)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB18E,0xF2D7,0xB191,"call",None)
        if r.pc!=0xB191:return  # preserve nonlocal stack return
        self._y(0x01)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x07)
        if not (yield from self._local_call(self.random_bounded,0xB19F,0xB1A2)):return
        self._flag(C,False)
        self._add(0x0E)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xB1A7,0xB1AA)):return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_word,0xB1BA,0xB1BD)):return
        self._a(m[0x0002])
        m[0x0003]=r.a
        self._a(m[0x0001])
        m[0x0002]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB1CB,0xF2D7,0xB1CE,"call",None)
        if r.pc!=0xB1CE:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.troop_loss,0xB1CE,0xB1D1)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB1D4)
        self._rts();return

    def local_b1d5(self):
        """$B1D5: local b1d5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1D5)
        if not (yield from self._local_call(self.local_b7be,0xB1D5,0xB1D8)):return
        self._mark(0xB1D8)
        if r.p&C:
            return (yield from self.local_b1e3())
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB1E2)
            self._rts();return

    def local_b1e3(self):
        """$B1E3: local b1e3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1E3)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB1E9,0xF2D7,0xB1EC,"call",None)
        if r.pc!=0xB1EC:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._push(r.a)
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x07)
        if not (yield from self._local_call(self.random_bounded,0xB203,0xB206)):return
        self._flag(C,False)
        self._add(0x14)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xB20B,0xB20E)):return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_word,0xB21E,0xB221)):return
        self._a(self._pop())
        self._flag(C,False)
        self._add(0x07)
        self._add(m[0x0001])
        m[0x0001]=r.a
        self._a(m[0x0002])
        self._add(0x00)
        m[0x0003]=r.a
        self._a(m[0x0001])
        m[0x0002]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB239,0xF2D7,0xB23C,"call",None)
        if r.pc!=0xB23C:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.troop_loss,0xB23C,0xB23F)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB242)
        self._rts();return

    def local_b243(self):
        """$B243: local b243; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB243)
        if not (yield from self._local_call(self.local_b7be,0xB243,0xB246)):return
        self._mark(0xB246)
        if r.p&C:
            self._a(0x05)
            if not (yield from self._local_call(self.random_bounded,0xB253,0xB256)):return
            self._flag(C,False)
            self._add(0x0A)
            m[0x0003]=r.a
            self._y(0x00)
            self._a(m[SIDE])
            self._mark(0xB260)
            if r.p&N:
                pass
            else:
                self._y(0x02)
                pass
            self._a(m[(0x0522+r.y)&65535])
            m[0x0000]=r.a
            self._a(m[(0x0523+r.y)&65535])
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            if not (yield from self._local_call(self.multiply_24bit,0xB272,0xB275)):return
            self._a(m[0x0006])
            m[0x0000]=r.a
            self._a(m[0x0007])
            m[0x0001]=r.a
            self._a(m[0x0008])
            m[0x0002]=r.a
            self._a(0x64)
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0004]=r.a
            if not (yield from self._local_call(self.divide_24bit,0xB289,0xB28C)):return
            self._a(m[0x0000])
            m[0x0010]=r.a
            self._a(m[0x0001])
            m[0x0011]=r.a
            self._y(m[ACTOR_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            yield from self._external(0xB29A,0xF2D7,0xB29D,"call",None)
            if r.pc!=0xB29D:return  # preserve nonlocal stack return
            self._y(0x02)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            m[0x0004]=r.a
            self._a(0x05)
            m[0x0003]=r.a
            if not (yield from self._local_call(self.divide_word,0xB2AD,0xB2B0)):return
            self._a(m[0x0001])
            self._flag(C,False)
            self._add(m[0x0010])
            m[0x0010]=r.a
            self._a(m[0x0011])
            self._add(0x00)
            m[0x0011]=r.a
            self._y(0x00)
            self._a(m[SIDE])
            self._mark(0xB2C2)
            if r.p&N:
                pass
            else:
                self._y(0x02)
                pass
            if not (yield from self._local_call(self.local_b6f0,0xB2C6,0xB2C9)):return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xB2CC)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB250)
            self._rts();return

    def local_b2cd(self):
        """$B2CD: local b2cd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB2CD)
        if not (yield from self._local_call(self.local_b7be,0xB2CD,0xB2D0)):return
        self._mark(0xB2D0)
        if r.p&C:
            if not (yield from self._local_call(self.local_b070,0xB2DB,0xB2DE)):return
            if not (yield from self._local_call(self.local_b67b,0xB2DE,0xB2E1)):return
            m[0x0010]=self._nz(m[0x0010]-1)
            if not (yield from self._local_call(self.local_b304,0xB2E3,0xB2E6)):return
            if not (yield from self._local_call(self.local_b67b,0xB2E6,0xB2E9)):return
            m[0x0010]=self._nz(m[0x0010]+1)
            if not (yield from self._local_call(self.local_b304,0xB2EB,0xB2EE)):return
            if not (yield from self._local_call(self.local_b67b,0xB2EE,0xB2F1)):return
            m[0x0011]=self._nz(m[0x0011]-1)
            if not (yield from self._local_call(self.local_b304,0xB2F3,0xB2F6)):return
            if not (yield from self._local_call(self.local_b67b,0xB2F6,0xB2F9)):return
            m[0x0011]=self._nz(m[0x0011]+1)
            if not (yield from self._local_call(self.local_b304,0xB2FB,0xB2FE)):return
            self._a(0x07)
            m[PHASE]=r.a
            self._mark(0xB303)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB2DA)
            self._rts();return

    def local_b304(self):
        """$B304: local b304; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB304)
        if not (yield from self._local_call(self.local_b643,0xB304,0xB307)):return
        self._mark(0xB307)
        if r.p&Z:
            pass
        else:
            self._compare(r.a,0xFE)
            self._mark(0xB30B)
            if r.p&Z:
                pass
            else:
                self._a(m[SELECTED_SLOT])
                self._push(r.a)
                m[SELECTED_SLOT]=r.y
                if not (yield from self._local_call(self.local_b070,0xB314,0xB317)):return
                self._a(self._pop())
                m[SELECTED_SLOT]=r.a
                pass
            pass
        self._mark(0xB31B)
        self._rts();return

    def local_b31c(self):
        """$B31C: local b31c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB31C)
        if not (yield from self._local_call(self.local_b72b,0xB31C,0xB31F)):return
        self._mark(0xB31F)
        if r.p&C:
            self._y(m[SELECTED_SLOT])
            if not (yield from self._local_call(self.local_c886,0xB32D,0xB330)):return
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0628+r.y)&65535])
            self._a(r.a ^ 0x80)
            m[(0x0628+r.y)&65535]=r.a
            self._a(m[(0x0664+r.y)&65535])
            m[0x042C]=r.a
            self._a(0xFF)
            self._compare(r.y,m[0x04D8])
            self._mark(0xB346)
            if not r.p&Z:
                pass
            else:
                m[0x04D8]=r.a
                pass
            self._compare(r.y,m[0x04DC])
            self._mark(0xB34E)
            if not r.p&Z:
                pass
            else:
                m[0x04DC]=r.a
                pass
            self._a(m[(0x6FA1+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xB358)
            if not r.p&Z:
                self._a(0xFF)
                m[(0x6FA1+r.y)&65535]=r.a
                pass
            else:
                self._a(0x04)
                m[(0x6FA1+r.y)&65535]=r.a
                pass
            self._a(m[RULERS])
            self._a(r.a & 0x0F)
            m[0x0010]=r.a
            self._a(m[RULERS])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0011]=r.a
            self._x(m[0x0010])
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0628+r.y)&65535])
            self._mark(0xB37F)
            if not r.p&N:
                pass
            else:
                self._x(m[0x0011])
                pass
            self._a(r.x)
            if not (yield from self._local_call(self.ruler_pointer,0xB384,0xB387)):return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0030]=r.a
            self._x(m[0x0011])
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0628+r.y)&65535])
            self._mark(0xB395)
            if not r.p&N:
                pass
            else:
                self._x(m[0x0010])
                pass
            self._a(r.x)
            if not (yield from self._local_call(self.ruler_pointer,0xB39A,0xB39D)):return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0032]=r.a
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            m[0x0031]=r.a
            self._y(0x2A)
            yield from self._external(0xB3AD,0xEE07,0xB3B2,"far_call",40966)
            if r.pc!=0xB3B2:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xB3B5)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB329)
            self._rts();return

    def local_b3b6(self):
        """$B3B6: local b3b6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB3B6)
        if not (yield from self._local_call(self.local_b7be,0xB3B6,0xB3B9)):return
        self._mark(0xB3B9)
        if r.p&C:
            if not (yield from self._local_call(self.local_b0eb,0xB3C4,0xB3C7)):return
            if not (yield from self._local_call(self.local_b188,0xB3C7,0xB3CA)):return
            self._a(0x07)
            m[PHASE]=r.a
            self._mark(0xB3CF)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB3C3)
            self._rts();return

    def local_b3d0(self):
        """$B3D0: local b3d0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB3D0)
        if not (yield from self._local_call(self.local_b7be,0xB3D0,0xB3D3)):return
        self._mark(0xB3D3)
        if r.p&C:
            if not (yield from self._local_call(self.local_b8a1,0xB3DE,0xB3E1)):return
            self._y(0x00)
            while True:  # natural loop $B3E3
                self._a(m[(0x6FC9+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB3E8)
                if r.p&Z:
                    pass
                else:
                    m[0x0012]=r.a
                    self._a(r.y)
                    self._push(r.a)
                    if not (yield from self._local_call(self.local_b3fe,0xB3EE,0xB3F1)):return
                    self._a(self._pop())
                    self._y(r.a)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xB3F6)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0x07)
                m[PHASE]=r.a
                self._mark(0xB3FD)
                self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB3DD)
            self._rts();return

    def local_b3fe(self):
        """$B3FE: local b3fe; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB3FE)
        self._y(m[0x0012])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        if not (yield from self._local_call(self.terrain_at_position,0xB40A,0xB40D)):return
        self._compare(r.a,0x03)
        self._mark(0xB40F)
        if not r.p&Z:
            pass
        else:
            self._a(0x02)
            if not (yield from self._local_call(self.random_bounded,0xB413,0xB416)):return
            self._flag(C,False)
            self._add(0x03)
            m[0x0000]=r.a
            self._a(m[SIDE])
            self._mark(0xB41E)
            if not r.p&N:
                pass
            else:
                m[0x0000]=self._nz(m[0x0000]+1)
                pass
            self._y(m[0x0012])
            self._a(m[0x0000])
            m[(0x0650+r.y)&65535]=r.a
            pass
        self._mark(0xB429)
        self._rts();return

    def local_b42a(self):
        """$B42A: local b42a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB42A)
        self._x(0x00)
        self._a(m[SIDE])
        self._mark(0xB42F)
        if not r.p&N:
            pass
        else:
            self._x(0x04)
            pass
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[(0x04D9+r.x)&65535]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[(0x04DA+r.x)&65535]=r.a
        self._a(0x05)
        m[(0x04DB+r.x)&65535]=r.a
        self._a(r.y)
        m[(0x04D8+r.x)&65535]=r.a
        self._y(r.a)
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB44F,0xF2D7,0xB452,"call",None)
        if r.pc!=0xB452:return  # preserve nonlocal stack return
        self._y(0x08)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x64,subtract=True)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(0x00,subtract=True)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB465)
        self._rts();return

    def local_b466(self):
        """$B466: local b466; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB466)
        if not (yield from self._local_call(self.local_b7be,0xB466,0xB469)):return
        self._mark(0xB469)
        if r.p&C:
            if not (yield from self._local_call(self.local_b8a1,0xB474,0xB477)):return
            self._y(0x00)
            while True:  # natural loop $B479
                self._a(m[(0x6FC9+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB47E)
                if r.p&Z:
                    pass
                else:
                    m[0x0012]=r.a
                    self._a(r.y)
                    self._push(r.a)
                    if not (yield from self._local_call(self.local_b494,0xB484,0xB487)):return
                    self._a(self._pop())
                    self._y(r.a)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xB48C)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(0x07)
                m[PHASE]=r.a
                self._mark(0xB493)
                self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB473)
            self._rts();return

    def local_b494(self):
        """$B494: local b494; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB494)
        self._y(m[0x0012])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        if not (yield from self._local_call(self.terrain_at_position,0xB4A0,0xB4A3)):return
        self._compare(r.a,0x03)
        self._mark(0xB4A5)
        if not r.p&Z:
            pass
        else:
            self._y(m[0x0012])
            self._a(m[SELECTED_SLOT])
            self._push(r.a)
            m[SELECTED_SLOT]=r.y
            if not (yield from self._local_call(self.local_b1e3,0xB4B0,0xB4B3)):return
            self._a(self._pop())
            m[SELECTED_SLOT]=r.a
            pass
        self._mark(0xB4B7)
        self._rts();return

    def local_b4b8(self):
        """$B4B8: local b4b8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB4B8)
        if not (yield from self._local_call(self.local_b7be,0xB4B8,0xB4BB)):return
        self._mark(0xB4BB)
        if r.p&C:
            self._y(m[ACTOR_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            yield from self._external(0xB4CC,0xF2D7,0xB4CF,"call",None)
            if r.pc!=0xB4CF:return  # preserve nonlocal stack return
            self._a(0x00)
            m[0x0002]=r.a
            m[0x0003]=r.a
            while True:  # natural loop $B4D5
                yield from self._external(0xB4D5,0xE87A,0xB4D8,"call",None)
                if r.pc!=0xB4D8:return  # preserve nonlocal stack return
                self._compare(r.a,0xC8)
                self._mark(0xB4DA)
                if r.p&C:
                    continue
                else:
                    pass
                self._flag(C,False)
                self._add(0x96)
                m[0x0002]=r.a
                self._a(m[0x0003])
                self._add(0x00)
                m[0x0003]=r.a
                self._y(0x01)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._y(0x02)
                self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                self._flag(C,False)
                self._add(m[0x0002])
                m[0x0002]=r.a
                self._a(m[0x0003])
                self._add(0x00)
                m[0x0003]=r.a
                self._y(m[SELECTED_SLOT])
                self._a(m[(0x0664+r.y)&65535])
                yield from self._external(0xB502,0xF2D7,0xB505,"call",None)
                if r.pc!=0xB505:return  # preserve nonlocal stack return
                if not (yield from self._local_call(self.troop_loss,0xB505,0xB508)):return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xB50B)
                self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB4C5)
            self._rts();return

    def local_b50c(self):
        """$B50C: local b50c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB50C)
        if not (yield from self._local_call(self.local_b7be,0xB50C,0xB50F)):return
        self._mark(0xB50F)
        if r.p&C:
            if not (yield from self._local_call(self.local_b8a1,0xB51A,0xB51D)):return
            self._y(0x00)
            while True:  # natural loop $B51F
                self._a(m[(0x6FC9+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB524)
                if r.p&Z:
                    pass
                else:
                    m[0x0012]=r.a
                    self._a(r.y)
                    self._push(r.a)
                    if not (yield from self._local_call(self.local_b538,0xB52A,0xB52D)):return
                    self._a(self._pop())
                    self._y(r.a)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xB532)
                if not r.p&C:
                    continue
                else:
                    pass
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xB537)
                self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB519)
            self._rts();return

    def local_b538(self):
        """$B538: local b538; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB538)
        self._y(m[0x0012])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        if not (yield from self._local_call(self.terrain_at_position,0xB544,0xB547)):return
        self._compare(r.a,0x05)
        self._mark(0xB549)
        if r.p&Z:
            pass
        else:
            self._y(m[0x0012])
            self._a(m[SELECTED_SLOT])
            self._push(r.a)
            m[SELECTED_SLOT]=r.y
            if not (yield from self._local_call(self.local_b55c,0xB554,0xB557)):return
            self._a(self._pop())
            m[SELECTED_SLOT]=r.a
            pass
        self._mark(0xB55B)
        self._rts();return

    def local_b55c(self):
        """$B55C: local b55c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB55C)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB562,0xF2D7,0xB565,"call",None)
        if r.pc!=0xB565:return  # preserve nonlocal stack return
        self._a(0x06)
        if not (yield from self._local_call(self.random_bounded,0xB567,0xB56A)):return
        self._flag(C,False)
        self._add(0x1E)
        m[0x0003]=r.a
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xB57B,0xB57E)):return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_word,0xB58E,0xB591)):return
        self._a(m[0x0002])
        m[0x0003]=r.a
        self._a(m[0x0001])
        m[0x0002]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB59F,0xF2D7,0xB5A2,"call",None)
        if r.pc!=0xB5A2:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.troop_loss,0xB5A2,0xB5A5)):return
        self._mark(0xB5A5)
        self._rts();return

    def local_b5a6(self):
        """$B5A6: local b5a6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB5A6)
        if not (yield from self._local_call(self.local_b7be,0xB5A6,0xB5A9)):return
        self._mark(0xB5A9)
        if r.p&C:
            if not (yield from self._local_call(self.random_four,0xB5B4,0xB5B7)):return
            self._flag(C,False)
            self._add(0x05)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0000]=r.a
            self._a(m[SIDE])
            self._mark(0xB5C3)
            if not r.p&N:
                pass
            else:
                self._a(m[0x0000])
                self._flag(C,False)
                self._add(0x10)
                m[0x0000]=r.a
                pass
            self._y(m[SELECTED_SLOT])
            self._a(m[0x0000])
            m[(0x0650+r.y)&65535]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xB5D7)
            self._rts();return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xFF)
            m[TACTIC_FAILED]=r.a
            self._mark(0xB5B3)
            self._rts();return

    def health_loss(self):
        """$B5D8: health loss; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB5D8)
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0004]=r.a
        self._flag(C,True)
        self._add(m[0x0002],subtract=True)
        m[0x0006]=r.a
        self._mark(0xB5E3)
        if r.p&C:
            pass
        else:
            self._a(m[0x0004])
            m[0x0002]=r.a
            self._a(0x00)
            m[0x0006]=r.a
            pass
        self._y(0x00)
        self._a(m[0x0006])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(m[0x0002])
        m[0x042F]=r.a
        self._a(0x00)
        m[0x0430]=r.a
        m[0x0431]=r.a
        self._a(0xFF)
        m[0x0432]=r.a
        self._a(m[0x0006])
        self._mark(0xB607)
        if not r.p&Z:
            pass
        else:
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a | 0x03)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            if not (yield from self._local_call(self.map_refresh,0xB615,0xB618)):return
            self._y(m[ACTOR_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            m[0x000A]=r.a
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            m[0x000B]=r.a
            self._y(0x2E)
            yield from self._external(0xB62A,0xEE07,0xB62F,"far_call",40969)
            if r.pc!=0xB62F:return  # preserve nonlocal stack return
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            m[0x0432]=r.a
            m[0x0000]=r.y
            self._y(0x28)
            yield from self._external(0xB63D,0xEE07,0xB642,"far_call",41002)
            if r.pc!=0xB642:return  # preserve nonlocal stack return
            pass
        self._mark(0xB642)
        self._rts();return

    def local_b643(self):
        """$B643: local b643; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB643)
        self._a(m[0x0011])
        self._compare(r.a,0x0F)
        self._mark(0xB647)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0001])
            self._compare(r.a,0x0E)
            self._mark(0xB64D)
            if r.p&Z:
                self._a(0x10)
                m[0x0011]=r.a
                pass
            else:
                self._a(0x0E)
                m[0x0011]=r.a
                pass
            pass
        self._a(m[0x0010])
        m[0x0000]=r.a
        self._a(m[0x0011])
        m[0x0001]=r.a
        self._a(m[0x0000])
        self._compare(r.a,0x20)
        self._mark(0xB666)
        if r.p&C:
            self._a(0xFE)
            self._mark(0xB67A)
            self._rts();return
        else:
            self._a(m[0x0001])
            self._compare(r.a,0x14)
            self._mark(0xB66C)
            if r.p&C:
                self._a(0xFE)
                self._mark(0xB67A)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_d6b6,0xB66E,0xB671)):return
                self._a(r.y)
                self._mark(0xB672)
                if r.p&N:
                    self._a(0xFE)
                    self._mark(0xB67A)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xB674,0xB677)):return
                    self._mark(0xB677)
                    self._rts();return

    def local_b67b(self):
        """$B67B: local b67b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB67B)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        m[0x0001]=r.a
        self._mark(0xB68A)
        self._rts();return

    def troop_loss(self):
        """$B68B: troop loss; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB68B)
        self._y(0x08)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0004]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x03)
        m[0x0005]=r.a
        self._a(m[0x0004])
        self._flag(C,True)
        self._add(m[0x0002],subtract=True)
        m[0x0006]=r.a
        self._a(m[0x0005])
        self._add(m[0x0003],subtract=True)
        m[0x0007]=r.a
        self._mark(0xB6A5)
        if r.p&C:
            pass
        else:
            self._a(m[0x0004])
            m[0x0002]=r.a
            self._a(m[0x0005])
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0006]=r.a
            m[0x0007]=r.a
            pass
        self._y(0x08)
        self._a(m[0x0006])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[0x0007])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(m[0x0002])
        self._flag(C,False)
        self._add(m[0x042C])
        m[0x042C]=r.a
        self._a(m[0x0003])
        self._add(m[0x042D])
        m[0x042D]=r.a
        self._a(0x00)
        m[0x042E]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        m[0x000A]=r.a
        self._a(m[0x042C])
        m[0x000B]=r.a
        self._a(m[0x042D])
        m[0x000C]=r.a
        self._y(0x2E)
        yield from self._external(0xB6EA,0xEE07,0xB6EF,"far_call",40966)
        if r.pc!=0xB6EF:return  # preserve nonlocal stack return
        self._mark(0xB6EF)
        self._rts();return

    def local_b6f0(self):
        """$B6F0: local b6f0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB6F0)
        self._a(m[(0x0522+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0010],subtract=True)
        m[0x0012]=r.a
        self._a(m[(0x0523+r.y)&65535])
        self._add(m[0x0011],subtract=True)
        m[0x0013]=r.a
        self._mark(0xB6FF)
        if r.p&C:
            pass
        else:
            self._a(m[(0x0522+r.y)&65535])
            m[0x0010]=r.a
            self._a(m[(0x0523+r.y)&65535])
            m[0x0011]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            m[0x0013]=r.a
            pass
        self._a(m[0x0012])
        m[(0x0522+r.y)&65535]=r.a
        self._a(m[0x0013])
        m[(0x0523+r.y)&65535]=r.a
        self._a(m[0x0010])
        m[0x042C]=r.a
        self._a(m[0x0011])
        m[0x042D]=r.a
        self._a(0x00)
        m[0x042E]=r.a
        self._mark(0xB72A)
        self._rts();return

    def local_b72b(self):
        """$B72B: local b72b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB72B)
        if not (yield from self._local_call(self.local_b860,0xB72B,0xB72E)):return
        self._compare(r.a,0x06)
        self._mark(0xB730)
        if not r.p&C:
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0664+r.y)&65535])
            yield from self._external(0xB73B,0xF2D7,0xB73E,"call",None)
            if r.pc!=0xB73E:return  # preserve nonlocal stack return
            self._x(0x00)
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0011]=r.a
            self._y(0x03)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0x1F)
            self._mark(0xB750)
            if not r.p&C:
                self._a(m[(0xB7BA+r.x)&65535])
                m[0x0010]=r.a
                self._y(m[ACTOR_SLOT])
                self._a(m[(0x0664+r.y)&65535])
                yield from self._external(0xB769,0xF2D7,0xB76C,"call",None)
                if r.pc!=0xB76C:return  # preserve nonlocal stack return
                self._a(m[0x0000])
                m[0x000A]=r.a
                self._a(m[0x0001])
                m[0x000B]=r.a
                self._y(0x0B)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._flag(C,True)
                self._add(m[0x0011],subtract=True)
                self._mark(0xB77F)
                if not r.p&N:
                    pass
                else:
                    self._a(0x00)
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0011]=r.a
                self._y(0x02)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                m[0x0001]=r.a
                self._y(0x04)
                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0001])
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                m[0x0004]=r.a
                self._a(0x0A)
                m[0x0003]=r.a
                if not (yield from self._local_call(self.divide_word,0xB79F,0xB7A2)):return
                self._a(m[0x0001])
                self._flag(C,False)
                self._add(m[0x0010])
                self._add(m[0x0011])
                m[0x0000]=r.a
                while True:  # natural loop $B7AB
                    yield from self._external(0xB7AB,0xE87A,0xB7AE,"call",None)
                    if r.pc!=0xB7AE:return  # preserve nonlocal stack return
                    self._compare(r.a,0x64)
                    self._mark(0xB7B0)
                    if r.p&C:
                        continue
                    else:
                        pass
                    self._compare(r.a,m[0x0000])
                    self._mark(0xB7B4)
                    if not r.p&C:
                        self._flag(C,True)
                        self._mark(0xB7B9)
                        self._rts();return
                    else:
                        self._flag(C,False)
                        self._mark(0xB7B7)
                        self._rts();return
            else:
                self._x(r.x+1)
                self._compare(r.a,0x33)
                self._mark(0xB755)
                if not r.p&C:
                    self._a(m[(0xB7BA+r.x)&65535])
                    m[0x0010]=r.a
                    self._y(m[ACTOR_SLOT])
                    self._a(m[(0x0664+r.y)&65535])
                    yield from self._external(0xB769,0xF2D7,0xB76C,"call",None)
                    if r.pc!=0xB76C:return  # preserve nonlocal stack return
                    self._a(m[0x0000])
                    m[0x000A]=r.a
                    self._a(m[0x0001])
                    m[0x000B]=r.a
                    self._y(0x0B)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._flag(C,True)
                    self._add(m[0x0011],subtract=True)
                    self._mark(0xB77F)
                    if not r.p&N:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0011]=r.a
                    self._y(0x02)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    self._y(0x04)
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0001])
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    m[0x0004]=r.a
                    self._a(0x0A)
                    m[0x0003]=r.a
                    if not (yield from self._local_call(self.divide_word,0xB79F,0xB7A2)):return
                    self._a(m[0x0001])
                    self._flag(C,False)
                    self._add(m[0x0010])
                    self._add(m[0x0011])
                    m[0x0000]=r.a
                    while True:  # natural loop $B7AB
                        yield from self._external(0xB7AB,0xE87A,0xB7AE,"call",None)
                        if r.pc!=0xB7AE:return  # preserve nonlocal stack return
                        self._compare(r.a,0x64)
                        self._mark(0xB7B0)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._compare(r.a,m[0x0000])
                        self._mark(0xB7B4)
                        if not r.p&C:
                            self._flag(C,True)
                            self._mark(0xB7B9)
                            self._rts();return
                        else:
                            self._flag(C,False)
                            self._mark(0xB7B7)
                            self._rts();return
                else:
                    self._x(r.x+1)
                    self._compare(r.a,0x47)
                    self._mark(0xB75A)
                    if not r.p&C:
                        self._a(m[(0xB7BA+r.x)&65535])
                        m[0x0010]=r.a
                        self._y(m[ACTOR_SLOT])
                        self._a(m[(0x0664+r.y)&65535])
                        yield from self._external(0xB769,0xF2D7,0xB76C,"call",None)
                        if r.pc!=0xB76C:return  # preserve nonlocal stack return
                        self._a(m[0x0000])
                        m[0x000A]=r.a
                        self._a(m[0x0001])
                        m[0x000B]=r.a
                        self._y(0x0B)
                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._flag(C,True)
                        self._add(m[0x0011],subtract=True)
                        self._mark(0xB77F)
                        if not r.p&N:
                            pass
                        else:
                            self._a(0x00)
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        m[0x0011]=r.a
                        self._y(0x02)
                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                        m[0x0001]=r.a
                        self._y(0x04)
                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x0001])
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        m[0x0004]=r.a
                        self._a(0x0A)
                        m[0x0003]=r.a
                        if not (yield from self._local_call(self.divide_word,0xB79F,0xB7A2)):return
                        self._a(m[0x0001])
                        self._flag(C,False)
                        self._add(m[0x0010])
                        self._add(m[0x0011])
                        m[0x0000]=r.a
                        while True:  # natural loop $B7AB
                            yield from self._external(0xB7AB,0xE87A,0xB7AE,"call",None)
                            if r.pc!=0xB7AE:return  # preserve nonlocal stack return
                            self._compare(r.a,0x64)
                            self._mark(0xB7B0)
                            if r.p&C:
                                continue
                            else:
                                pass
                            self._compare(r.a,m[0x0000])
                            self._mark(0xB7B4)
                            if not r.p&C:
                                self._flag(C,True)
                                self._mark(0xB7B9)
                                self._rts();return
                            else:
                                self._flag(C,False)
                                self._mark(0xB7B7)
                                self._rts();return
                    else:
                        self._flag(C,False)
                        self._mark(0xB75D)
                        self._rts();return
        else:
            self._flag(C,False)
            self._mark(0xB7B7)
            self._rts();return

    def local_b7be(self):
        """$B7BE: local b7be; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB7BE)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB7C4,0xF2D7,0xB7C7,"call",None)
        if r.pc!=0xB7C7:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0010]=r.a
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0011]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xB7DD,0xF2D7,0xB7E0,"call",None)
        if r.pc!=0xB7E0:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0012]=r.a
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0013]=r.a
        self._a(m[0x0012])
        self._flag(C,True)
        self._add(m[0x0010],subtract=True)
        self._mark(0xB7F5)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            pass
        m[0x0010]=r.a
        self._a(m[0x0013])
        self._flag(C,True)
        self._add(m[0x0011],subtract=True)
        self._mark(0xB800)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            pass
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0011]=r.a
        if not (yield from self._local_call(self.local_b860,0xB807,0xB80A)):return
        self._y(r.a)
        self._compare(r.y,0x06)
        self._mark(0xB80D)
        if r.p&C:
            self._flag(C,False)
            self._mark(0xB857)
            self._rts();return
        else:
            self._a(m[(0xB85A+r.y)&65535])
            m[0x0012]=r.a
            self._x(0x0A)
            self._a(m[CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xB81B)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x6F02])
                self._compare(r.a,0x01)
                self._mark(0xB822)
                if r.p&Z:
                    pass
                else:
                    self._x(0x14)
                    self._compare(r.a,0x02)
                    self._mark(0xB828)
                    if r.p&Z:
                        pass
                    else:
                        self._x(0x05)
                        pass
                    pass
                pass
            m[0x0014]=r.x
            self._a(m[0x0012])
            self._flag(C,False)
            self._add(m[0x0010])
            self._flag(C,False)
            self._add(m[0x0011])
            self._flag(C,False)
            self._add(m[0x0014])
            self._mark(0xB839)
            if not r.p&N:
                pass
            else:
                self._a(0x00)
                pass
            self._compare(r.a,0x5F)
            self._mark(0xB83F)
            if not r.p&C:
                pass
            else:
                self._a(0x5F)
                pass
            self._compare(r.a,0x05)
            self._mark(0xB845)
            if r.p&C:
                pass
            else:
                self._a(0x05)
                pass
            m[0x0000]=r.a
            while True:  # natural loop $B84B
                yield from self._external(0xB84B,0xE87A,0xB84E,"call",None)
                if r.pc!=0xB84E:return  # preserve nonlocal stack return
                self._compare(r.a,0x64)
                self._mark(0xB850)
                if r.p&C:
                    continue
                else:
                    pass
                self._compare(r.a,m[0x0000])
                self._mark(0xB854)
                if not r.p&C:
                    self._flag(C,True)
                    self._mark(0xB859)
                    self._rts();return
                else:
                    self._flag(C,False)
                    self._mark(0xB857)
                    self._rts();return

    def local_b860(self):
        """$B860: local b860; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB860)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0614+r.y)&65535])
        self._compare(r.a,0x10)
        self._mark(0xB868)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        m[0x0000]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0614+r.y)&65535])
        self._compare(r.a,0x10)
        self._mark(0xB876)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        self._flag(C,True)
        self._add(m[0x0000],subtract=True)
        self._mark(0xB87D)
        if r.p&C:
            pass
        else:
            self._a(r.a ^ 0xFF)
            self._flag(C,False)
            self._add(0x01)
            pass
        m[0x0000]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        self._flag(C,True)
        self._y(m[SELECTED_SLOT])
        self._add(m[(0x0600+r.y)&65535],subtract=True)
        self._mark(0xB893)
        if r.p&C:
            pass
        else:
            self._a(r.a ^ 0xFF)
            self._flag(C,False)
            self._add(0x01)
            pass
        self._compare(r.a,m[0x0000])
        self._mark(0xB89C)
        if r.p&C:
            pass
        else:
            self._a(m[0x0000])
            pass
        self._mark(0xB8A0)
        self._rts();return

    def local_b8a1(self):
        """$B8A1: local b8a1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB8A1)
        self._y(0x00)
        self._a(0xFF)
        while True:  # natural loop $B8A5
            m[(0x6FC9+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x14)
            self._mark(0xB8AB)
            if not r.p&C:
                continue
            else:
                pass
            self._a(m[SELECTED_SLOT])
            m[0x6FC9]=r.a
            self._y(r.a)
            if not (yield from self._local_call(self.local_b8ce,0xB8B4,0xB8B7)):return
            self._x(0x01)
            while True:  # natural loop $B8B9
                self._a(m[(0x6FC9+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xB8BE)
                if r.p&Z:
                    pass
                else:
                    self._y(r.a)
                    self._a(r.x)
                    self._push(r.a)
                    if not (yield from self._local_call(self.local_b8ce,0xB8C3,0xB8C6)):return
                    self._a(self._pop())
                    self._x(r.a)
                    self._x(r.x+1)
                    self._compare(r.x,0x14)
                    self._mark(0xB8CB)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    pass
                self._mark(0xB8CD)
                self._rts();return

    def local_b8ce(self):
        """$B8CE: local b8ce; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB8CE)
        self._a(m[(0x0600+r.y)&65535])
        m[0x0012]=r.a
        self._a(m[(0x0614+r.y)&65535])
        self._compare(r.a,0x10)
        self._mark(0xB8D8)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            pass
        m[0x0013]=r.a
        m[0x0012]=self._nz(m[0x0012]+1)
        if not (yield from self._local_call(self.local_b8fa,0xB8E1,0xB8E4)):return
        m[0x0012]=self._nz(m[0x0012]-1)
        m[0x0012]=self._nz(m[0x0012]-1)
        if not (yield from self._local_call(self.local_b8fa,0xB8E8,0xB8EB)):return
        m[0x0012]=self._nz(m[0x0012]+1)
        m[0x0013]=self._nz(m[0x0013]+1)
        if not (yield from self._local_call(self.local_b8fa,0xB8EF,0xB8F2)):return
        m[0x0013]=self._nz(m[0x0013]-1)
        m[0x0013]=self._nz(m[0x0013]-1)
        if not (yield from self._local_call(self.local_b8fa,0xB8F6,0xB8F9)):return
        self._mark(0xB8F9)
        self._rts();return

    def local_b8fa(self):
        """$B8FA: local b8fa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB8FA)
        self._y(0x00)
        while True:  # natural loop $B8FC
            self._a(m[(0x0600+r.y)&65535])
            self._compare(r.a,m[0x0012])
            self._mark(0xB901)
            if not r.p&Z:
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xB91B)
                if not r.p&C:
                    continue
                else:
                    self._mark(0xB91D)
                    self._rts();return
            else:
                self._a(m[(0x0614+r.y)&65535])
                self._compare(r.a,0x10)
                self._mark(0xB908)
                if not r.p&C:
                    pass
                else:
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    pass
                self._compare(r.a,m[0x0013])
                self._mark(0xB90F)
                if not r.p&Z:
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    self._mark(0xB91B)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xB91D)
                        self._rts();return
                else:
                    if not (yield from self._local_call(self.target_side_filter,0xB911,0xB914)):return
                    self._compare(r.a,0xFF)
                    self._mark(0xB916)
                    if r.p&Z:
                        m[0x0014]=r.y
                        self._a(m[(0x0600+r.y)&65535])
                        m[0x0010]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        m[0x0011]=r.a
                        if not (yield from self._local_call(self.terrain_at_position,0xB92A,0xB92D)):return
                        self._compare(r.a,0x05)
                        self._mark(0xB92F)
                        if r.p&Z:
                            self._mark(0xB949)
                            self._rts();return
                        else:
                            self._y(0x00)
                            while True:  # natural loop $B933
                                self._a(m[(0x6FC9+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xB938)
                                if not r.p&Z:
                                    self._compare(r.a,m[0x0014])
                                    self._mark(0xB942)
                                    if not r.p&Z:
                                        self._y(r.y+1)
                                        continue
                                    else:
                                        self._mark(0xB944)
                                        self._rts();return
                                else:
                                    self._a(m[0x0014])
                                    m[(0x6FC9+r.y)&65535]=r.a
                                    self._mark(0xB93F)
                                    self._rts();return
                    else:
                        self._y(r.y+1)
                        self._compare(r.y,0x14)
                        self._mark(0xB91B)
                        if not r.p&C:
                            continue
                        else:
                            self._mark(0xB91D)
                            self._rts();return

    def withdrawal(self):
        """$B94A: withdrawal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB94A)
        self._a(0x00)
        m[0x00A4]=r.a
        if not (yield from self._local_call(self.local_dc33,0xB94F,0xB952)):return
        self._a(m[PHASE])
        self._mark(0xB955)
        index=self._dispatch(0xB955,(47460, 47469, 47542, 47664, 47716, 47747))
        return (yield from (self.request_retreat,self.select_retreat_answer,self.open_retreat_destination,self.select_retreat_destination,self.commit_retreat,self.acknowledge_retreat,)[index]())

    def request_retreat(self):
        """$B964: request retreat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB964)
        self._a(0xD6)
        yield from self._external(0xB966,0xF283,0xB969,"call",None)
        if r.pc!=0xB969:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xB96C)
        self._rts();return

    def select_retreat_answer(self):
        """$B96D: select retreat answer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB96D)
        if not (yield from self._local_call(self.alternate_highlight,0xB96D,0xB970)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xB970,0xB973)):return
        if not (yield from self._local_call(self.text_readiness,0xB973,0xB976)):return
        self._mark(0xB976)
        if not r.p&C:
            self._mark(0xB9B5)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xB97C)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xB98F)
                if r.p&Z:
                    pass
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0xD7)
                    yield from self._external(0xB996,0xF283,0xB999,"call",None)
                    if r.pc!=0xB999:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    if not (yield from self._local_call(self.local_bb84,0xB9A1,0xB9A4)):return
                    self._a(m[ACTOR_SLOT])
                    self._compare(r.a,0xFF)
                    self._mark(0xB9A9)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x05)
                        m[PHASE]=r.a
                        self._a(0xD9)
                        yield from self._external(0xB9B2,0xF283,0xB9B5,"call",None)
                        if r.pc!=0xB9B5:return  # preserve nonlocal stack return
                        pass
                    pass
                self._mark(0xB9B5)
                self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def open_retreat_destination(self):
        """$B9B6: open retreat destination; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB9B6)
        if not (yield from self._local_call(self.blink_command_cursor,0xB9B6,0xB9B9)):return
        self._a(m[ACTOR_SLOT])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBA9F+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xBAA0+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xB9CC,0xED1E,0xB9CF,"call",None)
        if r.pc!=0xB9CF:return  # preserve nonlocal stack return
        self._a(0x6F)
        m[0x0010]=r.a
        self._a(0xBB)
        m[0x0011]=r.a
        self._a(0x7F)
        m[0x0000]=r.a
        self._a(0xBB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xB9E1,0xEDF5,0xB9E4,"call",None)
        if r.pc!=0xB9E4:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xB9E4,0xB9E7)):return
        self._mark(0xB9E7)
        if not r.p&C:
            self._mark(0xB9B5)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xB9ED)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xBA00)
                if r.p&Z:
                    self._mark(0xBA19)
                    self._rts();return
                else:
                    self._y(m[0x0012])
                    self._a(m[(0x042C+r.y)&65535])
                    m[0x050B]=r.a
                    if not (yield from self._local_call(self.local_bc11,0xBA0A,0xBA0D)):return
                    self._mark(0xBA0D)
                    if not r.p&C:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(m[SELECTED_SLOT])
                        self._mark(0xBA20)
                        if r.p&Z:
                            self._a(0x52)
                            self._mark(0xBA28)
                            yield from self._external(0xBA28,0xF283,None,"tail")
                            return
                        else:
                            self._compare(r.a,0x0A)
                            self._mark(0xBA24)
                            if not r.p&Z:
                                self._a(0xC8)
                                self._mark(0xBA2D)
                                yield from self._external(0xBA2D,0xF283,None,"tail")
                                return
                            else:
                                self._a(0x52)
                                self._mark(0xBA28)
                                yield from self._external(0xBA28,0xF283,None,"tail")
                                return
                    else:
                        self._a(0x01)
                        m[PHASE]=r.a
                        self._a(0xDA)
                        yield from self._external(0xBA16,0xF283,0xBA19,"call",None)
                        if r.pc!=0xBA19:return  # preserve nonlocal stack return
                        self._mark(0xBA19)
                        self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def select_retreat_destination(self):
        """$BA30: select retreat destination; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA30)
        if not (yield from self._local_call(self.alternate_highlight,0xBA30,0xBA33)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xBA33,0xBA36)):return
        if not (yield from self._local_call(self.text_readiness,0xBA36,0xBA39)):return
        self._mark(0xBA39)
        if not r.p&C:
            self._mark(0xBA63)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xBA3F)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xBA52)
                if r.p&Z:
                    pass
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[0x0012]=r.a
                    if not (yield from self._local_call(self.map_refresh,0xBA5B,0xBA5E)):return
                    self._a(0xD8)
                    yield from self._external(0xBA60,0xF293,0xBA63,"call",None)
                    if r.pc!=0xBA63:return  # preserve nonlocal stack return
                    pass
                self._mark(0xBA63)
                self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def commit_retreat(self):
        """$BA64: commit retreat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA64)
        if not (yield from self._local_call(self.text_readiness,0xBA64,0xBA67)):return
        self._mark(0xBA67)
        if not r.p&C:
            self._mark(0xBA82)
            self._rts();return
        else:
            if not (yield from self._local_call(self.alternate_highlight,0xBA69,0xBA6C)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xBA70)
            if r.p&Z:
                self._mark(0xBA82)
                self._rts();return
            else:
                if not (yield from self._local_call(self.local_bc2a,0xBA72,0xBA75)):return
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def acknowledge_retreat(self):
        """$BA83: acknowledge retreat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA83)
        if not (yield from self._local_call(self.text_readiness,0xBA83,0xBA86)):return
        self._mark(0xBA86)
        if not r.p&C:
            self._mark(0xBA9E)
            self._rts();return
        else:
            if not (yield from self._local_call(self.alternate_highlight,0xBA88,0xBA8B)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xBA8F)
            if r.p&Z:
                self._mark(0xBA9E)
                self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def local_bb84(self):
        """$BB84: local bb84; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB84)
        self._a(0xFF)
        m[ACTOR_SLOT]=r.a
        self._y(0x3F)
        self._a(0xFF)
        while True:  # natural loop $BB8D
            m[(0x042C+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xBB91)
            if not r.p&N:
                continue
            else:
                pass
            self._y(0x0F)
            self._a(0xFF)
            while True:  # natural loop $BB97
                m[(0x0550+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xBB9B)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(m[RULERS])
                self._y(m[SIDE])
                self._mark(0xBBA3)
                if not r.p&N:
                    pass
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    pass
                self._a(r.a & 0x0F)
                m[0x0002]=r.a
                self._y(0x30)
                yield from self._external(0xBBAF,0xF25F,0xBBB2,"call",None)
                if r.pc!=0xBBB2:return  # preserve nonlocal stack return
                self._a(m[CITY])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._x(0x00)
                while True:  # natural loop $BBBB
                    self._a(m[(0x9D72+r.y)&65535])
                    self._mark(0xBBBE)
                    if r.p&N:
                        pass
                    else:
                        m[0x0003]=r.a
                        m[0x0004]=r.y
                        if not (yield from self._local_call(self.city_pointer,0xBBC4,0xBBC7)):return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x07)
                        self._compare(r.a,0x07)
                        self._mark(0xBBCF)
                        if r.p&Z:
                            self._a(r.x)
                            self._push(r.a)
                            m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
                            self._y(m[ACTOR_SLOT])
                            self._a(m[0x0003])
                            m[(0x042C+r.y)&65535]=r.a
                            if not (yield from self._local_call(self.local_bc14,0xBBE2,0xBBE5)):return
                            self._y(m[ACTOR_SLOT])
                            self._a(m[(0xBC09+r.y)&65535])
                            self._y(r.a)
                            self._a(0x00)
                            m[(0x042D+r.y)&65535]=r.a
                            m[(0x042E+r.y)&65535]=r.a
                            self._a(r.x)
                            m[(0x042C+r.y)&65535]=r.a
                            self._y(m[ACTOR_SLOT])
                            m[(0x0550+r.y)&65535]=r.a
                            self._a(self._pop())
                            self._x(r.a)
                            pass
                        else:
                            self._compare(r.a,m[0x0002])
                            self._mark(0xBBD3)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(r.x)
                                self._push(r.a)
                                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
                                self._y(m[ACTOR_SLOT])
                                self._a(m[0x0003])
                                m[(0x042C+r.y)&65535]=r.a
                                if not (yield from self._local_call(self.local_bc14,0xBBE2,0xBBE5)):return
                                self._y(m[ACTOR_SLOT])
                                self._a(m[(0xBC09+r.y)&65535])
                                self._y(r.a)
                                self._a(0x00)
                                m[(0x042D+r.y)&65535]=r.a
                                m[(0x042E+r.y)&65535]=r.a
                                self._a(r.x)
                                m[(0x042C+r.y)&65535]=r.a
                                self._y(m[ACTOR_SLOT])
                                m[(0x0550+r.y)&65535]=r.a
                                self._a(self._pop())
                                self._x(r.a)
                                pass
                            pass
                        self._y(m[0x0004])
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._compare(r.x,0x08)
                        self._mark(0xBC06)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        pass
                    self._mark(0xBC08)
                    self._rts();return

    def local_bc11(self):
        """$BC11: local bc11; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC11)
        self._a(m[0x050B])
        return (yield from self.local_bc14())

    def local_bc14(self):
        """$BC14: local bc14; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC14)
        if not (yield from self._local_call(self.city_pointer,0xBC14,0xBC17)):return
        self._y(0x11)
        self._x(0x00)
        while True:  # natural loop $BC1B
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xBC1F)
            if r.p&Z:
                self._flag(C,False)
                self._mark(0xBC29)
                self._rts();return
            else:
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x1B)
                self._mark(0xBC25)
                if not r.p&C:
                    continue
                else:
                    self._mark(0xBC27)
                    self._rts();return

    def local_bc2a(self):
        """$BC2A: local bc2a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC2A)
        if not (yield from self._local_call(self.local_c91e,0xBC2A,0xBC2D)):return
        if not (yield from self._local_call(self.local_bc11,0xBC2D,0xBC30)):return
        self._x(m[SELECTED_SLOT])
        self._mark(0xBC33)
        if r.p&Z:
            self._a(m[(0x0664+r.x)&65535])
            m[0x052B]=r.a
            self._a(m[0x050B])
            m[0x052C]=r.a
            pass
        else:
            self._compare(r.x,0x0A)
            self._mark(0xBC37)
            if not r.p&Z:
                pass
            else:
                self._a(m[(0x0664+r.x)&65535])
                m[0x052B]=r.a
                self._a(m[0x050B])
                m[0x052C]=r.a
                pass
            pass
        self._a(m[(0x0664+r.x)&65535])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(0xFF)
        m[(0x0600+r.x)&65535]=r.a
        m[(0x0614+r.x)&65535]=r.a
        m[(0x0628+r.x)&65535]=r.a
        m[(0x063C+r.x)&65535]=r.a
        m[(0x0650+r.x)&65535]=r.a
        m[(0x0664+r.x)&65535]=r.a
        self._compare(r.x,m[0x04D8])
        self._mark(0xBC61)
        if not r.p&Z:
            pass
        else:
            m[0x04D8]=r.a
            pass
        self._compare(r.x,m[0x04DC])
        self._mark(0xBC69)
        if not r.p&Z:
            pass
        else:
            m[0x04DC]=r.a
            pass
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0x07)
        self._compare(r.a,0x07)
        self._mark(0xBC76)
        if not r.p&Z:
            pass
        else:
            self._a(m[RULERS])
            self._y(m[SIDE])
            self._mark(0xBC7E)
            if not r.p&N:
                pass
            else:
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                pass
            self._a(r.a & 0x0F)
            m[0x0002]=r.a
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0xF0)
            self._a(r.a | m[0x0002])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xBC92)
        self._rts();return

    def wait_action(self):
        """$BC93: wait action; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBC93)
        self._a(m[PHASE])
        self._compare(r.a,0x04)
        self._mark(0xBC98)
        if r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.local_dc33,0xBC9A,0xBC9D)):return
            pass
        self._a(m[PHASE])
        self._mark(0xBCA0)
        index=self._dispatch(0xBCA0,(48307, 48321, 48374, 48403, 48428, 48449, 48495, 48365))
        return (yield from (self.request_wait_action,self.confirm_wait_action,self.prepare_side_notice,self.acknowledge_side_notice,self.refresh_units_for_side,self.inspect_strategy_notice,self.acknowledge_strategy_notice,self.wait_text_then_change_side,)[index]())

    def request_wait_action(self):
        """$BCB3: request wait action; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBCB3)
        self._a(0x00)
        m[0x00A4]=r.a
        self._a(0xCA)
        yield from self._external(0xBCBA,0xF283,0xBCBD,"call",None)
        if r.pc!=0xBCBD:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xBCC0)
        self._rts();return

    def confirm_wait_action(self):
        """$BCC1: confirm wait action; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBCC1)
        if not (yield from self._local_call(self.text_readiness,0xBCC1,0xBCC4)):return
        self._mark(0xBCC4)
        if not r.p&C:
            self._mark(0xBCEC)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xBCC6,0xBCC9)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x02)
            self._mark(0xBCCD)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x01)
                self._mark(0xBCE0)
                if r.p&Z:
                    pass
                else:
                    self._a(0x07)
                    m[PHASE]=r.a
                    self._a(0x05)
                    yield from self._external(0xBCE9,0xF293,0xBCEC,"call",None)
                    if r.pc!=0xBCEC:return  # preserve nonlocal stack return
                    pass
                self._mark(0xBCEC)
                self._rts();return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x00)
                m[STATE]=r.a
                return (yield from self.return_command_cursor())

    def wait_text_then_change_side(self):
        """$BCED: wait text then change side; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBCED)
        if not (yield from self._local_call(self.text_readiness,0xBCED,0xBCF0)):return
        self._mark(0xBCF0)
        if not r.p&C:
            self._mark(0xBCF5)
            self._rts();return
        else:
            return (yield from self.finish_side_turn())

    def prepare_side_notice(self):
        """$BCF6: prepare side notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBCF6)
        self._y(0x3D)
        yield from self._external(0xBCF8,0xEE07,0xBCFD,"far_call",40999)
        if r.pc!=0xBCFD:return  # preserve nonlocal stack return
        self._a(m[0x042C])
        if not (yield from self._local_call(self.ruler_pointer,0xBD00,0xBD03)):return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x042C]=r.a
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(m[ACTOR_SLOT])
        self._mark(0xBD10)
        yield from self._external(0xBD10,0xF283,None,"tail")
        return

    def acknowledge_side_notice(self):
        """$BD13: acknowledge side notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD13)
        if not (yield from self._local_call(self.text_readiness,0xBD13,0xBD16)):return
        self._mark(0xBD16)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xBD18,0xBD1B)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xBD1F)
            if r.p&Z:
                pass
            else:
                self._a(0x0C)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xBD2B)
        self._rts();return

    def refresh_units_for_side(self):
        """$BD2C: refresh units for side; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD2C)
        self._a(0x01)
        m[0x0012]=r.a
        if not (yield from self._local_call(self.map_refresh,0xBD30,0xBD33)):return
        m[SELECTED_SLOT]=self._nz(m[SELECTED_SLOT]+1)
        self._a(m[SELECTED_SLOT])
        self._compare(r.a,0x14)
        self._mark(0xBD3B)
        if not r.p&C:
            pass
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xBD40)
        self._rts();return

    def inspect_strategy_notice(self):
        """$BD41: inspect strategy notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD41)
        self._a(m[0x052E])
        self._mark(0xBD44)
        if not r.p&Z:
            self._y(m[0x052F])
            self._a(m[(0x6FA1+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xBD51)
            if r.p&Z:
                self._a(0x6D)
                m[0x042C]=r.a
                if not (yield from self._local_call(self.local_dee9,0xBD5B,0xBD5E)):return
                self._mark(0xBD5E)
                if r.p&C:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    yield from self._external(0xBD66,0xE57F,0xBD69,"call",None)
                    if r.pc!=0xBD69:return  # preserve nonlocal stack return
                    self._a(0x7B)
                    yield from self._external(0xBD6B,0xE68B,0xBD6E,"call",None)
                    if r.pc!=0xBD6E:return  # preserve nonlocal stack return
                    self._mark(0xBD6E)
                    self._rts();return
                else:
                    self._a(m[0x0470])
                    m[0x0000]=r.a
                    self._a(m[0x0471])
                    m[0x0002]=r.a
                    if not (yield from self._local_call(self.local_da5a,0xBDA1,0xBDA4)):return
                    self._a(m[0x0000])
                    m[0x6F3F]=r.a
                    self._a(m[0x0001])
                    m[0x6F40]=r.a
                    self._a(m[0x0002])
                    m[0x6F41]=r.a
                    self._a(m[0x0003])
                    m[0x6F42]=r.a
                    self._a(0x05)
                    yield from self._external(0xBDBA,0xF293,0xBDBD,"call",None)
                    if r.pc!=0xBDBD:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[PHASE]=r.a
                    m[STATE]=r.a
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    self._mark(0xA21A)
                    self._rts();return
            else:
                self._a(m[0x0470])
                m[0x0000]=r.a
                self._a(m[0x0471])
                m[0x0002]=r.a
                if not (yield from self._local_call(self.local_da5a,0xBDA1,0xBDA4)):return
                self._a(m[0x0000])
                m[0x6F3F]=r.a
                self._a(m[0x0001])
                m[0x6F40]=r.a
                self._a(m[0x0002])
                m[0x6F41]=r.a
                self._a(m[0x0003])
                m[0x6F42]=r.a
                self._a(0x05)
                yield from self._external(0xBDBA,0xF293,0xBDBD,"call",None)
                if r.pc!=0xBDBD:return  # preserve nonlocal stack return
                self._a(0x00)
                m[PHASE]=r.a
                m[STATE]=r.a
                m[0x0424]=r.a
                m[0x0425]=r.a
                self._mark(0xA21A)
                self._rts();return
        else:
            self._a(m[0x0470])
            m[0x0000]=r.a
            self._a(m[0x0471])
            m[0x0002]=r.a
            if not (yield from self._local_call(self.local_da5a,0xBDA1,0xBDA4)):return
            self._a(m[0x0000])
            m[0x6F3F]=r.a
            self._a(m[0x0001])
            m[0x6F40]=r.a
            self._a(m[0x0002])
            m[0x6F41]=r.a
            self._a(m[0x0003])
            m[0x6F42]=r.a
            self._a(0x05)
            yield from self._external(0xBDBA,0xF293,0xBDBD,"call",None)
            if r.pc!=0xBDBD:return  # preserve nonlocal stack return
            self._a(0x00)
            m[PHASE]=r.a
            m[STATE]=r.a
            m[0x0424]=r.a
            m[0x0425]=r.a
            self._mark(0xA21A)
            self._rts();return

    def acknowledge_strategy_notice(self):
        """$BD6F: acknowledge strategy notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD6F)
        if not (yield from self._local_call(self.text_readiness,0xBD6F,0xBD72)):return
        self._mark(0xBD72)
        if not r.p&C:
            self._mark(0xBD8E)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xBD74,0xBD77)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xBD7B)
            if r.p&Z:
                self._mark(0xBD8E)
                self._rts();return
            else:
                self._a(m[0x042D])
                self._compare(r.a,0xFF)
                self._mark(0xBD82)
                if r.p&Z:
                    yield from self._external(0xBD8F,0xE57F,0xBD92,"call",None)
                    if r.pc!=0xBD92:return  # preserve nonlocal stack return
                    self._a(0x1D)
                    yield from self._external(0xBD94,0xE673,0xBD97,"call",None)
                    if r.pc!=0xBD97:return  # preserve nonlocal stack return
                    self._a(m[0x0470])
                    m[0x0000]=r.a
                    self._a(m[0x0471])
                    m[0x0002]=r.a
                    if not (yield from self._local_call(self.local_da5a,0xBDA1,0xBDA4)):return
                    self._a(m[0x0000])
                    m[0x6F3F]=r.a
                    self._a(m[0x0001])
                    m[0x6F40]=r.a
                    self._a(m[0x0002])
                    m[0x6F41]=r.a
                    self._a(m[0x0003])
                    m[0x6F42]=r.a
                    self._a(0x05)
                    yield from self._external(0xBDBA,0xF293,0xBDBD,"call",None)
                    if r.pc!=0xBDBD:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[PHASE]=r.a
                    m[STATE]=r.a
                    m[0x0424]=r.a
                    m[0x0425]=r.a
                    self._mark(0xA21A)
                    self._rts();return
                else:
                    self._a(0xFF)
                    m[0x042D]=r.a
                    self._a(0x4B)
                    self._mark(0xBD8B)
                    yield from self._external(0xBD8B,0xF293,None,"tail")
                    return

    def finish_side_turn(self):
        """$BDC0: finish side turn; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBDC0)
        self._a(m[AP])
        self._mark(0xBDC3)
        if not r.p&N:
            pass
        else:
            self._a(0x00)
            m[AP]=r.a
            pass
        self._a(0x00)
        m[0x6F94]=r.a
        m[0x6F95]=r.a
        m[0x6F96]=r.a
        m[0x052C]=r.a
        m[0x052E]=r.a
        self._a(m[SIDE])
        self._a(r.a ^ 0x80)
        m[SIDE]=r.a
        self._a(r.a & 0x80)
        self._mark(0xBDE5)
        if r.p&Z:
            self._a(m[RULERS])
            self._a(r.a & 0x0F)
            if not (yield from self._local_call(self.ruler_pointer,0xBE38,0xBE3B)):return
            self._y(0x03)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[CONTROLLER]=r.a
            self._a(m[AP])
            m[0x050D]=r.a
            self._a(m[0x050C])
            m[AP]=r.a
            self._a(m[0x0600])
            m[0x0470]=r.a
            self._a(m[0x0614])
            m[0x0471]=r.a
            self._a(m[CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xBE5F)
            if r.p&Z:
                self._y(0x28)
                yield from self._external(0xBE69,0xEE07,0xBE6E,"far_call",40972)
                if r.pc!=0xBE6E:return  # preserve nonlocal stack return
                pass
            else:
                m[0x6F44]=r.a
                pass
            self._a(0x04)
            m[PHASE]=r.a
            self._a(0x07)
            m[STATE]=r.a
            self._a(0x00)
            m[SELECTED_SLOT]=r.a
            self._mark(0xBE7D)
            self._rts();return
        else:
            self._a(m[RULERS])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            if not (yield from self._local_call(self.ruler_pointer,0xBDEE,0xBDF1)):return
            self._y(0x03)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[CONTROLLER]=r.a
            self._a(m[AP])
            m[0x050C]=r.a
            if not (yield from self._local_call(self.local_c5a0,0xBDFE,0xBE01)):return
            m[ROUND]=self._nz(m[ROUND]+1)
            self._a(m[0x050D])
            m[AP]=r.a
            self._y(0x28)
            yield from self._external(0xBE0C,0xEE07,0xBE11,"far_call",40975)
            if r.pc!=0xBE11:return  # preserve nonlocal stack return
            self._a(m[ACTOR_SLOT])
            self._mark(0xBE14)
            if r.p&Z:
                if not (yield from self._local_call(self.refresh_hundred_troops,0xBE21,0xBE24)):return
                self._a(m[0x060A])
                m[0x0470]=r.a
                self._a(m[0x061E])
                m[0x0471]=r.a
                self._a(m[CONTROLLER])
                self._compare(r.a,0x03)
                self._mark(0xBE5F)
                if r.p&Z:
                    self._y(0x28)
                    yield from self._external(0xBE69,0xEE07,0xBE6E,"far_call",40972)
                    if r.pc!=0xBE6E:return  # preserve nonlocal stack return
                    pass
                else:
                    m[0x6F44]=r.a
                    pass
                self._a(0x04)
                m[PHASE]=r.a
                self._a(0x07)
                m[STATE]=r.a
                self._a(0x00)
                m[SELECTED_SLOT]=r.a
                self._mark(0xBE7D)
                self._rts();return
            else:
                self._a(0x07)
                m[STATE]=r.a
                self._a(0x02)
                m[PHASE]=r.a
                self._mark(0xBE20)
                self._rts();return

    def computer_action(self):
        """$BE7E: computer action; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE7E)
        self._a(m[PHASE])
        self._mark(0xBE81)
        index=self._dispatch(0xBE81,(48806, 48826, 48897, 48921, 49020, 49048, 49080, 49116, 49156, 49236, 49277, 49424, 49467, 49481, 49528, 49617, 49643))
        return (yield from (self.request_AI_scan,self.await_AI_proposal,self.route_AI_proposal,self.prepare_AI_movement,self.commit_AI_movement,self.prepare_AI_attack,self.show_AI_attack_target,self.launch_AI_attack,self.prepare_AI_tactic,self.show_AI_tactic_notice,self.apply_AI_tactic,self.show_AI_tactic_actor,self.finish_AI_side,self.prepare_AI_withdrawal,self.show_AI_withdrawal,self.confirm_AI_withdrawal,self.return_from_AI,)[index]())

    def request_AI_scan(self):
        """$BEA6: request AI scan; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBEA6)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBEA9)
        if not r.p&N:
            pass
        else:
            self._a(0x00)
            m[0x6F8B]=r.a
            m[0x6F8D]=r.a
            m[0x6F8E]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xBEB9)
        self._rts();return

    def await_AI_proposal(self):
        """$BEBA: await AI proposal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBEBA)
        self._a(m[0x6F8B])
        self._compare(r.a,0xFF)
        self._mark(0xBEBF)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x6F8F])
            self._compare(r.a,0x03)
            self._mark(0xBEC6)
            if r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            else:
                self._a(m[0x6F8C])
                m[SELECTED_SLOT]=r.a
                self._y(r.a)
                self._a(m[(0x0600+r.y)&65535])
                m[0x0000]=r.a
                self._a(m[(0x0614+r.y)&65535])
                m[0x0002]=r.a
                if not (yield from self._local_call(self.local_da5a,0xBED9,0xBEDC)):return
                self._a(m[0x0000])
                m[0x6F3F]=r.a
                self._a(m[0x0001])
                m[0x6F40]=r.a
                self._a(m[0x0002])
                m[0x6F41]=r.a
                self._a(m[0x0003])
                m[0x6F42]=r.a
                if not (yield from self._local_call(self.cursor_input,0xBEF0,0xBEF3)):return
                self._a(m[0x0508])
                self._mark(0xBEF6)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[PPU_JOBS])
                    self._mark(0xBEFB)
                    if not r.p&Z:
                        pass
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        pass
                    pass
                pass
            pass
        self._mark(0xBF00)
        self._rts();return

    def route_AI_proposal(self):
        """$BF01: route AI proposal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF01)
        self._y(m[0x6F8F])
        self._a(m[(0xBF14+r.y)&65535])
        m[PHASE]=r.a
        self._compare(r.a,0x0C)
        self._mark(0xBF0C)
        if not r.p&Z:
            pass
        else:
            self._a(0x05)
            yield from self._external(0xBF10,0xF293,0xBF13,"call",None)
            if r.pc!=0xBF13:return  # preserve nonlocal stack return
            pass
        self._mark(0xBF13)
        self._rts();return

    def prepare_AI_movement(self):
        """$BF19: prepare AI movement; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF19)
        self._a(m[PPU_JOBS])
        self._mark(0xBF1C)
        if r.p&Z:
            self._a(0x00)
            m[0x0012]=r.a
            if not (yield from self._local_call(self.map_refresh,0xBF23,0xBF26)):return
            self._a(0x00)
            m[0x0000]=r.a
            m[0x0001]=r.a
            self._a(0x01)
            m[0x0002]=r.a
            self._a(m[0x6F8D])
            self._a(r.a & 0x01)
            self._mark(0xBF35)
            if not r.p&Z:
                pass
            else:
                self._a(0xFF)
                m[0x0002]=r.a
                pass
            self._a(m[0x6F8D])
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x01)
            self._a(r.a ^ 0x01)
            self._x(r.a)
            self._a(m[0x0002])
            m[(0x0000+r.x)&65535]=r.a
            self._y(m[SELECTED_SLOT])
            self._a(m[(0x0600+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0000])
            m[(0x0600+r.y)&65535]=r.a
            self._a(m[(0x0614+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0001])
            m[(0x0614+r.y)&65535]=r.a
            self._compare(r.a,0x0F)
            self._mark(0xBF60)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0001])
                self._mark(0xBF64)
                if r.p&N:
                    self._a(m[(0x0614+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    pass
                else:
                    self._a(m[(0x0614+r.y)&65535])
                    self._flag(C,False)
                    self._add(0x01)
                    pass
                m[(0x0614+r.y)&65535]=r.a
                pass
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xBF7B)
            self._rts();return
        else:
            self._mark(0xBF1E)
            self._rts();return

    def commit_AI_movement(self):
        """$BF7C: commit AI movement; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF7C)
        self._a(0x01)
        m[0x0012]=r.a
        if not (yield from self._local_call(self.map_refresh,0xBF80,0xBF83)):return
        self._a(m[AP])
        self._flag(C,True)
        self._add(m[0x6F97],subtract=True)
        m[AP]=r.a
        self._a(0x04)
        m[STATE]=r.a
        self._a(0x02)
        m[PHASE]=r.a
        self._mark(0xBF97)
        self._rts();return

    def prepare_AI_attack(self):
        """$BF98: prepare AI attack; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF98)
        self._a(m[0x6F8D])
        m[SELECTED_SLOT]=r.a
        self._y(0x3D)
        yield from self._external(0xBFA0,0xEE07,0xBFA5,"far_call",40999)
        if r.pc!=0xBFA5:return  # preserve nonlocal stack return
        self._a(0x02)
        m[0x00A4]=r.a
        m[AP]=self._nz(m[AP]-1)
        m[AP]=self._nz(m[AP]-1)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0xA0)
        self._mark(0xBFB5)
        yield from self._external(0xBFB5,0xF283,None,"tail")
        return

    def show_AI_attack_target(self):
        """$BFB8: show AI attack target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFB8)
        self._y(m[0x6F8D])
        if not (yield from self._local_call(self.local_dc36,0xBFBB,0xBFBE)):return
        self._a(m[0x6F8C])
        m[SELECTED_SLOT]=r.a
        if not (yield from self._local_call(self.blink_command_cursor,0xBFC4,0xBFC7)):return
        if not (yield from self._local_call(self.text_readiness,0xBFC7,0xBFCA)):return
        self._mark(0xBFCA)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xBFCC,0xBFCF)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xBFD3)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                yield from self._external(0xBFD8,0xECEE,0xBFDB,"call",None)
                if r.pc!=0xBFDB:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xBFDB)
        self._rts();return

    def launch_AI_attack(self):
        """$BFDC: launch AI attack; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFDC)
        self._y(m[0x6F8D])
        if not (yield from self._local_call(self.local_dc36,0xBFDF,0xBFE2)):return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xBFE5)
        if not r.p&N:
            self._mark(0xC003)
            self._rts();return
        else:
            self._a(m[0x6F8D])
            m[SELECTED_SLOT]=r.a
            self._a(m[0x6F8C])
            m[ACTOR_SLOT]=r.a
            self._a(0x03)
            m[STATE]=r.a
            m[PHASE]=r.a
            self._a(0x00)
            m[0x00A4]=r.a
            return (yield from self.prepare_attack_parameters())

    def prepare_AI_tactic(self):
        """$C004: prepare AI tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC004)
        self._a(m[0x6F8D])
        self._compare(r.a,0x0B)
        self._mark(0xC009)
        if not r.p&Z:
            self._a(m[0x6F8E])
            m[SELECTED_SLOT]=r.a
            self._y(0x3D)
            yield from self._external(0xC016,0xEE07,0xC01B,"far_call",40999)
            if r.pc!=0xC01B:return  # preserve nonlocal stack return
            self._y(m[0x6F8D])
            self._a(m[AP])
            self._flag(C,True)
            self._add(m[(0xC044+r.y)&65535],subtract=True)
            m[AP]=r.a
            self._a(m[0x6F8D])
            m[0x042C]=r.a
            self._a(0x00)
            m[0x042D]=r.a
            m[0x042E]=r.a
            self._a(0xA1)
            yield from self._external(0xC038,0xF283,0xC03B,"call",None)
            if r.pc!=0xC03B:return  # preserve nonlocal stack return
            self._a(0x65)
            yield from self._external(0xC03D,0xE69B,0xC040,"call",None)
            if r.pc!=0xC040:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xC043)
            self._rts();return
        else:
            self._a(m[0x6F8D])
            m[TACTIC]=r.a
            self._a(m[0x6F8C])
            m[SELECTED_SLOT]=r.a
            m[ACTOR_SLOT]=r.a
            if not (yield from self._local_call(self.apply_tactic,0xC1BE,0xC1C1)):return
            if not (yield from self._local_call(self.refresh_hundred_troops,0xC1C1,0xC1C4)):return
            self._a(0x01)
            m[0x0012]=r.a
            if not (yield from self._local_call(self.map_refresh,0xC1C8,0xC1CB)):return
            if not (yield from self._local_call(self.return_command_cursor,0xC1CB,0xC1CE)):return
            self._a(0x00)
            m[STATE]=r.a
            m[PHASE]=r.a
            m[0x00A4]=r.a
            self._mark(0xC1FB)
            self._rts();return

    def show_AI_tactic_notice(self):
        """$C054: show AI tactic notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC054)
        m[0x042D]=self._nz(m[0x042D]+1)
        self._a(0x00)
        m[0x00A4]=r.a
        self._y(m[0x6F8E])
        if not (yield from self._local_call(self.local_dc36,0xC05F,0xC062)):return
        self._a(m[0x6F8C])
        m[SELECTED_SLOT]=r.a
        if not (yield from self._local_call(self.blink_command_cursor,0xC068,0xC06B)):return
        if not (yield from self._local_call(self.text_readiness,0xC06B,0xC06E)):return
        self._mark(0xC06E)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC070,0xC073)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC077)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xC07C)
        self._rts();return

    def apply_AI_tactic(self):
        """$C07D: apply AI tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC07D)
        self._y(m[0x6F8E])
        if not (yield from self._local_call(self.local_dc36,0xC080,0xC083)):return
        self._a(m[0x6F8D])
        m[TACTIC]=r.a
        self._a(m[0x6F8C])
        m[ACTOR_SLOT]=r.a
        self._a(m[0x6F8E])
        m[SELECTED_SLOT]=r.a
        self._y(m[SELECTED_SLOT])
        self._a(0x00)
        m[(0x0650+r.y)&65535]=r.a
        if not (yield from self._local_call(self.apply_tactic,0xC09D,0xC0A0)):return
        if not (yield from self._local_call(self.refresh_hundred_troops,0xC0A0,0xC0A3)):return
        self._a(0x01)
        m[0x0012]=r.a
        if not (yield from self._local_call(self.map_refresh,0xC0A7,0xC0AA)):return
        self._a(0x0B)
        m[PHASE]=r.a
        self._a(m[TACTIC_FAILED])
        self._mark(0xC0B2)
        if r.p&Z:
            self._a(0x04)
            m[0x00A4]=r.a
            self._a(m[TACTIC])
            self._a(r.a & 0x0F)
            self._y(r.a)
            self._compare(r.y,0x08)
            self._mark(0xC0CB)
            if r.p&Z:
                self._a(0xB7)
                self._mark(0xC0FD)
                yield from self._external(0xC0FD,0xF293,None,"tail")
                return
            else:
                self._compare(r.y,0x01)
                self._mark(0xC0CF)
                if r.p&Z:
                    self._a(m[0x0432])
                    self._compare(r.a,0xFF)
                    self._mark(0xC0E6)
                    if r.p&Z:
                        self._a(m[(0xC100+r.y)&65535])
                        self._mark(0xC0F8)
                        yield from self._external(0xC0F8,0xF283,None,"tail")
                        return
                    else:
                        m[0x042C]=r.a
                        self._a(0x0F)
                        m[PHASE]=r.a
                        self._a(0x4E)
                        self._mark(0xC0F2)
                        yield from self._external(0xC0F2,0xF293,None,"tail")
                        return
                else:
                    self._compare(r.y,0x09)
                    self._mark(0xC0D3)
                    if not r.p&Z:
                        self._a(m[(0xC100+r.y)&65535])
                        self._mark(0xC0F8)
                        yield from self._external(0xC0F8,0xF283,None,"tail")
                        return
                    else:
                        self._a(m[0x042C])
                        self._mark(0xC0D8)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x042D])
                            self._mark(0xC0DD)
                            if not r.p&Z:
                                pass
                            else:
                                self._y(0x01)
                                pass
                            pass
                        self._a(m[0x0432])
                        self._compare(r.a,0xFF)
                        self._mark(0xC0E6)
                        if r.p&Z:
                            self._a(m[(0xC100+r.y)&65535])
                            self._mark(0xC0F8)
                            yield from self._external(0xC0F8,0xF283,None,"tail")
                            return
                        else:
                            m[0x042C]=r.a
                            self._a(0x0F)
                            m[PHASE]=r.a
                            self._a(0x4E)
                            self._mark(0xC0F2)
                            yield from self._external(0xC0F2,0xF293,None,"tail")
                            return
        else:
            self._a(0x03)
            m[0x00A4]=r.a
            self._a(0xA2)
            self._mark(0xC0BB)
            yield from self._external(0xC0BB,0xF283,None,"tail")
            return

    def show_AI_tactic_actor(self):
        """$C110: show AI tactic actor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC110)
        self._y(m[0x6F8E])
        if not (yield from self._local_call(self.local_dc36,0xC113,0xC116)):return
        self._a(m[0x6F8C])
        m[SELECTED_SLOT]=r.a
        if not (yield from self._local_call(self.blink_command_cursor,0xC11C,0xC11F)):return
        if not (yield from self._local_call(self.text_readiness,0xC11F,0xC122)):return
        self._mark(0xC122)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC124,0xC127)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC12B)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.return_command_cursor,0xC12D,0xC130)):return
                self._a(0x05)
                yield from self._external(0xC132,0xF293,0xC135,"call",None)
                if r.pc!=0xC135:return  # preserve nonlocal stack return
                self._a(0x10)
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xC13A)
        self._rts();return

    def finish_AI_side(self):
        """$C13B: finish AI side; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC13B)
        if not (yield from self._local_call(self.text_readiness,0xC13B,0xC13E)):return
        self._mark(0xC13E)
        if not r.p&C:
            self._mark(0xC13A)
            self._rts();return
        else:
            self._a(m[0x6F8C])
            m[SELECTED_SLOT]=r.a
            return (yield from self.finish_side_turn())

    def prepare_AI_withdrawal(self):
        """$C149: prepare AI withdrawal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC149)
        self._y(0x00)
        self._a(m[SIDE])
        self._mark(0xC14E)
        if r.p&N:
            pass
        else:
            self._y(0x0A)
            pass
        self._a(r.y)
        m[SELECTED_SLOT]=r.a
        self._y(0x3D)
        yield from self._external(0xC158,0xEE07,0xC15D,"far_call",40999)
        if r.pc!=0xC15D:return  # preserve nonlocal stack return
        self._a(m[SELECTED_SLOT])
        m[ACTOR_SLOT]=r.a
        self._a(m[0x6F8C])
        m[SELECTED_SLOT]=r.a
        self._y(r.a)
        self._a(m[(0x0664+r.y)&65535])
        m[0x042C]=r.a
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0xBD)
        self._mark(0xC175)
        yield from self._external(0xC175,0xF283,None,"tail")
        return

    def show_AI_withdrawal(self):
        """$C178: show AI withdrawal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC178)
        self._a(0x00)
        m[0x00A4]=r.a
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.local_dc36,0xC180,0xC183)):return
        if not (yield from self._local_call(self.blink_command_cursor,0xC183,0xC186)):return
        if not (yield from self._local_call(self.text_readiness,0xC186,0xC189)):return
        self._mark(0xC189)
        if not r.p&C:
            self._mark(0xC13A)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC18B,0xC18E)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC192)
            if r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x0012]=r.a
                if not (yield from self._local_call(self.map_refresh,0xC198,0xC19B)):return
                self._a(m[0x6F8D])
                m[0x050B]=r.a
                if not (yield from self._local_call(self.local_bc2a,0xC1A1,0xC1A4)):return
                self._a(0x05)
                yield from self._external(0xC1A6,0xF293,0xC1A9,"call",None)
                if r.pc!=0xC1A9:return  # preserve nonlocal stack return
                self._a(0x10)
                m[PHASE]=r.a
                pass
            self._mark(0xC1AE)
            self._rts();return

    def confirm_AI_withdrawal(self):
        """$C1D1: confirm AI withdrawal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1D1)
        if not (yield from self._local_call(self.text_readiness,0xC1D1,0xC1D4)):return
        self._mark(0xC1D4)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC1D6,0xC1D9)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC1DD)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.return_command_cursor,0xC1DF,0xC1E2)):return
                self._a(0x05)
                yield from self._external(0xC1E4,0xF293,0xC1E7,"call",None)
                if r.pc!=0xC1E7:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xC1EA)
        self._rts();return

    def return_from_AI(self):
        """$C1EB: return from AI; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1EB)
        if not (yield from self._local_call(self.text_readiness,0xC1EB,0xC1EE)):return
        self._mark(0xC1EE)
        if not r.p&C:
            pass
        else:
            self._a(0x00)
            m[STATE]=r.a
            m[PHASE]=r.a
            m[0x00A4]=r.a
            pass
        self._mark(0xC1FB)
        self._rts();return

    def village_service(self):
        """$C1FC: village service; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1FC)
        self._y(0x28)
        yield from self._external(0xC1FE,0xEE07,0xC203,"far_call",40969)
        if r.pc!=0xC203:return  # preserve nonlocal stack return
        self._mark(0xC203)
        self._rts();return

    def next_side(self):
        """$C204: next side; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC204)
        self._a(m[PHASE])
        self._mark(0xC207)
        index=self._dispatch(0xC207,(49688, 49743, 49802, 49869, 49911, 49934, 50000))
        return (yield from (self.prepare_next_side,self.prepare_first_side_control,self.prepare_second_side_control,self.enter_unit_selection,self.acknowledge_next_side_notice,self.scan_next_officer,self.draw_next_officer_notice,)[index]())

    def prepare_next_side(self):
        """$C218: prepare next side; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC218)
        if not (yield from self._local_call(self.round_resource_update,0xC218,0xC21B)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(m[0x060A])
        m[0x0000]=r.a
        self._a(m[0x061E])
        m[0x0002]=r.a
        if not (yield from self._local_call(self.local_da5a,0xC228,0xC22B)):return
        self._a(m[0x0000])
        m[0x6F3F]=r.a
        self._a(m[0x0001])
        m[0x6F40]=r.a
        self._a(m[0x0002])
        m[0x6F41]=r.a
        self._a(m[0x0003])
        m[0x6F42]=r.a
        if not (yield from self._local_call(self.local_c5a0,0xC23F,0xC242)):return
        m[ROUND]=self._nz(m[ROUND]+1)
        self._a(m[0x050D])
        m[AP]=r.a
        if not (yield from self._local_call(self.local_dc1e,0xC24B,0xC24E)):return
        self._mark(0xC24E)
        self._rts();return

    def prepare_first_side_control(self):
        """$C24F: prepare first side control; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC24F)
        self._a(m[RULERS])
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.ruler_pointer,0xC254,0xC257)):return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x03)
        self._mark(0xC25D)
        if r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xC289)
            self._rts();return
        else:
            m[0x6F44]=r.a
            self._a(0x04)
            m[PHASE]=r.a
            self._a(0x02)
            m[0x050B]=r.a
            self._a(0x00)
            m[SELECTED_SLOT]=r.a
            self._a(0xF9)
            yield from self._external(0xC273,0xF293,0xC276,"call",None)
            if r.pc!=0xC276:return  # preserve nonlocal stack return
            self._a(m[RULERS])
            self._a(r.a & 0x0F)
            if not (yield from self._local_call(self.ruler_pointer,0xC27B,0xC27E)):return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._mark(0xC285)
            self._rts();return

    def prepare_second_side_control(self):
        """$C28A: prepare second side control; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC28A)
        self._a(m[RULERS])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.ruler_pointer,0xC293,0xC296)):return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x03)
        self._mark(0xC29C)
        if r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xC2CC)
            self._rts();return
        else:
            m[0x6F44]=r.a
            self._a(0x04)
            m[PHASE]=r.a
            self._a(0x03)
            m[0x050B]=r.a
            self._a(0x0A)
            m[SELECTED_SLOT]=r.a
            self._a(0xF9)
            yield from self._external(0xC2B2,0xF293,0xC2B5,"call",None)
            if r.pc!=0xC2B5:return  # preserve nonlocal stack return
            self._a(m[RULERS])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a & 0x0F)
            if not (yield from self._local_call(self.ruler_pointer,0xC2BE,0xC2C1)):return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x042C]=r.a
            self._mark(0xC2C8)
            self._rts();return

    def enter_unit_selection(self):
        """$C2CD: enter unit selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC2CD)
        self._a(0x00)
        m[STATE]=r.a
        self._a(0x00)
        m[PHASE]=r.a
        m[0x0508]=r.a
        m[SELECTED_SLOT]=r.a
        m[ACTOR_SLOT]=r.a
        m[0x050B]=r.a
        self._a(m[RULERS])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.ruler_pointer,0xC2EC,0xC2EF)):return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[CONTROLLER]=r.a
        self._mark(0xC2F6)
        self._rts();return

    def acknowledge_next_side_notice(self):
        """$C2F7: acknowledge next side notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC2F7)
        if not (yield from self._local_call(self.text_readiness,0xC2F7,0xC2FA)):return
        self._mark(0xC2FA)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC2FC,0xC2FF)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xC303)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xFF)
                m[ACTOR_SLOT]=r.a
                pass
            pass
        self._mark(0xC30D)
        self._rts();return

    def scan_next_officer(self):
        """$C30E: scan next officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $C30E
            self._mark(0xC30E)
            m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
            self._a(m[ACTOR_SLOT])
            self._compare(r.a,0x0A)
            self._mark(0xC316)
            if not r.p&C:
                self._y(m[SELECTED_SLOT])
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC330)
                if not r.p&Z:
                    m[0x0410]=r.a
                    self._a(0x08)
                    m[0x00BA]=r.a
                    self._a(0x00)
                    m[0x040C]=r.a
                    self._a(0x00)
                    m[0x040D]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.local_c3cb,0xC34C,0xC34F)):return
                    self._mark(0xC34F)
                    self._rts();return
                else:
                    m[SELECTED_SLOT]=self._nz(m[SELECTED_SLOT]+1)
                    continue
            else:
                self._a(0x09)
                m[0x00BB]=r.a
                self._a(m[0x050B])
                m[PHASE]=r.a
                self._a(0x05)
                self._mark(0xC324)
                yield from self._external(0xC324,0xF293,None,"tail")
                return

    def draw_next_officer_notice(self):
        """$C350: draw next officer notice; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC350)
        self._a(0xA7)
        m[0x000A]=r.a
        self._a(m[0x0410])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x00A4]=r.a
        self._y(0x39)
        yield from self._external(0xC360,0xEE07,0xC365,"far_call",40960)
        if r.pc!=0xC365:return  # preserve nonlocal stack return
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0002]=r.a
        if not (yield from self._local_call(self.local_da5a,0xC372,0xC375)):return
        self._a(m[0x0000])
        m[0x6F3F]=r.a
        self._a(m[0x0001])
        m[0x6F40]=r.a
        self._a(m[0x0002])
        m[0x6F41]=r.a
        self._a(m[0x0003])
        m[0x6F42]=r.a
        if not (yield from self._local_call(self.cursor_input,0xC389,0xC38C)):return
        self._a(m[0x0508])
        self._mark(0xC38F)
        if not r.p&Z:
            pass
        else:
            self._a(m[PPU_JOBS])
            self._mark(0xC394)
            if not r.p&Z:
                pass
            else:
                self._a(0x06)
                m[0x00BB]=r.a
                self._y(0x39)
                yield from self._external(0xC39C,0xEE07,0xC3A1,"far_call",40978)
                if r.pc!=0xC3A1:return  # preserve nonlocal stack return
                if not (yield from self._local_call(self.blink_command_cursor,0xC3A1,0xC3A4)):return
                self._a(m[0x040D])
                self._compare(r.a,0xFF)
                self._mark(0xC3A9)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.local_c4b1,0xC3AB,0xC3AE)):return
                    if not (yield from self._local_call(self.text_readiness,0xC3AE,0xC3B1)):return
                    self._mark(0xC3B1)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[NEW_BUTTONS])
                        self._compare(r.a,0x10)
                        self._mark(0xC3B7)
                        if r.p&C:
                            pass
                        else:
                            self._a(r.a & 0x01)
                            self._mark(0xC3BB)
                            if r.p&Z:
                                pass
                            else:
                                m[PHASE]=self._nz(m[PHASE]-1)
                                self._a(0x01)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xC3C4,0xC3C7)):return
                                m[SELECTED_SLOT]=self._nz(m[SELECTED_SLOT]+1)
                                pass
                            pass
                        pass
                    pass
                pass
            pass
        self._mark(0xC3CA)
        self._rts();return

    def local_c3cb(self):
        """$C3CB: local c3cb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3CB)
        self._a(m[0x050B])
        self._compare(r.a,0x02)
        self._mark(0xC3D0)
        if not r.p&Z:
            if not (yield from self._local_call(self.local_de9e,0xC41C,0xC41F)):return
            m[0x0018]=r.a
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._flag(C,False)
            self._add(m[0x0018])
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0018]=r.a
            self._y(0x26)
            yield from self._external(0xC42D,0xF25F,0xC430,"call",None)
            if r.pc!=0xC430:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x8000+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0018])
            m[0x0010]=r.a
            self._a(m[(0x8001+r.y)&65535])
            self._add(0x00)
            m[0x0011]=r.a
            pass
        else:
            if not (yield from self._local_call(self.local_debf,0xC3D2,0xC3D5)):return
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0018]=r.a
            self._y(0x26)
            yield from self._external(0xC3DE,0xF25F,0xC3E1,"call",None)
            if r.pc!=0xC3E1:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x8C52+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0018])
            m[0x0010]=r.a
            self._a(m[(0x8C53+r.y)&65535])
            self._add(0x00)
            m[0x0011]=r.a
            pass
        self._y(0x00)
        while True:  # natural loop $C3F7
            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
            m[0x0001]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
            m[0x0000]=r.a
            self._y(r.y+1)
            m[0x0012]=r.y
            if not (yield from self._local_call(self.local_d6b6,0xC403,0xC406)):return
            self._a(r.y)
            self._mark(0xC407)
            if r.p&N:
                pass
            else:
                self._y(m[0x0012])
                continue
            self._y(m[SELECTED_SLOT])
            self._a(m[0x0000])
            m[(0x0600+r.y)&65535]=r.a
            self._a(m[0x0001])
            m[(0x0614+r.y)&65535]=r.a
            self._mark(0xC41B)
            self._rts();return

    def local_c447(self):
        """$C447: local c447; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC447)
        self._a(m[0x050B])
        self._compare(r.a,0x02)
        self._mark(0xC44C)
        if not r.p&Z:
            if not (yield from self._local_call(self.local_de9e,0xC48E,0xC491)):return
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0018]=r.a
            self._y(0x26)
            yield from self._external(0xC497,0xF25F,0xC49A,"call",None)
            if r.pc!=0xC49A:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x932E+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0018])
            m[0x0010]=r.a
            self._a(m[(0x932F+r.y)&65535])
            self._add(0x00)
            m[0x0011]=r.a
            pass
        else:
            if not (yield from self._local_call(self.local_debf,0xC44E,0xC451)):return
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0018]=r.a
            self._y(0x26)
            yield from self._external(0xC457,0xF25F,0xC45A,"call",None)
            if r.pc!=0xC45A:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x94D6+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0018])
            m[0x0010]=r.a
            self._a(m[(0x94D7+r.y)&65535])
            self._add(0x00)
            m[0x0011]=r.a
            pass
        self._y(0x00)
        self._a(m[0x0001])
        self._compare(r.a,m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
        self._mark(0xC474)
        if not r.p&C:
            self._flag(C,False)
            self._mark(0xC48D)
            self._rts();return
        else:
            self._y(0x02)
            self._compare(r.a,m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
            self._mark(0xC47A)
            if r.p&C:
                self._flag(C,False)
                self._mark(0xC48D)
                self._rts();return
            else:
                self._y(0x01)
                self._a(m[0x0000])
                self._compare(r.a,m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                self._mark(0xC482)
                if not r.p&C:
                    self._flag(C,False)
                    self._mark(0xC48D)
                    self._rts();return
                else:
                    self._y(0x03)
                    self._compare(r.a,m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                    self._mark(0xC488)
                    if r.p&C:
                        self._flag(C,False)
                        self._mark(0xC48D)
                        self._rts();return
                    else:
                        self._flag(C,True)
                        self._mark(0xC48B)
                        self._rts();return

    def local_c4b1(self):
        """$C4B1: local c4b1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC4B1)
        self._a(m[0x040D])
        self._compare(r.a,0xFF)
        self._mark(0xC4B6)
        if r.p&Z:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xC4BC)
            if not r.p&N:
                self._a(m[NEW_BUTTONS])
                self._mark(0xC4EB)
                if not r.p&N:
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._mark(0xC51F)
                    if not r.p&N:
                        pass
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x01,subtract=True)
                        self._mark(0xC52F)
                        if r.p&N:
                            pass
                        else:
                            self._compare(r.a,0x0F)
                            self._mark(0xC533)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                pass
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                            self._a(r.y)
                            self._mark(0xC53E)
                            if not r.p&N:
                                pass
                            else:
                                if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                self._mark(0xC543)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                    self._a(m[(0x0614+r.x)&65535])
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC557)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._mark(0xC560)
                    if not r.p&N:
                        pass
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x14)
                        self._mark(0xC572)
                        if r.p&C:
                            pass
                        else:
                            self._compare(r.a,0x0F)
                            self._mark(0xC576)
                            if not r.p&Z:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                            self._a(r.y)
                            self._mark(0xC581)
                            if not r.p&N:
                                pass
                            else:
                                if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                self._mark(0xC586)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                    self._a(m[(0x0614+r.x)&65535])
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC59A)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    self._mark(0xC59F)
                    self._rts();return
                else:
                    self._y(m[SELECTED_SLOT])
                    self._a(m[(0x0600+r.y)&65535])
                    self._flag(C,False)
                    self._add(0x01)
                    self._compare(r.a,0x1F)
                    self._mark(0xC4F8)
                    if r.p&C:
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC51F)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._mark(0xC52F)
                            if r.p&N:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xC533)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                self._a(r.y)
                                self._mark(0xC53E)
                                if not r.p&N:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                    self._mark(0xC543)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC557)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC560)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x14)
                            self._mark(0xC572)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xC576)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                self._a(r.y)
                                self._mark(0xC581)
                                if not r.p&N:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                    self._mark(0xC586)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC59A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xC59F)
                        self._rts();return
                    else:
                        m[0x0000]=r.a
                        self._a(m[(0x0614+r.y)&65535])
                        m[0x0001]=r.a
                        if not (yield from self._local_call(self.local_d6b6,0xC501,0xC504)):return
                        self._a(r.y)
                        self._mark(0xC505)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC51F)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xC52F)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC533)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                    self._a(r.y)
                                    self._mark(0xC53E)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                        self._mark(0xC543)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC557)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC560)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xC572)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC576)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                    self._a(r.y)
                                    self._mark(0xC581)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                        self._mark(0xC586)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC59A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xC59F)
                            self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_c447,0xC507,0xC50A)):return
                            self._mark(0xC50A)
                            if not r.p&C:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC51F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xC52F)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC533)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                        self._a(r.y)
                                        self._mark(0xC53E)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                            self._mark(0xC543)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC557)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC560)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xC572)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC576)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                        self._a(r.y)
                                        self._mark(0xC581)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                            self._mark(0xC586)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC59A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xC59F)
                                self._rts();return
                            else:
                                self._a(0x00)
                                m[0x0012]=r.a
                                if not (yield from self._local_call(self.map_refresh,0xC510,0xC513)):return
                                self._x(m[SELECTED_SLOT])
                                m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                self._mark(0xC519)
                                self._rts();return
            else:
                self._y(m[SELECTED_SLOT])
                self._a(m[(0x0600+r.y)&65535])
                self._flag(C,True)
                self._add(0x01,subtract=True)
                self._mark(0xC4C7)
                if not r.p&C:
                    self._a(m[NEW_BUTTONS])
                    self._mark(0xC4EB)
                    if not r.p&N:
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC51F)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            self._mark(0xC52F)
                            if r.p&N:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xC533)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                self._a(r.y)
                                self._mark(0xC53E)
                                if not r.p&N:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                    self._mark(0xC543)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC557)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xC560)
                        if not r.p&N:
                            pass
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x14)
                            self._mark(0xC572)
                            if r.p&C:
                                pass
                            else:
                                self._compare(r.a,0x0F)
                                self._mark(0xC576)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x01)
                                    pass
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                self._a(r.y)
                                self._mark(0xC581)
                                if not r.p&N:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                    self._mark(0xC586)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                        self._a(m[(0x0614+r.x)&65535])
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC59A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xC59F)
                        self._rts();return
                    else:
                        self._y(m[SELECTED_SLOT])
                        self._a(m[(0x0600+r.y)&65535])
                        self._flag(C,False)
                        self._add(0x01)
                        self._compare(r.a,0x1F)
                        self._mark(0xC4F8)
                        if r.p&C:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC51F)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xC52F)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC533)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                    self._a(r.y)
                                    self._mark(0xC53E)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                        self._mark(0xC543)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC557)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC560)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xC572)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC576)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                    self._a(r.y)
                                    self._mark(0xC581)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                        self._mark(0xC586)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC59A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xC59F)
                            self._rts();return
                        else:
                            m[0x0000]=r.a
                            self._a(m[(0x0614+r.y)&65535])
                            m[0x0001]=r.a
                            if not (yield from self._local_call(self.local_d6b6,0xC501,0xC504)):return
                            self._a(r.y)
                            self._mark(0xC505)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC51F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xC52F)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC533)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                        self._a(r.y)
                                        self._mark(0xC53E)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                            self._mark(0xC543)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC557)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC560)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xC572)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC576)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                        self._a(r.y)
                                        self._mark(0xC581)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                            self._mark(0xC586)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC59A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xC59F)
                                self._rts();return
                            else:
                                if not (yield from self._local_call(self.local_c447,0xC507,0xC50A)):return
                                self._mark(0xC50A)
                                if not r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC51F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xC52F)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC533)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                            self._a(r.y)
                                            self._mark(0xC53E)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                self._mark(0xC543)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC557)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC560)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xC572)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC576)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                            self._a(r.y)
                                            self._mark(0xC581)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                self._mark(0xC586)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC59A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xC59F)
                                    self._rts();return
                                else:
                                    self._a(0x00)
                                    m[0x0012]=r.a
                                    if not (yield from self._local_call(self.map_refresh,0xC510,0xC513)):return
                                    self._x(m[SELECTED_SLOT])
                                    m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                    self._mark(0xC519)
                                    self._rts();return
                else:
                    m[0x0000]=r.a
                    self._a(m[(0x0614+r.y)&65535])
                    m[0x0001]=r.a
                    if not (yield from self._local_call(self.local_d6b6,0xC4D0,0xC4D3)):return
                    self._a(r.y)
                    self._mark(0xC4D4)
                    if not r.p&N:
                        self._a(m[NEW_BUTTONS])
                        self._mark(0xC4EB)
                        if not r.p&N:
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC51F)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,True)
                                self._add(0x01,subtract=True)
                                self._mark(0xC52F)
                                if r.p&N:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC533)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                    self._a(r.y)
                                    self._mark(0xC53E)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                        self._mark(0xC543)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC557)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._a(m[NEW_BUTTONS])
                            r.a=self._shift(r.a,True,rotate=False)
                            r.a=self._shift(r.a,True,rotate=False)
                            self._mark(0xC560)
                            if not r.p&N:
                                pass
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x14)
                                self._mark(0xC572)
                                if r.p&C:
                                    pass
                                else:
                                    self._compare(r.a,0x0F)
                                    self._mark(0xC576)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x01)
                                        pass
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                    self._a(r.y)
                                    self._mark(0xC581)
                                    if not r.p&N:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                        self._mark(0xC586)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                            self._a(m[(0x0614+r.x)&65535])
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC59A)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            self._mark(0xC59F)
                            self._rts();return
                        else:
                            self._y(m[SELECTED_SLOT])
                            self._a(m[(0x0600+r.y)&65535])
                            self._flag(C,False)
                            self._add(0x01)
                            self._compare(r.a,0x1F)
                            self._mark(0xC4F8)
                            if r.p&C:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC51F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xC52F)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC533)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                        self._a(r.y)
                                        self._mark(0xC53E)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                            self._mark(0xC543)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC557)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC560)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xC572)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC576)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                        self._a(r.y)
                                        self._mark(0xC581)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                            self._mark(0xC586)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC59A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xC59F)
                                self._rts();return
                            else:
                                m[0x0000]=r.a
                                self._a(m[(0x0614+r.y)&65535])
                                m[0x0001]=r.a
                                if not (yield from self._local_call(self.local_d6b6,0xC501,0xC504)):return
                                self._a(r.y)
                                self._mark(0xC505)
                                if not r.p&N:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC51F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xC52F)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC533)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                            self._a(r.y)
                                            self._mark(0xC53E)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                self._mark(0xC543)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC557)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC560)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xC572)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC576)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                            self._a(r.y)
                                            self._mark(0xC581)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                self._mark(0xC586)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC59A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xC59F)
                                    self._rts();return
                                else:
                                    if not (yield from self._local_call(self.local_c447,0xC507,0xC50A)):return
                                    self._mark(0xC50A)
                                    if not r.p&C:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xC51F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xC52F)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC533)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                                self._a(r.y)
                                                self._mark(0xC53E)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                    self._mark(0xC543)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xC557)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xC560)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xC572)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC576)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                                self._a(r.y)
                                                self._mark(0xC581)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                    self._mark(0xC586)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xC59A)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xC59F)
                                        self._rts();return
                                    else:
                                        self._a(0x00)
                                        m[0x0012]=r.a
                                        if not (yield from self._local_call(self.map_refresh,0xC510,0xC513)):return
                                        self._x(m[SELECTED_SLOT])
                                        m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                        self._mark(0xC519)
                                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.local_c447,0xC4D6,0xC4D9)):return
                        self._mark(0xC4D9)
                        if not r.p&C:
                            self._a(m[NEW_BUTTONS])
                            self._mark(0xC4EB)
                            if not r.p&N:
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC51F)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    self._mark(0xC52F)
                                    if r.p&N:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC533)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                        self._a(r.y)
                                        self._mark(0xC53E)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                            self._mark(0xC543)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC557)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._a(m[NEW_BUTTONS])
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._mark(0xC560)
                                if not r.p&N:
                                    pass
                                else:
                                    self._y(m[SELECTED_SLOT])
                                    self._a(m[(0x0600+r.y)&65535])
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(0x01)
                                    self._compare(r.a,0x14)
                                    self._mark(0xC572)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,0x0F)
                                        self._mark(0xC576)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x01)
                                            pass
                                        m[0x0001]=r.a
                                        if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                        self._a(r.y)
                                        self._mark(0xC581)
                                        if not r.p&N:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                            self._mark(0xC586)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x00)
                                                m[0x0012]=r.a
                                                if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                self._x(m[SELECTED_SLOT])
                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                self._a(m[(0x0614+r.x)&65535])
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC59A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    pass
                                                pass
                                            pass
                                        pass
                                    pass
                                self._mark(0xC59F)
                                self._rts();return
                            else:
                                self._y(m[SELECTED_SLOT])
                                self._a(m[(0x0600+r.y)&65535])
                                self._flag(C,False)
                                self._add(0x01)
                                self._compare(r.a,0x1F)
                                self._mark(0xC4F8)
                                if r.p&C:
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC51F)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x01,subtract=True)
                                        self._mark(0xC52F)
                                        if r.p&N:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC533)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                            self._a(r.y)
                                            self._mark(0xC53E)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                self._mark(0xC543)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC557)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._a(m[NEW_BUTTONS])
                                    r.a=self._shift(r.a,True,rotate=False)
                                    r.a=self._shift(r.a,True,rotate=False)
                                    self._mark(0xC560)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._y(m[SELECTED_SLOT])
                                        self._a(m[(0x0600+r.y)&65535])
                                        m[0x0000]=r.a
                                        self._a(m[(0x0614+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(0x01)
                                        self._compare(r.a,0x14)
                                        self._mark(0xC572)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._compare(r.a,0x0F)
                                            self._mark(0xC576)
                                            if not r.p&Z:
                                                pass
                                            else:
                                                self._flag(C,False)
                                                self._add(0x01)
                                                pass
                                            m[0x0001]=r.a
                                            if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                            self._a(r.y)
                                            self._mark(0xC581)
                                            if not r.p&N:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                self._mark(0xC586)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0012]=r.a
                                                    if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                    self._x(m[SELECTED_SLOT])
                                                    m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                    self._a(m[(0x0614+r.x)&65535])
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC59A)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        pass
                                    self._mark(0xC59F)
                                    self._rts();return
                                else:
                                    m[0x0000]=r.a
                                    self._a(m[(0x0614+r.y)&65535])
                                    m[0x0001]=r.a
                                    if not (yield from self._local_call(self.local_d6b6,0xC501,0xC504)):return
                                    self._a(r.y)
                                    self._mark(0xC505)
                                    if not r.p&N:
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xC51F)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            self._mark(0xC52F)
                                            if r.p&N:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC533)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                                self._a(r.y)
                                                self._mark(0xC53E)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                    self._mark(0xC543)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xC557)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._a(m[NEW_BUTTONS])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._mark(0xC560)
                                        if not r.p&N:
                                            pass
                                        else:
                                            self._y(m[SELECTED_SLOT])
                                            self._a(m[(0x0600+r.y)&65535])
                                            m[0x0000]=r.a
                                            self._a(m[(0x0614+r.y)&65535])
                                            self._flag(C,False)
                                            self._add(0x01)
                                            self._compare(r.a,0x14)
                                            self._mark(0xC572)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._compare(r.a,0x0F)
                                                self._mark(0xC576)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._flag(C,False)
                                                    self._add(0x01)
                                                    pass
                                                m[0x0001]=r.a
                                                if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                                self._a(r.y)
                                                self._mark(0xC581)
                                                if not r.p&N:
                                                    pass
                                                else:
                                                    if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                    self._mark(0xC586)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x00)
                                                        m[0x0012]=r.a
                                                        if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                        self._x(m[SELECTED_SLOT])
                                                        m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                        self._a(m[(0x0614+r.x)&65535])
                                                        self._compare(r.a,0x0F)
                                                        self._mark(0xC59A)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            pass
                                        self._mark(0xC59F)
                                        self._rts();return
                                    else:
                                        if not (yield from self._local_call(self.local_c447,0xC507,0xC50A)):return
                                        self._mark(0xC50A)
                                        if not r.p&C:
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xC51F)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,True)
                                                self._add(0x01,subtract=True)
                                                self._mark(0xC52F)
                                                if r.p&N:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC533)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,True)
                                                        self._add(0x01,subtract=True)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xC53A,0xC53D)):return
                                                    self._a(r.y)
                                                    self._mark(0xC53E)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        if not (yield from self._local_call(self.local_c447,0xC540,0xC543)):return
                                                        self._mark(0xC543)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xC549,0xC54C)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xC557)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]-1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._a(m[NEW_BUTTONS])
                                            r.a=self._shift(r.a,True,rotate=False)
                                            r.a=self._shift(r.a,True,rotate=False)
                                            self._mark(0xC560)
                                            if not r.p&N:
                                                pass
                                            else:
                                                self._y(m[SELECTED_SLOT])
                                                self._a(m[(0x0600+r.y)&65535])
                                                m[0x0000]=r.a
                                                self._a(m[(0x0614+r.y)&65535])
                                                self._flag(C,False)
                                                self._add(0x01)
                                                self._compare(r.a,0x14)
                                                self._mark(0xC572)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._compare(r.a,0x0F)
                                                    self._mark(0xC576)
                                                    if not r.p&Z:
                                                        pass
                                                    else:
                                                        self._flag(C,False)
                                                        self._add(0x01)
                                                        pass
                                                    m[0x0001]=r.a
                                                    if not (yield from self._local_call(self.local_d6b6,0xC57D,0xC580)):return
                                                    self._a(r.y)
                                                    self._mark(0xC581)
                                                    if not r.p&N:
                                                        pass
                                                    else:
                                                        if not (yield from self._local_call(self.local_c447,0xC583,0xC586)):return
                                                        self._mark(0xC586)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._a(0x00)
                                                            m[0x0012]=r.a
                                                            if not (yield from self._local_call(self.map_refresh,0xC58C,0xC58F)):return
                                                            self._x(m[SELECTED_SLOT])
                                                            m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                            self._a(m[(0x0614+r.x)&65535])
                                                            self._compare(r.a,0x0F)
                                                            self._mark(0xC59A)
                                                            if not r.p&Z:
                                                                pass
                                                            else:
                                                                m[(0x0614+r.x)&65535]=self._nz(m[(0x0614+r.x)&65535]+1)
                                                                pass
                                                            pass
                                                        pass
                                                    pass
                                                pass
                                            self._mark(0xC59F)
                                            self._rts();return
                                        else:
                                            self._a(0x00)
                                            m[0x0012]=r.a
                                            if not (yield from self._local_call(self.map_refresh,0xC510,0xC513)):return
                                            self._x(m[SELECTED_SLOT])
                                            m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]+1)
                                            self._mark(0xC519)
                                            self._rts();return
                        else:
                            self._a(0x00)
                            m[0x0012]=r.a
                            if not (yield from self._local_call(self.map_refresh,0xC4DF,0xC4E2)):return
                            self._x(m[SELECTED_SLOT])
                            m[(0x0600+r.x)&65535]=self._nz(m[(0x0600+r.x)&65535]-1)
                            self._mark(0xC4E8)
                            self._rts();return
        else:
            self._mark(0xC4B8)
            self._rts();return

    def local_c5a0(self):
        """$C5A0: local c5a0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5A0)
        if not (yield from self._local_call(self.refresh_hundred_troops,0xC5A0,0xC5A3)):return
        if not (yield from self._local_call(self.local_da83,0xC5A3,0xC5A6)):return
        self._a(m[0x000B])
        m[0x0000]=r.a
        self._a(m[0x000C])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._a(0xE8)
        m[0x0003]=r.a
        self._a(0x03)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_24bit,0xC5BA,0xC5BD)):return
        self._y(m[0x0000])
        self._a(m[(0xC606+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x050C])
        m[0x050C]=r.a
        self._compare(r.a,m[(0xC613+r.y)&65535])
        self._mark(0xC5CC)
        if not r.p&C:
            pass
        else:
            self._a(m[(0xC613+r.y)&65535])
            m[0x050C]=r.a
            pass
        if not (yield from self._local_call(self.local_dac3,0xC5D4,0xC5D7)):return
        self._a(m[0x000B])
        m[0x0000]=r.a
        self._a(m[0x000C])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._a(0xE8)
        m[0x0003]=r.a
        self._a(0x03)
        m[0x0004]=r.a
        if not (yield from self._local_call(self.divide_24bit,0xC5EB,0xC5EE)):return
        self._y(m[0x0000])
        self._a(m[(0xC606+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x050D])
        m[0x050D]=r.a
        self._compare(r.a,m[(0xC613+r.y)&65535])
        self._mark(0xC5FD)
        if not r.p&C:
            pass
        else:
            self._a(m[(0xC613+r.y)&65535])
            m[0x050D]=r.a
            pass
        self._mark(0xC605)
        self._rts();return

    def round_resource_update(self):
        """$C620: round resource update; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC620)
        self._a(0x00)
        m[0x051A]=r.a
        m[0x051B]=r.a
        m[0x051E]=r.a
        while True:  # natural loop $C62B
            self._y(r.a)
            self._push(r.a)
            self._a(m[(0x0664+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xC632)
            if r.p&Z:
                pass
            else:
                yield from self._external(0xC634,0xF2D7,0xC637,"call",None)
                if r.pc!=0xC637:return  # preserve nonlocal stack return
                self._y(0x08)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x051A])
                m[0x051A]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x03)
                self._add(m[0x051B])
                m[0x051B]=r.a
                m[0x051E]=self._nz(m[0x051E]+1)
                pass
            self._a(self._pop())
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x0A)
            self._mark(0xC656)
            if not r.p&C:
                continue
            else:
                pass
            self._a(0x00)
            m[0x051C]=r.a
            m[0x051D]=r.a
            m[0x051F]=r.a
            while True:  # natural loop $C663
                self._y(r.a)
                self._push(r.a)
                self._a(m[(0x066E+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC66A)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xC66C,0xF2D7,0xC66F,"call",None)
                    if r.pc!=0xC66F:return  # preserve nonlocal stack return
                    self._y(0x08)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x051C])
                    m[0x051C]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    self._add(m[0x051D])
                    m[0x051D]=r.a
                    m[0x051F]=self._nz(m[0x051F]+1)
                    pass
                self._a(self._pop())
                self._flag(C,False)
                self._add(0x01)
                self._compare(r.a,0x0A)
                self._mark(0xC68E)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xC690)
                self._rts();return

    def duel_result(self):
        """$C691: duel result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC691)
        self._a(m[PHASE])
        self._mark(0xC694)
        index=self._dispatch(0xC694,(50847, 50860, 50873, 50876))
        return (yield from (self.prepare_first_duel_result,self.prepare_second_duel_result,self.finish_duel_result,self.acknowledge_duel_upgrade,)[index]())

    def prepare_first_duel_result(self):
        """$C69F: prepare first duel result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC69F)
        self._a(m[0x0514])
        m[0x0010]=r.a
        self._a(0x01)
        m[0x0470]=r.a
        self._y(0x00)
        self._a(m[0x0010])
        self._compare(r.a,m[0x0560])
        self._mark(0xC6F1)
        if r.p&Z:
            pass
        else:
            self._y(0x01)
            pass
        self._a(m[(0x052E+r.y)&65535])
        m[0x0011]=r.a
        self._a(m[(0x052C+r.y)&65535])
        m[0x0012]=r.a
        self._a(m[0x0010])
        m[0x042C]=r.a
        if not (yield from self._local_call(self.find_duel_officer_slot,0xC704,0xC707)):return
        self._compare(r.y,0xFF)
        self._mark(0xC709)
        if r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xC715)
            self._rts();return
        else:
            self._a(m[(0x6FA1+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xC710)
            if r.p&Z:
                self._a(m[0x042C])
                yield from self._external(0xC719,0xF2D7,0xC71C,"call",None)
                if r.pc!=0xC71C:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                self._compare(r.a,m[0x0012])
                self._mark(0xC724)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xC715)
                    self._rts();return
                else:
                    self._y(0x01)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x0011],subtract=True)
                    m[0x042F]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x0430]=r.a
                    m[0x0431]=r.a
                    self._y(0x28)
                    yield from self._external(0xC73D,0xEE07,0xC742,"far_call",40984)
                    if r.pc!=0xC742:return  # preserve nonlocal stack return
                    self._a(0x03)
                    m[PHASE]=r.a
                    yield from self._external(0xC747,0xE57F,0xC74A,"call",None)
                    if r.pc!=0xC74A:return  # preserve nonlocal stack return
                    self._a(0x7B)
                    yield from self._external(0xC74C,0xE68B,0xC74F,"call",None)
                    if r.pc!=0xC74F:return  # preserve nonlocal stack return
                    self._a(0x4A)
                    self._y(m[0x042F])
                    self._mark(0xC754)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x4D)
                        pass
                    self._mark(0xC758)
                    yield from self._external(0xC758,0xF293,None,"tail")
                    return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xC715)
                self._rts();return

    def prepare_second_duel_result(self):
        """$C6AC: prepare second duel result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6AC)
        self._a(m[0x0516])
        m[0x0010]=r.a
        self._a(0x02)
        m[0x0470]=r.a
        self._y(0x00)
        self._a(m[0x0010])
        self._compare(r.a,m[0x0560])
        self._mark(0xC6F1)
        if r.p&Z:
            pass
        else:
            self._y(0x01)
            pass
        self._a(m[(0x052E+r.y)&65535])
        m[0x0011]=r.a
        self._a(m[(0x052C+r.y)&65535])
        m[0x0012]=r.a
        self._a(m[0x0010])
        m[0x042C]=r.a
        if not (yield from self._local_call(self.find_duel_officer_slot,0xC704,0xC707)):return
        self._compare(r.y,0xFF)
        self._mark(0xC709)
        if r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xC715)
            self._rts();return
        else:
            self._a(m[(0x6FA1+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xC710)
            if r.p&Z:
                self._a(m[0x042C])
                yield from self._external(0xC719,0xF2D7,0xC71C,"call",None)
                if r.pc!=0xC71C:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                self._compare(r.a,m[0x0012])
                self._mark(0xC724)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xC715)
                    self._rts();return
                else:
                    self._y(0x01)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x0011],subtract=True)
                    m[0x042F]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x0430]=r.a
                    m[0x0431]=r.a
                    self._y(0x28)
                    yield from self._external(0xC73D,0xEE07,0xC742,"far_call",40984)
                    if r.pc!=0xC742:return  # preserve nonlocal stack return
                    self._a(0x03)
                    m[PHASE]=r.a
                    yield from self._external(0xC747,0xE57F,0xC74A,"call",None)
                    if r.pc!=0xC74A:return  # preserve nonlocal stack return
                    self._a(0x7B)
                    yield from self._external(0xC74C,0xE68B,0xC74F,"call",None)
                    if r.pc!=0xC74F:return  # preserve nonlocal stack return
                    self._a(0x4A)
                    self._y(m[0x042F])
                    self._mark(0xC754)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x4D)
                        pass
                    self._mark(0xC758)
                    yield from self._external(0xC758,0xF293,None,"tail")
                    return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xC715)
                self._rts();return

    def finish_duel_result(self):
        """$C6B9: finish duel result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6B9)
        self._a(0x00)
        m[PHASE]=r.a
        m[STATE]=r.a
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xA21A)
        self._rts();return

    def acknowledge_duel_upgrade(self):
        """$C6BC: acknowledge duel upgrade; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6BC)
        if not (yield from self._local_call(self.text_readiness,0xC6BC,0xC6BF)):return
        self._mark(0xC6BF)
        if not r.p&C:
            self._mark(0xC6DF)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xC6C1,0xC6C4)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xC6C8)
            if r.p&Z:
                self._mark(0xC6DF)
                self._rts();return
            else:
                self._a(m[0x042D])
                self._compare(r.a,0xFF)
                self._mark(0xC6CF)
                if not r.p&Z:
                    self._a(0xFF)
                    m[0x042D]=r.a
                    self._a(0x4B)
                    self._mark(0xC6E7)
                    yield from self._external(0xC6E7,0xF293,None,"tail")
                    return
                else:
                    yield from self._external(0xC6D1,0xE57F,0xC6D4,"call",None)
                    if r.pc!=0xC6D4:return  # preserve nonlocal stack return
                    self._a(0x1D)
                    yield from self._external(0xC6D6,0xE673,0xC6D9,"call",None)
                    if r.pc!=0xC6D9:return  # preserve nonlocal stack return
                    self._a(m[0x0470])
                    m[PHASE]=r.a
                    self._mark(0xC6DF)
                    self._rts();return

    def find_duel_officer_slot(self):
        """$C75B: find duel officer slot; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC75B)
        self._y(0x13)
        while True:  # natural loop $C75D
            self._compare(r.a,m[(0x0664+r.y)&65535])
            self._mark(0xC760)
            if r.p&Z:
                pass
            else:
                self._y(r.y-1)
                self._mark(0xC763)
                if not r.p&N:
                    continue
                else:
                    pass
                pass
            self._mark(0xC765)
            self._rts();return

    def apply_duel_outcomes(self):
        """$C766: apply duel outcomes; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC766)
        if not (yield from self._local_call(self.refresh_hundred_troops,0xC766,0xC769)):return
        self._a(m[0x0514])
        if not (yield from self._local_call(self.find_duel_officer_slot,0xC76C,0xC76F)):return
        self._a(m[0x0515])
        if not (yield from self._local_call(self.dispatch_duel_outcome,0xC772,0xC775)):return
        self._a(m[0x0516])
        if not (yield from self._local_call(self.find_duel_officer_slot,0xC778,0xC77B)):return
        self._a(m[0x0517])
        if not (yield from self._local_call(self.dispatch_duel_outcome,0xC77E,0xC781)):return
        self._mark(0xC781)
        self._rts();return

    def dispatch_duel_outcome(self):
        """$C782: dispatch duel outcome; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC782)
        self._a(r.a & 0x07)
        self._mark(0xC784)
        index=self._dispatch(0xC784,(51095, 51096, 51097, 51163, 51231, 51231, 51231, 51231))
        return (yield from (self.local_c797,self.local_c798,self.remove_duel_defeated_unit,self.collect_duel_captive,self.local_c81f,self.local_c81f,self.local_c81f,self.local_c81f,)[index]())

    def local_c797(self):
        """$C797: local c797; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC797)
        self._rts();return

    def local_c798(self):
        """$C798: local c798; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC798)
        self._rts();return

    def remove_duel_defeated_unit(self):
        """$C799: remove duel defeated unit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC799)
        self._a(r.y)
        self._push(r.a)
        self._a(m[(0x0664+r.y)&65535])
        m[0x000B]=r.a
        self._a(m[0x0514])
        self._compare(r.a,m[(0x0664+r.y)&65535])
        self._mark(0xC7A6)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0516])
            pass
        m[0x000A]=r.a
        self._y(0x2E)
        yield from self._external(0xC7AF,0xEE07,0xC7B4,"far_call",40969)
        if r.pc!=0xC7B4:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._y(r.a)
        self._a(r.y)
        self._push(r.a)
        self._a(m[(0x0664+r.y)&65535])
        yield from self._external(0xC7BB,0xF2D7,0xC7BE,"call",None)
        if r.pc!=0xC7BE:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a | 0x03)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._a(self._pop())
        self._y(r.a)
        self._a(m[(0x0628+r.y)&65535])
        self._mark(0xC7CB)
        if not r.p&N:
            pass
        else:
            pass
        m[0x0000]=r.y
        self._y(0x28)
        yield from self._external(0xC7D5,0xEE07,0xC7DA,"far_call",41002)
        if r.pc!=0xC7DA:return  # preserve nonlocal stack return
        self._mark(0xC7DA)
        self._rts();return

    def collect_duel_captive(self):
        """$C7DB: collect duel captive; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC7DB)
        self._a(m[(0x0628+r.y)&65535])
        self._mark(0xC7DE)
        if not r.p&N:
            self._x(0x00)
            while True:  # natural loop $C7FB
                self._a(m[(0x6F5B+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC800)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    continue
                self._a(m[(0x0664+r.y)&65535])
                m[(0x6F5B+r.x)&65535]=r.a
                m[0x0521]=self._nz(m[0x0521]+1)
                m[0x0020]=r.a
                m[0x0012]=r.y
                self._y(0x2A)
                yield from self._external(0xC815,0xEE07,0xC81A,"far_call",40972)
                if r.pc!=0xC81A:return  # preserve nonlocal stack return
                self._y(m[0x0012])
                m[0x0000]=r.y
                self._y(0x28)
                yield from self._external(0xC7D5,0xEE07,0xC7DA,"far_call",41002)
                if r.pc!=0xC7DA:return  # preserve nonlocal stack return
                self._mark(0xC7DA)
                self._rts();return
        else:
            self._x(0x00)
            while True:  # natural loop $C7E2
                self._a(m[(0x6F47+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xC7E7)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    continue
                self._a(m[(0x0664+r.y)&65535])
                m[(0x6F47+r.x)&65535]=r.a
                m[0x0520]=self._nz(m[0x0520]+1)
                m[0x0020]=r.a
                m[0x0012]=r.y
                self._y(0x2A)
                yield from self._external(0xC815,0xEE07,0xC81A,"far_call",40972)
                if r.pc!=0xC81A:return  # preserve nonlocal stack return
                self._y(m[0x0012])
                m[0x0000]=r.y
                self._y(0x28)
                yield from self._external(0xC7D5,0xEE07,0xC7DA,"far_call",41002)
                if r.pc!=0xC7DA:return  # preserve nonlocal stack return
                self._mark(0xC7DA)
                self._rts();return

    def local_c81f(self):
        """$C81F: local c81f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC81F)
        if not (yield from self._local_call(self.local_c886,0xC81F,0xC822)):return
        self._a(m[(0x0628+r.y)&65535])
        self._a(r.a ^ 0x80)
        m[(0x0628+r.y)&65535]=r.a
        self._a(0xFF)
        self._compare(r.y,m[0x04D8])
        self._mark(0xC82F)
        if not r.p&Z:
            pass
        else:
            m[0x04D8]=r.a
            pass
        self._compare(r.y,m[0x04DC])
        self._mark(0xC837)
        if not r.p&Z:
            pass
        else:
            m[0x04DC]=r.a
            pass
        self._a(m[(0x6FA1+r.y)&65535])
        self._compare(r.a,0xFF)
        self._mark(0xC841)
        if not r.p&Z:
            self._a(0xFF)
            m[(0x6FA1+r.y)&65535]=r.a
            pass
        else:
            self._a(0x04)
            m[(0x6FA1+r.y)&65535]=r.a
            pass
        m[0x0012]=r.y
        self._a(m[RULERS])
        self._a(r.a & 0x0F)
        m[0x0010]=r.a
        self._a(m[RULERS])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0011]=r.a
        self._x(m[0x0010])
        self._y(m[0x0012])
        self._a(m[(0x0628+r.y)&65535])
        self._mark(0xC869)
        if not r.p&N:
            pass
        else:
            self._x(m[0x0011])
            pass
        self._a(r.x)
        yield from self._external(0xC86E,0xF368,0xC871,"call",None)
        if r.pc!=0xC871:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0030]=r.a
        self._y(m[0x0012])
        self._a(m[(0x0664+r.y)&65535])
        m[0x0031]=r.a
        self._y(0x2A)
        yield from self._external(0xC880,0xEE07,0xC885,"far_call",40966)
        if r.pc!=0xC885:return  # preserve nonlocal stack return
        self._mark(0xC885)
        self._rts();return

    def local_c886(self):
        """$C886: local c886; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC886)
        self._a(r.y)
        self._x(r.a)
        self._push(r.a)
        self._a(m[(0x0628+r.x)&65535])
        self._mark(0xC88C)
        if r.p&N:
            m[0x051F]=self._nz(m[0x051F]-1)
            self._a(m[(0x0664+r.x)&65535])
            yield from self._external(0xC8DC,0xF2D7,0xC8DF,"call",None)
            if r.pc!=0xC8DF:return  # preserve nonlocal stack return
            self._y(0x08)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0002]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            m[0x0003]=r.a
            self._a(m[0x051C])
            self._flag(C,True)
            self._add(m[0x0002],subtract=True)
            m[0x051C]=r.a
            self._a(m[0x051D])
            self._add(m[0x0003],subtract=True)
            m[0x051D]=r.a
            self._mark(0xC8FD)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x051C]=r.a
                m[0x051D]=r.a
                pass
            m[0x051E]=self._nz(m[0x051E]+1)
            self._a(m[0x051A])
            self._flag(C,False)
            self._add(m[0x0002])
            m[0x051A]=r.a
            self._a(m[0x051B])
            self._add(m[0x0003])
            m[0x051B]=r.a
            pass
        else:
            m[0x051E]=self._nz(m[0x051E]-1)
            self._a(m[(0x0664+r.x)&65535])
            yield from self._external(0xC894,0xF2D7,0xC897,"call",None)
            if r.pc!=0xC897:return  # preserve nonlocal stack return
            self._y(0x08)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0002]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            m[0x0003]=r.a
            self._a(m[0x051A])
            self._flag(C,True)
            self._add(m[0x0002],subtract=True)
            m[0x051A]=r.a
            self._a(m[0x051B])
            self._add(m[0x0003],subtract=True)
            m[0x051B]=r.a
            self._mark(0xC8B5)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x051A]=r.a
                m[0x051B]=r.a
                pass
            m[0x051F]=self._nz(m[0x051F]+1)
            self._a(m[0x051C])
            self._flag(C,False)
            self._add(m[0x0002])
            m[0x051C]=r.a
            self._a(m[0x051D])
            self._add(m[0x0003])
            m[0x051D]=r.a
            pass
        self._a(self._pop())
        self._y(r.a)
        self._mark(0xC91D)
        self._rts();return

    def local_c91e(self):
        """$C91E: local c91e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC91E)
        self._x(m[SELECTED_SLOT])
        self._a(m[(0x0628+r.x)&65535])
        self._mark(0xC924)
        if r.p&N:
            m[0x051F]=self._nz(m[0x051F]-1)
            self._a(m[(0x0664+r.x)&65535])
            yield from self._external(0xC960,0xF2D7,0xC963,"call",None)
            if r.pc!=0xC963:return  # preserve nonlocal stack return
            self._y(0x08)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0002]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            m[0x0003]=r.a
            self._a(m[0x051C])
            self._flag(C,True)
            self._add(m[0x0002],subtract=True)
            m[0x051C]=r.a
            self._a(m[0x051D])
            self._add(m[0x0003],subtract=True)
            m[0x051D]=r.a
            self._mark(0xC981)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x051C]=r.a
                m[0x051D]=r.a
                pass
            pass
        else:
            m[0x051E]=self._nz(m[0x051E]-1)
            self._a(m[(0x0664+r.x)&65535])
            yield from self._external(0xC92C,0xF2D7,0xC92F,"call",None)
            if r.pc!=0xC92F:return  # preserve nonlocal stack return
            self._y(0x08)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0002]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x03)
            m[0x0003]=r.a
            self._a(m[0x051A])
            self._flag(C,True)
            self._add(m[0x0002],subtract=True)
            m[0x051A]=r.a
            self._a(m[0x051B])
            self._add(m[0x0003],subtract=True)
            m[0x051B]=r.a
            self._mark(0xC94D)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x051A]=r.a
                m[0x051B]=r.a
                pass
            pass
        self._mark(0xC98B)
        self._rts();return

    def battle_result(self):
        """$C98C: battle result; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC98C)
        self._a(m[PHASE])
        self._mark(0xC98F)
        index=self._dispatch(0xC98F,(51614, 51629, 51651, 51710, 51731, 51759))
        return (yield from (self.prepare_result_summary,self.await_result_text,self.prepare_result_panel,self.confirm_result_panel,self.select_result_resolution,self.acknowledge_result_exit,)[index]())

    def prepare_result_summary(self):
        """$C99E: prepare result summary; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC99E)
        yield from self._external(0xC99E,0xE57F,0xC9A1,"call",None)
        if r.pc!=0xC9A1:return  # preserve nonlocal stack return
        self._a(0xD5)
        yield from self._external(0xC9A3,0xF293,0xC9A6,"call",None)
        if r.pc!=0xC9A6:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.prepare_postbattle_summary,0xC9A6,0xC9A9)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xC9AC)
        self._rts();return

    def await_result_text(self):
        """$C9AD: await result text; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9AD)
        if not (yield from self._local_call(self.text_readiness,0xC9AD,0xC9B0)):return
        self._mark(0xC9B0)
        if not r.p&C:
            pass
        else:
            self._a(m[PPU_JOBS])
            self._mark(0xC9B5)
            if not r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.local_ca53,0xC9BA,0xC9BD)):return
                self._a(0x04)
                yield from self._external(0xC9BF,0xF28B,0xC9C2,"call",None)
                if r.pc!=0xC9C2:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xC9C2)
        self._rts();return

    def prepare_result_panel(self):
        """$C9C3: prepare result panel; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9C3)
        self._a(m[PPU_JOBS])
        self._mark(0xC9C6)
        if not r.p&Z:
            self._mark(0xC9C2)
            self._rts();return
        else:
            self._a(0xE1)
            m[0x00E6]=r.a
            self._a(0xE1)
            m[0x00E8]=r.a
            self._a(0x08)
            m[0x00B2]=r.a
            self._a(0x09)
            m[0x00B3]=r.a
            self._a(0x02)
            m[0x00B4]=r.a
            self._a(0x03)
            m[0x00B5]=r.a
            self._a(0x00)
            self._x(0x1F)
            while True:  # natural loop $C9E4
                m[(0x044C+r.x)&65535]=r.a
                self._x(r.x-1)
                self._mark(0xC9E8)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(0x00)
                m[0x008E]=r.a
                self._a(0x50)
                m[0x0090]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.local_ca41,0xC9F5,0xC9F8)):return
                self._a(0x18)
                yield from self._external(0xC9FA,0xE683,0xC9FD,"call",None)
                if r.pc!=0xC9FD:return  # preserve nonlocal stack return
                self._mark(0xC9FD)
                self._rts();return

    def confirm_result_panel(self):
        """$C9FE: confirm result panel; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9FE)
        if not (yield from self._local_call(self.draw_postbattle_units,0xC9FE,0xCA01)):return
        if not (yield from self._local_call(self.text_readiness,0xCA01,0xCA04)):return
        self._mark(0xCA04)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xCA06,0xCA09)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCA0D)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xCA12)
        self._rts();return

    def select_result_resolution(self):
        """$CA13: select result resolution; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA13)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCA13,0xCA16)):return
        if not (yield from self._local_call(self.result_yes_flag,0xCA16,0xCA19)):return
        self._mark(0xCA19)
        if not r.p&C:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xD5)
            yield from self._external(0xCA2B,0xF293,0xCA2E,"call",None)
            if r.pc!=0xCA2E:return  # preserve nonlocal stack return
            self._mark(0xCA2E)
            self._rts();return
        else:
            self._a(0x0F)
            m[STATE]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            self._mark(0xCA25)
            self._rts();return

    def acknowledge_result_exit(self):
        """$CA2F: acknowledge result exit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA2F)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCA2F,0xCA32)):return
        if not (yield from self._local_call(self.text_readiness,0xCA32,0xCA35)):return
        self._mark(0xCA35)
        if not r.p&C:
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCA3B)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]-1)
                pass
            pass
        self._mark(0xCA40)
        self._rts();return

    def local_ca41(self):
        """$CA41: local ca41; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA41)
        self._a(0xE0)
        m[0x0310]=r.a
        self._a(0xDB)
        m[0x0311]=r.a
        self._a(0x00)
        m[0x0300]=r.a
        self._mark(0xCA50)
        self._rts();return

    def result_yes_flag(self):
        """$CA51: result yes flag; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA51)
        self._flag(C,True)
        self._mark(0xCA52)
        self._rts();return

    def local_ca53(self):
        """$CA53: local ca53; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA53)
        self._x(0x00)
        self._a(m[0x0514])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xCA91+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xCA92+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[(0xCA99+r.y)&65535])
        m[0x0002]=r.a
        self._a(m[(0xCA9A+r.y)&65535])
        m[0x0003]=r.a
        self._y(0x00)
        while True:  # natural loop $CA70
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[(0x0380+r.x)&65535]=r.a
            self._x(r.x+1)
            self._y(r.y+1)
            self._compare(r.y,0x0E)
            self._mark(0xCA79)
            if not r.p&C:
                continue
            else:
                pass
            self._y(0x00)
            while True:  # natural loop $CA7D
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[(0x0380+r.x)&65535]=r.a
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x0F)
                self._mark(0xCA86)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xCA90)
                self._rts();return

    def prepare_postbattle_summary(self):
        """$CAF8: prepare postbattle summary; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAF8)
        if not (yield from self._local_call(self.local_cb6e,0xCAF8,0xCAFB)):return
        self._a(m[0x051A])
        m[0x044F]=r.a
        self._a(m[0x051B])
        m[0x0450]=r.a
        self._a(0x00)
        m[0x044E]=r.a
        m[0x0451]=r.a
        self._a(m[0x051C])
        m[0x044C]=r.a
        self._a(m[0x051D])
        m[0x044D]=r.a
        self._a(m[0x051E])
        m[0x0455]=r.a
        self._a(m[0x051F])
        m[0x0452]=r.a
        self._a(0x00)
        m[0x0453]=r.a
        m[0x0454]=r.a
        m[0x0456]=r.a
        m[0x0457]=r.a
        self._y(0x00)
        self._x(0x00)
        while True:  # natural loop $CB39
            self._a(m[(0x6F47+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xCB3E)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                pass
            self._y(r.y+1)
            self._compare(r.y,0x14)
            self._mark(0xCB44)
            if not r.p&C:
                continue
            else:
                pass
            m[0x045B]=r.x
            self._x(0x00)
            m[0x045C]=r.x
            m[0x045D]=r.x
            self._y(0x00)
            self._x(0x00)
            while True:  # natural loop $CB55
                self._a(m[(0x6F5B+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCB5A)
                if r.p&Z:
                    pass
                else:
                    self._x(r.x+1)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xCB60)
                if not r.p&C:
                    continue
                else:
                    pass
                m[0x0458]=r.x
                self._x(0x00)
                m[0x0459]=r.x
                m[0x045A]=r.x
                self._mark(0xCB6D)
                self._rts();return

    def local_cb6e(self):
        """$CB6E: local cb6e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB6E)
        self._a(0x00)
        m[0x000A]=r.a
        m[0x000B]=r.a
        m[0x000C]=r.a
        while True:  # natural loop $CB76
            self._y(r.a)
            self._push(r.a)
            self._a(m[(0x0628+r.y)&65535])
            self._mark(0xCB7B)
            if r.p&N:
                pass
            else:
                self._a(m[(0x0664+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCB82)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xCB84,0xF2D7,0xCB87,"call",None)
                    if r.pc!=0xCB87:return  # preserve nonlocal stack return
                    self._y(0x08)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x000A])
                    m[0x000A]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    self._add(m[0x000B])
                    m[0x000B]=r.a
                    m[0x000C]=self._nz(m[0x000C]+1)
                    pass
                pass
            self._a(self._pop())
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x14)
            self._mark(0xCBA1)
            if not r.p&C:
                continue
            else:
                pass
            self._a(m[0x051A])
            self._flag(C,True)
            self._add(m[0x000A],subtract=True)
            m[0x051A]=r.a
            self._a(m[0x051B])
            self._add(m[0x000B],subtract=True)
            m[0x051B]=r.a
            self._mark(0xCBB4)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                m[0x051A]=r.a
                m[0x051B]=r.a
                pass
            self._a(m[0x051E])
            self._flag(C,True)
            self._add(m[0x000C],subtract=True)
            self._mark(0xCBC4)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                pass
            m[0x051E]=r.a
            self._a(0x00)
            m[0x000A]=r.a
            m[0x000B]=r.a
            m[0x000C]=r.a
            while True:  # natural loop $CBD3
                self._y(r.a)
                self._push(r.a)
                self._a(m[(0x0628+r.y)&65535])
                self._mark(0xCBD8)
                if not r.p&N:
                    pass
                else:
                    self._a(m[(0x0664+r.y)&65535])
                    self._compare(r.a,0xFF)
                    self._mark(0xCBDF)
                    if r.p&Z:
                        pass
                    else:
                        yield from self._external(0xCBE1,0xF2D7,0xCBE4,"call",None)
                        if r.pc!=0xCBE4:return  # preserve nonlocal stack return
                        self._y(0x08)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x000A])
                        m[0x000A]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x03)
                        self._add(m[0x000B])
                        m[0x000B]=r.a
                        m[0x000C]=self._nz(m[0x000C]+1)
                        pass
                    pass
                self._a(self._pop())
                self._flag(C,False)
                self._add(0x01)
                self._compare(r.a,0x14)
                self._mark(0xCBFE)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x051C])
                self._flag(C,True)
                self._add(m[0x000A],subtract=True)
                m[0x051C]=r.a
                self._a(m[0x051D])
                self._add(m[0x000B],subtract=True)
                m[0x051D]=r.a
                self._mark(0xCC11)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[0x051C]=r.a
                    m[0x051D]=r.a
                    pass
                self._a(m[0x051F])
                self._flag(C,True)
                self._add(m[0x000C],subtract=True)
                self._mark(0xCC21)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    pass
                m[0x051F]=r.a
                self._mark(0xCC28)
                self._rts();return

    def draw_postbattle_units(self):
        """$CC29: draw postbattle units; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC29)
        self._y(0x31)
        yield from self._external(0xCC2B,0xF25F,0xCC2E,"call",None)
        if r.pc!=0xCC2E:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x000A]=r.a
        self._a(m[0x005E])
        self._a(r.a & 0x01)
        self._mark(0xCC37)
        if not r.p&Z:
            if not (yield from self._local_call(self.local_cc5a,0xCC3F,0xCC42)):return
            return (yield from self.local_cc45())
        else:
            if not (yield from self._local_call(self.local_cc45,0xCC39,0xCC3C)):return
            return (yield from self.local_cc5a())

    def local_cc45(self):
        """$CC45: local cc45; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC45)
        self._a(0x40)
        m[0x000B]=r.a
        self._a(0x00)
        m[0x000C]=r.a
        self._a(m[RULERS])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        if not (yield from self._local_call(self.local_cc6d,0xCC54,0xCC57)):return
        m[0x00AF]=r.a
        self._mark(0xCC59)
        self._rts();return

    def local_cc5a(self):
        """$CC5A: local cc5a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC5A)
        self._a(0x80)
        m[0x000B]=r.a
        self._a(0x70)
        m[0x000C]=r.a
        self._a(m[RULERS])
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.local_cc6d,0xCC67,0xCC6A)):return
        m[0x00B0]=r.a
        self._mark(0xCC6C)
        self._rts();return

    def local_cc6d(self):
        """$CC6D: local cc6d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC6D)
        if not (yield from self._local_call(self.ruler_pointer,0xCC6D,0xCC70)):return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x0D)
        m[0x0003]=r.a
        if not (yield from self._local_call(self.multiply_24bit,0xCC80,0xCC83)):return
        self._a(m[0x0006])
        self._flag(C,False)
        self._add(0xB4)
        m[0x0006]=r.a
        self._a(m[0x0007])
        self._add(0x8D)
        m[0x0007]=r.a
        self._y(0x00)
        self._a(m[((m[0x06]|m[0x07]<<8)+r.y)&65535])
        self._push(r.a)
        if not (yield from self._local_call(self.local_ccdf,0xCC95,0xCC98)):return
        self._a(0x00)
        while True:  # natural loop $CC9A
            self._push(r.a)
            if not (yield from self._local_call(self.local_ccaa,0xCC9B,0xCC9E)):return
            self._a(self._pop())
            m[0x000A]=self._nz(m[0x000A]+1)
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x0C)
            self._mark(0xCCA6)
            if not r.p&C:
                continue
            else:
                pass
            self._a(self._pop())
            self._mark(0xCCA9)
            self._rts();return

    def local_ccaa(self):
        """$CCAA: local ccaa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCAA)
        self._y(0x00)
        self._a(m[((m[0x06]|m[0x07]<<8)+r.y)&65535])
        if not (yield from self._local_call(self.local_ccdf,0xCCAE,0xCCB1)):return
        self._compare(r.a,0xFF)
        self._mark(0xCCB3)
        if r.p&Z:
            pass
        else:
            self._y(m[0x000A])
            self._x(m[0x007C])
            self._flag(C,False)
            self._add(m[0x000B])
            m[(0x0201+r.x)&65535]=r.a
            self._a(m[(0xCCE6+r.y)&65535])
            self._flag(C,True)
            self._add(0x01,subtract=True)
            m[(0x0200+r.x)&65535]=r.a
            self._a(m[(0xCCFE+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x000C])
            m[(0x0203+r.x)&65535]=r.a
            self._a(0x00)
            m[(0x0202+r.x)&65535]=r.a
            self._x(r.x+1)
            self._x(r.x+1)
            self._x(r.x+1)
            self._x(r.x+1)
            m[0x007C]=r.x
            pass
        self._mark(0xCCDE)
        self._rts();return

    def local_ccdf(self):
        """$CCDF: local ccdf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCDF)
        m[0x0006]=self._nz(m[0x0006]+1)
        self._mark(0xCCE1)
        if not r.p&Z:
            pass
        else:
            m[0x0007]=self._nz(m[0x0007]+1)
            pass
        self._mark(0xCCE5)
        self._rts();return

    def defeated_roster(self):
        """$CD16: defeated roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD16)
        self._a(m[PHASE])
        self._mark(0xCD19)
        index=self._dispatch(0xCD19,(52522, 52562, 52722, 52822, 52854, 52894, 53001))
        return (yield from (self.prepare_defeated_roster,self.select_defeated_roster_destination,self.open_defeated_roster_selection,self.choose_defeated_roster_officer,self.exclude_defeated_roster_officer,self.prepare_defeated_roster_confirmation,self.confirm_defeated_roster_transfer,)[index]())

    def prepare_defeated_roster(self):
        """$CD2A: prepare defeated roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD2A)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCD2A,0xCD2D)):return
        if not (yield from self._local_call(self.postbattle_roster,0xCD2D,0xCD30)):return
        self._a(0xFF)
        m[(0x042C+r.x)&65535]=r.a
        self._a(r.x)
        self._mark(0xCD36)
        if not r.p&Z:
            self._a(0xDC)
            yield from self._external(0xCD48,0xF293,0xCD4B,"call",None)
            if r.pc!=0xCD4B:return  # preserve nonlocal stack return
            if not (yield from self._local_call(self.local_d0c3,0xCD4B,0xCD4E)):return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xCD51)
            self._rts();return
        else:
            self._a(m[0x050B])
            self._a(r.a & 0x0F)
            m[PHASE]=r.a
            self._a(0x0F)
            m[STATE]=r.a
            self._mark(0xCD45)
            self._rts();return

    def select_defeated_roster_destination(self):
        """$CD52: select defeated roster destination; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD52)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCD52,0xCD55)):return
        if not (yield from self._local_call(self.text_readiness,0xCD55,0xCD58)):return
        self._mark(0xCD58)
        if not r.p&C:
            self._mark(0xCD63)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xCD5A,0xCD5D)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCD61)
            if not r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x00)
                m[0x0424]=r.a
                m[0x0425]=r.a
                self._a(m[0x050B])
                self._a(r.a & 0x10)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[SIDE]=r.a
                if not (yield from self._local_call(self.local_bb84,0xCD7A,0xCD7D)):return
                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
                self._a(m[ACTOR_SLOT])
                self._mark(0xCD83)
                if r.p&Z:
                    self._a(m[RULERS])
                    self._y(m[0x050B])
                    self._compare(r.y,0x02)
                    self._mark(0xCDA4)
                    if r.p&Z:
                        pass
                    else:
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        pass
                    self._a(r.a & 0x0F)
                    if not (yield from self._local_call(self.ruler_pointer,0xCDAC,0xCDAF)):return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0003]=r.a
                    if not (yield from self._local_call(self.postbattle_roster,0xCDB5,0xCDB8)):return
                    self._x(0x00)
                    while True:  # natural loop $CDBA
                        self._a(m[(0x042C+r.x)&65535])
                        self._compare(r.a,0xFE)
                        self._mark(0xCDBF)
                        if r.p&C:
                            pass
                        else:
                            self._compare(r.a,m[0x0003])
                            self._mark(0xCDC3)
                            if r.p&Z:
                                yield from self._external(0xCDE3,0xF2D7,0xCDE6,"call",None)
                                if r.pc!=0xCDE6:return  # preserve nonlocal stack return
                                self._y(0x0B)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._a(r.a | 0x03)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            else:
                                yield from self._external(0xCDC5,0xF2D7,0xCDC8,"call",None)
                                if r.pc!=0xCDC8:return  # preserve nonlocal stack return
                                self._y(0x0B)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._a(r.a & 0xFC)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._y(0x05)
                                self._a(m[CITY])
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            continue
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(m[0x050B])
                        self._a(r.a & 0x0F)
                        m[PHASE]=r.a
                        self._a(0x0F)
                        m[STATE]=r.a
                        self._mark(0xCD45)
                        self._rts();return
                else:
                    self._y(r.a)
                    self._a(0x1E)
                    m[(0x042C+r.y)&65535]=r.a
                    self._y(r.y-1)
                    while True:  # natural loop $CD8C
                        self._a(m[(0x0550+r.y)&65535])
                        self._compare(r.a,0x0A)
                        self._mark(0xCD91)
                        if r.p&C:
                            self._y(r.y-1)
                            self._mark(0xCD9A)
                            if not r.p&N:
                                continue
                            else:
                                self._a(m[RULERS])
                                self._y(m[0x050B])
                                self._compare(r.y,0x02)
                                self._mark(0xCDA4)
                                if r.p&Z:
                                    pass
                                else:
                                    r.a=self._shift(r.a,False,rotate=False)
                                    r.a=self._shift(r.a,False,rotate=False)
                                    r.a=self._shift(r.a,False,rotate=False)
                                    r.a=self._shift(r.a,False,rotate=False)
                                    pass
                                self._a(r.a & 0x0F)
                                if not (yield from self._local_call(self.ruler_pointer,0xCDAC,0xCDAF)):return
                                self._y(0x00)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x0003]=r.a
                                if not (yield from self._local_call(self.postbattle_roster,0xCDB5,0xCDB8)):return
                                self._x(0x00)
                                while True:  # natural loop $CDBA
                                    self._a(m[(0x042C+r.x)&65535])
                                    self._compare(r.a,0xFE)
                                    self._mark(0xCDBF)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._compare(r.a,m[0x0003])
                                        self._mark(0xCDC3)
                                        if r.p&Z:
                                            yield from self._external(0xCDE3,0xF2D7,0xCDE6,"call",None)
                                            if r.pc!=0xCDE6:return  # preserve nonlocal stack return
                                            self._y(0x0B)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._a(r.a | 0x03)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._x(r.x+1)
                                            pass
                                        else:
                                            yield from self._external(0xCDC5,0xF2D7,0xCDC8,"call",None)
                                            if r.pc!=0xCDC8:return  # preserve nonlocal stack return
                                            self._y(0x0B)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._a(r.a & 0xFC)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(0x05)
                                            self._a(m[CITY])
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._x(r.x+1)
                                            pass
                                        continue
                                    self._a(0x00)
                                    m[PHASE]=r.a
                                    self._a(m[0x050B])
                                    self._a(r.a & 0x0F)
                                    m[PHASE]=r.a
                                    self._a(0x0F)
                                    m[STATE]=r.a
                                    self._mark(0xCD45)
                                    self._rts();return
                        else:
                            self._a(0xD7)
                            yield from self._external(0xCD95,0xF283,0xCD98,"call",None)
                            if r.pc!=0xCD98:return  # preserve nonlocal stack return
                            self._mark(0xCD98)
                            self._rts();return
            else:
                self._mark(0xCD63)
                self._rts();return

    def open_defeated_roster_selection(self):
        """$CDF2: open defeated roster selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCDF2)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCDF2,0xCDF5)):return
        self._a(m[ACTOR_SLOT])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBA9F+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xBAA0+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xCE08,0xED1E,0xCE0B,"call",None)
        if r.pc!=0xCE0B:return  # preserve nonlocal stack return
        self._a(0x6F)
        m[0x0010]=r.a
        self._a(0xBB)
        m[0x0011]=r.a
        self._a(0x7F)
        m[0x0000]=r.a
        self._a(0xBB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xCE1D,0xEDF5,0xCE20,"call",None)
        if r.pc!=0xCE20:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xCE20,0xCE23)):return
        self._mark(0xCE23)
        if not r.p&C:
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCE29)
            if r.p&Z:
                pass
            else:
                self._y(m[0x0012])
                self._a(m[(0x042C+r.y)&65535])
                m[0x0540]=r.a
                m[0x0541]=r.y
                self._compare(r.a,0x1E)
                self._mark(0xCE38)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0xDD)
                    self._y(m[0x0540])
                    self._compare(r.y,0x1E)
                    self._mark(0xCE4B)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0xE5)
                        pass
                    yield from self._external(0xCE4F,0xF283,0xCE52,"call",None)
                    if r.pc!=0xCE52:return  # preserve nonlocal stack return
                    if not (yield from self._local_call(self.local_d0c3,0xCE52,0xCE55)):return
                    pass
                else:
                    self._a(m[(0x0550+r.y)&65535])
                    self._compare(r.a,0x0A)
                    self._mark(0xCE3F)
                    if r.p&C:
                        pass
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0xDD)
                        self._y(m[0x0540])
                        self._compare(r.y,0x1E)
                        self._mark(0xCE4B)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0xE5)
                            pass
                        yield from self._external(0xCE4F,0xF283,0xCE52,"call",None)
                        if r.pc!=0xCE52:return  # preserve nonlocal stack return
                        if not (yield from self._local_call(self.local_d0c3,0xCE52,0xCE55)):return
                        pass
                    pass
                pass
            pass
        self._mark(0xCE55)
        self._rts();return

    def choose_defeated_roster_officer(self):
        """$CE56: choose defeated roster officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE56)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCE56,0xCE59)):return
        if not (yield from self._local_call(self.text_readiness,0xCE59,0xCE5C)):return
        self._mark(0xCE5C)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xCE5E,0xCE61)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCE65)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.postbattle_roster,0xCE67,0xCE6A)):return
                m[ACTOR_SLOT]=r.x
                self._a(0xDE)
                yield from self._external(0xCE6F,0xF28B,0xCE72,"call",None)
                if r.pc!=0xCE72:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xCE75)
        self._rts();return

    def exclude_defeated_roster_officer(self):
        """$CE76: exclude defeated roster officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE76)
        if not (yield from self._local_call(self.draw_postbattle_units,0xCE76,0xCE79)):return
        if not (yield from self._local_call(self.text_readiness,0xCE79,0xCE7C)):return
        self._mark(0xCE7C)
        if not r.p&C:
            pass
        else:
            self._x(m[ACTOR_SLOT])
            self._a(0xFF)
            m[(0x042C+r.x)&65535]=r.a
            self._a(0xE0)
            m[0x00E6]=r.a
            m[0x00E7]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x00)
            m[0x008E]=r.a
            m[0x0090]=r.a
            self._a(0x00)
            m[0x0424]=r.a
            m[0x0425]=r.a
            pass
        self._mark(0xCE9D)
        self._rts();return

    def prepare_defeated_roster_confirmation(self):
        """$CE9E: prepare defeated roster confirmation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE9E)
        self._a(m[ACTOR_SLOT])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xCF5E+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xCF5F+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xCEB1,0xED23,0xCEB4,"call",None)
        if r.pc!=0xCEB4:return  # preserve nonlocal stack return
        self._a(0x34)
        m[0x0010]=r.a
        self._a(0xCF)
        m[0x0011]=r.a
        self._a(0x04)
        m[0x0000]=r.a
        self._a(0xCF)
        m[0x0001]=r.a
        self._a(m[0x0012])
        m[0x0508]=r.a
        yield from self._external(0xCEC9,0xEDF5,0xCECC,"call",None)
        if r.pc!=0xCECC:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.local_d167,0xCECC,0xCECF)):return
        if not (yield from self._local_call(self.local_d1bc,0xCECF,0xCED2)):return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x01)
        self._mark(0xCED6)
        if r.p&Z:
            self._mark(0xCF03)
            self._rts();return
        else:
            self._a(m[ACTOR_SLOT])
            self._compare(r.a,m[0x0508])
            self._mark(0xCEDE)
            if not r.p&Z:
                self._mark(0xCF03)
                self._rts();return
            else:
                self._y(0x00)
                self._x(0x00)
                while True:  # natural loop $CEE4
                    self._a(m[(0x0580+r.y)&65535])
                    self._mark(0xCEE7)
                    if r.p&N:
                        pass
                    else:
                        self._x(r.x+1)
                        pass
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    self._mark(0xCEED)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(r.x)
                    self._mark(0xCEF0)
                    if r.p&Z:
                        self._a(0xE1)
                        m[0x00E6]=r.a
                        m[0x00E7]=r.a
                        self._a(0x00)
                        m[0x008E]=r.a
                        self._a(0x50)
                        m[0x0090]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.local_d1f9,0xCF2D,0xCF30)):return
                        return (yield from self.prepare_defeated_roster())
                    else:
                        self._a(0xD8)
                        self._y(m[0x0540])
                        self._compare(r.y,0x1E)
                        self._mark(0xCEF9)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0xE6)
                            pass
                        yield from self._external(0xCEFD,0xF283,0xCF00,"call",None)
                        if r.pc!=0xCF00:return  # preserve nonlocal stack return
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._mark(0xCF03)
                        self._rts();return

    def confirm_defeated_roster_transfer(self):
        """$CF09: confirm defeated roster transfer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF09)
        if not (yield from self._local_call(self.local_d1bc,0xCF09,0xCF0C)):return
        if not (yield from self._local_call(self.text_readiness,0xCF0C,0xCF0F)):return
        self._mark(0xCF0F)
        if not r.p&C:
            self._mark(0xCF33)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xCF11,0xCF14)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xCF18)
            if r.p&Z:
                self._mark(0xCF33)
                self._rts();return
            else:
                self._a(0xE1)
                m[0x00E6]=r.a
                m[0x00E7]=r.a
                self._a(0x00)
                m[0x008E]=r.a
                self._a(0x50)
                m[0x0090]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                if not (yield from self._local_call(self.local_d1f9,0xCF2D,0xCF30)):return
                return (yield from self.prepare_defeated_roster())

    def local_d0c3(self):
        """$D0C3: local d0c3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0C3)
        self._y(m[RULERS])
        self._a(m[0x050B])
        self._a(r.a & 0xF0)
        self._mark(0xD0CB)
        if r.p&Z:
            pass
        else:
            self._a(r.y)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._y(r.a)
            pass
        self._a(r.y)
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.ruler_pointer,0xD0D6,0xD0D9)):return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x044C]=r.a
        self._mark(0xD0E0)
        self._rts();return

    def postbattle_roster(self):
        """$D0E1: postbattle roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0E1)
        self._y(0x20)
        self._a(0xFF)
        while True:  # natural loop $D0E5
            m[(0x0580+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xD0E9)
            if not r.p&N:
                continue
            else:
                pass
            self._a(0xFF)
            m[ACTOR_SLOT]=r.a
            self._y(0x1F)
            self._a(0xFF)
            while True:  # natural loop $D0F4
                m[(0x042C+r.y)&65535]=r.a
                self._y(r.y-1)
                self._mark(0xD0F8)
                if not r.p&N:
                    continue
                else:
                    pass
                self._a(m[0x050B])
                self._a(r.a & 0x10)
                self._mark(0xD0FF)
                if not r.p&Z:
                    self._y(0x00)
                    self._x(0x00)
                    while True:  # natural loop $D138
                        self._a(m[(0x0628+r.y)&65535])
                        self._a(r.a & 0x80)
                        self._mark(0xD13D)
                        if r.p&Z:
                            pass
                        else:
                            self._a(m[(0x0664+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xD144)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x042C+r.x)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x14)
                        self._mark(0xD14D)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x00)
                        while True:  # natural loop $D151
                            self._a(m[(0x6F5B+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xD156)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x042C+r.x)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            self._mark(0xD15F)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(0xFE)
                            m[(0x042C+r.x)&65535]=r.a
                            self._mark(0xD166)
                            self._rts();return
                else:
                    self._y(0x00)
                    self._x(0x00)
                    while True:  # natural loop $D105
                        self._a(m[(0x0628+r.y)&65535])
                        self._a(r.a & 0x80)
                        self._mark(0xD10A)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[(0x0664+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xD111)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x042C+r.x)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x14)
                        self._mark(0xD11A)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x00)
                        while True:  # natural loop $D11E
                            self._a(m[(0x6F47+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xD123)
                            if r.p&Z:
                                pass
                            else:
                                m[(0x042C+r.x)&65535]=r.a
                                self._x(r.x+1)
                                pass
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            self._mark(0xD12C)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(0xFE)
                            m[(0x042C+r.x)&65535]=r.a
                            self._mark(0xD133)
                            self._rts();return

    def local_d167(self):
        """$D167: local d167; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD167)
        self._x(0x00)
        self._y(0x1F)
        while True:  # natural loop $D16B
            self._a(m[(0x0580+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xD170)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                pass
            self._y(r.y-1)
            self._mark(0xD174)
            if not r.p&N:
                continue
            else:
                pass
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD17A)
            if r.p&Z:
                self._mark(0xD1BB)
                self._rts();return
            else:
                self._y(m[0x0508])
                self._compare(r.y,m[ACTOR_SLOT])
                self._mark(0xD182)
                if r.p&Z:
                    self._mark(0xD1BB)
                    self._rts();return
                else:
                    self._a(m[(0x0580+r.y)&65535])
                    self._mark(0xD187)
                    if r.p&Z:
                        self._a(0xFF)
                        m[(0x0580+r.y)&65535]=r.a
                        self._mark(0xD1BB)
                        self._rts();return
                    else:
                        self._a(m[0x0540])
                        self._compare(r.a,0x1E)
                        self._mark(0xD18E)
                        if not r.p&Z:
                            m[0x0000]=r.x
                            self._y(m[0x0541])
                            self._a(0x09)
                            self._flag(C,True)
                            self._add(m[(0x0550+r.y)&65535],subtract=True)
                            self._compare(r.a,m[0x0000])
                            self._mark(0xD1AB)
                            if not r.p&C:
                                self._mark(0xD1BB)
                                self._rts();return
                            else:
                                self._y(m[0x0508])
                                self._a(0x00)
                                m[(0x0580+r.y)&65535]=r.a
                                self._mark(0xD1B5)
                                self._rts();return
                        else:
                            if not (yield from self._local_call(self.local_d0c3,0xD190,0xD193)):return
                            self._y(m[0x0508])
                            self._compare(r.a,m[(0x042C+r.y)&65535])
                            self._mark(0xD199)
                            if r.p&Z:
                                self._mark(0xD1BB)
                                self._rts();return
                            else:
                                self._y(m[0x0508])
                                self._a(0x00)
                                m[(0x0580+r.y)&65535]=r.a
                                self._mark(0xD1B5)
                                self._rts();return

    def local_d1bc(self):
        """$D1BC: local d1bc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1BC)
        self._a(0x08)
        m[0x00AF]=r.a
        self._a(0x36)
        m[0x0115]=r.a
        self._a(0x16)
        m[0x0117]=r.a
        self._y(0x00)
        while True:  # natural loop $D1CD
            self._a(m[(0x0580+r.y)&65535])
            self._mark(0xD1D0)
            if r.p&N:
                pass
            else:
                self._a(r.y)
                self._push(r.a)
                if not (yield from self._local_call(self.local_d1df,0xD1D4,0xD1D7)):return
                self._a(self._pop())
                self._y(r.a)
                pass
            self._y(r.y+1)
            self._compare(r.y,0x14)
            self._mark(0xD1DC)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD1DE)
            self._rts();return

    def local_d1df(self):
        """$D1DF: local d1df; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1DF)
        self._a(0x34)
        m[0x0010]=r.a
        self._a(0xCF)
        m[0x0011]=r.a
        self._a(0xF4)
        m[0x0000]=r.a
        self._a(0xD1)
        m[0x0001]=r.a
        self._a(r.y)
        yield from self._external(0xD1F0,0xEDF5,0xD1F3,"call",None)
        if r.pc!=0xD1F3:return  # preserve nonlocal stack return
        self._mark(0xD1F3)
        self._rts();return

    def local_d1f9(self):
        """$D1F9: local d1f9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1F9)
        self._y(0x00)
        while True:  # natural loop $D1FB
            self._a(m[(0x0580+r.y)&65535])
            self._mark(0xD1FE)
            if r.p&N:
                pass
            else:
                self._a(r.y)
                self._push(r.a)
                if not (yield from self._local_call(self.local_d20d,0xD202,0xD205)):return
                self._a(self._pop())
                self._y(r.a)
                pass
            self._y(r.y+1)
            self._compare(r.y,0x14)
            self._mark(0xD20A)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD20C)
            self._rts();return

    def local_d20d(self):
        """$D20D: local d20d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD20D)
        self._a(m[0x0540])
        self._compare(r.a,0x1E)
        self._mark(0xD212)
        if not r.p&Z:
            self._a(r.y)
            self._push(r.a)
            self._a(m[0x050B])
            self._push(r.a)
            self._a(m[0x0540])
            m[0x050B]=r.a
            if not (yield from self._local_call(self.local_bc11,0xD255,0xD258)):return
            self._a(self._pop())
            m[0x050B]=r.a
            self._a(self._pop())
            self._x(r.a)
            self._a(m[(0x042C+r.x)&65535])
            self._compare(r.a,m[0x052B])
            self._mark(0xD264)
            if not r.p&Z:
                pass
            else:
                self._x(m[0x0540])
                m[0x052C]=r.x
                pass
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._push(r.a)
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x07)
            self._compare(r.a,0x07)
            self._mark(0xD277)
            if not r.p&Z:
                pass
            else:
                self._y(m[RULERS])
                self._a(m[0x050B])
                self._a(r.a & 0xF0)
                self._mark(0xD281)
                if r.p&Z:
                    pass
                else:
                    self._a(r.y)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._y(r.a)
                    pass
                self._a(r.y)
                self._a(r.a & 0x0F)
                m[0x0002]=r.a
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                self._a(r.a | m[0x0002])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                pass
            self._a(self._pop())
            pass
        else:
            self._a(m[(0x042C+r.y)&65535])
            self._push(r.a)
            yield from self._external(0xD218,0xF2D7,0xD21B,"call",None)
            if r.pc!=0xD21B:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0xFC)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(0x30)
            yield from self._external(0xD225,0xF266,0xD228,"call",None)
            if r.pc!=0xD228:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0002]=r.a
            if not (yield from self._local_call(self.random_eight,0xD231,0xD234)):return
            self._flag(C,False)
            self._add(m[0x0002])
            self._y(r.a)
            self._a(m[(0x9D72+r.y)&65535])
            self._mark(0xD23C)
            if not r.p&N:
                pass
            else:
                self._a(m[CITY])
                pass
            self._y(0x05)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(self._pop())
            pass
        self._x(0x00)
        while True:  # natural loop $D29B
            self._compare(r.a,m[(0x0664+r.x)&65535])
            self._mark(0xD29E)
            if r.p&Z:
                self._a(0xFF)
                m[(0x0600+r.x)&65535]=r.a
                m[(0x0614+r.x)&65535]=r.a
                m[(0x0628+r.x)&65535]=r.a
                m[(0x063C+r.x)&65535]=r.a
                m[(0x0650+r.x)&65535]=r.a
                m[(0x0664+r.x)&65535]=r.a
                self._mark(0xD2C6)
                self._rts();return
            else:
                self._x(r.x+1)
                self._compare(r.x,0x14)
                self._mark(0xD2A3)
                if not r.p&C:
                    continue
                else:
                    self._x(0x00)
                    while True:  # natural loop $D2A7
                        self._compare(r.a,m[(0x6F47+r.x)&65535])
                        self._mark(0xD2AA)
                        if r.p&Z:
                            self._a(0xFF)
                            m[(0x6F47+r.x)&65535]=r.a
                            self._mark(0xD2CC)
                            self._rts();return
                        else:
                            self._x(r.x+1)
                            self._compare(r.x,0x28)
                            self._mark(0xD2AF)
                            if not r.p&C:
                                continue
                            else:
                                self._mark(0xD2B1)
                                self._rts();return

    def victor_roster(self):
        """$D2CD: victor roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2CD)
        self._a(m[PHASE])
        self._mark(0xD2D0)
        index=self._dispatch(0xD2D0,(53985, 54032, 54091, 54191, 54231, 54263, 54370))
        return (yield from (self.prepare_victor_roster,self.select_victor_roster_destination,self.open_victor_roster_selection,self.choose_victor_roster_officer,self.exclude_victor_roster_officer,self.prepare_victor_roster_confirmation,self.confirm_victor_roster_transfer,)[index]())

    def prepare_victor_roster(self):
        """$D2E1: prepare victor roster; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2E1)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD2E1,0xD2E4)):return
        if not (yield from self._local_call(self.postbattle_roster,0xD2E4,0xD2E7)):return
        self._a(0xFF)
        m[(0x042C+r.x)&65535]=r.a
        m[ACTOR_SLOT]=r.x
        self._compare(r.x,0x0B)
        self._mark(0xD2F1)
        if r.p&C:
            self._a(0xDF)
            yield from self._external(0xD306,0xF293,0xD309,"call",None)
            if r.pc!=0xD309:return  # preserve nonlocal stack return
            if not (yield from self._local_call(self.local_d0c3,0xD309,0xD30C)):return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._mark(0xD30F)
            self._rts();return
        else:
            if not (yield from self._local_call(self.remove_postbattle_officer,0xD2F3,0xD2F6)):return
            self._a(0x0F)
            m[STATE]=r.a
            self._a(m[0x050B])
            self._a(r.a & 0x0F)
            m[PHASE]=r.a
            self._mark(0xD303)
            self._rts();return

    def select_victor_roster_destination(self):
        """$D310: select victor roster destination; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD310)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD310,0xD313)):return
        if not (yield from self._local_call(self.text_readiness,0xD313,0xD316)):return
        self._mark(0xD316)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xD318,0xD31B)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD31F)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xD7)
                yield from self._external(0xD326,0xF283,0xD329,"call",None)
                if r.pc!=0xD329:return  # preserve nonlocal stack return
                self._a(0x00)
                m[0x0424]=r.a
                m[0x0425]=r.a
                self._a(m[0x050B])
                self._a(r.a & 0x10)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[SIDE]=r.a
                if not (yield from self._local_call(self.local_bb84,0xD33C,0xD33F)):return
                m[ACTOR_SLOT]=self._nz(m[ACTOR_SLOT]+1)
                self._y(m[ACTOR_SLOT])
                self._a(0x1E)
                m[(0x042C+r.y)&65535]=r.a
                pass
            pass
        self._mark(0xD34A)
        self._rts();return

    def open_victor_roster_selection(self):
        """$D34B: open victor roster selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD34B)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD34B,0xD34E)):return
        self._a(m[ACTOR_SLOT])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBA9F+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xBAA0+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xD361,0xED1E,0xD364,"call",None)
        if r.pc!=0xD364:return  # preserve nonlocal stack return
        self._a(0x6F)
        m[0x0010]=r.a
        self._a(0xBB)
        m[0x0011]=r.a
        self._a(0x7F)
        m[0x0000]=r.a
        self._a(0xBB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xD376,0xEDF5,0xD379,"call",None)
        if r.pc!=0xD379:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_readiness,0xD379,0xD37C)):return
        self._mark(0xD37C)
        if not r.p&C:
            self._mark(0xD34A)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD382)
            if r.p&Z:
                pass
            else:
                self._y(m[0x0012])
                self._a(m[(0x042C+r.y)&65535])
                m[0x0540]=r.a
                m[0x0541]=r.y
                self._compare(r.a,0x1E)
                self._mark(0xD391)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0xDD)
                    self._y(m[0x0540])
                    self._compare(r.y,0x1E)
                    self._mark(0xD3A4)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0xE5)
                        pass
                    yield from self._external(0xD3A8,0xF283,0xD3AB,"call",None)
                    if r.pc!=0xD3AB:return  # preserve nonlocal stack return
                    if not (yield from self._local_call(self.local_d0c3,0xD3AB,0xD3AE)):return
                    pass
                else:
                    self._a(m[(0x0550+r.y)&65535])
                    self._compare(r.a,0x0A)
                    self._mark(0xD398)
                    if r.p&C:
                        pass
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0xDD)
                        self._y(m[0x0540])
                        self._compare(r.y,0x1E)
                        self._mark(0xD3A4)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0xE5)
                            pass
                        yield from self._external(0xD3A8,0xF283,0xD3AB,"call",None)
                        if r.pc!=0xD3AB:return  # preserve nonlocal stack return
                        if not (yield from self._local_call(self.local_d0c3,0xD3AB,0xD3AE)):return
                        pass
                    pass
                pass
            self._mark(0xD3AE)
            self._rts();return

    def choose_victor_roster_officer(self):
        """$D3AF: choose victor roster officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3AF)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD3AF,0xD3B2)):return
        if not (yield from self._local_call(self.text_readiness,0xD3B2,0xD3B5)):return
        self._mark(0xD3B5)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xD3B7,0xD3BA)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD3BE)
            if r.p&Z:
                pass
            else:
                self._a(0x00)
                m[0x0424]=r.a
                m[0x0425]=r.a
                if not (yield from self._local_call(self.postbattle_roster,0xD3C8,0xD3CB)):return
                m[ACTOR_SLOT]=r.x
                self._a(0xDE)
                yield from self._external(0xD3D0,0xF28B,0xD3D3,"call",None)
                if r.pc!=0xD3D3:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xD3D6)
        self._rts();return

    def exclude_victor_roster_officer(self):
        """$D3D7: exclude victor roster officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3D7)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD3D7,0xD3DA)):return
        if not (yield from self._local_call(self.text_readiness,0xD3DA,0xD3DD)):return
        self._mark(0xD3DD)
        if not r.p&C:
            pass
        else:
            self._x(m[ACTOR_SLOT])
            self._a(0xFF)
            m[(0x042C+r.x)&65535]=r.a
            self._a(0xE0)
            m[0x00E6]=r.a
            m[0x00E7]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x00)
            m[0x008E]=r.a
            m[0x0090]=r.a
            pass
        self._mark(0xD3F6)
        self._rts();return

    def prepare_victor_roster_confirmation(self):
        """$D3F7: prepare victor roster confirmation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3F7)
        self._a(m[ACTOR_SLOT])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xCF5E+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xCF5F+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xD40A,0xED23,0xD40D,"call",None)
        if r.pc!=0xD40D:return  # preserve nonlocal stack return
        self._a(0x34)
        m[0x0010]=r.a
        self._a(0xCF)
        m[0x0011]=r.a
        self._a(0x5D)
        m[0x0000]=r.a
        self._a(0xD4)
        m[0x0001]=r.a
        self._a(m[0x0012])
        m[0x0508]=r.a
        yield from self._external(0xD422,0xEDF5,0xD425,"call",None)
        if r.pc!=0xD425:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.local_d167,0xD425,0xD428)):return
        if not (yield from self._local_call(self.local_d1bc,0xD428,0xD42B)):return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x01)
        self._mark(0xD42F)
        if r.p&Z:
            self._mark(0xD45C)
            self._rts();return
        else:
            self._a(m[ACTOR_SLOT])
            self._compare(r.a,m[0x0508])
            self._mark(0xD437)
            if not r.p&Z:
                self._mark(0xD45C)
                self._rts();return
            else:
                self._y(0x00)
                self._x(0x00)
                while True:  # natural loop $D43D
                    self._a(m[(0x0580+r.y)&65535])
                    self._mark(0xD440)
                    if r.p&N:
                        pass
                    else:
                        self._x(r.x+1)
                        pass
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    self._mark(0xD446)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(r.x)
                    self._mark(0xD449)
                    if r.p&Z:
                        self._a(0xE1)
                        m[0x00E6]=r.a
                        m[0x00E7]=r.a
                        self._a(0x00)
                        m[0x008E]=r.a
                        self._a(0x50)
                        m[0x0090]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.local_d1f9,0xD486,0xD489)):return
                        return (yield from self.prepare_victor_roster())
                    else:
                        self._a(0xD8)
                        self._y(m[0x0540])
                        self._compare(r.y,0x1E)
                        self._mark(0xD452)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0xE6)
                            pass
                        yield from self._external(0xD456,0xF283,0xD459,"call",None)
                        if r.pc!=0xD459:return  # preserve nonlocal stack return
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._mark(0xD45C)
                        self._rts();return

    def confirm_victor_roster_transfer(self):
        """$D462: confirm victor roster transfer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD462)
        if not (yield from self._local_call(self.local_d1bc,0xD462,0xD465)):return
        if not (yield from self._local_call(self.text_readiness,0xD465,0xD468)):return
        self._mark(0xD468)
        if not r.p&C:
            self._mark(0xD48C)
            self._rts();return
        else:
            if not (yield from self._local_call(self.dialog_highlight,0xD46A,0xD46D)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD471)
            if r.p&Z:
                self._mark(0xD48C)
                self._rts();return
            else:
                self._a(0xE1)
                m[0x00E6]=r.a
                m[0x00E7]=r.a
                self._a(0x00)
                m[0x008E]=r.a
                self._a(0x50)
                m[0x0090]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                if not (yield from self._local_call(self.local_d1f9,0xD486,0xD489)):return
                return (yield from self.prepare_victor_roster())

    def remove_postbattle_officer(self):
        """$D48D: remove postbattle officer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD48D)
        self._y(0x00)
        while True:  # natural loop $D48F
            self._a(m[(0x042C+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xD494)
            if r.p&Z:
                pass
            else:
                self._a(r.y)
                self._push(r.a)
                if not (yield from self._local_call(self.local_d4a3,0xD498,0xD49B)):return
                self._a(self._pop())
                self._y(r.a)
                pass
            self._y(r.y+1)
            self._compare(r.y,0x14)
            self._mark(0xD4A0)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD4A2)
            self._rts();return

    def local_d4a3(self):
        """$D4A3: local d4a3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4A3)
        self._push(r.a)
        self._a(m[0x050B])
        self._push(r.a)
        self._a(m[CITY])
        m[0x050B]=r.a
        if not (yield from self._local_call(self.local_bc11,0xD4AE,0xD4B1)):return
        self._a(self._pop())
        m[0x050B]=r.a
        self._a(self._pop())
        self._x(r.a)
        self._a(m[(0x042C+r.x)&65535])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._x(0x00)
        while True:  # natural loop $D4BE
            self._compare(r.a,m[(0x0664+r.x)&65535])
            self._mark(0xD4C1)
            if r.p&Z:
                self._a(0xFF)
                m[(0x0600+r.x)&65535]=r.a
                m[(0x0614+r.x)&65535]=r.a
                m[(0x0628+r.x)&65535]=r.a
                m[(0x063C+r.x)&65535]=r.a
                m[(0x0650+r.x)&65535]=r.a
                m[(0x0664+r.x)&65535]=r.a
                self._mark(0xD4E9)
                self._rts();return
            else:
                self._x(r.x+1)
                self._compare(r.x,0x14)
                self._mark(0xD4C6)
                if not r.p&C:
                    continue
                else:
                    self._x(0x00)
                    while True:  # natural loop $D4CA
                        self._compare(r.a,m[(0x6F47+r.x)&65535])
                        self._mark(0xD4CD)
                        if r.p&Z:
                            self._a(0xFF)
                            m[(0x6F47+r.x)&65535]=r.a
                            self._mark(0xD4EF)
                            self._rts();return
                        else:
                            self._x(r.x+1)
                            self._compare(r.x,0x28)
                            self._mark(0xD4D2)
                            if not r.p&C:
                                continue
                            else:
                                self._mark(0xD4D4)
                                self._rts();return

    def return_to_city(self):
        """$D4F0: return to city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4F0)
        if not (yield from self._local_call(self.draw_postbattle_units,0xD4F0,0xD4F3)):return
        self._y(0x28)
        yield from self._external(0xD4F5,0xEE07,0xD4FA,"far_call",40966)
        if r.pc!=0xD4FA:return  # preserve nonlocal stack return
        self._mark(0xD4FA)
        self._rts();return

    def direction_repeat(self):
        """$D4FB: direction repeat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4FB)
        self._a(m[0x0318])
        m[0x0000]=r.a
        self._a(m[0x0083])
        self._a(r.a & 0xF0)
        m[0x0318]=r.a
        self._mark(0xD508)
        if r.p&Z:
            self._a(0x00)
            m[0x0319]=r.a
            self._mark(0xD52A)
            self._rts();return
        else:
            self._compare(r.a,m[0x0000])
            self._mark(0xD50C)
            if not r.p&Z:
                self._a(0x00)
                m[0x0319]=r.a
                self._a(m[0x0083])
                self._mark(0xD533)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F40])
                    self._compare(r.x,0x01)
                    self._mark(0xD53A)
                    if not r.p&Z:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(m[0x008E],subtract=True)
                        self._compare(r.a,0xF0)
                        self._mark(0xD54C)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x6F3F])
                            self._flag(C,False)
                            self._add(0x10)
                            m[0x6F3F]=r.a
                            self._a(m[0x6F40])
                            self._add(0x00)
                            m[0x6F40]=r.a
                            pass
                        self._a(self._pop())
                        pass
                    else:
                        self._x(m[0x6F3F])
                        self._compare(r.x,0xF0)
                        self._mark(0xD541)
                        if r.p&C:
                            pass
                        else:
                            self._push(r.a)
                            self._a(m[0x6F3F])
                            self._flag(C,True)
                            self._add(m[0x008E],subtract=True)
                            self._compare(r.a,0xF0)
                            self._mark(0xD54C)
                            if r.p&C:
                                pass
                            else:
                                self._a(m[0x6F3F])
                                self._flag(C,False)
                                self._add(0x10)
                                m[0x6F3F]=r.a
                                self._a(m[0x6F40])
                                self._add(0x00)
                                m[0x6F40]=r.a
                                pass
                            self._a(self._pop())
                            pass
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xD561)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F40])
                    self._mark(0xD566)
                    if not r.p&Z:
                        self._push(r.a)
                        self._a(m[0x6F3F])
                        self._flag(C,True)
                        self._add(m[0x008E],subtract=True)
                        self._compare(r.a,0x10)
                        self._mark(0xD576)
                        if not r.p&C:
                            pass
                        else:
                            self._a(m[0x6F3F])
                            self._flag(C,True)
                            self._add(0x10,subtract=True)
                            m[0x6F3F]=r.a
                            self._a(m[0x6F40])
                            self._add(0x00,subtract=True)
                            m[0x6F40]=r.a
                            pass
                        self._a(self._pop())
                        pass
                    else:
                        self._x(m[0x6F3F])
                        self._mark(0xD56B)
                        if r.p&Z:
                            pass
                        else:
                            self._push(r.a)
                            self._a(m[0x6F3F])
                            self._flag(C,True)
                            self._add(m[0x008E],subtract=True)
                            self._compare(r.a,0x10)
                            self._mark(0xD576)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x6F3F])
                                self._flag(C,True)
                                self._add(0x10,subtract=True)
                                m[0x6F3F]=r.a
                                self._a(m[0x6F40])
                                self._add(0x00,subtract=True)
                                m[0x6F40]=r.a
                                pass
                            self._a(self._pop())
                            pass
                        pass
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xD58B)
                if not r.p&N:
                    pass
                else:
                    self._push(r.a)
                    self._a(m[0x6F42])
                    self._mark(0xD591)
                    if r.p&Z:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(m[0x0090],subtract=True)
                        self._compare(r.a,0xA0)
                        self._mark(0xD5A3)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,False)
                            self._add(0x10)
                            self._compare(r.a,0xF0)
                            self._mark(0xD5AD)
                            if not r.p&C:
                                pass
                            else:
                                self._flag(C,False)
                                self._add(0x10)
                                self._flag(C,True)
                                pass
                            m[0x6F41]=r.a
                            self._a(m[0x6F42])
                            self._add(0x00)
                            m[0x6F42]=r.a
                            pass
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._compare(r.a,0x40)
                        self._mark(0xD598)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,True)
                            self._add(m[0x0090],subtract=True)
                            self._compare(r.a,0xA0)
                            self._mark(0xD5A3)
                            if r.p&C:
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._flag(C,False)
                                self._add(0x10)
                                self._compare(r.a,0xF0)
                                self._mark(0xD5AD)
                                if not r.p&C:
                                    pass
                                else:
                                    self._flag(C,False)
                                    self._add(0x10)
                                    self._flag(C,True)
                                    pass
                                m[0x6F41]=r.a
                                self._a(m[0x6F42])
                                self._add(0x00)
                                m[0x6F42]=r.a
                                pass
                            pass
                        pass
                    self._a(self._pop())
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xD5C0)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F42])
                    self._mark(0xD5C5)
                    if not r.p&Z:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(m[0x0090],subtract=True)
                        self._compare(r.a,0x10)
                        self._mark(0xD5D7)
                        if not r.p&C:
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,True)
                            self._add(0x10,subtract=True)
                            m[0x6F41]=r.a
                            self._mark(0xD5E2)
                            if r.p&C:
                                pass
                            else:
                                self._flag(C,True)
                                self._add(0x10,subtract=True)
                                m[0x6F41]=r.a
                                m[0x6F42]=self._nz(m[0x6F42]-1)
                                pass
                            pass
                        pass
                    else:
                        self._x(m[0x6F41])
                        self._compare(r.x,0x10)
                        self._mark(0xD5CC)
                        if not r.p&C:
                            pass
                        else:
                            self._a(m[0x6F41])
                            self._flag(C,True)
                            self._add(m[0x0090],subtract=True)
                            self._compare(r.a,0x10)
                            self._mark(0xD5D7)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(0x10,subtract=True)
                                m[0x6F41]=r.a
                                self._mark(0xD5E2)
                                if r.p&C:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x10,subtract=True)
                                    m[0x6F41]=r.a
                                    m[0x6F42]=self._nz(m[0x6F42]-1)
                                    pass
                                pass
                            pass
                        pass
                    pass
                self._mark(0xD5ED)
                self._rts();return
            else:
                m[0x0319]=self._nz(m[0x0319]+1)
                self._a(m[0x0319])
                self._compare(r.a,0x0F)
                self._mark(0xD516)
                if not r.p&C:
                    self._mark(0xD524)
                    self._rts();return
                else:
                    self._a(0x0F)
                    m[0x0319]=r.a
                    self._a(m[0x005E])
                    self._a(r.a & 0x03)
                    self._mark(0xD522)
                    if r.p&Z:
                        self._a(m[0x0083])
                        self._mark(0xD533)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F40])
                            self._compare(r.x,0x01)
                            self._mark(0xD53A)
                            if not r.p&Z:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,True)
                                self._add(m[0x008E],subtract=True)
                                self._compare(r.a,0xF0)
                                self._mark(0xD54C)
                                if r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F3F])
                                    self._flag(C,False)
                                    self._add(0x10)
                                    m[0x6F3F]=r.a
                                    self._a(m[0x6F40])
                                    self._add(0x00)
                                    m[0x6F40]=r.a
                                    pass
                                self._a(self._pop())
                                pass
                            else:
                                self._x(m[0x6F3F])
                                self._compare(r.x,0xF0)
                                self._mark(0xD541)
                                if r.p&C:
                                    pass
                                else:
                                    self._push(r.a)
                                    self._a(m[0x6F3F])
                                    self._flag(C,True)
                                    self._add(m[0x008E],subtract=True)
                                    self._compare(r.a,0xF0)
                                    self._mark(0xD54C)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._a(m[0x6F3F])
                                        self._flag(C,False)
                                        self._add(0x10)
                                        m[0x6F3F]=r.a
                                        self._a(m[0x6F40])
                                        self._add(0x00)
                                        m[0x6F40]=r.a
                                        pass
                                    self._a(self._pop())
                                    pass
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xD561)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F40])
                            self._mark(0xD566)
                            if not r.p&Z:
                                self._push(r.a)
                                self._a(m[0x6F3F])
                                self._flag(C,True)
                                self._add(m[0x008E],subtract=True)
                                self._compare(r.a,0x10)
                                self._mark(0xD576)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F3F])
                                    self._flag(C,True)
                                    self._add(0x10,subtract=True)
                                    m[0x6F3F]=r.a
                                    self._a(m[0x6F40])
                                    self._add(0x00,subtract=True)
                                    m[0x6F40]=r.a
                                    pass
                                self._a(self._pop())
                                pass
                            else:
                                self._x(m[0x6F3F])
                                self._mark(0xD56B)
                                if r.p&Z:
                                    pass
                                else:
                                    self._push(r.a)
                                    self._a(m[0x6F3F])
                                    self._flag(C,True)
                                    self._add(m[0x008E],subtract=True)
                                    self._compare(r.a,0x10)
                                    self._mark(0xD576)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(m[0x6F3F])
                                        self._flag(C,True)
                                        self._add(0x10,subtract=True)
                                        m[0x6F3F]=r.a
                                        self._a(m[0x6F40])
                                        self._add(0x00,subtract=True)
                                        m[0x6F40]=r.a
                                        pass
                                    self._a(self._pop())
                                    pass
                                pass
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xD58B)
                        if not r.p&N:
                            pass
                        else:
                            self._push(r.a)
                            self._a(m[0x6F42])
                            self._mark(0xD591)
                            if r.p&Z:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(m[0x0090],subtract=True)
                                self._compare(r.a,0xA0)
                                self._mark(0xD5A3)
                                if r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F41])
                                    self._flag(C,False)
                                    self._add(0x10)
                                    self._compare(r.a,0xF0)
                                    self._mark(0xD5AD)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._flag(C,False)
                                        self._add(0x10)
                                        self._flag(C,True)
                                        pass
                                    m[0x6F41]=r.a
                                    self._a(m[0x6F42])
                                    self._add(0x00)
                                    m[0x6F42]=r.a
                                    pass
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._compare(r.a,0x40)
                                self._mark(0xD598)
                                if r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F41])
                                    self._flag(C,True)
                                    self._add(m[0x0090],subtract=True)
                                    self._compare(r.a,0xA0)
                                    self._mark(0xD5A3)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._a(m[0x6F41])
                                        self._flag(C,False)
                                        self._add(0x10)
                                        self._compare(r.a,0xF0)
                                        self._mark(0xD5AD)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._flag(C,False)
                                            self._add(0x10)
                                            self._flag(C,True)
                                            pass
                                        m[0x6F41]=r.a
                                        self._a(m[0x6F42])
                                        self._add(0x00)
                                        m[0x6F42]=r.a
                                        pass
                                    pass
                                pass
                            self._a(self._pop())
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xD5C0)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F42])
                            self._mark(0xD5C5)
                            if not r.p&Z:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(m[0x0090],subtract=True)
                                self._compare(r.a,0x10)
                                self._mark(0xD5D7)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F41])
                                    self._flag(C,True)
                                    self._add(0x10,subtract=True)
                                    m[0x6F41]=r.a
                                    self._mark(0xD5E2)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._flag(C,True)
                                        self._add(0x10,subtract=True)
                                        m[0x6F41]=r.a
                                        m[0x6F42]=self._nz(m[0x6F42]-1)
                                        pass
                                    pass
                                pass
                            else:
                                self._x(m[0x6F41])
                                self._compare(r.x,0x10)
                                self._mark(0xD5CC)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(m[0x6F41])
                                    self._flag(C,True)
                                    self._add(m[0x0090],subtract=True)
                                    self._compare(r.a,0x10)
                                    self._mark(0xD5D7)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(m[0x6F41])
                                        self._flag(C,True)
                                        self._add(0x10,subtract=True)
                                        m[0x6F41]=r.a
                                        self._mark(0xD5E2)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x10,subtract=True)
                                            m[0x6F41]=r.a
                                            m[0x6F42]=self._nz(m[0x6F42]-1)
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        self._mark(0xD5ED)
                        self._rts();return
                    else:
                        self._mark(0xD524)
                        self._rts();return

    def cursor_input(self):
        """$D5EE: cursor input; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5EE)
        if not (yield from self._local_call(self.local_da17,0xD5EE,0xD5F1)):return
        self._a(0x00)
        m[0x0004]=r.a
        self._a(m[0x0002])
        self._flag(C,True)
        self._add(m[0x0000],subtract=True)
        self._mark(0xD5FC)
        if not r.p&C:
            self._y(m[0x0090])
            self._mark(0xD605)
            if r.p&Z:
                self._compare(r.a,0x07)
                self._mark(0xD611)
                if not r.p&C:
                    pass
                else:
                    self._y(m[0x0090])
                    self._compare(r.y,0x8E)
                    self._mark(0xD618)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x10)
                        m[0x0004]=r.a
                        pass
                    pass
                pass
            else:
                self._a(0x20)
                m[0x0004]=r.a
                pass
            pass
        else:
            self._compare(r.a,0x03)
            self._mark(0xD600)
            if r.p&C:
                self._compare(r.a,0x07)
                self._mark(0xD611)
                if not r.p&C:
                    pass
                else:
                    self._y(m[0x0090])
                    self._compare(r.y,0x8E)
                    self._mark(0xD618)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x10)
                        m[0x0004]=r.a
                        pass
                    pass
                pass
            else:
                self._y(m[0x0090])
                self._mark(0xD605)
                if r.p&Z:
                    self._compare(r.a,0x07)
                    self._mark(0xD611)
                    if not r.p&C:
                        pass
                    else:
                        self._y(m[0x0090])
                        self._compare(r.y,0x8E)
                        self._mark(0xD618)
                        if r.p&C:
                            pass
                        else:
                            self._a(0x10)
                            m[0x0004]=r.a
                            pass
                        pass
                    pass
                else:
                    self._a(0x20)
                    m[0x0004]=r.a
                    pass
                pass
            pass
        self._a(m[0x0003])
        self._flag(C,True)
        self._add(m[0x0001],subtract=True)
        self._mark(0xD626)
        if not r.p&C:
            self._y(m[0x008E])
            self._mark(0xD62E)
            if r.p&Z:
                self._compare(r.a,0x0C)
                self._mark(0xD63D)
                if not r.p&C:
                    pass
                else:
                    self._y(m[0x008E])
                    self._compare(r.y,0xFE)
                    self._mark(0xD643)
                    if r.p&C:
                        pass
                    else:
                        self._a(m[0x0004])
                        self._a(r.a | 0x80)
                        m[0x0004]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x0004])
                self._a(r.a | 0x40)
                m[0x0004]=r.a
                pass
            pass
        else:
            self._compare(r.a,0x04)
            self._mark(0xD62A)
            if r.p&C:
                self._compare(r.a,0x0C)
                self._mark(0xD63D)
                if not r.p&C:
                    pass
                else:
                    self._y(m[0x008E])
                    self._compare(r.y,0xFE)
                    self._mark(0xD643)
                    if r.p&C:
                        pass
                    else:
                        self._a(m[0x0004])
                        self._a(r.a | 0x80)
                        m[0x0004]=r.a
                        pass
                    pass
                pass
            else:
                self._y(m[0x008E])
                self._mark(0xD62E)
                if r.p&Z:
                    self._compare(r.a,0x0C)
                    self._mark(0xD63D)
                    if not r.p&C:
                        pass
                    else:
                        self._y(m[0x008E])
                        self._compare(r.y,0xFE)
                        self._mark(0xD643)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x0004])
                            self._a(r.a | 0x80)
                            m[0x0004]=r.a
                            pass
                        pass
                    pass
                else:
                    self._a(m[0x0004])
                    self._a(r.a | 0x40)
                    m[0x0004]=r.a
                    pass
                pass
            pass
        self._a(m[0x0508])
        self._a(r.a | m[0x0004])
        m[0x0508]=r.a
        self._mark(0xD656)
        self._rts();return

    def battle_cursor(self):
        """$D657: battle cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD657)
        self._a(m[0x6F41])
        m[0x000A]=r.a
        self._a(m[0x6F42])
        m[0x000B]=r.a
        self._a(m[0x6F3F])
        m[0x000C]=r.a
        self._a(m[0x6F40])
        m[0x000D]=r.a
        self._a(0x81)
        m[0x0000]=r.a
        self._a(0xD6)
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xD67E)
        yield from self._external(0xD67E,0xF092,None,"tail")
        return

    def unit_at_cursor(self):
        """$D68A: unit at cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD68A)
        self._a(m[0x6F3F])
        m[0x0000]=r.a
        self._a(m[0x6F40])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        self._a(m[0x6F41])
        m[0x0001]=r.a
        self._a(m[0x6F42])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0001]=self._shift(m[0x0001],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=True)
        return (yield from self.local_d6b6())

    def local_d6b6(self):
        """$D6B6: local d6b6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6B6)
        self._y(0x13)
        while True:  # natural loop $D6B8
            self._a(m[(0x0600+r.y)&65535])
            self._compare(r.a,m[0x0000])
            self._mark(0xD6BE)
            if not r.p&Z:
                self._y(r.y-1)
                self._mark(0xD6C9)
                if not r.p&N:
                    continue
                else:
                    pass
                pass
            else:
                self._a(m[(0x0614+r.y)&65535])
                self._compare(r.a,m[0x0001])
                self._mark(0xD6C6)
                if r.p&Z:
                    pass
                else:
                    self._y(r.y-1)
                    self._mark(0xD6C9)
                    if not r.p&N:
                        continue
                    else:
                        pass
                    pass
                pass
            self._mark(0xD6CB)
            self._rts();return

    def map_refresh(self):
        """$D6CC: map refresh; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6CC)
        self._y(m[SELECTED_SLOT])
        self._a(m[(0x0600+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0x0614+r.y)&65535])
        m[0x0011]=r.a
        self._a(m[0x0090])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0000]=r.a
        self._a(m[0x0011])
        self._flag(C,True)
        self._add(m[0x0000],subtract=True)
        self._compare(r.a,0x0F)
        self._mark(0xD6ED)
        if r.p&C:
            self._mark(0xD6CF)
            self._rts();return
        else:
            self._a(m[0x008E])
            self._flag(C,False)
            self._add(0x04)
            self._mark(0xD6F4)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                pass
            else:
                self._a(0x10)
                pass
            m[0x0000]=r.a
            self._a(m[0x0010])
            self._flag(C,True)
            self._add(m[0x0000],subtract=True)
            self._compare(r.a,0x10)
            self._mark(0xD708)
            if r.p&C:
                self._mark(0xD6CF)
                self._rts();return
            else:
                self._y(0x00)
                self._a(m[0x0010])
                self._compare(r.a,0x10)
                self._mark(0xD710)
                if not r.p&C:
                    pass
                else:
                    self._y(0x01)
                    pass
                self._a(m[0x0011])
                self._compare(r.a,0x10)
                self._mark(0xD718)
                if not r.p&C:
                    pass
                else:
                    self._a(r.y)
                    self._a(r.a | 0x02)
                    self._y(r.a)
                    pass
                self._a(m[((m[0xA8]|m[0xA9]<<8)+r.y)&65535])
                m[0x0000]=r.a
                self._a(r.y)
                self._a(r.a ^ 0x01)
                self._y(r.a)
                self._a(m[((m[0xA8]|m[0xA9]<<8)+r.y)&65535])
                self._push(r.a)
                self._a(m[0x0000])
                self._push(r.a)
                self._y(0x37)
                yield from self._external(0xD72E,0xEE07,0xD733,"far_call",40978)
                if r.pc!=0xD733:return  # preserve nonlocal stack return
                self._a(m[0x0010])
                self._a(r.a & 0x0F)
                m[0x0008]=r.a
                self._x(0x00)
                self._a(m[0x0011])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._push(r.a)
                self._a(r.a | m[0x0008])
                self._y(r.a)
                self._a(0x00)
                m[0x0004]=r.a
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0004]=self._shift(m[0x0004],True,rotate=True)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x0004]=self._shift(m[0x0004],True,rotate=True)
                self._flag(C,False)
                self._add(m[0x0002])
                m[0x0002]=r.a
                self._a(m[0x0003])
                self._add(m[0x0004])
                m[0x0003]=r.a
                self._y(0x00)
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[0x0383]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[0x0384]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[0x0388]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                m[0x0389]=r.a
                m[0x0008]=self._shift(m[0x0008],True,rotate=False)
                self._a(0x00)
                m[0x000B]=r.a
                self._a(self._pop())
                r.a=self._shift(r.a,True,rotate=False)
                m[0x000B]=self._shift(m[0x000B],True,rotate=True)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x000B]=self._shift(m[0x000B],True,rotate=True)
                self._flag(C,False)
                self._add(m[0x0008])
                m[0x0382]=r.a
                self._a(m[0x000B])
                self._add(0x20)
                m[0x0381]=r.a
                self._a(m[0x0382])
                self._flag(C,False)
                self._add(0x20)
                m[0x0387]=r.a
                self._a(m[0x0381])
                self._add(0x00)
                m[0x0386]=r.a
                self._a(0x02)
                m[0x0380]=r.a
                self._a(0x02)
                m[0x0385]=r.a
                self._a(m[0x0012])
                self._mark(0xD7AC)
                if r.p&Z:
                    pass
                else:
                    self._a(m[SELECTED_SLOT])
                    m[0x0000]=r.a
                    self._y(0x37)
                    yield from self._external(0xD7B5,0xEE07,0xD7BA,"far_call",40984)
                    if r.pc!=0xD7BA:return  # preserve nonlocal stack return
                    self._a(0xB0)
                    m[0x0000]=r.a
                    self._a(0x01)
                    m[0x0001]=r.a
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0383]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0384]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0388]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0389]=r.a
                    pass
                self._a(self._pop())
                m[0x0000]=r.a
                self._y(0x37)
                yield from self._external(0xD7E0,0xEE07,0xD7E5,"far_call",40981)
                if r.pc!=0xD7E5:return  # preserve nonlocal stack return
                self._a(m[0x0010])
                self._a(r.a & 0x0E)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x0008]=r.a
                self._a(m[0x0011])
                self._a(r.a & 0x0E)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[0x0008])
                self._y(r.a)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x000A]=r.a
                self._a(self._pop())
                m[0x0000]=r.a
                self._a(m[0x008E])
                self._flag(C,False)
                self._add(0x04)
                self._mark(0xD801)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    pass
                else:
                    self._a(0x10)
                    pass
                self._x(r.a)
                self._a(r.a & 0x01)
                self._mark(0xD80F)
                if r.p&Z:
                    pass
                else:
                    self._a(r.x)
                    self._a(r.a & 0x1F)
                    m[0x0004]=r.a
                    self._a(m[0x0010])
                    self._flag(C,True)
                    self._add(m[0x0004],subtract=True)
                    self._mark(0xD81B)
                    if not r.p&Z:
                        self._compare(r.a,0x0F)
                        self._mark(0xD83B)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x000A])
                            self._a(r.a & 0x33)
                            m[0x000A]=r.a
                            self._a(r.y)
                            self._push(r.a)
                            self._y(0x37)
                            yield from self._external(0xD847,0xEE07,0xD84C,"far_call",40981)
                            if r.pc!=0xD84C:return  # preserve nonlocal stack return
                            self._a(self._pop())
                            self._y(r.a)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._a(r.a & 0xCC)
                            self._a(r.a | m[0x000A])
                            m[0x000A]=r.a
                            pass
                        pass
                    else:
                        self._a(m[0x000A])
                        self._a(r.a & 0xCC)
                        m[0x000A]=r.a
                        self._a(r.y)
                        self._push(r.a)
                        self._y(0x37)
                        yield from self._external(0xD827,0xEE07,0xD82C,"far_call",40981)
                        if r.pc!=0xD82C:return  # preserve nonlocal stack return
                        self._a(self._pop())
                        self._y(r.a)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x33)
                        self._a(r.a | m[0x000A])
                        m[0x000A]=r.a
                        pass
                    pass
                self._a(m[0x000A])
                m[0x0000]=r.a
                if not (yield from self._local_call(self.local_d88e,0xD85A,0xD85D)):return
                self._a(m[0x0000])
                m[0x038D]=r.a
                self._a(m[0x0010])
                self._a(r.a & 0x0E)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x0000]=r.a
                self._a(m[0x0011])
                self._a(r.a & 0x0E)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[0x0000])
                self._a(r.a | 0xC0)
                m[0x038C]=r.a
                self._a(0x23)
                m[0x038B]=r.a
                self._a(0x01)
                m[0x038A]=r.a
                self._a(0xFF)
                m[0x038E]=r.a
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x04)
                m[PPU_JOBS]=r.a
                self._mark(0xD88D)
                self._rts();return

    def local_d88e(self):
        """$D88E: local d88e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD88E)
        self._a(m[0x0010])
        self._a(r.a & 0x1E)
        m[0x0002]=r.a
        self._a(m[0x0011])
        self._a(r.a & 0x1E)
        m[0x0003]=r.a
        self._y(0x13)
        while True:  # natural loop $D89C
            self._a(m[0x0012])
            self._mark(0xD89E)
            if not r.p&Z:
                if not (yield from self._local_call(self.local_d8ac,0xD8A5,0xD8A8)):return
                pass
            else:
                self._compare(r.y,m[SELECTED_SLOT])
                self._mark(0xD8A3)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.local_d8ac,0xD8A5,0xD8A8)):return
                    pass
                pass
            self._y(r.y-1)
            self._mark(0xD8A9)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xD8AB)
            self._rts();return

    def local_d8ac(self):
        """$D8AC: local d8ac; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD8AC)
        self._a(m[0x008E])
        self._flag(C,False)
        self._add(0x04)
        self._mark(0xD8B1)
        if not r.p&C:
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            pass
        else:
            self._a(0x10)
            pass
        self._x(r.a)
        self._a(r.a & 0x01)
        self._mark(0xD8BF)
        if r.p&Z:
            self._a(m[0x0002])
            self._compare(r.a,m[(0x0600+r.y)&65535])
            self._mark(0xD8DC)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0003])
                self._compare(r.a,m[(0x0614+r.y)&65535])
                self._mark(0xD8E3)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0000])
                    self._a(r.a & 0xFC)
                    self._a(r.a | 0x02)
                    m[0x0000]=r.a
                    pass
                pass
            m[0x0002]=self._nz(m[0x0002]+1)
            self._a(m[0x0002])
            self._compare(r.a,m[(0x0600+r.y)&65535])
            self._mark(0xD8F4)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0003])
                self._compare(r.a,m[(0x0614+r.y)&65535])
                self._mark(0xD8FB)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0000])
                    self._a(r.a & 0xF3)
                    self._a(r.a | 0x08)
                    m[0x0000]=r.a
                    pass
                pass
            m[0x0003]=self._nz(m[0x0003]+1)
            self._a(m[0x0002])
            self._compare(r.a,m[(0x0600+r.y)&65535])
            self._mark(0xD90C)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0003])
                self._compare(r.a,m[(0x0614+r.y)&65535])
                self._mark(0xD913)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0000])
                    self._a(r.a & 0x3F)
                    self._a(r.a | 0x80)
                    m[0x0000]=r.a
                    pass
                pass
            m[0x0002]=self._nz(m[0x0002]-1)
            self._a(m[0x0002])
            self._compare(r.a,m[(0x0600+r.y)&65535])
            self._mark(0xD924)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0003])
                self._compare(r.a,m[(0x0614+r.y)&65535])
                self._mark(0xD92B)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0000])
                    self._a(r.a & 0xCF)
                    self._a(r.a | 0x20)
                    m[0x0000]=r.a
                    pass
                pass
            m[0x0003]=self._nz(m[0x0003]-1)
            self._mark(0xD937)
            self._rts();return
        else:
            self._a(r.x)
            self._a(r.a & 0x1F)
            m[0x0004]=r.a
            self._a(m[0x0010])
            self._flag(C,True)
            self._add(m[0x0004],subtract=True)
            self._mark(0xD8CB)
            if not r.p&Z:
                self._compare(r.a,0x0F)
                self._mark(0xD8D2)
                if not r.p&Z:
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD8DC)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD8E3)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xFC)
                            self._a(r.a | 0x02)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0002]=self._nz(m[0x0002]+1)
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD8F4)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD8FB)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xF3)
                            self._a(r.a | 0x08)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0003]=self._nz(m[0x0003]+1)
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD90C)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD913)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0x3F)
                            self._a(r.a | 0x80)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0002]=self._nz(m[0x0002]-1)
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD924)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD92B)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xCF)
                            self._a(r.a | 0x20)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0003]=self._nz(m[0x0003]-1)
                    self._mark(0xD937)
                    self._rts();return
                else:
                    self._a(m[0x0010])
                    m[0x0002]=r.a
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD941)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD948)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xFC)
                            self._a(r.a | 0x02)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0003]=self._nz(m[0x0003]+1)
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD959)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD960)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xCF)
                            self._a(r.a | 0x20)
                            m[0x0000]=r.a
                            pass
                        pass
                    self._a(m[0x0002])
                    self._flag(C,True)
                    self._add(0x0F,subtract=True)
                    m[0x0002]=r.a
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD976)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD97D)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0x3F)
                            self._a(r.a | 0x80)
                            m[0x0000]=r.a
                            pass
                        pass
                    m[0x0003]=self._nz(m[0x0003]-1)
                    self._a(m[0x0002])
                    self._compare(r.a,m[(0x0600+r.y)&65535])
                    self._mark(0xD98E)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0003])
                        self._compare(r.a,m[(0x0614+r.y)&65535])
                        self._mark(0xD995)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0000])
                            self._a(r.a & 0xF3)
                            self._a(r.a | 0x08)
                            m[0x0000]=r.a
                            pass
                        pass
                    self._a(m[0x0002])
                    self._flag(C,False)
                    self._add(0x0F)
                    m[0x0002]=r.a
                    self._mark(0xD9A6)
                    self._rts();return
            else:
                self._a(m[0x0010])
                m[0x0002]=r.a
                self._a(m[0x0002])
                self._flag(C,False)
                self._add(0x0F)
                m[0x0002]=r.a
                self._a(m[0x0002])
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xD9B7)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0003])
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xD9BE)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        self._a(r.a & 0xFC)
                        self._a(r.a | 0x02)
                        m[0x0000]=r.a
                        pass
                    pass
                m[0x0003]=self._nz(m[0x0003]+1)
                self._a(m[0x0002])
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xD9CF)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0003])
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xD9D6)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        self._a(r.a & 0xCF)
                        self._a(r.a | 0x20)
                        m[0x0000]=r.a
                        pass
                    pass
                self._a(m[0x0002])
                self._flag(C,True)
                self._add(0x0F,subtract=True)
                m[0x0002]=r.a
                self._a(m[0x0002])
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xD9EC)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0003])
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xD9F3)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        self._a(r.a & 0x3F)
                        self._a(r.a | 0x80)
                        m[0x0000]=r.a
                        pass
                    pass
                m[0x0003]=self._nz(m[0x0003]-1)
                self._a(m[0x0002])
                self._compare(r.a,m[(0x0600+r.y)&65535])
                self._mark(0xDA05)
                if not r.p&Z:
                    pass
                else:
                    self._a(m[0x0003])
                    self._compare(r.a,m[(0x0614+r.y)&65535])
                    self._mark(0xDA0C)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0000])
                        self._a(r.a & 0xF3)
                        self._a(r.a | 0x08)
                        m[0x0000]=r.a
                        pass
                    pass
                self._mark(0xDA16)
                self._rts();return

    def local_da17(self):
        """$DA17: local da17; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA17)
        self._a(m[0x0090])
        m[0x0000]=r.a
        self._a(m[0x0091])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        self._a(m[0x008E])
        m[0x0001]=r.a
        self._a(m[0x008F])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0001]=self._shift(m[0x0001],False,rotate=True)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        self._a(m[0x6F41])
        m[0x0002]=r.a
        self._a(m[0x6F42])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=True)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        self._a(m[0x6F3F])
        m[0x0003]=r.a
        self._a(m[0x6F40])
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0003]=self._shift(m[0x0003],False,rotate=True)
        m[0x0003]=self._shift(m[0x0003],False,rotate=False)
        m[0x0003]=self._shift(m[0x0003],False,rotate=False)
        m[0x0003]=self._shift(m[0x0003],False,rotate=False)
        self._mark(0xDA59)
        self._rts();return

    def local_da5a(self):
        """$DA5A: local da5a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA5A)
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        m[0x0000]=self._shift(m[0x0000],True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._a(0x00)
        m[0x0003]=r.a
        m[0x0002]=self._shift(m[0x0002],True,rotate=False)
        m[0x0003]=self._shift(m[0x0003],True,rotate=True)
        m[0x0002]=self._shift(m[0x0002],True,rotate=False)
        m[0x0003]=self._shift(m[0x0003],True,rotate=True)
        m[0x0002]=self._shift(m[0x0002],True,rotate=False)
        m[0x0003]=self._shift(m[0x0003],True,rotate=True)
        m[0x0002]=self._shift(m[0x0002],True,rotate=False)
        m[0x0003]=self._shift(m[0x0003],True,rotate=True)
        self._mark(0xDA82)
        self._rts();return

    def local_da83(self):
        """$DA83: local da83; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA83)
        self._a(0x00)
        m[0x000A]=r.a
        m[0x000B]=r.a
        m[0x000C]=r.a
        self._x(0x13)
        while True:  # natural loop $DA90
            self._a(m[(0x0628+r.x)&65535])
            self._mark(0xDA93)
            if r.p&N:
                pass
            else:
                self._a(m[(0x0664+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xDA9A)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xDA9C,0xF2D7,0xDA9F,"call",None)
                    if r.pc!=0xDA9F:return  # preserve nonlocal stack return
                    self._y(0x09)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    m[0x0002]=r.a
                    self._y(0x08)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x000B])
                    m[0x000B]=r.a
                    self._a(m[0x000C])
                    self._add(m[0x0002])
                    m[0x000C]=r.a
                    m[0x000A]=self._nz(m[0x000A]+1)
                    pass
                pass
            self._x(r.x-1)
            self._mark(0xDAC0)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xDAC2)
            self._rts();return

    def local_dac3(self):
        """$DAC3: local dac3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDAC3)
        self._a(0x00)
        m[0x000A]=r.a
        m[0x000B]=r.a
        m[0x000C]=r.a
        self._x(0x13)
        while True:  # natural loop $DAD0
            self._a(m[(0x0628+r.x)&65535])
            self._mark(0xDAD3)
            if not r.p&N:
                pass
            else:
                self._a(m[(0x0664+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xDADA)
                if r.p&Z:
                    pass
                else:
                    yield from self._external(0xDADC,0xF2D7,0xDADF,"call",None)
                    if r.pc!=0xDADF:return  # preserve nonlocal stack return
                    self._y(0x09)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x03)
                    m[0x0002]=r.a
                    self._y(0x08)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x000B])
                    m[0x000B]=r.a
                    self._a(m[0x000C])
                    self._add(m[0x0002])
                    m[0x000C]=r.a
                    m[0x000A]=self._nz(m[0x000A]+1)
                    pass
                pass
            self._x(r.x-1)
            self._mark(0xDB00)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xDB02)
            self._rts();return

    def refresh_hundred_troops(self):
        """$DB03: refresh hundred troops; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB03)
        self._y(0x31)
        yield from self._external(0xDB05,0xF25F,0xDB08,"call",None)
        if r.pc!=0xDB08:return  # preserve nonlocal stack return
        self._x(0x13)
        while True:  # natural loop $DB0A
            self._a(m[(0x0664+r.x)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xDB0F)
            if r.p&Z:
                pass
            else:
                yield from self._external(0xDB11,0xF2D7,0xDB14,"call",None)
                if r.pc!=0xDB14:return  # preserve nonlocal stack return
                self._a(r.x)
                self._push(r.a)
                self._y(0x08)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._push(r.a)
                self._y(0x09)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x03)
                m[0x0001]=r.a
                self._a(self._pop())
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                self._a(0x64)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                if not (yield from self._local_call(self.divide_24bit,0xDB37,0xDB3A)):return
                self._a(self._pop())
                self._x(r.a)
                self._a(m[0x0000])
                pass
            m[(0x063C+r.x)&65535]=r.a
            self._x(r.x-1)
            self._mark(0xDB43)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xDB45)
            self._rts();return

    def terrain_at_position(self):
        """$DB46: terrain at position; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB46)
        if not (yield from self._local_call(self.raw_terrain_at_position,0xDB46,0xDB49)):return
        self._compare(r.a,0x06)
        self._mark(0xDB4B)
        if not r.p&C:
            pass
        else:
            self._a(0x02)
            pass
        self._mark(0xDB4F)
        self._rts();return

    def raw_terrain_at_position(self):
        """$DB50: raw terrain at position; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB50)
        self._y(0x00)
        self._a(m[0x0010])
        self._compare(r.a,0x10)
        self._mark(0xDB57)
        if not r.p&C:
            pass
        else:
            self._y(0x01)
            pass
        self._a(m[0x0011])
        self._compare(r.a,0x10)
        self._mark(0xDB60)
        if not r.p&C:
            pass
        else:
            self._a(r.y)
            self._a(r.a | 0x02)
            self._y(r.a)
            pass
        self._a(m[((m[0xA8]|m[0xA9]<<8)+r.y)&65535])
        m[0x0000]=r.a
        self._y(0x37)
        yield from self._external(0xDB6D,0xEE07,0xDB72,"far_call",40978)
        if r.pc!=0xDB72:return  # preserve nonlocal stack return
        self._a(0x9E)
        m[0x0002]=r.a
        self._a(0xDB)
        m[0x0003]=r.a
        self._a(m[0x0010])
        self._a(r.a & 0x0F)
        m[0x0008]=r.a
        self._x(0x00)
        self._a(m[0x0011])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0008])
        self._y(r.a)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._y(r.a)
        self._compare(r.a,0x80)
        self._mark(0xDB96)
        if not r.p&C:
            self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
            self._mark(0xDB9D)
            self._rts();return
        else:
            self._a(0x00)
            self._mark(0xDB9A)
            self._rts();return

    def local_dc1e(self):
        """$DC1E: local dc1e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC1E)
        self._y(0x13)
        while True:  # natural loop $DC20
            self._a(m[(0x0664+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xDC25)
            if not r.p&Z:
                pass
            else:
                self._a(0xFF)
                m[(0x0600+r.y)&65535]=r.a
                m[(0x0614+r.y)&65535]=r.a
                pass
            self._y(r.y-1)
            self._mark(0xDC30)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xDC32)
            self._rts();return

    def local_dc33(self):
        """$DC33: local dc33; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC33)
        self._y(m[SELECTED_SLOT])
        return (yield from self.local_dc36())

    def local_dc36(self):
        """$DC36: local dc36; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC36)
        self._a(m[(0x0664+r.y)&65535])
        m[0x0000]=r.a
        self._a(0xA7)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xDC45,0xEE07,0xDC4A,"far_call",40960)
        if r.pc!=0xDC4A:return  # preserve nonlocal stack return
        self._mark(0xDC4A)
        self._rts();return

    def target_side_filter(self):
        """$DC4B: target side filter; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC4B)
        self._a(m[SIDE])
        self._mark(0xDC4E)
        if r.p&N:
            self._a(m[(0x0628+r.y)&65535])
            self._mark(0xDC5E)
            if not r.p&N:
                self._a(0xFF)
                self._mark(0xDC5A)
                self._rts();return
            else:
                self._a(0x00)
                self._mark(0xDC62)
                self._rts();return
        else:
            self._a(m[(0x0628+r.y)&65535])
            self._mark(0xDC53)
            if r.p&N:
                self._a(0xFF)
                self._mark(0xDC5A)
                self._rts();return
            else:
                self._a(0x00)
                self._mark(0xDC57)
                self._rts();return

    def dialog_highlight(self):
        """$DC63: dialog highlight; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC63)
        self._a(0xD8)
        m[0x000A]=r.a
        self._a(0xA0)
        m[0x000C]=r.a
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xDC7F)
        if not r.p&Z:
            self._mark(0xDC93)
            self._rts();return
        else:
            self._a(0x94)
            m[0x0000]=r.a
            self._a(0xDC)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._mark(0xDC90)
            yield from self._external(0xDC90,0xF1AD,None,"tail")
            return

    def alternate_highlight(self):
        """$DC70: alternate highlight; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC70)
        self._a(0xE0)
        m[0x000A]=r.a
        self._a(0xA0)
        m[0x000C]=r.a
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xDC7F)
        if not r.p&Z:
            self._mark(0xDC93)
            self._rts();return
        else:
            self._a(0x94)
            m[0x0000]=r.a
            self._a(0xDC)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._mark(0xDC90)
            yield from self._external(0xDC90,0xF1AD,None,"tail")
            return

    def initialize_battle_arrays(self):
        """$DC99: initialize battle arrays; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC99)
        self._y(0x31)
        yield from self._external(0xDC9B,0xF25F,0xDC9E,"call",None)
        if r.pc!=0xDC9E:return  # preserve nonlocal stack return
        self._a(m[0x0402])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0x9D5A+r.y)&65535])
        self._flag(C,True)
        self._add(0x80,subtract=True)
        m[0x0512]=r.a
        self._a(m[(0x9D5B+r.y)&65535])
        self._add(0x00,subtract=True)
        m[0x0513]=r.a
        self._mark(0xDCB5)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0512]=r.a
            m[0x0513]=r.a
            pass
        self._a(m[0x0513])
        self._mark(0xDCC2)
        if r.p&Z:
            pass
        else:
            self._a(0xFE)
            m[0x0512]=r.a
            self._a(0x00)
            m[0x0513]=r.a
            pass
        self._a(m[(0x9D58+r.y)&65535])
        self._flag(C,True)
        self._add(0x60,subtract=True)
        m[0x0510]=r.a
        self._a(m[(0x9D59+r.y)&65535])
        self._add(0x00,subtract=True)
        m[0x0511]=r.a
        self._mark(0xDCDF)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            m[0x0510]=r.a
            m[0x0511]=r.a
            pass
        self._a(m[0x0510])
        self._compare(r.a,0x90)
        self._mark(0xDCEE)
        if not r.p&C:
            pass
        else:
            self._a(0x8E)
            m[0x0510]=r.a
            self._a(0x00)
            m[0x0511]=r.a
            pass
        self._a(m[0x0402])
        m[0x052A]=r.a
        self._a(0x00)
        m[0x050C]=r.a
        m[0x050D]=r.a
        m[0x051A]=r.a
        m[0x051B]=r.a
        m[0x051C]=r.a
        m[0x051D]=r.a
        m[0x051E]=r.a
        m[0x051F]=r.a
        m[0x0520]=r.a
        m[0x0521]=r.a
        self._a(0xFF)
        m[0x052B]=r.a
        self._y(0x27)
        self._a(0xFF)
        while True:  # natural loop $DD29
            m[(0x6F47+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xDD2D)
            if not r.p&N:
                continue
            else:
                pass
            self._x(0x13)
            while True:  # natural loop $DD31
                self._a(m[(0x0664+r.x)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xDD36)
                if r.p&Z:
                    m[(0x0600+r.x)&65535]=r.a
                    m[(0x0614+r.x)&65535]=r.a
                    m[(0x0628+r.x)&65535]=r.a
                    m[(0x063C+r.x)&65535]=r.a
                    m[(0x0650+r.x)&65535]=r.a
                    pass
                else:
                    yield from self._external(0xDD38,0xF2D7,0xDD3B,"call",None)
                    if r.pc!=0xDD3B:return  # preserve nonlocal stack return
                    self._a(0xFF)
                    m[(0x0600+r.x)&65535]=r.a
                    m[(0x0614+r.x)&65535]=r.a
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._a(r.a & 0x03)
                    self._compare(r.x,0x0A)
                    self._mark(0xDD4D)
                    if not r.p&C:
                        pass
                    else:
                        self._a(r.a | 0x80)
                        pass
                    m[(0x0628+r.x)&65535]=r.a
                    self._a(0x00)
                    m[(0x0650+r.x)&65535]=r.a
                    pass
                self._x(r.x-1)
                self._mark(0xDD6C)
                if not r.p&N:
                    continue
                else:
                    pass
                if not (yield from self._local_call(self.refresh_hundred_troops,0xDD6E,0xDD71)):return
                self._mark(0xDD71)
                self._rts();return

    def commander_outcome(self):
        """$DD72: commander outcome; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD72)
        self._x(0x00)
        self._a(m[0x0664])
        self._compare(r.a,0xFF)
        self._mark(0xDD79)
        if r.p&Z:
            self._a(0x00)
            m[0x0514]=r.a
            self._a(m[0x052B])
            self._compare(r.a,0xFF)
            self._mark(0xDD8A)
            if not r.p&Z:
                self._a(0x0C)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._a(self._pop())
                self._a(self._pop())
                self._mark(0xDDB8)
                self._rts();return
            else:
                self._a(0x07)
                m[STATE]=r.a
                self._a(0x02)
                m[PHASE]=r.a
                self._a(self._pop())
                self._a(self._pop())
                self._a(m[RULERS])
                self._a(r.a & 0x0F)
                m[0x042C]=r.a
                self._a(0x00)
                if not (yield from self._local_call(self.local_de82,0xDDCF,0xDDD2)):return
                self._mark(0xDDD2)
                if r.p&C:
                    m[SELECTED_SLOT]=r.y
                    self._a(m[RULERS])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    if not (yield from self._local_call(self.ruler_pointer,0xDDE1,0xDDE4)):return
                    self._y(0x03)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x03)
                    self._mark(0xDDEA)
                    if not r.p&Z:
                        m[0x6F44]=r.a
                        self._a(m[RULERS])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        m[0x042C]=r.a
                        self._a(0x0A)
                        m[SELECTED_SLOT]=r.a
                        self._a(0x03)
                        m[0x00A4]=r.a
                        self._a(0x53)
                        m[ACTOR_SLOT]=r.a
                        self._mark(0xDE13)
                        self._rts();return
                    else:
                        self._a(0x04)
                        m[0x00A4]=r.a
                        self._a(0x54)
                        m[ACTOR_SLOT]=r.a
                        self._mark(0xDDF6)
                        self._rts();return
                else:
                    self._a(m[0x042C])
                    if not (yield from self._local_call(self.ruler_pointer,0xDE70,0xDE73)):return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x042C]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x55)
                    self._mark(0xDE7F)
                    yield from self._external(0xDE7F,0xF293,None,"tail")
                    return
        else:
            self._a(m[0x0628])
            self._mark(0xDD7E)
            if not r.p&N:
                self._x(r.x+1)
                self._a(m[0x066E])
                self._compare(r.a,0xFF)
                self._mark(0xDD95)
                if r.p&Z:
                    self._a(0x01)
                    m[0x0514]=r.a
                    self._a(m[0x052B])
                    self._compare(r.a,0xFF)
                    self._mark(0xDDA6)
                    if not r.p&Z:
                        self._a(0x0C)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(self._pop())
                        self._a(self._pop())
                        self._mark(0xDDB8)
                        self._rts();return
                    else:
                        self._a(0x07)
                        m[STATE]=r.a
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(m[RULERS])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        m[0x042C]=r.a
                        self._a(0x80)
                        if not (yield from self._local_call(self.local_de82,0xDE2C,0xDE2F)):return
                        self._mark(0xDE2F)
                        if r.p&C:
                            m[SELECTED_SLOT]=r.y
                            self._a(m[RULERS])
                            self._a(r.a & 0x0F)
                            if not (yield from self._local_call(self.ruler_pointer,0xDE3C,0xDE3F)):return
                            self._y(0x03)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._compare(r.a,0x03)
                            self._mark(0xDE45)
                            if not r.p&Z:
                                m[0x6F44]=r.a
                                self._a(m[RULERS])
                                self._a(r.a & 0x0F)
                                m[0x042C]=r.a
                                self._a(0x00)
                                m[SELECTED_SLOT]=r.a
                                self._a(0x03)
                                m[0x00A4]=r.a
                                self._a(0x53)
                                m[ACTOR_SLOT]=r.a
                                self._mark(0xDE6C)
                                self._rts();return
                            else:
                                self._a(0x04)
                                m[0x00A4]=r.a
                                self._a(0x54)
                                m[ACTOR_SLOT]=r.a
                                self._mark(0xDE51)
                                self._rts();return
                        else:
                            self._a(m[0x042C])
                            if not (yield from self._local_call(self.ruler_pointer,0xDE70,0xDE73)):return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x042C]=r.a
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x55)
                            self._mark(0xDE7F)
                            yield from self._external(0xDE7F,0xF293,None,"tail")
                            return
                else:
                    self._a(m[0x0632])
                    self._mark(0xDD9A)
                    if r.p&N:
                        self._mark(0xDDAB)
                        self._rts();return
                    else:
                        self._a(0x01)
                        m[0x0514]=r.a
                        self._a(m[0x052B])
                        self._compare(r.a,0xFF)
                        self._mark(0xDDA6)
                        if not r.p&Z:
                            self._a(0x0C)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            self._a(self._pop())
                            self._a(self._pop())
                            self._mark(0xDDB8)
                            self._rts();return
                        else:
                            self._a(0x07)
                            m[STATE]=r.a
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._a(self._pop())
                            self._a(self._pop())
                            self._a(m[RULERS])
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            m[0x042C]=r.a
                            self._a(0x80)
                            if not (yield from self._local_call(self.local_de82,0xDE2C,0xDE2F)):return
                            self._mark(0xDE2F)
                            if r.p&C:
                                m[SELECTED_SLOT]=r.y
                                self._a(m[RULERS])
                                self._a(r.a & 0x0F)
                                if not (yield from self._local_call(self.ruler_pointer,0xDE3C,0xDE3F)):return
                                self._y(0x03)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._compare(r.a,0x03)
                                self._mark(0xDE45)
                                if not r.p&Z:
                                    m[0x6F44]=r.a
                                    self._a(m[RULERS])
                                    self._a(r.a & 0x0F)
                                    m[0x042C]=r.a
                                    self._a(0x00)
                                    m[SELECTED_SLOT]=r.a
                                    self._a(0x03)
                                    m[0x00A4]=r.a
                                    self._a(0x53)
                                    m[ACTOR_SLOT]=r.a
                                    self._mark(0xDE6C)
                                    self._rts();return
                                else:
                                    self._a(0x04)
                                    m[0x00A4]=r.a
                                    self._a(0x54)
                                    m[ACTOR_SLOT]=r.a
                                    self._mark(0xDE51)
                                    self._rts();return
                            else:
                                self._a(m[0x042C])
                                if not (yield from self._local_call(self.ruler_pointer,0xDE70,0xDE73)):return
                                self._y(0x00)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x042C]=r.a
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(0x55)
                                self._mark(0xDE7F)
                                yield from self._external(0xDE7F,0xF293,None,"tail")
                                return
            else:
                self._a(0x00)
                m[0x0514]=r.a
                self._a(m[0x052B])
                self._compare(r.a,0xFF)
                self._mark(0xDD8A)
                if not r.p&Z:
                    self._a(0x0C)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(self._pop())
                    self._a(self._pop())
                    self._mark(0xDDB8)
                    self._rts();return
                else:
                    self._a(0x07)
                    m[STATE]=r.a
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._a(self._pop())
                    self._a(self._pop())
                    self._a(m[RULERS])
                    self._a(r.a & 0x0F)
                    m[0x042C]=r.a
                    self._a(0x00)
                    if not (yield from self._local_call(self.local_de82,0xDDCF,0xDDD2)):return
                    self._mark(0xDDD2)
                    if r.p&C:
                        m[SELECTED_SLOT]=r.y
                        self._a(m[RULERS])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        if not (yield from self._local_call(self.ruler_pointer,0xDDE1,0xDDE4)):return
                        self._y(0x03)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x03)
                        self._mark(0xDDEA)
                        if not r.p&Z:
                            m[0x6F44]=r.a
                            self._a(m[RULERS])
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            m[0x042C]=r.a
                            self._a(0x0A)
                            m[SELECTED_SLOT]=r.a
                            self._a(0x03)
                            m[0x00A4]=r.a
                            self._a(0x53)
                            m[ACTOR_SLOT]=r.a
                            self._mark(0xDE13)
                            self._rts();return
                        else:
                            self._a(0x04)
                            m[0x00A4]=r.a
                            self._a(0x54)
                            m[ACTOR_SLOT]=r.a
                            self._mark(0xDDF6)
                            self._rts();return
                    else:
                        self._a(m[0x042C])
                        if not (yield from self._local_call(self.ruler_pointer,0xDE70,0xDE73)):return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x042C]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x55)
                        self._mark(0xDE7F)
                        yield from self._external(0xDE7F,0xF293,None,"tail")
                        return

    def local_de82(self):
        """$DE82: local de82; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDE82)
        m[0x0002]=r.a
        self._y(0x00)
        while True:  # natural loop $DE87
            self._a(m[(0x0628+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xDE8C)
            if r.p&Z:
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xDE98)
                if not r.p&C:
                    continue
                else:
                    self._flag(C,False)
                    self._mark(0xDE9B)
                    self._rts();return
            else:
                self._a(r.a & 0x80)
                self._compare(r.a,m[0x0002])
                self._mark(0xDE93)
                if r.p&Z:
                    self._flag(C,True)
                    self._mark(0xDE9D)
                    self._rts();return
                else:
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    self._mark(0xDE98)
                    if not r.p&C:
                        continue
                    else:
                        self._flag(C,False)
                        self._mark(0xDE9B)
                        self._rts();return

    def local_de9e(self):
        """$DE9E: local de9e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDE9E)
        self._y(0x30)
        yield from self._external(0xDEA0,0xF25F,0xDEA3,"call",None)
        if r.pc!=0xDEA3:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        while True:  # natural loop $DEAA
            self._a(m[(0x9D72+r.y)&65535])
            self._mark(0xDEAD)
            if r.p&N:
                self._a(0x00)
                self._mark(0xDEBE)
                self._rts();return
            else:
                self._compare(r.a,m[0x052A])
                self._mark(0xDEB2)
                if r.p&Z:
                    self._a(m[(0x9E62+r.y)&65535])
                    self._mark(0xDEBB)
                    self._rts();return
                else:
                    self._y(r.y+1)
                    continue

    def local_debf(self):
        """$DEBF: local debf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDEBF)
        self._y(0x30)
        yield from self._external(0xDEC1,0xF25F,0xDEC4,"call",None)
        if r.pc!=0xDEC4:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        while True:  # natural loop $DECB
            self._a(m[(0x9D72+r.y)&65535])
            self._mark(0xDECE)
            if r.p&N:
                self._a(0x00)
                self._mark(0xDEE8)
                self._rts();return
            else:
                self._compare(r.a,m[0x052A])
                self._mark(0xDED3)
                if r.p&Z:
                    self._a(r.y)
                    self._push(r.a)
                    self._y(0x31)
                    yield from self._external(0xDEDD,0xF25F,0xDEE0,"call",None)
                    if r.pc!=0xDEE0:return  # preserve nonlocal stack return
                    self._a(self._pop())
                    self._y(r.a)
                    self._a(m[(0x9AB4+r.y)&65535])
                    self._mark(0xDEE5)
                    self._rts();return
                else:
                    self._y(r.y+1)
                    continue

    def local_dee9(self):
        """$DEE9: local dee9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDEE9)
        self._a(m[0x042C])
        yield from self._external(0xDEEC,0xF2D7,0xDEEF,"call",None)
        if r.pc!=0xDEEF:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0xF0)
        self._compare(r.a,m[0x052C])
        self._mark(0xDEF8)
        if r.p&Z:
            self._flag(C,False)
            self._mark(0xDF26)
            self._rts();return
        else:
            self._y(0x01)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x052E],subtract=True)
            m[0x042F]=r.a
            self._a(0x00)
            m[0x042D]=r.a
            m[0x0430]=r.a
            m[0x0431]=r.a
            self._y(0x28)
            yield from self._external(0xDF12,0xEE07,0xDF17,"far_call",40984)
            if r.pc!=0xDF17:return  # preserve nonlocal stack return
            self._a(0x4A)
            self._y(m[0x042F])
            self._mark(0xDF1C)
            if not r.p&Z:
                pass
            else:
                self._a(0x4D)
                pass
            yield from self._external(0xDF20,0xF293,0xDF23,"call",None)
            if r.pc!=0xDF23:return  # preserve nonlocal stack return
            self._flag(C,True)
            self._mark(0xDF24)
            self._rts();return

    def text_readiness(self):
        """$DF27: text readiness; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF27)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xDF2C)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xDF38)
            self._rts();return
        else:
            self._a(m[0x0300])
            self._compare(r.a,0xFF)
            self._mark(0xDF33)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xDF38)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xDF36)
                self._rts();return

    def select_battle_IRQ_layout(self):
        """$DF39: select battle IRQ layout; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF39)
        self._a(m[0x0518])
        self._mark(0xDF3C)
        if not r.p&Z:
            pass
        else:
            self._a(0x68)
            m[0x0068]=r.a
            self._a(0xE4)
            m[0x0069]=r.a
            self._a(0x96)
            m[0x006A]=r.a
            self._a(0xEF)
            m[0x006B]=r.a
            self._a(0x30)
            m[0x006C]=r.a
            self._a(0xF2)
            m[0x006D]=r.a
            self._a(0x40)
            m[0x006E]=r.a
            self._a(0xEA)
            m[0x006F]=r.a
            self._a(0x20)
            m[0x0070]=r.a
            self._a(0xF8)
            m[0x0071]=r.a
            self._a(0x07)
            m[0x0061]=r.a
            self._a(0xFF)
            m[0x0518]=r.a
            pass
        self._a(m[0x0518])
        self._compare(r.a,0x01)
        self._mark(0xDF74)
        if not r.p&Z:
            pass
        else:
            self._a(0x72)
            m[0x0068]=r.a
            self._a(0xAF)
            m[0x0069]=r.a
            self._a(0x05)
            m[0x0061]=r.a
            self._a(0xFF)
            m[0x0518]=r.a
            pass
        self._mark(0xDF87)
        self._rts();return

    def adjust_battle_IRQ_delay(self):
        """$DF88: adjust battle IRQ delay; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF88)
        self._a(m[0x0061])
        self._compare(r.a,0x05)
        self._mark(0xDF8C)
        if not r.p&Z:
            self._mark(0xDF9D)
            self._rts();return
        else:
            self._a(m[0x008E])
            self._compare(r.a,0x10)
            self._mark(0xDF92)
            if r.p&C:
                self._a(0x74)
                m[0x0068]=r.a
                self._mark(0xDF9D)
                self._rts();return
            else:
                self._a(0x72)
                m[0x0068]=r.a
                self._mark(0xDF98)
                self._rts();return

    def random_four(self):
        """$E850: random four; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xE850)
        yield from self._external(0xE850,0xE87A,0xE853,"call",None)
        if r.pc!=0xE853:return  # preserve nonlocal stack return
        self._a(r.a & 0x03)
        self._mark(0xE855)
        self._rts();return

    def random_eight(self):
        """$E856: random eight; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xE856)
        yield from self._external(0xE856,0xE87A,0xE859,"call",None)
        if r.pc!=0xE859:return  # preserve nonlocal stack return
        self._a(r.a & 0x07)
        self._mark(0xE85B)
        self._rts();return

    def random_bounded(self):
        """$E862: random bounded; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xE862)
        m[0x0010]=r.a
        self._compare(r.a,0x0F)
        self._mark(0xE866)
        if r.p&C:
            while True:  # natural loop $E872
                yield from self._external(0xE872,0xE87A,0xE875,"call",None)
                if r.pc!=0xE875:return  # preserve nonlocal stack return
                self._compare(r.a,m[0x0010])
                self._mark(0xE877)
                if r.p&C:
                    continue
                else:
                    pass
                self._mark(0xE879)
                self._rts();return
        else:
            while True:  # natural loop $E868
                yield from self._external(0xE868,0xE87A,0xE86B,"call",None)
                if r.pc!=0xE86B:return  # preserve nonlocal stack return
                self._a(r.a & 0x0F)
                self._compare(r.a,m[0x0010])
                self._mark(0xE86F)
                if r.p&C:
                    continue
                else:
                    pass
                self._mark(0xE871)
                self._rts();return

    def divide_word(self):
        """$EA7C: divide word; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xEA7C)
        self._a(0x00)
        m[0x0005]=r.a
        m[0x0006]=r.a
        self._y(0x0F)
        while True:  # natural loop $EA84
            m[0x0001]=self._shift(m[0x0001],True,rotate=False)
            m[0x0002]=self._shift(m[0x0002],True,rotate=True)
            m[0x0005]=self._shift(m[0x0005],True,rotate=True)
            m[0x0006]=self._shift(m[0x0006],True,rotate=True)
            self._a(m[0x0005])
            self._flag(C,True)
            self._add(m[0x0003],subtract=True)
            m[0x0007]=r.a
            self._a(m[0x0006])
            self._add(m[0x0004],subtract=True)
            self._mark(0xEA97)
            if not r.p&C:
                pass
            else:
                m[0x0006]=r.a
                self._a(m[0x0007])
                m[0x0005]=r.a
                m[0x0001]=self._nz(m[0x0001]+1)
                pass
            self._y(r.y-1)
            self._mark(0xEAA2)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xEAA4)
            self._rts();return

    def divide_24bit(self):
        """$EAA5: divide 24bit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xEAA5)
        self._a(0x00)
        m[0x0005]=r.a
        m[0x0006]=r.a
        m[0x0007]=r.a
        self._y(0x17)
        while True:  # natural loop $EAAF
            m[0x0000]=self._shift(m[0x0000],True,rotate=False)
            m[0x0001]=self._shift(m[0x0001],True,rotate=True)
            m[0x0002]=self._shift(m[0x0002],True,rotate=True)
            m[0x0005]=self._shift(m[0x0005],True,rotate=True)
            m[0x0006]=self._shift(m[0x0006],True,rotate=True)
            m[0x0007]=self._shift(m[0x0007],True,rotate=True)
            self._a(m[0x0005])
            self._flag(C,True)
            self._add(m[0x0003],subtract=True)
            m[0x0008]=r.a
            self._a(m[0x0006])
            self._add(m[0x0004],subtract=True)
            m[0x0009]=r.a
            self._a(m[0x0007])
            self._add(0x00,subtract=True)
            self._mark(0xEACC)
            if not r.p&C:
                pass
            else:
                m[0x0007]=r.a
                self._a(m[0x0008])
                m[0x0005]=r.a
                self._a(m[0x0009])
                m[0x0006]=r.a
                m[0x0000]=self._nz(m[0x0000]+1)
                pass
            self._y(r.y-1)
            self._mark(0xEADB)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xEADD)
            self._rts();return

    def multiply_24bit(self):
        """$EBE9: multiply 24bit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xEBE9)
        self._y(0x07)
        self._a(0x00)
        m[0x0004]=r.a
        m[0x0005]=r.a
        m[0x0006]=r.a
        m[0x0007]=r.a
        m[0x0008]=r.a
        m[0x0009]=r.a
        while True:  # natural loop $EBF9
            m[0x0003]=self._shift(m[0x0003],False,rotate=False)
            self._mark(0xEBFB)
            if not r.p&C:
                pass
            else:
                self._a(m[0x0000])
                self._flag(C,False)
                self._add(m[0x0006])
                m[0x0006]=r.a
                self._a(m[0x0001])
                self._add(m[0x0007])
                m[0x0007]=r.a
                self._a(m[0x0002])
                self._add(m[0x0008])
                m[0x0008]=r.a
                self._a(m[0x0004])
                self._add(m[0x0009])
                m[0x0009]=r.a
                pass
            m[0x0000]=self._shift(m[0x0000],True,rotate=False)
            m[0x0001]=self._shift(m[0x0001],True,rotate=True)
            m[0x0002]=self._shift(m[0x0002],True,rotate=True)
            m[0x0004]=self._shift(m[0x0004],True,rotate=True)
            self._y(r.y-1)
            self._mark(0xEC1F)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xEC21)
            self._rts();return

    def city_pointer(self):
        """$F2AF: city pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xF2AF)
        self._y(0x00)
        m[0x0001]=r.y
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0001]=self._shift(m[0x0001],True,rotate=True)
        self._flag(C,False)
        self._add(0x00)
        m[0x0000]=r.a
        self._a(m[0x0001])
        self._add(0x60)
        m[0x0001]=r.a
        self._mark(0xF2D6)
        self._rts();return

    def ruler_pointer(self):
        """$F368: ruler pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xF368)
        self._a(r.a & 0x0F)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xF379+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xF37A+r.y)&65535])
        m[0x0001]=r.a
        self._mark(0xF378)
        self._rts();return

    def attack_target(self):
        """Main2 alias of original shared main2/3 A293 controller."""
        return (yield from self.attack_confirmation())
