"""Readable, bounded bank14/15 normal-attack scene controller.

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
STATE,PHASE,CONTROL,BACKGROUND=0x540,0x541,0x542,0x544
OBJECT_INDEX,ACTION_CLASS,ACTION_CURSOR,SCAN_CURSOR=0x545,0x546,0x547,0x548
ACTIVE_SIDE,SAVED_STATE,SAVED_PHASE,OBJECT_ACTION=0x549,0x54B,0x54C,0x54F
FIRST_OFFICER,SECOND_OFFICER,FIRST_CONTROLLER,SECOND_CONTROLLER=0x560,0x561,0x562,0x563
FIRST_FORMATION,SECOND_FORMATION=0x56C,0x56D
OBJECT_X,OBJECT_Y,OBJECT_VALUE,OBJECT_ENCODING=0x580,0x596,0x5AC,0x5C2
NEW_BUTTONS,FADE_FLAG,GLOBAL,NMI_SCENE,PPU_JOBS=0x81,0x87,0x7A,0x78,0x7E

@dataclass
class AttackRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA069

class AttackBudgetExceeded(RuntimeError):pass

class AttackSceneController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned attack ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=AttackRegisters();self.events=[];self.pending=None;self._program=None
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
    def _mark(self,pc):
        self.registers.pc=pc;self._blocks+=1
        if self._blocks>self._limit:raise AttackBudgetExceeded('Source control-block budget reached')
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
                try:result=self.services(call)
                except UnsupportedHardware:return self._result('dependency')
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except AttackBudgetExceeded:
                self._program=None;return self._result('budget')
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[CONTROL]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending attack invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def tick_control(self,registers=None,**kwargs):return self.run_entry(0xA069,registers=registers,**kwargs)
    def run_entry(self,entry=0xA000,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing attack invocation first')
        self.registers=registers or AttackRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[CONTROL])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def _entry(self,entry):
        if entry==0xA000:return self.attack_scene_tick()
        elif entry==0xA00F:return self.scene_service_wrapper()
        elif entry==0xA030:return self.participant_cards_then_control()
        elif entry==0xA069:return self.attack_tick()
        elif entry==0xA06C:return self.attack_main_dispatch()
        elif entry==0xA085:return self.setup_and_information()
        elif entry==0xA088:return self.setup_and_information_phase_dispatch()
        elif entry==0xA095:return self.setup_and_information_phase_0()
        elif entry==0xA0D3:return self.setup_and_information_phase_1()
        elif entry==0xA0F9:return self.setup_and_information_phase_2()
        elif entry==0xA119:return self.setup_and_information_phase_3()
        elif entry==0xA137:return self.setup_and_information_phase_4()
        elif entry==0xA15F:return self.formation_action_round()
        elif entry==0xA165:return self.formation_action_round_phase_dispatch()
        elif entry==0xA16E:return self.formation_action_round_phase_0()
        elif entry==0xA183:return self.formation_action_round_phase_1()
        elif entry==0xA235:return self.formation_action_round_phase_2()
        elif entry==0xA2A9:return self.check_round_participant_request()
        elif entry==0xA32F:return self.scan_participant_object()
        elif entry==0xA39D:return self.prepare_selected_object_side()
        elif entry==0xA3BC:return self.result_confirmation()
        elif entry==0xA3BF:return self.result_confirmation_phase_dispatch()
        elif entry==0xA3D0:return self.result_confirmation_phase_0()
        elif entry==0xA3D4:return self.result_confirmation_phase_1()
        elif entry==0xA3F2:return self.result_confirmation_phase_6()
        elif entry==0xA407:return self.result_confirmation_phase_3()
        elif entry==0xA488:return self.result_confirmation_phase_4()
        elif entry==0xA4B5:return self.result_confirmation_phase_5()
        elif entry==0xA4D8:return self.selected_participant_health()
        elif entry==0xA4E6:return self.mark_participant_withdrawal()
        elif entry==0xA4F7:return self.object_action()
        elif entry==0xA500:return self.object_action_phase_dispatch()
        elif entry==0xA519:return self.object_action_phase_0()
        elif entry==0xA5C4:return self.object_action_phase_1()
        elif entry==0xA5F3:return self.object_action_phase_2()
        elif entry==0xA61D:return self.object_action_phase_3()
        elif entry==0xA654:return self.object_action_phase_4()
        elif entry==0xA6D0:return self.set_object_result_phase()
        elif entry==0xA6E4:return self.object_action_phase_5()
        elif entry==0xA702:return self.object_action_phase_6()
        elif entry==0xA72E:return self.object_action_phase_7()
        elif entry==0xA74A:return self.object_action_phase_8()
        elif entry==0xA75B:return self.object_action_phase_9()
        elif entry==0xA7C5:return self.move_active_object()
        elif entry==0xA7E0:return self.object_action_phase_10()
        elif entry==0xA7FE:return self.choose_object_destination()
        elif entry==0xA84D:return self.resolve_object_collision()
        elif entry==0xA871:return self.resolve_object_health_change()
        elif entry==0xA8CF:return self.read_object_pair()
        elif entry==0xA8F2:return self.read_object_parameters()
        elif entry==0xA9A0:return self.commit_object_pair_health()
        elif entry==0xA9BD:return self.test_selected_object_health()
        elif entry==0xA9E6:return self.write_object_map_pair()
        elif entry==0xAA0F:return self.queue_object_redraw()
        elif entry==0xAA23:return self.participant_menu()
        elif entry==0xAA3D:return self.participant_menu_phase_dispatch()
        elif entry==0xAA4A:return self.participant_menu_phase_0()
        elif entry==0xAABD:return self.participant_menu_phase_1()
        elif entry==0xAAF0:return self.participant_menu_phase_2()
        elif entry==0xAB75:return self.participant_menu_phase_3()
        elif entry==0xAB9A:return self.participant_menu_phase_4()
        elif entry==0xABC3:return self.participant_menu_choice()
        elif entry==0xAC73:return self.choose_computer_participant_menu()
        elif entry==0xACA8:return self.change_participant_control()
        elif entry==0xACC5:return self.intelligence_action()
        elif entry==0xACDF:return self.intelligence_action_phase_dispatch()
        elif entry==0xACEC:return self.intelligence_action_phase_0()
        elif entry==0xAD3C:return self.intelligence_action_phase_1()
        elif entry==0xAD5D:return self.intelligence_action_phase_2()
        elif entry==0xAE11:return self.intelligence_action_phase_3()
        elif entry==0xAE8E:return self.intelligence_action_phase_4()
        elif entry==0xAF17:return self.object_action_choice_dispatch()
        elif entry==0xAF26:return self.object_action_move()
        elif entry==0xAFD2:return self.object_action_wait()
        elif entry==0xAFF6:return self.prepare_intelligence_objects()
        elif entry==0xB00E:return self.object_action_advance()
        elif entry==0xB016:return self.advance_action_object()
        elif entry==0xB02E:return self.object_action_evaluate()
        elif entry==0xB036:return self.evaluate_action_object()
        elif entry==0xB066:return self.resolve_action_success()
        elif entry==0xB07C:return self.object_action_success()
        elif entry==0xB084:return self.queue_action_success()
        elif entry==0xB09C:return self.object_action_failure()
        elif entry==0xB0AC:return self.queue_action_failure()
        elif entry==0xB15B:return self.round_health_update()
        elif entry==0xB198:return self.draw_action_objects()
        elif entry==0xB1B7:return self.draw_action_counter()
        elif entry==0xB1EC:return self.object_animation()
        elif entry==0xB206:return self.object_animation_phase_dispatch()
        elif entry==0xB211:return self.object_animation_phase_0()
        elif entry==0xB25B:return self.object_animation_phase_1()
        elif entry==0xB2F5:return self.object_animation_phase_2()
        elif entry==0xB3EF:return self.object_animation_phase_3()
        elif entry==0xB44B:return self.resolve_animation_collision()
        elif entry==0xB48A:return self.update_animation_object()
        elif entry==0xB4E3:return self.finish_animation_object()
        elif entry==0xB548:return self.prepare_attack_object_arrays()
        elif entry==0xB870:return self.text_readiness()
        elif entry==0xB882:return self.build_object_nametable_packet()
        elif entry==0xBA18:return self.insert_object_nametable_overlay()
        elif entry==0xBA56:return self.prepare_object_packet_colors()
        elif entry==0xBA79:return self.build_object_attribute_packet()
        elif entry==0xBB8F:return self.initialize_attack_background()
        elif entry==0xBE15:return self.build_initial_nametable_rows()
        elif entry==0xBE76:return self.build_initial_attribute_rows()
        elif entry==0xBF15:return self.flush_attack_background()
        elif entry==0xBF4C:return self.draw_attack_scene_objects()
        elif entry==0xBF9D:return self.object_position_to_world()
        elif entry==0xBFA1:return self.object_position_to_world_saved()
        elif entry==0xC01B:return self.animate_background_CHR()
        elif entry==0xC064:return self.choose_object_axis_direction()
        elif entry==0xC1CD:return self.probe_shifted_object_position()
        elif entry==0xC20F:return self.choose_shifted_object_destination()
        elif entry==0xC30F:return self.search_axis_object_target()
        elif entry==0xC827:return self.classify_object_collision()
        elif entry==0xC839:return self.check_object_side()
        elif entry==0xC8FD:return self.draw_formation_selection_result()
        elif entry==0xC926:return self.prepare_participant_statistics()
        elif entry==0xC991:return self.compute_combat_equipment_parameters()
        elif entry==0xCA3F:return self.write_attack_results_to_battle()
        elif entry==0xCAC8:return self.probe_shifted_object_terrain()
        elif entry==0xCAF9:return self.read_object_terrain_with_affinity()
        elif entry==0xCBF1:return self.build_participant_stats_packets()
        elif entry==0xCC7A:return self.participant_controller_input()
        elif entry==0xCCA8:return self.selected_side_controller_input()
        elif entry==0xCCDE:return self.side_controller_input()
        elif entry==0xCD22:return self.active_side_controller_input()
        elif entry==0xCD43:return self.duel_handoff()
        elif entry==0xCD46:return self.duel_handoff_phase_dispatch()
        elif entry==0xCD4F:return self.duel_handoff_phase_0()
        elif entry==0xCD59:return self.duel_handoff_phase_1()
        elif entry==0xCDCF:return self.duel_handoff_phase_2()
        elif entry==0xCE10:return self.restore_saved_main_phase()
        elif entry==0xCE25:return self.first_formation()
        elif entry==0xCE28:return self.first_formation_phase_dispatch()
        elif entry==0xCE33:return self.first_formation_phase_0()
        elif entry==0xCE68:return self.first_formation_phase_1()
        elif entry==0xCEAE:return self.first_formation_phase_2()
        elif entry==0xCEFA:return self.first_formation_phase_3()
        elif entry==0xCF05:return self.formation_choice_input()
        elif entry==0xCF67:return self.second_formation()
        elif entry==0xCF6A:return self.second_formation_phase_dispatch()
        elif entry==0xCF77:return self.second_formation_phase_0()
        elif entry==0xCF9D:return self.second_formation_phase_1()
        elif entry==0xCFC2:return self.second_formation_phase_2()
        elif entry==0xD008:return self.second_formation_phase_3()
        elif entry==0xD054:return self.second_formation_phase_4()
        elif entry==0xD067:return self.round_stat_check()
        elif entry==0xD0AE:return self.round_resource_check()
        elif entry==0xD0CB:return self.test_first_commander()
        elif entry==0xD102:return self.formation_pair_evaluation()
        elif entry==0xD1D8:return self.formation_damage_evaluation()
        elif entry==0xD2D4:return self.formation_object_parameters()
        elif entry==0xD32A:return self.formation_probability_evaluation()
        elif entry==0xD3C7:return self.formation_special_evaluation()
        elif entry==0xD42F:return self.resolve_formation_results()
        elif entry==0xD506:return self.commit_formation_damage()
        elif entry==0xD558:return self.evaluate_routed_formation()
        elif entry==0xD5A0:return self.draw_formation_counter()
        elif entry==0xD5BC:return self.queued_object_map_update()
        elif entry==0xD5F3:return self.draw_selected_participant()
        elif entry==0xD612:return self.side_object_position()
        elif entry==0xD652:return self.prepare_selected_side_object()
        elif entry==0xD6BA:return self.duel_selection()
        elif entry==0xD6BD:return self.duel_selection_phase_dispatch()
        elif entry==0xD6CC:return self.duel_selection_phase_0()
        elif entry==0xD6DD:return self.duel_selection_phase_1()
        elif entry==0xD72A:return self.duel_selection_phase_3()
        elif entry==0xD72B:return self.draw_other_participant_menu()
        elif entry==0xD743:return self.duel_selection_phase_4()
        elif entry==0xD77F:return self.duel_selection_phase_5()
        elif entry==0xD7FB:return self.experience_level_code()
        raise ValueError("Entry is outside the proven attack procedure catalog")

    def attack_scene_tick(self):
        """Original entry $A000; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA000)
        return (yield from self.scene_service_wrapper())

    def scene_service_wrapper(self):
        """Original entry $A00F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA00F)
        self._push(0xA0);self._push(0x11)
        yield from self.animate_background_CHR()
        if r.pc!=0xA012:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x057B]=r.a
        self._push(0xA0);self._push(0x19)
        yield from self.participant_cards_then_control()
        if r.pc!=0xA01A:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        self._push(r.a)
        self._a(m[0x057B])
        m[NEW_BUTTONS]=r.a
        self._y(0x3D)
        yield from self._external(0xA026,0xEE07,0xA02B,"far_call",40963)
        if r.pc!=0xA02B:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[NEW_BUTTONS]=r.a
        self._mark(0xA02F)
        self._rts();return

    def participant_cards_then_control(self):
        """Original entry $A030; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA030)
        self._a(m[STATE])
        self._mark(0xA033)
        if r.p&Z:
            self._a(m[FIRST_OFFICER])
            m[0x0000]=r.a
            self._a(0xA5)
            m[0x000A]=r.a
            self._x(0x00)
            self._y(0x39)
            yield from self._external(0xA04D,0xEE07,0xA052,"far_call",40960)
            if r.pc!=0xA052:return  # preserve nonlocal stack return
            self._a(0xD0)
            m[0x04BC]=r.a
            self._a(m[SECOND_OFFICER])
            m[0x0000]=r.a
            self._a(0xA5)
            m[0x000A]=r.a
            self._x(0x01)
            self._y(0x39)
            yield from self._external(0xA064,0xEE07,0xA069,"far_call",40960)
            if r.pc!=0xA069:return  # preserve nonlocal stack return
            pass
        else:
            self._compare(r.a,0x01)
            self._mark(0xA037)
            if r.p&Z:
                self._a(m[FIRST_OFFICER])
                m[0x0000]=r.a
                self._a(0xA5)
                m[0x000A]=r.a
                self._x(0x00)
                self._y(0x39)
                yield from self._external(0xA04D,0xEE07,0xA052,"far_call",40960)
                if r.pc!=0xA052:return  # preserve nonlocal stack return
                self._a(0xD0)
                m[0x04BC]=r.a
                self._a(m[SECOND_OFFICER])
                m[0x0000]=r.a
                self._a(0xA5)
                m[0x000A]=r.a
                self._x(0x01)
                self._y(0x39)
                yield from self._external(0xA064,0xEE07,0xA069,"far_call",40960)
                if r.pc!=0xA069:return  # preserve nonlocal stack return
                pass
            else:
                self._compare(r.a,0x02)
                self._mark(0xA03B)
                if r.p&Z:
                    self._a(m[FIRST_OFFICER])
                    m[0x0000]=r.a
                    self._a(0xA5)
                    m[0x000A]=r.a
                    self._x(0x00)
                    self._y(0x39)
                    yield from self._external(0xA04D,0xEE07,0xA052,"far_call",40960)
                    if r.pc!=0xA052:return  # preserve nonlocal stack return
                    self._a(0xD0)
                    m[0x04BC]=r.a
                    self._a(m[SECOND_OFFICER])
                    m[0x0000]=r.a
                    self._a(0xA5)
                    m[0x000A]=r.a
                    self._x(0x01)
                    self._y(0x39)
                    yield from self._external(0xA064,0xEE07,0xA069,"far_call",40960)
                    if r.pc!=0xA069:return  # preserve nonlocal stack return
                    pass
                else:
                    pass
                pass
            pass
        return (yield from self.attack_tick())

    def attack_tick(self):
        """Original entry $A069; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA069)
        self._a(m[STATE])
        return (yield from self.attack_main_dispatch())

    def attack_main_dispatch(self):
        """Original entry $A06C; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA06C)
        index=self._dispatch(0xA06C,(41093, 41311, 42231, 43555, 41916, 52547, 52773, 53095, 44229, 45548, 54970))
        return (yield from (self.setup_and_information,self.formation_action_round,self.object_action,self.participant_menu,self.result_confirmation,self.duel_handoff,self.first_formation,self.second_formation,self.intelligence_action,self.object_animation,self.duel_selection,)[index]())

    def setup_and_information(self):
        """Original entry $A085; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA085)
        self._a(m[PHASE])
        return (yield from self.setup_and_information_phase_dispatch())

    def setup_and_information_phase_dispatch(self):
        """Original entry $A088; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA088)
        index=self._dispatch(0xA088,(41109, 41171, 41209, 41241, 41271))
        return (yield from (self.setup_and_information_phase_0,self.setup_and_information_phase_1,self.setup_and_information_phase_2,self.setup_and_information_phase_3,self.setup_and_information_phase_4,)[index]())

    def setup_and_information_phase_0(self):
        """A095..A0D2: wait for fade, clear control arrays, prepare both sides."""
        r=self.registers;m=self.memory
        self._mark(0xA095);self._a(m[FADE_FLAG])
        if not r.p&N:self._rts();return
        self._a(6);m[STATE]=r.a;self._a(0);m[PHASE]=r.a
        self._a(0)
        for address in (*range(0x550,0x558),*range(0x574,0x578)):m[address]=r.a
        self._a(0);m[SCAN_CURSOR]=r.a
        self._push(0xA0);self._push(0xD1)
        yield from self.prepare_participant_statistics()
        if r.pc!=0xA0D2:return
        self._rts();return

    def setup_and_information_phase_1(self):
        """Original entry $A0D3; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA0D3)
        self._push(0xA0);self._push(0xD5)
        yield from self.text_readiness()
        if r.pc!=0xA0D6:return  # preserve nonlocal stack return
        self._mark(0xA0D6)
        if not r.p&C:
            pass
        else:
            self._a(0x10)
            m[0x0012]=r.a
            self._y(m[SCAN_CURSOR])
            m[0x0013]=r.y
            self._a(m[(OBJECT_X+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xA0E6)
            if r.p&Z:
                pass
            else:
                self._push(0xA0);self._push(0xEA)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xA0EB:return  # preserve nonlocal stack return
                pass
            m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
            self._a(m[SCAN_CURSOR])
            self._compare(r.a,0x16)
            self._mark(0xA0F3)
            if not r.p&C:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                pass
            pass
        self._mark(0xA0F8)
        self._rts();return

    def setup_and_information_phase_2(self):
        """Original entry $A0F9; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA0F9)
        self._push(0xA0);self._push(0xFB)
        yield from self.text_readiness()
        if r.pc!=0xA0FC:return  # preserve nonlocal stack return
        self._mark(0xA0FC)
        if not r.p&C:
            pass
        else:
            self._a(0xE8)
            m[0x0310]=r.a
            self._a(0xE9)
            m[0x0311]=r.a
            self._a(0x00)
            m[0x0300]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x05)
            m[0x00BC]=r.a
            self._push(0xA1);self._push(0x17)
            yield from self.build_participant_stats_packets()
            if r.pc!=0xA118:return  # preserve nonlocal stack return
            pass
        self._mark(0xA118)
        self._rts();return

    def setup_and_information_phase_3(self):
        """Original entry $A119; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA119)
        self._push(0xA1);self._push(0x1B)
        yield from self.text_readiness()
        if r.pc!=0xA11C:return  # preserve nonlocal stack return
        self._mark(0xA11C)
        if not r.p&C:
            pass
        else:
            self._a(0x09)
            m[0x00BB]=r.a
            self._a(m[FIRST_OFFICER])
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            self._y(0x3D)
            yield from self._external(0xA12E,0xEE07,0xA133,"far_call",41020)
            if r.pc!=0xA133:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xA136)
        self._rts();return

    def setup_and_information_phase_4(self):
        """Original entry $A137; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA137)
        self._a(m[PPU_JOBS])
        self._mark(0xA13A)
        if not r.p&Z:
            pass
        else:
            self._a(m[SECOND_OFFICER])
            m[0x0000]=r.a
            self._a(0x01)
            m[0x0001]=r.a
            self._y(0x3D)
            yield from self._external(0xA147,0xEE07,0xA14C,"far_call",41020)
            if r.pc!=0xA14C:return  # preserve nonlocal stack return
            self._a(0x01)
            m[STATE]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            self._a(0x00)
            m[0x0568]=r.a
            m[0x0569]=r.a
            pass
        self._mark(0xA15E)
        self._rts();return

    def formation_action_round(self):
        """Original entry $A15F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA15F)
        self._push(0xA1);self._push(0x61)
        yield from self.draw_attack_scene_objects()
        if r.pc!=0xA162:return  # preserve nonlocal stack return
        self._a(m[PHASE])
        return (yield from self.formation_action_round_phase_dispatch())

    def formation_action_round_phase_dispatch(self):
        """Original entry $A165; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA165)
        index=self._dispatch(0xA165,(41326, 41347, 41525))
        return (yield from (self.formation_action_round_phase_0,self.formation_action_round_phase_1,self.formation_action_round_phase_2,)[index]())

    def formation_action_round_phase_0(self):
        """Original entry $A16E; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA16E)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[OBJECT_INDEX]=r.a
        m[ACTION_CLASS]=r.a
        m[ACTION_CURSOR]=r.a
        m[0x057A]=r.a
        self._push(0xA1);self._push(0x81)
        yield from self.round_stat_check()
        if r.pc!=0xA182:return  # preserve nonlocal stack return
        self._mark(0xA182)
        self._rts();return

    def formation_action_round_phase_1(self):
        """Original entry $A183; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA183)
        self._push(0xA1);self._push(0x85)
        yield from self.scan_participant_object()
        if r.pc!=0xA186:return  # preserve nonlocal stack return
        self._push(0xA1);self._push(0x88)
        yield from self.check_round_participant_request()
        if r.pc!=0xA189:return  # preserve nonlocal stack return
        self._a(m[0x0568])
        self._a(r.a | m[0x0569])
        self._mark(0xA18F)
        if r.p&Z:
            self._a(0x00)
            m[0x0568]=r.a
            m[0x0569]=r.a
            while True:  # natural loop $A1BC
                self._y(m[ACTION_CLASS])
                self._a(m[(0xA231+r.y)&65535])
                m[0x0000]=r.a
                self._y(m[OBJECT_INDEX])
                self._a(m[(OBJECT_ENCODING+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xA1CC)
                if r.p&Z:
                    self._a(0x00)
                    m[ACTION_CURSOR]=r.a
                    m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
                    self._a(m[OBJECT_INDEX])
                    self._compare(r.a,0x16)
                    self._mark(0xA21C)
                    if not r.p&C:
                        continue
                    else:
                        self._a(0x00)
                        m[OBJECT_INDEX]=r.a
                        m[ACTION_CLASS]=self._nz(m[ACTION_CLASS]+1)
                        self._a(m[ACTION_CLASS])
                        self._compare(r.a,0x04)
                        self._mark(0xA22B)
                        if not r.p&C:
                            continue
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._mark(0xA230)
                            self._rts();return
                else:
                    self._a(r.a & 0x0F)
                    self._compare(r.a,m[0x0000])
                    self._mark(0xA1D2)
                    if not r.p&Z:
                        self._a(0x00)
                        m[ACTION_CURSOR]=r.a
                        m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
                        self._a(m[OBJECT_INDEX])
                        self._compare(r.a,0x16)
                        self._mark(0xA21C)
                        if not r.p&C:
                            continue
                        else:
                            self._a(0x00)
                            m[OBJECT_INDEX]=r.a
                            m[ACTION_CLASS]=self._nz(m[ACTION_CLASS]+1)
                            self._a(m[ACTION_CLASS])
                            self._compare(r.a,0x04)
                            self._mark(0xA22B)
                            if not r.p&C:
                                continue
                            else:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._mark(0xA230)
                                self._rts();return
                    else:
                        self._a(0x02)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0x00)
                        self._y(m[OBJECT_INDEX])
                        self._compare(r.y,0x0B)
                        self._mark(0xA1E5)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x04)
                            pass
                        m[0x0000]=r.a
                        self._a(m[(OBJECT_ENCODING+r.y)&65535])
                        self._a(r.a & 0x0F)
                        self._a(r.a | m[0x0000])
                        self._y(r.a)
                        self._a(m[(0x0550+r.y)&65535])
                        m[OBJECT_ACTION]=r.a
                        self._compare(r.a,0x80)
                        self._mark(0xA1FB)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x00)
                            m[OBJECT_ACTION]=r.a
                            yield from self._external(0xA202,0xE87A,0xA205,"call",None)
                            if r.pc!=0xA205:return  # preserve nonlocal stack return
                            self._a(r.a & 0x01)
                            self._mark(0xA207)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(0x02)
                                m[OBJECT_ACTION]=r.a
                                pass
                            pass
                        self._mark(0xA20E)
                        self._rts();return
        else:
            self._a(m[0x0569])
            m[ACTIVE_SIDE]=r.a
            self._a(0x03)
            m[STATE]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            self._a(0x01)
            m[SAVED_STATE]=r.a
            self._a(0x01)
            m[SAVED_PHASE]=r.a
            self._a(0x00)
            m[0x0568]=r.a
            m[0x0569]=r.a
            self._mark(0xA1B3)
            self._rts();return

    def formation_action_round_phase_2(self):
        """Original entry $A235; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA235)
        self._a(0x01)
        m[PHASE]=r.a
        self._push(0xA2);self._push(0x3C)
        yield from self.text_readiness()
        if r.pc!=0xA23D:return  # preserve nonlocal stack return
        self._mark(0xA23D)
        if not r.p&C:
            pass
        else:
            self._a(0xE9)
            m[0x0310]=r.a
            self._a(0x00)
            m[0x0300]=r.a
            self._push(0xA2);self._push(0x4B)
            yield from self.build_participant_stats_packets()
            if r.pc!=0xA24C:return  # preserve nonlocal stack return
            pass
        self._a(m[ACTION_CLASS])
        self._compare(r.a,0x04)
        self._mark(0xA251)
        if r.p&C:
            self._a(0x00)
            m[OBJECT_INDEX]=r.a
            m[ACTION_CLASS]=r.a
            m[0x057A]=self._nz(m[0x057A]+1)
            self._push(0xA2);self._push(0x99)
            yield from self.round_health_update()
            if r.pc!=0xA29A:return  # preserve nonlocal stack return
            self._push(0xA2);self._push(0x9C)
            yield from self.round_resource_check()
            if r.pc!=0xA29D:return  # preserve nonlocal stack return
            self._push(0xA2);self._push(0x9F)
            yield from self.round_stat_check()
            if r.pc!=0xA2A0:return  # preserve nonlocal stack return
            self._a(0x00)
            m[OBJECT_INDEX]=r.a
            m[ACTION_CLASS]=r.a
            pass
        else:
            self._y(m[ACTION_CLASS])
            self._a(m[(0xA231+r.y)&65535])
            self._compare(r.a,0x02)
            self._mark(0xA25B)
            if r.p&Z:
                self._a(0x00)
                m[ACTION_CURSOR]=r.a
                m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
                self._a(m[OBJECT_INDEX])
                self._compare(r.a,0x16)
                self._mark(0xA278)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[OBJECT_INDEX]=r.a
                    m[ACTION_CURSOR]=r.a
                    m[ACTION_CLASS]=self._nz(m[ACTION_CLASS]+1)
                    self._a(m[ACTION_CLASS])
                    self._compare(r.a,0x04)
                    self._mark(0xA28A)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[OBJECT_INDEX]=r.a
                        m[ACTION_CLASS]=r.a
                        m[0x057A]=self._nz(m[0x057A]+1)
                        self._push(0xA2);self._push(0x99)
                        yield from self.round_health_update()
                        if r.pc!=0xA29A:return  # preserve nonlocal stack return
                        self._push(0xA2);self._push(0x9C)
                        yield from self.round_resource_check()
                        if r.pc!=0xA29D:return  # preserve nonlocal stack return
                        self._push(0xA2);self._push(0x9F)
                        yield from self.round_stat_check()
                        if r.pc!=0xA2A0:return  # preserve nonlocal stack return
                        self._a(0x00)
                        m[OBJECT_INDEX]=r.a
                        m[ACTION_CLASS]=r.a
                        pass
                    pass
                pass
            else:
                self._compare(r.a,0x03)
                self._mark(0xA25F)
                if r.p&Z:
                    self._a(0x00)
                    m[ACTION_CURSOR]=r.a
                    m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
                    self._a(m[OBJECT_INDEX])
                    self._compare(r.a,0x16)
                    self._mark(0xA278)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[OBJECT_INDEX]=r.a
                        m[ACTION_CURSOR]=r.a
                        m[ACTION_CLASS]=self._nz(m[ACTION_CLASS]+1)
                        self._a(m[ACTION_CLASS])
                        self._compare(r.a,0x04)
                        self._mark(0xA28A)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x00)
                            m[OBJECT_INDEX]=r.a
                            m[ACTION_CLASS]=r.a
                            m[0x057A]=self._nz(m[0x057A]+1)
                            self._push(0xA2);self._push(0x99)
                            yield from self.round_health_update()
                            if r.pc!=0xA29A:return  # preserve nonlocal stack return
                            self._push(0xA2);self._push(0x9C)
                            yield from self.round_resource_check()
                            if r.pc!=0xA29D:return  # preserve nonlocal stack return
                            self._push(0xA2);self._push(0x9F)
                            yield from self.round_stat_check()
                            if r.pc!=0xA2A0:return  # preserve nonlocal stack return
                            self._a(0x00)
                            m[OBJECT_INDEX]=r.a
                            m[ACTION_CLASS]=r.a
                            pass
                        pass
                    pass
                else:
                    m[ACTION_CURSOR]=self._nz(m[ACTION_CURSOR]+1)
                    self._a(m[ACTION_CURSOR])
                    self._compare(r.a,0x01)
                    self._mark(0xA269)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0x00)
                        m[ACTION_CURSOR]=r.a
                        m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
                        self._a(m[OBJECT_INDEX])
                        self._compare(r.a,0x16)
                        self._mark(0xA278)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x00)
                            m[OBJECT_INDEX]=r.a
                            m[ACTION_CURSOR]=r.a
                            m[ACTION_CLASS]=self._nz(m[ACTION_CLASS]+1)
                            self._a(m[ACTION_CLASS])
                            self._compare(r.a,0x04)
                            self._mark(0xA28A)
                            if not r.p&C:
                                pass
                            else:
                                self._a(0x00)
                                m[OBJECT_INDEX]=r.a
                                m[ACTION_CLASS]=r.a
                                m[0x057A]=self._nz(m[0x057A]+1)
                                self._push(0xA2);self._push(0x99)
                                yield from self.round_health_update()
                                if r.pc!=0xA29A:return  # preserve nonlocal stack return
                                self._push(0xA2);self._push(0x9C)
                                yield from self.round_resource_check()
                                if r.pc!=0xA29D:return  # preserve nonlocal stack return
                                self._push(0xA2);self._push(0x9F)
                                yield from self.round_stat_check()
                                if r.pc!=0xA2A0:return  # preserve nonlocal stack return
                                self._a(0x00)
                                m[OBJECT_INDEX]=r.a
                                m[ACTION_CLASS]=r.a
                                pass
                            pass
                        pass
                    pass
                pass
            pass
        self._mark(0xA2A8)
        self._rts();return

    def check_round_participant_request(self):
        """Original entry $A2A9; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2A9)
        self._a(m[OBJECT_X])
        self._compare(r.a,0xFF)
        self._mark(0xA2AE)
        if not r.p&Z:
            self._a(m[0x058B])
            self._compare(r.a,0xFF)
            self._mark(0xA2F1)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x05B7])
                self._mark(0xA2F6)
                if r.p&Z:
                    self._a(m[FIRST_OFFICER])
                    m[0x0514]=r.a
                    self._a(0x00)
                    m[0x0515]=r.a
                    self._a(m[SECOND_OFFICER])
                    m[0x042C]=r.a
                    m[0x0516]=r.a
                    self._a(0x02)
                    m[0x0517]=r.a
                    self._a(0x04)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0xD3)
                    yield from self._external(0xA321,0xF28B,0xA324,"call",None)
                    if r.pc!=0xA324:return  # preserve nonlocal stack return
                    yield from self._external(0xA324,0xE57F,0xA327,"call",None)
                    if r.pc!=0xA327:return  # preserve nonlocal stack return
                    self._a(0x71)
                    yield from self._external(0xA329,0xE683,0xA32C,"call",None)
                    if r.pc!=0xA32C:return  # preserve nonlocal stack return
                    self._a(self._pop())
                    self._a(self._pop())
                    pass
                else:
                    self._compare(r.a,0xFF)
                    self._mark(0xA2FA)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[FIRST_OFFICER])
                        m[0x0514]=r.a
                        self._a(0x00)
                        m[0x0515]=r.a
                        self._a(m[SECOND_OFFICER])
                        m[0x042C]=r.a
                        m[0x0516]=r.a
                        self._a(0x02)
                        m[0x0517]=r.a
                        self._a(0x04)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0xD3)
                        yield from self._external(0xA321,0xF28B,0xA324,"call",None)
                        if r.pc!=0xA324:return  # preserve nonlocal stack return
                        yield from self._external(0xA324,0xE57F,0xA327,"call",None)
                        if r.pc!=0xA327:return  # preserve nonlocal stack return
                        self._a(0x71)
                        yield from self._external(0xA329,0xE683,0xA32C,"call",None)
                        if r.pc!=0xA32C:return  # preserve nonlocal stack return
                        self._a(self._pop())
                        self._a(self._pop())
                        pass
                    pass
                pass
            self._mark(0xA32E)
            self._rts();return
        else:
            self._a(m[OBJECT_VALUE])
            self._mark(0xA2B3)
            if r.p&Z:
                self._a(m[FIRST_OFFICER])
                m[0x042C]=r.a
                m[0x0514]=r.a
                self._a(0x02)
                m[0x0515]=r.a
                self._a(m[SECOND_OFFICER])
                m[0x0516]=r.a
                self._a(0x00)
                m[0x0517]=r.a
                self._a(0x04)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0xD3)
                yield from self._external(0xA2DE,0xF28B,0xA2E1,"call",None)
                if r.pc!=0xA2E1:return  # preserve nonlocal stack return
                yield from self._external(0xA2E1,0xE57F,0xA2E4,"call",None)
                if r.pc!=0xA2E4:return  # preserve nonlocal stack return
                self._a(0x71)
                yield from self._external(0xA2E6,0xE683,0xA2E9,"call",None)
                if r.pc!=0xA2E9:return  # preserve nonlocal stack return
                self._a(self._pop())
                self._a(self._pop())
                self._mark(0xA2EB)
                self._rts();return
            else:
                self._compare(r.a,0xFF)
                self._mark(0xA2B7)
                if not r.p&Z:
                    self._a(m[0x058B])
                    self._compare(r.a,0xFF)
                    self._mark(0xA2F1)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x05B7])
                        self._mark(0xA2F6)
                        if r.p&Z:
                            self._a(m[FIRST_OFFICER])
                            m[0x0514]=r.a
                            self._a(0x00)
                            m[0x0515]=r.a
                            self._a(m[SECOND_OFFICER])
                            m[0x042C]=r.a
                            m[0x0516]=r.a
                            self._a(0x02)
                            m[0x0517]=r.a
                            self._a(0x04)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            self._a(0xD3)
                            yield from self._external(0xA321,0xF28B,0xA324,"call",None)
                            if r.pc!=0xA324:return  # preserve nonlocal stack return
                            yield from self._external(0xA324,0xE57F,0xA327,"call",None)
                            if r.pc!=0xA327:return  # preserve nonlocal stack return
                            self._a(0x71)
                            yield from self._external(0xA329,0xE683,0xA32C,"call",None)
                            if r.pc!=0xA32C:return  # preserve nonlocal stack return
                            self._a(self._pop())
                            self._a(self._pop())
                            pass
                        else:
                            self._compare(r.a,0xFF)
                            self._mark(0xA2FA)
                            if not r.p&Z:
                                pass
                            else:
                                self._a(m[FIRST_OFFICER])
                                m[0x0514]=r.a
                                self._a(0x00)
                                m[0x0515]=r.a
                                self._a(m[SECOND_OFFICER])
                                m[0x042C]=r.a
                                m[0x0516]=r.a
                                self._a(0x02)
                                m[0x0517]=r.a
                                self._a(0x04)
                                m[STATE]=r.a
                                self._a(0x00)
                                m[PHASE]=r.a
                                self._a(0xD3)
                                yield from self._external(0xA321,0xF28B,0xA324,"call",None)
                                if r.pc!=0xA324:return  # preserve nonlocal stack return
                                yield from self._external(0xA324,0xE57F,0xA327,"call",None)
                                if r.pc!=0xA327:return  # preserve nonlocal stack return
                                self._a(0x71)
                                yield from self._external(0xA329,0xE683,0xA32C,"call",None)
                                if r.pc!=0xA32C:return  # preserve nonlocal stack return
                                self._a(self._pop())
                                self._a(self._pop())
                                pass
                            pass
                        pass
                    self._mark(0xA32E)
                    self._rts();return
                else:
                    self._a(m[FIRST_OFFICER])
                    m[0x042C]=r.a
                    m[0x0514]=r.a
                    self._a(0x02)
                    m[0x0515]=r.a
                    self._a(m[SECOND_OFFICER])
                    m[0x0516]=r.a
                    self._a(0x00)
                    m[0x0517]=r.a
                    self._a(0x04)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0xD3)
                    yield from self._external(0xA2DE,0xF28B,0xA2E1,"call",None)
                    if r.pc!=0xA2E1:return  # preserve nonlocal stack return
                    yield from self._external(0xA2E1,0xE57F,0xA2E4,"call",None)
                    if r.pc!=0xA2E4:return  # preserve nonlocal stack return
                    self._a(0x71)
                    yield from self._external(0xA2E6,0xE683,0xA2E9,"call",None)
                    if r.pc!=0xA2E9:return  # preserve nonlocal stack return
                    self._a(self._pop())
                    self._a(self._pop())
                    self._mark(0xA2EB)
                    self._rts();return

    def scan_participant_object(self):
        """Original entry $A32F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA32F)
        self._a(m[OBJECT_X])
        self._compare(r.a,0xFE)
        self._mark(0xA334)
        if not r.p&Z:
            self._a(m[0x058B])
            self._compare(r.a,0xFE)
            self._mark(0xA36B)
            if not r.p&Z:
                pass
            else:
                self._a(m[FIRST_OFFICER])
                m[0x0514]=r.a
                self._a(0x00)
                m[0x0515]=r.a
                self._a(m[SECOND_OFFICER])
                m[0x042C]=r.a
                m[0x0516]=r.a
                self._a(0x01)
                m[0x0517]=r.a
                self._a(0x04)
                m[STATE]=r.a
                self._a(0x03)
                m[PHASE]=r.a
                self._a(0xFA)
                yield from self._external(0xA392,0xF28B,0xA395,"call",None)
                if r.pc!=0xA395:return  # preserve nonlocal stack return
                self._a(0x01)
                m[OBJECT_INDEX]=r.a
                self._a(self._pop())
                self._a(self._pop())
                pass
            self._mark(0xA39C)
            self._rts();return
        else:
            self._a(m[FIRST_OFFICER])
            m[0x042C]=r.a
            m[0x0514]=r.a
            self._a(0x01)
            m[0x0515]=r.a
            self._a(m[SECOND_OFFICER])
            m[0x0516]=r.a
            self._a(0x00)
            m[0x0517]=r.a
            self._a(0x00)
            m[OBJECT_INDEX]=r.a
            self._a(0x04)
            m[STATE]=r.a
            self._a(0x03)
            m[PHASE]=r.a
            self._a(0xFA)
            yield from self._external(0xA360,0xF28B,0xA363,"call",None)
            if r.pc!=0xA363:return  # preserve nonlocal stack return
            self._a(self._pop())
            self._a(self._pop())
            self._mark(0xA365)
            self._rts();return

    def prepare_selected_object_side(self):
        """Original entry $A39D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA39D)
        self._a(0x00)
        self._push(0xA3);self._push(0xA1)
        yield from self.side_controller_input()
        if r.pc!=0xA3A2:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        r.a=self._shift(r.a,False,rotate=False)
        self._mark(0xA3A5)
        if not r.p&C:
            pass
        else:
            self._a(0x01)
            m[0x0568]=r.a
            pass
        self._a(0x01)
        self._push(0xA3);self._push(0xB0)
        yield from self.side_controller_input()
        if r.pc!=0xA3B1:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        r.a=self._shift(r.a,False,rotate=False)
        self._mark(0xA3B4)
        if not r.p&C:
            pass
        else:
            self._a(0x01)
            m[0x0569]=r.a
            pass
        self._mark(0xA3BB)
        self._rts();return

    def result_confirmation(self):
        """Original entry $A3BC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3BC)
        self._a(m[PHASE])
        return (yield from self.result_confirmation_phase_dispatch())

    def result_confirmation_phase_dispatch(self):
        """Original entry $A3BF; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3BF)
        index=self._dispatch(0xA3BF,(41936, 41940, 41970, 41991, 42120, 42165, 41970))
        return (yield from (self.result_confirmation_phase_0,self.result_confirmation_phase_1,self.result_confirmation_phase_6,self.result_confirmation_phase_3,self.result_confirmation_phase_4,self.result_confirmation_phase_5,self.result_confirmation_phase_6,)[index]())

    def result_confirmation_phase_0(self):
        """Original entry $A3D0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3D0)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._mark(0xA3D3)
        self._rts();return

    def result_confirmation_phase_1(self):
        """Original entry $A3D4; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3D4)
        self._push(0xA3);self._push(0xD6)
        yield from self.active_side_controller_input()
        if r.pc!=0xA3D7:return  # preserve nonlocal stack return
        self._push(0xA3);self._push(0xD9)
        yield from self.text_readiness()
        if r.pc!=0xA3DA:return  # preserve nonlocal stack return
        self._mark(0xA3DA)
        if not r.p&C:
            pass
        else:
            self._push(0xA3);self._push(0xDE)
            yield from self.selected_side_controller_input()
            if r.pc!=0xA3DF:return  # preserve nonlocal stack return
            self._push(0xA3);self._push(0xE1)
            yield from self.active_side_controller_input()
            if r.pc!=0xA3E2:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x03)
            self._mark(0xA3E6)
            if r.p&Z:
                pass
            else:
                yield from self._external(0xA3E8,0xECEE,0xA3EB,"call",None)
                if r.pc!=0xA3EB:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._push(0xA3);self._push(0xF0)
                yield from self.write_attack_results_to_battle()
                if r.pc!=0xA3F1:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xA3F1)
        self._rts();return

    def result_confirmation_phase_6(self):
        """Original entry $A3F2; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3F2)
        self._a(m[FADE_FLAG])
        self._mark(0xA3F5)
        if not r.p&N:
            pass
        else:
            self._a(0x0B)
            m[0x0500]=r.a
            self._a(0x00)
            m[0x0501]=r.a
            self._a(0x03)
            m[GLOBAL]=r.a
            pass
        self._mark(0xA406)
        self._rts();return

    def result_confirmation_phase_3(self):
        """Original entry $A407; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA407)
        self._push(0xA4);self._push(0x09)
        yield from self.active_side_controller_input()
        if r.pc!=0xA40A:return  # preserve nonlocal stack return
        self._push(0xA4);self._push(0x0C)
        yield from self.text_readiness()
        if r.pc!=0xA40D:return  # preserve nonlocal stack return
        self._mark(0xA40D)
        if not r.p&C:
            self._mark(0xA46C)
            self._rts();return
        else:
            self._push(0xA4);self._push(0x11)
            yield from self.selected_side_controller_input()
            if r.pc!=0xA412:return  # preserve nonlocal stack return
            self._push(0xA4);self._push(0x14)
            yield from self.active_side_controller_input()
            if r.pc!=0xA415:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x03)
            self._mark(0xA419)
            if r.p&Z:
                self._mark(0xA46C)
                self._rts();return
            else:
                self._a(0x64)
                yield from self._external(0xA41D,0xE862,0xA420,"call",None)
                if r.pc!=0xA420:return  # preserve nonlocal stack return
                self._compare(r.a,0x20)
                self._mark(0xA422)
                if r.p&C:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x0A)
                    yield from self._external(0xA434,0xE862,0xA437,"call",None)
                    if r.pc!=0xA437:return  # preserve nonlocal stack return
                    self._flag(C,False)
                    self._add(0x05)
                    m[0x042F]=r.a
                    m[SCAN_CURSOR]=r.a
                    self._a(0x00)
                    m[0x0430]=r.a
                    m[0x0431]=r.a
                    self._a(0x7E)
                    yield from self._external(0xA44A,0xF28B,0xA44D,"call",None)
                    if r.pc!=0xA44D:return  # preserve nonlocal stack return
                    self._a(m[OBJECT_INDEX])
                    self._mark(0xA450)
                    if not r.p&Z:
                        self._a(m[0x0516])
                        m[0x042C]=r.a
                        self._a(m[0x05B7])
                        self._flag(C,True)
                        self._add(m[SCAN_CURSOR],subtract=True)
                        self._mark(0xA47A)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x05B7])
                            m[0x042F]=r.a
                            self._a(0x00)
                            pass
                        m[0x05B7]=r.a
                        self._mark(0xA487)
                        self._rts();return
                    else:
                        self._a(m[0x0514])
                        m[0x042C]=r.a
                        self._a(m[OBJECT_VALUE])
                        self._flag(C,True)
                        self._add(m[SCAN_CURSOR],subtract=True)
                        self._mark(0xA45F)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[OBJECT_VALUE])
                            m[0x042F]=r.a
                            self._a(0x00)
                            pass
                        m[OBJECT_VALUE]=r.a
                        self._mark(0xA46C)
                        self._rts();return
                else:
                    yield from self._external(0xA424,0xECEE,0xA427,"call",None)
                    if r.pc!=0xA427:return  # preserve nonlocal stack return
                    self._a(0x02)
                    m[PHASE]=r.a
                    return (yield from self.write_attack_results_to_battle())

    def result_confirmation_phase_4(self):
        """Original entry $A488; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA488)
        self._push(0xA4);self._push(0x8A)
        yield from self.active_side_controller_input()
        if r.pc!=0xA48B:return  # preserve nonlocal stack return
        self._push(0xA4);self._push(0x8D)
        yield from self.text_readiness()
        if r.pc!=0xA48E:return  # preserve nonlocal stack return
        self._mark(0xA48E)
        if not r.p&C:
            self._mark(0xA4B4)
            self._rts();return
        else:
            self._push(0xA4);self._push(0x92)
            yield from self.selected_side_controller_input()
            if r.pc!=0xA493:return  # preserve nonlocal stack return
            self._push(0xA4);self._push(0x95)
            yield from self.active_side_controller_input()
            if r.pc!=0xA496:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x03)
            self._mark(0xA49A)
            if r.p&Z:
                self._mark(0xA4B4)
                self._rts();return
            else:
                self._push(0xA4);self._push(0x9E)
                yield from self.selected_participant_health()
                if r.pc!=0xA49F:return  # preserve nonlocal stack return
                self._mark(0xA49F)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0xD3)
                    yield from self._external(0xA4B1,0xF28B,0xA4B4,"call",None)
                    if r.pc!=0xA4B4:return  # preserve nonlocal stack return
                    self._mark(0xA4B4)
                    self._rts();return
                else:
                    yield from self._external(0xA4A1,0xECEE,0xA4A4,"call",None)
                    if r.pc!=0xA4A4:return  # preserve nonlocal stack return
                    self._a(0x02)
                    m[PHASE]=r.a
                    return (yield from self.write_attack_results_to_battle())

    def result_confirmation_phase_5(self):
        """Original entry $A4B5; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4B5)
        self._push(0xA4);self._push(0xB7)
        yield from self.active_side_controller_input()
        if r.pc!=0xA4B8:return  # preserve nonlocal stack return
        self._push(0xA4);self._push(0xBA)
        yield from self.text_readiness()
        if r.pc!=0xA4BB:return  # preserve nonlocal stack return
        self._mark(0xA4BB)
        if not r.p&C:
            self._mark(0xA4D7)
            self._rts();return
        else:
            self._push(0xA4);self._push(0xBF)
            yield from self.selected_side_controller_input()
            if r.pc!=0xA4C0:return  # preserve nonlocal stack return
            self._push(0xA4);self._push(0xC2)
            yield from self.active_side_controller_input()
            if r.pc!=0xA4C3:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x03)
            self._mark(0xA4C7)
            if r.p&Z:
                self._mark(0xA4D7)
                self._rts();return
            else:
                self._push(0xA4);self._push(0xCB)
                yield from self.mark_participant_withdrawal()
                if r.pc!=0xA4CC:return  # preserve nonlocal stack return
                yield from self._external(0xA4CC,0xECEE,0xA4CF,"call",None)
                if r.pc!=0xA4CF:return  # preserve nonlocal stack return
                self._a(0x02)
                m[PHASE]=r.a
                return (yield from self.write_attack_results_to_battle())

    def selected_participant_health(self):
        """Original entry $A4D8; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4D8)
        self._a(m[OBJECT_VALUE])
        self._y(m[OBJECT_INDEX])
        self._mark(0xA4DE)
        if r.p&Z:
            pass
        else:
            self._a(m[0x05B7])
            pass
        self._compare(r.a,0x00)
        self._mark(0xA4E5)
        self._rts();return

    def mark_participant_withdrawal(self):
        """Original entry $A4E6; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4E6)
        self._y(m[OBJECT_INDEX])
        self._mark(0xA4E9)
        if r.p&Z:
            self._a(0x02)
            m[0x0515]=r.a
            self._mark(0xA4F6)
            self._rts();return
        else:
            self._a(0x02)
            m[0x0517]=r.a
            self._mark(0xA4F0)
            self._rts();return

    def object_action(self):
        """Original entry $A4F7; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA4F7)
        self._push(0xA4);self._push(0xF9)
        yield from self.draw_attack_scene_objects()
        if r.pc!=0xA4FA:return  # preserve nonlocal stack return
        self._push(0xA4);self._push(0xFC)
        yield from self.prepare_selected_object_side()
        if r.pc!=0xA4FD:return  # preserve nonlocal stack return
        self._a(m[PHASE])
        return (yield from self.object_action_phase_dispatch())

    def object_action_phase_dispatch(self):
        """Original entry $A500; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA500)
        index=self._dispatch(0xA500,(42265, 42436, 42483, 42525, 42580, 42724, 42754, 42798, 42826, 42843, 42976))
        return (yield from (self.object_action_phase_0,self.object_action_phase_1,self.object_action_phase_2,self.object_action_phase_3,self.object_action_phase_4,self.object_action_phase_5,self.object_action_phase_6,self.object_action_phase_7,self.object_action_phase_8,self.object_action_phase_9,self.object_action_phase_10,)[index]())

    def object_action_phase_0(self):
        """Original entry $A519; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA519)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._a(0x00)
        m[SAVED_PHASE]=r.a
        self._a(m[OBJECT_ACTION])
        self._compare(r.a,0x01)
        self._mark(0xA528)
        if r.p&Z:
            self._a(m[OBJECT_ACTION])
            self._compare(r.a,0x02)
            self._mark(0xA591)
            if r.p&Z:
                self._a(0x10)
                m[0x0012]=r.a
                self._a(m[OBJECT_INDEX])
                m[0x0013]=r.a
                self._push(0xA6);self._push(0x11)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xA612:return  # preserve nonlocal stack return
                self._a(0x01)
                m[STATE]=r.a
                self._a(0x02)
                m[PHASE]=r.a
                self._mark(0xA61C)
                self._rts();return
            else:
                self._y(m[OBJECT_INDEX])
                self._mark(0xA596)
                if r.p&Z:
                    self._a(m[0x0574])
                    self._a(r.a & 0xF0)
                    self._mark(0xA5AA)
                    if not r.p&Z:
                        self._a(0x10)
                        m[0x0012]=r.a
                        self._a(m[OBJECT_INDEX])
                        m[0x0013]=r.a
                        self._push(0xA6);self._push(0x11)
                        yield from self.build_object_nametable_packet()
                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                        self._a(0x01)
                        m[STATE]=r.a
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._mark(0xA61C)
                        self._rts();return
                    else:
                        self._push(0xA5);self._push(0xAE)
                        yield from self.choose_object_destination()
                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                        self._push(0xA5);self._push(0xB1)
                        yield from self.choose_object_axis_direction()
                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                        self._a(m[ACTIVE_SIDE])
                        self._mark(0xA5B5)
                        if r.p&N:
                            self._a(0x10)
                            m[0x0012]=r.a
                            self._a(m[OBJECT_INDEX])
                            m[0x0013]=r.a
                            self._push(0xA6);self._push(0x11)
                            yield from self.build_object_nametable_packet()
                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                            self._a(0x01)
                            m[STATE]=r.a
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._mark(0xA61C)
                            self._rts();return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(m[ACTIVE_SIDE])
                            self._push(0xA5);self._push(0xBF)
                            yield from self.queue_object_redraw()
                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                            self._mark(0xA5C0)
                            self._rts();return
                else:
                    self._compare(r.y,0x0B)
                    self._mark(0xA59A)
                    if not r.p&Z:
                        self._push(0xA5);self._push(0xAE)
                        yield from self.choose_object_destination()
                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                        self._push(0xA5);self._push(0xB1)
                        yield from self.choose_object_axis_direction()
                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                        self._a(m[ACTIVE_SIDE])
                        self._mark(0xA5B5)
                        if r.p&N:
                            self._a(0x10)
                            m[0x0012]=r.a
                            self._a(m[OBJECT_INDEX])
                            m[0x0013]=r.a
                            self._push(0xA6);self._push(0x11)
                            yield from self.build_object_nametable_packet()
                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                            self._a(0x01)
                            m[STATE]=r.a
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._mark(0xA61C)
                            self._rts();return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(m[ACTIVE_SIDE])
                            self._push(0xA5);self._push(0xBF)
                            yield from self.queue_object_redraw()
                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                            self._mark(0xA5C0)
                            self._rts();return
                    else:
                        self._a(m[0x0574])
                        self._a(r.a & 0x0F)
                        self._mark(0xA5A1)
                        if not r.p&Z:
                            self._a(0x10)
                            m[0x0012]=r.a
                            self._a(m[OBJECT_INDEX])
                            m[0x0013]=r.a
                            self._push(0xA6);self._push(0x11)
                            yield from self.build_object_nametable_packet()
                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                            self._a(0x01)
                            m[STATE]=r.a
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._mark(0xA61C)
                            self._rts();return
                        else:
                            self._mark(0xA5A3)
                            if r.p&Z:
                                self._push(0xA5);self._push(0xAE)
                                yield from self.choose_object_destination()
                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                self._push(0xA5);self._push(0xB1)
                                yield from self.choose_object_axis_direction()
                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                self._a(m[ACTIVE_SIDE])
                                self._mark(0xA5B5)
                                if r.p&N:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(m[ACTIVE_SIDE])
                                    self._push(0xA5);self._push(0xBF)
                                    yield from self.queue_object_redraw()
                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                    self._mark(0xA5C0)
                                    self._rts();return
                            else:
                                self._a(m[0x0574])
                                self._a(r.a & 0xF0)
                                self._mark(0xA5AA)
                                if not r.p&Z:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    self._push(0xA5);self._push(0xAE)
                                    yield from self.choose_object_destination()
                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                    self._push(0xA5);self._push(0xB1)
                                    yield from self.choose_object_axis_direction()
                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                    self._a(m[ACTIVE_SIDE])
                                    self._mark(0xA5B5)
                                    if r.p&N:
                                        self._a(0x10)
                                        m[0x0012]=r.a
                                        self._a(m[OBJECT_INDEX])
                                        m[0x0013]=r.a
                                        self._push(0xA6);self._push(0x11)
                                        yield from self.build_object_nametable_packet()
                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                        self._a(0x01)
                                        m[STATE]=r.a
                                        self._a(0x02)
                                        m[PHASE]=r.a
                                        self._mark(0xA61C)
                                        self._rts();return
                                    else:
                                        m[PHASE]=self._nz(m[PHASE]+1)
                                        self._a(m[ACTIVE_SIDE])
                                        self._push(0xA5);self._push(0xBF)
                                        yield from self.queue_object_redraw()
                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                        self._mark(0xA5C0)
                                        self._rts();return
        else:
            self._y(m[OBJECT_INDEX])
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0x0F)
            self._compare(r.a,0x02)
            self._mark(0xA534)
            if not r.p&Z:
                self._push(0xA5);self._push(0x63)
                yield from self.choose_shifted_object_destination()
                if r.pc!=0xA564:return  # preserve nonlocal stack return
                self._a(m[ACTIVE_SIDE])
                self._mark(0xA567)
                if r.p&N:
                    self._a(m[OBJECT_ACTION])
                    self._compare(r.a,0x02)
                    self._mark(0xA591)
                    if r.p&Z:
                        self._a(0x10)
                        m[0x0012]=r.a
                        self._a(m[OBJECT_INDEX])
                        m[0x0013]=r.a
                        self._push(0xA6);self._push(0x11)
                        yield from self.build_object_nametable_packet()
                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                        self._a(0x01)
                        m[STATE]=r.a
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._mark(0xA61C)
                        self._rts();return
                    else:
                        self._y(m[OBJECT_INDEX])
                        self._mark(0xA596)
                        if r.p&Z:
                            self._a(m[0x0574])
                            self._a(r.a & 0xF0)
                            self._mark(0xA5AA)
                            if not r.p&Z:
                                self._a(0x10)
                                m[0x0012]=r.a
                                self._a(m[OBJECT_INDEX])
                                m[0x0013]=r.a
                                self._push(0xA6);self._push(0x11)
                                yield from self.build_object_nametable_packet()
                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                self._a(0x01)
                                m[STATE]=r.a
                                self._a(0x02)
                                m[PHASE]=r.a
                                self._mark(0xA61C)
                                self._rts();return
                            else:
                                self._push(0xA5);self._push(0xAE)
                                yield from self.choose_object_destination()
                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                self._push(0xA5);self._push(0xB1)
                                yield from self.choose_object_axis_direction()
                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                self._a(m[ACTIVE_SIDE])
                                self._mark(0xA5B5)
                                if r.p&N:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(m[ACTIVE_SIDE])
                                    self._push(0xA5);self._push(0xBF)
                                    yield from self.queue_object_redraw()
                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                    self._mark(0xA5C0)
                                    self._rts();return
                        else:
                            self._compare(r.y,0x0B)
                            self._mark(0xA59A)
                            if not r.p&Z:
                                self._push(0xA5);self._push(0xAE)
                                yield from self.choose_object_destination()
                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                self._push(0xA5);self._push(0xB1)
                                yield from self.choose_object_axis_direction()
                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                self._a(m[ACTIVE_SIDE])
                                self._mark(0xA5B5)
                                if r.p&N:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(m[ACTIVE_SIDE])
                                    self._push(0xA5);self._push(0xBF)
                                    yield from self.queue_object_redraw()
                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                    self._mark(0xA5C0)
                                    self._rts();return
                            else:
                                self._a(m[0x0574])
                                self._a(r.a & 0x0F)
                                self._mark(0xA5A1)
                                if not r.p&Z:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    self._mark(0xA5A3)
                                    if r.p&Z:
                                        self._push(0xA5);self._push(0xAE)
                                        yield from self.choose_object_destination()
                                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                        self._push(0xA5);self._push(0xB1)
                                        yield from self.choose_object_axis_direction()
                                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                        self._a(m[ACTIVE_SIDE])
                                        self._mark(0xA5B5)
                                        if r.p&N:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            m[PHASE]=self._nz(m[PHASE]+1)
                                            self._a(m[ACTIVE_SIDE])
                                            self._push(0xA5);self._push(0xBF)
                                            yield from self.queue_object_redraw()
                                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                            self._mark(0xA5C0)
                                            self._rts();return
                                    else:
                                        self._a(m[0x0574])
                                        self._a(r.a & 0xF0)
                                        self._mark(0xA5AA)
                                        if not r.p&Z:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                else:
                    self._a(m[OBJECT_ACTION])
                    self._compare(r.a,0x03)
                    self._mark(0xA56E)
                    if not r.p&Z:
                        self._y(m[OBJECT_INDEX])
                        self._a(m[(OBJECT_ENCODING+r.y)&65535])
                        m[SAVED_STATE]=r.a
                        self._a(m[ACTIVE_SIDE])
                        self._push(0xA5);self._push(0x85)
                        yield from self.queue_object_redraw()
                        if r.pc!=0xA586:return  # preserve nonlocal stack return
                        self._a(0x03)
                        m[PHASE]=r.a
                        self._mark(0xA58B)
                        self._rts();return
                    else:
                        self._a(m[(OBJECT_ENCODING+r.x)&65535])
                        self._a(r.a & 0x03)
                        self._mark(0xA575)
                        if r.p&Z:
                            self._a(m[OBJECT_ACTION])
                            self._compare(r.a,0x02)
                            self._mark(0xA591)
                            if r.p&Z:
                                self._a(0x10)
                                m[0x0012]=r.a
                                self._a(m[OBJECT_INDEX])
                                m[0x0013]=r.a
                                self._push(0xA6);self._push(0x11)
                                yield from self.build_object_nametable_packet()
                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                self._a(0x01)
                                m[STATE]=r.a
                                self._a(0x02)
                                m[PHASE]=r.a
                                self._mark(0xA61C)
                                self._rts();return
                            else:
                                self._y(m[OBJECT_INDEX])
                                self._mark(0xA596)
                                if r.p&Z:
                                    self._a(m[0x0574])
                                    self._a(r.a & 0xF0)
                                    self._mark(0xA5AA)
                                    if not r.p&Z:
                                        self._a(0x10)
                                        m[0x0012]=r.a
                                        self._a(m[OBJECT_INDEX])
                                        m[0x0013]=r.a
                                        self._push(0xA6);self._push(0x11)
                                        yield from self.build_object_nametable_packet()
                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                        self._a(0x01)
                                        m[STATE]=r.a
                                        self._a(0x02)
                                        m[PHASE]=r.a
                                        self._mark(0xA61C)
                                        self._rts();return
                                    else:
                                        self._push(0xA5);self._push(0xAE)
                                        yield from self.choose_object_destination()
                                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                        self._push(0xA5);self._push(0xB1)
                                        yield from self.choose_object_axis_direction()
                                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                        self._a(m[ACTIVE_SIDE])
                                        self._mark(0xA5B5)
                                        if r.p&N:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            m[PHASE]=self._nz(m[PHASE]+1)
                                            self._a(m[ACTIVE_SIDE])
                                            self._push(0xA5);self._push(0xBF)
                                            yield from self.queue_object_redraw()
                                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                            self._mark(0xA5C0)
                                            self._rts();return
                                else:
                                    self._compare(r.y,0x0B)
                                    self._mark(0xA59A)
                                    if not r.p&Z:
                                        self._push(0xA5);self._push(0xAE)
                                        yield from self.choose_object_destination()
                                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                        self._push(0xA5);self._push(0xB1)
                                        yield from self.choose_object_axis_direction()
                                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                        self._a(m[ACTIVE_SIDE])
                                        self._mark(0xA5B5)
                                        if r.p&N:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            m[PHASE]=self._nz(m[PHASE]+1)
                                            self._a(m[ACTIVE_SIDE])
                                            self._push(0xA5);self._push(0xBF)
                                            yield from self.queue_object_redraw()
                                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                            self._mark(0xA5C0)
                                            self._rts();return
                                    else:
                                        self._a(m[0x0574])
                                        self._a(r.a & 0x0F)
                                        self._mark(0xA5A1)
                                        if not r.p&Z:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            self._mark(0xA5A3)
                                            if r.p&Z:
                                                self._push(0xA5);self._push(0xAE)
                                                yield from self.choose_object_destination()
                                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                self._push(0xA5);self._push(0xB1)
                                                yield from self.choose_object_axis_direction()
                                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                self._a(m[ACTIVE_SIDE])
                                                self._mark(0xA5B5)
                                                if r.p&N:
                                                    self._a(0x10)
                                                    m[0x0012]=r.a
                                                    self._a(m[OBJECT_INDEX])
                                                    m[0x0013]=r.a
                                                    self._push(0xA6);self._push(0x11)
                                                    yield from self.build_object_nametable_packet()
                                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                    self._a(0x01)
                                                    m[STATE]=r.a
                                                    self._a(0x02)
                                                    m[PHASE]=r.a
                                                    self._mark(0xA61C)
                                                    self._rts();return
                                                else:
                                                    m[PHASE]=self._nz(m[PHASE]+1)
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._push(0xA5);self._push(0xBF)
                                                    yield from self.queue_object_redraw()
                                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                    self._mark(0xA5C0)
                                                    self._rts();return
                                            else:
                                                self._a(m[0x0574])
                                                self._a(r.a & 0xF0)
                                                self._mark(0xA5AA)
                                                if not r.p&Z:
                                                    self._a(0x10)
                                                    m[0x0012]=r.a
                                                    self._a(m[OBJECT_INDEX])
                                                    m[0x0013]=r.a
                                                    self._push(0xA6);self._push(0x11)
                                                    yield from self.build_object_nametable_packet()
                                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                    self._a(0x01)
                                                    m[STATE]=r.a
                                                    self._a(0x02)
                                                    m[PHASE]=r.a
                                                    self._mark(0xA61C)
                                                    self._rts();return
                                                else:
                                                    self._push(0xA5);self._push(0xAE)
                                                    yield from self.choose_object_destination()
                                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                    self._push(0xA5);self._push(0xB1)
                                                    yield from self.choose_object_axis_direction()
                                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._mark(0xA5B5)
                                                    if r.p&N:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        m[PHASE]=self._nz(m[PHASE]+1)
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._push(0xA5);self._push(0xBF)
                                                        yield from self.queue_object_redraw()
                                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                        self._mark(0xA5C0)
                                                        self._rts();return
                        else:
                            self._y(m[OBJECT_INDEX])
                            self._a(m[(OBJECT_ENCODING+r.y)&65535])
                            m[SAVED_STATE]=r.a
                            self._a(m[ACTIVE_SIDE])
                            self._push(0xA5);self._push(0x85)
                            yield from self.queue_object_redraw()
                            if r.pc!=0xA586:return  # preserve nonlocal stack return
                            self._a(0x03)
                            m[PHASE]=r.a
                            self._mark(0xA58B)
                            self._rts();return
            else:
                self._push(0xA5);self._push(0x38)
                yield from self.search_axis_object_target()
                if r.pc!=0xA539:return  # preserve nonlocal stack return
                self._a(m[ACTIVE_SIDE])
                self._mark(0xA53C)
                if r.p&N:
                    self._push(0xA5);self._push(0x63)
                    yield from self.choose_shifted_object_destination()
                    if r.pc!=0xA564:return  # preserve nonlocal stack return
                    self._a(m[ACTIVE_SIDE])
                    self._mark(0xA567)
                    if r.p&N:
                        self._a(m[OBJECT_ACTION])
                        self._compare(r.a,0x02)
                        self._mark(0xA591)
                        if r.p&Z:
                            self._a(0x10)
                            m[0x0012]=r.a
                            self._a(m[OBJECT_INDEX])
                            m[0x0013]=r.a
                            self._push(0xA6);self._push(0x11)
                            yield from self.build_object_nametable_packet()
                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                            self._a(0x01)
                            m[STATE]=r.a
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._mark(0xA61C)
                            self._rts();return
                        else:
                            self._y(m[OBJECT_INDEX])
                            self._mark(0xA596)
                            if r.p&Z:
                                self._a(m[0x0574])
                                self._a(r.a & 0xF0)
                                self._mark(0xA5AA)
                                if not r.p&Z:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    self._push(0xA5);self._push(0xAE)
                                    yield from self.choose_object_destination()
                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                    self._push(0xA5);self._push(0xB1)
                                    yield from self.choose_object_axis_direction()
                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                    self._a(m[ACTIVE_SIDE])
                                    self._mark(0xA5B5)
                                    if r.p&N:
                                        self._a(0x10)
                                        m[0x0012]=r.a
                                        self._a(m[OBJECT_INDEX])
                                        m[0x0013]=r.a
                                        self._push(0xA6);self._push(0x11)
                                        yield from self.build_object_nametable_packet()
                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                        self._a(0x01)
                                        m[STATE]=r.a
                                        self._a(0x02)
                                        m[PHASE]=r.a
                                        self._mark(0xA61C)
                                        self._rts();return
                                    else:
                                        m[PHASE]=self._nz(m[PHASE]+1)
                                        self._a(m[ACTIVE_SIDE])
                                        self._push(0xA5);self._push(0xBF)
                                        yield from self.queue_object_redraw()
                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                        self._mark(0xA5C0)
                                        self._rts();return
                            else:
                                self._compare(r.y,0x0B)
                                self._mark(0xA59A)
                                if not r.p&Z:
                                    self._push(0xA5);self._push(0xAE)
                                    yield from self.choose_object_destination()
                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                    self._push(0xA5);self._push(0xB1)
                                    yield from self.choose_object_axis_direction()
                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                    self._a(m[ACTIVE_SIDE])
                                    self._mark(0xA5B5)
                                    if r.p&N:
                                        self._a(0x10)
                                        m[0x0012]=r.a
                                        self._a(m[OBJECT_INDEX])
                                        m[0x0013]=r.a
                                        self._push(0xA6);self._push(0x11)
                                        yield from self.build_object_nametable_packet()
                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                        self._a(0x01)
                                        m[STATE]=r.a
                                        self._a(0x02)
                                        m[PHASE]=r.a
                                        self._mark(0xA61C)
                                        self._rts();return
                                    else:
                                        m[PHASE]=self._nz(m[PHASE]+1)
                                        self._a(m[ACTIVE_SIDE])
                                        self._push(0xA5);self._push(0xBF)
                                        yield from self.queue_object_redraw()
                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                        self._mark(0xA5C0)
                                        self._rts();return
                                else:
                                    self._a(m[0x0574])
                                    self._a(r.a & 0x0F)
                                    self._mark(0xA5A1)
                                    if not r.p&Z:
                                        self._a(0x10)
                                        m[0x0012]=r.a
                                        self._a(m[OBJECT_INDEX])
                                        m[0x0013]=r.a
                                        self._push(0xA6);self._push(0x11)
                                        yield from self.build_object_nametable_packet()
                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                        self._a(0x01)
                                        m[STATE]=r.a
                                        self._a(0x02)
                                        m[PHASE]=r.a
                                        self._mark(0xA61C)
                                        self._rts();return
                                    else:
                                        self._mark(0xA5A3)
                                        if r.p&Z:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                                        else:
                                            self._a(m[0x0574])
                                            self._a(r.a & 0xF0)
                                            self._mark(0xA5AA)
                                            if not r.p&Z:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                self._push(0xA5);self._push(0xAE)
                                                yield from self.choose_object_destination()
                                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                self._push(0xA5);self._push(0xB1)
                                                yield from self.choose_object_axis_direction()
                                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                self._a(m[ACTIVE_SIDE])
                                                self._mark(0xA5B5)
                                                if r.p&N:
                                                    self._a(0x10)
                                                    m[0x0012]=r.a
                                                    self._a(m[OBJECT_INDEX])
                                                    m[0x0013]=r.a
                                                    self._push(0xA6);self._push(0x11)
                                                    yield from self.build_object_nametable_packet()
                                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                    self._a(0x01)
                                                    m[STATE]=r.a
                                                    self._a(0x02)
                                                    m[PHASE]=r.a
                                                    self._mark(0xA61C)
                                                    self._rts();return
                                                else:
                                                    m[PHASE]=self._nz(m[PHASE]+1)
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._push(0xA5);self._push(0xBF)
                                                    yield from self.queue_object_redraw()
                                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                    self._mark(0xA5C0)
                                                    self._rts();return
                    else:
                        self._a(m[OBJECT_ACTION])
                        self._compare(r.a,0x03)
                        self._mark(0xA56E)
                        if not r.p&Z:
                            self._y(m[OBJECT_INDEX])
                            self._a(m[(OBJECT_ENCODING+r.y)&65535])
                            m[SAVED_STATE]=r.a
                            self._a(m[ACTIVE_SIDE])
                            self._push(0xA5);self._push(0x85)
                            yield from self.queue_object_redraw()
                            if r.pc!=0xA586:return  # preserve nonlocal stack return
                            self._a(0x03)
                            m[PHASE]=r.a
                            self._mark(0xA58B)
                            self._rts();return
                        else:
                            self._a(m[(OBJECT_ENCODING+r.x)&65535])
                            self._a(r.a & 0x03)
                            self._mark(0xA575)
                            if r.p&Z:
                                self._a(m[OBJECT_ACTION])
                                self._compare(r.a,0x02)
                                self._mark(0xA591)
                                if r.p&Z:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    self._y(m[OBJECT_INDEX])
                                    self._mark(0xA596)
                                    if r.p&Z:
                                        self._a(m[0x0574])
                                        self._a(r.a & 0xF0)
                                        self._mark(0xA5AA)
                                        if not r.p&Z:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                                    else:
                                        self._compare(r.y,0x0B)
                                        self._mark(0xA59A)
                                        if not r.p&Z:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                                        else:
                                            self._a(m[0x0574])
                                            self._a(r.a & 0x0F)
                                            self._mark(0xA5A1)
                                            if not r.p&Z:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                self._mark(0xA5A3)
                                                if r.p&Z:
                                                    self._push(0xA5);self._push(0xAE)
                                                    yield from self.choose_object_destination()
                                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                    self._push(0xA5);self._push(0xB1)
                                                    yield from self.choose_object_axis_direction()
                                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._mark(0xA5B5)
                                                    if r.p&N:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        m[PHASE]=self._nz(m[PHASE]+1)
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._push(0xA5);self._push(0xBF)
                                                        yield from self.queue_object_redraw()
                                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                        self._mark(0xA5C0)
                                                        self._rts();return
                                                else:
                                                    self._a(m[0x0574])
                                                    self._a(r.a & 0xF0)
                                                    self._mark(0xA5AA)
                                                    if not r.p&Z:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        self._push(0xA5);self._push(0xAE)
                                                        yield from self.choose_object_destination()
                                                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                        self._push(0xA5);self._push(0xB1)
                                                        yield from self.choose_object_axis_direction()
                                                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._mark(0xA5B5)
                                                        if r.p&N:
                                                            self._a(0x10)
                                                            m[0x0012]=r.a
                                                            self._a(m[OBJECT_INDEX])
                                                            m[0x0013]=r.a
                                                            self._push(0xA6);self._push(0x11)
                                                            yield from self.build_object_nametable_packet()
                                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                            self._a(0x01)
                                                            m[STATE]=r.a
                                                            self._a(0x02)
                                                            m[PHASE]=r.a
                                                            self._mark(0xA61C)
                                                            self._rts();return
                                                        else:
                                                            m[PHASE]=self._nz(m[PHASE]+1)
                                                            self._a(m[ACTIVE_SIDE])
                                                            self._push(0xA5);self._push(0xBF)
                                                            yield from self.queue_object_redraw()
                                                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                            self._mark(0xA5C0)
                                                            self._rts();return
                            else:
                                self._y(m[OBJECT_INDEX])
                                self._a(m[(OBJECT_ENCODING+r.y)&65535])
                                m[SAVED_STATE]=r.a
                                self._a(m[ACTIVE_SIDE])
                                self._push(0xA5);self._push(0x85)
                                yield from self.queue_object_redraw()
                                if r.pc!=0xA586:return  # preserve nonlocal stack return
                                self._a(0x03)
                                m[PHASE]=r.a
                                self._mark(0xA58B)
                                self._rts();return
                else:
                    self._a(m[OBJECT_ACTION])
                    self._compare(r.a,0x03)
                    self._mark(0xA543)
                    if not r.p&Z:
                        self._y(m[OBJECT_INDEX])
                        self._a(m[(OBJECT_ENCODING+r.y)&65535])
                        m[SAVED_PHASE]=r.a
                        self._a(m[ACTIVE_SIDE])
                        self._push(0xA5);self._push(0x5A)
                        yield from self.queue_object_redraw()
                        if r.pc!=0xA55B:return  # preserve nonlocal stack return
                        self._a(0x06)
                        m[PHASE]=r.a
                        self._mark(0xA560)
                        self._rts();return
                    else:
                        self._a(m[(OBJECT_ENCODING+r.x)&65535])
                        self._a(r.a & 0x03)
                        self._mark(0xA54A)
                        if r.p&Z:
                            self._push(0xA5);self._push(0x63)
                            yield from self.choose_shifted_object_destination()
                            if r.pc!=0xA564:return  # preserve nonlocal stack return
                            self._a(m[ACTIVE_SIDE])
                            self._mark(0xA567)
                            if r.p&N:
                                self._a(m[OBJECT_ACTION])
                                self._compare(r.a,0x02)
                                self._mark(0xA591)
                                if r.p&Z:
                                    self._a(0x10)
                                    m[0x0012]=r.a
                                    self._a(m[OBJECT_INDEX])
                                    m[0x0013]=r.a
                                    self._push(0xA6);self._push(0x11)
                                    yield from self.build_object_nametable_packet()
                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                    self._a(0x01)
                                    m[STATE]=r.a
                                    self._a(0x02)
                                    m[PHASE]=r.a
                                    self._mark(0xA61C)
                                    self._rts();return
                                else:
                                    self._y(m[OBJECT_INDEX])
                                    self._mark(0xA596)
                                    if r.p&Z:
                                        self._a(m[0x0574])
                                        self._a(r.a & 0xF0)
                                        self._mark(0xA5AA)
                                        if not r.p&Z:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                                    else:
                                        self._compare(r.y,0x0B)
                                        self._mark(0xA59A)
                                        if not r.p&Z:
                                            self._push(0xA5);self._push(0xAE)
                                            yield from self.choose_object_destination()
                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                            self._push(0xA5);self._push(0xB1)
                                            yield from self.choose_object_axis_direction()
                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                            self._a(m[ACTIVE_SIDE])
                                            self._mark(0xA5B5)
                                            if r.p&N:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                self._a(m[ACTIVE_SIDE])
                                                self._push(0xA5);self._push(0xBF)
                                                yield from self.queue_object_redraw()
                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                self._mark(0xA5C0)
                                                self._rts();return
                                        else:
                                            self._a(m[0x0574])
                                            self._a(r.a & 0x0F)
                                            self._mark(0xA5A1)
                                            if not r.p&Z:
                                                self._a(0x10)
                                                m[0x0012]=r.a
                                                self._a(m[OBJECT_INDEX])
                                                m[0x0013]=r.a
                                                self._push(0xA6);self._push(0x11)
                                                yield from self.build_object_nametable_packet()
                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                self._a(0x01)
                                                m[STATE]=r.a
                                                self._a(0x02)
                                                m[PHASE]=r.a
                                                self._mark(0xA61C)
                                                self._rts();return
                                            else:
                                                self._mark(0xA5A3)
                                                if r.p&Z:
                                                    self._push(0xA5);self._push(0xAE)
                                                    yield from self.choose_object_destination()
                                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                    self._push(0xA5);self._push(0xB1)
                                                    yield from self.choose_object_axis_direction()
                                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._mark(0xA5B5)
                                                    if r.p&N:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        m[PHASE]=self._nz(m[PHASE]+1)
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._push(0xA5);self._push(0xBF)
                                                        yield from self.queue_object_redraw()
                                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                        self._mark(0xA5C0)
                                                        self._rts();return
                                                else:
                                                    self._a(m[0x0574])
                                                    self._a(r.a & 0xF0)
                                                    self._mark(0xA5AA)
                                                    if not r.p&Z:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        self._push(0xA5);self._push(0xAE)
                                                        yield from self.choose_object_destination()
                                                        if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                        self._push(0xA5);self._push(0xB1)
                                                        yield from self.choose_object_axis_direction()
                                                        if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._mark(0xA5B5)
                                                        if r.p&N:
                                                            self._a(0x10)
                                                            m[0x0012]=r.a
                                                            self._a(m[OBJECT_INDEX])
                                                            m[0x0013]=r.a
                                                            self._push(0xA6);self._push(0x11)
                                                            yield from self.build_object_nametable_packet()
                                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                            self._a(0x01)
                                                            m[STATE]=r.a
                                                            self._a(0x02)
                                                            m[PHASE]=r.a
                                                            self._mark(0xA61C)
                                                            self._rts();return
                                                        else:
                                                            m[PHASE]=self._nz(m[PHASE]+1)
                                                            self._a(m[ACTIVE_SIDE])
                                                            self._push(0xA5);self._push(0xBF)
                                                            yield from self.queue_object_redraw()
                                                            if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                            self._mark(0xA5C0)
                                                            self._rts();return
                            else:
                                self._a(m[OBJECT_ACTION])
                                self._compare(r.a,0x03)
                                self._mark(0xA56E)
                                if not r.p&Z:
                                    self._y(m[OBJECT_INDEX])
                                    self._a(m[(OBJECT_ENCODING+r.y)&65535])
                                    m[SAVED_STATE]=r.a
                                    self._a(m[ACTIVE_SIDE])
                                    self._push(0xA5);self._push(0x85)
                                    yield from self.queue_object_redraw()
                                    if r.pc!=0xA586:return  # preserve nonlocal stack return
                                    self._a(0x03)
                                    m[PHASE]=r.a
                                    self._mark(0xA58B)
                                    self._rts();return
                                else:
                                    self._a(m[(OBJECT_ENCODING+r.x)&65535])
                                    self._a(r.a & 0x03)
                                    self._mark(0xA575)
                                    if r.p&Z:
                                        self._a(m[OBJECT_ACTION])
                                        self._compare(r.a,0x02)
                                        self._mark(0xA591)
                                        if r.p&Z:
                                            self._a(0x10)
                                            m[0x0012]=r.a
                                            self._a(m[OBJECT_INDEX])
                                            m[0x0013]=r.a
                                            self._push(0xA6);self._push(0x11)
                                            yield from self.build_object_nametable_packet()
                                            if r.pc!=0xA612:return  # preserve nonlocal stack return
                                            self._a(0x01)
                                            m[STATE]=r.a
                                            self._a(0x02)
                                            m[PHASE]=r.a
                                            self._mark(0xA61C)
                                            self._rts();return
                                        else:
                                            self._y(m[OBJECT_INDEX])
                                            self._mark(0xA596)
                                            if r.p&Z:
                                                self._a(m[0x0574])
                                                self._a(r.a & 0xF0)
                                                self._mark(0xA5AA)
                                                if not r.p&Z:
                                                    self._a(0x10)
                                                    m[0x0012]=r.a
                                                    self._a(m[OBJECT_INDEX])
                                                    m[0x0013]=r.a
                                                    self._push(0xA6);self._push(0x11)
                                                    yield from self.build_object_nametable_packet()
                                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                    self._a(0x01)
                                                    m[STATE]=r.a
                                                    self._a(0x02)
                                                    m[PHASE]=r.a
                                                    self._mark(0xA61C)
                                                    self._rts();return
                                                else:
                                                    self._push(0xA5);self._push(0xAE)
                                                    yield from self.choose_object_destination()
                                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                    self._push(0xA5);self._push(0xB1)
                                                    yield from self.choose_object_axis_direction()
                                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._mark(0xA5B5)
                                                    if r.p&N:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        m[PHASE]=self._nz(m[PHASE]+1)
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._push(0xA5);self._push(0xBF)
                                                        yield from self.queue_object_redraw()
                                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                        self._mark(0xA5C0)
                                                        self._rts();return
                                            else:
                                                self._compare(r.y,0x0B)
                                                self._mark(0xA59A)
                                                if not r.p&Z:
                                                    self._push(0xA5);self._push(0xAE)
                                                    yield from self.choose_object_destination()
                                                    if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                    self._push(0xA5);self._push(0xB1)
                                                    yield from self.choose_object_axis_direction()
                                                    if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                    self._a(m[ACTIVE_SIDE])
                                                    self._mark(0xA5B5)
                                                    if r.p&N:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        m[PHASE]=self._nz(m[PHASE]+1)
                                                        self._a(m[ACTIVE_SIDE])
                                                        self._push(0xA5);self._push(0xBF)
                                                        yield from self.queue_object_redraw()
                                                        if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                        self._mark(0xA5C0)
                                                        self._rts();return
                                                else:
                                                    self._a(m[0x0574])
                                                    self._a(r.a & 0x0F)
                                                    self._mark(0xA5A1)
                                                    if not r.p&Z:
                                                        self._a(0x10)
                                                        m[0x0012]=r.a
                                                        self._a(m[OBJECT_INDEX])
                                                        m[0x0013]=r.a
                                                        self._push(0xA6);self._push(0x11)
                                                        yield from self.build_object_nametable_packet()
                                                        if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                        self._a(0x01)
                                                        m[STATE]=r.a
                                                        self._a(0x02)
                                                        m[PHASE]=r.a
                                                        self._mark(0xA61C)
                                                        self._rts();return
                                                    else:
                                                        self._mark(0xA5A3)
                                                        if r.p&Z:
                                                            self._push(0xA5);self._push(0xAE)
                                                            yield from self.choose_object_destination()
                                                            if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                            self._push(0xA5);self._push(0xB1)
                                                            yield from self.choose_object_axis_direction()
                                                            if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                            self._a(m[ACTIVE_SIDE])
                                                            self._mark(0xA5B5)
                                                            if r.p&N:
                                                                self._a(0x10)
                                                                m[0x0012]=r.a
                                                                self._a(m[OBJECT_INDEX])
                                                                m[0x0013]=r.a
                                                                self._push(0xA6);self._push(0x11)
                                                                yield from self.build_object_nametable_packet()
                                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                                self._a(0x01)
                                                                m[STATE]=r.a
                                                                self._a(0x02)
                                                                m[PHASE]=r.a
                                                                self._mark(0xA61C)
                                                                self._rts();return
                                                            else:
                                                                m[PHASE]=self._nz(m[PHASE]+1)
                                                                self._a(m[ACTIVE_SIDE])
                                                                self._push(0xA5);self._push(0xBF)
                                                                yield from self.queue_object_redraw()
                                                                if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                                self._mark(0xA5C0)
                                                                self._rts();return
                                                        else:
                                                            self._a(m[0x0574])
                                                            self._a(r.a & 0xF0)
                                                            self._mark(0xA5AA)
                                                            if not r.p&Z:
                                                                self._a(0x10)
                                                                m[0x0012]=r.a
                                                                self._a(m[OBJECT_INDEX])
                                                                m[0x0013]=r.a
                                                                self._push(0xA6);self._push(0x11)
                                                                yield from self.build_object_nametable_packet()
                                                                if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                                self._a(0x01)
                                                                m[STATE]=r.a
                                                                self._a(0x02)
                                                                m[PHASE]=r.a
                                                                self._mark(0xA61C)
                                                                self._rts();return
                                                            else:
                                                                self._push(0xA5);self._push(0xAE)
                                                                yield from self.choose_object_destination()
                                                                if r.pc!=0xA5AF:return  # preserve nonlocal stack return
                                                                self._push(0xA5);self._push(0xB1)
                                                                yield from self.choose_object_axis_direction()
                                                                if r.pc!=0xA5B2:return  # preserve nonlocal stack return
                                                                self._a(m[ACTIVE_SIDE])
                                                                self._mark(0xA5B5)
                                                                if r.p&N:
                                                                    self._a(0x10)
                                                                    m[0x0012]=r.a
                                                                    self._a(m[OBJECT_INDEX])
                                                                    m[0x0013]=r.a
                                                                    self._push(0xA6);self._push(0x11)
                                                                    yield from self.build_object_nametable_packet()
                                                                    if r.pc!=0xA612:return  # preserve nonlocal stack return
                                                                    self._a(0x01)
                                                                    m[STATE]=r.a
                                                                    self._a(0x02)
                                                                    m[PHASE]=r.a
                                                                    self._mark(0xA61C)
                                                                    self._rts();return
                                                                else:
                                                                    m[PHASE]=self._nz(m[PHASE]+1)
                                                                    self._a(m[ACTIVE_SIDE])
                                                                    self._push(0xA5);self._push(0xBF)
                                                                    yield from self.queue_object_redraw()
                                                                    if r.pc!=0xA5C0:return  # preserve nonlocal stack return
                                                                    self._mark(0xA5C0)
                                                                    self._rts();return
                                    else:
                                        self._y(m[OBJECT_INDEX])
                                        self._a(m[(OBJECT_ENCODING+r.y)&65535])
                                        m[SAVED_STATE]=r.a
                                        self._a(m[ACTIVE_SIDE])
                                        self._push(0xA5);self._push(0x85)
                                        yield from self.queue_object_redraw()
                                        if r.pc!=0xA586:return  # preserve nonlocal stack return
                                        self._a(0x03)
                                        m[PHASE]=r.a
                                        self._mark(0xA58B)
                                        self._rts();return
                        else:
                            self._y(m[OBJECT_INDEX])
                            self._a(m[(OBJECT_ENCODING+r.y)&65535])
                            m[SAVED_PHASE]=r.a
                            self._a(m[ACTIVE_SIDE])
                            self._push(0xA5);self._push(0x5A)
                            yield from self.queue_object_redraw()
                            if r.pc!=0xA55B:return  # preserve nonlocal stack return
                            self._a(0x06)
                            m[PHASE]=r.a
                            self._mark(0xA560)
                            self._rts();return

    def object_action_phase_1(self):
        """Original entry $A5C4; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5C4)
        self._a(0x00)
        m[0x0012]=r.a
        self._a(m[OBJECT_INDEX])
        m[0x0013]=r.a
        self._push(0xA5);self._push(0xCF)
        yield from self.build_object_nametable_packet()
        if r.pc!=0xA5D0:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_X+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x054A]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[SAVED_STATE]=r.a
        self._push(0xA5);self._push(0xF1)
        yield from self.initialize_attack_background()
        if r.pc!=0xA5F2:return  # preserve nonlocal stack return
        self._mark(0xA5F2)
        self._rts();return

    def object_action_phase_2(self):
        """Original entry $A5F3; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA5F3)
        self._push(0xA5);self._push(0xF5)
        yield from self.initialize_attack_background()
        if r.pc!=0xA5F6:return  # preserve nonlocal stack return
        self._push(0xA5);self._push(0xF8)
        yield from self.commit_object_pair_health()
        if r.pc!=0xA5F9:return  # preserve nonlocal stack return
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
        self._a(m[SCAN_CURSOR])
        self._compare(r.a,0x10)
        self._mark(0xA601)
        if not r.p&C:
            pass
        else:
            self._push(0xA6);self._push(0x05)
            yield from self.test_selected_object_health()
            if r.pc!=0xA606:return  # preserve nonlocal stack return
            self._a(0x10)
            m[0x0012]=r.a
            self._a(m[OBJECT_INDEX])
            m[0x0013]=r.a
            self._push(0xA6);self._push(0x11)
            yield from self.build_object_nametable_packet()
            if r.pc!=0xA612:return  # preserve nonlocal stack return
            self._a(0x01)
            m[STATE]=r.a
            self._a(0x02)
            m[PHASE]=r.a
            pass
        self._mark(0xA61C)
        self._rts();return

    def object_action_phase_3(self):
        """Original entry $A61D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA61D)
        self._a(m[OBJECT_INDEX])
        self._mark(0xA620)
        if r.p&Z:
            self._a(m[0x054A])
            self._mark(0xA629)
            if r.p&Z:
                self._a(0x05)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xA639)
                self._rts();return
            else:
                self._compare(r.a,0x0B)
                self._mark(0xA62D)
                if not r.p&Z:
                    self._a(0x10)
                    m[0x0012]=r.a
                    self._a(m[OBJECT_INDEX])
                    m[0x0013]=r.a
                    self._push(0xA6);self._push(0x45)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA646:return  # preserve nonlocal stack return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[SCAN_CURSOR]=r.a
                    self._a(0x5E)
                    yield from self._external(0xA650,0xE609,0xA653,"call",None)
                    if r.pc!=0xA653:return  # preserve nonlocal stack return
                    self._mark(0xA653)
                    self._rts();return
                else:
                    self._a(0x05)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA639)
                    self._rts();return
        else:
            self._compare(r.a,0x0B)
            self._mark(0xA624)
            if not r.p&Z:
                self._a(0x10)
                m[0x0012]=r.a
                self._a(m[OBJECT_INDEX])
                m[0x0013]=r.a
                self._push(0xA6);self._push(0x45)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xA646:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x00)
                m[SCAN_CURSOR]=r.a
                self._a(0x5E)
                yield from self._external(0xA650,0xE609,0xA653,"call",None)
                if r.pc!=0xA653:return  # preserve nonlocal stack return
                self._mark(0xA653)
                self._rts();return
            else:
                self._a(m[0x054A])
                self._mark(0xA629)
                if r.p&Z:
                    self._a(0x05)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA639)
                    self._rts();return
                else:
                    self._compare(r.a,0x0B)
                    self._mark(0xA62D)
                    if not r.p&Z:
                        self._a(0x10)
                        m[0x0012]=r.a
                        self._a(m[OBJECT_INDEX])
                        m[0x0013]=r.a
                        self._push(0xA6);self._push(0x45)
                        yield from self.build_object_nametable_packet()
                        if r.pc!=0xA646:return  # preserve nonlocal stack return
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x00)
                        m[SCAN_CURSOR]=r.a
                        self._a(0x5E)
                        yield from self._external(0xA650,0xE609,0xA653,"call",None)
                        if r.pc!=0xA653:return  # preserve nonlocal stack return
                        self._mark(0xA653)
                        self._rts();return
                    else:
                        self._a(0x05)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xA639)
                        self._rts();return

    def object_action_phase_4(self):
        """Original entry $A654; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA654)
        self._push(0xA6);self._push(0x56)
        yield from self.build_initial_nametable_rows()
        if r.pc!=0xA657:return  # preserve nonlocal stack return
        self._y(m[0x054A])
        self._push(0xA6);self._push(0x5C)
        yield from self.set_object_result_phase()
        if r.pc!=0xA65D:return  # preserve nonlocal stack return
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
        self._a(m[SCAN_CURSOR])
        self._compare(r.a,0x20)
        self._mark(0xA665)
        if not r.p&C:
            self._mark(0xA653)
            self._rts();return
        else:
            self._y(m[OBJECT_INDEX])
            self._a(m[SAVED_STATE])
            m[(OBJECT_ENCODING+r.y)&65535]=r.a
            self._y(m[OBJECT_INDEX])
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0x0F)
            self._compare(r.a,0x02)
            self._mark(0xA67A)
            if not r.p&Z:
                self._push(0xA6);self._push(0x84)
                yield from self.read_object_parameters()
                if r.pc!=0xA685:return  # preserve nonlocal stack return
                pass
            else:
                self._push(0xA6);self._push(0x7E)
                yield from self.resolve_object_collision()
                if r.pc!=0xA67F:return  # preserve nonlocal stack return
                pass
            self._y(m[0x054A])
            self._a(m[(OBJECT_VALUE+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x0000],subtract=True)
            m[(OBJECT_VALUE+r.y)&65535]=r.a
            self._mark(0xA691)
            if r.p&Z:
                self._a(m[0x0001])
                m[0x0000]=r.a
                self._push(0xA6);self._push(0x9B)
                yield from self.move_active_object()
                if r.pc!=0xA69C:return  # preserve nonlocal stack return
                self._a(0x00)
                m[0x0012]=r.a
                self._a(m[0x054A])
                m[0x0013]=r.a
                self._push(0xA6);self._push(0xA7)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xA6A8:return  # preserve nonlocal stack return
                self._y(m[0x054A])
                self._a(0xFF)
                m[(OBJECT_X+r.y)&65535]=r.a
                m[(OBJECT_Y+r.y)&65535]=r.a
                m[(OBJECT_VALUE+r.y)&65535]=r.a
                m[(OBJECT_ENCODING+r.y)&65535]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xA6BC)
                self._rts();return
            else:
                self._mark(0xA693)
                if r.p&C:
                    self._push(0xA6);self._push(0xBF)
                    yield from self.move_active_object()
                    if r.pc!=0xA6C0:return  # preserve nonlocal stack return
                    self._a(0x10)
                    m[0x0012]=r.a
                    self._a(m[0x054A])
                    m[0x0013]=r.a
                    self._push(0xA6);self._push(0xCB)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA6CC:return  # preserve nonlocal stack return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xA6CF)
                    self._rts();return
                else:
                    self._a(m[0x0001])
                    m[0x0000]=r.a
                    self._push(0xA6);self._push(0x9B)
                    yield from self.move_active_object()
                    if r.pc!=0xA69C:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[0x0012]=r.a
                    self._a(m[0x054A])
                    m[0x0013]=r.a
                    self._push(0xA6);self._push(0xA7)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA6A8:return  # preserve nonlocal stack return
                    self._y(m[0x054A])
                    self._a(0xFF)
                    m[(OBJECT_X+r.y)&65535]=r.a
                    m[(OBJECT_Y+r.y)&65535]=r.a
                    m[(OBJECT_VALUE+r.y)&65535]=r.a
                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xA6BC)
                    self._rts();return

    def set_object_result_phase(self):
        """Original entry $A6D0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6D0)
        self._a(m[0x005E])
        self._a(r.a & 0x03)
        self._mark(0xA6D5)
        if r.p&Z:
            pass
        else:
            self._a(m[0x005E])
            self._a(r.a & 0x08)
            m[0x0012]=r.a
            m[0x0013]=r.y
            self._push(0xA6);self._push(0xE2)
            yield from self.build_object_nametable_packet()
            if r.pc!=0xA6E3:return  # preserve nonlocal stack return
            pass
        self._mark(0xA6E3)
        self._rts();return

    def object_action_phase_5(self):
        """Original entry $A6E4; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6E4)
        self._a(m[PPU_JOBS])
        self._a(r.a & 0x04)
        self._mark(0xA6E9)
        if not r.p&Z:
            pass
        else:
            self._a(0x10)
            m[0x0012]=r.a
            self._a(m[OBJECT_INDEX])
            m[0x0013]=r.a
            self._push(0xA6);self._push(0xF6)
            yield from self.build_object_nametable_packet()
            if r.pc!=0xA6F7:return  # preserve nonlocal stack return
            self._a(0x01)
            m[STATE]=r.a
            self._a(0x02)
            m[PHASE]=r.a
            pass
        self._mark(0xA701)
        self._rts();return

    def object_action_phase_6(self):
        """Original entry $A702; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA702)
        self._a(0x10)
        m[0x0012]=r.a
        self._a(m[OBJECT_INDEX])
        m[0x0013]=r.a
        self._push(0xA7);self._push(0x0D)
        yield from self.build_object_nametable_packet()
        if r.pc!=0xA70E:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_X+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x054A]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[SAVED_STATE]=r.a
        self._a(0x5A)
        yield from self._external(0xA72A,0xE69B,0xA72D,"call",None)
        if r.pc!=0xA72D:return  # preserve nonlocal stack return
        self._mark(0xA72D)
        self._rts();return

    def object_action_phase_7(self):
        """Original entry $A72E; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA72E)
        self._push(0xA7);self._push(0x30)
        yield from self.build_initial_attribute_rows()
        if r.pc!=0xA731:return  # preserve nonlocal stack return
        self._push(0xA7);self._push(0x33)
        yield from self.write_object_map_pair()
        if r.pc!=0xA734:return  # preserve nonlocal stack return
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]-1)
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]-1)
        self._mark(0xA73A)
        if not r.p&N:
            self._mark(0xA7B1)
            self._rts();return
        else:
            self._a(0x08)
            m[SCAN_CURSOR]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x5D)
            yield from self._external(0xA746,0xE609,0xA749,"call",None)
            if r.pc!=0xA749:return  # preserve nonlocal stack return
            self._mark(0xA749)
            self._rts();return

    def object_action_phase_8(self):
        """Original entry $A74A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA74A)
        self._push(0xA7);self._push(0x4C)
        yield from self.flush_attack_background()
        if r.pc!=0xA74D:return  # preserve nonlocal stack return
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]-1)
        self._mark(0xA750)
        if not r.p&N:
            pass
        else:
            self._a(0x18)
            m[SCAN_CURSOR]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xA75A)
        self._rts();return

    def object_action_phase_9(self):
        """Original entry $A75B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA75B)
        self._y(m[0x054D])
        self._push(0xA7);self._push(0x60)
        yield from self.set_object_result_phase()
        if r.pc!=0xA761:return  # preserve nonlocal stack return
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]-1)
        self._mark(0xA764)
        if not r.p&N:
            self._mark(0xA7B1)
            self._rts();return
        else:
            self._y(m[OBJECT_INDEX])
            self._a(m[SAVED_PHASE])
            m[(OBJECT_ENCODING+r.y)&65535]=r.a
            self._a(m[0x054D])
            m[0x054A]=r.a
            self._push(0xA7);self._push(0x77)
            yield from self.resolve_object_health_change()
            if r.pc!=0xA778:return  # preserve nonlocal stack return
            self._y(m[0x054D])
            self._a(m[(OBJECT_VALUE+r.y)&65535])
            m[0x0001]=r.a
            self._flag(C,True)
            self._add(m[0x0000],subtract=True)
            m[(OBJECT_VALUE+r.y)&65535]=r.a
            self._mark(0xA786)
            if r.p&Z:
                self._a(m[0x0001])
                m[0x0000]=r.a
                self._push(0xA7);self._push(0x90)
                yield from self.move_active_object()
                if r.pc!=0xA791:return  # preserve nonlocal stack return
                self._a(0x00)
                m[0x0012]=r.a
                self._a(m[0x054D])
                m[0x0013]=r.a
                self._push(0xA7);self._push(0x9C)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xA79D:return  # preserve nonlocal stack return
                self._y(m[0x054D])
                self._a(0xFF)
                m[(OBJECT_X+r.y)&65535]=r.a
                m[(OBJECT_Y+r.y)&65535]=r.a
                m[(OBJECT_VALUE+r.y)&65535]=r.a
                m[(OBJECT_ENCODING+r.y)&65535]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xA7B1)
                self._rts();return
            else:
                self._mark(0xA788)
                if r.p&C:
                    self._push(0xA7);self._push(0xB4)
                    yield from self.move_active_object()
                    if r.pc!=0xA7B5:return  # preserve nonlocal stack return
                    self._a(0x10)
                    m[0x0012]=r.a
                    self._a(m[0x054D])
                    m[0x0013]=r.a
                    self._push(0xA7);self._push(0xC0)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA7C1:return  # preserve nonlocal stack return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xA7C4)
                    self._rts();return
                else:
                    self._a(m[0x0001])
                    m[0x0000]=r.a
                    self._push(0xA7);self._push(0x90)
                    yield from self.move_active_object()
                    if r.pc!=0xA791:return  # preserve nonlocal stack return
                    self._a(0x00)
                    m[0x0012]=r.a
                    self._a(m[0x054D])
                    m[0x0013]=r.a
                    self._push(0xA7);self._push(0x9C)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA79D:return  # preserve nonlocal stack return
                    self._y(m[0x054D])
                    self._a(0xFF)
                    m[(OBJECT_X+r.y)&65535]=r.a
                    m[(OBJECT_Y+r.y)&65535]=r.a
                    m[(OBJECT_VALUE+r.y)&65535]=r.a
                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xA7B1)
                    self._rts();return

    def move_active_object(self):
        """Original entry $A7C5; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7C5)
        self._a(m[0x0000])
        m[0x000B]=r.a
        self._a(0x00)
        m[0x000C]=r.a
        self._a(m[FIRST_OFFICER])
        self._y(m[OBJECT_INDEX])
        self._compare(r.y,0x0B)
        self._mark(0xA7D5)
        if not r.p&C:
            pass
        else:
            self._a(m[SECOND_OFFICER])
            pass
        m[0x000A]=r.a
        self._push(0xA7);self._push(0xDE)
        yield from self.experience_level_code()
        if r.pc!=0xA7DF:return  # preserve nonlocal stack return
        self._mark(0xA7DF)
        self._rts();return

    def object_action_phase_10(self):
        """Original entry $A7E0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7E0)
        self._a(m[PPU_JOBS])
        self._a(r.a & 0x04)
        self._mark(0xA7E5)
        if not r.p&Z:
            pass
        else:
            self._a(0x10)
            m[0x0012]=r.a
            self._a(m[OBJECT_INDEX])
            m[0x0013]=r.a
            self._push(0xA7);self._push(0xF2)
            yield from self.build_object_nametable_packet()
            if r.pc!=0xA7F3:return  # preserve nonlocal stack return
            self._a(0x01)
            m[STATE]=r.a
            self._a(0x02)
            m[PHASE]=r.a
            pass
        self._mark(0xA7FD)
        self._rts();return

    def choose_object_destination(self):
        """Original entry $A7FE; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7FE)
        self._y(m[OBJECT_INDEX])
        self._compare(r.y,0x0B)
        self._mark(0xA803)
        if r.p&C:
            self._a(m[OBJECT_ACTION])
            self._compare(r.a,0x01)
            self._mark(0xA819)
            if not r.p&Z:
                pass
            else:
                self._a(m[(OBJECT_X+r.y)&65535])
                self._a(r.a & 0x0F)
                self._compare(r.a,0x0F)
                self._mark(0xA822)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x00)
                    m[0x0012]=r.a
                    self._a(m[OBJECT_INDEX])
                    m[0x0013]=r.a
                    self._push(0xA8);self._push(0x2F)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA830:return  # preserve nonlocal stack return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._y(m[OBJECT_INDEX])
                    self._a(0xFE)
                    m[(OBJECT_X+r.y)&65535]=r.a
                    m[(OBJECT_Y+r.y)&65535]=r.a
                    self._a(0xFF)
                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                    self._a(self._pop())
                    self._a(self._pop())
                    pass
                pass
            pass
        else:
            self._a(m[OBJECT_ACTION])
            self._compare(r.a,0x01)
            self._mark(0xA80A)
            if not r.p&Z:
                pass
            else:
                self._a(m[(OBJECT_X+r.y)&65535])
                self._mark(0xA80F)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x00)
                    m[0x0012]=r.a
                    self._a(m[OBJECT_INDEX])
                    m[0x0013]=r.a
                    self._push(0xA8);self._push(0x2F)
                    yield from self.build_object_nametable_packet()
                    if r.pc!=0xA830:return  # preserve nonlocal stack return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._y(m[OBJECT_INDEX])
                    self._a(0xFE)
                    m[(OBJECT_X+r.y)&65535]=r.a
                    m[(OBJECT_Y+r.y)&65535]=r.a
                    self._a(0xFF)
                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                    self._a(self._pop())
                    self._a(self._pop())
                    pass
                pass
            pass
        self._mark(0xA84C)
        self._rts();return

    def resolve_object_collision(self):
        """Original entry $A84D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA84D)
        self._a(m[0x056A])
        self._push(r.a)
        self._y(0x3C)
        self._push(0xA8);self._push(0x55)
        yield from self.read_object_pair()
        if r.pc!=0xA856:return  # preserve nonlocal stack return
        m[0x056A]=r.a
        self._a(m[0x056B])
        self._push(r.a)
        self._y(0x3C)
        self._push(0xA8);self._push(0x61)
        yield from self.read_object_pair()
        if r.pc!=0xA862:return  # preserve nonlocal stack return
        m[0x056B]=r.a
        self._push(0xA8);self._push(0x67)
        yield from self.read_object_parameters()
        if r.pc!=0xA868:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[0x056B]=r.a
        self._a(self._pop())
        m[0x056A]=r.a
        self._mark(0xA870)
        self._rts();return

    def resolve_object_health_change(self):
        """Original entry $A871; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA871)
        self._a(m[0x056A])
        self._push(r.a)
        self._y(0x46)
        self._push(0xA8);self._push(0x79)
        yield from self.read_object_pair()
        if r.pc!=0xA87A:return  # preserve nonlocal stack return
        m[0x056A]=r.a
        self._a(m[0x0577])
        self._a(r.a & 0x0F)
        self._mark(0xA882)
        if r.p&Z:
            pass
        else:
            while True:  # natural loop $A884
                yield from self._external(0xA884,0xE87A,0xA887,"call",None)
                if r.pc!=0xA887:return  # preserve nonlocal stack return
                self._a(r.a & 0x0F)
                self._compare(r.a,0x0A)
                self._mark(0xA88B)
                if r.p&C:
                    continue
                else:
                    pass
                self._flag(C,False)
                self._add(m[0x056A])
                self._compare(r.a,0x64)
                self._mark(0xA893)
                if not r.p&C:
                    pass
                else:
                    self._a(0x64)
                    pass
                m[0x056A]=r.a
                self._a(m[0x056B])
                self._push(r.a)
                self._y(0x46)
                self._push(0xA8);self._push(0xA2)
                yield from self.read_object_pair()
                if r.pc!=0xA8A3:return  # preserve nonlocal stack return
                m[0x056B]=r.a
                self._a(m[0x0577])
                self._a(r.a & 0xF0)
                self._mark(0xA8AB)
                if r.p&Z:
                    pass
                else:
                    while True:  # natural loop $A8AD
                        yield from self._external(0xA8AD,0xE87A,0xA8B0,"call",None)
                        if r.pc!=0xA8B0:return  # preserve nonlocal stack return
                        self._a(r.a & 0x0F)
                        self._compare(r.a,0x0A)
                        self._mark(0xA8B4)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._flag(C,False)
                        self._add(m[0x056B])
                        self._compare(r.a,0x64)
                        self._mark(0xA8BC)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x64)
                            pass
                        m[0x056B]=r.a
                        self._push(0xA8);self._push(0xC5)
                        yield from self.read_object_parameters()
                        if r.pc!=0xA8C6:return  # preserve nonlocal stack return
                        self._a(self._pop())
                        m[0x056B]=r.a
                        self._a(self._pop())
                        m[0x056A]=r.a
                        self._mark(0xA8CE)
                        self._rts();return
                self._push(0xA8);self._push(0xC5)
                yield from self.read_object_parameters()
                if r.pc!=0xA8C6:return  # preserve nonlocal stack return
                self._a(self._pop())
                m[0x056B]=r.a
                self._a(self._pop())
                m[0x056A]=r.a
                self._mark(0xA8CE)
                self._rts();return
        self._a(m[0x056B])
        self._push(r.a)
        self._y(0x46)
        self._push(0xA8);self._push(0xA2)
        yield from self.read_object_pair()
        if r.pc!=0xA8A3:return  # preserve nonlocal stack return
        m[0x056B]=r.a
        self._a(m[0x0577])
        self._a(r.a & 0xF0)
        self._mark(0xA8AB)
        if r.p&Z:
            pass
        else:
            while True:  # natural loop $A8AD
                yield from self._external(0xA8AD,0xE87A,0xA8B0,"call",None)
                if r.pc!=0xA8B0:return  # preserve nonlocal stack return
                self._a(r.a & 0x0F)
                self._compare(r.a,0x0A)
                self._mark(0xA8B4)
                if r.p&C:
                    continue
                else:
                    pass
                self._flag(C,False)
                self._add(m[0x056B])
                self._compare(r.a,0x64)
                self._mark(0xA8BC)
                if not r.p&C:
                    pass
                else:
                    self._a(0x64)
                    pass
                m[0x056B]=r.a
                self._push(0xA8);self._push(0xC5)
                yield from self.read_object_parameters()
                if r.pc!=0xA8C6:return  # preserve nonlocal stack return
                self._a(self._pop())
                m[0x056B]=r.a
                self._a(self._pop())
                m[0x056A]=r.a
                self._mark(0xA8CE)
                self._rts();return
        self._push(0xA8);self._push(0xC5)
        yield from self.read_object_parameters()
        if r.pc!=0xA8C6:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[0x056B]=r.a
        self._a(self._pop())
        m[0x056A]=r.a
        self._mark(0xA8CE)
        self._rts();return

    def read_object_pair(self):
        """Original entry $A8CF; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8CF)
        m[0x0003]=r.y
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        yield from self._external(0xA8D9,0xEBE9,0xA8DC,"call",None)
        if r.pc!=0xA8DC:return  # preserve nonlocal stack return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x64)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        yield from self._external(0xA8EC,0xEA7C,0xA8EF,"call",None)
        if r.pc!=0xA8EF:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        self._mark(0xA8F1)
        self._rts();return

    def read_object_parameters(self):
        """Original entry $A8F2; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8F2)
        self._y(m[OBJECT_INDEX])
        self._compare(r.y,0x0B)
        self._mark(0xA8F7)
        if r.p&C:
            self._a(m[0x056B])
            self._compare(r.y,0x0B)
            self._mark(0xA90C)
            if not r.p&Z:
                pass
            else:
                self._flag(C,False)
                self._add(m[0x0571])
                pass
            pass
        else:
            self._a(m[0x056A])
            self._compare(r.y,0x00)
            self._mark(0xA8FE)
            if not r.p&Z:
                pass
            else:
                self._flag(C,False)
                self._add(m[0x0570])
                pass
            pass
        self._push(r.a)
        self._a(m[(OBJECT_VALUE+r.y)&65535])
        self._y(0x14)
        self._compare(r.a,0x0F)
        self._mark(0xA91D)
        if not r.p&C:
            pass
        else:
            self._y(0x28)
            self._compare(r.a,0x23)
            self._mark(0xA923)
            if not r.p&C:
                pass
            else:
                self._y(0x32)
                self._compare(r.a,0x3C)
                self._mark(0xA929)
                if not r.p&C:
                    pass
                else:
                    self._y(0x46)
                    self._compare(r.a,0x50)
                    self._mark(0xA92F)
                    if not r.p&C:
                        pass
                    else:
                        self._y(0x55)
                        self._compare(r.a,0x5A)
                        self._mark(0xA935)
                        if not r.p&C:
                            pass
                        else:
                            self._y(0x5F)
                            self._compare(r.a,0x64)
                            self._mark(0xA93B)
                            if not r.p&C:
                                pass
                            else:
                                self._y(0x64)
                                pass
                            pass
                        pass
                    pass
                pass
            pass
        m[0x0003]=r.y
        self._a(self._pop())
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        yield from self._external(0xA94A,0xEBE9,0xA94D,"call",None)
        if r.pc!=0xA94D:return  # preserve nonlocal stack return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x64)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        yield from self._external(0xA95D,0xEA7C,0xA960,"call",None)
        if r.pc!=0xA960:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        m[0x0000]=r.a
        self._y(m[0x054A])
        self._mark(0xA967)
        if r.p&Z:
            self._a(m[0x0000])
            r.a=self._shift(r.a,False,rotate=False)
            self._push(r.a)
            self._a(m[0x056E])
            self._compare(r.y,0x0B)
            self._mark(0xA982)
            if not r.p&C:
                pass
            else:
                self._a(m[0x056F])
                pass
            m[0x0000]=r.a
            self._a(self._pop())
            self._flag(C,True)
            self._add(m[0x0000],subtract=True)
            self._mark(0xA98D)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                pass
            m[0x0000]=r.a
            pass
        else:
            self._compare(r.y,0x0B)
            self._mark(0xA96B)
            if r.p&Z:
                self._a(m[0x0000])
                r.a=self._shift(r.a,False,rotate=False)
                self._push(r.a)
                self._a(m[0x056E])
                self._compare(r.y,0x0B)
                self._mark(0xA982)
                if not r.p&C:
                    pass
                else:
                    self._a(m[0x056F])
                    pass
                m[0x0000]=r.a
                self._a(self._pop())
                self._flag(C,True)
                self._add(m[0x0000],subtract=True)
                self._mark(0xA98D)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    pass
                m[0x0000]=r.a
                pass
            else:
                self._a(m[(OBJECT_ENCODING+r.y)&65535])
                self._a(r.a & 0x0F)
                self._compare(r.a,0x01)
                self._mark(0xA974)
                if r.p&Z:
                    self._a(m[0x0000])
                    r.a=self._shift(r.a,False,rotate=False)
                    m[0x0000]=r.a
                    r.a=self._shift(r.a,False,rotate=False)
                    self._flag(C,False)
                    self._add(m[0x0000])
                    m[0x0000]=r.a
                    pass
                else:
                    pass
                pass
            pass
        self._mark(0xA99F)
        self._rts();return

    def commit_object_pair_health(self):
        """Original entry $A9A0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9A0)
        self._a(m[ACTIVE_SIDE])
        self._mark(0xA9A3)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xA9AB)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xA9B3)
                if not r.p&Z:
                    m[0x054A]=self._nz(m[0x054A]+1)
                    self._mark(0xA9BC)
                    self._rts();return
                else:
                    m[0x054A]=self._nz(m[0x054A]-1)
                    self._mark(0xA9B8)
                    self._rts();return
            else:
                m[SAVED_STATE]=self._nz(m[SAVED_STATE]+1)
                self._mark(0xA9B0)
                self._rts();return
        else:
            m[SAVED_STATE]=self._nz(m[SAVED_STATE]-1)
            self._mark(0xA9A8)
            self._rts();return

    def test_selected_object_health(self):
        """Original entry $A9BD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9BD)
        self._a(m[ACTIVE_SIDE])
        self._mark(0xA9C0)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xA9CB)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xA9D6)
                if not r.p&Z:
                    self._x(m[OBJECT_INDEX])
                    m[(OBJECT_X+r.x)&65535]=self._nz(m[(OBJECT_X+r.x)&65535]+1)
                    self._mark(0xA9E5)
                    self._rts();return
                else:
                    self._x(m[OBJECT_INDEX])
                    m[(OBJECT_X+r.x)&65535]=self._nz(m[(OBJECT_X+r.x)&65535]-1)
                    self._mark(0xA9DE)
                    self._rts();return
            else:
                self._x(m[OBJECT_INDEX])
                m[(OBJECT_Y+r.x)&65535]=self._nz(m[(OBJECT_Y+r.x)&65535]+1)
                self._mark(0xA9D3)
                self._rts();return
        else:
            self._x(m[OBJECT_INDEX])
            m[(OBJECT_Y+r.x)&65535]=self._nz(m[(OBJECT_Y+r.x)&65535]-1)
            self._mark(0xA9C8)
            self._rts();return

    def write_object_map_pair(self):
        """Original entry $A9E6; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9E6)
        self._a(m[ACTIVE_SIDE])
        self._mark(0xA9E9)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xA9F4)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xA9FF)
                if not r.p&Z:
                    m[0x054A]=self._nz(m[0x054A]+1)
                    m[0x054A]=self._nz(m[0x054A]+1)
                    self._mark(0xAA0E)
                    self._rts();return
                else:
                    m[0x054A]=self._nz(m[0x054A]-1)
                    m[0x054A]=self._nz(m[0x054A]-1)
                    self._mark(0xAA07)
                    self._rts();return
            else:
                m[SAVED_STATE]=self._nz(m[SAVED_STATE]+1)
                m[SAVED_STATE]=self._nz(m[SAVED_STATE]+1)
                self._mark(0xA9FC)
                self._rts();return
        else:
            m[SAVED_STATE]=self._nz(m[SAVED_STATE]-1)
            m[SAVED_STATE]=self._nz(m[SAVED_STATE]-1)
            self._mark(0xA9F1)
            self._rts();return

    def queue_object_redraw(self):
        """Original entry $AA0F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA0F)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0000]=r.a
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        self._a(r.a & 0x0F)
        self._a(r.a | m[0x0000])
        m[(OBJECT_ENCODING+r.y)&65535]=r.a
        self._mark(0xAA22)
        self._rts();return

    def participant_menu(self):
        """Original entry $AA23; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA23)
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xAA35,0xEE07,0xAA3A,"far_call",40960)
        if r.pc!=0xAA3A:return  # preserve nonlocal stack return
        self._a(m[PHASE])
        return (yield from self.participant_menu_phase_dispatch())

    def participant_menu_phase_dispatch(self):
        """Original entry $AA3D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA3D)
        index=self._dispatch(0xAA3D,(43594, 43709, 43760, 43893, 43930))
        return (yield from (self.participant_menu_phase_0,self.participant_menu_phase_1,self.participant_menu_phase_2,self.participant_menu_phase_3,self.participant_menu_phase_4,)[index]())

    def participant_menu_phase_0(self):
        """Original entry $AA4A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA4A)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        m[0x054A]=r.a
        self._a(0xD1)
        yield from self._external(0xAA57,0xF26D,0xAA5A,"call",None)
        if r.pc!=0xAA5A:return  # preserve nonlocal stack return
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        yield from self._external(0xAA60,0xF2D7,0xAA63,"call",None)
        if r.pc!=0xAA63:return  # preserve nonlocal stack return
        self._a(m[OBJECT_VALUE])
        self._y(m[ACTIVE_SIDE])
        self._mark(0xAA69)
        if r.p&Z:
            pass
        else:
            self._a(m[0x05B7])
            pass
        m[0x044C]=r.a
        self._x(m[SAVED_STATE])
        self._compare(r.x,0x01)
        self._mark(0xAA76)
        if r.p&Z:
            pass
        else:
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x044C]=r.a
            pass
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x044F]=r.a
        self._y(0x01)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0452]=r.a
        self._a(0x00)
        m[0x044D]=r.a
        m[0x044E]=r.a
        m[0x0450]=r.a
        m[0x0451]=r.a
        m[0x0453]=r.a
        m[0x0454]=r.a
        m[0x0456]=r.a
        m[0x0457]=r.a
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0455]=r.a
        self._compare(r.a,0x64)
        self._mark(0xAAB0)
        if not r.p&Z:
            pass
        else:
            self._a(0xFE)
            m[0x0457]=r.a
            pass
        self._a(0x06)
        m[0x00BD]=r.a
        self._mark(0xAABC)
        self._rts();return

    def participant_menu_phase_1(self):
        """Original entry $AABD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAABD)
        self._push(0xAA);self._push(0xBF)
        yield from self.text_readiness()
        if r.pc!=0xAAC0:return  # preserve nonlocal stack return
        self._mark(0xAAC0)
        if not r.p&C:
            self._mark(0xAAEF)
            self._rts();return
        else:
            self._a(m[PPU_JOBS])
            self._a(r.a & 0x04)
            self._mark(0xAAC7)
            if not r.p&Z:
                self._mark(0xAAEF)
                self._rts();return
            else:
                self._a(m[SCAN_CURSOR])
                self._compare(r.a,0x04)
                self._mark(0xAACE)
                if r.p&C:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[SCAN_CURSOR]=r.a
                    self._y(m[ACTIVE_SIDE])
                    self._a(m[(FIRST_OFFICER+r.y)&65535])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xAAEA,0xEE07,0xAAEF,"far_call",41008)
                    if r.pc!=0xAAEF:return  # preserve nonlocal stack return
                    self._mark(0xAAEF)
                    self._rts();return
                else:
                    self._push(0xAA);self._push(0xD2)
                    yield from self.change_participant_control()
                    if r.pc!=0xAAD3:return  # preserve nonlocal stack return
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    self._mark(0xAAD6)
                    self._rts();return

    def participant_menu_phase_2(self):
        """Original entry $AAF0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAAF0)
        self._a(m[ACTIVE_SIDE])
        self._push(0xAA);self._push(0xF5)
        yield from self.side_controller_input()
        if r.pc!=0xAAF6:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        self._a(r.a & 0x02)
        self._mark(0xAAFB)
        if r.p&Z:
            pass
        else:
            self._a(m[0x008F])
            self._a(r.a ^ 0x01)
            m[0x008F]=r.a
            pass
        self._a(m[ACTIVE_SIDE])
        self._push(0xAB);self._push(0x0A)
        yield from self.side_controller_input()
        if r.pc!=0xAB0B:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        self._a(r.a & 0x01)
        self._mark(0xAB10)
        if r.p&Z:
            self._push(0xAB);self._push(0x70)
            yield from self.participant_menu_choice()
            if r.pc!=0xAB71:return  # preserve nonlocal stack return
            self._push(0xAB);self._push(0x73)
            yield from self.choose_computer_participant_menu()
            if r.pc!=0xAB74:return  # preserve nonlocal stack return
            self._mark(0xAB74)
            self._rts();return
        else:
            self._a(m[ACTIVE_SIDE])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x0550+r.y)&65535])
            self._compare(r.a,0x04)
            self._mark(0xAB1D)
            if not r.p&Z:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[SAVED_STATE])
                self._compare(r.a,0x01)
                self._mark(0xAB59)
                if not r.p&Z:
                    self._a(0x00)
                    m[0x008F]=r.a
                    self._a(m[SAVED_STATE])
                    m[STATE]=r.a
                    self._a(m[SAVED_PHASE])
                    m[PHASE]=r.a
                    self._mark(0xABC2)
                    self._rts();return
                else:
                    self._a(0xE8)
                    m[0x0310]=r.a
                    self._a(0xE9)
                    m[0x0311]=r.a
                    self._a(0x00)
                    m[0x0300]=r.a
                    self._push(0xAB);self._push(0x6C)
                    yield from self.build_participant_stats_packets()
                    if r.pc!=0xAB6D:return  # preserve nonlocal stack return
                    self._mark(0xAB6D)
                    self._rts();return
            else:
                self._a(m[0x0574])
                self._a(r.a | m[0x0575])
                self._a(r.a | m[0x0576])
                self._a(r.a | m[0x0577])
                self._y(m[ACTIVE_SIDE])
                self._mark(0xAB2E)
                if r.p&Z:
                    self._a(r.a & 0x0F)
                    self._mark(0xAB39)
                    if not r.p&Z:
                        self._push(0xAB);self._push(0x70)
                        yield from self.participant_menu_choice()
                        if r.pc!=0xAB71:return  # preserve nonlocal stack return
                        self._push(0xAB);self._push(0x73)
                        yield from self.choose_computer_participant_menu()
                        if r.pc!=0xAB74:return  # preserve nonlocal stack return
                        self._mark(0xAB74)
                        self._rts();return
                    else:
                        self._a(0x08)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(m[ACTIVE_SIDE])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(0x02)
                        m[(0x0550+r.y)&65535]=r.a
                        self._mark(0xAB50)
                        self._rts();return
                else:
                    self._a(r.a & 0xF0)
                    self._mark(0xAB32)
                    if not r.p&Z:
                        self._push(0xAB);self._push(0x70)
                        yield from self.participant_menu_choice()
                        if r.pc!=0xAB71:return  # preserve nonlocal stack return
                        self._push(0xAB);self._push(0x73)
                        yield from self.choose_computer_participant_menu()
                        if r.pc!=0xAB74:return  # preserve nonlocal stack return
                        self._mark(0xAB74)
                        self._rts();return
                    else:
                        self._a(0x08)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(m[ACTIVE_SIDE])
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(0x02)
                        m[(0x0550+r.y)&65535]=r.a
                        self._mark(0xAB50)
                        self._rts();return

    def participant_menu_phase_3(self):
        """Original entry $AB75; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB75)
        self._a(0x06)
        m[0x00BD]=r.a
        self._push(0xAB);self._push(0x7C)
        yield from self.text_readiness()
        if r.pc!=0xAB7D:return  # preserve nonlocal stack return
        self._mark(0xAB7D)
        if not r.p&C:
            pass
        else:
            self._a(0x09)
            m[0x00BB]=r.a
            self._a(m[FIRST_OFFICER])
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            self._y(0x3D)
            yield from self._external(0xAB91,0xEE07,0xAB96,"far_call",41020)
            if r.pc!=0xAB96:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xAB99)
        self._rts();return

    def participant_menu_phase_4(self):
        """Original entry $AB9A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAB9A)
        self._a(m[PPU_JOBS])
        self._mark(0xAB9D)
        if not r.p&Z:
            pass
        else:
            self._a(m[SECOND_OFFICER])
            m[0x0000]=r.a
            self._a(0x01)
            m[0x0001]=r.a
            self._y(0x3D)
            yield from self._external(0xABAC,0xEE07,0xABB1,"far_call",41020)
            if r.pc!=0xABB1:return  # preserve nonlocal stack return
            self._a(0x00)
            m[0x008F]=r.a
            self._a(m[SAVED_STATE])
            m[STATE]=r.a
            self._a(m[SAVED_PHASE])
            m[PHASE]=r.a
            pass
        self._mark(0xABC2)
        self._rts();return

    def participant_menu_choice(self):
        """Original entry $ABC3; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABC3)
        self._a(m[ACTIVE_SIDE])
        self._push(0xAB);self._push(0xC8)
        yield from self.side_controller_input()
        if r.pc!=0xABC9:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        self._a(r.a & 0x80)
        self._mark(0xABCE)
        if r.p&Z:
            self._a(m[ACTIVE_SIDE])
            self._push(0xAB);self._push(0xFF)
            yield from self.side_controller_input()
            if r.pc!=0xAC00:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x40)
            self._mark(0xAC05)
            if r.p&Z:
                self._a(m[ACTIVE_SIDE])
                self._push(0xAC);self._push(0x3E)
                yield from self.side_controller_input()
                if r.pc!=0xAC3F:return  # preserve nonlocal stack return
                self._a(m[0x0001])
                self._a(r.a & 0x20)
                self._mark(0xAC44)
                if r.p&Z:
                    self._a(m[ACTIVE_SIDE])
                    self._push(0xAC);self._push(0x5D)
                    yield from self.side_controller_input()
                    if r.pc!=0xAC5E:return  # preserve nonlocal stack return
                    self._a(m[0x0001])
                    self._a(r.a & 0x10)
                    self._mark(0xAC63)
                    if r.p&Z:
                        pass
                    else:
                        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]-1)
                        self._mark(0xAC68)
                        if not r.p&N:
                            pass
                        else:
                            self._a(0x03)
                            m[SCAN_CURSOR]=r.a
                            pass
                        self._push(0xAC);self._push(0x71)
                        yield from self.change_participant_control()
                        if r.pc!=0xAC72:return  # preserve nonlocal stack return
                        pass
                    pass
                else:
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    self._a(m[SCAN_CURSOR])
                    self._compare(r.a,0x04)
                    self._mark(0xAC4E)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[SCAN_CURSOR]=r.a
                        pass
                    self._push(0xAC);self._push(0x71)
                    yield from self.change_participant_control()
                    if r.pc!=0xAC72:return  # preserve nonlocal stack return
                    pass
                pass
            else:
                self._a(m[ACTIVE_SIDE])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[SCAN_CURSOR])
                self._y(r.a)
                self._a(0x04)
                self._compare(r.y,0x00)
                self._mark(0xAC14)
                if r.p&Z:
                    self._x(m[SAVED_STATE])
                    self._compare(r.x,0x01)
                    self._mark(0xAC1F)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x05)
                        pass
                    pass
                else:
                    self._compare(r.y,0x04)
                    self._mark(0xAC18)
                    if not r.p&Z:
                        pass
                    else:
                        self._x(m[SAVED_STATE])
                        self._compare(r.x,0x01)
                        self._mark(0xAC1F)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x05)
                            pass
                        pass
                    pass
                m[0x0000]=r.a
                self._a(m[(0x0550+r.y)&65535])
                self._flag(C,False)
                self._add(0x01)
                self._compare(r.a,m[0x0000])
                self._mark(0xAC2F)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    pass
                m[(0x0550+r.y)&65535]=r.a
                self._push(0xAC);self._push(0x71)
                yield from self.change_participant_control()
                if r.pc!=0xAC72:return  # preserve nonlocal stack return
                pass
            pass
        else:
            self._a(m[ACTIVE_SIDE])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._a(r.a | m[SCAN_CURSOR])
            self._y(r.a)
            self._a(m[(0x0550+r.y)&65535])
            self._flag(C,True)
            self._add(0x01,subtract=True)
            self._mark(0xABDF)
            if r.p&C:
                pass
            else:
                self._a(0x03)
                self._compare(r.y,0x00)
                self._mark(0xABE5)
                if r.p&Z:
                    self._x(m[SAVED_STATE])
                    self._compare(r.x,0x01)
                    self._mark(0xABF0)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x04)
                        pass
                    pass
                else:
                    self._compare(r.y,0x04)
                    self._mark(0xABE9)
                    if not r.p&Z:
                        pass
                    else:
                        self._x(m[SAVED_STATE])
                        self._compare(r.x,0x01)
                        self._mark(0xABF0)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x04)
                            pass
                        pass
                    pass
                pass
            m[(0x0550+r.y)&65535]=r.a
            self._push(0xAC);self._push(0x71)
            yield from self.change_participant_control()
            if r.pc!=0xAC72:return  # preserve nonlocal stack return
            pass
        self._mark(0xAC72)
        self._rts();return

    def choose_computer_participant_menu(self):
        """Original entry $AC73; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC73)
        self._a(0xA3)
        m[0x0000]=r.a
        self._a(0xAC)
        m[0x0001]=r.a
        self._y(m[SCAN_CURSOR])
        self._a(m[(0xAC9B+r.y)&65535])
        m[0x000A]=r.a
        self._a(0x80)
        m[0x000C]=r.a
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xAC98)
        yield from self._external(0xAC98,0xF1AD,None,"tail")
        return

    def change_participant_control(self):
        """Original entry $ACA8; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACA8)
        self._a(m[SCAN_CURSOR])
        m[0x0000]=r.a
        self._a(m[ACTIVE_SIDE])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[SCAN_CURSOR])
        self._y(r.a)
        self._a(m[(0x0550+r.y)&65535])
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._push(0xAC);self._push(0xC3)
        yield from self.check_object_side()
        if r.pc!=0xACC4:return  # preserve nonlocal stack return
        self._mark(0xACC4)
        self._rts();return

    def intelligence_action(self):
        """Original entry $ACC5; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACC5)
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xACD7,0xEE07,0xACDC,"far_call",40960)
        if r.pc!=0xACDC:return  # preserve nonlocal stack return
        self._a(m[PHASE])
        return (yield from self.intelligence_action_phase_dispatch())

    def intelligence_action_phase_dispatch(self):
        """Original entry $ACDF; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACDF)
        index=self._dispatch(0xACDF,(44268, 44348, 44381, 44561, 44686))
        return (yield from (self.intelligence_action_phase_0,self.intelligence_action_phase_1,self.intelligence_action_phase_2,self.intelligence_action_phase_3,self.intelligence_action_phase_4,)[index]())

    def intelligence_action_phase_0(self):
        """Original entry $ACEC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACEC)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._y(m[ACTIVE_SIDE])
        self._a(m[(0x0572+r.y)&65535])
        self._y(0x00)
        self._compare(r.a,0x05)
        self._mark(0xACFE)
        if not r.p&C:
            pass
        else:
            self._y(r.y+1)
            self._compare(r.a,0x07)
            self._mark(0xAD03)
            if not r.p&C:
                pass
            else:
                self._y(r.y+1)
                self._compare(r.a,0x08)
                self._mark(0xAD08)
                if not r.p&C:
                    pass
                else:
                    self._y(r.y+1)
                    self._compare(r.a,0x0A)
                    self._mark(0xAD0D)
                    if not r.p&C:
                        pass
                    else:
                        self._y(r.y+1)
                        self._compare(r.a,0x0C)
                        self._mark(0xAD12)
                        if not r.p&C:
                            pass
                        else:
                            self._y(r.y+1)
                            pass
                        pass
                    pass
                pass
            pass
        m[0x054A]=r.y
        self._a(0xE7)
        yield from self._external(0xAD1A,0xF26D,0xAD1D,"call",None)
        if r.pc!=0xAD1D:return  # preserve nonlocal stack return
        self._y(m[ACTIVE_SIDE])
        self._a(m[(0x0572+r.y)&65535])
        m[0x044C]=r.a
        self._a(0x00)
        m[0x044D]=r.a
        m[0x044E]=r.a
        self._a(0x57)
        m[0x00BD]=r.a
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xAD3B)
        self._rts();return

    def intelligence_action_phase_1(self):
        """Original entry $AD3C; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD3C)
        self._push(0xAD);self._push(0x3E)
        yield from self.text_readiness()
        if r.pc!=0xAD3F:return  # preserve nonlocal stack return
        self._mark(0xAD3F)
        if not r.p&C:
            pass
        else:
            self._a(m[PPU_JOBS])
            self._mark(0xAD44)
            if not r.p&Z:
                pass
            else:
                self._a(0x09)
                m[0x00BB]=r.a
                self._push(0xAD);self._push(0x4D)
                yield from self.queue_action_failure()
                if r.pc!=0xAD4E:return  # preserve nonlocal stack return
                self._a(m[SCAN_CURSOR])
                m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                self._compare(r.a,m[0x054A])
                self._mark(0xAD57)
                if not r.p&C:
                    pass
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    pass
                pass
            pass
        self._mark(0xAD5C)
        self._rts();return

    def intelligence_action_phase_2(self):
        """Original entry $AD5D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAD5D)
        self._a(m[0x0083])
        self._push(r.a)
        self._a(m[NEW_BUTTONS])
        self._push(r.a)
        self._a(m[ACTIVE_SIDE])
        self._push(0xAD);self._push(0x6A)
        yield from self.side_controller_input()
        if r.pc!=0xAD6B:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0083]=r.a
        self._a(m[0x0001])
        m[NEW_BUTTONS]=r.a
        self._a(m[0x054A])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xAED0+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(0xAED1+r.y)&65535])
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xAD8D,0xED1E,0xAD90,"call",None)
        if r.pc!=0xAD90:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0010]=r.a
        self._a(0xAF)
        m[0x0011]=r.a
        self._a(0x0C)
        m[0x0000]=r.a
        self._a(0xAF)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xADA7,0xEDF5,0xADAA,"call",None)
        if r.pc!=0xADAA:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[NEW_BUTTONS]=r.a
        self._a(self._pop())
        m[0x0083]=r.a
        self._push(0xAD);self._push(0xB4)
        yield from self.text_readiness()
        if r.pc!=0xADB5:return  # preserve nonlocal stack return
        self._mark(0xADB5)
        if not r.p&C:
            self._mark(0xAE10)
            self._rts();return
        else:
            self._a(m[ACTIVE_SIDE])
            self._push(0xAD);self._push(0xBC)
            yield from self.side_controller_input()
            if r.pc!=0xADBD:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xADC2)
            if r.p&Z:
                self._a(m[ACTIVE_SIDE])
                self._push(0xAD);self._push(0xEC)
                yield from self.side_controller_input()
                if r.pc!=0xADED:return  # preserve nonlocal stack return
                self._a(m[0x0001])
                self._a(r.a & 0x02)
                self._mark(0xADF2)
                if r.p&Z:
                    pass
                else:
                    self._a(0x03)
                    m[STATE]=r.a
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._a(0xE8)
                    m[0x0310]=r.a
                    self._a(0xE9)
                    m[0x0311]=r.a
                    self._a(0x00)
                    m[0x0300]=r.a
                    self._push(0xAE);self._push(0x0F)
                    yield from self.build_participant_stats_packets()
                    if r.pc!=0xAE10:return  # preserve nonlocal stack return
                    pass
                self._mark(0xAE10)
                self._rts();return
            else:
                self._y(m[ACTIVE_SIDE])
                self._a(m[(0x0572+r.y)&65535])
                self._y(m[0x0012])
                self._compare(r.a,m[(0xADDF+r.y)&65535])
                self._mark(0xADD0)
                if not r.p&C:
                    self._a(m[ACTIVE_SIDE])
                    self._push(0xAD);self._push(0xEC)
                    yield from self.side_controller_input()
                    if r.pc!=0xADED:return  # preserve nonlocal stack return
                    self._a(m[0x0001])
                    self._a(r.a & 0x02)
                    self._mark(0xADF2)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0x03)
                        m[STATE]=r.a
                        self._a(0x03)
                        m[PHASE]=r.a
                        self._a(0xE8)
                        m[0x0310]=r.a
                        self._a(0xE9)
                        m[0x0311]=r.a
                        self._a(0x00)
                        m[0x0300]=r.a
                        self._push(0xAE);self._push(0x0F)
                        yield from self.build_participant_stats_packets()
                        if r.pc!=0xAE10:return  # preserve nonlocal stack return
                        pass
                    self._mark(0xAE10)
                    self._rts();return
                else:
                    self._flag(C,True)
                    self._add(m[(0xADDF+r.y)&65535],subtract=True)
                    self._y(m[ACTIVE_SIDE])
                    m[(0x0572+r.y)&65535]=r.a
                    self._a(m[0x0012])
                    m[SCAN_CURSOR]=r.a
                    return (yield from self.object_action_choice_dispatch())

    def intelligence_action_phase_3(self):
        """Original entry $AE11; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE11)
        self._push(0xAE);self._push(0x13)
        yield from self.selected_side_controller_input()
        if r.pc!=0xAE14:return  # preserve nonlocal stack return
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_CONTROLLER+r.y)&65535])
        self._compare(r.a,0x03)
        self._mark(0xAE1C)
        if not r.p&Z:
            self._a(m[ACTIVE_SIDE])
            self._push(0xAE);self._push(0x29)
            yield from self.side_controller_input()
            if r.pc!=0xAE2A:return  # preserve nonlocal stack return
            pass
        else:
            self._push(0xAE);self._push(0x20)
            yield from self.active_side_controller_input()
            if r.pc!=0xAE21:return  # preserve nonlocal stack return
            pass
        self._push(0xAE);self._push(0x2C)
        yield from self.text_readiness()
        if r.pc!=0xAE2D:return  # preserve nonlocal stack return
        self._mark(0xAE2D)
        if not r.p&C:
            self._mark(0xAE6B)
            self._rts();return
        else:
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xAE34)
            if r.p&Z:
                self._mark(0xAE6B)
                self._rts();return
            else:
                self._y(m[ACTIVE_SIDE])
                self._a(m[(FIRST_CONTROLLER+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xAE3E)
                if not r.p&Z:
                    self._a(0x03)
                    m[STATE]=r.a
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._a(0xE8)
                    m[0x0310]=r.a
                    self._a(0xE9)
                    m[0x0311]=r.a
                    self._a(0x00)
                    m[0x0300]=r.a
                    self._a(0x00)
                    m[0x0310]=r.a
                    self._push(0xAE);self._push(0x8C)
                    yield from self.build_participant_stats_packets()
                    if r.pc!=0xAE8D:return  # preserve nonlocal stack return
                    self._mark(0xAE8D)
                    self._rts();return
                else:
                    self._a(0x03)
                    m[STATE]=r.a
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._a(0xE8)
                    m[0x0310]=r.a
                    self._a(0xE9)
                    m[0x0311]=r.a
                    self._a(0x00)
                    m[0x0300]=r.a
                    self._a(0x00)
                    m[0x0310]=r.a
                    self._a(0x01)
                    m[SAVED_STATE]=r.a
                    self._a(0x01)
                    m[SAVED_PHASE]=r.a
                    self._push(0xAE);self._push(0x6A)
                    yield from self.build_participant_stats_packets()
                    if r.pc!=0xAE6B:return  # preserve nonlocal stack return
                    self._mark(0xAE6B)
                    self._rts();return

    def intelligence_action_phase_4(self):
        """Original entry $AE8E; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE8E)
        self._push(0xAE);self._push(0x90)
        yield from self.selected_side_controller_input()
        if r.pc!=0xAE91:return  # preserve nonlocal stack return
        self._a(m[ACTIVE_SIDE])
        self._push(0xAE);self._push(0x96)
        yield from self.side_controller_input()
        if r.pc!=0xAE97:return  # preserve nonlocal stack return
        self._push(0xAE);self._push(0x99)
        yield from self.text_readiness()
        if r.pc!=0xAE9A:return  # preserve nonlocal stack return
        self._mark(0xAE9A)
        if not r.p&C:
            pass
        else:
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xAEA1)
            if r.p&Z:
                pass
            else:
                self._a(0x05)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xAEAD)
        self._rts();return

    def object_action_choice_dispatch(self):
        """Original entry $AF17; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF17)
        index=self._dispatch(0xAF17,(45010, 44838, 45070, 45102, 45180, 45212))
        return (yield from (self.object_action_wait,self.object_action_move,self.object_action_advance,self.object_action_evaluate,self.object_action_success,self.object_action_failure,)[index]())

    def object_action_move(self):
        """Original entry $AF26; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF26)
        self._a(m[BACKGROUND])
        self._compare(r.a,0x05)
        self._mark(0xAF2B)
        if not r.p&Z:
            self._a(m[FIRST_OFFICER])
            yield from self._external(0xAF38,0xF2D7,0xAF3B,"call",None)
            if r.pc!=0xAF3B:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x000A]=r.a
            self._y(0x02)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x000C]=r.a
            self._a(m[SECOND_OFFICER])
            yield from self._external(0xAF50,0xF2D7,0xAF53,"call",None)
            if r.pc!=0xAF53:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x000B]=r.a
            self._y(0x02)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x000D]=r.a
            self._a(m[ACTIVE_SIDE])
            self._mark(0xAF68)
            if r.p&Z:
                pass
            else:
                self._y(m[0x000A])
                self._a(m[0x000B])
                m[0x000A]=r.a
                m[0x000B]=r.y
                self._y(m[0x000C])
                self._a(m[0x000D])
                m[0x000C]=r.a
                m[0x000D]=r.y
                pass
            self._a(m[0x000A])
            self._flag(C,True)
            self._add(m[0x000B],subtract=True)
            self._mark(0xAF89)
            if r.p&C:
                pass
            else:
                self._a(0x00)
                pass
            r.a=self._shift(r.a,True,rotate=False)
            m[0x000A]=r.a
            self._a(m[0x000D])
            m[0x0001]=r.a
            self._a(0x0A)
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            m[0x0004]=r.a
            yield from self._external(0xAFA4,0xEA7C,0xAFA7,"call",None)
            if r.pc!=0xAFA7:return  # preserve nonlocal stack return
            self._a(m[0x000A])
            self._flag(C,False)
            self._add(0x20)
            self._flag(C,True)
            self._add(m[0x0001],subtract=True)
            m[0x000A]=r.a
            self._a(0x64)
            yield from self._external(0xAFB6,0xE862,0xAFB9,"call",None)
            if r.pc!=0xAFB9:return  # preserve nonlocal stack return
            self._compare(r.a,m[0x000A])
            self._mark(0xAFBC)
            if r.p&C:
                self._a(0xEB)
                yield from self._external(0xAFCB,0xF26D,0xAFCE,"call",None)
                if r.pc!=0xAFCE:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xAFD1)
                self._rts();return
            else:
                self._a(0xEA)
                yield from self._external(0xAFC0,0xF26D,0xAFC3,"call",None)
                if r.pc!=0xAFC3:return  # preserve nonlocal stack return
                self._a(0x04)
                m[PHASE]=r.a
                self._mark(0xAFC8)
                self._rts();return
        else:
            self._a(m[ACTIVE_SIDE])
            self._mark(0xAF30)
            if not r.p&Z:
                self._a(m[FIRST_OFFICER])
                yield from self._external(0xAF38,0xF2D7,0xAF3B,"call",None)
                if r.pc!=0xAF3B:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x000A]=r.a
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x000C]=r.a
                self._a(m[SECOND_OFFICER])
                yield from self._external(0xAF50,0xF2D7,0xAF53,"call",None)
                if r.pc!=0xAF53:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x000B]=r.a
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x000D]=r.a
                self._a(m[ACTIVE_SIDE])
                self._mark(0xAF68)
                if r.p&Z:
                    pass
                else:
                    self._y(m[0x000A])
                    self._a(m[0x000B])
                    m[0x000A]=r.a
                    m[0x000B]=r.y
                    self._y(m[0x000C])
                    self._a(m[0x000D])
                    m[0x000C]=r.a
                    m[0x000D]=r.y
                    pass
                self._a(m[0x000A])
                self._flag(C,True)
                self._add(m[0x000B],subtract=True)
                self._mark(0xAF89)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    pass
                r.a=self._shift(r.a,True,rotate=False)
                m[0x000A]=r.a
                self._a(m[0x000D])
                m[0x0001]=r.a
                self._a(0x0A)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                m[0x0004]=r.a
                yield from self._external(0xAFA4,0xEA7C,0xAFA7,"call",None)
                if r.pc!=0xAFA7:return  # preserve nonlocal stack return
                self._a(m[0x000A])
                self._flag(C,False)
                self._add(0x20)
                self._flag(C,True)
                self._add(m[0x0001],subtract=True)
                m[0x000A]=r.a
                self._a(0x64)
                yield from self._external(0xAFB6,0xE862,0xAFB9,"call",None)
                if r.pc!=0xAFB9:return  # preserve nonlocal stack return
                self._compare(r.a,m[0x000A])
                self._mark(0xAFBC)
                if r.p&C:
                    self._a(0xEB)
                    yield from self._external(0xAFCB,0xF26D,0xAFCE,"call",None)
                    if r.pc!=0xAFCE:return  # preserve nonlocal stack return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xAFD1)
                    self._rts();return
                else:
                    self._a(0xEA)
                    yield from self._external(0xAFC0,0xF26D,0xAFC3,"call",None)
                    if r.pc!=0xAFC3:return  # preserve nonlocal stack return
                    self._a(0x04)
                    m[PHASE]=r.a
                    self._mark(0xAFC8)
                    self._rts();return
            else:
                self._a(0xEB)
                yield from self._external(0xAFCB,0xF26D,0xAFCE,"call",None)
                if r.pc!=0xAFCE:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._mark(0xAFD1)
                self._rts();return

    def object_action_wait(self):
        """Original entry $AFD2; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFD2)
        yield from self._external(0xAFD2,0xE87A,0xAFD5,"call",None)
        if r.pc!=0xAFD5:return  # preserve nonlocal stack return
        self._a(r.a & 0x01)
        self._mark(0xAFD7)
        if not r.p&Z:
            self._a(0xEC)
            yield from self._external(0xAFE4,0xF26D,0xAFE7,"call",None)
            if r.pc!=0xAFE7:return  # preserve nonlocal stack return
            self._a(m[ACTIVE_SIDE])
            self._a(r.a ^ 0x01)
            self._y(r.a)
            self._a(m[(FIRST_OFFICER+r.y)&65535])
            m[0x042C]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            return (yield from self.prepare_intelligence_objects())
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0xED)
            yield from self._external(0xAFDE,0xF26D,0xAFE1,"call",None)
            if r.pc!=0xAFE1:return  # preserve nonlocal stack return
            self._mark(0xAFE1)
            self._rts();return

    def prepare_intelligence_objects(self):
        """Original entry $AFF6; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFF6)
        self._a(m[0x0574])
        self._y(m[ACTIVE_SIDE])
        self._mark(0xAFFC)
        if not r.p&Z:
            self._a(r.a & 0x0F)
            self._a(r.a | 0x40)
            m[0x0574]=r.a
            self._mark(0xB00D)
            self._rts();return
        else:
            self._a(r.a & 0xF0)
            self._a(r.a | 0x04)
            m[0x0574]=r.a
            self._mark(0xB005)
            self._rts();return

    def object_action_advance(self):
        """Original entry $B00E; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB00E)
        self._a(0xEE)
        yield from self._external(0xB010,0xF26D,0xB013,"call",None)
        if r.pc!=0xB013:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        return (yield from self.advance_action_object())

    def advance_action_object(self):
        """Original entry $B016; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB016)
        self._a(m[0x0575])
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB01C)
        if not r.p&Z:
            self._a(r.a & 0x0F)
            self._a(r.a | 0x30)
            m[0x0575]=r.a
            self._mark(0xB02D)
            self._rts();return
        else:
            self._a(r.a & 0xF0)
            self._a(r.a | 0x03)
            m[0x0575]=r.a
            self._mark(0xB025)
            self._rts();return

    def object_action_evaluate(self):
        """Original entry $B02E; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB02E)
        self._a(0xEF)
        yield from self._external(0xB030,0xF26D,0xB033,"call",None)
        if r.pc!=0xB033:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        return (yield from self.evaluate_action_object())

    def evaluate_action_object(self):
        """Original entry $B036; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB036)
        self._a(m[0x0576])
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB03C)
        if r.p&Z:
            self._a(r.a & 0xF0)
            self._a(r.a | 0x04)
            m[0x0576]=r.a
            self._a(m[0x056A])
            m[0x0578]=r.a
            self._push(0xB0);self._push(0x61)
            yield from self.resolve_action_success()
            if r.pc!=0xB062:return  # preserve nonlocal stack return
            m[0x056A]=r.a
            self._mark(0xB065)
            self._rts();return
        else:
            self._a(r.a & 0x0F)
            self._a(r.a | 0x40)
            m[0x0576]=r.a
            self._a(m[0x056B])
            m[0x0579]=r.a
            self._push(0xB0);self._push(0x4D)
            yield from self.resolve_action_success()
            if r.pc!=0xB04E:return  # preserve nonlocal stack return
            m[0x056B]=r.a
            self._mark(0xB051)
            self._rts();return

    def resolve_action_success(self):
        """Original entry $B066; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB066)
        self._push(r.a)
        while True:  # natural loop $B067
            yield from self._external(0xB067,0xE87A,0xB06A,"call",None)
            if r.pc!=0xB06A:return  # preserve nonlocal stack return
            self._a(r.a & 0x07)
            self._compare(r.a,0x05)
            self._mark(0xB06E)
            if r.p&C:
                continue
            else:
                pass
            m[0x0000]=r.a
            self._a(self._pop())
            self._flag(C,False)
            self._add(0x05)
            self._flag(C,False)
            self._add(m[0x0000])
            self._mark(0xB07B)
            self._rts();return

    def object_action_success(self):
        """Original entry $B07C; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB07C)
        self._a(0xF0)
        yield from self._external(0xB07E,0xF26D,0xB081,"call",None)
        if r.pc!=0xB081:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        return (yield from self.queue_action_success())

    def queue_action_success(self):
        """Original entry $B084; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB084)
        self._a(m[0x0577])
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB08A)
        if not r.p&Z:
            self._a(r.a & 0x0F)
            self._a(r.a | 0x30)
            m[0x0577]=r.a
            self._mark(0xB09B)
            self._rts();return
        else:
            self._a(r.a & 0xF0)
            self._a(r.a | 0x03)
            m[0x0577]=r.a
            self._mark(0xB093)
            self._rts();return

    def object_action_failure(self):
        """Original entry $B09C; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB09C)
        self._a(0x09)
        m[STATE]=r.a
        self._a(0x00)
        m[PHASE]=r.a
        self._a(0xF1)
        yield from self._external(0xB0A8,0xF26D,0xB0AB,"call",None)
        if r.pc!=0xB0AB:return  # preserve nonlocal stack return
        self._mark(0xB0AB)
        self._rts();return

    def queue_action_failure(self):
        """Original entry $B0AC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB0AC)
        self._a(m[SCAN_CURSOR])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xB0D5+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xB0D6+r.y)&65535])
        m[0x0001]=r.a
        self._y(0x00)
        while True:  # natural loop $B0BF
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0xFF)
            m[(0x0380+r.y)&65535]=r.a
            self._mark(0xB0C6)
            if r.p&Z:
                pass
            else:
                self._y(r.y+1)
                continue
            self._a(m[PPU_JOBS])
            self._a(r.a | 0x04)
            m[PPU_JOBS]=r.a
            self._mark(0xB0D4)
            self._rts();return

    def round_health_update(self):
        """Original entry $B15B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB15B)
        self._a(m[0x0574])
        m[0x0000]=r.a
        self._push(0xB1);self._push(0x63)
        yield from self.draw_action_objects()
        if r.pc!=0xB164:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0574]=r.a
        self._a(m[0x0575])
        m[0x0000]=r.a
        self._push(0xB1);self._push(0x72)
        yield from self.draw_action_objects()
        if r.pc!=0xB173:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0575]=r.a
        self._a(m[0x0576])
        m[0x0000]=r.a
        self._push(0xB1);self._push(0x81)
        yield from self.draw_action_counter()
        if r.pc!=0xB182:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0576]=r.a
        self._a(m[0x0577])
        m[0x0000]=r.a
        self._push(0xB1);self._push(0x90)
        yield from self.draw_action_objects()
        if r.pc!=0xB191:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0577]=r.a
        self._mark(0xB197)
        self._rts();return

    def draw_action_objects(self):
        """Original entry $B198; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB198)
        self._a(m[0x0000])
        self._a(r.a & 0x0F)
        self._mark(0xB19D)
        if r.p&Z:
            pass
        else:
            self._y(m[0x0000])
            self._y(r.y-1)
            m[0x0000]=r.y
            pass
        self._a(m[0x0000])
        self._a(r.a & 0xF0)
        self._mark(0xB1AB)
        if r.p&Z:
            pass
        else:
            self._a(m[0x0000])
            self._flag(C,True)
            self._add(0x10,subtract=True)
            m[0x0000]=r.a
            pass
        self._mark(0xB1B6)
        self._rts();return

    def draw_action_counter(self):
        """Original entry $B1B7; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1B7)
        self._a(m[0x0000])
        self._a(r.a & 0x0F)
        self._mark(0xB1BC)
        if r.p&Z:
            pass
        else:
            self._a(m[0x0000])
            self._flag(C,True)
            self._add(0x01,subtract=True)
            m[0x0000]=r.a
            self._a(r.a & 0x0F)
            self._mark(0xB1C9)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0578])
                m[0x056A]=r.a
                pass
            pass
        self._a(m[0x0000])
        self._a(r.a & 0xF0)
        self._mark(0xB1D6)
        if r.p&Z:
            pass
        else:
            self._a(m[0x0000])
            self._flag(C,True)
            self._add(0x10,subtract=True)
            m[0x0000]=r.a
            self._a(r.a & 0xF0)
            self._mark(0xB1E3)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0579])
                m[0x056B]=r.a
                pass
            pass
        self._mark(0xB1EB)
        self._rts();return

    def object_animation(self):
        """Original entry $B1EC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB1EC)
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xB1FE,0xEE07,0xB203,"far_call",40960)
        if r.pc!=0xB203:return  # preserve nonlocal stack return
        self._a(m[PHASE])
        return (yield from self.object_animation_phase_dispatch())

    def object_animation_phase_dispatch(self):
        """Original entry $B206; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB206)
        index=self._dispatch(0xB206,(45585, 45659, 45813, 46063))
        return (yield from (self.object_animation_phase_0,self.object_animation_phase_1,self.object_animation_phase_2,self.object_animation_phase_3,)[index]())

    def object_animation_phase_0(self):
        """Original entry $B211; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB211)
        self._a(0x7F)
        m[0x00B1]=r.a
        m[0x00C1]=r.a
        m[0x00D1]=r.a
        m[0x00C9]=r.a
        m[0x00D9]=r.a
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB22F)
        if r.p&Z:
            pass
        else:
            self._a(0x0B)
            pass
        m[0x0558]=r.a
        self._y(r.a)
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x0559]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x055A]=r.a
        self._a(m[(OBJECT_X+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x055B]=r.a
        self._a(0x00)
        m[0x008F]=r.a
        self._mark(0xB25A)
        self._rts();return

    def object_animation_phase_1(self):
        """Original entry $B25B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB25B)
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
        self._a(m[SCAN_CURSOR])
        self._compare(r.a,0x20)
        self._mark(0xB263)
        if not r.p&C:
            pass
        else:
            self._a(0x00)
            m[SCAN_CURSOR]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._a(m[0x0559])
        self._mark(0xB270)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xB281)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xB292)
                if not r.p&Z:
                    m[0x055B]=self._nz(m[0x055B]+1)
                    self._a(m[0x055B])
                    self._mark(0xB2A7)
                    if not r.p&Z:
                        self._a(0xE8)
                        m[0x0000]=r.a
                        self._a(0xB2)
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(m[SCAN_CURSOR])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._a(r.a & 0x07)
                        self._y(r.a)
                        self._a(m[0x055A])
                        self._flag(C,True)
                        self._add(m[(0xB2ED+r.y)&65535],subtract=True)
                        m[0x000A]=r.a
                        self._a(m[0x055B])
                        m[0x000C]=r.a
                        self._a(0x00)
                        m[0x000B]=r.a
                        m[0x000D]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        self._a(0xA0)
                        m[0x0004]=r.a
                        self._mark(0xB2E5)
                        yield from self._external(0xB2E5,0xF09C,None,"tail")
                        return
                    else:
                        self._a(0x08)
                        m[STATE]=r.a
                        self._a(0x03)
                        m[PHASE]=r.a
                        self._mark(0xB44A)
                        self._rts();return
                else:
                    m[0x055B]=self._nz(m[0x055B]-1)
                    self._a(m[0x055B])
                    self._compare(r.a,0xFF)
                    self._mark(0xB29C)
                    if r.p&Z:
                        self._a(0x08)
                        m[STATE]=r.a
                        self._a(0x03)
                        m[PHASE]=r.a
                        self._mark(0xB44A)
                        self._rts();return
                    else:
                        self._a(0xE8)
                        m[0x0000]=r.a
                        self._a(0xB2)
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(m[SCAN_CURSOR])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._a(r.a & 0x07)
                        self._y(r.a)
                        self._a(m[0x055A])
                        self._flag(C,True)
                        self._add(m[(0xB2ED+r.y)&65535],subtract=True)
                        m[0x000A]=r.a
                        self._a(m[0x055B])
                        m[0x000C]=r.a
                        self._a(0x00)
                        m[0x000B]=r.a
                        m[0x000D]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        self._a(0xA0)
                        m[0x0004]=r.a
                        self._mark(0xB2E5)
                        yield from self._external(0xB2E5,0xF09C,None,"tail")
                        return
            else:
                m[0x055A]=self._nz(m[0x055A]+1)
                self._a(m[0x055A])
                self._compare(r.a,0xA0)
                self._mark(0xB28B)
                if r.p&C:
                    self._a(0x08)
                    m[STATE]=r.a
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._mark(0xB44A)
                    self._rts();return
                else:
                    self._a(0xE8)
                    m[0x0000]=r.a
                    self._a(0xB2)
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._a(m[SCAN_CURSOR])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._a(r.a & 0x07)
                    self._y(r.a)
                    self._a(m[0x055A])
                    self._flag(C,True)
                    self._add(m[(0xB2ED+r.y)&65535],subtract=True)
                    m[0x000A]=r.a
                    self._a(m[0x055B])
                    m[0x000C]=r.a
                    self._a(0x00)
                    m[0x000B]=r.a
                    m[0x000D]=r.a
                    self._a(0x00)
                    m[0x0003]=r.a
                    self._a(0xA0)
                    m[0x0004]=r.a
                    self._mark(0xB2E5)
                    yield from self._external(0xB2E5,0xF09C,None,"tail")
                    return
        else:
            m[0x055A]=self._nz(m[0x055A]-1)
            self._a(m[0x055A])
            self._compare(r.a,0xA0)
            self._mark(0xB27A)
            if r.p&C:
                self._a(0x08)
                m[STATE]=r.a
                self._a(0x03)
                m[PHASE]=r.a
                self._mark(0xB44A)
                self._rts();return
            else:
                self._a(0xE8)
                m[0x0000]=r.a
                self._a(0xB2)
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                self._a(m[SCAN_CURSOR])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._a(r.a & 0x07)
                self._y(r.a)
                self._a(m[0x055A])
                self._flag(C,True)
                self._add(m[(0xB2ED+r.y)&65535],subtract=True)
                m[0x000A]=r.a
                self._a(m[0x055B])
                m[0x000C]=r.a
                self._a(0x00)
                m[0x000B]=r.a
                m[0x000D]=r.a
                self._a(0x00)
                m[0x0003]=r.a
                self._a(0xA0)
                m[0x0004]=r.a
                self._mark(0xB2E5)
                yield from self._external(0xB2E5,0xF09C,None,"tail")
                return

    def object_animation_phase_2(self):
        """Original entry $B2F5; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB2F5)
        self._a(m[0x005E])
        self._a(r.a & 0x0F)
        self._mark(0xB2FA)
        if not r.p&Z:
            self._a(m[SCAN_CURSOR])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0xB349+r.y)&65535])
            m[0x0000]=r.a
            self._a(m[(0xB34A+r.y)&65535])
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._a(m[0x055A])
            m[0x000A]=r.a
            self._a(m[0x055B])
            m[0x000C]=r.a
            self._a(0x00)
            m[0x000B]=r.a
            m[0x000D]=r.a
            self._a(0x00)
            m[0x0003]=r.a
            self._a(0xA0)
            m[0x0004]=r.a
            self._mark(0xB346)
            yield from self._external(0xB346,0xF09C,None,"tail")
            return
        else:
            m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
            self._a(m[SCAN_CURSOR])
            self._compare(r.a,0x04)
            self._mark(0xB304)
            if not r.p&C:
                self._a(m[SCAN_CURSOR])
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xB349+r.y)&65535])
                m[0x0000]=r.a
                self._a(m[(0xB34A+r.y)&65535])
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                self._a(m[0x055A])
                m[0x000A]=r.a
                self._a(m[0x055B])
                m[0x000C]=r.a
                self._a(0x00)
                m[0x000B]=r.a
                m[0x000D]=r.a
                self._a(0x00)
                m[0x0003]=r.a
                self._a(0xA0)
                m[0x0004]=r.a
                self._mark(0xB346)
                yield from self._external(0xB346,0xF09C,None,"tail")
                return
            else:
                self._push(0xB3);self._push(0x08)
                yield from self.resolve_animation_collision()
                if r.pc!=0xB309:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x00)
                m[SCAN_CURSOR]=r.a
                self._mark(0xB311)
                self._rts();return

    def object_animation_phase_3(self):
        """Original entry $B3EF; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB3EF)
        self._a(0x00)
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB3F4)
        if not r.p&Z:
            pass
        else:
            self._a(0x0B)
            pass
        self._flag(C,False)
        self._add(m[SCAN_CURSOR])
        self._y(r.a)
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        self._compare(r.a,0xFF)
        self._mark(0xB402)
        if r.p&Z:
            pass
        else:
            self._a(m[(OBJECT_VALUE+r.y)&65535])
            self._mark(0xB407)
            if not r.p&Z:
                self._a(0x01)
                m[0x0012]=r.a
                m[0x0013]=r.y
                self._push(0xB4);self._push(0x35)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xB436:return  # preserve nonlocal stack return
                pass
            else:
                self._a(0x00)
                m[0x0012]=r.a
                m[0x0013]=r.y
                self._a(r.y)
                self._push(r.a)
                self._push(0xB4);self._push(0x15)
                yield from self.build_object_nametable_packet()
                if r.pc!=0xB416:return  # preserve nonlocal stack return
                self._a(self._pop())
                self._y(r.a)
                self._a(0xFF)
                m[(OBJECT_X+r.y)&65535]=r.a
                m[(OBJECT_Y+r.y)&65535]=r.a
                m[(OBJECT_ENCODING+r.y)&65535]=r.a
                self._a(0x00)
                m[(OBJECT_VALUE+r.y)&65535]=r.a
                pass
            pass
        m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
        self._a(m[SCAN_CURSOR])
        self._compare(r.a,0x0B)
        self._mark(0xB43E)
        if not r.p&C:
            pass
        else:
            self._a(0x08)
            m[STATE]=r.a
            self._a(0x03)
            m[PHASE]=r.a
            pass
        self._mark(0xB44A)
        self._rts();return

    def resolve_animation_collision(self):
        """Original entry $B44B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB44B)
        self._a(m[0x055A])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x001A]=r.a
        self._a(m[0x055B])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x001B]=r.a
        self._y(m[ACTIVE_SIDE])
        self._mark(0xB462)
        if not r.p&Z:
            self._a(0x00)
            m[0x001C]=r.a
            while True:  # natural loop $B47C
                self._push(0xB4);self._push(0x7E)
                yield from self.update_animation_object()
                if r.pc!=0xB47F:return  # preserve nonlocal stack return
                m[0x001C]=self._nz(m[0x001C]+1)
                self._a(m[0x001C])
                self._compare(r.a,0x0B)
                self._mark(0xB487)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB489)
                self._rts();return
        else:
            self._a(0x0B)
            m[0x001C]=r.a
            while True:  # natural loop $B469
                self._push(0xB4);self._push(0x6B)
                yield from self.update_animation_object()
                if r.pc!=0xB46C:return  # preserve nonlocal stack return
                m[0x001C]=self._nz(m[0x001C]+1)
                self._a(m[0x001C])
                self._compare(r.a,0x16)
                self._mark(0xB474)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB476)
                self._rts();return

    def update_animation_object(self):
        """Original entry $B48A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB48A)
        self._y(m[0x001C])
        self._a(m[(OBJECT_Y+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x001A],subtract=True)
        self._flag(C,False)
        self._add(0x01)
        self._compare(r.a,0x03)
        self._mark(0xB499)
        if r.p&C:
            self._mark(0xB4A9)
            self._rts();return
        else:
            self._a(m[(OBJECT_X+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x001B],subtract=True)
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x03)
            self._mark(0xB4A7)
            if not r.p&C:
                self._push(0xB4);self._push(0xAC)
                yield from self.finish_animation_object()
                if r.pc!=0xB4AD:return  # preserve nonlocal stack return
                self._y(m[0x001C])
                self._a(m[(OBJECT_VALUE+r.y)&65535])
                m[0x0001]=r.a
                self._flag(C,True)
                self._add(m[0x0000],subtract=True)
                m[(OBJECT_VALUE+r.y)&65535]=r.a
                self._mark(0xB4BD)
                if r.p&Z:
                    pass
                else:
                    self._mark(0xB4BF)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[(OBJECT_VALUE+r.y)&65535]=r.a
                        self._a(m[0x0001])
                        m[0x0000]=r.a
                        pass
                    pass
                self._a(m[0x0000])
                m[0x000B]=r.a
                self._a(0x00)
                m[0x000C]=r.a
                self._y(m[ACTIVE_SIDE])
                self._a(m[(FIRST_OFFICER+r.y)&65535])
                m[0x000A]=r.a
                return (yield from self.experience_level_code())
            else:
                self._mark(0xB4A9)
                self._rts();return

    def finish_animation_object(self):
        """Original entry $B4E3; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB4E3)
        self._y(m[ACTIVE_SIDE])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        yield from self._external(0xB4E9,0xF2D7,0xB4EC,"call",None)
        if r.pc!=0xB4EC:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._push(r.a)
        self._a(0x0A)
        yield from self._external(0xB4F3,0xE862,0xB4F6,"call",None)
        if r.pc!=0xB4F6:return  # preserve nonlocal stack return
        self._flag(C,False)
        self._add(0x02)
        m[0x0000]=r.a
        self._a(self._pop())
        self._flag(C,True)
        self._add(m[0x0000],subtract=True)
        self._mark(0xB501)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            pass
        self._flag(C,False)
        self._add(0x01)
        m[0x0000]=r.a
        self._y(m[0x001C])
        self._mark(0xB50E)
        if r.p&Z:
            self._a(m[0x0000])
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0000]=r.a
            pass
        else:
            self._compare(r.y,0x0B)
            self._mark(0xB512)
            if r.p&Z:
                self._a(m[0x0000])
                r.a=self._shift(r.a,False,rotate=False)
                m[0x0000]=r.a
                pass
            else:
                self._a(m[(OBJECT_ENCODING+r.y)&65535])
                self._a(r.a & 0x0F)
                self._compare(r.a,0x01)
                self._mark(0xB51B)
                if r.p&Z:
                    self._a(m[0x0000])
                    m[0x0001]=r.a
                    self._a(0x03)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    m[0x0004]=r.a
                    yield from self._external(0xB53D,0xEA7C,0xB540,"call",None)
                    if r.pc!=0xB540:return  # preserve nonlocal stack return
                    self._a(m[0x0001])
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0000]=r.a
                    pass
                else:
                    pass
                pass
            pass
        self._mark(0xB547)
        self._rts();return

    def prepare_attack_object_arrays(self):
        """Original entry $B548; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB548)
        self._y(0x57)
        self._a(0xFF)
        while True:  # natural loop $B54C
            m[(OBJECT_X+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xB550)
            if not r.p&N:
                continue
            else:
                pass
            self._a(m[FIRST_OFFICER])
            yield from self._external(0xB555,0xF2D7,0xB558,"call",None)
            if r.pc!=0xB558:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[OBJECT_VALUE]=r.a
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._push(r.a)
            self._y(0x01)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._push(r.a)
            self._y(0x09)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._push(r.a)
            m[0x0002]=r.a
            self._y(r.y-1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._push(r.a)
            m[0x0001]=r.a
            self._a(0x64)
            m[0x0003]=r.a
            self._a(0x00)
            m[0x0004]=r.a
            yield from self._external(0xB582,0xEA7C,0xB585,"call",None)
            if r.pc!=0xB585:return  # preserve nonlocal stack return
            self._a(m[0x0005])
            self._mark(0xB588)
            if r.p&Z:
                pass
            else:
                m[0x0001]=self._nz(m[0x0001]+1)
                pass
            self._a(m[0x0001])
            m[0x0566]=r.a
            m[0x0003]=r.a
            self._a(self._pop())
            m[0x0001]=r.a
            self._a(self._pop())
            m[0x0002]=r.a
            self._a(0x00)
            m[0x0004]=r.a
            yield from self._external(0xB5A3,0xEA7C,0xB5A6,"call",None)
            if r.pc!=0xB5A6:return  # preserve nonlocal stack return
            self._y(0x00)
            m[0x0001]=self._nz(m[0x0001]+1)
            self._a(m[0x0001])
            while True:  # natural loop $B5AE
                self._compare(r.y,m[0x0005])
                self._mark(0xB5B1)
                if r.p&C:
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    while True:  # natural loop $B5C1
                        m[(0x05AD+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._compare(r.y,m[0x0566])
                        self._mark(0xB5C8)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._a(m[FIRST_FORMATION])
                        self._a(r.a & 0x03)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(m[(0xB794+r.y)&65535])
                        m[0x000A]=r.a
                        self._a(m[(0xB795+r.y)&65535])
                        m[0x000B]=r.a
                        self._a(m[(0xB7A0+r.y)&65535])
                        m[0x000C]=r.a
                        self._a(m[(0xB7A1+r.y)&65535])
                        m[0x000D]=r.a
                        self._y(0x00)
                        self._a(self._pop())
                        self._compare(r.a,0x50)
                        self._mark(0xB5EE)
                        if r.p&C:
                            pass
                        else:
                            self._y(r.y+1)
                            self._compare(r.a,0x32)
                            self._mark(0xB5F3)
                            if r.p&C:
                                pass
                            else:
                                self._y(r.y+1)
                                pass
                            pass
                        m[0x0000]=r.y
                        self._a(self._pop())
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._a(r.a | m[0x0000])
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(m[(0xB7AC+r.y)&65535])
                        m[0x0001]=r.a
                        self._a(m[(0xB7AD+r.y)&65535])
                        m[0x0002]=r.a
                        self._a(m[0x0566])
                        m[0x0000]=r.a
                        m[0x0000]=self._nz(m[0x0000]+1)
                        self._y(0x00)
                        while True:  # natural loop $B61C
                            self._a(0x30)
                            self._compare(r.y,0x00)
                            self._mark(0xB620)
                            if r.p&Z:
                                pass
                            else:
                                self._a(0x33)
                                self._compare(r.y,m[0x0001])
                                self._mark(0xB627)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x32)
                                    self._compare(r.y,m[0x0002])
                                    self._mark(0xB62E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x31)
                                        pass
                                    pass
                                pass
                            m[(OBJECT_ENCODING+r.y)&65535]=r.a
                            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                            m[(OBJECT_X+r.y)&65535]=r.a
                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                            m[(OBJECT_Y+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._compare(r.y,m[0x0000])
                            self._mark(0xB643)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(m[SECOND_OFFICER])
                            yield from self._external(0xB648,0xF2D7,0xB64B,"call",None)
                            if r.pc!=0xB64B:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x05B7]=r.a
                            self._y(0x0B)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._push(r.a)
                            self._y(0x01)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._push(r.a)
                            self._y(0x09)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._push(r.a)
                            m[0x0002]=r.a
                            self._y(r.y-1)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._push(r.a)
                            m[0x0001]=r.a
                            self._a(0x64)
                            m[0x0003]=r.a
                            self._a(0x00)
                            m[0x0004]=r.a
                            yield from self._external(0xB675,0xEA7C,0xB678,"call",None)
                            if r.pc!=0xB678:return  # preserve nonlocal stack return
                            self._a(m[0x0005])
                            self._mark(0xB67B)
                            if r.p&Z:
                                pass
                            else:
                                m[0x0001]=self._nz(m[0x0001]+1)
                                pass
                            self._a(m[0x0001])
                            m[0x0567]=r.a
                            m[0x0003]=r.a
                            self._a(self._pop())
                            m[0x0001]=r.a
                            self._a(self._pop())
                            m[0x0002]=r.a
                            self._a(0x00)
                            m[0x0004]=r.a
                            yield from self._external(0xB696,0xEA7C,0xB699,"call",None)
                            if r.pc!=0xB699:return  # preserve nonlocal stack return
                            self._y(0x00)
                            m[0x0001]=self._nz(m[0x0001]+1)
                            self._a(m[0x0001])
                            while True:  # natural loop $B6A1
                                self._compare(r.y,m[0x0005])
                                self._mark(0xB6A4)
                                if r.p&C:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    while True:  # natural loop $B6B4
                                        m[(0x05B8+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,m[0x0567])
                                        self._mark(0xB6BB)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0x04)
                                        self._y(m[BACKGROUND])
                                        self._compare(r.y,0x05)
                                        self._mark(0xB6C4)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._a(m[SECOND_FORMATION])
                                            self._a(r.a & 0x03)
                                            pass
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB794+r.y)&65535])
                                        m[0x000A]=r.a
                                        self._a(m[(0xB795+r.y)&65535])
                                        m[0x000B]=r.a
                                        self._a(m[(0xB7A0+r.y)&65535])
                                        m[0x000C]=r.a
                                        self._a(m[(0xB7A1+r.y)&65535])
                                        m[0x000D]=r.a
                                        self._a(m[(0xB796+r.y)&65535])
                                        m[0x001A]=r.a
                                        self._a(m[(0xB797+r.y)&65535])
                                        m[0x001B]=r.a
                                        self._a(m[(0xB7A2+r.y)&65535])
                                        m[0x001C]=r.a
                                        self._a(m[(0xB7A3+r.y)&65535])
                                        m[0x001D]=r.a
                                        self._y(0x00)
                                        self._a(self._pop())
                                        self._compare(r.a,0x50)
                                        self._mark(0xB702)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(r.y+1)
                                            self._compare(r.a,0x32)
                                            self._mark(0xB707)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._y(r.y+1)
                                                pass
                                            pass
                                        m[0x0000]=r.y
                                        self._a(self._pop())
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._a(r.a | m[0x0000])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB7AC+r.y)&65535])
                                        m[0x0001]=r.a
                                        self._a(m[(0xB7AD+r.y)&65535])
                                        m[0x0002]=r.a
                                        self._a(m[BACKGROUND])
                                        self._compare(r.a,0x05)
                                        self._mark(0xB72A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0001]=r.a
                                            pass
                                        self._a(m[0x0567])
                                        m[0x0000]=r.a
                                        m[0x0000]=self._nz(m[0x0000]+1)
                                        self._y(0x00)
                                        while True:  # natural loop $B73C
                                            self._a(0x20)
                                            self._compare(r.y,0x00)
                                            self._mark(0xB740)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(0x23)
                                                self._compare(r.y,m[0x0001])
                                                self._mark(0xB747)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x22)
                                                    self._compare(r.y,m[0x0002])
                                                    self._mark(0xB74E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x21)
                                                        pass
                                                    pass
                                                pass
                                            m[(0x05CD+r.y)&65535]=r.a
                                            self._compare(r.a,0x22)
                                            self._mark(0xB757)
                                            if r.p&Z:
                                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                m[0x0003]=r.a
                                                self._a(0x0F)
                                                self._flag(C,True)
                                                self._add(m[0x0003],subtract=True)
                                                m[(0x058B+r.y)&65535]=r.a
                                                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                m[(0x05A1+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,m[0x0000])
                                                self._mark(0xB791)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._mark(0xB793)
                                                    self._rts();return
                                            else:
                                                self._a(m[BACKGROUND])
                                                self._compare(r.a,0x05)
                                                self._mark(0xB75E)
                                                if not r.p&Z:
                                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB791)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB793)
                                                        self._rts();return
                                                else:
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB777)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB779)
                                                        self._rts();return
                                else:
                                    m[(0x05B8+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0567])
                                    self._mark(0xB6AD)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._mark(0xB6AF)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            while True:  # natural loop $B6B4
                                                m[(0x05B8+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,m[0x0567])
                                                self._mark(0xB6BB)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(0x04)
                                                self._y(m[BACKGROUND])
                                                self._compare(r.y,0x05)
                                                self._mark(0xB6C4)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    self._a(m[SECOND_FORMATION])
                                                    self._a(r.a & 0x03)
                                                    pass
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._y(r.a)
                                                self._a(m[(0xB794+r.y)&65535])
                                                m[0x000A]=r.a
                                                self._a(m[(0xB795+r.y)&65535])
                                                m[0x000B]=r.a
                                                self._a(m[(0xB7A0+r.y)&65535])
                                                m[0x000C]=r.a
                                                self._a(m[(0xB7A1+r.y)&65535])
                                                m[0x000D]=r.a
                                                self._a(m[(0xB796+r.y)&65535])
                                                m[0x001A]=r.a
                                                self._a(m[(0xB797+r.y)&65535])
                                                m[0x001B]=r.a
                                                self._a(m[(0xB7A2+r.y)&65535])
                                                m[0x001C]=r.a
                                                self._a(m[(0xB7A3+r.y)&65535])
                                                m[0x001D]=r.a
                                                self._y(0x00)
                                                self._a(self._pop())
                                                self._compare(r.a,0x50)
                                                self._mark(0xB702)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._y(r.y+1)
                                                    self._compare(r.a,0x32)
                                                    self._mark(0xB707)
                                                    if r.p&C:
                                                        pass
                                                    else:
                                                        self._y(r.y+1)
                                                        pass
                                                    pass
                                                m[0x0000]=r.y
                                                self._a(self._pop())
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._a(r.a | m[0x0000])
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._y(r.a)
                                                self._a(m[(0xB7AC+r.y)&65535])
                                                m[0x0001]=r.a
                                                self._a(m[(0xB7AD+r.y)&65535])
                                                m[0x0002]=r.a
                                                self._a(m[BACKGROUND])
                                                self._compare(r.a,0x05)
                                                self._mark(0xB72A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0001]=r.a
                                                    pass
                                                self._a(m[0x0567])
                                                m[0x0000]=r.a
                                                m[0x0000]=self._nz(m[0x0000]+1)
                                                self._y(0x00)
                                                while True:  # natural loop $B73C
                                                    self._a(0x20)
                                                    self._compare(r.y,0x00)
                                                    self._mark(0xB740)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._a(0x23)
                                                        self._compare(r.y,m[0x0001])
                                                        self._mark(0xB747)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._a(0x22)
                                                            self._compare(r.y,m[0x0002])
                                                            self._mark(0xB74E)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                self._a(0x21)
                                                                pass
                                                            pass
                                                        pass
                                                    m[(0x05CD+r.y)&65535]=r.a
                                                    self._compare(r.a,0x22)
                                                    self._mark(0xB757)
                                                    if r.p&Z:
                                                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                        m[0x0003]=r.a
                                                        self._a(0x0F)
                                                        self._flag(C,True)
                                                        self._add(m[0x0003],subtract=True)
                                                        m[(0x058B+r.y)&65535]=r.a
                                                        self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                        m[(0x05A1+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,m[0x0000])
                                                        self._mark(0xB791)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._mark(0xB793)
                                                            self._rts();return
                                                    else:
                                                        self._a(m[BACKGROUND])
                                                        self._compare(r.a,0x05)
                                                        self._mark(0xB75E)
                                                        if not r.p&Z:
                                                            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                            m[0x0003]=r.a
                                                            self._a(0x0F)
                                                            self._flag(C,True)
                                                            self._add(m[0x0003],subtract=True)
                                                            m[(0x058B+r.y)&65535]=r.a
                                                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                            m[(0x05A1+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,m[0x0000])
                                                            self._mark(0xB791)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xB793)
                                                                self._rts();return
                                                        else:
                                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                            m[0x0003]=r.a
                                                            self._a(0x0F)
                                                            self._flag(C,True)
                                                            self._add(m[0x0003],subtract=True)
                                                            m[(0x058B+r.y)&65535]=r.a
                                                            self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                            m[(0x05A1+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,m[0x0000])
                                                            self._mark(0xB777)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xB779)
                                                                self._rts();return
                                        pass
                                    pass
                                self._a(0x04)
                                self._y(m[BACKGROUND])
                                self._compare(r.y,0x05)
                                self._mark(0xB6C4)
                                if r.p&Z:
                                    pass
                                else:
                                    self._a(m[SECOND_FORMATION])
                                    self._a(r.a & 0x03)
                                    pass
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB794+r.y)&65535])
                                m[0x000A]=r.a
                                self._a(m[(0xB795+r.y)&65535])
                                m[0x000B]=r.a
                                self._a(m[(0xB7A0+r.y)&65535])
                                m[0x000C]=r.a
                                self._a(m[(0xB7A1+r.y)&65535])
                                m[0x000D]=r.a
                                self._a(m[(0xB796+r.y)&65535])
                                m[0x001A]=r.a
                                self._a(m[(0xB797+r.y)&65535])
                                m[0x001B]=r.a
                                self._a(m[(0xB7A2+r.y)&65535])
                                m[0x001C]=r.a
                                self._a(m[(0xB7A3+r.y)&65535])
                                m[0x001D]=r.a
                                self._y(0x00)
                                self._a(self._pop())
                                self._compare(r.a,0x50)
                                self._mark(0xB702)
                                if r.p&C:
                                    pass
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.a,0x32)
                                    self._mark(0xB707)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._y(r.y+1)
                                        pass
                                    pass
                                m[0x0000]=r.y
                                self._a(self._pop())
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._a(r.a | m[0x0000])
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB7AC+r.y)&65535])
                                m[0x0001]=r.a
                                self._a(m[(0xB7AD+r.y)&65535])
                                m[0x0002]=r.a
                                self._a(m[BACKGROUND])
                                self._compare(r.a,0x05)
                                self._mark(0xB72A)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(0x00)
                                    m[0x0001]=r.a
                                    pass
                                self._a(m[0x0567])
                                m[0x0000]=r.a
                                m[0x0000]=self._nz(m[0x0000]+1)
                                self._y(0x00)
                                while True:  # natural loop $B73C
                                    self._a(0x20)
                                    self._compare(r.y,0x00)
                                    self._mark(0xB740)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(0x23)
                                        self._compare(r.y,m[0x0001])
                                        self._mark(0xB747)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x22)
                                            self._compare(r.y,m[0x0002])
                                            self._mark(0xB74E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x21)
                                                pass
                                            pass
                                        pass
                                    m[(0x05CD+r.y)&65535]=r.a
                                    self._compare(r.a,0x22)
                                    self._mark(0xB757)
                                    if r.p&Z:
                                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                        m[0x0003]=r.a
                                        self._a(0x0F)
                                        self._flag(C,True)
                                        self._add(m[0x0003],subtract=True)
                                        m[(0x058B+r.y)&65535]=r.a
                                        self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                        m[(0x05A1+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,m[0x0000])
                                        self._mark(0xB791)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._mark(0xB793)
                                            self._rts();return
                                    else:
                                        self._a(m[BACKGROUND])
                                        self._compare(r.a,0x05)
                                        self._mark(0xB75E)
                                        if not r.p&Z:
                                            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                            m[0x0003]=r.a
                                            self._a(0x0F)
                                            self._flag(C,True)
                                            self._add(m[0x0003],subtract=True)
                                            m[(0x058B+r.y)&65535]=r.a
                                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                            m[(0x05A1+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,m[0x0000])
                                            self._mark(0xB791)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB793)
                                                self._rts();return
                                        else:
                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                            m[0x0003]=r.a
                                            self._a(0x0F)
                                            self._flag(C,True)
                                            self._add(m[0x0003],subtract=True)
                                            m[(0x058B+r.y)&65535]=r.a
                                            self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                            m[(0x05A1+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,m[0x0000])
                                            self._mark(0xB777)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB779)
                                                self._rts();return
                else:
                    m[(0x05AD+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._compare(r.y,m[0x0566])
                    self._mark(0xB5BA)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xB5BC)
                        if r.p&C:
                            pass
                        else:
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            while True:  # natural loop $B5C1
                                m[(0x05AD+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._compare(r.y,m[0x0566])
                                self._mark(0xB5C8)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(m[FIRST_FORMATION])
                                self._a(r.a & 0x03)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB794+r.y)&65535])
                                m[0x000A]=r.a
                                self._a(m[(0xB795+r.y)&65535])
                                m[0x000B]=r.a
                                self._a(m[(0xB7A0+r.y)&65535])
                                m[0x000C]=r.a
                                self._a(m[(0xB7A1+r.y)&65535])
                                m[0x000D]=r.a
                                self._y(0x00)
                                self._a(self._pop())
                                self._compare(r.a,0x50)
                                self._mark(0xB5EE)
                                if r.p&C:
                                    pass
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.a,0x32)
                                    self._mark(0xB5F3)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._y(r.y+1)
                                        pass
                                    pass
                                m[0x0000]=r.y
                                self._a(self._pop())
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._a(r.a | m[0x0000])
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB7AC+r.y)&65535])
                                m[0x0001]=r.a
                                self._a(m[(0xB7AD+r.y)&65535])
                                m[0x0002]=r.a
                                self._a(m[0x0566])
                                m[0x0000]=r.a
                                m[0x0000]=self._nz(m[0x0000]+1)
                                self._y(0x00)
                                while True:  # natural loop $B61C
                                    self._a(0x30)
                                    self._compare(r.y,0x00)
                                    self._mark(0xB620)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(0x33)
                                        self._compare(r.y,m[0x0001])
                                        self._mark(0xB627)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x32)
                                            self._compare(r.y,m[0x0002])
                                            self._mark(0xB62E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x31)
                                                pass
                                            pass
                                        pass
                                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                    m[(OBJECT_X+r.y)&65535]=r.a
                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                    m[(OBJECT_Y+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0000])
                                    self._mark(0xB643)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    self._a(m[SECOND_OFFICER])
                                    yield from self._external(0xB648,0xF2D7,0xB64B,"call",None)
                                    if r.pc!=0xB64B:return  # preserve nonlocal stack return
                                    self._y(0x00)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    m[0x05B7]=r.a
                                    self._y(0x0B)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._push(r.a)
                                    self._y(0x01)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._push(r.a)
                                    self._y(0x09)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._push(r.a)
                                    m[0x0002]=r.a
                                    self._y(r.y-1)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._push(r.a)
                                    m[0x0001]=r.a
                                    self._a(0x64)
                                    m[0x0003]=r.a
                                    self._a(0x00)
                                    m[0x0004]=r.a
                                    yield from self._external(0xB675,0xEA7C,0xB678,"call",None)
                                    if r.pc!=0xB678:return  # preserve nonlocal stack return
                                    self._a(m[0x0005])
                                    self._mark(0xB67B)
                                    if r.p&Z:
                                        pass
                                    else:
                                        m[0x0001]=self._nz(m[0x0001]+1)
                                        pass
                                    self._a(m[0x0001])
                                    m[0x0567]=r.a
                                    m[0x0003]=r.a
                                    self._a(self._pop())
                                    m[0x0001]=r.a
                                    self._a(self._pop())
                                    m[0x0002]=r.a
                                    self._a(0x00)
                                    m[0x0004]=r.a
                                    yield from self._external(0xB696,0xEA7C,0xB699,"call",None)
                                    if r.pc!=0xB699:return  # preserve nonlocal stack return
                                    self._y(0x00)
                                    m[0x0001]=self._nz(m[0x0001]+1)
                                    self._a(m[0x0001])
                                    while True:  # natural loop $B6A1
                                        self._compare(r.y,m[0x0005])
                                        self._mark(0xB6A4)
                                        if r.p&C:
                                            self._flag(C,True)
                                            self._add(0x01,subtract=True)
                                            while True:  # natural loop $B6B4
                                                m[(0x05B8+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,m[0x0567])
                                                self._mark(0xB6BB)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    pass
                                                self._a(0x04)
                                                self._y(m[BACKGROUND])
                                                self._compare(r.y,0x05)
                                                self._mark(0xB6C4)
                                                if r.p&Z:
                                                    pass
                                                else:
                                                    self._a(m[SECOND_FORMATION])
                                                    self._a(r.a & 0x03)
                                                    pass
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._y(r.a)
                                                self._a(m[(0xB794+r.y)&65535])
                                                m[0x000A]=r.a
                                                self._a(m[(0xB795+r.y)&65535])
                                                m[0x000B]=r.a
                                                self._a(m[(0xB7A0+r.y)&65535])
                                                m[0x000C]=r.a
                                                self._a(m[(0xB7A1+r.y)&65535])
                                                m[0x000D]=r.a
                                                self._a(m[(0xB796+r.y)&65535])
                                                m[0x001A]=r.a
                                                self._a(m[(0xB797+r.y)&65535])
                                                m[0x001B]=r.a
                                                self._a(m[(0xB7A2+r.y)&65535])
                                                m[0x001C]=r.a
                                                self._a(m[(0xB7A3+r.y)&65535])
                                                m[0x001D]=r.a
                                                self._y(0x00)
                                                self._a(self._pop())
                                                self._compare(r.a,0x50)
                                                self._mark(0xB702)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._y(r.y+1)
                                                    self._compare(r.a,0x32)
                                                    self._mark(0xB707)
                                                    if r.p&C:
                                                        pass
                                                    else:
                                                        self._y(r.y+1)
                                                        pass
                                                    pass
                                                m[0x0000]=r.y
                                                self._a(self._pop())
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,False,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._a(r.a | m[0x0000])
                                                r.a=self._shift(r.a,True,rotate=False)
                                                self._y(r.a)
                                                self._a(m[(0xB7AC+r.y)&65535])
                                                m[0x0001]=r.a
                                                self._a(m[(0xB7AD+r.y)&65535])
                                                m[0x0002]=r.a
                                                self._a(m[BACKGROUND])
                                                self._compare(r.a,0x05)
                                                self._mark(0xB72A)
                                                if not r.p&Z:
                                                    pass
                                                else:
                                                    self._a(0x00)
                                                    m[0x0001]=r.a
                                                    pass
                                                self._a(m[0x0567])
                                                m[0x0000]=r.a
                                                m[0x0000]=self._nz(m[0x0000]+1)
                                                self._y(0x00)
                                                while True:  # natural loop $B73C
                                                    self._a(0x20)
                                                    self._compare(r.y,0x00)
                                                    self._mark(0xB740)
                                                    if r.p&Z:
                                                        pass
                                                    else:
                                                        self._a(0x23)
                                                        self._compare(r.y,m[0x0001])
                                                        self._mark(0xB747)
                                                        if not r.p&C:
                                                            pass
                                                        else:
                                                            self._a(0x22)
                                                            self._compare(r.y,m[0x0002])
                                                            self._mark(0xB74E)
                                                            if not r.p&C:
                                                                pass
                                                            else:
                                                                self._a(0x21)
                                                                pass
                                                            pass
                                                        pass
                                                    m[(0x05CD+r.y)&65535]=r.a
                                                    self._compare(r.a,0x22)
                                                    self._mark(0xB757)
                                                    if r.p&Z:
                                                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                        m[0x0003]=r.a
                                                        self._a(0x0F)
                                                        self._flag(C,True)
                                                        self._add(m[0x0003],subtract=True)
                                                        m[(0x058B+r.y)&65535]=r.a
                                                        self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                        m[(0x05A1+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,m[0x0000])
                                                        self._mark(0xB791)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            self._mark(0xB793)
                                                            self._rts();return
                                                    else:
                                                        self._a(m[BACKGROUND])
                                                        self._compare(r.a,0x05)
                                                        self._mark(0xB75E)
                                                        if not r.p&Z:
                                                            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                            m[0x0003]=r.a
                                                            self._a(0x0F)
                                                            self._flag(C,True)
                                                            self._add(m[0x0003],subtract=True)
                                                            m[(0x058B+r.y)&65535]=r.a
                                                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                            m[(0x05A1+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,m[0x0000])
                                                            self._mark(0xB791)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xB793)
                                                                self._rts();return
                                                        else:
                                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                            m[0x0003]=r.a
                                                            self._a(0x0F)
                                                            self._flag(C,True)
                                                            self._add(m[0x0003],subtract=True)
                                                            m[(0x058B+r.y)&65535]=r.a
                                                            self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                            m[(0x05A1+r.y)&65535]=r.a
                                                            self._y(r.y+1)
                                                            self._compare(r.y,m[0x0000])
                                                            self._mark(0xB777)
                                                            if not r.p&C:
                                                                continue
                                                            else:
                                                                self._mark(0xB779)
                                                                self._rts();return
                                        else:
                                            m[(0x05B8+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,m[0x0567])
                                            self._mark(0xB6AD)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB6AF)
                                                if r.p&C:
                                                    pass
                                                else:
                                                    self._flag(C,True)
                                                    self._add(0x01,subtract=True)
                                                    while True:  # natural loop $B6B4
                                                        m[(0x05B8+r.y)&65535]=r.a
                                                        self._y(r.y+1)
                                                        self._compare(r.y,m[0x0567])
                                                        self._mark(0xB6BB)
                                                        if not r.p&C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(0x04)
                                                        self._y(m[BACKGROUND])
                                                        self._compare(r.y,0x05)
                                                        self._mark(0xB6C4)
                                                        if r.p&Z:
                                                            pass
                                                        else:
                                                            self._a(m[SECOND_FORMATION])
                                                            self._a(r.a & 0x03)
                                                            pass
                                                        r.a=self._shift(r.a,True,rotate=False)
                                                        self._y(r.a)
                                                        self._a(m[(0xB794+r.y)&65535])
                                                        m[0x000A]=r.a
                                                        self._a(m[(0xB795+r.y)&65535])
                                                        m[0x000B]=r.a
                                                        self._a(m[(0xB7A0+r.y)&65535])
                                                        m[0x000C]=r.a
                                                        self._a(m[(0xB7A1+r.y)&65535])
                                                        m[0x000D]=r.a
                                                        self._a(m[(0xB796+r.y)&65535])
                                                        m[0x001A]=r.a
                                                        self._a(m[(0xB797+r.y)&65535])
                                                        m[0x001B]=r.a
                                                        self._a(m[(0xB7A2+r.y)&65535])
                                                        m[0x001C]=r.a
                                                        self._a(m[(0xB7A3+r.y)&65535])
                                                        m[0x001D]=r.a
                                                        self._y(0x00)
                                                        self._a(self._pop())
                                                        self._compare(r.a,0x50)
                                                        self._mark(0xB702)
                                                        if r.p&C:
                                                            pass
                                                        else:
                                                            self._y(r.y+1)
                                                            self._compare(r.a,0x32)
                                                            self._mark(0xB707)
                                                            if r.p&C:
                                                                pass
                                                            else:
                                                                self._y(r.y+1)
                                                                pass
                                                            pass
                                                        m[0x0000]=r.y
                                                        self._a(self._pop())
                                                        r.a=self._shift(r.a,False,rotate=False)
                                                        r.a=self._shift(r.a,False,rotate=False)
                                                        r.a=self._shift(r.a,False,rotate=False)
                                                        r.a=self._shift(r.a,False,rotate=False)
                                                        r.a=self._shift(r.a,True,rotate=False)
                                                        r.a=self._shift(r.a,True,rotate=False)
                                                        self._a(r.a | m[0x0000])
                                                        r.a=self._shift(r.a,True,rotate=False)
                                                        self._y(r.a)
                                                        self._a(m[(0xB7AC+r.y)&65535])
                                                        m[0x0001]=r.a
                                                        self._a(m[(0xB7AD+r.y)&65535])
                                                        m[0x0002]=r.a
                                                        self._a(m[BACKGROUND])
                                                        self._compare(r.a,0x05)
                                                        self._mark(0xB72A)
                                                        if not r.p&Z:
                                                            pass
                                                        else:
                                                            self._a(0x00)
                                                            m[0x0001]=r.a
                                                            pass
                                                        self._a(m[0x0567])
                                                        m[0x0000]=r.a
                                                        m[0x0000]=self._nz(m[0x0000]+1)
                                                        self._y(0x00)
                                                        while True:  # natural loop $B73C
                                                            self._a(0x20)
                                                            self._compare(r.y,0x00)
                                                            self._mark(0xB740)
                                                            if r.p&Z:
                                                                pass
                                                            else:
                                                                self._a(0x23)
                                                                self._compare(r.y,m[0x0001])
                                                                self._mark(0xB747)
                                                                if not r.p&C:
                                                                    pass
                                                                else:
                                                                    self._a(0x22)
                                                                    self._compare(r.y,m[0x0002])
                                                                    self._mark(0xB74E)
                                                                    if not r.p&C:
                                                                        pass
                                                                    else:
                                                                        self._a(0x21)
                                                                        pass
                                                                    pass
                                                                pass
                                                            m[(0x05CD+r.y)&65535]=r.a
                                                            self._compare(r.a,0x22)
                                                            self._mark(0xB757)
                                                            if r.p&Z:
                                                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                                m[0x0003]=r.a
                                                                self._a(0x0F)
                                                                self._flag(C,True)
                                                                self._add(m[0x0003],subtract=True)
                                                                m[(0x058B+r.y)&65535]=r.a
                                                                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                                m[(0x05A1+r.y)&65535]=r.a
                                                                self._y(r.y+1)
                                                                self._compare(r.y,m[0x0000])
                                                                self._mark(0xB791)
                                                                if not r.p&C:
                                                                    continue
                                                                else:
                                                                    self._mark(0xB793)
                                                                    self._rts();return
                                                            else:
                                                                self._a(m[BACKGROUND])
                                                                self._compare(r.a,0x05)
                                                                self._mark(0xB75E)
                                                                if not r.p&Z:
                                                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                                    m[0x0003]=r.a
                                                                    self._a(0x0F)
                                                                    self._flag(C,True)
                                                                    self._add(m[0x0003],subtract=True)
                                                                    m[(0x058B+r.y)&65535]=r.a
                                                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                                    m[(0x05A1+r.y)&65535]=r.a
                                                                    self._y(r.y+1)
                                                                    self._compare(r.y,m[0x0000])
                                                                    self._mark(0xB791)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._mark(0xB793)
                                                                        self._rts();return
                                                                else:
                                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                                    m[0x0003]=r.a
                                                                    self._a(0x0F)
                                                                    self._flag(C,True)
                                                                    self._add(m[0x0003],subtract=True)
                                                                    m[(0x058B+r.y)&65535]=r.a
                                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                                    m[(0x05A1+r.y)&65535]=r.a
                                                                    self._y(r.y+1)
                                                                    self._compare(r.y,m[0x0000])
                                                                    self._mark(0xB777)
                                                                    if not r.p&C:
                                                                        continue
                                                                    else:
                                                                        self._mark(0xB779)
                                                                        self._rts();return
                                                pass
                                            pass
                                        self._a(0x04)
                                        self._y(m[BACKGROUND])
                                        self._compare(r.y,0x05)
                                        self._mark(0xB6C4)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._a(m[SECOND_FORMATION])
                                            self._a(r.a & 0x03)
                                            pass
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB794+r.y)&65535])
                                        m[0x000A]=r.a
                                        self._a(m[(0xB795+r.y)&65535])
                                        m[0x000B]=r.a
                                        self._a(m[(0xB7A0+r.y)&65535])
                                        m[0x000C]=r.a
                                        self._a(m[(0xB7A1+r.y)&65535])
                                        m[0x000D]=r.a
                                        self._a(m[(0xB796+r.y)&65535])
                                        m[0x001A]=r.a
                                        self._a(m[(0xB797+r.y)&65535])
                                        m[0x001B]=r.a
                                        self._a(m[(0xB7A2+r.y)&65535])
                                        m[0x001C]=r.a
                                        self._a(m[(0xB7A3+r.y)&65535])
                                        m[0x001D]=r.a
                                        self._y(0x00)
                                        self._a(self._pop())
                                        self._compare(r.a,0x50)
                                        self._mark(0xB702)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(r.y+1)
                                            self._compare(r.a,0x32)
                                            self._mark(0xB707)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._y(r.y+1)
                                                pass
                                            pass
                                        m[0x0000]=r.y
                                        self._a(self._pop())
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._a(r.a | m[0x0000])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB7AC+r.y)&65535])
                                        m[0x0001]=r.a
                                        self._a(m[(0xB7AD+r.y)&65535])
                                        m[0x0002]=r.a
                                        self._a(m[BACKGROUND])
                                        self._compare(r.a,0x05)
                                        self._mark(0xB72A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0001]=r.a
                                            pass
                                        self._a(m[0x0567])
                                        m[0x0000]=r.a
                                        m[0x0000]=self._nz(m[0x0000]+1)
                                        self._y(0x00)
                                        while True:  # natural loop $B73C
                                            self._a(0x20)
                                            self._compare(r.y,0x00)
                                            self._mark(0xB740)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(0x23)
                                                self._compare(r.y,m[0x0001])
                                                self._mark(0xB747)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x22)
                                                    self._compare(r.y,m[0x0002])
                                                    self._mark(0xB74E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x21)
                                                        pass
                                                    pass
                                                pass
                                            m[(0x05CD+r.y)&65535]=r.a
                                            self._compare(r.a,0x22)
                                            self._mark(0xB757)
                                            if r.p&Z:
                                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                m[0x0003]=r.a
                                                self._a(0x0F)
                                                self._flag(C,True)
                                                self._add(m[0x0003],subtract=True)
                                                m[(0x058B+r.y)&65535]=r.a
                                                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                m[(0x05A1+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,m[0x0000])
                                                self._mark(0xB791)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._mark(0xB793)
                                                    self._rts();return
                                            else:
                                                self._a(m[BACKGROUND])
                                                self._compare(r.a,0x05)
                                                self._mark(0xB75E)
                                                if not r.p&Z:
                                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB791)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB793)
                                                        self._rts();return
                                                else:
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB777)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB779)
                                                        self._rts();return
                        pass
                    pass
                self._a(m[FIRST_FORMATION])
                self._a(r.a & 0x03)
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xB794+r.y)&65535])
                m[0x000A]=r.a
                self._a(m[(0xB795+r.y)&65535])
                m[0x000B]=r.a
                self._a(m[(0xB7A0+r.y)&65535])
                m[0x000C]=r.a
                self._a(m[(0xB7A1+r.y)&65535])
                m[0x000D]=r.a
                self._y(0x00)
                self._a(self._pop())
                self._compare(r.a,0x50)
                self._mark(0xB5EE)
                if r.p&C:
                    pass
                else:
                    self._y(r.y+1)
                    self._compare(r.a,0x32)
                    self._mark(0xB5F3)
                    if r.p&C:
                        pass
                    else:
                        self._y(r.y+1)
                        pass
                    pass
                m[0x0000]=r.y
                self._a(self._pop())
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._a(r.a | m[0x0000])
                r.a=self._shift(r.a,True,rotate=False)
                self._y(r.a)
                self._a(m[(0xB7AC+r.y)&65535])
                m[0x0001]=r.a
                self._a(m[(0xB7AD+r.y)&65535])
                m[0x0002]=r.a
                self._a(m[0x0566])
                m[0x0000]=r.a
                m[0x0000]=self._nz(m[0x0000]+1)
                self._y(0x00)
                while True:  # natural loop $B61C
                    self._a(0x30)
                    self._compare(r.y,0x00)
                    self._mark(0xB620)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0x33)
                        self._compare(r.y,m[0x0001])
                        self._mark(0xB627)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x32)
                            self._compare(r.y,m[0x0002])
                            self._mark(0xB62E)
                            if not r.p&C:
                                pass
                            else:
                                self._a(0x31)
                                pass
                            pass
                        pass
                    m[(OBJECT_ENCODING+r.y)&65535]=r.a
                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                    m[(OBJECT_X+r.y)&65535]=r.a
                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                    m[(OBJECT_Y+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._compare(r.y,m[0x0000])
                    self._mark(0xB643)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(m[SECOND_OFFICER])
                    yield from self._external(0xB648,0xF2D7,0xB64B,"call",None)
                    if r.pc!=0xB64B:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x05B7]=r.a
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._push(r.a)
                    self._y(0x01)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._push(r.a)
                    self._y(0x09)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._push(r.a)
                    m[0x0002]=r.a
                    self._y(r.y-1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._push(r.a)
                    m[0x0001]=r.a
                    self._a(0x64)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    yield from self._external(0xB675,0xEA7C,0xB678,"call",None)
                    if r.pc!=0xB678:return  # preserve nonlocal stack return
                    self._a(m[0x0005])
                    self._mark(0xB67B)
                    if r.p&Z:
                        pass
                    else:
                        m[0x0001]=self._nz(m[0x0001]+1)
                        pass
                    self._a(m[0x0001])
                    m[0x0567]=r.a
                    m[0x0003]=r.a
                    self._a(self._pop())
                    m[0x0001]=r.a
                    self._a(self._pop())
                    m[0x0002]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    yield from self._external(0xB696,0xEA7C,0xB699,"call",None)
                    if r.pc!=0xB699:return  # preserve nonlocal stack return
                    self._y(0x00)
                    m[0x0001]=self._nz(m[0x0001]+1)
                    self._a(m[0x0001])
                    while True:  # natural loop $B6A1
                        self._compare(r.y,m[0x0005])
                        self._mark(0xB6A4)
                        if r.p&C:
                            self._flag(C,True)
                            self._add(0x01,subtract=True)
                            while True:  # natural loop $B6B4
                                m[(0x05B8+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._compare(r.y,m[0x0567])
                                self._mark(0xB6BB)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._a(0x04)
                                self._y(m[BACKGROUND])
                                self._compare(r.y,0x05)
                                self._mark(0xB6C4)
                                if r.p&Z:
                                    pass
                                else:
                                    self._a(m[SECOND_FORMATION])
                                    self._a(r.a & 0x03)
                                    pass
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB794+r.y)&65535])
                                m[0x000A]=r.a
                                self._a(m[(0xB795+r.y)&65535])
                                m[0x000B]=r.a
                                self._a(m[(0xB7A0+r.y)&65535])
                                m[0x000C]=r.a
                                self._a(m[(0xB7A1+r.y)&65535])
                                m[0x000D]=r.a
                                self._a(m[(0xB796+r.y)&65535])
                                m[0x001A]=r.a
                                self._a(m[(0xB797+r.y)&65535])
                                m[0x001B]=r.a
                                self._a(m[(0xB7A2+r.y)&65535])
                                m[0x001C]=r.a
                                self._a(m[(0xB7A3+r.y)&65535])
                                m[0x001D]=r.a
                                self._y(0x00)
                                self._a(self._pop())
                                self._compare(r.a,0x50)
                                self._mark(0xB702)
                                if r.p&C:
                                    pass
                                else:
                                    self._y(r.y+1)
                                    self._compare(r.a,0x32)
                                    self._mark(0xB707)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._y(r.y+1)
                                        pass
                                    pass
                                m[0x0000]=r.y
                                self._a(self._pop())
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                r.a=self._shift(r.a,True,rotate=False)
                                self._a(r.a | m[0x0000])
                                r.a=self._shift(r.a,True,rotate=False)
                                self._y(r.a)
                                self._a(m[(0xB7AC+r.y)&65535])
                                m[0x0001]=r.a
                                self._a(m[(0xB7AD+r.y)&65535])
                                m[0x0002]=r.a
                                self._a(m[BACKGROUND])
                                self._compare(r.a,0x05)
                                self._mark(0xB72A)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(0x00)
                                    m[0x0001]=r.a
                                    pass
                                self._a(m[0x0567])
                                m[0x0000]=r.a
                                m[0x0000]=self._nz(m[0x0000]+1)
                                self._y(0x00)
                                while True:  # natural loop $B73C
                                    self._a(0x20)
                                    self._compare(r.y,0x00)
                                    self._mark(0xB740)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(0x23)
                                        self._compare(r.y,m[0x0001])
                                        self._mark(0xB747)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._a(0x22)
                                            self._compare(r.y,m[0x0002])
                                            self._mark(0xB74E)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(0x21)
                                                pass
                                            pass
                                        pass
                                    m[(0x05CD+r.y)&65535]=r.a
                                    self._compare(r.a,0x22)
                                    self._mark(0xB757)
                                    if r.p&Z:
                                        self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                        m[0x0003]=r.a
                                        self._a(0x0F)
                                        self._flag(C,True)
                                        self._add(m[0x0003],subtract=True)
                                        m[(0x058B+r.y)&65535]=r.a
                                        self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                        m[(0x05A1+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,m[0x0000])
                                        self._mark(0xB791)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._mark(0xB793)
                                            self._rts();return
                                    else:
                                        self._a(m[BACKGROUND])
                                        self._compare(r.a,0x05)
                                        self._mark(0xB75E)
                                        if not r.p&Z:
                                            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                            m[0x0003]=r.a
                                            self._a(0x0F)
                                            self._flag(C,True)
                                            self._add(m[0x0003],subtract=True)
                                            m[(0x058B+r.y)&65535]=r.a
                                            self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                            m[(0x05A1+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,m[0x0000])
                                            self._mark(0xB791)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB793)
                                                self._rts();return
                                        else:
                                            self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                            m[0x0003]=r.a
                                            self._a(0x0F)
                                            self._flag(C,True)
                                            self._add(m[0x0003],subtract=True)
                                            m[(0x058B+r.y)&65535]=r.a
                                            self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                            m[(0x05A1+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._compare(r.y,m[0x0000])
                                            self._mark(0xB777)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._mark(0xB779)
                                                self._rts();return
                        else:
                            m[(0x05B8+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._compare(r.y,m[0x0567])
                            self._mark(0xB6AD)
                            if not r.p&C:
                                continue
                            else:
                                self._mark(0xB6AF)
                                if r.p&C:
                                    pass
                                else:
                                    self._flag(C,True)
                                    self._add(0x01,subtract=True)
                                    while True:  # natural loop $B6B4
                                        m[(0x05B8+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._compare(r.y,m[0x0567])
                                        self._mark(0xB6BB)
                                        if not r.p&C:
                                            continue
                                        else:
                                            pass
                                        self._a(0x04)
                                        self._y(m[BACKGROUND])
                                        self._compare(r.y,0x05)
                                        self._mark(0xB6C4)
                                        if r.p&Z:
                                            pass
                                        else:
                                            self._a(m[SECOND_FORMATION])
                                            self._a(r.a & 0x03)
                                            pass
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB794+r.y)&65535])
                                        m[0x000A]=r.a
                                        self._a(m[(0xB795+r.y)&65535])
                                        m[0x000B]=r.a
                                        self._a(m[(0xB7A0+r.y)&65535])
                                        m[0x000C]=r.a
                                        self._a(m[(0xB7A1+r.y)&65535])
                                        m[0x000D]=r.a
                                        self._a(m[(0xB796+r.y)&65535])
                                        m[0x001A]=r.a
                                        self._a(m[(0xB797+r.y)&65535])
                                        m[0x001B]=r.a
                                        self._a(m[(0xB7A2+r.y)&65535])
                                        m[0x001C]=r.a
                                        self._a(m[(0xB7A3+r.y)&65535])
                                        m[0x001D]=r.a
                                        self._y(0x00)
                                        self._a(self._pop())
                                        self._compare(r.a,0x50)
                                        self._mark(0xB702)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(r.y+1)
                                            self._compare(r.a,0x32)
                                            self._mark(0xB707)
                                            if r.p&C:
                                                pass
                                            else:
                                                self._y(r.y+1)
                                                pass
                                            pass
                                        m[0x0000]=r.y
                                        self._a(self._pop())
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,False,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._a(r.a | m[0x0000])
                                        r.a=self._shift(r.a,True,rotate=False)
                                        self._y(r.a)
                                        self._a(m[(0xB7AC+r.y)&65535])
                                        m[0x0001]=r.a
                                        self._a(m[(0xB7AD+r.y)&65535])
                                        m[0x0002]=r.a
                                        self._a(m[BACKGROUND])
                                        self._compare(r.a,0x05)
                                        self._mark(0xB72A)
                                        if not r.p&Z:
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[0x0001]=r.a
                                            pass
                                        self._a(m[0x0567])
                                        m[0x0000]=r.a
                                        m[0x0000]=self._nz(m[0x0000]+1)
                                        self._y(0x00)
                                        while True:  # natural loop $B73C
                                            self._a(0x20)
                                            self._compare(r.y,0x00)
                                            self._mark(0xB740)
                                            if r.p&Z:
                                                pass
                                            else:
                                                self._a(0x23)
                                                self._compare(r.y,m[0x0001])
                                                self._mark(0xB747)
                                                if not r.p&C:
                                                    pass
                                                else:
                                                    self._a(0x22)
                                                    self._compare(r.y,m[0x0002])
                                                    self._mark(0xB74E)
                                                    if not r.p&C:
                                                        pass
                                                    else:
                                                        self._a(0x21)
                                                        pass
                                                    pass
                                                pass
                                            m[(0x05CD+r.y)&65535]=r.a
                                            self._compare(r.a,0x22)
                                            self._mark(0xB757)
                                            if r.p&Z:
                                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                m[0x0003]=r.a
                                                self._a(0x0F)
                                                self._flag(C,True)
                                                self._add(m[0x0003],subtract=True)
                                                m[(0x058B+r.y)&65535]=r.a
                                                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                m[(0x05A1+r.y)&65535]=r.a
                                                self._y(r.y+1)
                                                self._compare(r.y,m[0x0000])
                                                self._mark(0xB791)
                                                if not r.p&C:
                                                    continue
                                                else:
                                                    self._mark(0xB793)
                                                    self._rts();return
                                            else:
                                                self._a(m[BACKGROUND])
                                                self._compare(r.a,0x05)
                                                self._mark(0xB75E)
                                                if not r.p&Z:
                                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB791)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB793)
                                                        self._rts();return
                                                else:
                                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                                    m[0x0003]=r.a
                                                    self._a(0x0F)
                                                    self._flag(C,True)
                                                    self._add(m[0x0003],subtract=True)
                                                    m[(0x058B+r.y)&65535]=r.a
                                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                                    m[(0x05A1+r.y)&65535]=r.a
                                                    self._y(r.y+1)
                                                    self._compare(r.y,m[0x0000])
                                                    self._mark(0xB777)
                                                    if not r.p&C:
                                                        continue
                                                    else:
                                                        self._mark(0xB779)
                                                        self._rts();return
                                pass
                            pass
                        self._a(0x04)
                        self._y(m[BACKGROUND])
                        self._compare(r.y,0x05)
                        self._mark(0xB6C4)
                        if r.p&Z:
                            pass
                        else:
                            self._a(m[SECOND_FORMATION])
                            self._a(r.a & 0x03)
                            pass
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(m[(0xB794+r.y)&65535])
                        m[0x000A]=r.a
                        self._a(m[(0xB795+r.y)&65535])
                        m[0x000B]=r.a
                        self._a(m[(0xB7A0+r.y)&65535])
                        m[0x000C]=r.a
                        self._a(m[(0xB7A1+r.y)&65535])
                        m[0x000D]=r.a
                        self._a(m[(0xB796+r.y)&65535])
                        m[0x001A]=r.a
                        self._a(m[(0xB797+r.y)&65535])
                        m[0x001B]=r.a
                        self._a(m[(0xB7A2+r.y)&65535])
                        m[0x001C]=r.a
                        self._a(m[(0xB7A3+r.y)&65535])
                        m[0x001D]=r.a
                        self._y(0x00)
                        self._a(self._pop())
                        self._compare(r.a,0x50)
                        self._mark(0xB702)
                        if r.p&C:
                            pass
                        else:
                            self._y(r.y+1)
                            self._compare(r.a,0x32)
                            self._mark(0xB707)
                            if r.p&C:
                                pass
                            else:
                                self._y(r.y+1)
                                pass
                            pass
                        m[0x0000]=r.y
                        self._a(self._pop())
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._a(r.a | m[0x0000])
                        r.a=self._shift(r.a,True,rotate=False)
                        self._y(r.a)
                        self._a(m[(0xB7AC+r.y)&65535])
                        m[0x0001]=r.a
                        self._a(m[(0xB7AD+r.y)&65535])
                        m[0x0002]=r.a
                        self._a(m[BACKGROUND])
                        self._compare(r.a,0x05)
                        self._mark(0xB72A)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x00)
                            m[0x0001]=r.a
                            pass
                        self._a(m[0x0567])
                        m[0x0000]=r.a
                        m[0x0000]=self._nz(m[0x0000]+1)
                        self._y(0x00)
                        while True:  # natural loop $B73C
                            self._a(0x20)
                            self._compare(r.y,0x00)
                            self._mark(0xB740)
                            if r.p&Z:
                                pass
                            else:
                                self._a(0x23)
                                self._compare(r.y,m[0x0001])
                                self._mark(0xB747)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x22)
                                    self._compare(r.y,m[0x0002])
                                    self._mark(0xB74E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._a(0x21)
                                        pass
                                    pass
                                pass
                            m[(0x05CD+r.y)&65535]=r.a
                            self._compare(r.a,0x22)
                            self._mark(0xB757)
                            if r.p&Z:
                                self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                m[0x0003]=r.a
                                self._a(0x0F)
                                self._flag(C,True)
                                self._add(m[0x0003],subtract=True)
                                m[(0x058B+r.y)&65535]=r.a
                                self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                m[(0x05A1+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._compare(r.y,m[0x0000])
                                self._mark(0xB791)
                                if not r.p&C:
                                    continue
                                else:
                                    self._mark(0xB793)
                                    self._rts();return
                            else:
                                self._a(m[BACKGROUND])
                                self._compare(r.a,0x05)
                                self._mark(0xB75E)
                                if not r.p&Z:
                                    self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
                                    m[0x0003]=r.a
                                    self._a(0x0F)
                                    self._flag(C,True)
                                    self._add(m[0x0003],subtract=True)
                                    m[(0x058B+r.y)&65535]=r.a
                                    self._a(m[((m[0x0C]|m[0x0D]<<8)+r.y)&65535])
                                    m[(0x05A1+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0000])
                                    self._mark(0xB791)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._mark(0xB793)
                                        self._rts();return
                                else:
                                    self._a(m[((m[0x1A]|m[0x1B]<<8)+r.y)&65535])
                                    m[0x0003]=r.a
                                    self._a(0x0F)
                                    self._flag(C,True)
                                    self._add(m[0x0003],subtract=True)
                                    m[(0x058B+r.y)&65535]=r.a
                                    self._a(m[((m[0x1C]|m[0x1D]<<8)+r.y)&65535])
                                    m[(0x05A1+r.y)&65535]=r.a
                                    self._y(r.y+1)
                                    self._compare(r.y,m[0x0000])
                                    self._mark(0xB777)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._mark(0xB779)
                                        self._rts();return

    def text_readiness(self):
        """Original entry $B870; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB870)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xB875)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xB881)
            self._rts();return
        else:
            self._a(m[0x0300])
            self._compare(r.a,0xFF)
            self._mark(0xB87C)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xB881)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xB87F)
                self._rts();return

    def build_object_nametable_packet(self):
        """Original entry $B882; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB882)
        self._y(m[0x0013])
        self._a(m[(OBJECT_X+r.y)&65535])
        m[0x0010]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535])
        m[0x0011]=r.a
        self._a(m[BACKGROUND])
        self._push(r.a)
        self._push(r.a)
        self._y(r.a)
        self._a(m[(0xBB48+r.y)&65535])
        self._y(r.a)
        yield from self._external(0xB89B,0xF25F,0xB89E,"call",None)
        if r.pc!=0xB89E:return  # preserve nonlocal stack return
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBB1E+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xBB1F+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[(0xBB2C+r.y)&65535])
        m[0x0002]=r.a
        self._a(m[(0xBB2D+r.y)&65535])
        m[0x0003]=r.a
        self._a(m[0x0010])
        m[0x0008]=r.a
        self._x(0x00)
        self._a(m[0x0011])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._push(r.a)
        self._a(r.a | m[0x0010])
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
        m[0x0391]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
        m[0x0384]=r.a
        m[0x0392]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
        m[0x0388]=r.a
        m[0x0396]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
        m[0x0389]=r.a
        m[0x0397]=r.a
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
        m[0x0390]=r.a
        self._a(m[0x000B])
        self._a(r.a | 0x20)
        m[0x0381]=r.a
        self._a(r.a | 0x04)
        m[0x038F]=r.a
        self._a(m[0x0382])
        self._flag(C,False)
        self._add(0x20)
        m[0x0387]=r.a
        m[0x0395]=r.a
        self._a(m[0x0381])
        self._add(0x00)
        m[0x0386]=r.a
        self._a(r.a | 0x04)
        m[0x0394]=r.a
        self._a(0x02)
        m[0x0380]=r.a
        m[0x0385]=r.a
        m[0x038E]=r.a
        m[0x0393]=r.a
        self._a(m[0x0012])
        self._mark(0xB963)
        if r.p&Z:
            pass
        else:
            self._y(m[0x0013])
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0x03)
            m[0x0000]=r.a
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0xF0)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._a(r.a | m[0x0000])
            self._compare(r.a,0x10)
            self._mark(0xB97C)
            if not r.p&C:
                pass
            else:
                pass  # original deliberate no-op
                pass
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0xBB4F+r.y)&65535])
            m[0x0383]=r.a
            m[0x0391]=r.a
            self._a(m[(0xBB50+r.y)&65535])
            m[0x0384]=r.a
            m[0x0392]=r.a
            self._a(m[(0xBB51+r.y)&65535])
            m[0x0388]=r.a
            m[0x0396]=r.a
            self._a(m[(0xBB52+r.y)&65535])
            m[0x0389]=r.a
            m[0x0397]=r.a
            self._push(0xB9);self._push(0xA8)
            yield from self.insert_object_nametable_overlay()
            if r.pc!=0xB9A9:return  # preserve nonlocal stack return
            pass
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBB3A+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xBB3B+r.y)&65535])
        m[0x0001]=r.a
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
        m[0x0000]=r.a
        self._push(0xB9);self._push(0xD3)
        yield from self.prepare_object_packet_colors()
        if r.pc!=0xB9D4:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x038D]=r.a
        m[0x039B]=r.a
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
        m[0x039A]=r.a
        self._a(0x23)
        m[0x038B]=r.a
        self._a(0x27)
        m[0x0399]=r.a
        self._a(0x01)
        m[0x038A]=r.a
        m[0x0398]=r.a
        self._a(0xFF)
        m[0x039C]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x04)
        m[PPU_JOBS]=r.a
        self._mark(0xBA17)
        self._rts();return

    def insert_object_nametable_overlay(self):
        """Original entry $BA18; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA18)
        self._y(m[0x0013])
        self._a(m[(OBJECT_VALUE+r.y)&65535])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        m[0x0003]=r.a
        yield from self._external(0xBA29,0xE9BA,0xBA2C,"call",None)
        if r.pc!=0xBA2C:return  # preserve nonlocal stack return
        self._a(m[0x0007])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._flag(C,False)
        self._add(0xB4)
        m[0x0396]=r.a
        self._a(m[0x0007])
        self._a(r.a & 0x0F)
        self._flag(C,False)
        self._add(0xB4)
        m[0x0397]=r.a
        self._a(m[0x0008])
        self._a(r.a & 0x0F)
        self._mark(0xBA49)
        if r.p&Z:
            pass
        else:
            self._a(0xBE)
            m[0x0396]=r.a
            self._a(0xBF)
            m[0x0397]=r.a
            pass
        self._mark(0xBA55)
        self._rts();return

    def prepare_object_packet_colors(self):
        """Original entry $BA56; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA56)
        self._a(m[0x0010])
        self._a(r.a & 0x0E)
        m[0x0002]=r.a
        self._a(m[0x0011])
        self._a(r.a & 0x0E)
        m[0x0003]=r.a
        self._y(0x15)
        while True:  # natural loop $BA68
            self._a(m[0x0012])
            self._mark(0xBA6B)
            if not r.p&Z:
                self._push(0xBA);self._push(0x74)
                yield from self.build_object_attribute_packet()
                if r.pc!=0xBA75:return  # preserve nonlocal stack return
                pass
            else:
                self._compare(r.y,m[0x0013])
                self._mark(0xBA70)
                if r.p&Z:
                    pass
                else:
                    self._push(0xBA);self._push(0x74)
                    yield from self.build_object_attribute_packet()
                    if r.pc!=0xBA75:return  # preserve nonlocal stack return
                    pass
                pass
            self._y(r.y-1)
            self._mark(0xBA76)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xBA78)
            self._rts();return

    def build_object_attribute_packet(self):
        """Original entry $BA79; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA79)
        self._a(0x01)
        m[0x000A]=r.a
        self._a(0x04)
        m[0x000B]=r.a
        self._a(0x10)
        m[0x000C]=r.a
        self._a(0x40)
        m[0x000D]=r.a
        self._compare(r.y,0x0B)
        self._mark(0xBA8F)
        if r.p&C:
            pass
        else:
            self._a(0x03)
            m[0x000A]=r.a
            self._a(0x0C)
            m[0x000B]=r.a
            self._a(0x30)
            m[0x000C]=r.a
            self._a(0xC0)
            m[0x000D]=r.a
            pass
        self._a(m[0x0002])
        self._compare(r.a,m[(OBJECT_X+r.y)&65535])
        self._mark(0xBAAB)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0003])
            self._compare(r.a,m[(OBJECT_Y+r.y)&65535])
            self._mark(0xBAB3)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0xFC)
                self._a(r.a | m[0x000A])
                m[0x0000]=r.a
                pass
            pass
        m[0x0002]=self._nz(m[0x0002]+1)
        self._a(m[0x0002])
        self._compare(r.a,m[(OBJECT_X+r.y)&65535])
        self._mark(0xBAC9)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0003])
            self._compare(r.a,m[(OBJECT_Y+r.y)&65535])
            self._mark(0xBAD1)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0xF3)
                self._a(r.a | m[0x000B])
                m[0x0000]=r.a
                pass
            pass
        m[0x0003]=self._nz(m[0x0003]+1)
        self._a(m[0x0002])
        self._compare(r.a,m[(OBJECT_X+r.y)&65535])
        self._mark(0xBAE7)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0003])
            self._compare(r.a,m[(OBJECT_Y+r.y)&65535])
            self._mark(0xBAEF)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0x3F)
                self._a(r.a | m[0x000D])
                m[0x0000]=r.a
                pass
            pass
        m[0x0002]=self._nz(m[0x0002]-1)
        self._a(m[0x0002])
        self._compare(r.a,m[(OBJECT_X+r.y)&65535])
        self._mark(0xBB05)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0003])
            self._compare(r.a,m[(OBJECT_Y+r.y)&65535])
            self._mark(0xBB0D)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0xCF)
                self._a(r.a | m[0x000C])
                m[0x0000]=r.a
                pass
            pass
        m[0x0003]=self._nz(m[0x0003]-1)
        self._mark(0xBB1D)
        self._rts();return

    def initialize_attack_background(self):
        """Original entry $BB8F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB8F)
        self._a(m[0x005E])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x03)
        m[0x0001]=r.a
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        self._a(r.a & 0x03)
        m[0x0000]=r.a
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        self._a(r.a & 0xF0)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a | m[0x0000])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0001])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBBFD+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xBBFE+r.y)&65535])
        m[0x0001]=r.a
        self._a(m[0x054A])
        self._flag(C,False)
        self._add(0x08)
        m[0x000C]=r.a
        self._a(m[SAVED_STATE])
        m[0x000A]=r.a
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._compare(r.a,0x03)
        self._mark(0xBBE9)
        if not r.p&Z:
            pass
        else:
            self._a(0x40)
            m[0x0002]=r.a
            pass
        self._y(m[OBJECT_INDEX])
        self._compare(r.y,0x0B)
        self._mark(0xBBF5)
        if r.p&C:
            pass
        else:
            m[0x0002]=self._nz(m[0x0002]+1)
            pass
        self._mark(0xBBFA)
        yield from self._external(0xBBFA,0xF092,None,"tail")
        return

    def build_initial_nametable_rows(self):
        """Original entry $BE15; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE15)
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_X+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x000C]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        m[0x000A]=r.a
        self._a(0x65)
        m[0x0000]=r.a
        self._a(0xBE)
        m[0x0001]=r.a
        self._y(m[ACTIVE_SIDE])
        self._a(m[0x000C])
        self._flag(C,False)
        self._add(m[(0xBE5D+r.y)&65535])
        m[0x000C]=r.a
        self._a(m[0x000A])
        self._flag(C,False)
        self._add(m[(0xBE61+r.y)&65535])
        m[0x000A]=r.a
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xBE5A)
        yield from self._external(0xBE5A,0xF092,None,"tail")
        return

    def build_initial_attribute_rows(self):
        """Original entry $BE76; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE76)
        self._a(m[OBJECT_INDEX])
        self._compare(r.a,0x0B)
        self._mark(0xBE7B)
        if not r.p&C:
            self._a(m[0x0577])
            self._a(r.a & 0x0F)
            self._mark(0xBE92)
            if r.p&Z:
                self._a(m[ACTIVE_SIDE])
                pass
            else:
                self._a(m[ACTIVE_SIDE])
                self._flag(C,False)
                self._add(0x04)
                pass
            pass
        else:
            self._a(m[0x0577])
            self._a(r.a & 0xF0)
            self._mark(0xBE82)
            if r.p&Z:
                self._a(m[ACTIVE_SIDE])
                pass
            else:
                self._a(m[ACTIVE_SIDE])
                self._flag(C,False)
                self._add(0x04)
                pass
            pass
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBEDD+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xBEDE+r.y)&65535])
        m[0x0001]=r.a
        self._y(m[ACTIVE_SIDE])
        self._a(m[0x054A])
        self._flag(C,False)
        self._add(m[(0xBED5+r.y)&65535])
        m[0x000C]=r.a
        self._a(m[SAVED_STATE])
        self._flag(C,False)
        self._add(m[(0xBED9+r.y)&65535])
        m[0x000A]=r.a
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xBED2)
        yield from self._external(0xBED2,0xF092,None,"tail")
        return

    def flush_attack_background(self):
        """Original entry $BF15; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF15)
        self._a(0x3B)
        m[0x0000]=r.a
        self._a(0xBF)
        m[0x0001]=r.a
        self._a(m[0x054A])
        m[0x000C]=r.a
        self._a(m[SAVED_STATE])
        m[0x000A]=r.a
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xBF38)
        yield from self._external(0xBF38,0xF092,None,"tail")
        return

    def draw_attack_scene_objects(self):
        """Original entry $BF4C; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF4C)
        self._y(0x00)
        self._a(m[0x0574])
        self._x(0x80)
        self._push(0xBF);self._push(0x55)
        yield from self.object_position_to_world()
        if r.pc!=0xBF56:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[0x0574])
        self._x(0x70)
        self._push(0xBF);self._push(0x5F)
        yield from self.object_position_to_world_saved()
        if r.pc!=0xBF60:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[0x0575])
        self._x(0x80)
        self._push(0xBF);self._push(0x69)
        yield from self.object_position_to_world()
        if r.pc!=0xBF6A:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[0x0575])
        self._x(0x70)
        self._push(0xBF);self._push(0x73)
        yield from self.object_position_to_world_saved()
        if r.pc!=0xBF74:return  # preserve nonlocal stack return
        self._y(0x04)
        self._a(m[0x0576])
        self._x(0x80)
        self._push(0xBF);self._push(0x7D)
        yield from self.object_position_to_world()
        if r.pc!=0xBF7E:return  # preserve nonlocal stack return
        self._y(0x04)
        self._a(m[0x0576])
        self._x(0x70)
        self._push(0xBF);self._push(0x87)
        yield from self.object_position_to_world_saved()
        if r.pc!=0xBF88:return  # preserve nonlocal stack return
        self._y(0x06)
        self._a(m[0x0577])
        self._x(0x80)
        self._push(0xBF);self._push(0x91)
        yield from self.object_position_to_world()
        if r.pc!=0xBF92:return  # preserve nonlocal stack return
        self._y(0x06)
        self._a(m[0x0577])
        self._x(0x70)
        self._push(0xBF);self._push(0x9B)
        yield from self.object_position_to_world_saved()
        if r.pc!=0xBF9C:return  # preserve nonlocal stack return
        self._mark(0xBF9C)
        self._rts();return

    def object_position_to_world(self):
        """Original entry $BF9D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF9D)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        return (yield from self.object_position_to_world_saved())

    def object_position_to_world_saved(self):
        """Original entry $BFA1; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFA1)
        self._a(r.a & 0x0F)
        self._mark(0xBFA3)
        if r.p&Z:
            pass
        else:
            m[0x000C]=r.x
            self._a(m[(0xBFCF+r.y)&65535])
            m[0x0000]=r.a
            self._a(m[(0xBFD0+r.y)&65535])
            m[0x0001]=r.a
            self._a(0xD0)
            m[0x000A]=r.a
            self._a(0x00)
            m[0x000B]=r.a
            m[0x000D]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            yield from self._external(0xBFC6,0xF092,0xBFC9,"call",None)
            if r.pc!=0xBFC9:return  # preserve nonlocal stack return
            self._a(0x91)
            m[0x00B7]=r.a
            pass
        self._mark(0xBFCE)
        self._rts();return

    def animate_background_CHR(self):
        """Original entry $C01B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC01B)
        self._a(m[0x005E])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x03)
        self._y(r.a)
        self._a(m[BACKGROUND])
        self._compare(r.a,0x03)
        self._mark(0xC029)
        if not r.p&Z:
            pass
        else:
            self._y(r.y+1)
            self._y(r.y+1)
            self._y(r.y+1)
            self._y(r.y+1)
            pass
        self._a(m[(0xC054+r.y)&65535])
        m[0x00B3]=r.a
        m[0x00C3]=r.a
        m[0x00CB]=r.a
        m[0x00D3]=r.a
        m[0x00DB]=r.a
        self._a(m[(0xC05C+r.y)&65535])
        m[0x00B5]=r.a
        m[0x00C5]=r.a
        m[0x00CD]=r.a
        m[0x00D5]=r.a
        m[0x00DD]=r.a
        self._mark(0xC053)
        self._rts();return

    def choose_object_axis_direction(self):
        """C064..C1CC: two-axis object direction choice with one fallback.

        The object class chooses horizontal/vertical priority from the byte
        distances. Only the other axis is tried after a rejected probe; the
        original 0012 retry byte, zero-distance RNG and signed-byte quirks
        remain observable. This is not a general path search.
        """
        r=self.registers;m=self.memory
        self._mark(0xC064)
        self._a(0);m[0x12]=r.a
        self._a(m[OBJECT_ACTION]);self._compare(r.a,1)
        if r.p&Z:
            self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
            if r.p&C:
                self._a(32);m[0x10]=r.a;self._a(m[OBJECT_Y]);m[0x11]=r.a
            else:
                self._a(255);m[0x10]=r.a;self._a(m[OBJECT_Y+11]);m[0x11]=r.a
        else:
            self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
            if r.p&C:
                self._a(m[OBJECT_X]);m[0x10]=r.a;self._a(m[OBJECT_Y]);m[0x11]=r.a
            else:
                self._a(m[OBJECT_X+11]);m[0x10]=r.a;self._a(m[OBJECT_Y+11]);m[0x11]=r.a
        self._a(m[(OBJECT_X+r.y)&65535]);self._flag(C,True);self._add(m[0x10],subtract=True);m[0x10]=r.a
        if not r.p&C:self._a(r.a^255);self._flag(C,False);self._add(1)
        m[0]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535]);self._flag(C,True);self._add(m[0x11],subtract=True);m[0x11]=r.a
        if not r.p&C:self._a(r.a^255);self._flag(C,False);self._add(1)
        m[1]=r.a
        self._a(m[(OBJECT_ENCODING+r.y)&65535]);self._a(r.a&15)
        if r.p&Z:
            compare_axes=True
        else:
            self._compare(r.a,3)
            if r.p&Z:compare_axes=True
            else:
                compare_axes=False;self._compare(r.a,2)
                if r.p&Z:
                    self._a(m[1]);self._compare(r.a,2);horizontal=not bool(r.p&C)
                else:
                    self._a(m[0]);self._compare(r.a,2);horizontal=bool(r.p&C)
        if compare_axes:
            self._a(m[1]);self._compare(r.a,m[0])
            if r.p&Z:
                yield from self._external(0xC116,0xE87A,0xC119,'call')
                self._a(r.a&1);horizontal=bool(r.p&Z)
            else:horizontal=not bool(r.p&C)
        while True:
            self._mark(0xC123 if horizontal else 0xC178)
            self._a(m[0x10 if horizontal else 0x11])
            if r.p&Z:
                call_pc=0xC12C if horizontal else 0xC181
                yield from self._external(call_pc,0xE87A,call_pc+3,'call')
                self._a(r.a&128);positive=not bool(r.p&Z)
            else:positive=bool(r.p&N)
            self._a(1 if horizontal and positive else 255 if horizontal else 0);m[0]=r.a
            self._a(0 if horizontal else 1 if positive else 255);m[1]=r.a
            probe_pc=(0xC157 if positive else 0xC13D)if horizontal else(0xC1AC if positive else 0xC192)
            self._push((probe_pc+2)>>8);self._push(probe_pc+2)
            yield from self.probe_shifted_object_position()
            if r.pc!=probe_pc+3:return
            if r.p&C:
                parameter_pc=(0xC15C if positive else 0xC142)if horizontal else(0xC1B1 if positive else 0xC197)
                self._push((parameter_pc+2)>>8);self._push(parameter_pc+2)
                yield from self.read_object_terrain_with_affinity()
                if r.pc!=parameter_pc+3:return
                accepted=bool(r.p&Z)
            else:accepted=False
            if accepted:
                self._a((3 if positive else 2)if horizontal else(1 if positive else 0));m[ACTIVE_SIDE]=r.a
                self._rts();return
            self._a(m[0x12])
            if not r.p&Z:
                self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
            m[0x12]=self._nz(m[0x12]+1)
            horizontal=not horizontal

    def probe_shifted_object_position(self):
        """Original entry $C1CD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1CD)
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_X+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0000])
        m[0x0000]=r.a
        self._compare(r.a,0x10)
        self._mark(0xC1DC)
        if r.p&C:
            self._a(0x00)
            self._flag(C,False)
            self._mark(0xC209)
            self._rts();return
        else:
            self._a(m[(OBJECT_Y+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0001])
            m[0x0001]=r.a
            self._compare(r.a,0x0A)
            self._mark(0xC1EA)
            if r.p&C:
                self._a(0x00)
                self._flag(C,False)
                self._mark(0xC209)
                self._rts();return
            else:
                self._x(0x15)
                while True:  # natural loop $C1EE
                    self._a(m[(OBJECT_X+r.x)&65535])
                    self._compare(r.a,m[0x0000])
                    self._mark(0xC1F4)
                    if not r.p&Z:
                        self._x(r.x-1)
                        self._mark(0xC20B)
                        if not r.p&N:
                            continue
                        else:
                            self._flag(C,True)
                            self._mark(0xC20E)
                            self._rts();return
                    else:
                        self._a(m[(OBJECT_Y+r.x)&65535])
                        self._compare(r.a,m[0x0001])
                        self._mark(0xC1FC)
                        if not r.p&Z:
                            self._x(r.x-1)
                            self._mark(0xC20B)
                            if not r.p&N:
                                continue
                            else:
                                self._flag(C,True)
                                self._mark(0xC20E)
                                self._rts();return
                        else:
                            self._a(m[OBJECT_INDEX])
                            self._push(0xC2);self._push(0x03)
                            yield from self.classify_object_collision()
                            if r.pc!=0xC204:return  # preserve nonlocal stack return
                            self._flag(C,False)
                            self._mark(0xC205)
                            self._rts();return

    def choose_shifted_object_destination(self):
        """C20F..C30E: randomized four-neighbor occupied-object probe.

        Randomly choose an axis and its initial sign. Try that sign, its
        opposite, then the two signs on the other axis; only the axis switch
        draws another sign. A clear-carry nonzero collision code is accepted.
        """
        r=self.registers;m=self.memory
        self._mark(0xC20F);self._a(0);m[0x10]=m[0x11]=r.a
        yield from self._external(0xC217,0xE87A,0xC21A,'call')
        self._a(r.a&1);horizontal=bool(r.p&Z);choose_sign=True
        while True:
            self._mark(0xC221 if horizontal else 0xC298)
            if choose_sign:
                sign_pc=0xC221 if horizontal else 0xC298
                yield from self._external(sign_pc,0xE87A,sign_pc+3,'call')
                self._a(r.a&128);positive=not bool(r.p&Z)
            self._a(1 if horizontal and positive else 255 if horizontal else 0);m[0]=r.a
            self._a(0 if horizontal else 1 if positive else 255);m[1]=r.a
            probe_pc=(0xC26A if positive else 0xC232)if horizontal else(0xC2E1 if positive else 0xC2A9)
            self._push((probe_pc+2)>>8);self._push(probe_pc+2)
            yield from self.probe_shifted_object_position()
            if r.pc!=probe_pc+3:return
            if not r.p&C:
                self._y(r.a)
                if not r.p&Z:
                    m[0x54A]=r.x;self._a((3 if positive else 2)if horizontal else(1 if positive else 0))
                    m[ACTIVE_SIDE]=r.a;self._rts();return
            self._a(m[0x10]);self._compare(r.a,3)
            if r.p&Z:
                self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
            self._compare(r.a,1);switch_axis=bool(r.p&Z)
            m[0x10]=self._nz(m[0x10]+1)
            if switch_axis:
                horizontal=not horizontal;choose_sign=True
            else:
                positive=not positive;choose_sign=False

    def search_axis_object_target(self):
        """C30F..C826: randomized axis rays, two-to-six cell target search.

        A nearer occupied cell or terrain blocks that ray. Distance5/6 needs
        the selected side's 0575 nibble. The negative horizontal failure
        re-enters its own failure test instead of probing the opposite sign;
        this original asymmetry is retained, not normalized to four rays.
        """
        r=self.registers;m=self.memory
        self._mark(0xC30F);self._a(0);m[0x10]=m[0x11]=r.a
        yield from self._external(0xC317,0xE87A,0xC31A,'call')
        self._a(r.a&1);horizontal=bool(r.p&Z);choose_sign=True
        while True:
            self._mark(0xC321 if horizontal else 0xC5A4)
            if choose_sign:
                sign_pc=0xC321 if horizontal else 0xC5A4
                yield from self._external(sign_pc,0xE87A,sign_pc+3,'call')
                self._a(r.a&128);positive=bool(r.p&Z)
            if horizontal:
                terrain_calls=(0xC473,0xC49B,0xC4C5,0xC4EF,0xC534,0xC55E)if positive else(0xC335,0xC35D,0xC387,0xC3B1,0xC3F6,0xC420)
            else:
                terrain_calls=(0xC6F6,0xC71E,0xC748,0xC772,0xC7B7,0xC7E1)if positive else(0xC5B8,0xC5E0,0xC60A,0xC634,0xC679,0xC6A3)
            for distance in range(1,7):
                if distance==5:
                    self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
                    second=bool(r.p&C);self._a(m[0x575]);self._a(r.a&(240 if second else 15))
                    if r.p&Z:break
                delta=distance if positive else(-distance)&255
                self._a(delta if horizontal else 0);m[0]=r.a
                self._a(0 if horizontal else delta);m[1]=r.a
                terrain_pc=terrain_calls[distance-1]
                self._push((terrain_pc+2)>>8);self._push(terrain_pc+2)
                yield from self.probe_shifted_object_terrain()
                if r.pc!=terrain_pc+3:return
                self._y(r.a)
                if not r.p&Z:break
                self._a(delta if horizontal else 0);m[0]=r.a
                self._a(0 if horizontal else delta);m[1]=r.a
                probe_pc=terrain_pc+0x13
                self._push((probe_pc+2)>>8);self._push(probe_pc+2)
                yield from self.probe_shifted_object_position()
                if r.pc!=probe_pc+3:return
                if not r.p&C:
                    self._y(r.a)
                    if not r.p&Z:
                        if distance==1:break
                        self._a((distance-1)*16+12);m[0x54D]=r.x;m[SCAN_CURSOR]=r.a
                        self._a((3 if positive else 2)if horizontal else(1 if positive else 0));m[ACTIVE_SIDE]=r.a
                        self._rts();return
            while True:
                self._a(m[0x10]);self._compare(r.a,3)
                if r.p&Z:self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
                self._compare(r.a,1);switch_axis=bool(r.p&Z)
                m[0x10]=self._nz(m[0x10]+1)
                if switch_axis:
                    horizontal=not horizontal;choose_sign=True;break
                if horizontal and not positive:
                    continue  # C466 JMP C44C, including the skipped +X ray
                positive=not positive;choose_sign=False;break

    def classify_object_collision(self):
        """Original entry $C827; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC827)
        self._compare(r.x,0x0B)
        self._mark(0xC829)
        if r.p&C:
            self._compare(r.a,0x0B)
            self._mark(0xC834)
            if r.p&C:
                self._a(0x00)
                self._mark(0xC831)
                self._rts();return
            else:
                self._a(0x01)
                self._mark(0xC838)
                self._rts();return
        else:
            self._compare(r.a,0x0B)
            self._mark(0xC82D)
            if r.p&C:
                self._a(0x01)
                self._mark(0xC838)
                self._rts();return
            else:
                self._a(0x00)
                self._mark(0xC831)
                self._rts();return

    def check_object_side(self):
        """Original entry $C839; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC839)
        self._a(m[0x0000])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xC8BC+r.y)&65535])
        m[0x0381]=r.a
        self._a(m[(0xC8BB+r.y)&65535])
        m[0x0382]=r.a
        self._a(m[(0xC8BE+r.y)&65535])
        m[0x0389]=r.a
        self._a(m[(0xC8BD+r.y)&65535])
        m[0x038A]=r.a
        self._a(m[0x0001])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0001])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xC8CB+r.y)&65535])
        m[0x0383]=r.a
        self._a(m[(0xC8CC+r.y)&65535])
        m[0x0384]=r.a
        self._a(m[(0xC8CD+r.y)&65535])
        m[0x0385]=r.a
        self._a(m[(0xC8CE+r.y)&65535])
        m[0x0386]=r.a
        self._a(m[(0xC8CF+r.y)&65535])
        m[0x0387]=r.a
        self._a(m[(0xC8D0+r.y)&65535])
        m[0x038B]=r.a
        self._a(m[(0xC8D1+r.y)&65535])
        m[0x038C]=r.a
        self._a(m[(0xC8D2+r.y)&65535])
        m[0x038D]=r.a
        self._a(m[(0xC8D3+r.y)&65535])
        m[0x038E]=r.a
        self._a(m[(0xC8D4+r.y)&65535])
        m[0x038F]=r.a
        self._a(0x05)
        m[0x0380]=r.a
        self._a(0x05)
        m[0x0388]=r.a
        self._a(0xFF)
        m[0x0390]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x04)
        m[PPU_JOBS]=r.a
        self._a(0x77)
        m[0x00BB]=r.a
        self._mark(0xC8BA)
        self._rts();return

    def draw_formation_selection_result(self):
        """Original entry $C8FD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC8FD)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xC902)
        if not r.p&Z:
            self._mark(0xC920)
            self._rts();return
        else:
            self._a(0xD8)
            m[0x000A]=r.a
            self._a(0xA0)
            m[0x000C]=r.a
            self._a(0x21)
            m[0x0000]=r.a
            self._a(0xC9)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._mark(0xC91D)
            yield from self._external(0xC91D,0xF1AD,None,"tail")
            return

    def prepare_participant_statistics(self):
        """C926..C990: derive each participant's martial/equipment/IQ fields.

        056A/B and04C1/2 hold the derived attack parameter,056E/F the armor
        correction,0570/1 the weapon correction,0572/3 floor(IQ/13). The real
        officer pointer and arithmetic services keep their calling conventions.
        """
        r=self.registers;m=self.memory
        self._mark(0xC926)
        for side,pointer_pc,parameter_pc,IQ_pointer_pc,division_pc in ((0,0xC929,0xC92C,0xC93E,0xC952),(1,0xC95E,0xC961,0xC973,0xC987)):
            self._a(m[FIRST_OFFICER+side])
            yield from self._external(pointer_pc,0xF2D7,pointer_pc+3,'call')
            self._push((parameter_pc+2)>>8);self._push(parameter_pc+2)
            yield from self.compute_combat_equipment_parameters()
            if r.pc!=parameter_pc+3:return
            m[0x56A+side]=m[0x4C1+side]=r.a;m[0x570+side]=r.y;m[0x56E+side]=r.x
            self._a(m[FIRST_OFFICER+side])
            yield from self._external(IQ_pointer_pc,0xF2D7,IQ_pointer_pc+3,'call')
            self._y(2);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0]=r.a
            self._a(0);m[1]=r.a;self._a(13);m[3]=r.a
            yield from self._external(division_pc,0xEBCA,division_pc+3,'call')
            self._a(m[0]);m[0x572+side]=r.a
        self._rts();return

    def compute_combat_equipment_parameters(self):
        """C991..CA1E: martial coefficient, RNG bias and equipment corrections.

        Preserve the duplicate45 coefficient at both <50 and <65. RNG accepts
        only low-nibble0..8; rejected values consume the real permutation cursor.
        Weapon and armor are the original packed record byte10, not troop type.
        """
        r=self.registers;m=self.memory
        self._mark(0xC991);self._y(10);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._push(r.a)
        self._y(1);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
        for threshold,coefficient in ((50,45),(65,45),(80,50),(87,55),(92,60),(97,65)):
            self._y(coefficient);self._compare(r.a,threshold)
            if not r.p&C:break
        else:self._y(70)
        m[3]=r.y;m[0]=r.a;self._a(0);m[1]=m[2]=r.a
        yield from self._external(0xC9CE,0xEBE9,0xC9D1,'call')
        self._a(m[6]);m[1]=r.a;self._a(m[7]);m[2]=r.a
        self._a(100);m[3]=r.a;self._a(0);m[4]=r.a
        yield from self._external(0xC9E7,0xEA7C,0xC9EA,'call')
        while True:
            yield from self._external(0xC9EA,0xE87A,0xC9ED,'call')
            self._a(r.a&15);self._compare(r.a,9)
            if not r.p&C:break
        m[2]=r.a;self._a(m[1]);self._flag(C,False);self._add(9)
        self._flag(C,True);self._add(m[2],subtract=True)
        if not r.p&C:self._a(1)
        m[1]=r.a;self._a(self._pop());self._push(r.a)
        self._a(r.a&31);self._y(r.a);self._a(m[0xCA1F+r.y]);self._y(r.a)
        self._a(self._pop())
        for _ in range(5):r.a=self._shift(r.a,False)
        self._x(r.a);self._a(m[0xCA37+r.x]);self._x(r.a);self._a(m[1])
        self._rts();return

    def write_attack_results_to_battle(self):
        """Original entry $CA3F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA3F)
        self._a(m[FIRST_OFFICER])
        yield from self._external(0xCA42,0xF2D7,0xCA45,"call",None)
        if r.pc!=0xCA45:return  # preserve nonlocal stack return
        self._a(m[OBJECT_VALUE])
        self._y(0x00)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x00)
        m[0x0002]=r.y
        m[0x0003]=r.y
        while True:  # natural loop $CA54
            self._a(m[(0x05AD+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xCA59)
            if r.p&Z:
                pass
            else:
                self._a(m[(0x05AD+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0002])
                m[0x0002]=r.a
                self._a(m[0x0003])
                self._add(0x00)
                m[0x0003]=r.a
                pass
            self._y(r.y+1)
            self._compare(r.y,0x0A)
            self._mark(0xCA70)
            if not r.p&C:
                continue
            else:
                pass
            self._y(0x08)
            self._a(m[0x0002])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0xFC)
            self._a(r.a | m[0x0003])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(m[SECOND_OFFICER])
            yield from self._external(0xCA86,0xF2D7,0xCA89,"call",None)
            if r.pc!=0xCA89:return  # preserve nonlocal stack return
            self._a(m[0x05B7])
            self._y(0x00)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(0x00)
            m[0x0002]=r.y
            m[0x0003]=r.y
            while True:  # natural loop $CA98
                self._a(m[(0x05B8+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xCA9D)
                if r.p&Z:
                    pass
                else:
                    self._a(m[(0x05B8+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0002])
                    m[0x0002]=r.a
                    self._a(m[0x0003])
                    self._add(0x00)
                    m[0x0003]=r.a
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x0A)
                self._mark(0xCAB4)
                if not r.p&C:
                    continue
                else:
                    pass
                self._y(0x08)
                self._a(m[0x0002])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xFC)
                self._a(r.a | m[0x0003])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._mark(0xCAC7)
                self._rts();return

    def probe_shifted_object_terrain(self):
        """Original entry $CAC8; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAC8)
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_X+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0000])
        m[0x0000]=r.a
        self._compare(r.a,0x10)
        self._mark(0xCAD7)
        if r.p&C:
            self._a(0x01)
            self._mark(0xCAE9)
            self._rts();return
        else:
            self._a(m[(OBJECT_Y+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0001])
            m[0x0001]=r.a
            self._compare(r.a,0x0A)
            self._mark(0xCAE5)
            if not r.p&C:
                self._push(0xCA);self._push(0xEC)
                yield from self.read_object_terrain_with_affinity()
                if r.pc!=0xCAED:return  # preserve nonlocal stack return
                self._compare(r.a,0x04)
                self._mark(0xCAEF)
                if r.p&Z:
                    self._a(0x00)
                    pass
                else:
                    self._compare(r.a,0x05)
                    self._mark(0xCAF3)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    pass
                self._y(r.a)
                self._mark(0xCAF8)
                self._rts();return
            else:
                self._a(0x01)
                self._mark(0xCAE9)
                self._rts();return

    def read_object_terrain_with_affinity(self):
        """Original entry $CAF9; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCAF9)
        self._a(m[BACKGROUND])
        self._push(r.a)
        self._y(r.a)
        self._a(m[(0xBB48+r.y)&65535])
        self._y(r.a)
        yield from self._external(0xCB02,0xF25F,0xCB05,"call",None)
        if r.pc!=0xCB05:return  # preserve nonlocal stack return
        self._a(self._pop())
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xBB1E+r.y)&65535])
        m[0x0002]=r.a
        self._a(m[(0xBB1F+r.y)&65535])
        m[0x0003]=r.a
        self._a(m[0x0001])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0000])
        self._y(r.a)
        self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
        self._y(r.a)
        self._a(m[(0xCB59+r.y)&65535])
        self._mark(0xCB25)
        if r.p&Z:
            pass
        else:
            self._compare(r.a,0x01)
            self._mark(0xCB29)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x05)
                self._mark(0xCB2D)
                if r.p&Z:
                    pass
                else:
                    self._push(r.a)
                    self._y(0x00)
                    self._a(m[OBJECT_INDEX])
                    self._compare(r.a,0x0B)
                    self._mark(0xCB37)
                    if not r.p&C:
                        pass
                    else:
                        self._y(r.y+1)
                        pass
                    self._a(m[(FIRST_OFFICER+r.y)&65535])
                    yield from self._external(0xCB3D,0xF2D7,0xCB40,"call",None)
                    if r.pc!=0xCB40:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._a(r.a & 0x03)
                    self._y(r.a)
                    self._a(self._pop())
                    self._x(r.a)
                    self._compare(r.a,m[(0xCBE9+r.y)&65535])
                    self._mark(0xCB4E)
                    if r.p&Z:
                        self._a(0x00)
                        pass
                    else:
                        self._compare(r.a,m[(0xCBED+r.y)&65535])
                        self._mark(0xCB53)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x00)
                            pass
                        pass
                    pass
                pass
            pass
        self._y(r.a)
        self._mark(0xCB58)
        self._rts();return

    def build_participant_stats_packets(self):
        """Original entry $CBF1; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBF1)
        self._y(0x20)
        self._a(0x00)
        while True:  # natural loop $CBF5
            m[(0x044C+r.y)&65535]=r.a
            self._y(r.y-1)
            self._mark(0xCBF9)
            if not r.p&N:
                continue
            else:
                pass
            self._a(m[OBJECT_VALUE])
            m[0x044C]=r.a
            self._a(m[0x05B7])
            m[0x044F]=r.a
            self._a(0x01)
            self._y(0x00)
            self._push(0xCC);self._push(0x0D)
            yield from self.participant_controller_input()
            if r.pc!=0xCC0E:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x0452]=r.a
            self._a(m[0x0002])
            m[0x0453]=r.a
            self._a(0x01)
            self._y(0x0B)
            self._push(0xCC);self._push(0x20)
            yield from self.participant_controller_input()
            if r.pc!=0xCC21:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x0455]=r.a
            self._a(m[0x0002])
            m[0x0456]=r.a
            self._a(0x02)
            self._y(0x00)
            self._push(0xCC);self._push(0x33)
            yield from self.participant_controller_input()
            if r.pc!=0xCC34:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x0458]=r.a
            self._a(m[0x0002])
            m[0x0459]=r.a
            self._a(0x02)
            self._y(0x0B)
            self._push(0xCC);self._push(0x46)
            yield from self.participant_controller_input()
            if r.pc!=0xCC47:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x045B]=r.a
            self._a(m[0x0002])
            m[0x045C]=r.a
            self._a(0x03)
            self._y(0x00)
            self._push(0xCC);self._push(0x59)
            yield from self.participant_controller_input()
            if r.pc!=0xCC5A:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x045E]=r.a
            self._a(m[0x0002])
            m[0x045F]=r.a
            self._a(0x03)
            self._y(0x0B)
            self._push(0xCC);self._push(0x6C)
            yield from self.participant_controller_input()
            if r.pc!=0xCC6D:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            m[0x0461]=r.a
            self._a(m[0x0002])
            m[0x0462]=r.a
            self._mark(0xCC79)
            self._rts();return

    def participant_controller_input(self):
        """Original entry $CC7A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC7A)
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._x(0x0A)
        while True:  # natural loop $CC87
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0x0F)
            self._compare(r.a,m[0x0000])
            self._mark(0xCC8F)
            if not r.p&Z:
                pass
            else:
                self._a(m[(OBJECT_VALUE+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0001])
                m[0x0001]=r.a
                self._a(m[0x0002])
                self._add(0x00)
                m[0x0002]=r.a
                pass
            self._y(r.y+1)
            self._x(r.x-1)
            self._mark(0xCCA5)
            if not r.p&N:
                continue
            else:
                pass
            self._mark(0xCCA7)
            self._rts();return

    def selected_side_controller_input(self):
        """Original entry $CCA8; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCA8)
        self._a(0xD8)
        m[0x000A]=r.a
        self._a(0xA0)
        m[0x000C]=r.a
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xCCC4)
        if not r.p&Z:
            self._mark(0xCCD8)
            self._rts();return
        else:
            self._a(0xD9)
            m[0x0000]=r.a
            self._a(0xCC)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._mark(0xCCD5)
            yield from self._external(0xCCD5,0xF1AD,None,"tail")
            return

    def side_controller_input(self):
        """Original entry $CCDE; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCCDE)
        self._compare(r.a,0x00)
        self._mark(0xCCE0)
        if not r.p&Z:
            self._a(m[SECOND_CONTROLLER])
            pass
        else:
            self._a(m[FIRST_CONTROLLER])
            pass
        self._compare(r.a,0x01)
        self._mark(0xCCED)
        if r.p&Z:
            self._a(m[0x0085])
            m[0x0000]=r.a
            self._a(m[0x0082])
            m[0x0001]=r.a
            self._a(r.a | m[0x057B])
            m[0x057B]=r.a
            self._mark(0xCD18)
            self._rts();return
        else:
            self._compare(r.a,0x03)
            self._mark(0xCCF1)
            if r.p&Z:
                self._a(0x00)
                m[0x0000]=r.a
                m[0x0001]=r.a
                self._mark(0xCD21)
                self._rts();return
            else:
                self._a(m[0x0083])
                m[0x0000]=r.a
                self._a(m[NEW_BUTTONS])
                m[0x0001]=r.a
                self._a(r.a | m[0x057B])
                m[0x057B]=r.a
                self._mark(0xCD05)
                self._rts();return

    def active_side_controller_input(self):
        """Original entry $CD22; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD22)
        self._a(0x00)
        self._push(0xCD);self._push(0x26)
        yield from self.side_controller_input()
        if r.pc!=0xCD27:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        self._push(r.a)
        self._a(m[0x0001])
        self._push(r.a)
        self._a(0x01)
        self._push(0xCD);self._push(0x33)
        yield from self.side_controller_input()
        if r.pc!=0xCD34:return  # preserve nonlocal stack return
        self._a(self._pop())
        self._a(r.a | m[0x0001])
        m[0x0001]=r.a
        self._a(self._pop())
        self._a(r.a | m[0x0000])
        m[0x0000]=r.a
        self._mark(0xCD42)
        self._rts();return

    def duel_handoff(self):
        """Original entry $CD43; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD43)
        self._a(m[PHASE])
        return (yield from self.duel_handoff_phase_dispatch())

    def duel_handoff_phase_dispatch(self):
        """Original entry $CD46; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD46)
        index=self._dispatch(0xCD46,(52559, 52569, 52687))
        return (yield from (self.duel_handoff_phase_0,self.duel_handoff_phase_1,self.duel_handoff_phase_2,)[index]())

    def duel_handoff_phase_0(self):
        """Original entry $CD4F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD4F)
        yield from self._external(0xCD4F,0xECEE,0xCD52,"call",None)
        if r.pc!=0xCD52:return  # preserve nonlocal stack return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._push(0xCD);self._push(0x57)
        yield from self.write_attack_results_to_battle()
        if r.pc!=0xCD58:return  # preserve nonlocal stack return
        self._mark(0xCD58)
        self._rts();return

    def duel_handoff_phase_1(self):
        """Original entry $CD59; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD59)
        self._a(m[FADE_FLAG])
        self._mark(0xCD5C)
        if not r.p&N:
            self._mark(0xCD58)
            self._rts();return
        else:
            yield from self._external(0xCD5E,0xE768,0xCD61,"call",None)
            if r.pc!=0xCD61:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x07)
            m[GLOBAL]=r.a
            self._a(0x00)
            m[0x04A8]=r.a
            m[0x04A9]=r.a
            m[0x04AA]=r.a
            self._a(m[FIRST_CONTROLLER])
            self._mark(0xCD77)
            if r.p&Z:
                self._a(m[FIRST_OFFICER])
                m[0x04AD]=r.a
                self._a(m[SECOND_OFFICER])
                m[0x04AE]=r.a
                self._a(m[FIRST_CONTROLLER])
                self._compare(r.a,0x03)
                self._mark(0xCD96)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x80)
                    pass
                m[0x04AB]=r.a
                self._a(m[SECOND_CONTROLLER])
                self._compare(r.a,0x03)
                self._mark(0xCDA2)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x80)
                    pass
                m[0x04AC]=r.a
                self._mark(0xCDA9)
                self._rts();return
            else:
                self._a(m[SECOND_CONTROLLER])
                self._mark(0xCD7C)
                if r.p&Z:
                    self._a(m[FIRST_OFFICER])
                    m[0x04AE]=r.a
                    self._a(m[SECOND_OFFICER])
                    m[0x04AD]=r.a
                    self._a(m[FIRST_CONTROLLER])
                    self._compare(r.a,0x03)
                    self._mark(0xCDBB)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x80)
                        pass
                    m[0x04AC]=r.a
                    self._a(m[SECOND_CONTROLLER])
                    self._compare(r.a,0x03)
                    self._mark(0xCDC7)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x80)
                        pass
                    m[0x04AB]=r.a
                    self._mark(0xCDCE)
                    self._rts();return
                else:
                    self._a(m[SECOND_CONTROLLER])
                    self._compare(r.a,0x01)
                    self._mark(0xCD83)
                    if r.p&Z:
                        self._a(m[FIRST_OFFICER])
                        m[0x04AE]=r.a
                        self._a(m[SECOND_OFFICER])
                        m[0x04AD]=r.a
                        self._a(m[FIRST_CONTROLLER])
                        self._compare(r.a,0x03)
                        self._mark(0xCDBB)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x80)
                            pass
                        m[0x04AC]=r.a
                        self._a(m[SECOND_CONTROLLER])
                        self._compare(r.a,0x03)
                        self._mark(0xCDC7)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x80)
                            pass
                        m[0x04AB]=r.a
                        self._mark(0xCDCE)
                        self._rts();return
                    else:
                        self._a(m[FIRST_OFFICER])
                        m[0x04AD]=r.a
                        self._a(m[SECOND_OFFICER])
                        m[0x04AE]=r.a
                        self._a(m[FIRST_CONTROLLER])
                        self._compare(r.a,0x03)
                        self._mark(0xCD96)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x80)
                            pass
                        m[0x04AB]=r.a
                        self._a(m[SECOND_CONTROLLER])
                        self._compare(r.a,0x03)
                        self._mark(0xCDA2)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x80)
                            pass
                        m[0x04AC]=r.a
                        self._mark(0xCDA9)
                        self._rts();return

    def duel_handoff_phase_2(self):
        """Original entry $CDCF; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCDCF)
        self._a(m[FADE_FLAG])
        self._mark(0xCDD2)
        if not r.p&N:
            pass
        else:
            self._a(m[FIRST_OFFICER])
            yield from self._external(0xCDD7,0xF2D7,0xCDDA,"call",None)
            if r.pc!=0xCDDA:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[OBJECT_VALUE]=r.a
            self._a(m[SECOND_OFFICER])
            yield from self._external(0xCDE4,0xF2D7,0xCDE7,"call",None)
            if r.pc!=0xCDE7:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x05B7]=r.a
            self._a(0x00)
            m[STATE]=r.a
            self._a(0x01)
            m[PHASE]=r.a
            self._a(0x00)
            m[SCAN_CURSOR]=r.a
            self._a(m[0x0514])
            self._y(m[0x0515])
            self._push(0xCE);self._push(0x05)
            yield from self.restore_saved_main_phase()
            if r.pc!=0xCE06:return  # preserve nonlocal stack return
            self._a(m[0x0516])
            self._y(m[0x0517])
            self._push(0xCE);self._push(0x0E)
            yield from self.restore_saved_main_phase()
            if r.pc!=0xCE0F:return  # preserve nonlocal stack return
            pass
        self._mark(0xCE0F)
        self._rts();return

    def restore_saved_main_phase(self):
        """Original entry $CE10; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE10)
        self._compare(r.y,0x01)
        self._mark(0xCE12)
        if not r.p&Z:
            self._mark(0xCE24)
            self._rts();return
        else:
            self._compare(r.a,m[FIRST_OFFICER])
            self._mark(0xCE17)
            if not r.p&Z:
                self._a(0x01)
                m[0x0554]=r.a
                self._mark(0xCE24)
                self._rts();return
            else:
                self._a(0x01)
                m[0x0550]=r.a
                self._mark(0xCE1E)
                self._rts();return

    def first_formation(self):
        """Original entry $CE25; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE25)
        self._a(m[PHASE])
        return (yield from self.first_formation_phase_dispatch())

    def first_formation_phase_dispatch(self):
        """Original entry $CE28; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE28)
        index=self._dispatch(0xCE28,(52787, 52840, 52910, 52986))
        return (yield from (self.first_formation_phase_0,self.first_formation_phase_1,self.first_formation_phase_2,self.first_formation_phase_3,)[index]())

    def first_formation_phase_0(self):
        """Original entry $CE33; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE33)
        yield from self._external(0xCE33,0xE87A,0xCE36,"call",None)
        if r.pc!=0xCE36:return  # preserve nonlocal stack return
        self._a(r.a & 0x03)
        m[FIRST_FORMATION]=r.a
        self._a(m[FIRST_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xCE40)
        if not r.p&Z:
            self._a(0xD4)
            yield from self._external(0xCE47,0xF26D,0xCE4A,"call",None)
            if r.pc!=0xCE4A:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(m[FIRST_OFFICER])
            m[0x0000]=r.a
            self._y(0x3D)
            yield from self._external(0xCE55,0xEE07,0xCE5A,"far_call",41008)
            if r.pc!=0xCE5A:return  # preserve nonlocal stack return
            self._a(0x00)
            m[0x0424]=r.a
            m[0x0425]=r.a
            self._a(0x7D)
            m[0x00BC]=r.a
            self._mark(0xCE67)
            self._rts();return
        else:
            return (yield from self.first_formation_phase_3())

    def first_formation_phase_1(self):
        """Original entry $CE68; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE68)
        self._a(m[FIRST_OFFICER])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xCE77,0xEE07,0xCE7C,"far_call",40960)
        if r.pc!=0xCE7C:return  # preserve nonlocal stack return
        self._y(0x00)
        self._push(0xCE);self._push(0x80)
        yield from self.formation_choice_input()
        if r.pc!=0xCE81:return  # preserve nonlocal stack return
        self._a(m[0x0012])
        m[FIRST_FORMATION]=r.a
        self._a(0x00)
        self._push(0xCE);self._push(0x8B)
        yield from self.side_controller_input()
        if r.pc!=0xCE8C:return  # preserve nonlocal stack return
        self._push(0xCE);self._push(0x8E)
        yield from self.text_readiness()
        if r.pc!=0xCE8F:return  # preserve nonlocal stack return
        self._mark(0xCE8F)
        if not r.p&C:
            pass
        else:
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xCE96)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xD2)
                yield from self._external(0xCE9D,0xF26D,0xCEA0,"call",None)
                if r.pc!=0xCEA0:return  # preserve nonlocal stack return
                self._a(m[0x0564])
                yield from self._external(0xCEA3,0xF368,0xCEA6,"call",None)
                if r.pc!=0xCEA6:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x042C]=r.a
                pass
            pass
        self._mark(0xCEAD)
        self._rts();return

    def first_formation_phase_2(self):
        """Original entry $CEAE; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCEAE)
        self._a(m[FIRST_OFFICER])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xCEBD,0xEE07,0xCEC2,"far_call",40960)
        if r.pc!=0xCEC2:return  # preserve nonlocal stack return
        self._a(0x00)
        self._push(0xCE);self._push(0xC6)
        yield from self.side_controller_input()
        if r.pc!=0xCEC7:return  # preserve nonlocal stack return
        self._push(0xCE);self._push(0xC9)
        yield from self.text_readiness()
        if r.pc!=0xCECA:return  # preserve nonlocal stack return
        self._mark(0xCECA)
        if not r.p&C:
            pass
        else:
            self._push(0xCE);self._push(0xCE)
            yield from self.draw_formation_selection_result()
            if r.pc!=0xCECF:return  # preserve nonlocal stack return
            self._a(0x00)
            self._push(0xCE);self._push(0xD3)
            yield from self.side_controller_input()
            if r.pc!=0xCED4:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xCED9)
            if r.p&Z:
                pass
            else:
                self._a(0x03)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x06)
                m[SAVED_STATE]=r.a
                self._a(0x03)
                m[SAVED_PHASE]=r.a
                self._a(0x00)
                m[ACTIVE_SIDE]=r.a
                self._a(0x05)
                m[0x00BC]=r.a
                pass
            pass
        self._mark(0xCEF9)
        self._rts();return

    def first_formation_phase_3(self):
        """Original entry $CEFA; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCEFA)
        self._a(0x07)
        m[STATE]=r.a
        self._a(0x00)
        m[PHASE]=r.a
        self._mark(0xCF04)
        self._rts();return

    def formation_choice_input(self):
        """Original entry $CF05; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF05)
        self._a(m[0x0083])
        self._push(r.a)
        self._a(m[NEW_BUTTONS])
        self._push(r.a)
        self._a(r.y)
        self._push(0xCF);self._push(0x10)
        yield from self.side_controller_input()
        if r.pc!=0xCF11:return  # preserve nonlocal stack return
        self._a(m[0x0000])
        m[0x0083]=r.a
        self._a(m[0x0001])
        m[NEW_BUTTONS]=r.a
        self._a(0x52)
        m[0x0010]=r.a
        self._a(0xCF)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xCF2C,0xED28,0xCF2F,"call",None)
        if r.pc!=0xCF2F:return  # preserve nonlocal stack return
        self._a(0x5A)
        m[0x0010]=r.a
        self._a(0xCF)
        m[0x0011]=r.a
        self._a(0x62)
        m[0x0000]=r.a
        self._a(0xCF)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xCF46,0xEDF5,0xCF49,"call",None)
        if r.pc!=0xCF49:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[NEW_BUTTONS]=r.a
        self._a(self._pop())
        m[0x0083]=r.a
        self._mark(0xCF51)
        self._rts();return

    def second_formation(self):
        """Original entry $CF67; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF67)
        self._a(m[PHASE])
        return (yield from self.second_formation_phase_dispatch())

    def second_formation_phase_dispatch(self):
        """Original entry $CF6A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF6A)
        index=self._dispatch(0xCF6A,(53111, 53149, 53186, 53256, 53332))
        return (yield from (self.second_formation_phase_0,self.second_formation_phase_1,self.second_formation_phase_2,self.second_formation_phase_3,self.second_formation_phase_4,)[index]())

    def second_formation_phase_0(self):
        """Original entry $CF77; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF77)
        yield from self._external(0xCF77,0xE87A,0xCF7A,"call",None)
        if r.pc!=0xCF7A:return  # preserve nonlocal stack return
        self._a(r.a & 0x03)
        m[SECOND_FORMATION]=r.a
        self._a(m[SECOND_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xCF84)
        if not r.p&Z:
            self._a(0x00)
            m[0x0310]=r.a
            m[0x0300]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x00)
            m[0x0424]=r.a
            m[0x0425]=r.a
            self._mark(0xCF9C)
            self._rts();return
        else:
            return (yield from self.second_formation_phase_4())

    def second_formation_phase_1(self):
        """Original entry $CF9D; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF9D)
        self._push(0xCF);self._push(0x9F)
        yield from self.text_readiness()
        if r.pc!=0xCFA0:return  # preserve nonlocal stack return
        self._mark(0xCFA0)
        if not r.p&C:
            pass
        else:
            self._a(0xD4)
            yield from self._external(0xCFA4,0xF26D,0xCFA7,"call",None)
            if r.pc!=0xCFA7:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(m[SECOND_OFFICER])
            m[0x0000]=r.a
            self._y(0x3D)
            yield from self._external(0xCFB2,0xEE07,0xCFB7,"far_call",41008)
            if r.pc!=0xCFB7:return  # preserve nonlocal stack return
            self._a(0x09)
            m[0x00BB]=r.a
            self._a(0x7D)
            m[0x00BC]=r.a
            pass
        self._mark(0xCFC1)
        self._rts();return

    def second_formation_phase_2(self):
        """Original entry $CFC2; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCFC2)
        self._a(m[SECOND_OFFICER])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xCFD1,0xEE07,0xCFD6,"far_call",40960)
        if r.pc!=0xCFD6:return  # preserve nonlocal stack return
        self._y(0x01)
        self._push(0xCF);self._push(0xDA)
        yield from self.formation_choice_input()
        if r.pc!=0xCFDB:return  # preserve nonlocal stack return
        self._a(m[0x0012])
        m[SECOND_FORMATION]=r.a
        self._a(0x01)
        self._push(0xCF);self._push(0xE5)
        yield from self.side_controller_input()
        if r.pc!=0xCFE6:return  # preserve nonlocal stack return
        self._push(0xCF);self._push(0xE8)
        yield from self.text_readiness()
        if r.pc!=0xCFE9:return  # preserve nonlocal stack return
        self._mark(0xCFE9)
        if not r.p&C:
            pass
        else:
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xCFF0)
            if r.p&Z:
                pass
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xD2)
                yield from self._external(0xCFF7,0xF26D,0xCFFA,"call",None)
                if r.pc!=0xCFFA:return  # preserve nonlocal stack return
                self._a(m[0x0565])
                yield from self._external(0xCFFD,0xF368,0xD000,"call",None)
                if r.pc!=0xD000:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x042C]=r.a
                pass
            pass
        self._mark(0xD007)
        self._rts();return

    def second_formation_phase_3(self):
        """Original entry $D008; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD008)
        self._a(m[SECOND_OFFICER])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xD017,0xEE07,0xD01C,"far_call",40960)
        if r.pc!=0xD01C:return  # preserve nonlocal stack return
        self._a(0x01)
        self._push(0xD0);self._push(0x20)
        yield from self.side_controller_input()
        if r.pc!=0xD021:return  # preserve nonlocal stack return
        self._push(0xD0);self._push(0x23)
        yield from self.text_readiness()
        if r.pc!=0xD024:return  # preserve nonlocal stack return
        self._mark(0xD024)
        if not r.p&C:
            pass
        else:
            self._push(0xD0);self._push(0x28)
            yield from self.draw_formation_selection_result()
            if r.pc!=0xD029:return  # preserve nonlocal stack return
            self._a(0x01)
            self._push(0xD0);self._push(0x2D)
            yield from self.side_controller_input()
            if r.pc!=0xD02E:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xD033)
            if r.p&Z:
                pass
            else:
                self._a(0x03)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._a(0x07)
                m[SAVED_STATE]=r.a
                self._a(0x04)
                m[SAVED_PHASE]=r.a
                self._a(0x01)
                m[ACTIVE_SIDE]=r.a
                self._a(0x05)
                m[0x00BC]=r.a
                pass
            pass
        self._mark(0xD053)
        self._rts();return

    def second_formation_phase_4(self):
        """Original entry $D054; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD054)
        self._a(0x00)
        m[STATE]=r.a
        self._a(0x01)
        m[PHASE]=r.a
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._push(0xD0);self._push(0x65)
        yield from self.prepare_attack_object_arrays()
        if r.pc!=0xD066:return  # preserve nonlocal stack return
        self._mark(0xD066)
        self._rts();return

    def round_stat_check(self):
        """Original entry $D067; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD067)
        self._push(0xD0);self._push(0x69)
        yield from self.test_first_commander()
        if r.pc!=0xD06A:return  # preserve nonlocal stack return
        self._a(m[0x057A])
        self._compare(r.a,0x04)
        self._mark(0xD06F)
        if not r.p&C:
            pass
        else:
            self._a(m[FIRST_CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xD076)
            if not r.p&Z:
                pass
            else:
                self._y(0x00)
                self._push(0xD0);self._push(0x7C)
                yield from self.formation_damage_evaluation()
                if r.pc!=0xD07D:return  # preserve nonlocal stack return
                pass
            self._a(m[SECOND_CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xD082)
            if not r.p&Z:
                pass
            else:
                self._y(0x0B)
                self._push(0xD0);self._push(0x88)
                yield from self.formation_damage_evaluation()
                if r.pc!=0xD089:return  # preserve nonlocal stack return
                pass
            pass
        self._a(0x00)
        m[OBJECT_INDEX]=r.a
        self._a(m[0x057A])
        self._compare(r.a,0x04)
        self._mark(0xD093)
        if not r.p&C:
            pass
        else:
            self._a(m[FIRST_CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xD09A)
            if not r.p&Z:
                pass
            else:
                self._y(0x00)
                self._push(0xD0);self._push(0xA0)
                yield from self.formation_object_parameters()
                if r.pc!=0xD0A1:return  # preserve nonlocal stack return
                pass
            self._a(m[SECOND_CONTROLLER])
            self._compare(r.a,0x03)
            self._mark(0xD0A6)
            if not r.p&Z:
                pass
            else:
                self._y(0x0B)
                self._push(0xD0);self._push(0xAC)
                yield from self.formation_object_parameters()
                if r.pc!=0xD0AD:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xD0AD)
        self._rts();return

    def round_resource_check(self):
        """Original entry $D0AE; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0AE)
        self._a(m[FIRST_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xD0B3)
        if not r.p&Z:
            pass
        else:
            self._x(0x00)
            self._y(0x00)
            self._push(0xD0);self._push(0xBB)
            yield from self.formation_special_evaluation()
            if r.pc!=0xD0BC:return  # preserve nonlocal stack return
            pass
        self._a(m[SECOND_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xD0C1)
        if not r.p&Z:
            pass
        else:
            self._x(0x01)
            self._y(0x0B)
            self._push(0xD0);self._push(0xC9)
            yield from self.formation_special_evaluation()
            if r.pc!=0xD0CA:return  # preserve nonlocal stack return
            pass
        self._mark(0xD0CA)
        self._rts();return

    def test_first_commander(self):
        """Original entry $D0CB; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0CB)
        self._a(m[FIRST_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xD0D0)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0550])
            self._compare(r.a,0x01)
            self._mark(0xD0D7)
            if r.p&Z:
                pass
            else:
                self._a(m[FIRST_OFFICER])
                m[0x000C]=r.a
                self._a(0x00)
                self._x(0x00)
                self._push(0xD0);self._push(0xE5)
                yield from self.formation_pair_evaluation()
                if r.pc!=0xD0E6:return  # preserve nonlocal stack return
                pass
            pass
        self._a(m[SECOND_CONTROLLER])
        self._compare(r.a,0x03)
        self._mark(0xD0EB)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x0554])
            self._compare(r.a,0x01)
            self._mark(0xD0F2)
            if r.p&Z:
                pass
            else:
                self._a(m[SECOND_OFFICER])
                m[0x000C]=r.a
                self._a(0x04)
                self._x(0x01)
                self._push(0xD1);self._push(0x00)
                yield from self.formation_pair_evaluation()
                if r.pc!=0xD101:return  # preserve nonlocal stack return
                pass
            pass
        self._mark(0xD101)
        self._rts();return

    def formation_pair_evaluation(self):
        """Original entry $D102; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD102)
        m[0x000A]=r.a
        m[0x000B]=r.x
        self._a(m[0x000C])
        yield from self._external(0xD10B,0xF2D7,0xD10E,"call",None)
        if r.pc!=0xD10E:return  # preserve nonlocal stack return
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x03)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[BACKGROUND])
        self._y(r.a)
        self._a(m[(0xD1B0+r.y)&65535])
        m[0x000D]=r.a
        self._a(m[0x057A])
        self._compare(r.a,0x04)
        self._mark(0xD129)
        if not r.p&C:
            pass
        else:
            self._a(m[0x000D])
            self._flag(C,False)
            self._add(0x04)
            m[0x000D]=r.a
            pass
        self._x(m[0x000D])
        self._y(m[0x000A])
        self._a(m[BACKGROUND])
        self._compare(r.a,0x05)
        self._mark(0xD13F)
        if r.p&Z:
            self._compare(r.y,0x04)
            self._mark(0xD15C)
            if r.p&C:
                self._a(0x02)
                m[(0x0550+r.y)&65535]=r.a
                m[(0x0551+r.y)&65535]=r.a
                m[(0x0552+r.y)&65535]=r.a
                m[(0x0553+r.y)&65535]=r.a
                self._a(m[0x057A])
                self._compare(r.a,0x06)
                self._mark(0xD18E)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[(0x0551+r.y)&65535]=r.a
                    pass
                self._y(0x01)
                self._x(0x00)
                while True:  # natural loop $D199
                    self._a(m[(OBJECT_X+r.y)&65535])
                    self._compare(r.a,0x08)
                    self._mark(0xD19E)
                    if r.p&C:
                        pass
                    else:
                        self._x(r.x+1)
                        pass
                    self._y(r.y+1)
                    self._compare(r.y,0x0B)
                    self._mark(0xD1A4)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._compare(r.x,0x00)
                    self._mark(0xD1A8)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(0x00)
                        m[0x0556]=r.a
                        pass
                    self._mark(0xD1AF)
                    self._rts();return
            else:
                self._a(0x02)
                m[(0x0550+r.y)&65535]=r.a
                self._a(0x00)
                m[(0x0551+r.y)&65535]=r.a
                m[(0x0552+r.y)&65535]=r.a
                m[(0x0553+r.y)&65535]=r.a
                self._a(m[0x057A])
                self._compare(r.a,0x04)
                self._mark(0xD173)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[(0x0550+r.y)&65535]=r.a
                    pass
                self._mark(0xD17A)
                self._rts();return
        else:
            self._a(m[(0xD1C8+r.x)&65535])
            m[(0x0550+r.y)&65535]=r.a
            self._a(m[(0xD1C9+r.x)&65535])
            m[(0x0551+r.y)&65535]=r.a
            self._a(m[(0xD1CA+r.x)&65535])
            m[(0x0552+r.y)&65535]=r.a
            self._a(m[(0xD1CB+r.x)&65535])
            m[(0x0553+r.y)&65535]=r.a
            self._mark(0xD159)
            self._rts();return

    def formation_damage_evaluation(self):
        """Original entry $D1D8; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1D8)
        m[OBJECT_INDEX]=r.y
        self._a(m[(OBJECT_VALUE+r.y)&65535])
        self._y(m[0x6F02])
        self._compare(r.a,m[(0xD1E7+r.y)&65535])
        self._mark(0xD1E4)
        if not r.p&C:
            self._a(0x00)
            m[SCAN_CURSOR]=r.a
            self._a(0x01)
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            self._push(0xD1);self._push(0xFE)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD1FF:return  # preserve nonlocal stack return
            self._mark(0xD1FF)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD202)
                if r.p&Z:
                    pass
                else:
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    pass
                pass
            self._a(0xFF)
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            self._push(0xD2);self._push(0x13)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD214:return  # preserve nonlocal stack return
            self._mark(0xD214)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD217)
                if r.p&Z:
                    pass
                else:
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    pass
                pass
            self._a(0x00)
            m[0x0000]=r.a
            self._a(0xFF)
            m[0x0001]=r.a
            self._push(0xD2);self._push(0x28)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD229:return  # preserve nonlocal stack return
            self._mark(0xD229)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD22C)
                if r.p&Z:
                    pass
                else:
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    pass
                pass
            self._a(0x00)
            m[0x0000]=r.a
            self._a(0x01)
            m[0x0001]=r.a
            self._push(0xD2);self._push(0x3D)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD23E:return  # preserve nonlocal stack return
            self._mark(0xD23E)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD241)
                if r.p&Z:
                    pass
                else:
                    m[SCAN_CURSOR]=self._nz(m[SCAN_CURSOR]+1)
                    pass
                pass
            self._a(m[SCAN_CURSOR])
            self._compare(r.a,0x02)
            self._mark(0xD24B)
            if r.p&C:
                self._a(m[FIRST_OFFICER])
                self._y(m[OBJECT_INDEX])
                self._compare(r.y,0x0B)
                self._mark(0xD256)
                if not r.p&C:
                    pass
                else:
                    self._a(m[SECOND_OFFICER])
                    pass
                yield from self._external(0xD25B,0xF2D7,0xD25E,"call",None)
                if r.pc!=0xD25E:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x64)
                self._mark(0xD264)
                if r.p&Z:
                    self._mark(0xD24D)
                    self._rts();return
                else:
                    self._a(0x64)
                    yield from self._external(0xD268,0xE862,0xD26B,"call",None)
                    if r.pc!=0xD26B:return  # preserve nonlocal stack return
                    self._y(m[0x6F02])
                    self._compare(r.a,m[(0xD1EA+r.y)&65535])
                    self._mark(0xD271)
                    if r.p&C:
                        self._mark(0xD24D)
                        self._rts();return
                    else:
                        self._a(self._pop())
                        self._a(self._pop())
                        yield from self._external(0xD275,0xE57F,0xD278,"call",None)
                        if r.pc!=0xD278:return  # preserve nonlocal stack return
                        self._a(0x6C)
                        yield from self._external(0xD27A,0xE683,0xD27D,"call",None)
                        if r.pc!=0xD27D:return  # preserve nonlocal stack return
                        self._a(m[OBJECT_INDEX])
                        self._mark(0xD280)
                        if not r.p&Z:
                            self._a(m[SECOND_OFFICER])
                            m[0x042C]=r.a
                            m[0x0514]=r.a
                            self._a(0x03)
                            m[0x0515]=r.a
                            self._a(m[SECOND_OFFICER])
                            m[0x0516]=r.a
                            self._a(0x00)
                            m[0x0517]=r.a
                            self._a(0x04)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            self._a(0x7D)
                            yield from self._external(0xD2D0,0xF28B,0xD2D3,"call",None)
                            if r.pc!=0xD2D3:return  # preserve nonlocal stack return
                            self._mark(0xD2D3)
                            self._rts();return
                        else:
                            self._a(m[FIRST_OFFICER])
                            m[0x042C]=r.a
                            m[0x0514]=r.a
                            self._a(0x03)
                            m[0x0515]=r.a
                            self._a(m[SECOND_OFFICER])
                            m[0x0516]=r.a
                            self._a(0x00)
                            m[0x0517]=r.a
                            self._a(0x04)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            self._a(0x7D)
                            yield from self._external(0xD2A7,0xF28B,0xD2AA,"call",None)
                            if r.pc!=0xD2AA:return  # preserve nonlocal stack return
                            self._mark(0xD2AA)
                            self._rts();return
            else:
                self._mark(0xD24D)
                self._rts();return
        else:
            self._mark(0xD1E6)
            self._rts();return

    def formation_object_parameters(self):
        """Original entry $D2D4; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2D4)
        m[OBJECT_INDEX]=r.y
        self._a(m[OBJECT_INDEX])
        self._mark(0xD2DA)
        if not r.p&Z:
            self._a(m[0x0554])
            self._compare(r.a,0x01)
            self._mark(0xD2EA)
            if not r.p&Z:
                self._push(0xD2);self._push(0xEF)
                yield from self.formation_probability_evaluation()
                if r.pc!=0xD2F0:return  # preserve nonlocal stack return
                self._a(r.y)
                self._mark(0xD2F1)
                if not r.p&Z:
                    self._mark(0xD317)
                    self._rts();return
                else:
                    self._a(0x64)
                    yield from self._external(0xD2F5,0xE862,0xD2F8,"call",None)
                    if r.pc!=0xD2F8:return  # preserve nonlocal stack return
                    self._y(m[0x6F02])
                    self._compare(r.a,m[(0xD327+r.y)&65535])
                    self._mark(0xD2FE)
                    if r.p&C:
                        self._mark(0xD317)
                        self._rts();return
                    else:
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(m[OBJECT_INDEX])
                        self._mark(0xD307)
                        if not r.p&Z:
                            self._a(0x01)
                            m[0x0554]=r.a
                            m[0x0555]=r.a
                            m[0x0556]=r.a
                            m[0x0557]=r.a
                            self._mark(0xD326)
                            self._rts();return
                        else:
                            self._a(0x01)
                            m[0x0550]=r.a
                            m[0x0551]=r.a
                            m[0x0552]=r.a
                            m[0x0553]=r.a
                            self._mark(0xD317)
                            self._rts();return
            else:
                self._mark(0xD2EC)
                self._rts();return
        else:
            self._a(m[0x0550])
            self._compare(r.a,0x01)
            self._mark(0xD2E1)
            if not r.p&Z:
                self._push(0xD2);self._push(0xEF)
                yield from self.formation_probability_evaluation()
                if r.pc!=0xD2F0:return  # preserve nonlocal stack return
                self._a(r.y)
                self._mark(0xD2F1)
                if not r.p&Z:
                    self._mark(0xD317)
                    self._rts();return
                else:
                    self._a(0x64)
                    yield from self._external(0xD2F5,0xE862,0xD2F8,"call",None)
                    if r.pc!=0xD2F8:return  # preserve nonlocal stack return
                    self._y(m[0x6F02])
                    self._compare(r.a,m[(0xD327+r.y)&65535])
                    self._mark(0xD2FE)
                    if r.p&C:
                        self._mark(0xD317)
                        self._rts();return
                    else:
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(self._pop())
                        self._a(m[OBJECT_INDEX])
                        self._mark(0xD307)
                        if not r.p&Z:
                            self._a(0x01)
                            m[0x0554]=r.a
                            m[0x0555]=r.a
                            m[0x0556]=r.a
                            m[0x0557]=r.a
                            self._mark(0xD326)
                            self._rts();return
                        else:
                            self._a(0x01)
                            m[0x0550]=r.a
                            m[0x0551]=r.a
                            m[0x0552]=r.a
                            m[0x0553]=r.a
                            self._mark(0xD317)
                            self._rts();return
            else:
                self._mark(0xD2E3)
                if r.p&Z:
                    self._mark(0xD2EC)
                    self._rts();return
                else:
                    self._a(m[0x0554])
                    self._compare(r.a,0x01)
                    self._mark(0xD2EA)
                    if not r.p&Z:
                        self._push(0xD2);self._push(0xEF)
                        yield from self.formation_probability_evaluation()
                        if r.pc!=0xD2F0:return  # preserve nonlocal stack return
                        self._a(r.y)
                        self._mark(0xD2F1)
                        if not r.p&Z:
                            self._mark(0xD317)
                            self._rts();return
                        else:
                            self._a(0x64)
                            yield from self._external(0xD2F5,0xE862,0xD2F8,"call",None)
                            if r.pc!=0xD2F8:return  # preserve nonlocal stack return
                            self._y(m[0x6F02])
                            self._compare(r.a,m[(0xD327+r.y)&65535])
                            self._mark(0xD2FE)
                            if r.p&C:
                                self._mark(0xD317)
                                self._rts();return
                            else:
                                self._a(self._pop())
                                self._a(self._pop())
                                self._a(self._pop())
                                self._a(self._pop())
                                self._a(m[OBJECT_INDEX])
                                self._mark(0xD307)
                                if not r.p&Z:
                                    self._a(0x01)
                                    m[0x0554]=r.a
                                    m[0x0555]=r.a
                                    m[0x0556]=r.a
                                    m[0x0557]=r.a
                                    self._mark(0xD326)
                                    self._rts();return
                                else:
                                    self._a(0x01)
                                    m[0x0550]=r.a
                                    m[0x0551]=r.a
                                    m[0x0552]=r.a
                                    m[0x0553]=r.a
                                    self._mark(0xD317)
                                    self._rts();return
                    else:
                        self._mark(0xD2EC)
                        self._rts();return

    def formation_probability_evaluation(self):
        """Original entry $D32A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD32A)
        self._y(0x00)
        self._x(0x00)
        m[0x0000]=r.x
        m[0x0001]=r.x
        while True:  # natural loop $D334
            self._a(m[(0x0581+r.y)&65535])
            self._mark(0xD337)
            if r.p&N:
                pass
            else:
                self._a(m[(0x05AD+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0000])
                m[0x0000]=r.a
                self._a(m[0x0001])
                self._add(0x00)
                m[0x0001]=r.a
                pass
            self._y(r.y+1)
            self._x(r.x+1)
            self._compare(r.x,0x0A)
            self._mark(0xD34F)
            if not r.p&C:
                continue
            else:
                pass
            self._y(0x00)
            self._x(0x00)
            m[0x0002]=r.x
            m[0x0003]=r.x
            while True:  # natural loop $D35B
                self._a(m[(0x058C+r.y)&65535])
                self._mark(0xD35E)
                if r.p&N:
                    pass
                else:
                    self._a(m[(0x05B8+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0002])
                    m[0x0002]=r.a
                    self._a(m[0x0003])
                    self._add(0x00)
                    m[0x0003]=r.a
                    pass
                self._y(r.y+1)
                self._x(r.x+1)
                self._compare(r.x,0x0A)
                self._mark(0xD376)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[OBJECT_INDEX])
                self._mark(0xD37B)
                if r.p&Z:
                    pass
                else:
                    self._x(m[0x0000])
                    self._y(m[0x0001])
                    self._a(m[0x0002])
                    m[0x0000]=r.a
                    self._a(m[0x0003])
                    m[0x0001]=r.a
                    m[0x0002]=r.x
                    m[0x0003]=r.y
                    pass
                self._a(m[0x0001])
                self._mark(0xD398)
                if not r.p&Z:
                    self._y(0xFF)
                    self._mark(0xD3C6)
                    self._rts();return
                else:
                    self._a(m[0x0000])
                    self._compare(r.a,0xC8)
                    self._mark(0xD39F)
                    if r.p&C:
                        self._y(0xFF)
                        self._mark(0xD3C6)
                        self._rts();return
                    else:
                        self._a(m[0x0000])
                        self._flag(C,False)
                        self._add(0x90)
                        m[0x0000]=r.a
                        self._a(m[0x0001])
                        self._add(0x01)
                        m[0x0001]=r.a
                        self._a(m[0x0000])
                        self._flag(C,True)
                        self._add(m[0x0002],subtract=True)
                        self._a(m[0x0001])
                        self._add(m[0x0003],subtract=True)
                        self._mark(0xD3BF)
                        if r.p&C:
                            self._y(0xFF)
                            self._mark(0xD3C6)
                            self._rts();return
                        else:
                            self._y(0x00)
                            self._mark(0xD3C3)
                            self._rts();return

    def formation_special_evaluation(self):
        """Original entry $D3C7; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3C7)
        m[0x057C]=r.x
        m[ACTIVE_SIDE]=r.x
        m[OBJECT_INDEX]=r.y
        self._a(m[0x0574])
        self._a(r.a | m[0x0575])
        self._a(r.a | m[0x0576])
        self._a(r.a | m[0x0577])
        self._x(m[0x0572])
        self._compare(r.y,0x00)
        self._mark(0xD3E1)
        if r.p&Z:
            pass
        else:
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._x(m[0x0573])
            pass
        m[SCAN_CURSOR]=r.x
        self._a(r.a & 0x0F)
        self._mark(0xD3EF)
        if r.p&Z:
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x0C)
            self._mark(0xD3F7)
            if not r.p&C:
                pass
            else:
                self._push(0xD3);self._push(0xFB)
                yield from self.resolve_formation_results()
                if r.pc!=0xD3FC:return  # preserve nonlocal stack return
                pass
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x0A)
            self._mark(0xD401)
            if not r.p&C:
                pass
            else:
                self._push(0xD4);self._push(0x05)
                yield from self.commit_formation_damage()
                if r.pc!=0xD406:return  # preserve nonlocal stack return
                pass
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x08)
            self._mark(0xD40B)
            if not r.p&C:
                pass
            else:
                self._push(0xD4);self._push(0x0F)
                yield from self.draw_formation_counter()
                if r.pc!=0xD410:return  # preserve nonlocal stack return
                pass
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x07)
            self._mark(0xD415)
            if not r.p&C:
                pass
            else:
                self._push(0xD4);self._push(0x19)
                yield from self.queued_object_map_update()
                if r.pc!=0xD41A:return  # preserve nonlocal stack return
                pass
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x05)
            self._mark(0xD41F)
            if not r.p&C:
                pass
            else:
                self._push(0xD4);self._push(0x23)
                yield from self.prepare_selected_side_object()
                if r.pc!=0xD424:return  # preserve nonlocal stack return
                pass
            self._x(m[SCAN_CURSOR])
            self._compare(r.x,0x03)
            self._mark(0xD429)
            if not r.p&C:
                pass
            else:
                self._push(0xD4);self._push(0x2D)
                yield from self.side_object_position()
                if r.pc!=0xD42E:return  # preserve nonlocal stack return
                pass
            self._mark(0xD42E)
            self._rts();return
        else:
            self._mark(0xD3F1)
            self._rts();return

    def resolve_formation_results(self):
        """Original entry $D42F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD42F)
        self._y(m[OBJECT_INDEX])
        self._a(m[(OBJECT_ENCODING+r.y)&65535])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        m[0x057D]=r.a
        self._a(0x00)
        m[0x057E]=r.a
        while True:  # natural loop $D441
            self._push(r.a)
            self._y(r.a)
            self._a(m[0x057D])
            r.a=self._shift(r.a,True,rotate=False)
            self._x(r.a)
            self._a(m[(0xD4AA+r.x)&65535])
            m[0x000A]=r.a
            self._a(m[(0xD4AB+r.x)&65535])
            m[0x000B]=r.a
            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
            m[0x0000]=r.a
            self._a(r.y)
            self._flag(C,False)
            self._add(0x09)
            self._y(r.a)
            self._a(m[((m[0x0A]|m[0x0B]<<8)+r.y)&65535])
            m[0x0001]=r.a
            self._push(0xD4);self._push(0x65)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD466:return  # preserve nonlocal stack return
            self._mark(0xD466)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD469)
                if r.p&Z:
                    pass
                else:
                    m[0x057E]=self._nz(m[0x057E]+1)
                    pass
                pass
            self._a(self._pop())
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x09)
            self._mark(0xD474)
            if not r.p&C:
                continue
            else:
                pass
            self._y(m[0x057E])
            self._a(m[(0xD4FA+r.y)&65535])
            self._mark(0xD47C)
            if r.p&Z:
                self._mark(0xD48B)
                self._rts();return
            else:
                m[0x000A]=r.a
                self._a(0x64)
                yield from self._external(0xD483,0xE862,0xD486,"call",None)
                if r.pc!=0xD486:return  # preserve nonlocal stack return
                self._compare(r.a,m[0x000A])
                self._mark(0xD489)
                if not r.p&C:
                    self._a(self._pop())
                    self._a(self._pop())
                    self._a(0x09)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0xF1)
                    yield from self._external(0xD49A,0xF26D,0xD49D,"call",None)
                    if r.pc!=0xD49D:return  # preserve nonlocal stack return
                    self._y(m[0x057C])
                    self._a(m[(0x0572+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x0C,subtract=True)
                    m[(0x0572+r.y)&65535]=r.a
                    self._mark(0xD4A9)
                    self._rts();return
                else:
                    self._mark(0xD48B)
                    self._rts();return

    def commit_formation_damage(self):
        """Original entry $D506; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD506)
        self._a(0x00)
        m[0x057E]=r.a
        self._a(m[OBJECT_INDEX])
        self._push(r.a)
        while True:  # natural loop $D50F
            self._y(m[OBJECT_INDEX])
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._a(r.a & 0x0F)
            self._compare(r.a,0x02)
            self._mark(0xD519)
            if not r.p&Z:
                pass
            else:
                self._push(0xD5);self._push(0x1D)
                yield from self.evaluate_routed_formation()
                if r.pc!=0xD51E:return  # preserve nonlocal stack return
                pass
            m[OBJECT_INDEX]=self._nz(m[OBJECT_INDEX]+1)
            self._a(m[OBJECT_INDEX])
            self._compare(r.a,0x0B)
            self._mark(0xD526)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x16)
                self._mark(0xD52A)
                if not r.p&Z:
                    continue
                else:
                    pass
                pass
            self._a(self._pop())
            m[OBJECT_INDEX]=r.a
            self._y(m[0x057E])
            self._a(m[(0xD594+r.y)&65535])
            self._mark(0xD536)
            if r.p&Z:
                self._mark(0xD545)
                self._rts();return
            else:
                m[0x000A]=r.a
                self._a(0x64)
                yield from self._external(0xD53D,0xE862,0xD540,"call",None)
                if r.pc!=0xD540:return  # preserve nonlocal stack return
                self._compare(r.a,m[0x000A])
                self._mark(0xD543)
                if not r.p&C:
                    self._push(0xD5);self._push(0x48)
                    yield from self.queue_action_success()
                    if r.pc!=0xD549:return  # preserve nonlocal stack return
                    self._y(m[0x057C])
                    self._a(m[(0x0572+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x0A,subtract=True)
                    m[(0x0572+r.y)&65535]=r.a
                    self._a(self._pop())
                    self._a(self._pop())
                    self._mark(0xD557)
                    self._rts();return
                else:
                    self._mark(0xD545)
                    self._rts();return

    def evaluate_routed_formation(self):
        """Original entry $D558; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD558)
        self._a(0x00)
        while True:  # natural loop $D55A
            self._push(r.a)
            self._y(r.a)
            self._a(m[(0xD57C+r.y)&65535])
            m[0x0000]=r.a
            self._a(m[(0xD588+r.y)&65535])
            m[0x0001]=r.a
            self._push(0xD5);self._push(0x6A)
            yield from self.probe_shifted_object_position()
            if r.pc!=0xD56B:return  # preserve nonlocal stack return
            self._mark(0xD56B)
            if r.p&C:
                pass
            else:
                self._y(r.a)
                self._mark(0xD56E)
                if r.p&Z:
                    pass
                else:
                    m[0x057E]=self._nz(m[0x057E]+1)
                    pass
                pass
            self._a(self._pop())
            self._flag(C,False)
            self._add(0x01)
            self._compare(r.a,0x09)
            self._mark(0xD579)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD57B)
            self._rts();return

    def draw_formation_counter(self):
        """Original entry $D5A0; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5A0)
        self._a(0x64)
        yield from self._external(0xD5A2,0xE862,0xD5A5,"call",None)
        if r.pc!=0xD5A5:return  # preserve nonlocal stack return
        self._compare(r.a,0x14)
        self._mark(0xD5A7)
        if not r.p&C:
            self._push(0xD5);self._push(0xAC)
            yield from self.evaluate_action_object()
            if r.pc!=0xD5AD:return  # preserve nonlocal stack return
            self._y(m[0x057C])
            self._a(m[(0x0572+r.y)&65535])
            self._flag(C,True)
            self._add(0x08,subtract=True)
            m[(0x0572+r.y)&65535]=r.a
            self._a(self._pop())
            self._a(self._pop())
            self._mark(0xD5BB)
            self._rts();return
        else:
            self._mark(0xD5A9)
            self._rts();return

    def queued_object_map_update(self):
        """Original entry $D5BC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5BC)
        self._push(0xD5);self._push(0xBE)
        yield from self.draw_selected_participant()
        if r.pc!=0xD5BF:return  # preserve nonlocal stack return
        self._y(m[0x0000])
        self._mark(0xD5C2)
        if r.p&Z:
            self._mark(0xD5D4)
            self._rts();return
        else:
            self._a(m[(0xD5E7+r.y)&65535])
            m[0x000A]=r.a
            self._a(0x64)
            yield from self._external(0xD5CC,0xE862,0xD5CF,"call",None)
            if r.pc!=0xD5CF:return  # preserve nonlocal stack return
            self._compare(r.a,m[0x000A])
            self._mark(0xD5D2)
            if not r.p&C:
                self._push(0xD5);self._push(0xD7)
                yield from self.advance_action_object()
                if r.pc!=0xD5D8:return  # preserve nonlocal stack return
                self._y(m[0x057C])
                self._a(m[(0x0572+r.y)&65535])
                self._flag(C,True)
                self._add(0x07,subtract=True)
                m[(0x0572+r.y)&65535]=r.a
                self._a(self._pop())
                self._a(self._pop())
                self._mark(0xD5E6)
                self._rts();return
            else:
                self._mark(0xD5D4)
                self._rts();return

    def draw_selected_participant(self):
        """Original entry $D5F3; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5F3)
        self._y(m[OBJECT_INDEX])
        self._x(0x00)
        m[0x0000]=r.x
        while True:  # natural loop $D5FB
            self._a(m[(OBJECT_ENCODING+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xD600)
            if r.p&Z:
                pass
            else:
                self._a(r.a & 0x0F)
                self._compare(r.a,0x02)
                self._mark(0xD606)
                if not r.p&Z:
                    pass
                else:
                    m[0x0000]=self._nz(m[0x0000]+1)
                    pass
                pass
            self._y(r.y+1)
            self._x(r.x+1)
            self._compare(r.x,0x0B)
            self._mark(0xD60F)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xD611)
            self._rts();return

    def side_object_position(self):
        """Original entry $D612; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD612)
        self._a(m[OBJECT_INDEX])
        self._push(r.a)
        self._a(m[0x057C])
        self._a(r.a ^ 0x01)
        m[OBJECT_INDEX]=r.a
        self._push(0xD6);self._push(0x20)
        yield from self.formation_probability_evaluation()
        if r.pc!=0xD621:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[OBJECT_INDEX]=r.a
        self._a(r.y)
        self._mark(0xD626)
        if not r.p&Z:
            self._mark(0xD631)
            self._rts();return
        else:
            self._a(0x64)
            yield from self._external(0xD62A,0xE862,0xD62D,"call",None)
            if r.pc!=0xD62D:return  # preserve nonlocal stack return
            self._compare(r.a,0x32)
            self._mark(0xD62F)
            if not r.p&C:
                self._y(m[0x057C])
                self._a(m[(0x0572+r.y)&65535])
                self._flag(C,True)
                self._add(0x03,subtract=True)
                m[(0x0572+r.y)&65535]=r.a
                yield from self._external(0xD63E,0xE87A,0xD641,"call",None)
                if r.pc!=0xD641:return  # preserve nonlocal stack return
                self._a(r.a & 0x01)
                self._mark(0xD643)
                if not r.p&Z:
                    self._mark(0xD631)
                    self._rts();return
                else:
                    self._a(self._pop())
                    self._a(self._pop())
                    self._a(0x0A)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xD651)
                    self._rts();return
            else:
                self._mark(0xD631)
                self._rts();return

    def prepare_selected_side_object(self):
        """Original entry $D652; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD652)
        self._a(m[0x0570])
        m[0x000A]=r.a
        self._a(m[0x0571])
        m[0x000B]=r.a
        self._a(m[OBJECT_VALUE])
        m[0x000C]=r.a
        self._a(m[0x05B7])
        m[0x000D]=r.a
        self._a(m[OBJECT_INDEX])
        self._mark(0xD66D)
        if r.p&Z:
            pass
        else:
            self._x(m[0x000A])
            self._a(m[0x000B])
            m[0x000A]=r.a
            m[0x000B]=r.x
            self._x(m[0x000C])
            self._a(m[0x000D])
            m[0x000C]=r.a
            m[0x000D]=r.x
            pass
        self._a(m[0x000A])
        self._compare(r.a,m[0x000B])
        self._mark(0xD68D)
        if not r.p&C:
            self._mark(0xD697)
            self._rts();return
        else:
            self._a(m[0x000C])
            self._compare(r.a,m[0x000D])
            self._mark(0xD695)
            if r.p&C:
                self._a(0x64)
                yield from self._external(0xD69A,0xE862,0xD69D,"call",None)
                if r.pc!=0xD69D:return  # preserve nonlocal stack return
                self._compare(r.a,0x28)
                self._mark(0xD69F)
                if r.p&C:
                    self._mark(0xD697)
                    self._rts();return
                else:
                    self._a(self._pop())
                    self._a(self._pop())
                    self._a(0x0A)
                    m[STATE]=r.a
                    self._a(0x04)
                    m[PHASE]=r.a
                    self._y(m[0x057C])
                    self._a(m[(0x0572+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x05,subtract=True)
                    m[(0x0572+r.y)&65535]=r.a
                    self._mark(0xD6B9)
                    self._rts();return
            else:
                self._mark(0xD697)
                self._rts();return

    def duel_selection(self):
        """Original entry $D6BA; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6BA)
        self._a(m[PHASE])
        return (yield from self.duel_selection_phase_dispatch())

    def duel_selection_phase_dispatch(self):
        """Original entry $D6BD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6BD)
        index=self._dispatch(0xD6BD,(54988, 55005, 55082, 55082, 55107, 55167))
        return (yield from (self.duel_selection_phase_0,self.duel_selection_phase_1,self.duel_selection_phase_3,self.duel_selection_phase_3,self.duel_selection_phase_4,self.duel_selection_phase_5,)[index]())

    def duel_selection_phase_0(self):
        """Original entry $D6CC; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6CC)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._a(0x7B)
        yield from self._external(0xD6D6,0xF26D,0xD6D9,"call",None)
        if r.pc!=0xD6D9:return  # preserve nonlocal stack return
        self._push(0xD6);self._push(0xDB)
        yield from self.prepare_intelligence_objects()
        if r.pc!=0xD6DC:return  # preserve nonlocal stack return
        self._mark(0xD6DC)
        self._rts();return

    def duel_selection_phase_1(self):
        """Original entry $D6DD; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD6DD)
        self._a(m[0x057C])
        self._push(r.a)
        self._a(r.a ^ 0x01)
        m[0x057C]=r.a
        self._push(0xD6);self._push(0xE8)
        yield from self.draw_other_participant_menu()
        if r.pc!=0xD6E9:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[0x057C]=r.a
        self._push(0xD6);self._push(0xEF)
        yield from self.active_side_controller_input()
        if r.pc!=0xD6F0:return  # preserve nonlocal stack return
        self._push(0xD6);self._push(0xF2)
        yield from self.text_readiness()
        if r.pc!=0xD6F3:return  # preserve nonlocal stack return
        self._mark(0xD6F3)
        if not r.p&C:
            pass
        else:
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xD6FA)
            if r.p&Z:
                pass
            else:
                self._a(0x03)
                m[STATE]=r.a
                self._a(0x03)
                m[PHASE]=r.a
                self._a(0x00)
                m[OBJECT_INDEX]=r.a
                m[ACTION_CLASS]=r.a
                self._a(0x01)
                m[SAVED_STATE]=r.a
                self._a(0x01)
                m[SAVED_PHASE]=r.a
                self._a(0xE8)
                m[0x0310]=r.a
                self._a(0xE9)
                m[0x0311]=r.a
                self._a(0x00)
                m[0x0300]=r.a
                self._push(0xD7);self._push(0x29)
                yield from self.build_participant_stats_packets()
                if r.pc!=0xD72A:return  # preserve nonlocal stack return
                pass
            pass
        return (yield from self.duel_selection_phase_3())

    def duel_selection_phase_3(self):
        """Original entry $D72A; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD72A)
        self._rts();return

    def draw_other_participant_menu(self):
        """Original entry $D72B; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD72B)
        self._y(m[0x057C])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x0000]=r.a
        self._a(0xA5)
        m[0x000A]=r.a
        self._x(0x00)
        self._y(0x39)
        yield from self._external(0xD73D,0xEE07,0xD742,"far_call",40960)
        if r.pc!=0xD742:return  # preserve nonlocal stack return
        self._mark(0xD742)
        self._rts();return

    def duel_selection_phase_4(self):
        """Original entry $D743; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD743)
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[SCAN_CURSOR]=r.a
        self._a(0x7C)
        yield from self._external(0xD74D,0xF26D,0xD750,"call",None)
        if r.pc!=0xD750:return  # preserve nonlocal stack return
        self._y(m[0x057C])
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x042C]=r.a
        self._a(0x09)
        m[0x00BB]=r.a
        self._a(m[0x057C])
        self._a(r.a ^ 0x01)
        self._y(r.a)
        self._a(m[(FIRST_OFFICER+r.y)&65535])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        self._y(0x3D)
        yield from self._external(0xD771,0xEE07,0xD776,"far_call",41020)
        if r.pc!=0xD776:return  # preserve nonlocal stack return
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xD77E)
        self._rts();return

    def duel_selection_phase_5(self):
        """Original entry $D77F; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD77F)
        self._a(m[0x057C])
        self._push(r.a)
        self._a(r.a ^ 0x01)
        m[0x057C]=r.a
        self._push(0xD7);self._push(0x8A)
        yield from self.draw_other_participant_menu()
        if r.pc!=0xD78B:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[0x057C]=r.a
        self._a(m[NEW_BUTTONS])
        self._push(r.a)
        self._push(0xD7);self._push(0x95)
        yield from self.active_side_controller_input()
        if r.pc!=0xD796:return  # preserve nonlocal stack return
        self._a(m[0x0001])
        m[NEW_BUTTONS]=r.a
        self._a(0xEE)
        m[0x0010]=r.a
        self._a(0xD7)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xD7AB,0xED1E,0xD7AE,"call",None)
        if r.pc!=0xD7AE:return  # preserve nonlocal stack return
        self._a(self._pop())
        m[NEW_BUTTONS]=r.a
        self._a(0xF2)
        m[0x0010]=r.a
        self._a(0xD7)
        m[0x0011]=r.a
        self._a(0xF6)
        m[0x0000]=r.a
        self._a(0xD7)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xD7C9,0xEDF5,0xD7CC,"call",None)
        if r.pc!=0xD7CC:return  # preserve nonlocal stack return
        self._push(0xD7);self._push(0xCE)
        yield from self.text_readiness()
        if r.pc!=0xD7CF:return  # preserve nonlocal stack return
        self._mark(0xD7CF)
        if not r.p&C:
            self._mark(0xD7ED)
            self._rts();return
        else:
            self._push(0xD7);self._push(0xD3)
            yield from self.active_side_controller_input()
            if r.pc!=0xD7D4:return  # preserve nonlocal stack return
            self._a(m[0x0001])
            self._a(r.a & 0x01)
            self._mark(0xD7D9)
            if r.p&Z:
                self._mark(0xD7ED)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xD7DE)
                if r.p&Z:
                    self._a(0x05)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xD7ED)
                    self._rts();return
                else:
                    self._a(0x03)
                    m[STATE]=r.a
                    self._a(0x03)
                    m[PHASE]=r.a
                    self._a(0x00)
                    m[OBJECT_INDEX]=r.a
                    m[ACTION_CLASS]=r.a
                    self._a(0x01)
                    m[SAVED_STATE]=r.a
                    self._a(0x01)
                    m[SAVED_PHASE]=r.a
                    self._a(0xE8)
                    m[0x0310]=r.a
                    self._a(0xE9)
                    m[0x0311]=r.a
                    self._a(0x00)
                    m[0x0300]=r.a
                    self._push(0xD7);self._push(0x29)
                    yield from self.build_participant_stats_packets()
                    if r.pc!=0xD72A:return  # preserve nonlocal stack return
                    return (yield from self.duel_selection_phase_3())

    def experience_level_code(self):
        """Original entry $D7FB; explicit software control body."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD7FB)
        self._a(m[0x000A])
        yield from self._external(0xD7FE,0xF2D7,0xD801,"call",None)
        if r.pc!=0xD801:return  # preserve nonlocal stack return
        m[0x000C]=self._shift(m[0x000C],False,rotate=False)
        m[0x000B]=self._shift(m[0x000B],False,rotate=True)
        self._y(0x06)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x000B])
        m[0x000D]=r.a
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(m[0x000C])
        m[0x000E]=r.a
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x06)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x4F,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(0xC3,subtract=True)
        self._mark(0xD82B)
        if not r.p&C:
            pass
        else:
            self._y(0x06)
            self._a(0x4F)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y+1)
            self._a(0xC3)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            pass
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._a(r.a & 0xF0)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._compare(r.a,0x0E)
        self._mark(0xD843)
        if r.p&C:
            self._a(0x00)
            m[0x000F]=r.a
            self._mark(0xD85A)
            self._rts();return
        else:
            self._y(r.a)
            self._a(m[0x000D])
            self._flag(C,True)
            self._add(m[(0xD85B+r.y)&65535],subtract=True)
            self._a(m[0x000E])
            self._add(m[(0xD85C+r.y)&65535],subtract=True)
            self._mark(0xD853)
            if r.p&C:
                self._a(r.y)
                r.a=self._shift(r.a,False,rotate=False)
                self._flag(C,False)
                self._add(0x01)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                m[0x000F]=r.a
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0xF0)
                self._compare(r.a,m[0x000F])
                self._mark(0xD87E)
                if r.p&C:
                    self._a(0x00)
                    m[0x000F]=r.a
                    self._mark(0xD85A)
                    self._rts();return
                else:
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x0F)
                    self._a(r.a | m[0x000F])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(0x01)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._y(0x06)
                    self._compare(r.a,0x33)
                    self._mark(0xD893)
                    if not r.p&C:
                        self._a(r.y)
                        self._y(0x01)
                        self._flag(C,False)
                        self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        pass
                    else:
                        self._y(0x05)
                        self._compare(r.a,0x47)
                        self._mark(0xD899)
                        if not r.p&C:
                            self._a(r.y)
                            self._y(0x01)
                            self._flag(C,False)
                            self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            pass
                        else:
                            self._y(0x04)
                            self._compare(r.a,0x51)
                            self._mark(0xD89F)
                            if not r.p&C:
                                self._a(r.y)
                                self._y(0x01)
                                self._flag(C,False)
                                self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                pass
                            else:
                                self._y(0x02)
                                self._compare(r.a,0x5A)
                                self._mark(0xD8A5)
                                if r.p&C:
                                    pass
                                else:
                                    self._a(r.y)
                                    self._y(0x01)
                                    self._flag(C,False)
                                    self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    pass
                                pass
                            pass
                        pass
                    self._mark(0xD8AF)
                    self._rts();return
            else:
                self._a(0x00)
                m[0x000F]=r.a
                self._mark(0xD85A)
                self._rts();return

