"""Readable, bounded bank27/28 city menu controller.

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
STATE=0x400
PHASE=0x401
CITY=0x402
OFFICER_LIST=0x410
OFFICER_INDEX=0x40C
DETAIL_ROW=0x40D
WORLD_CURSOR=0x470
CURRENT_CITY=0x471
NEW_BUTTONS=0x81
REPEAT_BUTTONS=0x87
GLOBAL=0x7A
NMI_SCENE=0x78
PPU_JOBS=0x7E
ACTOR_SLOT=OFFICER_INDEX

@dataclass
class CityRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA000

class CityUIController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original city ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=CityRegisters();self.events=[];self.pending=None;self._program=None
        self._blocks=0;self._limit=200000;self._call_owner=None
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
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA000,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        if registers is None:raise ValueError('Supply actual caller registers and an existing RTS frame')
        self.registers=registers;r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(27,28) or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No city body owns this exact pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns pending city update'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

    LOCAL_ENTRIES=(40960, 40963, 40966, 40969, 40972, 40991, 41029, 41037, 41045, 41053, 41061, 41069, 41077, 41085, 41097, 41183, 41261, 41313, 41337, 41355, 41365, 41424, 41621, 41673, 41721, 41830, 41933, 42097, 42245, 42352, 42640, 42732, 42876, 42954, 43044, 43137, 43183, 43234, 43515, 43657, 43756, 43982, 44032, 44074, 44156, 44176, 44216, 44353, 44530, 44586, 44629, 44818, 44974, 45127, 45263, 45456, 45595, 45635, 45688, 45884, 45933, 46094, 46129, 46173, 46202, 46343, 46376, 46482, 46502, 46556, 46624, 46704, 46833, 46910, 46937, 46975, 47015, 47134, 47255, 47486, 47620, 47822, 47997, 48070, 48358, 48487, 48665, 48901, 48921, 48964, 49001, 49033, 49056, 49079, 49133, 49229, 49462, 49601, 49861, 49977, 50080, 50196, 50282, 50344, 50453, 50503, 50575, 50647, 50815, 50936, 50963, 50977, 51012, 51054, 51231, 51466, 51666, 51695, 51819, 51935, 51977, 52223, 52354, 52556, 52617, 52878, 52909, 52983, 53022, 53133, 53220, 53279, 53480, 53500, 53567, 53647, 53689, 53820, 53987, 54213, 54299, 54386, 54509, 54536, 54595, 54632, 54668, 54717, 54858, 55155, 55208, 55630, 55663, 55687, 55810, 55812, 56073, 56117, 56178, 56199, 56217, 56427, 56444, 56528, 56655, 56662, 56670, 56688, 56697, 56749, 56767, 56796, 56818, 56963, 57018, 57141, 57186)
    def _entry(self,entry):
        if entry==0xA000:return self.city_scene_entry()
        elif entry==0xA003:return self.city_context_entry()
        elif entry==0xA006:return self.city_setup_entry()
        elif entry==0xA009:return self.city_state_entry()
        elif entry==0xA00C:return self.city_scene_tick()
        elif entry==0xA01F:return self.city_main_dispatch()
        elif entry==0xA045:return self.city_helper_a045()
        elif entry==0xA04D:return self.city_helper_a04d()
        elif entry==0xA055:return self.city_helper_a055()
        elif entry==0xA05D:return self.city_helper_a05d()
        elif entry==0xA065:return self.city_helper_a065()
        elif entry==0xA06D:return self.city_helper_a06d()
        elif entry==0xA075:return self.city_helper_a075()
        elif entry==0xA07D:return self.world_map_selection()
        elif entry==0xA089:return self.prepare_world_map_selection()
        elif entry==0xA0DF:return self.navigate_world_map_selection()
        elif entry==0xA12D:return self.request_city_information()
        elif entry==0xA161:return self.request_system_menu()
        elif entry==0xA179:return self.await_world_selection_text()
        elif entry==0xA18B:return self.command_bar()
        elif entry==0xA195:return self.prepare_command_bar()
        elif entry==0xA1D0:return self.navigate_command_bar()
        elif entry==0xA295:return self.domestic_commands()
        elif entry==0xA2C9:return self.city_helper_a2c9()
        elif entry==0xA2F9:return self.city_helper_a2f9()
        elif entry==0xA366:return self.city_helper_a366()
        elif entry==0xA3CD:return self.city_helper_a3cd()
        elif entry==0xA471:return self.city_helper_a471()
        elif entry==0xA505:return self.city_helper_a505()
        elif entry==0xA570:return self.city_helper_a570()
        elif entry==0xA690:return self.city_helper_a690()
        elif entry==0xA6EC:return self.city_helper_a6ec()
        elif entry==0xA77C:return self.city_helper_a77c()
        elif entry==0xA7CA:return self.city_helper_a7ca()
        elif entry==0xA824:return self.city_helper_a824()
        elif entry==0xA881:return self.city_helper_a881()
        elif entry==0xA8AF:return self.city_helper_a8af()
        elif entry==0xA8E2:return self.city_helper_a8e2()
        elif entry==0xA9FB:return self.city_helper_a9fb()
        elif entry==0xAA89:return self.city_helper_aa89()
        elif entry==0xAAEC:return self.city_helper_aaec()
        elif entry==0xABCE:return self.city_helper_abce()
        elif entry==0xAC00:return self.city_helper_ac00()
        elif entry==0xAC2A:return self.city_helper_ac2a()
        elif entry==0xAC7C:return self.city_helper_ac7c()
        elif entry==0xAC90:return self.city_helper_ac90()
        elif entry==0xACB8:return self.city_helper_acb8()
        elif entry==0xAD41:return self.transfer_selected_officers()
        elif entry==0xADF2:return self.military_commands()
        elif entry==0xAE2A:return self.city_helper_ae2a()
        elif entry==0xAE55:return self.city_helper_ae55()
        elif entry==0xAF12:return self.city_helper_af12()
        elif entry==0xAFAE:return self.city_helper_afae()
        elif entry==0xB047:return self.city_helper_b047()
        elif entry==0xB0CF:return self.city_helper_b0cf()
        elif entry==0xB190:return self.city_helper_b190()
        elif entry==0xB21B:return self.city_helper_b21b()
        elif entry==0xB243:return self.city_helper_b243()
        elif entry==0xB278:return self.city_helper_b278()
        elif entry==0xB33C:return self.city_helper_b33c()
        elif entry==0xB36D:return self.city_helper_b36d()
        elif entry==0xB40E:return self.city_helper_b40e()
        elif entry==0xB431:return self.city_helper_b431()
        elif entry==0xB45D:return self.city_helper_b45d()
        elif entry==0xB47A:return self.city_helper_b47a()
        elif entry==0xB507:return self.city_helper_b507()
        elif entry==0xB528:return self.city_helper_b528()
        elif entry==0xB592:return self.city_helper_b592()
        elif entry==0xB5A6:return self.city_helper_b5a6()
        elif entry==0xB5DC:return self.city_helper_b5dc()
        elif entry==0xB620:return self.city_helper_b620()
        elif entry==0xB670:return self.city_helper_b670()
        elif entry==0xB6F1:return self.city_helper_b6f1()
        elif entry==0xB73E:return self.city_helper_b73e()
        elif entry==0xB759:return self.resource_commands()
        elif entry==0xB77F:return self.city_helper_b77f()
        elif entry==0xB7A7:return self.city_helper_b7a7()
        elif entry==0xB81E:return self.city_helper_b81e()
        elif entry==0xB897:return self.city_helper_b897()
        elif entry==0xB97E:return self.city_helper_b97e()
        elif entry==0xBA04:return self.city_helper_ba04()
        elif entry==0xBACE:return self.city_helper_bace()
        elif entry==0xBB7D:return self.city_helper_bb7d()
        elif entry==0xBBC6:return self.city_helper_bbc6()
        elif entry==0xBCE6:return self.city_helper_bce6()
        elif entry==0xBD67:return self.city_helper_bd67()
        elif entry==0xBE19:return self.city_helper_be19()
        elif entry==0xBF05:return self.city_helper_bf05()
        elif entry==0xBF19:return self.city_helper_bf19()
        elif entry==0xBF44:return self.city_helper_bf44()
        elif entry==0xBF69:return self.city_helper_bf69()
        elif entry==0xBF89:return self.city_helper_bf89()
        elif entry==0xBFA0:return self.city_helper_bfa0()
        elif entry==0xBFB7:return self.city_helper_bfb7()
        elif entry==0xBFED:return self.city_helper_bfed()
        elif entry==0xC04D:return self.city_helper_c04d()
        elif entry==0xC136:return self.city_helper_c136()
        elif entry==0xC1C1:return self.city_helper_c1c1()
        elif entry==0xC2C5:return self.city_helper_c2c5()
        elif entry==0xC339:return self.city_helper_c339()
        elif entry==0xC3A0:return self.city_helper_c3a0()
        elif entry==0xC414:return self.city_helper_c414()
        elif entry==0xC46A:return self.city_helper_c46a()
        elif entry==0xC4A8:return self.city_helper_c4a8()
        elif entry==0xC515:return self.city_helper_c515()
        elif entry==0xC547:return self.city_helper_c547()
        elif entry==0xC58F:return self.city_helper_c58f()
        elif entry==0xC5D7:return self.city_helper_c5d7()
        elif entry==0xC67F:return self.city_helper_c67f()
        elif entry==0xC6F8:return self.city_helper_c6f8()
        elif entry==0xC713:return self.city_helper_c713()
        elif entry==0xC721:return self.city_helper_c721()
        elif entry==0xC744:return self.city_helper_c744()
        elif entry==0xC76E:return self.city_helper_c76e()
        elif entry==0xC81F:return self.queue_equipment_icons()
        elif entry==0xC90A:return self.city_helper_c90a()
        elif entry==0xC9D2:return self.city_helper_c9d2()
        elif entry==0xC9EF:return self.city_helper_c9ef()
        elif entry==0xCA6B:return self.city_helper_ca6b()
        elif entry==0xCADF:return self.city_helper_cadf()
        elif entry==0xCB09:return self.city_helper_cb09()
        elif entry==0xCBFF:return self.city_helper_cbff()
        elif entry==0xCC82:return self.city_helper_cc82()
        elif entry==0xCD4C:return self.city_helper_cd4c()
        elif entry==0xCD89:return self.city_helper_cd89()
        elif entry==0xCE8E:return self.city_helper_ce8e()
        elif entry==0xCEAD:return self.city_helper_cead()
        elif entry==0xCEF7:return self.city_helper_cef7()
        elif entry==0xCF1E:return self.city_helper_cf1e()
        elif entry==0xCF8D:return self.city_helper_cf8d()
        elif entry==0xCFE4:return self.city_helper_cfe4()
        elif entry==0xD01F:return self.city_helper_d01f()
        elif entry==0xD0E8:return self.city_helper_d0e8()
        elif entry==0xD0FC:return self.city_helper_d0fc()
        elif entry==0xD13F:return self.city_helper_d13f()
        elif entry==0xD18F:return self.city_helper_d18f()
        elif entry==0xD1B9:return self.city_helper_d1b9()
        elif entry==0xD23C:return self.city_helper_d23c()
        elif entry==0xD2E3:return self.city_helper_d2e3()
        elif entry==0xD3C5:return self.city_helper_d3c5()
        elif entry==0xD41B:return self.city_helper_d41b()
        elif entry==0xD472:return self.city_helper_d472()
        elif entry==0xD4ED:return self.city_helper_d4ed()
        elif entry==0xD508:return self.city_helper_d508()
        elif entry==0xD543:return self.city_helper_d543()
        elif entry==0xD568:return self.city_helper_d568()
        elif entry==0xD58C:return self.city_helper_d58c()
        elif entry==0xD5BD:return self.city_helper_d5bd()
        elif entry==0xD64A:return self.city_helper_d64a()
        elif entry==0xD773:return self.city_helper_d773()
        elif entry==0xD7A8:return self.city_helper_d7a8()
        elif entry==0xD94E:return self.city_helper_d94e()
        elif entry==0xD96F:return self.city_helper_d96f()
        elif entry==0xD987:return self.city_helper_d987()
        elif entry==0xDA02:return self.city_helper_da02()
        elif entry==0xDA04:return self.city_helper_da04()
        elif entry==0xDB09:return self.city_helper_db09()
        elif entry==0xDB35:return self.city_helper_db35()
        elif entry==0xDB72:return self.city_helper_db72()
        elif entry==0xDB87:return self.city_helper_db87()
        elif entry==0xDB99:return self.city_helper_db99()
        elif entry==0xDC6B:return self.city_helper_dc6b()
        elif entry==0xDC7C:return self.city_helper_dc7c()
        elif entry==0xDCD0:return self.city_helper_dcd0()
        elif entry==0xDD4F:return self.city_helper_dd4f()
        elif entry==0xDD56:return self.city_helper_dd56()
        elif entry==0xDD5E:return self.city_helper_dd5e()
        elif entry==0xDD70:return self.city_helper_dd70()
        elif entry==0xDD79:return self.city_helper_dd79()
        elif entry==0xDDAD:return self.text_request_readiness()
        elif entry==0xDDBF:return self.city_helper_ddbf()
        elif entry==0xDDDC:return self.city_helper_dddc()
        elif entry==0xDDF2:return self.world_selection_portrait()
        elif entry==0xDE83:return self.update_cursor_repeat()
        elif entry==0xDEBA:return self.city_at_cursor()
        elif entry==0xDF35:return self.city_callback_preparation()
        elif entry==0xDF62:return self.city_helper_df62()
        raise ValueError("Entry outside original city menu closure")

    def city_scene_entry(self):
        """$A000: city scene entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA000)
        return (yield from self.city_scene_tick())

    def city_context_entry(self):
        """$A003: city context entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.city_helper_da02())

    def city_setup_entry(self):
        """$A006: city setup entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA006)
        return (yield from self.city_helper_d64a())

    def city_state_entry(self):
        """$A009: city state entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA009)
        self._y(m[0x000A])
        self._a(m[(0xDEE9+r.y)&65535])
        m[0x000B]=r.a
        self._a(m[(0xDF07+r.y)&65535])
        m[0x000C]=r.a
        self._mark(0xDF34)
        self._rts();return

    def city_scene_tick(self):
        """$A00C: city scene tick; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA00C)
        if not (yield from self._local_call(self.update_cursor_repeat,0xA00C,0xA00F)):return
        if not (yield from self._local_call(self.city_callback_preparation,0xA00F,0xA012)):return
        self._y(0x39)
        yield from self._external(0xA014,0xEE07,0xA019,"far_call",41002)
        if r.pc!=0xA019:return  # preserve nonlocal stack return
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xA01C)
        if r.p&N:
            return (yield from self.city_main_dispatch())
        else:
            self._mark(0xA01E)
            self._rts();return

    def city_main_dispatch(self):
        """$A01F: city main dispatch; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA01F)
        self._a(m[STATE])
        self._mark(0xA022)
        index=self._dispatch(0xA022,(41085, 41355, 41621, 44530, 46937, 49079, 51935, 41085, 41085, 41045, 41053, 41029, 41037, 41061, 41069, 41077))
        return (yield from (self.world_map_selection,self.command_bar,self.domestic_commands,self.military_commands,self.resource_commands,self.city_helper_bfb7,self.city_helper_cadf,self.world_map_selection,self.world_map_selection,self.city_helper_a055,self.city_helper_a05d,self.city_helper_a045,self.city_helper_a04d,self.city_helper_a065,self.city_helper_a06d,self.city_helper_a075,)[index]())

    def city_helper_a045(self):
        """$A045: city helper a045; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA045)
        self._y(0x39)
        yield from self._external(0xA047,0xEE07,0xA04C,"far_call",40963)
        if r.pc!=0xA04C:return  # preserve nonlocal stack return
        self._mark(0xA04C)
        self._rts();return

    def city_helper_a04d(self):
        """$A04D: city helper a04d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA04D)
        self._y(0x39)
        yield from self._external(0xA04F,0xEE07,0xA054,"far_call",40993)
        if r.pc!=0xA054:return  # preserve nonlocal stack return
        self._mark(0xA054)
        self._rts();return

    def city_helper_a055(self):
        """$A055: city helper a055; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA055)
        self._y(0x39)
        yield from self._external(0xA057,0xEE07,0xA05C,"far_call",40966)
        if r.pc!=0xA05C:return  # preserve nonlocal stack return
        self._mark(0xA05C)
        self._rts();return

    def city_helper_a05d(self):
        """$A05D: city helper a05d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA05D)
        self._y(0x39)
        yield from self._external(0xA05F,0xEE07,0xA064,"far_call",40969)
        if r.pc!=0xA064:return  # preserve nonlocal stack return
        self._mark(0xA064)
        self._rts();return

    def city_helper_a065(self):
        """$A065: city helper a065; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA065)
        self._y(0x39)
        yield from self._external(0xA067,0xEE07,0xA06C,"far_call",40972)
        if r.pc!=0xA06C:return  # preserve nonlocal stack return
        self._mark(0xA06C)
        self._rts();return

    def city_helper_a06d(self):
        """$A06D: city helper a06d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA06D)
        self._y(0x3D)
        yield from self._external(0xA06F,0xEE07,0xA074,"far_call",41017)
        if r.pc!=0xA074:return  # preserve nonlocal stack return
        self._mark(0xA074)
        self._rts();return

    def city_helper_a075(self):
        """$A075: city helper a075; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA075)
        self._y(0x39)
        yield from self._external(0xA077,0xEE07,0xA07C,"far_call",40990)
        if r.pc!=0xA07C:return  # preserve nonlocal stack return
        self._mark(0xA07C)
        self._rts();return

    def world_map_selection(self):
        """$A07D: world map selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA07D)
        self._a(m[PHASE])
        self._mark(0xA080)
        index=self._dispatch(0xA080,(41097, 41183, 41337))
        return (yield from (self.prepare_world_map_selection,self.navigate_world_map_selection,self.await_world_selection_text,)[index]())

    def prepare_world_map_selection(self):
        """$A089: prepare world map selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA089)
        self._a(0x00)
        m[WORLD_CURSOR]=r.a
        m[CURRENT_CITY]=r.a
        m[0x0472]=r.a
        m[0x00A4]=r.a
        m[0x04E4]=r.a
        self._a(m[0x6F03])
        m[0x0010]=r.a
        if not (yield from self._local_call(self.city_helper_ddbf,0xA0A0,0xA0A3)):return
        self._a(m[0x0011])
        self._compare(r.a,0x1E)
        self._mark(0xA0A8)
        if not r.p&Z:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(m[0x6F05])
            self._mark(0xA0B6)
            if r.p&N:
                self._a(0x0B)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xA0C4)
                yield from self._external(0xA0C4,0xF28B,None,"tail")
                return
            else:
                self._mark(0xA0B8)
                if not r.p&Z:
                    self._y(0x00)
                    self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                    m[0x042C]=r.a
                    m[0x0430]=r.y
                    m[0x0431]=r.y
                    self._a(m[0x6F05])
                    m[0x042F]=r.a
                    self._a(0x1F)
                    self._mark(0xA0DC)
                    yield from self._external(0xA0DC,0xF26D,None,"tail")
                    return
                else:
                    self._a(0x0B)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA0C4)
                    yield from self._external(0xA0C4,0xF28B,None,"tail")
                    return
        else:
            self._a(0x0F)
            m[STATE]=r.a
            self._mark(0xA0AF)
            self._rts();return

    def navigate_world_map_selection(self):
        """$A0DF: navigate world map selection; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA0DF)
        if not (yield from self._local_call(self.world_selection_portrait,0xA0DF,0xA0E2)):return
        self._y(0x3D)
        yield from self._external(0xA0E4,0xEE07,0xA0E9,"far_call",40993)
        if r.pc!=0xA0E9:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xA0E9,0xA0EC)):return
        self._mark(0xA0EC)
        if not r.p&C:
            self._mark(0xA12C)
            self._rts();return
        else:
            if not (yield from self._local_call(self.request_city_information,0xA0EE,0xA0F1)):return
            if not (yield from self._local_call(self.request_system_menu,0xA0F1,0xA0F4)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xA0F9)
            if r.p&Z:
                self._mark(0xA12C)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_at_cursor,0xA0FB,0xA0FE)):return
                self._compare(r.y,0xFF)
                self._mark(0xA100)
                if r.p&Z:
                    self._a(0x21)
                    self._mark(0xA124)
                    yield from self._external(0xA124,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    self._a(r.y)
                    yield from self._external(0xA106,0xF2AF,0xA109,"call",None)
                    if r.pc!=0xA109:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    self._compare(r.a,m[0x6F03])
                    self._mark(0xA112)
                    if not r.p&Z:
                        self._a(0x22)
                        self._mark(0xA129)
                        yield from self._external(0xA129,0xF26D,None,"tail")
                        return
                    else:
                        self._a(0xFF)
                        m[0x04E4]=r.a
                        m[STATE]=self._nz(m[STATE]+1)
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xA121)
                        self._rts();return

    def request_city_information(self):
        """$A12D: request city information; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA12D)
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x02)
        self._mark(0xA132)
        if r.p&Z:
            self._mark(0xA160)
            self._rts();return
        else:
            self._a(0x00)
            m[NEW_BUTTONS]=r.a
            if not (yield from self._local_call(self.city_at_cursor,0xA139,0xA13C)):return
            self._compare(r.y,0xFF)
            self._mark(0xA13E)
            if r.p&Z:
                self._mark(0xA160)
                self._rts();return
            else:
                m[CITY]=r.y
                self._a(r.y)
                yield from self._external(0xA144,0xF2AF,0xA147,"call",None)
                if r.pc!=0xA147:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._compare(r.a,m[0x6F03])
                self._mark(0xA150)
                if not r.p&Z:
                    self._mark(0xA160)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[WORLD_CURSOR]=r.a
                    m[CURRENT_CITY]=r.a
                    self._mark(0xA15D)
                    yield from self._external(0xA15D,0xF28B,None,"tail")
                    return

    def request_system_menu(self):
        """$A161: request system menu; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA161)
        self._a(m[NEW_BUTTONS])
        self._a(r.a | m[0x0082])
        self._a(r.a & 0x04)
        self._mark(0xA169)
        if r.p&Z:
            pass
        else:
            self._a(0x00)
            m[NEW_BUTTONS]=r.a
            self._a(0x0E)
            m[STATE]=r.a
            m[PHASE]=self._nz(m[PHASE]-1)
            pass
        self._mark(0xA178)
        self._rts();return

    def await_world_selection_text(self):
        """$A179: await world selection text; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA179)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xA17E)
        if not r.p&Z:
            pass
        else:
            self._a(0x0C)
            m[STATE]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            pass
        self._mark(0xA18A)
        self._rts();return

    def command_bar(self):
        """$A18B: command bar; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA18B)
        self._a(m[PHASE])
        self._mark(0xA18E)
        index=self._dispatch(0xA18E,(41365, 41424))
        return (yield from (self.prepare_command_bar,self.navigate_command_bar,)[index]())

    def prepare_command_bar(self):
        """$A195: prepare command bar; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA195)
        self._a(m[0x0140])
        self._mark(0xA198)
        if not r.p&Z:
            self._mark(0xA1CF)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA19F)
            if not r.p&Z:
                self._mark(0xA1CF)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xA1A4,0xA1A7)):return
                m[WORLD_CURSOR]=r.a
                self._a(0x01)
                m[CURRENT_CITY]=r.a
                m[0x00B3]=r.a
                self._a(0x0C)
                m[0x00BD]=r.a
                self._y(0x80)
                m[0x0140]=r.y
                self._x(0x01)
                self._a(m[0x6F3F])
                self._mark(0xA1C1)
                if r.p&N:
                    pass
                else:
                    self._x(0x81)
                    self._y(0x40)
                    pass
                m[0x0150]=r.x
                self._a(0x23)
                self._mark(0xA1CC)
                yield from self._external(0xA1CC,0xF26D,None,"tail")
                return

    def navigate_command_bar(self):
        """$A1D0: navigate command bar; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA1D0)
        self._a(0x44)
        m[0x0010]=r.a
        self._a(0xA2)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA1DF,0xED28,0xA1E2,"call",None)
        if r.pc!=0xA1E2:return  # preserve nonlocal stack return
        self._a(0x4C)
        m[0x0010]=r.a
        self._a(0xA2)
        m[0x0011]=r.a
        self._a(0x54)
        m[0x0000]=r.a
        self._a(0xA2)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA1F9,0xEDF5,0xA1FC,"call",None)
        if r.pc!=0xA1FC:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xA1FC,0xA1FF)):return
        self._mark(0xA1FF)
        if not r.p&C:
            self._mark(0xA243)
            self._rts();return
        else:
            self._a(m[WORLD_CURSOR])
            self._mark(0xA204)
            if r.p&Z:
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x30)
                self._mark(0xA20E)
                if not r.p&Z:
                    self._a(m[0x0140])
                    self._mark(0xA25C)
                    if not r.p&Z:
                        self._mark(0xA243)
                        self._rts();return
                    else:
                        self._a(m[WORLD_CURSOR])
                        self._mark(0xA261)
                        if r.p&N:
                            self._a(0x00)
                            m[WORLD_CURSOR]=r.a
                            self._mark(0xA272)
                            self._rts();return
                        else:
                            self._mark(0xA263)
                            if r.p&Z:
                                self._a(0x80)
                                m[0x0140]=r.a
                                m[WORLD_CURSOR]=self._nz(m[WORLD_CURSOR]+1)
                                self._mark(0xA27B)
                                self._rts();return
                            else:
                                self._compare(r.a,0x0A)
                                self._mark(0xA267)
                                if r.p&Z:
                                    self._a(0x80)
                                    m[0x0140]=r.a
                                    self._a(m[CURRENT_CITY])
                                    self._a(r.a ^ 0x03)
                                    m[CURRENT_CITY]=r.a
                                    self._a(r.a | m[0x0150])
                                    m[0x0150]=r.a
                                    self._a(0x80)
                                    m[WORLD_CURSOR]=r.a
                                    self._mark(0xA294)
                                    self._rts();return
                                else:
                                    m[WORLD_CURSOR]=self._nz(m[WORLD_CURSOR]+1)
                                    self._mark(0xA26C)
                                    self._rts();return
                else:
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xA214)
                    if not r.p&C:
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xA22C)
                        if not r.p&C:
                            pass
                        else:
                            self._a(0x00)
                            m[STATE]=r.a
                            m[PHASE]=r.a
                            self._a(0x80)
                            m[0x0140]=r.a
                            self._a(m[0x0150])
                            self._a(r.a | 0x00)
                            m[0x0150]=r.a
                            pass
                        self._mark(0xA243)
                        self._rts();return
                    else:
                        self._y(m[0x0012])
                        self._y(r.y+1)
                        self._y(r.y+1)
                        m[STATE]=r.y
                        self._a(0x80)
                        m[0x0140]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xA228)
                        yield from self._external(0xA228,0xF26D,None,"tail")
                        return
            else:
                self._a(m[0x0140])
                self._mark(0xA25C)
                if not r.p&Z:
                    self._mark(0xA243)
                    self._rts();return
                else:
                    self._a(m[WORLD_CURSOR])
                    self._mark(0xA261)
                    if r.p&N:
                        self._a(0x00)
                        m[WORLD_CURSOR]=r.a
                        self._mark(0xA272)
                        self._rts();return
                    else:
                        self._mark(0xA263)
                        if r.p&Z:
                            self._a(0x80)
                            m[0x0140]=r.a
                            m[WORLD_CURSOR]=self._nz(m[WORLD_CURSOR]+1)
                            self._mark(0xA27B)
                            self._rts();return
                        else:
                            self._compare(r.a,0x0A)
                            self._mark(0xA267)
                            if r.p&Z:
                                self._a(0x80)
                                m[0x0140]=r.a
                                self._a(m[CURRENT_CITY])
                                self._a(r.a ^ 0x03)
                                m[CURRENT_CITY]=r.a
                                self._a(r.a | m[0x0150])
                                m[0x0150]=r.a
                                self._a(0x80)
                                m[WORLD_CURSOR]=r.a
                                self._mark(0xA294)
                                self._rts();return
                            else:
                                m[WORLD_CURSOR]=self._nz(m[WORLD_CURSOR]+1)
                                self._mark(0xA26C)
                                self._rts();return

    def domestic_commands(self):
        """$A295: domestic commands; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA295)
        self._a(m[PHASE])
        self._mark(0xA298)
        index=self._dispatch(0xA298,(41673, 41721, 41830, 41933, 42097, 42245, 42352, 42732, 42876, 42954, 43044, 43137, 43183, 43234, 43515, 43657, 43756, 43982, 44032, 44074, 44156, 44176, 44216))
        return (yield from (self.city_helper_a2c9,self.city_helper_a2f9,self.city_helper_a366,self.city_helper_a3cd,self.city_helper_a471,self.city_helper_a505,self.city_helper_a570,self.city_helper_a6ec,self.city_helper_a77c,self.city_helper_a7ca,self.city_helper_a824,self.city_helper_a881,self.city_helper_a8af,self.city_helper_a8e2,self.city_helper_a9fb,self.city_helper_aa89,self.city_helper_aaec,self.city_helper_abce,self.city_helper_ac00,self.city_helper_ac2a,self.city_helper_ac7c,self.city_helper_ac90,self.city_helper_acb8,)[index]())

    def city_helper_a2c9(self):
        """$A2C9: city helper a2c9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2C9)
        self._a(m[0x0140])
        self._mark(0xA2CC)
        if not r.p&Z:
            self._mark(0xA2F8)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xA2D3)
            if not r.p&Z:
                self._mark(0xA2F8)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xA2D8,0xA2DB)):return
                m[0x0473]=r.a
                m[0x00A4]=r.a
                self._a(0xFF)
                m[0x0481]=r.a
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x02)
                self._a(r.a | m[0x0150])
                m[0x0150]=r.a
                self._a(0x25)
                self._mark(0xA2F5)
                yield from self._external(0xA2F5,0xF26D,None,"tail")
                return

    def city_helper_a2f9(self):
        """$A2F9: city helper a2f9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA2F9)
        self._a(0x4D)
        m[0x0010]=r.a
        self._a(0xA3)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA308,0xED1E,0xA30B,"call",None)
        if r.pc!=0xA30B:return  # preserve nonlocal stack return
        self._a(0x55)
        m[0x0010]=r.a
        self._a(0xA3)
        m[0x0011]=r.a
        self._a(0x61)
        m[0x0000]=r.a
        self._a(0xA3)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA322,0xEDF5,0xA325,"call",None)
        if r.pc!=0xA325:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xA325,0xA328)):return
        self._mark(0xA328)
        if not r.p&C:
            self._mark(0xA34C)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA32E)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA33D)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xA33F,0xA342)):return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xA34C)
                self._rts();return
            else:
                self._a(m[0x0012])
                m[WORLD_CURSOR]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                return (yield from self.city_helper_dd70())

    def city_helper_a366(self):
        """$A366: city helper a366; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA366)
        self._a(m[WORLD_CURSOR])
        self._mark(0xA369)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xA375)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xA38C)
                if not r.p&Z:
                    self._compare(r.a,0x03)
                    self._mark(0xA3A4)
                    if not r.p&Z:
                        self._compare(r.a,0x04)
                        self._mark(0xA3B2)
                        if not r.p&Z:
                            self._a(0x12)
                            m[PHASE]=r.a
                            self._a(0x51)
                            self._mark(0xA3CA)
                            yield from self._external(0xA3CA,0xF26D,None,"tail")
                            return
                        else:
                            self._a(0x06)
                            m[STATE]=r.a
                            self._a(0x00)
                            m[PHASE]=r.a
                            self._a(0x3B)
                            self._mark(0xA3C0)
                            yield from self._external(0xA3C0,0xF26D,None,"tail")
                            return
                    else:
                        self._a(0x11)
                        m[PHASE]=r.a
                        self._a(0x4F)
                        self._mark(0xA3AD)
                        yield from self._external(0xA3AD,0xF26D,None,"tail")
                        return
                else:
                    self._a(0x0B)
                    m[PHASE]=r.a
                    self._a(0x80)
                    m[0x0478]=r.a
                    self._a(0x0F)
                    m[0x047C]=r.a
                    self._a(0x27)
                    self._mark(0xA39F)
                    yield from self._external(0xA39F,0xF26D,None,"tail")
                    return
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xA377,0xA37A)):return
                self._a(m[CITY])
                m[WORLD_CURSOR]=r.a
                self._a(0x07)
                m[PHASE]=r.a
                self._a(0x2E)
                self._mark(0xA387)
                yield from self._external(0xA387,0xF26D,None,"tail")
                return
        else:
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x26)
            self._mark(0xA370)
            yield from self._external(0xA370,0xF26D,None,"tail")
            return

    def city_helper_a3cd(self):
        """$A3CD: city helper a3cd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA3CD)
        self._a(0x5F)
        m[0x0010]=r.a
        self._a(0xA4)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA3DC,0xED19,0xA3DF,"call",None)
        if r.pc!=0xA3DF:return  # preserve nonlocal stack return
        self._a(0x63)
        m[0x0010]=r.a
        self._a(0xA4)
        m[0x0011]=r.a
        self._a(0x69)
        m[0x0000]=r.a
        self._a(0xA4)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA3F6,0xEDF5,0xA3F9,"call",None)
        if r.pc!=0xA3F9:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xA3F9,0xA3FC)):return
        self._mark(0xA3FC)
        if not r.p&C:
            self._mark(0xA40C)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA402)
            if r.p&C:
                self._a(m[CITY])
                yield from self._external(0xA410,0xF2AF,0xA413,"call",None)
                if r.pc!=0xA413:return  # preserve nonlocal stack return
                self._a(0xE7)
                m[0x0010]=r.a
                self._a(0x03)
                m[0x0011]=r.a
                self._y(m[0x0012])
                m[WORLD_CURSOR]=r.y
                self._compare(r.y,0x02)
                self._mark(0xA425)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x0F)
                    m[0x0010]=r.a
                    self._a(0x27)
                    m[0x0011]=r.a
                    pass
                self._a(m[(0xA46E+r.y)&65535])
                self._y(r.a)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x0010],subtract=True)
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0011],subtract=True)
                self._mark(0xA441)
                if not r.p&C:
                    self._a(0x80)
                    m[0x0478]=r.a
                    self._a(0x0F)
                    m[0x047C]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x27)
                    self._mark(0xA45C)
                    yield from self._external(0xA45C,0xF26D,None,"tail")
                    return
                else:
                    self._a(0x16)
                    m[PHASE]=r.a
                    self._a(0xA7)
                    self._mark(0xA44A)
                    yield from self._external(0xA44A,0xF26D,None,"tail")
                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA405)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xA40C)
                self._rts();return

    def city_helper_a471(self):
        """$A471: city helper a471; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA471)
        self._a(m[0x0478])
        self._mark(0xA474)
        if not r.p&Z:
            self._mark(0xA49C)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xA476,0xA479)):return
            self._a(m[0x047C])
            self._mark(0xA47C)
            if not r.p&N:
                self._mark(0xA49C)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xA480)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xA49D,0xA4A0)):return
                    self._a(m[0x0481])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xA4A8,0xEE07,0xA4AD,"far_call",41002)
                    if r.pc!=0xA4AD:return  # preserve nonlocal stack return
                    self._a(m[0x0481])
                    yield from self._external(0xA4B0,0xF2D7,0xA4B3,"call",None)
                    if r.pc!=0xA4B3:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0482]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x03)
                    self._mark(0xA4C2)
                    if r.p&Z:
                        yield from self._external(0xA4D1,0xE850,0xA4D4,"call",None)
                        if r.pc!=0xA4D4:return  # preserve nonlocal stack return
                        m[0x0472]=r.a
                        self._a(m[0x0482])
                        self._compare(r.a,0x51)
                        self._mark(0xA4DC)
                        if not r.p&C:
                            self._compare(r.a,0x33)
                            self._mark(0xA4E5)
                            if not r.p&C:
                                self._a(0x0A)
                                pass
                            else:
                                self._a(0x0D)
                                pass
                            pass
                        else:
                            self._a(0x10)
                            pass
                        self._flag(C,False)
                        self._add(m[0x0472])
                        m[0x0472]=r.a
                        m[0x042C]=r.a
                        self._a(0x00)
                        m[0x042D]=r.a
                        m[0x042E]=r.a
                        self._a(0x4F)
                        self._mark(0xA502)
                        yield from self._external(0xA502,0xF26D,None,"tail")
                        return
                    else:
                        self._y(0x39)
                        yield from self._external(0xA4C6,0xEE07,0xA4CB,"far_call",40996)
                        if r.pc!=0xA4CB:return  # preserve nonlocal stack return
                        self._a(m[CURRENT_CITY])
                        self._mark(0xA4CE)
                        yield from self._external(0xA4CE,0xF26D,None,"tail")
                        return
                else:
                    if not (yield from self._local_call(self.city_helper_dd70,0xA482,0xA485)):return
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x03)
                    self._mark(0xA48A)
                    if not r.p&Z:
                        self._a(0x03)
                        m[PHASE]=r.a
                        self._a(0x26)
                        self._mark(0xA499)
                        yield from self._external(0xA499,0xF26D,None,"tail")
                        return
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xA491)
                        self._rts();return

    def city_helper_a505(self):
        """$A505: city helper a505; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA505)
        self._a(m[0x0481])
        if not (yield from self._local_call(self.city_helper_dd5e,0xA508,0xA50B)):return
        if not (yield from self._local_call(self.text_request_readiness,0xA50B,0xA50E)):return
        self._mark(0xA50E)
        if not r.p&C:
            self._mark(0xA53C)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xA510,0xA513)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA517)
            if r.p&C:
                self._a(m[CITY])
                yield from self._external(0xA540,0xF2AF,0xA543,"call",None)
                if r.pc!=0xA543:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,m[0x0472])
                self._mark(0xA54A)
                if r.p&C:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._y(0x3D)
                    yield from self._external(0xA556,0xEE07,0xA55B,"far_call",40996)
                    if r.pc!=0xA55B:return  # preserve nonlocal stack return
                    if not (yield from self._local_call(self.city_helper_dd70,0xA55B,0xA55E)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xA563)
                    yield from self._external(0xA563,0xF26D,None,"tail")
                    return
                else:
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xA54F)
                    if r.p&Z:
                        self._a(0x16)
                        m[PHASE]=r.a
                        self._a(0x2A)
                        self._mark(0xA56D)
                        yield from self._external(0xA56D,0xF26D,None,"tail")
                        return
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._y(0x3D)
                        yield from self._external(0xA556,0xEE07,0xA55B,"far_call",40996)
                        if r.pc!=0xA55B:return  # preserve nonlocal stack return
                        if not (yield from self._local_call(self.city_helper_dd70,0xA55B,0xA55E)):return
                        m[0x046C]=r.a
                        self._a(0x29)
                        self._mark(0xA563)
                        yield from self._external(0xA563,0xF26D,None,"tail")
                        return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA51A)
                if not r.p&C:
                    self._mark(0xA53C)
                    self._rts();return
                else:
                    self._y(0x3D)
                    yield from self._external(0xA51E,0xEE07,0xA523,"far_call",40996)
                    if r.pc!=0xA523:return  # preserve nonlocal stack return
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x03)
                    self._mark(0xA528)
                    if r.p&Z:
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xA53C)
                        self._rts();return
                    else:
                        self._a(0x03)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.city_helper_dd70,0xA52F,0xA532)):return
                        self._a(0x26)
                        self._mark(0xA534)
                        yield from self._external(0xA534,0xF26D,None,"tail")
                        return

    def city_helper_a570(self):
        """$A570: city helper a570; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA570)
        if not (yield from self._local_call(self.city_helper_d5bd,0xA570,0xA573)):return
        self._a(m[0x0013])
        self._mark(0xA576)
        if r.p&Z:
            self._mark(0xA581)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xA57A)
            if not r.p&Z:
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                self._a(m[0x0472])
                m[0x0000]=r.a
                self._a(m[0x0482])
                m[0x0003]=r.a
                yield from self._external(0xA596,0xEBE9,0xA599,"call",None)
                if r.pc!=0xA599:return  # preserve nonlocal stack return
                self._a(0x64)
                m[0x0003]=r.a
                self._a(0x00)
                m[0x0004]=r.a
                if not (yield from self._local_call(self.city_helper_db72,0xA5A3,0xA5A6)):return
                self._a(m[WORLD_CURSOR])
                self._compare(r.a,0x03)
                self._mark(0xA5AB)
                if r.p&Z:
                    while True:  # natural loop $A5B6
                        yield from self._external(0xA5B6,0xE856,0xA5B9,"call",None)
                        if r.pc!=0xA5B9:return  # preserve nonlocal stack return
                        self._compare(r.a,0x05)
                        self._mark(0xA5BB)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._add(0x06)
                        m[0x0003]=r.a
                        yield from self._external(0xA5C2,0xEBE9,0xA5C5,"call",None)
                        if r.pc!=0xA5C5:return  # preserve nonlocal stack return
                        self._a(0x00)
                        m[0x0004]=r.a
                        self._a(0x0A)
                        m[0x0003]=r.a
                        if not (yield from self._local_call(self.city_helper_db72,0xA5CF,0xA5D2)):return
                        self._a(m[0x0000])
                        self._mark(0xA5D5)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x01)
                            pass
                        m[0x042C]=r.a
                        self._a(0x00)
                        m[0x042D]=r.a
                        m[0x042E]=r.a
                        if not (yield from self._local_call(self.city_helper_d568,0xA5E4,0xA5E7)):return
                        self._a(m[CITY])
                        yield from self._external(0xA5EA,0xF2AF,0xA5ED,"call",None)
                        if r.pc!=0xA5ED:return  # preserve nonlocal stack return
                        self._y(0x02)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(m[0x0472],subtract=True)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._add(0x00,subtract=True)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(0x14)
                        m[PHASE]=r.a
                        self._a(0xFF)
                        m[0x0481]=r.a
                        self._a(0xE7)
                        m[0x0010]=r.a
                        self._a(0x03)
                        m[0x0011]=r.a
                        self._a(m[WORLD_CURSOR])
                        self._mark(0xA615)
                        if not r.p&Z:
                            self._compare(r.a,0x01)
                            self._mark(0xA628)
                            if not r.p&Z:
                                self._compare(r.a,0x02)
                                self._mark(0xA63B)
                                if not r.p&Z:
                                    self._y(0x0A)
                                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                    self._flag(C,False)
                                    self._add(m[0x042C])
                                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                    self._flag(C,True)
                                    self._add(0x63,subtract=True)
                                    self._mark(0xA66E)
                                    if not r.p&C:
                                        pass
                                    else:
                                        m[0x0002]=r.a
                                        self._a(m[0x042C])
                                        self._flag(C,True)
                                        self._add(m[0x0002],subtract=True)
                                        m[0x042C]=r.a
                                        self._a(0x63)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        pass
                                    self._a(0x07)
                                    m[0x04A2]=r.a
                                    self._a(0x24)
                                    m[0x04D6]=r.a
                                    self._a(0x50)
                                    self._mark(0xA68D)
                                    yield from self._external(0xA68D,0xF26D,None,"tail")
                                    return
                                else:
                                    m[0x042C]=self._shift(m[0x042C],False,rotate=False)
                                    self._a(m[0x042C])
                                    self._mark(0xA643)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        m[0x042C]=self._nz(m[0x042C]+1)
                                        pass
                                    self._a(0x0F)
                                    m[0x0010]=r.a
                                    self._a(0x27)
                                    m[0x0011]=r.a
                                    self._y(0x06)
                                    if not (yield from self._local_call(self.city_helper_a690,0xA654,0xA657)):return
                                    self._a(0x2E)
                                    m[0x04D6]=r.a
                                    self._a(0x2D)
                                    self._mark(0xA65E)
                                    yield from self._external(0xA65E,0xF26D,None,"tail")
                                    return
                            else:
                                self._y(0x0E)
                                if not (yield from self._local_call(self.city_helper_a690,0xA62C,0xA62F)):return
                                self._a(0x29)
                                m[0x04D6]=r.a
                                self._a(0x2C)
                                self._mark(0xA636)
                                yield from self._external(0xA636,0xF26D,None,"tail")
                                return
                        else:
                            self._y(0x08)
                            if not (yield from self._local_call(self.city_helper_a690,0xA619,0xA61C)):return
                            self._a(0x24)
                            m[0x04D6]=r.a
                            self._a(0x2B)
                            self._mark(0xA623)
                            yield from self._external(0xA623,0xF26D,None,"tail")
                            return
                else:
                    yield from self._external(0xA5AD,0xE856,0xA5B0,"call",None)
                    if r.pc!=0xA5B0:return  # preserve nonlocal stack return
                    self._flag(C,False)
                    self._add(0x0A)
                    pass
                m[0x0003]=r.a
                yield from self._external(0xA5C2,0xEBE9,0xA5C5,"call",None)
                if r.pc!=0xA5C5:return  # preserve nonlocal stack return
                self._a(0x00)
                m[0x0004]=r.a
                self._a(0x0A)
                m[0x0003]=r.a
                if not (yield from self._local_call(self.city_helper_db72,0xA5CF,0xA5D2)):return
                self._a(m[0x0000])
                self._mark(0xA5D5)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x01)
                    pass
                m[0x042C]=r.a
                self._a(0x00)
                m[0x042D]=r.a
                m[0x042E]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xA5E4,0xA5E7)):return
                self._a(m[CITY])
                yield from self._external(0xA5EA,0xF2AF,0xA5ED,"call",None)
                if r.pc!=0xA5ED:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x0472],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(0x00,subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(0x14)
                m[PHASE]=r.a
                self._a(0xFF)
                m[0x0481]=r.a
                self._a(0xE7)
                m[0x0010]=r.a
                self._a(0x03)
                m[0x0011]=r.a
                self._a(m[WORLD_CURSOR])
                self._mark(0xA615)
                if not r.p&Z:
                    self._compare(r.a,0x01)
                    self._mark(0xA628)
                    if not r.p&Z:
                        self._compare(r.a,0x02)
                        self._mark(0xA63B)
                        if not r.p&Z:
                            self._y(0x0A)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._flag(C,False)
                            self._add(m[0x042C])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._flag(C,True)
                            self._add(0x63,subtract=True)
                            self._mark(0xA66E)
                            if not r.p&C:
                                pass
                            else:
                                m[0x0002]=r.a
                                self._a(m[0x042C])
                                self._flag(C,True)
                                self._add(m[0x0002],subtract=True)
                                m[0x042C]=r.a
                                self._a(0x63)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                pass
                            self._a(0x07)
                            m[0x04A2]=r.a
                            self._a(0x24)
                            m[0x04D6]=r.a
                            self._a(0x50)
                            self._mark(0xA68D)
                            yield from self._external(0xA68D,0xF26D,None,"tail")
                            return
                        else:
                            m[0x042C]=self._shift(m[0x042C],False,rotate=False)
                            self._a(m[0x042C])
                            self._mark(0xA643)
                            if not r.p&Z:
                                pass
                            else:
                                m[0x042C]=self._nz(m[0x042C]+1)
                                pass
                            self._a(0x0F)
                            m[0x0010]=r.a
                            self._a(0x27)
                            m[0x0011]=r.a
                            self._y(0x06)
                            if not (yield from self._local_call(self.city_helper_a690,0xA654,0xA657)):return
                            self._a(0x2E)
                            m[0x04D6]=r.a
                            self._a(0x2D)
                            self._mark(0xA65E)
                            yield from self._external(0xA65E,0xF26D,None,"tail")
                            return
                    else:
                        self._y(0x0E)
                        if not (yield from self._local_call(self.city_helper_a690,0xA62C,0xA62F)):return
                        self._a(0x29)
                        m[0x04D6]=r.a
                        self._a(0x2C)
                        self._mark(0xA636)
                        yield from self._external(0xA636,0xF26D,None,"tail")
                        return
                else:
                    self._y(0x08)
                    if not (yield from self._local_call(self.city_helper_a690,0xA619,0xA61C)):return
                    self._a(0x24)
                    m[0x04D6]=r.a
                    self._a(0x2B)
                    self._mark(0xA623)
                    yield from self._external(0xA623,0xF26D,None,"tail")
                    return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xA581)
                self._rts();return

    def city_helper_a690(self):
        """$A690: city helper a690; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA690)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x042C])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        m[0x0002]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(0x00)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        m[0x0003]=r.a
        self._a(m[0x0002])
        self._flag(C,True)
        self._add(m[0x0010],subtract=True)
        m[0x0004]=r.a
        self._a(m[0x0003])
        self._add(m[0x0011],subtract=True)
        self._mark(0xA6B5)
        if not r.p&C:
            pass
        else:
            self._a(m[0x042C])
            self._flag(C,True)
            self._add(m[0x0004],subtract=True)
            m[0x042C]=r.a
            self._a(m[0x0011])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(m[0x0010])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            pass
        self._a(0x01)
        m[0x0002]=r.a
        self._a(m[0x042C])
        self._compare(r.a,0x1F)
        self._mark(0xA6D6)
        if not r.p&C:
            pass
        else:
            m[0x0002]=self._nz(m[0x0002]+1)
            pass
        self._y(0x0B)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0002])
        self._compare(r.a,0x64)
        self._mark(0xA6E5)
        if not r.p&C:
            pass
        else:
            self._a(0x64)
            pass
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._mark(0xA6EB)
        self._rts();return

    def city_helper_a6ec(self):
        """$A6EC: city helper a6ec; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA6EC)
        if not (yield from self._local_call(self.world_selection_portrait,0xA6EC,0xA6EF)):return
        if not (yield from self._local_call(self.text_request_readiness,0xA6EF,0xA6F2)):return
        self._mark(0xA6F2)
        if not r.p&C:
            self._mark(0xA771)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA6F8)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA75B)
                if not r.p&C:
                    pass
                else:
                    self._a(0xFF)
                    m[0x04E4]=r.a
                    if not (yield from self._local_call(self.text_request_readiness,0xA762,0xA765)):return
                    self._mark(0xA765)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0x02)
                        if not (yield from self._local_call(self.city_helper_d58c,0xA76E,0xA771)):return
                        pass
                    pass
                self._mark(0xA771)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_at_cursor,0xA6FA,0xA6FD)):return
                self._compare(r.y,0xFF)
                self._mark(0xA6FF)
                if r.p&Z:
                    self._a(0x24)
                    self._mark(0xA774)
                    yield from self._external(0xA774,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    if not (yield from self._local_call(self.city_helper_dd79,0xA704,0xA707)):return
                    self._a(m[CITY])
                    self._mark(0xA70A)
                    if r.p&N:
                        self._a(0x2F)
                        self._mark(0xA779)
                        yield from self._external(0xA779,0xF26D,None,"tail")
                        return
                    else:
                        m[CURRENT_CITY]=r.a
                        self._a(m[0x0010])
                        self._compare(r.a,0x07)
                        self._mark(0xA714)
                        if r.p&Z:
                            self._a(m[CURRENT_CITY])
                            if not (yield from self._local_call(self.city_helper_dc6b,0xA71E,0xA721)):return
                            self._compare(r.x,0x0A)
                            self._mark(0xA723)
                            if r.p&Z:
                                self._a(0x2F)
                                self._mark(0xA779)
                                yield from self._external(0xA779,0xF26D,None,"tail")
                                return
                            else:
                                m[0x047C]=r.x
                                self._a(0x0A)
                                self._flag(C,True)
                                self._add(m[0x047C],subtract=True)
                                m[0x047C]=r.a
                                self._a(m[WORLD_CURSOR])
                                yield from self._external(0xA734,0xF2AF,0xA737,"call",None)
                                if r.pc!=0xA737:return  # preserve nonlocal stack return
                                if not (yield from self._local_call(self.city_helper_dc6b,0xA737,0xA73A)):return
                                self._compare(r.x,m[0x047C])
                                self._mark(0xA73D)
                                if r.p&C:
                                    pass
                                else:
                                    m[0x047C]=r.x
                                    pass
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(0xFF)
                                m[0x04E4]=r.a
                                self._a(m[WORLD_CURSOR])
                                m[CITY]=r.a
                                self._a(0x80)
                                m[0x0478]=r.a
                                self._a(0x27)
                                self._mark(0xA757)
                                yield from self._external(0xA757,0xF26D,None,"tail")
                                return
                        else:
                            self._compare(r.a,m[0x6F03])
                            self._mark(0xA719)
                            if not r.p&Z:
                                self._a(0x2F)
                                self._mark(0xA779)
                                yield from self._external(0xA779,0xF26D,None,"tail")
                                return
                            else:
                                self._a(m[CURRENT_CITY])
                                if not (yield from self._local_call(self.city_helper_dc6b,0xA71E,0xA721)):return
                                self._compare(r.x,0x0A)
                                self._mark(0xA723)
                                if r.p&Z:
                                    self._a(0x2F)
                                    self._mark(0xA779)
                                    yield from self._external(0xA779,0xF26D,None,"tail")
                                    return
                                else:
                                    m[0x047C]=r.x
                                    self._a(0x0A)
                                    self._flag(C,True)
                                    self._add(m[0x047C],subtract=True)
                                    m[0x047C]=r.a
                                    self._a(m[WORLD_CURSOR])
                                    yield from self._external(0xA734,0xF2AF,0xA737,"call",None)
                                    if r.pc!=0xA737:return  # preserve nonlocal stack return
                                    if not (yield from self._local_call(self.city_helper_dc6b,0xA737,0xA73A)):return
                                    self._compare(r.x,m[0x047C])
                                    self._mark(0xA73D)
                                    if r.p&C:
                                        pass
                                    else:
                                        m[0x047C]=r.x
                                        pass
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(0xFF)
                                    m[0x04E4]=r.a
                                    self._a(m[WORLD_CURSOR])
                                    m[CITY]=r.a
                                    self._a(0x80)
                                    m[0x0478]=r.a
                                    self._a(0x27)
                                    self._mark(0xA757)
                                    yield from self._external(0xA757,0xF26D,None,"tail")
                                    return

    def city_helper_a77c(self):
        """$A77C: city helper a77c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA77C)
        self._a(m[0x0478])
        self._mark(0xA77F)
        if not r.p&Z:
            self._mark(0xA7C9)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xA781,0xA784)):return
            self._a(m[0x047C])
            self._mark(0xA787)
            if not r.p&N:
                self._mark(0xA7C9)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xA78B)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x02)
                    if not (yield from self._local_call(self.city_helper_d58c,0xA7C6,0xA7C9)):return
                    self._mark(0xA7C9)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xA78D,0xA790)):return
                    self._a(0x02)
                    if not (yield from self._local_call(self.city_helper_d58c,0xA792,0xA795)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xA798,0xA79B)):return
                    m[0x046C]=r.a
                    if not (yield from self._local_call(self.city_helper_dc6b,0xA79E,0xA7A1)):return
                    m[0x0002]=r.x
                    self._x(0x00)
                    self._y(0x00)
                    while True:  # natural loop $A7A8
                        self._a(m[(0x0481+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xA7AD)
                        if r.p&Z:
                            pass
                        else:
                            self._x(r.x+1)
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x0A)
                        self._mark(0xA7B3)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._compare(r.x,m[0x0002])
                        self._mark(0xA7B8)
                        if not r.p&Z:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x29)
                            self._mark(0xA80B)
                            yield from self._external(0xA80B,0xF26D,None,"tail")
                            return
                        else:
                            self._a(0x32)
                            self._mark(0xA7BC)
                            yield from self._external(0xA7BC,0xF26D,None,"tail")
                            return

    def city_helper_a7ca(self):
        """$A7CA: city helper a7ca; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA7CA)
        self._a(0x17)
        m[0x0010]=r.a
        self._a(0xA8)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xA7D9,0xED1E,0xA7DC,"call",None)
        if r.pc!=0xA7DC:return  # preserve nonlocal stack return
        self._a(0x1B)
        m[0x0010]=r.a
        self._a(0xA8)
        m[0x0011]=r.a
        self._a(0x1F)
        m[0x0000]=r.a
        self._a(0xA8)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xA7F3,0xEDF5,0xA7F6,"call",None)
        if r.pc!=0xA7F6:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xA7F6,0xA7F9)):return
        self._mark(0xA7F9)
        if not r.p&C:
            self._mark(0xA816)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xA7FF)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xA80F)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xA816)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xA804)
                if not r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA816)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x29)
                    self._mark(0xA80B)
                    yield from self._external(0xA80B,0xF26D,None,"tail")
                    return

    def city_helper_a824(self):
        """$A824: city helper a824; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA824)
        if not (yield from self._local_call(self.city_helper_d5bd,0xA824,0xA827)):return
        self._a(m[0x0013])
        self._mark(0xA82A)
        if r.p&Z:
            self._mark(0xA880)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xA82E)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xA880)
                self._rts();return
            else:
                if not (yield from self._local_call(self.transfer_selected_officers,0xA830,0xA833)):return
                self._a(0x11)
                m[0x04A2]=r.a
                self._a(0x32)
                m[0x04D6]=r.a
                self._a(0xFF)
                m[0x0481]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xA842,0xA845)):return
                self._a(0x14)
                m[PHASE]=r.a
                self._a(0xFF)
                m[0x0481]=r.a
                self._a(m[WORLD_CURSOR])
                yield from self._external(0xA852,0xF2AF,0xA855,"call",None)
                if r.pc!=0xA855:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0010]=r.a
                if not (yield from self._local_call(self.city_helper_dc6b,0xA85C,0xA85F)):return
                self._compare(r.x,0x00)
                self._mark(0xA861)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x07)
                    self._y(0x00)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    pass
                self._a(m[CURRENT_CITY])
                yield from self._external(0xA86C,0xF2AF,0xA86F,"call",None)
                if r.pc!=0xA86F:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[0x0010])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(0x31)
                self._mark(0xA878)
                yield from self._external(0xA878,0xF26D,None,"tail")
                return

    def city_helper_a881(self):
        """$A881: city helper a881; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA881)
        self._a(m[0x0478])
        self._mark(0xA884)
        if not r.p&Z:
            self._mark(0xA8AE)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xA886,0xA889)):return
            self._a(m[0x047C])
            self._mark(0xA88C)
            if not r.p&N:
                self._mark(0xA8AE)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xA890)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xA8AE)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xA892,0xA895)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(m[0x0481])
                    m[0x0482]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xA89E,0xA8A1)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xA8A6)
                    yield from self._external(0xA8A6,0xF26D,None,"tail")
                    return

    def city_helper_a8af(self):
        """$A8AF: city helper a8af; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8AF)
        if not (yield from self._local_call(self.city_helper_d5bd,0xA8AF,0xA8B2)):return
        self._a(m[0x0013])
        self._mark(0xA8B5)
        if r.p&Z:
            self._mark(0xA8E1)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xA8B9)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xA8E1)
                self._rts();return
            else:
                self._a(0x1B)
                m[0x04A2]=r.a
                self._a(0x32)
                m[0x04D6]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xA8C5,0xA8C8)):return
                self._a(0x80)
                m[0x0473]=r.a
                self._a(0xFF)
                m[0x0481]=r.a
                self._a(0x14)
                m[PHASE]=r.a
                self._a(0x31)
                self._mark(0xA8D9)
                yield from self._external(0xA8D9,0xF26D,None,"tail")
                return

    def city_helper_a8e2(self):
        """$A8E2: city helper a8e2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA8E2)
        self._a(m[0x0140])
        self._mark(0xA8E5)
        if not r.p&Z:
            self._mark(0xA8F6)
            self._rts();return
        else:
            if not (yield from self._local_call(self.text_request_readiness,0xA8E7,0xA8EA)):return
            self._mark(0xA8EA)
            if not r.p&C:
                self._mark(0xA8F6)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_helper_d543,0xA8EC,0xA8EF)):return
                self._a(m[NEW_BUTTONS])
                self._a(r.a & 0x03)
                self._mark(0xA8F4)
                if not r.p&Z:
                    self._a(m[0x0482])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xA8FF,0xEE07,0xA904,"far_call",41002)
                    if r.pc!=0xA904:return  # preserve nonlocal stack return
                    self._a(0x03)
                    m[0x00A4]=r.a
                    self._a(m[0x0482])
                    m[0x0481]=r.a
                    if not (yield from self._local_call(self.city_helper_db99,0xA90F,0xA912)):return
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x08)
                    self._mark(0xA917)
                    if r.p&Z:
                        self._a(0x04)
                        m[0x00A4]=r.a
                        self._a(0x16)
                        m[PHASE]=r.a
                        self._a(0x35)
                        self._mark(0xA93B)
                        yield from self._external(0xA93B,0xF26D,None,"tail")
                        return
                    else:
                        self._a(m[WORLD_CURSOR])
                        self._compare(r.a,0x04)
                        self._mark(0xA91E)
                        if r.p&Z:
                            while True:  # natural loop $A93E
                                yield from self._external(0xA93E,0xE850,0xA941,"call",None)
                                if r.pc!=0xA941:return  # preserve nonlocal stack return
                                self._mark(0xA941)
                                if r.p&Z:
                                    continue
                                else:
                                    pass
                                m[0x042C]=r.a
                                self._a(0x00)
                                m[0x042D]=r.a
                                m[0x042E]=r.a
                                self._a(m[CITY])
                                yield from self._external(0xA951,0xF2AF,0xA954,"call",None)
                                if r.pc!=0xA954:return  # preserve nonlocal stack return
                                self._y(0x10)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._flag(C,False)
                                self._add(m[0x042C])
                                self._compare(r.a,0x63)
                                self._mark(0xA95E)
                                if not r.p&C:
                                    pass
                                else:
                                    self._a(0x63)
                                    pass
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._a(0x16)
                                m[PHASE]=r.a
                                self._a(0x34)
                                self._mark(0xA96B)
                                yield from self._external(0xA96B,0xF26D,None,"tail")
                                return
                        else:
                            self._mark(0xA920)
                            if not r.p&C:
                                self._a(0x00)
                                m[0x042D]=r.a
                                m[0x042E]=r.a
                                while True:  # natural loop $A976
                                    yield from self._external(0xA976,0xE843,0xA979,"call",None)
                                    if r.pc!=0xA979:return  # preserve nonlocal stack return
                                    self._compare(r.a,0x29)
                                    self._mark(0xA97B)
                                    if r.p&C:
                                        continue
                                    else:
                                        pass
                                    m[0x042C]=r.a
                                    self._a(m[WORLD_CURSOR])
                                    self._compare(r.a,0x02)
                                    self._mark(0xA985)
                                    if r.p&Z:
                                        self._a(0x32)
                                        self._flag(C,False)
                                        self._add(m[0x042C])
                                        m[0x042C]=r.a
                                        self._a(m[CITY])
                                        yield from self._external(0xA9D7,0xF2AF,0xA9DA,"call",None)
                                        if r.pc!=0xA9DA:return  # preserve nonlocal stack return
                                        self._y(0x04)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(m[0x042C])
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._add(m[0x042D])
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(0x04)
                                        if not (yield from self._local_call(self.city_helper_dddc,0xA9EE,0xA9F1)):return
                                        self._a(0x16)
                                        m[PHASE]=r.a
                                        self._a(0xB9)
                                        self._mark(0xA9F8)
                                        yield from self._external(0xA9F8,0xF26D,None,"tail")
                                        return
                                    else:
                                        self._compare(r.a,0x03)
                                        self._mark(0xA989)
                                        if r.p&Z:
                                            self._a(0xBA)
                                            m[0x0010]=r.a
                                            self._a(0x50)
                                            pass
                                        else:
                                            self._a(0xB8)
                                            m[0x0010]=r.a
                                            self._a(0x1E)
                                            pass
                                        self._flag(C,False)
                                        self._add(m[0x042C])
                                        m[0x042C]=r.a
                                        self._a(m[CITY])
                                        yield from self._external(0xA9A6,0xF2AF,0xA9A9,"call",None)
                                        if r.pc!=0xA9A9:return  # preserve nonlocal stack return
                                        self._y(0x02)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._flag(C,False)
                                        self._add(m[0x042C])
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._add(m[0x042D])
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(0x02)
                                        if not (yield from self._local_call(self.city_helper_dddc,0xA9BD,0xA9C0)):return
                                        self._a(0x16)
                                        m[PHASE]=r.a
                                        self._a(m[0x0010])
                                        self._mark(0xA9C8)
                                        yield from self._external(0xA9C8,0xF26D,None,"tail")
                                        return
                            else:
                                self._a(0xFF)
                                m[0x0481]=r.a
                                m[PHASE]=self._nz(m[PHASE]+1)
                                self._a(0x33)
                                self._mark(0xA92C)
                                yield from self._external(0xA92C,0xF26D,None,"tail")
                                return
                else:
                    self._mark(0xA8F6)
                    self._rts();return

    def city_helper_a9fb(self):
        """$A9FB: city helper a9fb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA9FB)
        if not (yield from self._local_call(self.text_request_readiness,0xA9FB,0xA9FE)):return
        self._mark(0xA9FE)
        if not r.p&C:
            self._a(m[0x0482])
            return (yield from self.city_helper_dd5e())
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xAA00,0xAA03)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xAA08)
            if r.p&Z:
                self._a(m[0x0482])
                return (yield from self.city_helper_dd5e())
            else:
                if not (yield from self._local_call(self.city_helper_dd70,0xAA0A,0xAA0D)):return
                self._a(0x00)
                m[0x00A4]=r.a
                self._a(m[WORLD_CURSOR])
                self._compare(r.a,0x06)
                self._mark(0xAA17)
                if r.p&Z:
                    self._a(0x10)
                    m[PHASE]=r.a
                    self._a(m[0x0472])
                    yield from self._external(0xAA3D,0xF2D7,0xAA40,"call",None)
                    if r.pc!=0xAA40:return  # preserve nonlocal stack return
                    self._a(m[0x0000])
                    m[0x0010]=r.a
                    self._a(m[0x0001])
                    m[0x0011]=r.a
                    self._y(0x00)
                    m[0x0001]=r.y
                    m[0x0002]=r.y
                    while True:  # natural loop $AA54
                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x0001])
                        m[0x0001]=r.a
                        self._a(0x00)
                        self._add(m[0x0002])
                        m[0x0002]=r.a
                        self._y(r.y+1)
                        self._compare(r.y,0x03)
                        self._mark(0xAA68)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        m[0x0003]=r.y
                        self._a(0x00)
                        m[0x0004]=r.a
                        m[0x042E]=r.a
                        yield from self._external(0xAA75,0xEA7C,0xAA78,"call",None)
                        if r.pc!=0xAA78:return  # preserve nonlocal stack return
                        self._a(m[0x0001])
                        m[0x042C]=r.a
                        self._a(m[0x0002])
                        m[0x042D]=r.a
                        self._a(0x38)
                        self._mark(0xAA86)
                        yield from self._external(0xAA86,0xF26D,None,"tail")
                        return
                else:
                    self._compare(r.a,0x07)
                    self._mark(0xAA1B)
                    if r.p&Z:
                        self._a(0x10)
                        m[PHASE]=r.a
                        self._a(0x36)
                        self._mark(0xAA2C)
                        yield from self._external(0xAA2C,0xF26D,None,"tail")
                        return
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x37)
                        self._mark(0xAA22)
                        yield from self._external(0xAA22,0xF26D,None,"tail")
                        return

    def city_helper_aa89(self):
        """$AA89: city helper aa89; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAA89)
        self._a(0xDF)
        m[0x0010]=r.a
        self._a(0xAA)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xAA98,0xED1E,0xAA9B,"call",None)
        if r.pc!=0xAA9B:return  # preserve nonlocal stack return
        self._a(0xE3)
        m[0x0010]=r.a
        self._a(0xAA)
        m[0x0011]=r.a
        self._a(0xE7)
        m[0x0000]=r.a
        self._a(0xAA)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xAAB2,0xEDF5,0xAAB5,"call",None)
        if r.pc!=0xAAB5:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xAAB5,0xAAB8)):return
        self._mark(0xAAB8)
        if not r.p&C:
            self._a(m[0x0482])
            return (yield from self.city_helper_dd5e())
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xAABE)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAAC9)
                if not r.p&C:
                    self._a(m[0x0482])
                    return (yield from self.city_helper_dd5e())
                else:
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_d568,0xAAD3,0xAAD6)):return
                    self._mark(0xAAD6)
                    yield from self._external(0xAAD6,0xF28B,None,"tail")
                    return
            else:
                self._a(m[0x0012])
                self._mark(0xAAC3)
                if not r.p&Z:
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_d568,0xAAD3,0xAAD6)):return
                    self._mark(0xAAD6)
                    yield from self._external(0xAAD6,0xF28B,None,"tail")
                    return
                else:
                    self._a(m[0x0472])
                    m[0x0481]=r.a
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xACEB,0xEE07,0xACF0,"far_call",41002)
                    if r.pc!=0xACF0:return  # preserve nonlocal stack return
                    self._a(m[CITY])
                    yield from self._external(0xACF3,0xF2AF,0xACF6,"call",None)
                    if r.pc!=0xACF6:return  # preserve nonlocal stack return
                    if not (yield from self._local_call(self.city_helper_dc6b,0xACF6,0xACF9)):return
                    self._a(r.x)
                    self._flag(C,False)
                    self._add(0x11)
                    self._y(r.a)
                    self._a(m[0x0472])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    yield from self._external(0xAD07,0xF368,0xAD0A,"call",None)
                    if r.pc!=0xAD0A:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0030]=r.a
                    self._a(m[0x0472])
                    m[0x0031]=r.a
                    yield from self._external(0xAD17,0xF2D7,0xAD1A,"call",None)
                    if r.pc!=0xAD1A:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0002]=r.a
                    self._a(r.a & 0xFC)
                    self._a(r.a | 0x02)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(m[0x0002])
                    self._a(r.a & 0x03)
                    self._compare(r.a,0x01)
                    self._mark(0xAD2E)
                    if r.p&Z:
                        pass
                    else:
                        self._y(0x2A)
                        yield from self._external(0xAD32,0xEE07,0xAD37,"far_call",40966)
                        if r.pc!=0xAD37:return  # preserve nonlocal stack return
                        pass
                    self._a(0x16)
                    m[PHASE]=r.a
                    self._a(0x39)
                    self._mark(0xAD3E)
                    yield from self._external(0xAD3E,0xF26D,None,"tail")
                    return

    def city_helper_aaec(self):
        """$AAEC: city helper aaec; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAAEC)
        self._a(0xC1)
        m[0x0010]=r.a
        self._a(0xAB)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xAAFB,0xED1E,0xAAFE,"call",None)
        if r.pc!=0xAAFE:return  # preserve nonlocal stack return
        self._a(0xC5)
        m[0x0010]=r.a
        self._a(0xAB)
        m[0x0011]=r.a
        self._a(0xC9)
        m[0x0000]=r.a
        self._a(0xAB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xAB15,0xEDF5,0xAB18,"call",None)
        if r.pc!=0xAB18:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xAB18,0xAB1B)):return
        self._mark(0xAB1B)
        if not r.p&C:
            self._a(m[0x0482])
            return (yield from self.city_helper_dd5e())
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xAB21)
            if r.p&C:
                self._a(m[0x0012])
                self._mark(0xAB3D)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_helper_d568,0xAB26,0xAB29)):return
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    self._mark(0xAB31)
                    yield from self._external(0xAB31,0xF28B,None,"tail")
                    return
                else:
                    self._a(m[WORLD_CURSOR])
                    self._compare(r.a,0x06)
                    self._mark(0xAB44)
                    if not r.p&Z:
                        self._a(m[CITY])
                        yield from self._external(0xAB6C,0xF2AF,0xAB6F,"call",None)
                        if r.pc!=0xAB6F:return  # preserve nonlocal stack return
                        self._x(0x02)
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x0473])
                        self._mark(0xAB78)
                        if r.p&Z:
                            pass
                        else:
                            self._x(0x0D)
                            pass
                        m[0x0000]=r.x
                        yield from self._external(0xAB7F,0xE85C,0xAB82,"call",None)
                        if r.pc!=0xAB82:return  # preserve nonlocal stack return
                        self._compare(r.a,m[0x0000])
                        self._mark(0xAB85)
                        if not r.p&C:
                            self._a(m[0x0472])
                            m[0x0481]=r.a
                            m[0x0000]=r.a
                            self._y(0x3D)
                            yield from self._external(0xAB95,0xEE07,0xAB9A,"far_call",41002)
                            if r.pc!=0xAB9A:return  # preserve nonlocal stack return
                            self._a(0x16)
                            m[PHASE]=r.a
                            self._a(0x3A)
                            self._mark(0xABA1)
                            yield from self._external(0xABA1,0xF26D,None,"tail")
                            return
                        else:
                            self._a(m[0x0472])
                            m[0x0481]=r.a
                            m[0x0000]=r.a
                            self._y(0x3D)
                            yield from self._external(0xACEB,0xEE07,0xACF0,"far_call",41002)
                            if r.pc!=0xACF0:return  # preserve nonlocal stack return
                            self._a(m[CITY])
                            yield from self._external(0xACF3,0xF2AF,0xACF6,"call",None)
                            if r.pc!=0xACF6:return  # preserve nonlocal stack return
                            if not (yield from self._local_call(self.city_helper_dc6b,0xACF6,0xACF9)):return
                            self._a(r.x)
                            self._flag(C,False)
                            self._add(0x11)
                            self._y(r.a)
                            self._a(m[0x0472])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            yield from self._external(0xAD07,0xF368,0xAD0A,"call",None)
                            if r.pc!=0xAD0A:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0030]=r.a
                            self._a(m[0x0472])
                            m[0x0031]=r.a
                            yield from self._external(0xAD17,0xF2D7,0xAD1A,"call",None)
                            if r.pc!=0xAD1A:return  # preserve nonlocal stack return
                            self._y(0x0B)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0002]=r.a
                            self._a(r.a & 0xFC)
                            self._a(r.a | 0x02)
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._a(m[0x0002])
                            self._a(r.a & 0x03)
                            self._compare(r.a,0x01)
                            self._mark(0xAD2E)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x2A)
                                yield from self._external(0xAD32,0xEE07,0xAD37,"far_call",40966)
                                if r.pc!=0xAD37:return  # preserve nonlocal stack return
                                pass
                            self._a(0x16)
                            m[PHASE]=r.a
                            self._a(0x39)
                            self._mark(0xAD3E)
                            yield from self._external(0xAD3E,0xF26D,None,"tail")
                            return
                    else:
                        self._a(m[CITY])
                        yield from self._external(0xAB49,0xF2AF,0xAB4C,"call",None)
                        if r.pc!=0xAB4C:return  # preserve nonlocal stack return
                        self._y(0x02)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0002]=r.a
                        self._flag(C,True)
                        self._add(m[0x042C],subtract=True)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0003]=r.a
                        self._add(m[0x042D],subtract=True)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._mark(0xAB64)
                        if not r.p&C:
                            self._y(0x02)
                            self._a(m[0x0002])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._y(r.y+1)
                            self._a(m[0x0003])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._a(m[0x0482])
                            m[0x0481]=r.a
                            self._a(0x16)
                            m[PHASE]=r.a
                            self._a(0x2A)
                            self._mark(0xABBE)
                            yield from self._external(0xABBE,0xF26D,None,"tail")
                            return
                        else:
                            self._a(m[0x0472])
                            m[0x0481]=r.a
                            m[0x0000]=r.a
                            self._y(0x3D)
                            yield from self._external(0xACEB,0xEE07,0xACF0,"far_call",41002)
                            if r.pc!=0xACF0:return  # preserve nonlocal stack return
                            self._a(m[CITY])
                            yield from self._external(0xACF3,0xF2AF,0xACF6,"call",None)
                            if r.pc!=0xACF6:return  # preserve nonlocal stack return
                            if not (yield from self._local_call(self.city_helper_dc6b,0xACF6,0xACF9)):return
                            self._a(r.x)
                            self._flag(C,False)
                            self._add(0x11)
                            self._y(r.a)
                            self._a(m[0x0472])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            yield from self._external(0xAD07,0xF368,0xAD0A,"call",None)
                            if r.pc!=0xAD0A:return  # preserve nonlocal stack return
                            self._y(0x00)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0030]=r.a
                            self._a(m[0x0472])
                            m[0x0031]=r.a
                            yield from self._external(0xAD17,0xF2D7,0xAD1A,"call",None)
                            if r.pc!=0xAD1A:return  # preserve nonlocal stack return
                            self._y(0x0B)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0002]=r.a
                            self._a(r.a & 0xFC)
                            self._a(r.a | 0x02)
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._a(m[0x0002])
                            self._a(r.a & 0x03)
                            self._compare(r.a,0x01)
                            self._mark(0xAD2E)
                            if r.p&Z:
                                pass
                            else:
                                self._y(0x2A)
                                yield from self._external(0xAD32,0xEE07,0xAD37,"far_call",40966)
                                if r.pc!=0xAD37:return  # preserve nonlocal stack return
                                pass
                            self._a(0x16)
                            m[PHASE]=r.a
                            self._a(0x39)
                            self._mark(0xAD3E)
                            yield from self._external(0xAD3E,0xF26D,None,"tail")
                            return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAB24)
                if not r.p&C:
                    self._a(m[0x0482])
                    return (yield from self.city_helper_dd5e())
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xAB26,0xAB29)):return
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    self._mark(0xAB31)
                    yield from self._external(0xAB31,0xF28B,None,"tail")
                    return

    def city_helper_abce(self):
        """$ABCE: city helper abce; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xABCE)
        self._a(m[CITY])
        yield from self._external(0xABD1,0xF2AF,0xABD4,"call",None)
        if r.pc!=0xABD4:return  # preserve nonlocal stack return
        self._y(0x0A)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x63,subtract=True)
        self._mark(0xABDB)
        if not r.p&C:
            self._a(0x03)
            m[WORLD_CURSOR]=r.a
            self._a(0x04)
            m[PHASE]=r.a
            self._a(0x80)
            m[0x0478]=r.a
            self._a(0x0F)
            m[0x047C]=r.a
            self._a(0x27)
            self._mark(0xABFD)
            yield from self._external(0xABFD,0xF26D,None,"tail")
            return
        else:
            self._a(0x16)
            m[PHASE]=r.a
            self._a(0xA7)
            self._mark(0xABE4)
            yield from self._external(0xABE4,0xF26D,None,"tail")
            return

    def city_helper_ac00(self):
        """$AC00: city helper ac00; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC00)
        if not (yield from self._local_call(self.text_request_readiness,0xAC00,0xAC03)):return
        self._mark(0xAC03)
        if not r.p&C:
            self._mark(0xAC29)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xAC05,0xAC08)):return
            if not (yield from self._local_call(self.text_request_readiness,0xAC08,0xAC0B)):return
            self._mark(0xAC0B)
            if not r.p&C:
                self._mark(0xAC29)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAC11)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xAC22)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        pass
                    self._mark(0xAC29)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xAC16,0xAC19)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xAC1E)
                    yield from self._external(0xAC1E,0xF26D,None,"tail")
                    return

    def city_helper_ac2a(self):
        """$AC2A: city helper ac2a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC2A)
        if not (yield from self._local_call(self.city_helper_d5bd,0xAC2A,0xAC2D)):return
        self._a(m[0x0013])
        self._mark(0xAC30)
        if r.p&Z:
            self._mark(0xAC7B)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xAC34)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xAC7B)
                self._rts();return
            else:
                self._y(0x39)
                yield from self._external(0xAC38,0xEE07,0xAC3D,"far_call",41005)
                if r.pc!=0xAC3D:return  # preserve nonlocal stack return
                self._a(m[0x6F00])
                self._flag(C,False)
                self._add(0x64)
                m[0x042C]=r.a
                self._a(0x00)
                self._add(0x00)
                m[0x042D]=r.a
                self._a(m[0x6F01])
                self._flag(C,False)
                self._add(0x01)
                m[0x042F]=r.a
                self._a(0x00)
                m[0x042E]=r.a
                m[0x0430]=r.a
                m[0x0431]=r.a
                self._a(0x03)
                m[0x04A2]=r.a
                self._a(0x42)
                m[0x04D6]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xAC6B,0xAC6E)):return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x52)
                self._mark(0xAC73)
                yield from self._external(0xAC73,0xF26D,None,"tail")
                return

    def city_helper_ac7c(self):
        """$AC7C: city helper ac7c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC7C)
        self._a(m[0x0140])
        self._mark(0xAC7F)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x04A2])
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x30)
            m[0x046C]=r.a
            pass
        self._mark(0xAC8F)
        self._rts();return

    def city_helper_ac90(self):
        """$AC90: city helper ac90; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAC90)
        self._a(m[0x04A0])
        self._mark(0xAC93)
        if not r.p&Z:
            self._a(m[0x0481])
            self._compare(r.a,0xFF)
            self._mark(0xACB2)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_dd5e,0xACB4,0xACB7)):return
                pass
            self._mark(0xACB7)
            self._rts();return
        else:
            self._a(m[0x0140])
            self._mark(0xAC98)
            if not r.p&Z:
                self._mark(0xACB7)
                self._rts();return
            else:
                self._a(0x02)
                if not (yield from self._local_call(self.city_helper_d58c,0xAC9C,0xAC9F)):return
                self._a(m[0x0473])
                self._mark(0xACA2)
                if not r.p&N:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(m[0x0481])
                    self._compare(r.a,0xFF)
                    self._mark(0xACB2)
                    if r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.city_helper_dd5e,0xACB4,0xACB7)):return
                        pass
                    self._mark(0xACB7)
                    self._rts();return
                else:
                    self._a(0x0D)
                    m[PHASE]=r.a
                    self._mark(0xACA9)
                    self._rts();return

    def city_helper_acb8(self):
        """$ACB8: city helper acb8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xACB8)
        if not (yield from self._local_call(self.text_request_readiness,0xACB8,0xACBB)):return
        self._mark(0xACBB)
        if not r.p&C:
            self._a(m[0x0481])
            self._compare(r.a,0xFF)
            self._mark(0xACDA)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_dd5e,0xACDC,0xACDF)):return
                pass
            self._mark(0xACDF)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xACBD,0xACC0)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xACC5)
            if r.p&Z:
                self._a(m[0x0481])
                self._compare(r.a,0xFF)
                self._mark(0xACDA)
                if r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_dd5e,0xACDC,0xACDF)):return
                    pass
                self._mark(0xACDF)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xACC7,0xACCA)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                self._mark(0xACD2)
                yield from self._external(0xACD2,0xF28B,None,"tail")
                return

    def transfer_selected_officers(self):
        """AD41..ADF1: append ten selected officers, promote the ruler and compact source roster.

        The two region records keep their real seventeen-byte header and ten
        roster bytes. Searches retain byte wrapping and actual caller flags.
        This body transfers roster membership; it does not infer allegiance.
        """
        r=self.registers;m=self.memory;self._mark(0xAD41)
        self._a(m[CURRENT_CITY]);yield from self._external(0xAD44,0xF2AF,0xAD47,'call')
        if r.pc!=0xAD47:return
        self._x(0);self._y(17)
        while True:
            self._mark(0xAD4B);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            self._y(r.y+1)
        while True:
            self._mark(0xAD55);self._a(m[(0x481+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._x(r.x+1);self._y(r.y+1);self._compare(r.x,10)
            if r.p&C:break
        self._y(0);self._a(m[(m[0xEE]|m[0xEF]<<8)]);m[2]=r.a;self._y(17)
        ruler_present=False
        while True:
            self._mark(0xAD6D);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
            if r.p&Z:ruler_present=True;break
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        if ruler_present:
            self._a(r.y);self._push(r.a);self._y(17);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[3]=r.a
            self._a(m[2]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._a(self._pop());self._y(r.a)
            self._a(m[3]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._y(1);self._a(m[CURRENT_CITY]);m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
        self._mark(0xAD98);self._a(m[WORLD_CURSOR]);yield from self._external(0xAD9B,0xF2AF,0xAD9E,'call')
        if r.pc!=0xAD9E:return
        self._x(0)
        while True:
            self._mark(0xADA0);self._a(m[(0x481+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[0x10]=r.a;self._y(17)
            while True:
                self._mark(0xADAC);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0x10])
                if r.p&Z:
                    self._a(255);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;break
                self._y(r.y+1)
            self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        self._x(0);self._a(255)
        while True:
            self._mark(0xADC7);m[(0x481+r.x)&65535]=r.a;self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        self._y(17);self._x(0)
        while True:
            self._mark(0xADD3);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if not r.p&Z:m[(0x481+r.x)&65535]=r.a;self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        self._y(17);self._x(0)
        while True:
            self._mark(0xADE6);self._a(m[(0x481+r.x)&65535]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._x(r.x+1);self._y(r.y+1);self._compare(r.x,10)
            if r.p&C:break
        self._mark(0xADF1);self._rts();return

    def military_commands(self):
        """$ADF2: military commands; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xADF2)
        self._a(m[PHASE])
        self._mark(0xADF5)
        index=self._dispatch(0xADF5,(44586, 44629, 44818, 44974, 45127, 45263, 45456, 45595, 45635, 45688, 45884, 45933, 46094, 46129, 46173, 46202, 46343, 46376, 46482, 46502, 46833, 46556, 46910, 46624, 46704))
        return (yield from (self.city_helper_ae2a,self.city_helper_ae55,self.city_helper_af12,self.city_helper_afae,self.city_helper_b047,self.city_helper_b0cf,self.city_helper_b190,self.city_helper_b21b,self.city_helper_b243,self.city_helper_b278,self.city_helper_b33c,self.city_helper_b36d,self.city_helper_b40e,self.city_helper_b431,self.city_helper_b45d,self.city_helper_b47a,self.city_helper_b507,self.city_helper_b528,self.city_helper_b592,self.city_helper_b5a6,self.city_helper_b6f1,self.city_helper_b5dc,self.city_helper_b73e,self.city_helper_b620,self.city_helper_b670,)[index]())

    def city_helper_ae2a(self):
        """$AE2A: city helper ae2a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE2A)
        self._a(m[0x0140])
        self._mark(0xAE2D)
        if not r.p&Z:
            self._mark(0xAE54)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xAE34)
            if not r.p&Z:
                self._mark(0xAE54)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xAE39,0xAE3C)):return
                m[0x0473]=r.a
                m[0x00A4]=r.a
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x03)
                self._a(r.a | m[0x0150])
                m[0x0150]=r.a
                self._a(0x60)
                self._mark(0xAE51)
                yield from self._external(0xAE51,0xF26D,None,"tail")
                return

    def city_helper_ae55(self):
        """$AE55: city helper ae55; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAE55)
        self._a(0xFF)
        m[0x0010]=r.a
        self._a(0xAE)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xAE64,0xED1E,0xAE67,"call",None)
        if r.pc!=0xAE67:return  # preserve nonlocal stack return
        self._a(0x05)
        m[0x0010]=r.a
        self._a(0xAF)
        m[0x0011]=r.a
        self._a(0x0D)
        m[0x0000]=r.a
        self._a(0xAF)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xAE7E,0xEDF5,0xAE81,"call",None)
        if r.pc!=0xAE81:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xAE81,0xAE84)):return
        self._mark(0xAE84)
        if not r.p&C:
            self._mark(0xAEFE)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xAE8A)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAEEF)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xAEF1,0xAEF4)):return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xAEFE)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xAE8F)
                if not r.p&Z:
                    self._compare(r.a,0x01)
                    self._mark(0xAEA4)
                    if not r.p&Z:
                        self._compare(r.a,0x02)
                        self._mark(0xAEB2)
                        if not r.p&Z:
                            self._y(0x01)
                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                            self._compare(r.a,m[CITY])
                            self._mark(0xAECB)
                            if not r.p&Z:
                                self._a(0x14)
                                m[PHASE]=r.a
                                if not (yield from self._local_call(self.city_helper_dd70,0xAEDC,0xAEDF)):return
                                self._a(0x80)
                                m[0x0478]=r.a
                                self._a(0x0F)
                                m[0x047C]=r.a
                                self._a(0x6C)
                                self._mark(0xAEEB)
                                yield from self._external(0xAEEB,0xF26D,None,"tail")
                                return
                            else:
                                self._a(0x16)
                                m[PHASE]=r.a
                                self._a(0x49)
                                self._mark(0xAED4)
                                yield from self._external(0xAED4,0xF26D,None,"tail")
                                return
                        else:
                            self._a(0x0E)
                            m[PHASE]=r.a
                            if not (yield from self._local_call(self.city_helper_dd70,0xAEB9,0xAEBC)):return
                            m[0x046C]=r.a
                            self._a(0x29)
                            self._mark(0xAEC1)
                            yield from self._external(0xAEC1,0xF26D,None,"tail")
                            return
                    else:
                        self._a(0x09)
                        m[PHASE]=r.a
                        self._a(0x68)
                        self._mark(0xAEAD)
                        yield from self._external(0xAEAD,0xF26D,None,"tail")
                        return
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xAE91,0xAE94)):return
                    self._a(m[CITY])
                    m[WORLD_CURSOR]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x61)
                    self._mark(0xAE9F)
                    yield from self._external(0xAE9F,0xF26D,None,"tail")
                    return

    def city_helper_af12(self):
        """$AF12: city helper af12; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAF12)
        if not (yield from self._local_call(self.world_selection_portrait,0xAF12,0xAF15)):return
        if not (yield from self._local_call(self.text_request_readiness,0xAF15,0xAF18)):return
        self._mark(0xAF18)
        if not r.p&C:
            self._mark(0xAF37)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xAF1E)
            if r.p&C:
                if not (yield from self._local_call(self.city_at_cursor,0xAF38,0xAF3B)):return
                self._compare(r.y,0xFF)
                self._mark(0xAF3D)
                if r.p&Z:
                    self._a(0x24)
                    self._mark(0xAFA6)
                    yield from self._external(0xAFA6,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    if not (yield from self._local_call(self.city_helper_dd79,0xAF42,0xAF45)):return
                    self._a(m[CITY])
                    self._mark(0xAF48)
                    if r.p&N:
                        self._a(0x62)
                        self._mark(0xAFAB)
                        yield from self._external(0xAFAB,0xF26D,None,"tail")
                        return
                    else:
                        m[CURRENT_CITY]=r.a
                        m[0x050E]=r.a
                        self._a(m[0x0010])
                        self._compare(r.a,m[0x6F03])
                        self._mark(0xAF56)
                        if r.p&Z:
                            self._a(0x62)
                            self._mark(0xAFAB)
                            yield from self._external(0xAFAB,0xF26D,None,"tail")
                            return
                        else:
                            self._a(m[0x6F03])
                            yield from self._external(0xAF5B,0xF368,0xAF5E,"call",None)
                            if r.pc!=0xAF5E:return  # preserve nonlocal stack return
                            self._a(m[0x0010])
                            r.a=self._shift(r.a,False,rotate=False)
                            self._flag(C,False)
                            self._add(0x04)
                            self._y(r.a)
                            self._a(m[0x0010])
                            self._a(r.a & 0x01)
                            self._mark(0xAF6B)
                            if r.p&Z:
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._a(r.a & 0x0F)
                                self._mark(0xAF7C)
                                if not r.p&Z:
                                    self._a(0x41)
                                    self._mark(0xAFA1)
                                    yield from self._external(0xAFA1,0xF26D,None,"tail")
                                    return
                                else:
                                    self._a(m[WORLD_CURSOR])
                                    m[CITY]=r.a
                                    yield from self._external(0xAF84,0xF2AF,0xAF87,"call",None)
                                    if r.pc!=0xAF87:return  # preserve nonlocal stack return
                                    if not (yield from self._local_call(self.city_helper_dc6b,0xAF87,0xAF8A)):return
                                    m[0x047C]=r.x
                                    self._a(0xFF)
                                    m[0x04E4]=r.a
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(0x81)
                                    m[0x0478]=r.a
                                    self._a(0x27)
                                    self._mark(0xAF9C)
                                    yield from self._external(0xAF9C,0xF26D,None,"tail")
                                    return
                            else:
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                self._mark(0xAF73)
                                if not r.p&Z:
                                    self._a(0x41)
                                    self._mark(0xAFA1)
                                    yield from self._external(0xAFA1,0xF26D,None,"tail")
                                    return
                                else:
                                    self._a(m[WORLD_CURSOR])
                                    m[CITY]=r.a
                                    yield from self._external(0xAF84,0xF2AF,0xAF87,"call",None)
                                    if r.pc!=0xAF87:return  # preserve nonlocal stack return
                                    if not (yield from self._local_call(self.city_helper_dc6b,0xAF87,0xAF8A)):return
                                    m[0x047C]=r.x
                                    self._a(0xFF)
                                    m[0x04E4]=r.a
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(0x81)
                                    m[0x0478]=r.a
                                    self._a(0x27)
                                    self._mark(0xAF9C)
                                    yield from self._external(0xAF9C,0xF26D,None,"tail")
                                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xAF21)
                if not r.p&C:
                    pass
                else:
                    self._a(0xFF)
                    m[0x04E4]=r.a
                    if not (yield from self._local_call(self.text_request_readiness,0xAF28,0xAF2B)):return
                    self._mark(0xAF2B)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0x03)
                        if not (yield from self._local_call(self.city_helper_d58c,0xAF34,0xAF37)):return
                        pass
                    pass
                self._mark(0xAF37)
                self._rts();return

    def city_helper_afae(self):
        """$AFAE: city helper afae; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xAFAE)
        self._a(m[0x0478])
        self._mark(0xAFB1)
        if not r.p&Z:
            self._mark(0xAFD8)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xAFB3,0xAFB6)):return
            self._a(m[0x047C])
            self._mark(0xAFB9)
            if not r.p&N:
                self._mark(0xAFD8)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xAFBD)
                if not r.p&Z:
                    self._a(0x03)
                    if not (yield from self._local_call(self.city_helper_d58c,0xAFDB,0xAFDE)):return
                    self._x(0x00)
                    m[0x0010]=r.x
                    m[0x0011]=r.x
                    while True:  # natural loop $AFE6
                        self._a(m[(0x0481+r.x)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xAFEB)
                        if r.p&Z:
                            pass
                        else:
                            yield from self._external(0xAFED,0xF2D7,0xAFF0,"call",None)
                            if r.pc!=0xAFF0:return  # preserve nonlocal stack return
                            self._y(0x08)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._flag(C,False)
                            self._add(m[0x0010])
                            m[0x0010]=r.a
                            self._y(r.y+1)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._add(m[0x0011])
                            m[0x0011]=r.a
                            self._x(r.x+1)
                            self._compare(r.x,0x0A)
                            self._mark(0xB007)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            pass
                        self._a(m[0x0010])
                        m[0x042C]=r.a
                        self._a(m[0x0011])
                        m[0x042D]=r.a
                        self._a(0x00)
                        m[0x042E]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(m[WORLD_CURSOR])
                        yield from self._external(0xB020,0xF2AF,0xB023,"call",None)
                        if r.pc!=0xB023:return  # preserve nonlocal stack return
                        if not (yield from self._local_call(self.city_helper_dc6b,0xB023,0xB026)):return
                        m[0x0002]=r.x
                        self._y(0x00)
                        self._x(0x00)
                        while True:  # natural loop $B02D
                            self._a(m[(0x0481+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xB032)
                            if r.p&Z:
                                pass
                            else:
                                self._x(r.x+1)
                                pass
                            self._y(r.y+1)
                            self._compare(r.y,0x0A)
                            self._mark(0xB038)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._compare(r.x,m[0x0002])
                            self._mark(0xB03D)
                            if not r.p&Z:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                if not (yield from self._local_call(self.city_helper_db87,0xB08F,0xB092)):return
                                self._a(m[CITY])
                                yield from self._external(0xB095,0xF2AF,0xB098,"call",None)
                                if r.pc!=0xB098:return  # preserve nonlocal stack return
                                self._y(0x02)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x0498]=r.a
                                m[0x0490]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x0499]=r.a
                                m[0x0491]=r.a
                                self._y(0x04)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x049A]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x049B]=r.a
                                self._a(0x00)
                                m[0x0472]=r.a
                                self._a(0x63)
                                self._mark(0xB0BF)
                                yield from self._external(0xB0BF,0xF26D,None,"tail")
                                return
                            else:
                                if not (yield from self._local_call(self.city_helper_dd70,0xB03F,0xB042)):return
                                self._a(0x32)
                                self._mark(0xB044)
                                yield from self._external(0xB044,0xF26D,None,"tail")
                                return
                else:
                    self._a(0x02)
                    m[PHASE]=r.a
                    self._a(m[0x046D])
                    m[0x6F3F]=r.a
                    self._a(m[0x046E])
                    m[0x6F41]=r.a
                    if not (yield from self._local_call(self.city_helper_d568,0xAFD0,0xAFD3)):return
                    self._a(0x61)
                    self._mark(0xAFD5)
                    yield from self._external(0xAFD5,0xF26D,None,"tail")
                    return

    def city_helper_b047(self):
        """$B047: city helper b047; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB047)
        self._a(0xC2)
        m[0x0010]=r.a
        self._a(0xB0)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xB056,0xED1E,0xB059,"call",None)
        if r.pc!=0xB059:return  # preserve nonlocal stack return
        self._a(0xC6)
        m[0x0010]=r.a
        self._a(0xB0)
        m[0x0011]=r.a
        self._a(0xCA)
        m[0x0000]=r.a
        self._a(0xB0)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xB070,0xEDF5,0xB073,"call",None)
        if r.pc!=0xB073:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xB073,0xB076)):return
        self._mark(0xB076)
        if not r.p&C:
            self._mark(0xB086)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB07C)
            if r.p&C:
                self._a(m[0x0012])
                self._mark(0xB08A)
                if not r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xB086)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_db87,0xB08F,0xB092)):return
                    self._a(m[CITY])
                    yield from self._external(0xB095,0xF2AF,0xB098,"call",None)
                    if r.pc!=0xB098:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0498]=r.a
                    m[0x0490]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0499]=r.a
                    m[0x0491]=r.a
                    self._y(0x04)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x049A]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x049B]=r.a
                    self._a(0x00)
                    m[0x0472]=r.a
                    self._a(0x63)
                    self._mark(0xB0BF)
                    yield from self._external(0xB0BF,0xF26D,None,"tail")
                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB07F)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xB086)
                self._rts();return

    def city_helper_b0cf(self):
        """$B0CF: city helper b0cf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB0CF)
        if not (yield from self._local_call(self.text_request_readiness,0xB0CF,0xB0D2)):return
        self._mark(0xB0D2)
        if not r.p&C:
            self._mark(0xB126)
            self._rts();return
        else:
            self._a(m[0x0472])
            self._mark(0xB0D7)
            if not r.p&Z:
                self._compare(r.a,0x01)
                self._mark(0xB129)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_db87,0xB12B,0xB12E)):return
                    self._a(m[0x049A])
                    m[0x0490]=r.a
                    self._a(m[0x049B])
                    m[0x0491]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._a(m[0x0472])
                    pass
                self._a(0x38)
                m[0x031C]=r.a
                self._a(0x23)
                m[0x031D]=r.a
                if not (yield from self._local_call(self.city_helper_da02,0xB14A,0xB14D)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB151)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xB179)
                    if not r.p&C:
                        self._mark(0xB126)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.city_helper_db87,0xB17B,0xB17E)):return
                        self._a(m[0x0498])
                        m[0x0490]=r.a
                        self._a(m[0x0499])
                        m[0x0491]=r.a
                        self._a(0x00)
                        m[0x0472]=r.a
                        self._mark(0xB18F)
                        self._rts();return
                else:
                    self._a(m[0x048E])
                    m[0x0432]=r.a
                    m[0x0524]=r.a
                    self._a(m[0x048F])
                    m[0x0433]=r.a
                    m[0x0525]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xB165,0xB168)):return
                    m[0x0434]=r.a
                    m[0x046C]=r.a
                    self._a(0x06)
                    m[PHASE]=r.a
                    self._a(0x65)
                    self._mark(0xB175)
                    yield from self._external(0xB175,0xF26D,None,"tail")
                    return
            else:
                self._a(0x2E)
                m[0x031C]=r.a
                self._a(0x23)
                m[0x031D]=r.a
                if not (yield from self._local_call(self.city_helper_da02,0xB0E3,0xB0E6)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB0EA)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xB108)
                    if not r.p&C:
                        self._mark(0xB126)
                        self._rts();return
                    else:
                        m[PHASE]=self._nz(m[PHASE]-1)
                        m[PHASE]=self._nz(m[PHASE]-1)
                        self._a(m[CITY])
                        yield from self._external(0xB113,0xF2AF,0xB116,"call",None)
                        if r.pc!=0xB116:return  # preserve nonlocal stack return
                        if not (yield from self._local_call(self.city_helper_dc6b,0xB116,0xB119)):return
                        m[0x047C]=r.x
                        self._a(0x81)
                        m[0x0478]=r.a
                        self._a(0x27)
                        self._mark(0xB123)
                        yield from self._external(0xB123,0xF26D,None,"tail")
                        return
                else:
                    self._a(m[0x048E])
                    m[0x042F]=r.a
                    m[0x0528]=r.a
                    self._a(m[0x048F])
                    m[0x0430]=r.a
                    m[0x0529]=r.a
                    self._a(0x00)
                    m[0x0431]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._mark(0xB106)
                    self._rts();return

    def city_helper_b190(self):
        """$B190: city helper b190; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB190)
        self._a(0x0E)
        m[0x0010]=r.a
        self._a(0xB2)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xB19F,0xED1E,0xB1A2,"call",None)
        if r.pc!=0xB1A2:return  # preserve nonlocal stack return
        self._a(0x12)
        m[0x0010]=r.a
        self._a(0xB2)
        m[0x0011]=r.a
        self._a(0x16)
        m[0x0000]=r.a
        self._a(0xB2)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xB1B9,0xEDF5,0xB1BC,"call",None)
        if r.pc!=0xB1BC:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xB1BC,0xB1BF)):return
        self._mark(0xB1BF)
        if not r.p&C:
            self._mark(0xB20D)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB1C5)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB206)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xB20D)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xB1CA)
                if not r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xB20D)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._y(0x00)
                    self._x(0x00)
                    while True:  # natural loop $B1D3
                        self._a(m[(0x0481+r.y)&65535])
                        m[(0x0151+r.y)&65535]=r.a
                        self._compare(r.a,0xFF)
                        self._mark(0xB1DB)
                        if r.p&Z:
                            pass
                        else:
                            self._x(r.x+1)
                            pass
                        self._y(r.y+1)
                        self._compare(r.y,0x0A)
                        self._mark(0xB1E1)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._compare(r.x,0x02)
                        self._mark(0xB1E5)
                        if r.p&C:
                            self._y(0x00)
                            self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
                            self._compare(r.a,m[0x0481])
                            self._mark(0xB1F1)
                            if not r.p&Z:
                                self._a(0x81)
                                m[0x0478]=r.a
                                self._a(0xFF)
                                m[0x047C]=r.a
                                self._a(0x66)
                                self._mark(0xB202)
                                yield from self._external(0xB202,0xF26D,None,"tail")
                                return
                            else:
                                m[PHASE]=self._nz(m[PHASE]+1)
                                if not (yield from self._local_call(self.city_helper_dd70,0xB238,0xB23B)):return
                                m[0x046C]=r.a
                                self._a(0x29)
                                self._mark(0xB240)
                                yield from self._external(0xB240,0xF26D,None,"tail")
                                return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            if not (yield from self._local_call(self.city_helper_dd70,0xB238,0xB23B)):return
                            m[0x046C]=r.a
                            self._a(0x29)
                            self._mark(0xB240)
                            yield from self._external(0xB240,0xF26D,None,"tail")
                            return

    def city_helper_b21b(self):
        """$B21B: city helper b21b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB21B)
        self._a(m[0x0478])
        self._mark(0xB21E)
        if not r.p&Z:
            self._mark(0xB231)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xB220,0xB223)):return
            self._a(m[0x047C])
            self._mark(0xB226)
            if not r.p&N:
                self._mark(0xB231)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xB22A)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xB232,0xB235)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xB238,0xB23B)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xB240)
                    yield from self._external(0xB240,0xF26D,None,"tail")
                    return
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xB231)
                    self._rts();return

    def city_helper_b243(self):
        """$B243: city helper b243; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB243)
        if not (yield from self._local_call(self.city_helper_d5bd,0xB243,0xB246)):return
        self._a(m[0x0013])
        self._mark(0xB249)
        if r.p&Z:
            self._mark(0xB254)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xB24D)
            if not r.p&Z:
                self._y(0x39)
                yield from self._external(0xB257,0xEE07,0xB25C,"far_call",40981)
                if r.pc!=0xB25C:return  # preserve nonlocal stack return
                self._a(0x01)
                m[0x04A2]=r.a
                self._a(0x47)
                m[0x04D6]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xB266,0xB269)):return
                self._a(0x12)
                m[PHASE]=r.a
                self._a(0x00)
                m[0x0473]=r.a
                self._a(0x67)
                self._mark(0xB275)
                yield from self._external(0xB275,0xF26D,None,"tail")
                return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xB254)
                self._rts();return

    def city_helper_b278(self):
        """$B278: city helper b278; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB278)
        if not (yield from self._local_call(self.text_request_readiness,0xB278,0xB27B)):return
        self._mark(0xB27B)
        if not r.p&C:
            self._mark(0xB293)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xB27D,0xB280)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB284)
            if r.p&C:
                self._a(m[CITY])
                yield from self._external(0xB297,0xF2AF,0xB29A,"call",None)
                if r.pc!=0xB29A:return  # preserve nonlocal stack return
                self._y(0x0C)
                self._a(0x10)
                self._flag(C,True)
                self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
                m[0x0010]=r.a
                self._y(r.y+1)
                self._a(0x27)
                self._add(m[((m[0x00]|m[0x01]<<8)+r.y)&65535],subtract=True)
                m[0x0011]=r.a
                self._mark(0xB2AC)
                if r.p&C:
                    self._y(0x03)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0002]=r.a
                    self._y(r.y-1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    self._a(0x14)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    yield from self._external(0xB2D0,0xEA7C,0xB2D3,"call",None)
                    if r.pc!=0xB2D3:return  # preserve nonlocal stack return
                    self._a(m[0x0001])
                    m[0x0000]=r.a
                    self._a(m[0x0002])
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._a(0x64)
                    m[0x0003]=r.a
                    yield from self._external(0xB2E9,0xEBE9,0xB2EC,"call",None)
                    if r.pc!=0xB2EC:return  # preserve nonlocal stack return
                    self._a(m[0x0006])
                    m[0x0000]=r.a
                    self._a(m[0x0007])
                    m[0x0001]=r.a
                    self._a(m[0x0010])
                    self._flag(C,True)
                    self._add(m[0x0000],subtract=True)
                    self._a(m[0x0011])
                    self._add(m[0x0001],subtract=True)
                    self._mark(0xB305)
                    if r.p&C:
                        pass
                    else:
                        self._a(m[0x0010])
                        m[0x0000]=r.a
                        self._a(m[0x0011])
                        m[0x0001]=r.a
                        pass
                    self._a(0x00)
                    m[0x0002]=r.a
                    m[0x0004]=r.a
                    self._a(0x64)
                    m[0x0003]=r.a
                    self._a(0x00)
                    yield from self._external(0xB322,0xEAA5,0xB325,"call",None)
                    if r.pc!=0xB325:return  # preserve nonlocal stack return
                    pass
                else:
                    self._a(0x00)
                    m[0x0000]=r.a
                    m[0x0001]=r.a
                    pass
                self._a(m[0x0000])
                m[0x0490]=r.a
                self._a(m[0x0001])
                m[0x0491]=r.a
                if not (yield from self._local_call(self.city_helper_db87,0xB331,0xB334)):return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x69)
                self._mark(0xB339)
                yield from self._external(0xB339,0xF26D,None,"tail")
                return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB287)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.text_request_readiness,0xB289,0xB28C)):return
                    self._mark(0xB28C)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        pass
                    pass
                self._mark(0xB293)
                self._rts();return

    def city_helper_b33c(self):
        """$B33C: city helper b33c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB33C)
        if not (yield from self._local_call(self.text_request_readiness,0xB33C,0xB33F)):return
        self._mark(0xB33F)
        if not r.p&C:
            self._mark(0xB36C)
            self._rts();return
        else:
            self._a(0xD0)
            m[0x031C]=r.a
            self._a(0x22)
            m[0x031D]=r.a
            self._a(0x02)
            if not (yield from self._local_call(self.city_helper_da04,0xB34D,0xB350)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB354)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB365)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xB36C)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_helper_dd70,0xB356,0xB359)):return
                m[0x046C]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x29)
                self._mark(0xB361)
                yield from self._external(0xB361,0xF26D,None,"tail")
                return

    def city_helper_b36d(self):
        """$B36D: city helper b36d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB36D)
        if not (yield from self._local_call(self.city_helper_d5bd,0xB36D,0xB370)):return
        self._a(m[0x0013])
        self._mark(0xB373)
        if r.p&Z:
            self._mark(0xB37E)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xB377)
            if not r.p&Z:
                self._a(m[0x048E])
                m[0x0000]=r.a
                self._a(m[0x048F])
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                self._a(0x14)
                m[0x0003]=r.a
                yield from self._external(0xB395,0xEBE9,0xB398,"call",None)
                if r.pc!=0xB398:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x0010]=r.a
                self._a(m[0x0007])
                m[0x0011]=r.a
                self._a(m[0x048E])
                m[0x0000]=r.a
                self._a(m[0x048F])
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                self._a(0x64)
                m[0x0003]=r.a
                yield from self._external(0xB3BA,0xEBE9,0xB3BD,"call",None)
                if r.pc!=0xB3BD:return  # preserve nonlocal stack return
                self._a(m[CITY])
                yield from self._external(0xB3C0,0xF2AF,0xB3C3,"call",None)
                if r.pc!=0xB3C3:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x0010],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0011],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x0C)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x0006])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                m[0x042C]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0007])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                m[0x042D]=r.a
                self._a(0x00)
                m[0x042E]=r.a
                self._a(0x1A)
                m[0x04A2]=r.a
                self._a(0x4D)
                m[0x04D6]=r.a
                self._a(0x12)
                m[PHASE]=r.a
                self._a(0xFF)
                m[0x0473]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xB406,0xB409)):return
                self._a(0x00)
                self._mark(0xB40B)
                yield from self._external(0xB40B,0xF29B,None,"tail")
                return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xB37E)
                self._rts();return

    def city_helper_b40e(self):
        """$B40E: city helper b40e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB40E)
        if not (yield from self._local_call(self.text_request_readiness,0xB40E,0xB411)):return
        self._mark(0xB411)
        if not r.p&C:
            self._mark(0xB430)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xB413,0xB416)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xB41B)
            if not r.p&Z:
                self._a(0x81)
                m[0x0478]=r.a
                self._a(0x10)
                m[0x047C]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x6A)
                self._mark(0xB42D)
                yield from self._external(0xB42D,0xF26D,None,"tail")
                return
            else:
                self._mark(0xB41D)
                self._rts();return

    def city_helper_b431(self):
        """$B431: city helper b431; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB431)
        self._a(m[0x0478])
        self._mark(0xB434)
        if not r.p&Z:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xB436,0xB439)):return
            self._a(m[0x047C])
            self._mark(0xB43C)
            if not r.p&N:
                pass
            else:
                self._a(m[CITY])
                yield from self._external(0xB441,0xF2AF,0xB444,"call",None)
                if r.pc!=0xB444:return  # preserve nonlocal stack return
                self._y(0x0C)
                self._a(m[0x042C])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[0x042D])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xB451,0xB454)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xB45C)
        self._rts();return

    def city_helper_b45d(self):
        """$B45D: city helper b45d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB45D)
        if not (yield from self._local_call(self.city_helper_d5bd,0xB45D,0xB460)):return
        self._a(m[0x0013])
        self._mark(0xB463)
        if r.p&Z:
            self._mark(0xB479)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xB467)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xB479)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_d568,0xB46C,0xB46F)):return
                self._a(0x6B)
                self._mark(0xB471)
                yield from self._external(0xB471,0xF26D,None,"tail")
                return

    def city_helper_b47a(self):
        """$B47A: city helper b47a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB47A)
        if not (yield from self._local_call(self.world_selection_portrait,0xB47A,0xB47D)):return
        if not (yield from self._local_call(self.text_request_readiness,0xB47D,0xB480)):return
        self._mark(0xB480)
        if not r.p&C:
            self._mark(0xB479)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB486)
            if r.p&C:
                if not (yield from self._local_call(self.city_at_cursor,0xB4AA,0xB4AD)):return
                self._compare(r.y,0xFF)
                self._mark(0xB4AF)
                if r.p&Z:
                    self._a(0x24)
                    self._mark(0xB4A7)
                    yield from self._external(0xB4A7,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    self._a(r.y)
                    yield from self._external(0xB4B5,0xF2AF,0xB4B8,"call",None)
                    if r.pc!=0xB4B8:return  # preserve nonlocal stack return
                    self._a(0x80)
                    m[0x0140]=r.a
                    self._x(0x01)
                    self._y(0x80)
                    self._a(m[0x6F3F])
                    self._mark(0xB4C4)
                    if r.p&N:
                        pass
                    else:
                        self._x(0x81)
                        self._y(0x40)
                        pass
                    m[0x0150]=r.x
                    self._a(0xFF)
                    m[0x04E4]=r.a
                    self._a(0x00)
                    m[0x0472]=r.a
                    self._a(0x01)
                    m[0x0473]=r.a
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x07)
                    self._mark(0xB4E2)
                    if not r.p&Z:
                        self._a(0x00)
                        m[STATE]=r.a
                        self._a(0x02)
                        m[PHASE]=r.a
                        self._a(0x03)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x10)
                        m[CURRENT_CITY]=r.a
                        self._a(0x00)
                        self._mark(0xB504)
                        yield from self._external(0xB504,0xF26D,None,"tail")
                        return
                    else:
                        self._a(0x17)
                        m[PHASE]=r.a
                        self._a(0xB7)
                        self._mark(0xB4EB)
                        yield from self._external(0xB4EB,0xF26D,None,"tail")
                        return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB489)
                if not r.p&C:
                    self._mark(0xB479)
                    self._rts();return
                else:
                    self._a(0xFF)
                    m[0x04E4]=r.a
                    if not (yield from self._local_call(self.text_request_readiness,0xB490,0xB493)):return
                    self._mark(0xB493)
                    if not r.p&C:
                        self._mark(0xB479)
                        self._rts();return
                    else:
                        self._a(0x11)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.city_helper_dd70,0xB49A,0xB49D)):return
                        m[0x04E4]=r.a
                        self._a(0x6D)
                        self._mark(0xB4A2)
                        yield from self._external(0xB4A2,0xF26D,None,"tail")
                        return

    def city_helper_b507(self):
        """$B507: city helper b507; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB507)
        self._a(0x80)
        m[0x0140]=r.a
        self._x(0x00)
        self._a(m[0x6F3F])
        self._mark(0xB511)
        if r.p&N:
            pass
        else:
            self._x(0x80)
            pass
        m[0x0150]=r.x
        if not (yield from self._local_call(self.city_helper_dd70,0xB518,0xB51B)):return
        m[PHASE]=self._nz(m[PHASE]+1)
        self._a(0x00)
        m[0x04E4]=r.a
        self._a(0x6D)
        self._mark(0xB525)
        yield from self._external(0xB525,0xF26D,None,"tail")
        return

    def city_helper_b528(self):
        """$B528: city helper b528; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB528)
        self._a(0x85)
        m[0x0010]=r.a
        self._a(0xB5)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xB537,0xED1E,0xB53A,"call",None)
        if r.pc!=0xB53A:return  # preserve nonlocal stack return
        self._a(0x89)
        m[0x0010]=r.a
        self._a(0xB5)
        m[0x0011]=r.a
        self._a(0x8D)
        m[0x0000]=r.a
        self._a(0xB5)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xB551,0xEDF5,0xB554,"call",None)
        if r.pc!=0xB554:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xB554,0xB557)):return
        self._mark(0xB557)
        if not r.p&C:
            self._mark(0xB584)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB55D)
            if not r.p&C:
                self._mark(0xB584)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xB562)
                if not r.p&Z:
                    self._a(m[0x046D])
                    m[0x6F3F]=r.a
                    self._a(m[0x046E])
                    m[0x6F41]=r.a
                    self._a(0x00)
                    m[STATE]=r.a
                    m[PHASE]=r.a
                    self._a(0x03)
                    self._mark(0xB584)
                    self._rts();return
                else:
                    self._a(0x0F)
                    m[PHASE]=r.a
                    self._a(0x6B)
                    self._mark(0xB56B)
                    yield from self._external(0xB56B,0xF26D,None,"tail")
                    return

    def city_helper_b592(self):
        """$B592: city helper b592; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB592)
        self._a(m[0x0140])
        self._mark(0xB595)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x04A2])
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x20)
            m[0x046C]=r.a
            pass
        self._mark(0xB5A5)
        self._rts();return

    def city_helper_b5a6(self):
        """$B5A6: city helper b5a6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB5A6)
        self._a(m[0x04A0])
        self._mark(0xB5A9)
        if not r.p&Z:
            self._mark(0xB5DB)
            self._rts();return
        else:
            self._a(m[0x0140])
            self._mark(0xB5AE)
            if not r.p&Z:
                self._mark(0xB5DB)
                self._rts();return
            else:
                self._a(m[0x0473])
                self._mark(0xB5B3)
                if r.p&N:
                    self._a(0x03)
                    if not (yield from self._local_call(self.city_helper_d58c,0xB5D3,0xB5D6)):return
                    self._a(0x0C)
                    m[PHASE]=r.a
                    self._mark(0xB5DB)
                    self._rts();return
                else:
                    self._a(m[0x0507])
                    self._a(r.a & 0x0F)
                    self._compare(r.a,0x07)
                    self._mark(0xB5BC)
                    if r.p&Z:
                        return (yield from self.city_helper_b670())
                    else:
                        yield from self._external(0xB5BE,0xECEE,0xB5C1,"call",None)
                        if r.pc!=0xB5C1:return  # preserve nonlocal stack return
                        self._y(0x3D)
                        yield from self._external(0xB5C3,0xEE07,0xB5C8,"far_call",40996)
                        if r.pc!=0xB5C8:return  # preserve nonlocal stack return
                        self._a(0x15)
                        m[PHASE]=r.a
                        self._mark(0xB5CD)
                        self._rts();return

    def city_helper_b5dc(self):
        """$B5DC: city helper b5dc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB5DC)
        self._a(m[REPEAT_BUTTONS])
        self._mark(0xB5DF)
        if not r.p&N:
            pass
        else:
            self._a(0x03)
            m[GLOBAL]=r.a
            self._a(0x00)
            m[PHASE]=r.a
            self._a(0x00)
            m[0x0510]=r.a
            m[0x0511]=r.a
            m[0x0512]=r.a
            m[0x0513]=r.a
            self._a(0x0A)
            m[0x0500]=r.a
            self._a(0x00)
            m[0x0501]=r.a
            m[0x0502]=r.a
            m[0x0503]=r.a
            self._a(0x80)
            m[0x0504]=r.a
            self._a(0x00)
            m[0x0505]=r.a
            self._a(0x00)
            m[0x0506]=r.a
            self._y(0x2C)
            yield from self._external(0xB61A,0xEE07,0xB61F,"far_call",40963)
            if r.pc!=0xB61F:return  # preserve nonlocal stack return
            pass
        self._mark(0xB61F)
        self._rts();return

    def city_helper_b620(self):
        """$B620: city helper b620; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB620)
        self._a(m[0x0472])
        self._mark(0xB623)
        if not r.p&Z:
            self._a(m[0x0140])
            self._mark(0xB62E)
            if not r.p&Z:
                self._mark(0xB66F)
                self._rts();return
            else:
                self._a(m[0x0472])
                self._mark(0xB633)
                if r.p&N:
                    self._a(0x00)
                    m[0x0472]=r.a
                    self._mark(0xB644)
                    self._rts();return
                else:
                    self._mark(0xB635)
                    if r.p&Z:
                        self._a(0x80)
                        m[0x0140]=r.a
                        m[0x0472]=self._nz(m[0x0472]+1)
                        self._mark(0xB64D)
                        self._rts();return
                    else:
                        self._compare(r.a,0x0A)
                        self._mark(0xB639)
                        if r.p&Z:
                            self._a(0x80)
                            m[0x0140]=r.a
                            self._a(m[0x0473])
                            self._a(r.a ^ 0x03)
                            m[0x0473]=r.a
                            self._a(r.a | m[0x0150])
                            m[0x0150]=r.a
                            self._a(0x80)
                            m[0x0472]=r.a
                            self._mark(0xB666)
                            self._rts();return
                        else:
                            m[0x0472]=self._nz(m[0x0472]+1)
                            self._mark(0xB63E)
                            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB629)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB668)
                if not r.p&C:
                    pass
                else:
                    self._a(0x10)
                    m[PHASE]=r.a
                    pass
                self._mark(0xB66F)
                self._rts();return
            else:
                self._a(m[0x0140])
                self._mark(0xB62E)
                if not r.p&Z:
                    self._mark(0xB66F)
                    self._rts();return
                else:
                    self._a(m[0x0472])
                    self._mark(0xB633)
                    if r.p&N:
                        self._a(0x00)
                        m[0x0472]=r.a
                        self._mark(0xB644)
                        self._rts();return
                    else:
                        self._mark(0xB635)
                        if r.p&Z:
                            self._a(0x80)
                            m[0x0140]=r.a
                            m[0x0472]=self._nz(m[0x0472]+1)
                            self._mark(0xB64D)
                            self._rts();return
                        else:
                            self._compare(r.a,0x0A)
                            self._mark(0xB639)
                            if r.p&Z:
                                self._a(0x80)
                                m[0x0140]=r.a
                                self._a(m[0x0473])
                                self._a(r.a ^ 0x03)
                                m[0x0473]=r.a
                                self._a(r.a | m[0x0150])
                                m[0x0150]=r.a
                                self._a(0x80)
                                m[0x0472]=r.a
                                self._mark(0xB666)
                                self._rts();return
                            else:
                                m[0x0472]=self._nz(m[0x0472]+1)
                                self._mark(0xB63E)
                                self._rts();return

    def city_helper_b670(self):
        """$B670: city helper b670; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB670)
        yield from self._external(0xB670,0xE57F,0xB673,"call",None)
        if r.pc!=0xB673:return  # preserve nonlocal stack return
        self._a(0x81)
        yield from self._external(0xB675,0xE673,0xB678,"call",None)
        if r.pc!=0xB678:return  # preserve nonlocal stack return
        self._a(m[CURRENT_CITY])
        yield from self._external(0xB67B,0xF2AF,0xB67E,"call",None)
        if r.pc!=0xB67E:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[0x0526])
        self._flag(C,False)
        self._add(m[0x042F])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[0x0527])
        self._add(m[0x0430])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x02)
        if not (yield from self._local_call(self.city_helper_dddc,0xB694,0xB697)):return
        self._y(0x04)
        self._a(m[0x0522])
        self._flag(C,False)
        self._add(m[0x0432])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[0x0523])
        self._add(m[0x0433])
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(0x04)
        if not (yield from self._local_call(self.city_helper_dddc,0xB6AD,0xB6B0)):return
        self._y(0x00)
        self._a(m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535])
        m[0x000A]=r.a
        self._y(0x11)
        self._x(0x0A)
        while True:  # natural loop $B6BB
            self._a(m[(0x0664+r.x)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xB6C0)
            if r.p&Z:
                pass
            else:
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._compare(r.a,m[0x000A])
                self._mark(0xB6C7)
                if not r.p&Z:
                    pass
                else:
                    self._a(r.y)
                    self._push(r.a)
                    self._a(m[CURRENT_CITY])
                    self._y(0x01)
                    m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
                    self._a(self._pop())
                    self._y(r.a)
                    pass
                self._x(r.x+1)
                self._y(r.y+1)
                self._compare(r.y,0x1B)
                self._mark(0xB6D8)
                if not r.p&C:
                    continue
                else:
                    pass
                pass
            self._a(m[0x0507])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._y(0x00)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(0x00)
            m[STATE]=r.a
            m[PHASE]=r.a
            if not (yield from self._local_call(self.city_helper_d568,0xB6ED,0xB6F0)):return
            self._mark(0xB6F0)
            self._rts();return

    def city_helper_b6f1(self):
        """$B6F1: city helper b6f1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB6F1)
        self._a(m[0x0478])
        self._mark(0xB6F4)
        if not r.p&Z:
            self._mark(0xB707)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xB6F6,0xB6F9)):return
            self._a(m[0x047C])
            self._mark(0xB6FC)
            if not r.p&N:
                self._mark(0xB707)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xB700)
                if not r.p&Z:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xB708,0xB70B)):return
                    self._a(m[CITY])
                    yield from self._external(0xB70E,0xF2AF,0xB711,"call",None)
                    if r.pc!=0xB711:return  # preserve nonlocal stack return
                    self._y(0x11)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0010]=r.a
                    self._y(0x11)
                    while True:  # natural loop $B71A
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,m[0x0481])
                        self._mark(0xB71F)
                        if r.p&Z:
                            pass
                        else:
                            self._y(r.y+1)
                            continue
                        self._a(m[0x0010])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(0x11)
                        self._a(m[0x0481])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        m[0x042C]=r.a
                        self._a(0x16)
                        m[PHASE]=r.a
                        self._a(0x64)
                        self._mark(0xB73B)
                        yield from self._external(0xB73B,0xF26D,None,"tail")
                        return
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xB707)
                    self._rts();return

    def city_helper_b73e(self):
        """$B73E: city helper b73e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB73E)
        if not (yield from self._local_call(self.text_request_readiness,0xB73E,0xB741)):return
        self._mark(0xB741)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xB743,0xB746)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xB74B)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xB74D,0xB750)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                pass
            pass
        self._mark(0xB758)
        self._rts();return

    def resource_commands(self):
        """$B759: resource commands; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB759)
        self._a(m[PHASE])
        self._mark(0xB75C)
        index=self._dispatch(0xB75C,(46975, 47015, 47134, 47255, 47486, 47620, 47822, 47997, 48070, 48358, 48487, 48665, 48901, 48921, 48964, 49001))
        return (yield from (self.city_helper_b77f,self.city_helper_b7a7,self.city_helper_b81e,self.city_helper_b897,self.city_helper_b97e,self.city_helper_ba04,self.city_helper_bace,self.city_helper_bb7d,self.city_helper_bbc6,self.city_helper_bce6,self.city_helper_bd67,self.city_helper_be19,self.city_helper_bf05,self.city_helper_bf19,self.city_helper_bf44,self.city_helper_bf69,)[index]())

    def city_helper_b77f(self):
        """$B77F: city helper b77f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB77F)
        self._a(m[0x0140])
        self._mark(0xB782)
        if not r.p&Z:
            self._mark(0xB7A6)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xB789)
            if not r.p&Z:
                self._mark(0xB7A6)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xB78E,0xB791)):return
                m[0x0473]=r.a
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x04)
                self._a(r.a | m[0x0150])
                m[0x0150]=r.a
                self._a(0x53)
                self._mark(0xB7A3)
                yield from self._external(0xB7A3,0xF26D,None,"tail")
                return

    def city_helper_b7a7(self):
        """$B7A7: city helper b7a7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB7A7)
        self._a(0x12)
        m[0x0010]=r.a
        self._a(0xB8)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xB7B6,0xED19,0xB7B9,"call",None)
        if r.pc!=0xB7B9:return  # preserve nonlocal stack return
        self._a(0x15)
        m[0x0010]=r.a
        self._a(0xB8)
        m[0x0011]=r.a
        self._a(0x19)
        m[0x0000]=r.a
        self._a(0xB8)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xB7D0,0xEDF5,0xB7D3,"call",None)
        if r.pc!=0xB7D3:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xB7D3,0xB7D6)):return
        self._mark(0xB7D6)
        if not r.p&C:
            self._mark(0xB811)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB7DC)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB802)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xB804,0xB807)):return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xB811)
                self._rts();return
            else:
                self._a(m[0x0012])
                self._mark(0xB7E1)
                if not r.p&Z:
                    self._a(0x05)
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xB7F9,0xB7FC)):return
                    self._a(0x58)
                    self._mark(0xB7FE)
                    yield from self._external(0xB7FE,0xF26D,None,"tail")
                    return
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xB7E3,0xB7E6)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(m[CITY])
                    m[WORLD_CURSOR]=r.a
                    self._a(0x54)
                    self._mark(0xB7F1)
                    yield from self._external(0xB7F1,0xF26D,None,"tail")
                    return

    def city_helper_b81e(self):
        """$B81E: city helper b81e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB81E)
        if not (yield from self._local_call(self.world_selection_portrait,0xB81E,0xB821)):return
        if not (yield from self._local_call(self.text_request_readiness,0xB821,0xB824)):return
        self._mark(0xB824)
        if not r.p&C:
            self._mark(0xB83E)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xB82A)
            if r.p&C:
                if not (yield from self._local_call(self.city_at_cursor,0xB83F,0xB842)):return
                self._compare(r.y,0xFF)
                self._mark(0xB844)
                if r.p&Z:
                    self._a(0x24)
                    self._mark(0xB861)
                    yield from self._external(0xB861,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    if not (yield from self._local_call(self.city_helper_dd79,0xB849,0xB84C)):return
                    self._a(m[CITY])
                    self._mark(0xB84F)
                    if r.p&N:
                        self._a(0x55)
                        self._mark(0xB866)
                        yield from self._external(0xB866,0xF26D,None,"tail")
                        return
                    else:
                        m[CURRENT_CITY]=r.a
                        self._a(m[0x0010])
                        self._compare(r.a,m[0x6F03])
                        self._mark(0xB85A)
                        if not r.p&Z:
                            self._a(0x55)
                            self._mark(0xB866)
                            yield from self._external(0xB866,0xF26D,None,"tail")
                            return
                        else:
                            self._y(0x39)
                            yield from self._external(0xB86B,0xEE07,0xB870,"far_call",40984)
                            if r.pc!=0xB870:return  # preserve nonlocal stack return
                            self._a(m[0x0498])
                            m[0x0490]=r.a
                            self._a(m[0x0499])
                            m[0x0491]=r.a
                            self._a(0x04)
                            if not (yield from self._local_call(self.city_helper_d58c,0xB87E,0xB881)):return
                            if not (yield from self._local_call(self.city_helper_db87,0xB881,0xB884)):return
                            if not (yield from self._local_call(self.city_helper_dd70,0xB884,0xB887)):return
                            m[0x0472]=r.a
                            self._a(0xFF)
                            m[0x04E4]=r.a
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x57)
                            self._mark(0xB894)
                            yield from self._external(0xB894,0xF26D,None,"tail")
                            return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB82D)
                if not r.p&C:
                    pass
                else:
                    self._a(0xFF)
                    m[0x04E4]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x04)
                    if not (yield from self._local_call(self.city_helper_d58c,0xB83B,0xB83E)):return
                    pass
                self._mark(0xB83E)
                self._rts();return

    def city_helper_b897(self):
        """$B897: city helper b897; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB897)
        if not (yield from self._local_call(self.text_request_readiness,0xB897,0xB89A)):return
        self._mark(0xB89A)
        if not r.p&C:
            self._mark(0xB916)
            self._rts();return
        else:
            self._a(m[0x0472])
            self._mark(0xB89F)
            if not r.p&Z:
                self._compare(r.a,0x01)
                self._mark(0xB8D4)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_db87,0xB8D6,0xB8D9)):return
                    self._a(m[0x049A])
                    m[0x0490]=r.a
                    self._a(m[0x049B])
                    m[0x0491]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._a(m[0x0472])
                    pass
                self._compare(r.a,0x02)
                self._mark(0xB8ED)
                if not r.p&Z:
                    self._compare(r.a,0x03)
                    self._mark(0xB931)
                    if not r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.city_helper_db87,0xB933,0xB936)):return
                        self._a(m[0x049C])
                        m[0x0490]=r.a
                        self._a(0x00)
                        m[0x0491]=r.a
                        m[0x0472]=self._nz(m[0x0472]+1)
                        pass
                    self._a(0x2E)
                    m[0x031C]=r.a
                    self._a(0x23)
                    m[0x031D]=r.a
                    self._a(0x01)
                    if not (yield from self._local_call(self.city_helper_da04,0xB950,0xB953)):return
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xB957)
                    if r.p&C:
                        self._a(m[0x048E])
                        m[0x0432]=r.a
                        self._a(0x00)
                        m[0x0433]=r.a
                        m[0x0434]=r.a
                        if not (yield from self._local_call(self.city_helper_dd70,0xB970,0xB973)):return
                        m[0x046C]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x29)
                        self._mark(0xB97B)
                        yield from self._external(0xB97B,0xF26D,None,"tail")
                        return
                    else:
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xB95A)
                        if not r.p&C:
                            self._mark(0xB916)
                            self._rts();return
                        else:
                            self._a(0x01)
                            m[0x0472]=r.a
                            self._mark(0xB961)
                            self._rts();return
                else:
                    self._a(0xF8)
                    m[0x031C]=r.a
                    self._a(0x22)
                    m[0x031D]=r.a
                    if not (yield from self._local_call(self.city_helper_da02,0xB8F9,0xB8FC)):return
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xB900)
                    if not r.p&C:
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xB918)
                        if not r.p&C:
                            self._mark(0xB916)
                            self._rts();return
                        else:
                            if not (yield from self._local_call(self.city_helper_db87,0xB91A,0xB91D)):return
                            self._a(m[0x0498])
                            m[0x0490]=r.a
                            self._a(m[0x0499])
                            m[0x0491]=r.a
                            self._a(0x00)
                            m[0x0472]=r.a
                            self._mark(0xB92E)
                            self._rts();return
                    else:
                        self._a(m[0x048E])
                        m[0x042F]=r.a
                        self._a(m[0x048F])
                        m[0x0430]=r.a
                        self._a(0x00)
                        m[0x0431]=r.a
                        m[0x0472]=self._nz(m[0x0472]+1)
                        self._mark(0xB916)
                        self._rts();return
            else:
                self._a(0xEE)
                m[0x031C]=r.a
                self._a(0x22)
                m[0x031D]=r.a
                if not (yield from self._local_call(self.city_helper_da02,0xB8AB,0xB8AE)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xB8B2)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xB8CA)
                    if not r.p&C:
                        self._mark(0xB916)
                        self._rts();return
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._mark(0xB8D1)
                        self._rts();return
                else:
                    self._a(m[0x048E])
                    m[0x042C]=r.a
                    self._a(m[0x048F])
                    m[0x042D]=r.a
                    self._a(0x00)
                    m[0x042E]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._mark(0xB8C8)
                    self._rts();return

    def city_helper_b97e(self):
        """$B97E: city helper b97e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB97E)
        if not (yield from self._local_call(self.city_helper_d5bd,0xB97E,0xB981)):return
        self._a(m[0x0013])
        self._mark(0xB984)
        if r.p&Z:
            self._mark(0xBA03)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xB988)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xBA03)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xB98D,0xF2AF,0xB990,"call",None)
                if r.pc!=0xB990:return  # preserve nonlocal stack return
                self._y(0x02)
                self._x(0x00)
                while True:  # natural loop $B994
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[(0x042C+r.x)&65535],subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._x(r.x+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._add(m[(0x042C+r.x)&65535],subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._x(0x03)
                    self._compare(r.y,0x06)
                    self._mark(0xB9AA)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._y(0x10)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x0432],subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(m[CURRENT_CITY])
                    yield from self._external(0xB9B9,0xF2AF,0xB9BC,"call",None)
                    if r.pc!=0xB9BC:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._x(0x00)
                    while True:  # natural loop $B9C0
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[(0x042C+r.x)&65535])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._add(m[(0x042C+r.x)&65535])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        self._x(0x03)
                        self._compare(r.y,0x06)
                        self._mark(0xB9D6)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._y(0x10)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x0432])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(0x22)
                        m[0x04A2]=r.a
                        self._a(0x32)
                        m[0x04D6]=r.a
                        self._a(0xFF)
                        m[0x0481]=r.a
                        if not (yield from self._local_call(self.city_helper_d568,0xB9F1,0xB9F4)):return
                        self._a(0x0C)
                        m[PHASE]=r.a
                        self._a(0x31)
                        self._mark(0xB9FB)
                        yield from self._external(0xB9FB,0xF26D,None,"tail")
                        return

    def city_helper_ba04(self):
        """$BA04: city helper ba04; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBA04)
        self._a(0xC2)
        m[0x0010]=r.a
        self._a(0xBA)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xBA13,0xED19,0xBA16,"call",None)
        if r.pc!=0xBA16:return  # preserve nonlocal stack return
        self._a(0xC5)
        m[0x0010]=r.a
        self._a(0xBA)
        m[0x0011]=r.a
        self._a(0xC9)
        m[0x0000]=r.a
        self._a(0xBA)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xBA2D,0xEDF5,0xBA30,"call",None)
        if r.pc!=0xBA30:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xBA30,0xBA33)):return
        self._mark(0xBA33)
        if not r.p&C:
            self._mark(0xBA43)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xBA39)
            if r.p&C:
                if not (yield from self._local_call(self.city_helper_dd70,0xBA44,0xBA47)):return
                if not (yield from self._local_call(self.city_helper_db87,0xBA47,0xBA4A)):return
                self._a(m[0x0012])
                self._mark(0xBA4D)
                if not r.p&Z:
                    self._a(m[CITY])
                    yield from self._external(0xBA5A,0xF2AF,0xBA5D,"call",None)
                    if r.pc!=0xBA5D:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x64)
                    self._mark(0xBA63)
                    if not r.p&C:
                        self._a(m[0x0000])
                        m[0x0010]=r.a
                        self._a(m[0x0001])
                        m[0x0011]=r.a
                        self._x(0x64)
                        self._y(0x03)
                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                        self._mark(0xBA81)
                        if not r.p&Z:
                            pass
                        else:
                            self._y(r.y-1)
                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                            self._compare(r.a,0x64)
                            self._mark(0xBA88)
                            if r.p&C:
                                pass
                            else:
                                self._x(r.a)
                                pass
                            pass
                        if not (yield from self._local_call(self.city_helper_bf89,0xBA8B,0xBA8E)):return
                        m[0x0498]=r.x
                        m[0x0490]=r.x
                        self._x(0x64)
                        self._y(0x05)
                        self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                        self._mark(0xBA9A)
                        if not r.p&Z:
                            pass
                        else:
                            self._y(r.y-1)
                            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                            self._compare(r.a,0x64)
                            self._mark(0xBAA1)
                            if r.p&C:
                                pass
                            else:
                                self._x(r.a)
                                pass
                            pass
                        if not (yield from self._local_call(self.city_helper_bf89,0xBAA4,0xBAA7)):return
                        m[0x049A]=r.x
                        self._a(0x00)
                        m[0x0499]=r.a
                        m[0x049B]=r.a
                        m[0x0491]=r.a
                        m[0x0472]=r.a
                        self._a(0x0A)
                        m[PHASE]=r.a
                        self._a(0x59)
                        self._mark(0xBABF)
                        yield from self._external(0xBABF,0xF26D,None,"tail")
                        return
                    else:
                        self._a(0x0E)
                        m[PHASE]=r.a
                        self._a(0xA7)
                        self._mark(0xBA6C)
                        yield from self._external(0xBA6C,0xF26D,None,"tail")
                        return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x7E)
                    self._mark(0xBA54)
                    yield from self._external(0xBA54,0xF26D,None,"tail")
                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBA3C)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xBA43)
                self._rts();return

    def city_helper_bace(self):
        """$BACE: city helper bace; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBACE)
        self._a(0x70)
        m[0x0010]=r.a
        self._a(0xBB)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xBADD,0xED1E,0xBAE0,"call",None)
        if r.pc!=0xBAE0:return  # preserve nonlocal stack return
        self._a(0x74)
        m[0x0010]=r.a
        self._a(0xBB)
        m[0x0011]=r.a
        self._a(0x78)
        m[0x0000]=r.a
        self._a(0xBB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xBAF7,0xEDF5,0xBAFA,"call",None)
        if r.pc!=0xBAFA:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xBAFA,0xBAFD)):return
        self._mark(0xBAFD)
        if not r.p&C:
            self._mark(0xBB6F)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xBB03)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBB60)
                if not r.p&C:
                    self._mark(0xBB6F)
                    self._rts();return
                else:
                    self._a(0x05)
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xBB67,0xBB6A)):return
                    self._a(0x58)
                    self._mark(0xBB6C)
                    yield from self._external(0xBB6C,0xF26D,None,"tail")
                    return
            else:
                self._a(m[CITY])
                yield from self._external(0xBB08,0xF2AF,0xBB0B,"call",None)
                if r.pc!=0xBB0B:return  # preserve nonlocal stack return
                self._a(m[0x0012])
                self._mark(0xBB0E)
                if not r.p&Z:
                    self._y(0x10)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xBB3A)
                    if r.p&Z:
                        self._a(0x0F)
                        m[PHASE]=r.a
                        self._a(0xAC)
                        self._mark(0xBB5C)
                        yield from self._external(0xBB5C,0xF26D,None,"tail")
                        return
                    else:
                        self._a(0x08)
                        m[PHASE]=r.a
                        self._a(0x01)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x80)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        self._a(0x5D)
                        self._mark(0xBB52)
                        yield from self._external(0xBB52,0xF26D,None,"tail")
                        return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._y(0x03)
                    self._x(0x64)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xBB19)
                    if not r.p&Z:
                        pass
                    else:
                        self._y(r.y-1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x64)
                        self._mark(0xBB20)
                        if r.p&C:
                            pass
                        else:
                            self._x(r.a)
                            pass
                        pass
                    if not (yield from self._local_call(self.city_helper_bf89,0xBB23,0xBB26)):return
                    m[0x0490]=r.x
                    self._a(0x00)
                    m[0x0491]=r.a
                    m[WORLD_CURSOR]=r.a
                    self._a(0x5B)
                    self._mark(0xBB33)
                    yield from self._external(0xBB33,0xF26D,None,"tail")
                    return

    def city_helper_bb7d(self):
        """$BB7D: city helper bb7d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBB7D)
        if not (yield from self._local_call(self.text_request_readiness,0xBB7D,0xBB80)):return
        self._mark(0xBB80)
        if not r.p&C:
            self._mark(0xBBC5)
            self._rts();return
        else:
            self._a(0x2F)
            m[0x031C]=r.a
            self._a(0x23)
            m[0x031D]=r.a
            self._a(0x01)
            if not (yield from self._local_call(self.city_helper_da04,0xBB8E,0xBB91)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xBB95)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBBB5)
                if not r.p&C:
                    self._mark(0xBBC5)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]-1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xBBBA,0xBBBD)):return
                    if not (yield from self._local_call(self.city_helper_db87,0xBBBD,0xBBC0)):return
                    self._a(0x7E)
                    self._mark(0xBBC2)
                    yield from self._external(0xBBC2,0xF26D,None,"tail")
                    return
            else:
                self._a(m[0x048E])
                self._mark(0xBB9A)
                if r.p&Z:
                    self._mark(0xBBC5)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_bfa0,0xBB9C,0xBB9F)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    m[0x048E]=r.a
                    self._a(0x80)
                    m[0x0478]=r.a
                    self._a(0x0F)
                    m[0x047C]=r.a
                    self._a(0x5D)
                    self._mark(0xBBB1)
                    yield from self._external(0xBBB1,0xF26D,None,"tail")
                    return

    def city_helper_bbc6(self):
        """$BBC6: city helper bbc6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBBC6)
        self._a(m[0x0478])
        self._mark(0xBBC9)
        if not r.p&Z:
            self._mark(0xBC22)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xBBCB,0xBBCE)):return
            self._a(m[0x047C])
            self._mark(0xBBD1)
            if not r.p&N:
                self._mark(0xBC22)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xBBD5)
                if r.p&Z:
                    self._a(0x06)
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xBC17,0xBC1A)):return
                    if not (yield from self._local_call(self.city_helper_db87,0xBC1A,0xBC1D)):return
                    self._a(0x7E)
                    self._mark(0xBC1F)
                    yield from self._external(0xBC1F,0xF26D,None,"tail")
                    return
                else:
                    self._compare(r.a,0x81)
                    self._mark(0xBBD9)
                    if r.p&Z:
                        self._a(0x0F)
                        m[0x047C]=r.a
                        self._a(0x80)
                        m[0x0478]=r.a
                        self._a(0x4A)
                        self._mark(0xBBF8)
                        yield from self._external(0xBBF8,0xF26D,None,"tail")
                        return
                    else:
                        self._a(m[0x0481])
                        yield from self._external(0xBBDE,0xF2D7,0xBBE1,"call",None)
                        if r.pc!=0xBBE1:return  # preserve nonlocal stack return
                        self._y(0x03)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x5A)
                        self._mark(0xBBE7)
                        if r.p&C:
                            self._a(m[0x0481])
                            m[0x0000]=r.a
                            self._y(0x3D)
                            yield from self._external(0xBC03,0xEE07,0xBC08,"far_call",41002)
                            if r.pc!=0xBC08:return  # preserve nonlocal stack return
                            self._a(0x0E)
                            m[PHASE]=r.a
                            self._a(0x5E)
                            self._mark(0xBC0F)
                            yield from self._external(0xBC0F,0xF26D,None,"tail")
                            return
                        else:
                            self._a(m[CITY])
                            if not (yield from self._local_call(self.city_helper_dd4f,0xBC26,0xBC29)):return
                            yield from self._external(0xBC29,0xF2D7,0xBC2C,"call",None)
                            if r.pc!=0xBC2C:return  # preserve nonlocal stack return
                            self._y(0x04)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(m[WORLD_CURSOR])
                            self._mark(0xBC36)
                            if not r.p&Z:
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                m[0x0004]=r.a
                                self._a(0x0A)
                                m[0x0003]=r.a
                                yield from self._external(0xBC9B,0xEAA5,0xBC9E,"call",None)
                                if r.pc!=0xBC9E:return  # preserve nonlocal stack return
                                self._a(m[0x0000])
                                self._flag(C,False)
                                self._add(0x03)
                                m[0x0000]=r.a
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                while True:  # natural loop $BCAF
                                    yield from self._external(0xBCAF,0xE856,0xBCB2,"call",None)
                                    if r.pc!=0xBCB2:return  # preserve nonlocal stack return
                                    self._compare(r.a,0x07)
                                    self._mark(0xBCB4)
                                    if r.p&Z:
                                        continue
                                    else:
                                        pass
                                    self._flag(C,False)
                                    self._add(0x0A)
                                    m[0x0003]=r.a
                                    yield from self._external(0xBCBC,0xEBE9,0xBCBF,"call",None)
                                    if r.pc!=0xBCBF:return  # preserve nonlocal stack return
                                    self._a(0x0A)
                                    m[0x0003]=r.a
                                    self._a(0x00)
                                    m[0x0004]=r.a
                                    if not (yield from self._local_call(self.city_helper_db72,0xBCC9,0xBCCC)):return
                                    self._a(m[0x0000])
                                    m[0x042C]=r.a
                                    if not (yield from self._local_call(self.city_helper_dd70,0xBCD2,0xBCD5)):return
                                    m[0x042D]=r.a
                                    m[0x042E]=r.a
                                    m[0x046C]=r.a
                                    m[PHASE]=self._nz(m[PHASE]+1)
                                    self._a(0x29)
                                    self._mark(0xBCE3)
                                    yield from self._external(0xBCE3,0xF26D,None,"tail")
                                    return
                            else:
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                m[0x0004]=r.a
                                self._a(0x0A)
                                m[0x0003]=r.a
                                yield from self._external(0xBC48,0xEAA5,0xBC4B,"call",None)
                                if r.pc!=0xBC4B:return  # preserve nonlocal stack return
                                self._a(m[0x0000])
                                m[0x042C]=r.a
                                self._a(m[0x048E])
                                m[0x0000]=r.a
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                m[0x0004]=r.a
                                self._a(0x14)
                                m[0x0003]=r.a
                                yield from self._external(0xBC67,0xEAA5,0xBC6A,"call",None)
                                if r.pc!=0xBC6A:return  # preserve nonlocal stack return
                                self._a(m[0x0000])
                                self._flag(C,False)
                                self._add(m[0x042C])
                                m[0x0000]=r.a
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                yield from self._external(0xBC7C,0xE850,0xBC7F,"call",None)
                                if r.pc!=0xBC7F:return  # preserve nonlocal stack return
                                self._flag(C,False)
                                self._add(0x07)
                                m[0x0003]=r.a
                                yield from self._external(0xBC85,0xEBE9,0xBC88,"call",None)
                                if r.pc!=0xBC88:return  # preserve nonlocal stack return
                                pass
                            self._a(0x0A)
                            m[0x0003]=r.a
                            self._a(0x00)
                            m[0x0004]=r.a
                            if not (yield from self._local_call(self.city_helper_db72,0xBCC9,0xBCCC)):return
                            self._a(m[0x0000])
                            m[0x042C]=r.a
                            if not (yield from self._local_call(self.city_helper_dd70,0xBCD2,0xBCD5)):return
                            m[0x042D]=r.a
                            m[0x042E]=r.a
                            m[0x046C]=r.a
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x29)
                            self._mark(0xBCE3)
                            yield from self._external(0xBCE3,0xF26D,None,"tail")
                            return

    def city_helper_bce6(self):
        """$BCE6: city helper bce6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBCE6)
        if not (yield from self._local_call(self.city_helper_d5bd,0xBCE6,0xBCE9)):return
        self._a(m[0x0013])
        self._mark(0xBCEC)
        if r.p&Z:
            self._mark(0xBD66)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xBCF0)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xBD66)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xBCF5,0xF2AF,0xBCF8,"call",None)
                if r.pc!=0xBCF8:return  # preserve nonlocal stack return
                self._a(m[WORLD_CURSOR])
                self._mark(0xBCFB)
                if not r.p&Z:
                    self._y(0x10)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(0x01,subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    pass
                else:
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x048E],subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._add(0x00,subtract=True)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    pass
                self._a(m[0x0481])
                yield from self._external(0xBD1D,0xF2D7,0xBD20,"call",None)
                if r.pc!=0xBD20:return  # preserve nonlocal stack return
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x042C])
                self._compare(r.a,0x64)
                self._mark(0xBD2A)
                if not r.p&C:
                    pass
                else:
                    m[0x0002]=r.a
                    self._a(0x63)
                    self._flag(C,True)
                    self._add(m[0x0002],subtract=True)
                    self._flag(C,False)
                    self._add(m[0x042C])
                    m[0x042C]=r.a
                    self._a(0x63)
                    pass
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(0x17)
                m[0x04A2]=r.a
                self._a(0x29)
                m[0x04D6]=r.a
                self._a(0x03)
                m[0x00A4]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xBD4F,0xBD52)):return
                self._a(0x0C)
                m[PHASE]=r.a
                self._a(0x5F)
                m[0x0473]=r.a
                self._a(0x00)
                self._mark(0xBD5E)
                yield from self._external(0xBD5E,0xF29B,None,"tail")
                return

    def city_helper_bd67(self):
        """$BD67: city helper bd67; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBD67)
        if not (yield from self._local_call(self.text_request_readiness,0xBD67,0xBD6A)):return
        self._mark(0xBD6A)
        if not r.p&C:
            self._mark(0xBDAB)
            self._rts();return
        else:
            self._a(m[0x0472])
            self._mark(0xBD6F)
            if not r.p&Z:
                self._compare(r.a,0x01)
                self._mark(0xBDAE)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_db87,0xBDB0,0xBDB3)):return
                    self._a(m[0x049A])
                    m[0x0490]=r.a
                    self._a(m[0x049B])
                    m[0x0491]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._a(m[0x0472])
                    pass
                self._a(0x36)
                m[0x031C]=r.a
                self._a(0x23)
                m[0x031D]=r.a
                self._a(0x01)
                if not (yield from self._local_call(self.city_helper_da04,0xBDD1,0xBDD4)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBDD8)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xBE02)
                    if not r.p&C:
                        self._mark(0xBDAB)
                        self._rts();return
                    else:
                        if not (yield from self._local_call(self.city_helper_db87,0xBE04,0xBE07)):return
                        self._a(m[0x0498])
                        m[0x0490]=r.a
                        self._a(m[0x0499])
                        m[0x0491]=r.a
                        self._a(0x00)
                        m[0x0472]=r.a
                        self._mark(0xBE18)
                        self._rts();return
                else:
                    self._a(m[0x048E])
                    if not (yield from self._local_call(self.city_helper_bfa0,0xBDDD,0xBDE0)):return
                    m[0x042F]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xBDE3,0xBDE6)):return
                    m[0x0430]=r.a
                    m[0x0431]=r.a
                    m[0x046C]=r.a
                    self._a(m[0x042C])
                    self._mark(0xBDF2)
                    if not r.p&Z:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x29)
                        self._mark(0xBDFE)
                        yield from self._external(0xBDFE,0xF26D,None,"tail")
                        return
                    else:
                        self._a(m[0x042F])
                        self._mark(0xBDF7)
                        if r.p&Z:
                            self._mark(0xBDAB)
                            self._rts();return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x29)
                            self._mark(0xBDFE)
                            yield from self._external(0xBDFE,0xF26D,None,"tail")
                            return
            else:
                self._a(0x2C)
                m[0x031C]=r.a
                self._a(0x23)
                m[0x031D]=r.a
                self._a(0x01)
                if not (yield from self._local_call(self.city_helper_da04,0xBD7D,0xBD80)):return
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xBD84)
                if not r.p&C:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xBD9C)
                    if not r.p&C:
                        self._mark(0xBDAB)
                        self._rts();return
                    else:
                        self._a(0x05)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.city_helper_dd70,0xBDA3,0xBDA6)):return
                        self._a(0x58)
                        self._mark(0xBDA8)
                        yield from self._external(0xBDA8,0xF26D,None,"tail")
                        return
                else:
                    self._a(m[0x048E])
                    if not (yield from self._local_call(self.city_helper_bfa0,0xBD89,0xBD8C)):return
                    m[0x042C]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x042E]=r.a
                    m[0x0472]=self._nz(m[0x0472]+1)
                    self._mark(0xBD9A)
                    self._rts();return

    def city_helper_be19(self):
        """$BE19: city helper be19; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBE19)
        if not (yield from self._local_call(self.city_helper_d5bd,0xBE19,0xBE1C)):return
        self._a(m[0x0013])
        self._mark(0xBE1F)
        if r.p&Z:
            self._mark(0xBE2A)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xBE23)
            if not r.p&Z:
                self._a(m[CITY])
                yield from self._external(0xBE2E,0xF2AF,0xBE31,"call",None)
                if r.pc!=0xBE31:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042C],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x042D],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042F],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x0430],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(m[CITY])
                yield from self._external(0xBE58,0xF2AF,0xBE5B,"call",None)
                if r.pc!=0xBE5B:return  # preserve nonlocal stack return
                self._y(0x11)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                yield from self._external(0xBE5F,0xF2D7,0xBE62,"call",None)
                if r.pc!=0xBE62:return  # preserve nonlocal stack return
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0003]=r.a
                self._a(m[0x042C])
                self._flag(C,False)
                self._add(m[0x042F])
                m[0x0000]=r.a
                self._a(m[0x042D])
                self._add(m[0x0430])
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                yield from self._external(0xBE81,0xEBE9,0xBE84,"call",None)
                if r.pc!=0xBE84:return  # preserve nonlocal stack return
                self._a(0xD0)
                m[0x0003]=r.a
                self._a(0x07)
                m[0x0004]=r.a
                if not (yield from self._local_call(self.city_helper_db72,0xBE8E,0xBE91)):return
                while True:  # natural loop $BE91
                    yield from self._external(0xBE91,0xE856,0xBE94,"call",None)
                    if r.pc!=0xBE94:return  # preserve nonlocal stack return
                    self._compare(r.a,0x07)
                    self._mark(0xBE96)
                    if r.p&Z:
                        continue
                    else:
                        pass
                    self._flag(C,False)
                    self._add(0x0A)
                    m[0x0003]=r.a
                    yield from self._external(0xBE9E,0xEBE9,0xBEA1,"call",None)
                    if r.pc!=0xBEA1:return  # preserve nonlocal stack return
                    self._a(0x0A)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    if not (yield from self._local_call(self.city_helper_db72,0xBEAB,0xBEAE)):return
                    self._a(m[0x0000])
                    m[0x042C]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x042E]=r.a
                    self._a(m[CITY])
                    yield from self._external(0xBEBF,0xF2AF,0xBEC2,"call",None)
                    if r.pc!=0xBEC2:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x042C])
                    m[0x0002]=r.a
                    self._flag(C,True)
                    self._add(0x64,subtract=True)
                    self._mark(0xBED0)
                    if not r.p&C:
                        pass
                    else:
                        m[0x0002]=r.a
                        self._a(m[0x042C])
                        self._flag(C,True)
                        self._add(m[0x0002],subtract=True)
                        m[0x042C]=r.a
                        self._a(0x64)
                        m[0x0002]=r.a
                        pass
                    self._a(m[0x0002])
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(0x0C)
                    m[0x04A2]=r.a
                    self._a(0x29)
                    m[0x04D6]=r.a
                    self._a(0xFF)
                    m[0x0481]=r.a
                    if not (yield from self._local_call(self.city_helper_d568,0xBEF8,0xBEFB)):return
                    self._a(0x0C)
                    m[PHASE]=r.a
                    self._a(0x5A)
                    self._mark(0xBF02)
                    yield from self._external(0xBF02,0xF26D,None,"tail")
                    return
            else:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xBE2A)
                self._rts();return

    def city_helper_bf05(self):
        """$BF05: city helper bf05; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF05)
        self._a(m[0x0140])
        self._mark(0xBF08)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x04A2])
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x60)
            m[0x046C]=r.a
            pass
        self._mark(0xBF18)
        self._rts();return

    def city_helper_bf19(self):
        """$BF19: city helper bf19; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF19)
        self._a(m[0x04A0])
        self._mark(0xBF1C)
        if not r.p&Z:
            self._mark(0xBF43)
            self._rts();return
        else:
            self._a(m[0x0140])
            self._mark(0xBF21)
            if not r.p&Z:
                self._mark(0xBF43)
                self._rts();return
            else:
                self._a(0x04)
                if not (yield from self._local_call(self.city_helper_d58c,0xBF25,0xBF28)):return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[0x0473])
                self._mark(0xBF2E)
                if r.p&Z:
                    self._mark(0xBF43)
                    self._rts();return
                else:
                    self._a(m[0x0481])
                    m[0x0000]=r.a
                    self._y(0x3D)
                    yield from self._external(0xBF38,0xEE07,0xBF3D,"far_call",41002)
                    if r.pc!=0xBF3D:return  # preserve nonlocal stack return
                    self._a(m[0x0473])
                    self._mark(0xBF40)
                    yield from self._external(0xBF40,0xF26D,None,"tail")
                    return

    def city_helper_bf44(self):
        """$BF44: city helper bf44; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF44)
        if not (yield from self._local_call(self.text_request_readiness,0xBF44,0xBF47)):return
        self._mark(0xBF47)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xBF49,0xBF4C)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xBF51)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xBF53,0xBF56)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                pass
            pass
        self._a(m[0x0481])
        self._compare(r.a,0xFF)
        self._mark(0xBF63)
        if r.p&Z:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_dd5e,0xBF65,0xBF68)):return
            pass
        self._mark(0xBF68)
        self._rts();return

    def city_helper_bf69(self):
        """$BF69: city helper bf69; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF69)
        if not (yield from self._local_call(self.text_request_readiness,0xBF69,0xBF6C)):return
        self._mark(0xBF6C)
        if not r.p&C:
            self._mark(0xBF88)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xBF6E,0xBF71)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xBF76)
            if r.p&Z:
                self._mark(0xBF88)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_helper_dd70,0xBF78,0xBF7B)):return
                if not (yield from self._local_call(self.city_helper_db87,0xBF7B,0xBF7E)):return
                self._a(0x06)
                m[PHASE]=r.a
                self._a(0x7E)
                self._mark(0xBF85)
                yield from self._external(0xBF85,0xF26D,None,"tail")
                return

    def city_helper_bf89(self):
        """$BF89: city helper bf89; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBF89)
        m[0x0001]=r.x
        self._a(0x0A)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        m[0x0004]=r.a
        yield from self._external(0xBF99,0xEA7C,0xBF9C,"call",None)
        if r.pc!=0xBF9C:return  # preserve nonlocal stack return
        self._x(m[0x0001])
        self._mark(0xBF9F)
        self._rts();return

    def city_helper_bfa0(self):
        """$BFA0: city helper bfa0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFA0)
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        self._a(0x0A)
        m[0x0003]=r.a
        yield from self._external(0xBFB0,0xEBE9,0xBFB3,"call",None)
        if r.pc!=0xBFB3:return  # preserve nonlocal stack return
        self._a(m[0x0006])
        self._mark(0xBFB6)
        self._rts();return

    def city_helper_bfb7(self):
        """$BFB7: city helper bfb7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFB7)
        self._a(m[PHASE])
        self._mark(0xBFBA)
        index=self._dispatch(0xBFBA,(49133, 49229, 49462, 49601, 49861, 49977, 50080, 50196, 50282, 50344, 50453, 50503, 50575, 50647, 50815, 50936, 50963, 50977, 51012, 51054, 51231, 51466, 51666, 51695))
        return (yield from (self.city_helper_bfed,self.city_helper_c04d,self.city_helper_c136,self.city_helper_c1c1,self.city_helper_c2c5,self.city_helper_c339,self.city_helper_c3a0,self.city_helper_c414,self.city_helper_c46a,self.city_helper_c4a8,self.city_helper_c515,self.city_helper_c547,self.city_helper_c58f,self.city_helper_c5d7,self.city_helper_c67f,self.city_helper_c6f8,self.city_helper_c713,self.city_helper_c721,self.city_helper_c744,self.city_helper_c76e,self.queue_equipment_icons,self.city_helper_c90a,self.city_helper_c9d2,self.city_helper_c9ef,)[index]())

    def city_helper_bfed(self):
        """$BFED: city helper bfed; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xBFED)
        self._a(m[0x0140])
        self._mark(0xBFF0)
        if not r.p&Z:
            self._mark(0xC024)
            self._rts();return
        else:
            self._a(m[0x0304])
            self._compare(r.a,0xFF)
            self._mark(0xBFF7)
            if not r.p&Z:
                self._mark(0xC024)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xBFFC,0xBFFF)):return
                m[0x0473]=r.a
                self._a(0x0D)
                m[0x00BD]=r.a
                self._a(0x80)
                m[0x0140]=r.a
                self._a(0x04)
                self._a(r.a | m[0x0150])
                m[0x0150]=r.a
                self._y(m[CITY])
                self._a(m[(0xC025+r.y)&65535])
                m[WORLD_CURSOR]=r.a
                self._y(r.a)
                self._a(m[(0xC043+r.y)&65535])
                self._mark(0xC021)
                yield from self._external(0xC021,0xF26D,None,"tail")
                return

    def city_helper_c04d(self):
        """$C04D: city helper c04d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC04D)
        if not (yield from self._local_call(self.city_helper_dcd0,0xC04D,0xC050)):return
        self._a(m[0x0013])
        m[0x0010]=r.a
        self._a(m[0x0014])
        m[0x0011]=r.a
        self._a(0x09)
        m[0x0000]=r.a
        self._a(0xC1)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xC069,0xEDF5,0xC06C,"call",None)
        if r.pc!=0xC06C:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xC06C,0xC06F)):return
        self._mark(0xC06F)
        if not r.p&C:
            self._mark(0xC08A)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC075)
            if r.p&C:
                if not (yield from self._local_call(self.city_helper_dd70,0xC08B,0xC08E)):return
                self._a(m[WORLD_CURSOR])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(m[0x0012])
                self._y(r.a)
                self._a(m[(0xC10E+r.y)&65535])
                self._mark(0xC09B)
                if r.p&Z:
                    self._a(0x12)
                    m[PHASE]=r.a
                    self._a(0x80)
                    m[0x0478]=r.a
                    self._a(0x0F)
                    m[0x047C]=r.a
                    self._a(0xA4)
                    self._mark(0xC0CA)
                    yield from self._external(0xC0CA,0xF26D,None,"tail")
                    return
                else:
                    self._compare(r.a,0x01)
                    self._mark(0xC09F)
                    if r.p&Z:
                        self._a(0x0E)
                        m[PHASE]=r.a
                        self._a(0x80)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        self._a(0x78)
                        self._mark(0xC0DE)
                        yield from self._external(0xC0DE,0xF26D,None,"tail")
                        return
                    else:
                        self._compare(r.a,0x02)
                        self._mark(0xC0A3)
                        if r.p&Z:
                            if not (yield from self._local_call(self.city_helper_dc7c,0xC0E1,0xC0E4)):return
                            self._a(m[0x0151])
                            self._compare(r.a,0xFF)
                            self._mark(0xC0E9)
                            if r.p&Z:
                                self._a(0x11)
                                m[PHASE]=r.a
                                self._a(0xAD)
                                self._mark(0xC106)
                                yield from self._external(0xC106,0xF26D,None,"tail")
                                return
                            else:
                                self._a(0x0A)
                                m[PHASE]=r.a
                                self._a(0x80)
                                m[0x0478]=r.a
                                self._a(0xFF)
                                m[0x047C]=r.a
                                self._a(0x77)
                                self._mark(0xC0FC)
                                yield from self._external(0xC0FC,0xF26D,None,"tail")
                                return
                        else:
                            self._a(0x02)
                            m[PHASE]=r.a
                            self._a(0x21)
                            m[0x04A2]=r.a
                            self._a(0x2E)
                            m[0x04D6]=r.a
                            self._a(0x6F)
                            self._mark(0xC0B6)
                            yield from self._external(0xC0B6,0xF26D,None,"tail")
                            return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC078)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_d568,0xC07A,0xC07D)):return
                    self._a(0x01)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    yield from self._external(0xC087,0xF26D,0xC08A,"call",None)
                    if r.pc!=0xC08A:return  # preserve nonlocal stack return
                    pass
                self._mark(0xC08A)
                self._rts();return

    def city_helper_c136(self):
        """$C136: city helper c136; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC136)
        self._a(0xB4)
        m[0x0010]=r.a
        self._a(0xC1)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xC145,0xED1E,0xC148,"call",None)
        if r.pc!=0xC148:return  # preserve nonlocal stack return
        self._a(0xB8)
        m[0x0010]=r.a
        self._a(0xC1)
        m[0x0011]=r.a
        self._a(0xBC)
        m[0x0000]=r.a
        self._a(0xC1)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xC15F,0xEDF5,0xC162,"call",None)
        if r.pc!=0xC162:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xC162,0xC165)):return
        self._mark(0xC165)
        if not r.p&C:
            self._mark(0xC1B3)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC16B)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC1AC)
                if not r.p&C:
                    pass
                else:
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xC1B3)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_helper_db87,0xC16D,0xC170)):return
                self._a(m[0x0012])
                self._mark(0xC173)
                if not r.p&Z:
                    self._a(m[CITY])
                    yield from self._external(0xC183,0xF2AF,0xC186,"call",None)
                    if r.pc!=0xC186:return  # preserve nonlocal stack return
                    self._y(0x10)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xC18A)
                    if r.p&Z:
                        self._a(0x11)
                        m[PHASE]=r.a
                        self._a(0xAC)
                        self._mark(0xC1A8)
                        yield from self._external(0xC1A8,0xF26D,None,"tail")
                        return
                    else:
                        m[0x0490]=r.a
                        self._a(0x00)
                        m[0x0491]=r.a
                        self._a(0x08)
                        m[PHASE]=r.a
                        if not (yield from self._local_call(self.city_helper_db87,0xC199,0xC19C)):return
                        self._a(0x70)
                        self._mark(0xC19E)
                        yield from self._external(0xC19E,0xF26D,None,"tail")
                        return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC178,0xC17B)):return
                    self._a(0x72)
                    self._mark(0xC17D)
                    yield from self._external(0xC17D,0xF26D,None,"tail")
                    return

    def city_helper_c1c1(self):
        """$C1C1: city helper c1c1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC1C1)
        self._a(0xB8)
        m[0x0010]=r.a
        self._a(0xC2)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xC1D0,0xED1E,0xC1D3,"call",None)
        if r.pc!=0xC1D3:return  # preserve nonlocal stack return
        self._a(0xBC)
        m[0x0010]=r.a
        self._a(0xC2)
        m[0x0011]=r.a
        self._a(0xC0)
        m[0x0000]=r.a
        self._a(0xC2)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xC1EA,0xEDF5,0xC1ED,"call",None)
        if r.pc!=0xC1ED:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xC1ED,0xC1F0)):return
        self._mark(0xC1F0)
        if not r.p&C:
            self._mark(0xC206)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC1F6)
            if r.p&C:
                if not (yield from self._local_call(self.city_helper_db87,0xC207,0xC20A)):return
                self._y(0x30)
                yield from self._external(0xC20C,0xF25F,0xC20F,"call",None)
                if r.pc!=0xC20F:return  # preserve nonlocal stack return
                self._a(m[CITY])
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(0xC0)
                m[0x0002]=r.a
                self._a(0x8F)
                self._add(0x00)
                m[0x0003]=r.a
                self._a(m[CITY])
                yield from self._external(0xC223,0xF2AF,0xC226,"call",None)
                if r.pc!=0xC226:return  # preserve nonlocal stack return
                self._a(m[0x0012])
                self._mark(0xC229)
                if r.p&Z:
                    self._y(0x01)
                    self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                    m[0x0492]=r.a
                    m[0x042C]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x042E]=r.a
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0002]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0001]=r.a
                    self._a(m[0x0002])
                    m[0x0000]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._a(m[0x0492])
                    m[0x0003]=r.a
                    yield from self._external(0xC284,0xEBE9,0xC287,"call",None)
                    if r.pc!=0xC287:return  # preserve nonlocal stack return
                    self._a(0x64)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    if not (yield from self._local_call(self.city_helper_db72,0xC291,0xC294)):return
                    self._a(m[0x0005])
                    self._mark(0xC297)
                    if r.p&Z:
                        pass
                    else:
                        self._a(0x01)
                        m[0x0005]=r.a
                        pass
                    self._a(m[0x0000])
                    self._flag(C,False)
                    self._add(m[0x0005])
                    m[0x0490]=r.a
                    self._a(m[0x0001])
                    self._add(0x00)
                    m[0x0491]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x73)
                    self._mark(0xC2B5)
                    yield from self._external(0xC2B5,0xF26D,None,"tail")
                    return
                else:
                    self._y(0x04)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0490]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0491]=r.a
                    self._y(0x00)
                    self._a(m[((m[0x02]|m[0x03]<<8)+r.y)&65535])
                    m[0x0492]=r.a
                    m[0x042C]=r.a
                    self._a(0x00)
                    m[0x042D]=r.a
                    m[0x042E]=r.a
                    self._a(0x06)
                    m[PHASE]=r.a
                    self._a(0x74)
                    self._mark(0xC251)
                    yield from self._external(0xC251,0xF26D,None,"tail")
                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC1F9)
                if not r.p&C:
                    self._mark(0xC206)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]-1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC1FE,0xC201)):return
                    self._a(0x6F)
                    self._mark(0xC203)
                    yield from self._external(0xC203,0xF26D,None,"tail")
                    return

    def city_helper_c2c5(self):
        """$C2C5: city helper c2c5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC2C5)
        if not (yield from self._local_call(self.text_request_readiness,0xC2C5,0xC2C8)):return
        self._mark(0xC2C8)
        if not r.p&C:
            self._mark(0xC2EB)
            self._rts();return
        else:
            self._a(0x50)
            m[0x031C]=r.a
            self._a(0x23)
            m[0x031D]=r.a
            if not (yield from self._local_call(self.city_helper_da02,0xC2D4,0xC2D7)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC2DB)
            if r.p&C:
                self._a(m[0x048E])
                m[0x0000]=r.a
                self._a(m[0x048F])
                m[0x0001]=r.a
                self._mark(0xC2F8)
                if not r.p&Z:
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._a(0x64)
                    m[0x0003]=r.a
                    yield from self._external(0xC309,0xEBE9,0xC30C,"call",None)
                    if r.pc!=0xC30C:return  # preserve nonlocal stack return
                    self._a(m[0x0492])
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    if not (yield from self._local_call(self.city_helper_db72,0xC317,0xC31A)):return
                    self._a(m[0x0000])
                    m[0x042C]=r.a
                    self._a(m[0x0001])
                    m[0x042D]=r.a
                    self._a(0x00)
                    m[0x042E]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC32E,0xC331)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xC336)
                    yield from self._external(0xC336,0xF26D,None,"tail")
                    return
                else:
                    self._a(m[0x0000])
                    self._mark(0xC2FD)
                    if r.p&Z:
                        self._mark(0xC2EB)
                        self._rts();return
                    else:
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(0x64)
                        m[0x0003]=r.a
                        yield from self._external(0xC309,0xEBE9,0xC30C,"call",None)
                        if r.pc!=0xC30C:return  # preserve nonlocal stack return
                        self._a(m[0x0492])
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        if not (yield from self._local_call(self.city_helper_db72,0xC317,0xC31A)):return
                        self._a(m[0x0000])
                        m[0x042C]=r.a
                        self._a(m[0x0001])
                        m[0x042D]=r.a
                        self._a(0x00)
                        m[0x042E]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        if not (yield from self._local_call(self.city_helper_dd70,0xC32E,0xC331)):return
                        m[0x046C]=r.a
                        self._a(0x29)
                        self._mark(0xC336)
                        yield from self._external(0xC336,0xF26D,None,"tail")
                        return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC2DE)
                if not r.p&C:
                    self._mark(0xC2EB)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]-1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC2E3,0xC2E6)):return
                    self._a(0x72)
                    self._mark(0xC2E8)
                    yield from self._external(0xC2E8,0xF26D,None,"tail")
                    return

    def city_helper_c339(self):
        """$C339: city helper c339; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC339)
        if not (yield from self._local_call(self.city_helper_d5bd,0xC339,0xC33C)):return
        self._a(m[0x0013])
        self._mark(0xC33F)
        if r.p&Z:
            self._mark(0xC39F)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xC343)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xC39F)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xC348,0xF2AF,0xC34B,"call",None)
                if r.pc!=0xC34B:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042C],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x042D],subtract=True)
                self._mark(0xC35B)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    self._y(r.y-1)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    pass
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x048E])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x048F])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x04)
                if not (yield from self._local_call(self.city_helper_dddc,0xC379,0xC37C)):return
                self._a(m[0x048E])
                m[0x042C]=r.a
                self._a(m[0x048F])
                m[0x042D]=r.a
                self._a(0x00)
                m[0x042E]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xC38D,0xC390)):return
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(0x75)
                self._mark(0xC397)
                yield from self._external(0xC397,0xF26D,None,"tail")
                return

    def city_helper_c3a0(self):
        """$C3A0: city helper c3a0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC3A0)
        if not (yield from self._local_call(self.text_request_readiness,0xC3A0,0xC3A3)):return
        self._mark(0xC3A3)
        if not r.p&C:
            self._mark(0xC3C8)
            self._rts();return
        else:
            self._a(0x50)
            m[0x031C]=r.a
            self._a(0x23)
            m[0x031D]=r.a
            if not (yield from self._local_call(self.city_helper_da02,0xC3AF,0xC3B2)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC3B6)
            if r.p&C:
                self._a(m[0x048E])
                m[0x0000]=r.a
                self._a(m[0x048F])
                m[0x0001]=r.a
                self._mark(0xC3D5)
                if not r.p&Z:
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._a(m[0x0492])
                    m[0x0003]=r.a
                    yield from self._external(0xC3E7,0xEBE9,0xC3EA,"call",None)
                    if r.pc!=0xC3EA:return  # preserve nonlocal stack return
                    self._a(0x64)
                    m[0x0003]=r.a
                    self._a(0x00)
                    m[0x0004]=r.a
                    if not (yield from self._local_call(self.city_helper_db72,0xC3F4,0xC3F7)):return
                    self._a(m[0x0000])
                    m[0x042C]=r.a
                    self._a(m[0x0001])
                    m[0x042D]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xC403,0xC406)):return
                    m[0x042E]=r.a
                    m[0x046C]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x29)
                    self._mark(0xC411)
                    yield from self._external(0xC411,0xF26D,None,"tail")
                    return
                else:
                    self._a(m[0x0000])
                    self._mark(0xC3DA)
                    if r.p&Z:
                        self._mark(0xC3C8)
                        self._rts();return
                    else:
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(m[0x0492])
                        m[0x0003]=r.a
                        yield from self._external(0xC3E7,0xEBE9,0xC3EA,"call",None)
                        if r.pc!=0xC3EA:return  # preserve nonlocal stack return
                        self._a(0x64)
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0004]=r.a
                        if not (yield from self._local_call(self.city_helper_db72,0xC3F4,0xC3F7)):return
                        self._a(m[0x0000])
                        m[0x042C]=r.a
                        self._a(m[0x0001])
                        m[0x042D]=r.a
                        if not (yield from self._local_call(self.city_helper_dd70,0xC403,0xC406)):return
                        m[0x042E]=r.a
                        m[0x046C]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(0x29)
                        self._mark(0xC411)
                        yield from self._external(0xC411,0xF26D,None,"tail")
                        return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC3B9)
                if not r.p&C:
                    self._mark(0xC3C8)
                    self._rts();return
                else:
                    self._a(0x03)
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xC3C0,0xC3C3)):return
                    self._a(0x72)
                    self._mark(0xC3C5)
                    yield from self._external(0xC3C5,0xF26D,None,"tail")
                    return

    def city_helper_c414(self):
        """$C414: city helper c414; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC414)
        if not (yield from self._local_call(self.city_helper_d5bd,0xC414,0xC417)):return
        self._a(m[0x0013])
        self._mark(0xC41A)
        if r.p&Z:
            self._mark(0xC469)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xC41E)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xC469)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xC423,0xF2AF,0xC426,"call",None)
                if r.pc!=0xC426:return  # preserve nonlocal stack return
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x048E],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x048F],subtract=True)
                self._mark(0xC436)
                if r.p&C:
                    pass
                else:
                    self._a(0x00)
                    self._y(r.y-1)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._y(r.y+1)
                    pass
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x042C])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x042D])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x02)
                if not (yield from self._local_call(self.city_helper_dddc,0xC454,0xC457)):return
                if not (yield from self._local_call(self.city_helper_d568,0xC457,0xC45A)):return
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(0x76)
                self._mark(0xC461)
                yield from self._external(0xC461,0xF26D,None,"tail")
                return

    def city_helper_c46a(self):
        """$C46A: city helper c46a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC46A)
        if not (yield from self._local_call(self.text_request_readiness,0xC46A,0xC46D)):return
        self._mark(0xC46D)
        if not r.p&C:
            self._mark(0xC4A7)
            self._rts();return
        else:
            self._a(0x30)
            m[0x031C]=r.a
            self._a(0x23)
            m[0x031D]=r.a
            self._a(0x01)
            if not (yield from self._local_call(self.city_helper_da04,0xC47B,0xC47E)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC482)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC498)
                if not r.p&C:
                    self._mark(0xC4A7)
                    self._rts();return
                else:
                    self._a(0x02)
                    m[PHASE]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xC49F,0xC4A2)):return
                    self._a(0x6F)
                    self._mark(0xC4A4)
                    yield from self._external(0xC4A4,0xF26D,None,"tail")
                    return
            else:
                self._a(m[0x048E])
                self._mark(0xC487)
                if r.p&Z:
                    self._mark(0xC4A7)
                    self._rts();return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC48C,0xC48F)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xC494)
                    yield from self._external(0xC494,0xF26D,None,"tail")
                    return

    def city_helper_c4a8(self):
        """$C4A8: city helper c4a8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC4A8)
        if not (yield from self._local_call(self.city_helper_d5bd,0xC4A8,0xC4AB)):return
        self._a(m[0x0013])
        self._mark(0xC4AE)
        if r.p&Z:
            self._mark(0xC514)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xC4B2)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xC514)
                self._rts();return
            else:
                self._a(0x64)
                m[0x0003]=r.a
                self._a(m[0x048E])
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                yield from self._external(0xC4C7,0xEBE9,0xC4CA,"call",None)
                if r.pc!=0xC4CA:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                m[0x042C]=r.a
                self._a(m[0x0007])
                m[0x042D]=r.a
                self._a(0x00)
                m[0x042E]=r.a
                self._a(m[CITY])
                yield from self._external(0xC4DE,0xF2AF,0xC4E1,"call",None)
                if r.pc!=0xC4E1:return  # preserve nonlocal stack return
                self._y(0x10)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x048E],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x042C])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x042D])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(0x02)
                if not (yield from self._local_call(self.city_helper_dddc,0xC4FF,0xC502)):return
                if not (yield from self._local_call(self.city_helper_d568,0xC502,0xC505)):return
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(0x76)
                self._mark(0xC50C)
                yield from self._external(0xC50C,0xF26D,None,"tail")
                return

    def city_helper_c515(self):
        """$C515: city helper c515; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC515)
        self._a(m[0x0478])
        self._mark(0xC518)
        if not r.p&Z:
            self._mark(0xC546)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xC51A,0xC51D)):return
            self._a(m[0x047C])
            self._mark(0xC520)
            if not r.p&N:
                self._mark(0xC546)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xC524)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xC546)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xC526,0xC529)):return
                    self._a(0x00)
                    m[WORLD_CURSOR]=r.a
                    m[0x042D]=r.a
                    m[0x042E]=r.a
                    self._a(0x32)
                    m[0x042C]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x28)
                    self._mark(0xC53E)
                    yield from self._external(0xC53E,0xF26D,None,"tail")
                    return

    def city_helper_c547(self):
        """$C547: city helper c547; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC547)
        if not (yield from self._local_call(self.text_request_readiness,0xC547,0xC54A)):return
        self._mark(0xC54A)
        if not r.p&C:
            self._mark(0xC58E)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xC54C,0xC54F)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC553)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xC582)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.text_request_readiness,0xC584,0xC587)):return
                    self._mark(0xC587)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[PHASE]=r.a
                        pass
                    pass
                self._mark(0xC58E)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xC558,0xF2AF,0xC55B,"call",None)
                if r.pc!=0xC55B:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,m[0x042C])
                self._mark(0xC562)
                if r.p&C:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC56C,0xC56F)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xC574)
                    yield from self._external(0xC574,0xF26D,None,"tail")
                    return
                else:
                    self._y(r.y+1)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._mark(0xC567)
                    if r.p&Z:
                        self._a(0x11)
                        m[PHASE]=r.a
                        self._a(0x2A)
                        self._mark(0xC57E)
                        yield from self._external(0xC57E,0xF26D,None,"tail")
                        return
                    else:
                        m[PHASE]=self._nz(m[PHASE]+1)
                        if not (yield from self._local_call(self.city_helper_dd70,0xC56C,0xC56F)):return
                        m[0x046C]=r.a
                        self._a(0x29)
                        self._mark(0xC574)
                        yield from self._external(0xC574,0xF26D,None,"tail")
                        return

    def city_helper_c58f(self):
        """$C58F: city helper c58f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC58F)
        if not (yield from self._local_call(self.city_helper_d5bd,0xC58F,0xC592)):return
        self._a(m[0x0013])
        self._mark(0xC595)
        if r.p&Z:
            self._mark(0xC5D6)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xC599)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xC5D6)
                self._rts();return
            else:
                self._a(m[CITY])
                yield from self._external(0xC59E,0xF2AF,0xC5A1,"call",None)
                if r.pc!=0xC5A1:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042C],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(0x00,subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(m[0x0481])
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xC5BA,0xEE07,0xC5BF,"far_call",41002)
                if r.pc!=0xC5BF:return  # preserve nonlocal stack return
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[WORLD_CURSOR])
                self._mark(0xC5C5)
                if not r.p&Z:
                    self._a(0x7C)
                    self._mark(0xC5CE)
                    yield from self._external(0xC5CE,0xF26D,None,"tail")
                    return
                else:
                    self._a(0x7A)
                    self._mark(0xC5C9)
                    yield from self._external(0xC5C9,0xF26D,None,"tail")
                    return

    def city_helper_c5d7(self):
        """$C5D7: city helper c5d7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC5D7)
        self._a(m[0x0481])
        if not (yield from self._local_call(self.city_helper_dd5e,0xC5DA,0xC5DD)):return
        if not (yield from self._local_call(self.text_request_readiness,0xC5DD,0xC5E0)):return
        self._mark(0xC5E0)
        if not r.p&C:
            self._mark(0xC5EC)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xC5E2,0xC5E5)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC5EA)
            if not r.p&Z:
                if not (yield from self._local_call(self.city_helper_d568,0xC5ED,0xC5F0)):return
                self._y(0x3D)
                yield from self._external(0xC5F2,0xEE07,0xC5F7,"far_call",40996)
                if r.pc!=0xC5F7:return  # preserve nonlocal stack return
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(m[WORLD_CURSOR])
                self._mark(0xC5FF)
                if not r.p&Z:
                    while True:  # natural loop $C652
                        self._a(m[0x0481])
                        yield from self._external(0xC655,0xF2D7,0xC658,"call",None)
                        if r.pc!=0xC658:return  # preserve nonlocal stack return
                        yield from self._external(0xC658,0xE856,0xC65B,"call",None)
                        if r.pc!=0xC65B:return  # preserve nonlocal stack return
                        self._compare(r.a,0x05)
                        self._mark(0xC65D)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._flag(C,False)
                        self._add(m[CURRENT_CITY])
                        m[0x042C]=r.a
                        self._y(0x02)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x042C])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._a(0x02)
                        m[0x04A2]=r.a
                        self._a(0x52)
                        m[0x04D6]=r.a
                        self._a(0x7D)
                        self._mark(0xC67C)
                        yield from self._external(0xC67C,0xF26D,None,"tail")
                        return
                else:
                    while True:  # natural loop $C601
                        yield from self._external(0xC601,0xE85C,0xC604,"call",None)
                        if r.pc!=0xC604:return  # preserve nonlocal stack return
                        self._compare(r.a,0x0B)
                        self._mark(0xC606)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._flag(C,False)
                        self._add(0x23)
                        m[0x042C]=r.a
                        self._a(m[0x0481])
                        yield from self._external(0xC611,0xF387,0xC614,"call",None)
                        if r.pc!=0xC614:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0002]=r.a
                        self._a(m[0x0481])
                        yield from self._external(0xC61E,0xF2D7,0xC621,"call",None)
                        if r.pc!=0xC621:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._flag(C,False)
                        self._add(m[0x042C])
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._flag(C,True)
                        self._add(m[0x0002],subtract=True)
                        self._mark(0xC62F)
                        if not r.p&C:
                            pass
                        else:
                            m[0x0003]=r.a
                            self._a(m[0x042C])
                            self._flag(C,True)
                            self._add(m[0x0003],subtract=True)
                            m[0x042C]=r.a
                            self._a(m[0x0002])
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            pass
                        self._a(0x0D)
                        m[0x04A2]=r.a
                        self._a(0x52)
                        m[0x04D6]=r.a
                        self._a(0x7B)
                        self._mark(0xC64F)
                        yield from self._external(0xC64F,0xF26D,None,"tail")
                        return
            else:
                self._mark(0xC5EC)
                self._rts();return

    def city_helper_c67f(self):
        """$C67F: city helper c67f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC67F)
        self._a(m[0x0478])
        self._mark(0xC682)
        if not r.p&Z:
            self._mark(0xC6F7)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xC684,0xC687)):return
            self._a(m[0x047C])
            self._mark(0xC68A)
            if not r.p&N:
                self._mark(0xC6F7)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xC68E)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xC6F7)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xC690,0xC693)):return
                    self._a(m[0x0481])
                    yield from self._external(0xC696,0xF2D7,0xC699,"call",None)
                    if r.pc!=0xC699:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x50)
                    self._mark(0xC69F)
                    if r.p&C:
                        self._a(m[0x0481])
                        m[0x0473]=r.a
                        m[0x0000]=r.a
                        self._y(0x3D)
                        yield from self._external(0xC6E3,0xEE07,0xC6E8,"far_call",41002)
                        if r.pc!=0xC6E8:return  # preserve nonlocal stack return
                        self._a(0x11)
                        m[PHASE]=r.a
                        self._a(0x79)
                        self._mark(0xC6EF)
                        yield from self._external(0xC6EF,0xF26D,None,"tail")
                        return
                    else:
                        self._compare(r.a,0x3D)
                        self._mark(0xC6A3)
                        if not r.p&C:
                            self._compare(r.a,0x1F)
                            self._mark(0xC6AE)
                            if not r.p&C:
                                self._a(0x1E)
                                self._x(0x05)
                                pass
                            else:
                                self._a(0x14)
                                self._x(0x08)
                                pass
                            pass
                        else:
                            self._a(0x0A)
                            self._x(0x06)
                            pass
                        m[0x042C]=r.a
                        m[CURRENT_CITY]=r.x
                        self._a(0x00)
                        m[0x042D]=r.a
                        m[0x042E]=r.a
                        self._a(0x01)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x0B)
                        m[PHASE]=r.a
                        self._a(0x28)
                        self._mark(0xC6D5)
                        yield from self._external(0xC6D5,0xF26D,None,"tail")
                        return

    def city_helper_c6f8(self):
        """$C6F8: city helper c6f8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC6F8)
        self._y(0x3D)
        yield from self._external(0xC6FA,0xEE07,0xC6FF,"far_call",40996)
        if r.pc!=0xC6FF:return  # preserve nonlocal stack return
        self._a(m[0x0140])
        self._mark(0xC702)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x04A2])
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x60)
            m[0x046C]=r.a
            pass
        self._mark(0xC712)
        self._rts();return

    def city_helper_c713(self):
        """$C713: city helper c713; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC713)
        self._a(m[0x04A0])
        self._mark(0xC716)
        if not r.p&Z:
            pass
        else:
            self._a(0x04)
            if not (yield from self._local_call(self.city_helper_d58c,0xC71A,0xC71D)):return
            m[PHASE]=self._nz(m[PHASE]+1)
            pass
        self._mark(0xC720)
        self._rts();return

    def city_helper_c721(self):
        """$C721: city helper c721; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC721)
        if not (yield from self._local_call(self.text_request_readiness,0xC721,0xC724)):return
        self._mark(0xC724)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xC726,0xC729)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xC72E)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xC730,0xC733)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                pass
            pass
        self._a(m[0x0473])
        self._mark(0xC73E)
        if r.p&Z:
            self._mark(0xC743)
            self._rts();return
        else:
            return (yield from self.city_helper_dd5e())

    def city_helper_c744(self):
        """$C744: city helper c744; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC744)
        self._a(m[0x0478])
        self._mark(0xC747)
        if not r.p&Z:
            self._mark(0xC76D)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xC749,0xC74C)):return
            self._a(m[0x047C])
            self._mark(0xC74F)
            if not r.p&N:
                self._mark(0xC76D)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xC753)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._mark(0xC76D)
                    self._rts();return
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xC755,0xC758)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x8C)
                    m[0x00BD]=r.a
                    if not (yield from self._local_call(self.city_helper_dd70,0xC760,0xC763)):return
                    self._a(0xA5)
                    self._mark(0xC765)
                    yield from self._external(0xC765,0xF26D,None,"tail")
                    return

    def city_helper_c76e(self):
        """$C76E: city helper c76e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC76E)
        self._a(0xEE)
        m[0x0010]=r.a
        self._a(0xC7)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xC77D,0xED1E,0xC780,"call",None)
        if r.pc!=0xC780:return  # preserve nonlocal stack return
        self._a(0xF4)
        m[0x0010]=r.a
        self._a(0xC7)
        m[0x0011]=r.a
        self._a(0xFC)
        m[0x0000]=r.a
        self._a(0xC7)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xC797,0xEDF5,0xC79A,"call",None)
        if r.pc!=0xC79A:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        r.a=self._shift(r.a,False,rotate=False)
        self._mark(0xC79E)
        if not r.p&C:
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC7D9)
            if not r.p&C:
                self._mark(0xC7ED)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]-1)
                self._a(0x80)
                m[0x0478]=r.a
                self._a(0x0F)
                m[0x047C]=r.a
                self._a(0xA4)
                self._mark(0xC7EA)
                yield from self._external(0xC7EA,0xF26D,None,"tail")
                return
        else:
            self._y(m[CITY])
            self._a(m[(0xC801+r.y)&65535])
            m[0x0000]=r.a
            self._y(0x28)
            yield from self._external(0xC7AB,0xEE07,0xC7B0,"far_call",40990)
            if r.pc!=0xC7B0:return  # preserve nonlocal stack return
            self._a(m[CITY])
            self._compare(r.a,0x1B)
            self._mark(0xC7B5)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x044C])
                self._compare(r.a,0x10)
                self._mark(0xC7BC)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x17)
                    m[0x044F]=r.a
                    self._a(0x90)
                    m[0x0435]=r.a
                    self._a(0x01)
                    m[0x0436]=r.a
                    pass
                pass
            m[PHASE]=self._nz(m[PHASE]+1)
            if not (yield from self._local_call(self.city_helper_dd70,0xC7D0,0xC7D3)):return
            self._a(0xA6)
            self._mark(0xC7D5)
            yield from self._external(0xC7D5,0xF28B,None,"tail")
            return

    def queue_equipment_icons(self):
        """C81F..C8F9: four equipment records, two rows of eight tiles each.

        Requests the original nametable packet, keeps BC/BD font-page shadows
        and advances the city phase. It never acknowledges its PPU request.
        """
        r=self.registers;m=self.memory;self._mark(0xC81F)
        self._a(m[0x300]);self._compare(r.a,255)
        if not r.p&Z:self._rts();return
        self._y(48);yield from self._external(0xC829,0xF25F,0xC82C,'call')
        if r.pc!=0xC82C:return
        self._y(0);self._x(0);m[0x10]=m[0x11]=m[0x12]=r.x
        while True:
            self._mark(0xC839 if m[0x10]==0 else 0xC85B)
            self._y(m[0x10]);self._a(m[(0x44C+r.y)&65535]);r.a=self._shift(r.a,True);self._y(r.a)
            self._a(m[(0x9B12+r.y)&65535]);m[0]=r.a;self._y(r.y+1)
            self._a(m[(0x9B12+r.y)&65535]);self._flag(C,False);self._add(128);m[1]=r.a
            if m[0x10]==0:
                self._y(0);self._a(m[(m[0]|m[1]<<8)]);m[0xBC]=r.a
            self._y(0);m[0x14]=m[0x15]=r.y;self._a(m[(m[0]|m[1]<<8)]);self._compare(r.a,m[0xBC])
            if not r.p&Z:m[0xBD]=r.a;self._a(64);m[0x15]=r.a
            while True:
                self._mark(0xC88A);self._x(m[0x12]);self._a(m[(0xC8FA+r.x)&65535]);m[2]=r.a;self._x(r.x+1)
                self._a(m[(0xC8FA+r.x)&65535]);m[3]=r.a;self._x(r.x+1);m[0x12]=r.x;self._x(m[0x11])
                self._a(8);m[(0x380+r.x)&65535]=r.a;self._x(r.x+1);self._a(m[3]);m[(0x380+r.x)&65535]=r.a
                self._x(r.x+1);self._a(m[2]);m[(0x380+r.x)&65535]=r.a;self._a(0);m[0x13]=r.a
                while True:
                    self._mark(0xC8B9);self._x(r.x+1);self._y(r.y+1);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
                    self._flag(C,False);self._add(m[0x15]);m[(0x380+r.x)&65535]=r.a
                    m[0x13]=self._nz(m[0x13]+1);self._a(m[0x13]);self._compare(r.a,8)
                    if r.p&C:break
                self._x(r.x+1);m[0x11]=r.x;m[0x14]=self._nz(m[0x14]+1);self._a(m[0x14]);self._compare(r.a,2)
                if r.p&C:break
            m[0x10]=self._nz(m[0x10]+1);self._a(m[0x10]);self._compare(r.a,4)
            if r.p&C:break
        self._a(255);m[(0x380+r.x)&65535]=r.a;self._a(m[PPU_JOBS]);self._a(r.a|4);m[PPU_JOBS]=r.a
        m[PHASE]=self._nz(m[PHASE]+1);self._mark(0xC8F9);self._rts();return

    def city_helper_c90a(self):
        """$C90A: city helper c90a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC90A)
        self._a(0xBF)
        m[0x0010]=r.a
        self._a(0xC9)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xC919,0xED1E,0xC91C,"call",None)
        if r.pc!=0xC91C:return  # preserve nonlocal stack return
        self._a(0xC5)
        m[0x0010]=r.a
        self._a(0xC9)
        m[0x0011]=r.a
        self._a(0xCD)
        m[0x0000]=r.a
        self._a(0xC9)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xC933,0xEDF5,0xC936,"call",None)
        if r.pc!=0xC936:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        r.a=self._shift(r.a,False,rotate=False)
        self._mark(0xC93A)
        if r.p&C:
            self._y(m[0x0012])
            self._a(m[(0x044C+r.y)&65535])
            m[0x044C]=r.a
            self._a(m[0x0012])
            r.a=self._shift(r.a,True,rotate=False)
            self._flag(C,False)
            self._add(m[0x0012])
            self._y(r.a)
            self._a(m[(0x042C+r.y)&65535])
            m[0x0010]=r.a
            self._y(r.y+1)
            self._a(m[(0x042C+r.y)&65535])
            m[0x0011]=r.a
            self._a(m[CITY])
            yield from self._external(0xC972,0xF2AF,0xC975,"call",None)
            if r.pc!=0xC975:return  # preserve nonlocal stack return
            self._y(0x02)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._flag(C,True)
            self._add(m[0x0010],subtract=True)
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._add(m[0x0011],subtract=True)
            self._mark(0xC983)
            if not r.p&C:
                self._a(0x11)
                m[CURRENT_CITY]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0xAA)
                self._mark(0xC9BC)
                yield from self._external(0xC9BC,0xF28B,None,"tail")
                return
            else:
                if not (yield from self._local_call(self.city_helper_ca6b,0xC985,0xC988)):return
                self._mark(0xC988)
                if r.p&C:
                    self._a(m[0x0010])
                    m[0x042C]=r.a
                    self._a(m[0x0011])
                    m[0x042D]=r.a
                    self._a(0x17)
                    m[CURRENT_CITY]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xC9A7,0xC9AA)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xC9AF)
                    yield from self._external(0xC9AF,0xF28B,None,"tail")
                    return
                else:
                    self._a(0x11)
                    m[CURRENT_CITY]=r.a
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._mark(0xC992)
                    self._rts();return
        else:
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xC93D)
            if not r.p&C:
                self._mark(0xC94F)
                self._rts();return
            else:
                self._a(0x13)
                m[CURRENT_CITY]=r.a
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xC947,0xC94A)):return
                self._a(0xA5)
                self._mark(0xC94C)
                yield from self._external(0xC94C,0xF28B,None,"tail")
                return

    def city_helper_c9d2(self):
        """$C9D2: city helper c9d2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9D2)
        self._a(m[0x0300])
        self._mark(0xC9D5)
        if not r.p&Z:
            pass
        else:
            self._a(0x0D)
            m[0x00BC]=r.a
            self._a(0x8C)
            m[0x00BD]=r.a
            self._y(0x3D)
            yield from self._external(0xC9E3,0xEE07,0xC9E8,"far_call",40996)
            if r.pc!=0xC9E8:return  # preserve nonlocal stack return
            self._a(m[CURRENT_CITY])
            m[PHASE]=r.a
            pass
        self._mark(0xC9EE)
        self._rts();return

    def city_helper_c9ef(self):
        """$C9EF: city helper c9ef; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xC9EF)
        if not (yield from self._local_call(self.city_helper_d5bd,0xC9EF,0xC9F2)):return
        self._a(m[0x0013])
        self._mark(0xC9F5)
        if r.p&Z:
            self._mark(0xCA6A)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xC9F9)
            if r.p&Z:
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xCA6A)
                self._rts();return
            else:
                self._a(m[0x0472])
                self._mark(0xC9FE)
                if r.p&Z:
                    pass
                else:
                    self._a(r.a | m[0x6FE1])
                    m[0x6FE1]=r.a
                    pass
                self._a(0xE0)
                m[0x0010]=r.a
                self._a(m[0x044C])
                self._compare(r.a,0x18)
                self._mark(0xCA10)
                if not r.p&C:
                    pass
                else:
                    self._flag(C,True)
                    self._add(0x18,subtract=True)
                    self._flag(C,False)
                    r.a=self._shift(r.a,False,rotate=True)
                    r.a=self._shift(r.a,False,rotate=True)
                    r.a=self._shift(r.a,False,rotate=True)
                    r.a=self._shift(r.a,False,rotate=True)
                    self._a(r.a & 0xE0)
                    m[0x044C]=r.a
                    self._a(0x1F)
                    m[0x0010]=r.a
                    pass
                self._a(m[0x0481])
                yield from self._external(0xCA27,0xF2D7,0xCA2A,"call",None)
                if r.pc!=0xCA2A:return  # preserve nonlocal stack return
                self._y(0x0A)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & m[0x0010])
                self._a(r.a | m[0x044C])
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(m[CITY])
                yield from self._external(0xCA39,0xF2AF,0xCA3C,"call",None)
                if r.pc!=0xCA3C:return  # preserve nonlocal stack return
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._flag(C,True)
                self._add(m[0x042C],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._add(m[0x042D],subtract=True)
                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                self._a(0x08)
                m[0x04A2]=r.a
                self._a(0x4D)
                m[0x04D6]=r.a
                if not (yield from self._local_call(self.city_helper_d568,0xCA58,0xCA5B)):return
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(0xAB)
                self._mark(0xCA62)
                yield from self._external(0xCA62,0xF26D,None,"tail")
                return

    def city_helper_ca6b(self):
        """$CA6B: city helper ca6b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCA6B)
        self._a(0x00)
        m[0x0472]=r.a
        self._a(m[0x0481])
        m[0x0002]=r.a
        yield from self._external(0xCA76,0xF2D7,0xCA79,"call",None)
        if r.pc!=0xCA79:return  # preserve nonlocal stack return
        self._a(m[0x044C])
        self._compare(r.a,0x0F)
        self._mark(0xCA7E)
        if not r.p&Z:
            self._compare(r.a,0x17)
            self._mark(0xCA8E)
            if not r.p&Z:
                self._compare(r.a,0x16)
                self._mark(0xCA9E)
                if not r.p&Z:
                    self._compare(r.a,0x1E)
                    self._mark(0xCAAF)
                    if not r.p&Z:
                        self._flag(C,True)
                        self._mark(0xCAD7)
                        self._rts();return
                    else:
                        self._y(0x04)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0x5B)
                        self._mark(0xCAB7)
                        if not r.p&C:
                            self._a(0x9A)
                            yield from self._external(0xCAC0,0xF28B,0xCAC3,"call",None)
                            if r.pc!=0xCAC3:return  # preserve nonlocal stack return
                            self._flag(C,False)
                            self._mark(0xCAC4)
                            self._rts();return
                        else:
                            self._a(0x10)
                            m[0x0003]=r.a
                            self._a(m[0x6FE1])
                            self._a(r.a & m[0x0003])
                            self._mark(0xCACE)
                            if not r.p&Z:
                                self._a(0x9B)
                                yield from self._external(0xCADA,0xF28B,0xCADD,"call",None)
                                if r.pc!=0xCADD:return  # preserve nonlocal stack return
                                self._flag(C,False)
                                self._mark(0xCADE)
                                self._rts();return
                            else:
                                self._a(m[0x0003])
                                m[0x0472]=r.a
                                self._flag(C,True)
                                self._mark(0xCAD7)
                                self._rts();return
                else:
                    self._y(0x01)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._compare(r.a,0x5B)
                    self._mark(0xCAA6)
                    if not r.p&C:
                        self._a(0x9A)
                        yield from self._external(0xCAC0,0xF28B,0xCAC3,"call",None)
                        if r.pc!=0xCAC3:return  # preserve nonlocal stack return
                        self._flag(C,False)
                        self._mark(0xCAC4)
                        self._rts();return
                    else:
                        self._a(0x08)
                        m[0x0003]=r.a
                        self._a(m[0x6FE1])
                        self._a(r.a & m[0x0003])
                        self._mark(0xCACE)
                        if not r.p&Z:
                            self._a(0x9B)
                            yield from self._external(0xCADA,0xF28B,0xCADD,"call",None)
                            if r.pc!=0xCADD:return  # preserve nonlocal stack return
                            self._flag(C,False)
                            self._mark(0xCADE)
                            self._rts();return
                        else:
                            self._a(m[0x0003])
                            m[0x0472]=r.a
                            self._flag(C,True)
                            self._mark(0xCAD7)
                            self._rts();return
            else:
                self._a(m[0x0002])
                self._compare(r.a,0x99)
                self._mark(0xCA95)
                if not r.p&Z:
                    self._a(0x9A)
                    yield from self._external(0xCAC0,0xF28B,0xCAC3,"call",None)
                    if r.pc!=0xCAC3:return  # preserve nonlocal stack return
                    self._flag(C,False)
                    self._mark(0xCAC4)
                    self._rts();return
                else:
                    self._a(0x04)
                    m[0x0003]=r.a
                    self._a(m[0x6FE1])
                    self._a(r.a & m[0x0003])
                    self._mark(0xCACE)
                    if not r.p&Z:
                        self._a(0x9B)
                        yield from self._external(0xCADA,0xF28B,0xCADD,"call",None)
                        if r.pc!=0xCADD:return  # preserve nonlocal stack return
                        self._flag(C,False)
                        self._mark(0xCADE)
                        self._rts();return
                    else:
                        self._a(m[0x0003])
                        m[0x0472]=r.a
                        self._flag(C,True)
                        self._mark(0xCAD7)
                        self._rts();return
        else:
            self._a(m[0x0002])
            self._compare(r.a,0x26)
            self._mark(0xCA85)
            if not r.p&Z:
                self._a(0x9A)
                yield from self._external(0xCAC0,0xF28B,0xCAC3,"call",None)
                if r.pc!=0xCAC3:return  # preserve nonlocal stack return
                self._flag(C,False)
                self._mark(0xCAC4)
                self._rts();return
            else:
                self._a(0x02)
                m[0x0003]=r.a
                self._a(m[0x6FE1])
                self._a(r.a & m[0x0003])
                self._mark(0xCACE)
                if not r.p&Z:
                    self._a(0x9B)
                    yield from self._external(0xCADA,0xF28B,0xCADD,"call",None)
                    if r.pc!=0xCADD:return  # preserve nonlocal stack return
                    self._flag(C,False)
                    self._mark(0xCADE)
                    self._rts();return
                else:
                    self._a(m[0x0003])
                    m[0x0472]=r.a
                    self._flag(C,True)
                    self._mark(0xCAD7)
                    self._rts();return

    def city_helper_cadf(self):
        """$CADF: city helper cadf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCADF)
        self._a(m[PHASE])
        self._mark(0xCAE2)
        index=self._dispatch(0xCAE2,(51977, 52223, 52354, 52556, 52617, 52878, 52909, 52983, 53022, 53133, 53220, 53279, 53480, 53500, 53567, 53647, 53689, 53820))
        return (yield from (self.city_helper_cb09,self.city_helper_cbff,self.city_helper_cc82,self.city_helper_cd4c,self.city_helper_cd89,self.city_helper_ce8e,self.city_helper_cead,self.city_helper_cef7,self.city_helper_cf1e,self.city_helper_cf8d,self.city_helper_cfe4,self.city_helper_d01f,self.city_helper_d0e8,self.city_helper_d0fc,self.city_helper_d13f,self.city_helper_d18f,self.city_helper_d1b9,self.city_helper_d23c,)[index]())

    def city_helper_cb09(self):
        """$CB09: city helper cb09; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCB09)
        self._a(0xEE)
        m[0x0010]=r.a
        self._a(0xCB)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xCB18,0xED1E,0xCB1B,"call",None)
        if r.pc!=0xCB1B:return  # preserve nonlocal stack return
        self._a(0xF4)
        m[0x0010]=r.a
        self._a(0xCB)
        m[0x0011]=r.a
        self._a(0xFA)
        m[0x0000]=r.a
        self._a(0xCB)
        m[0x0001]=r.a
        self._a(m[0x0012])
        yield from self._external(0xCB32,0xEDF5,0xCB35,"call",None)
        if r.pc!=0xCB35:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xCB35,0xCB38)):return
        self._mark(0xCB38)
        if not r.p&C:
            self._mark(0xCB4D)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xCB3E)
            if r.p&C:
                self._a(0x3E)
                m[0x04D6]=r.a
                self._a(m[0x0012])
                self._mark(0xCB56)
                if r.p&Z:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[0x0472]=r.a
                    m[0x048B]=r.a
                    self._a(0x03)
                    m[CURRENT_CITY]=r.a
                    self._a(0x80)
                    m[0x0480]=r.a
                    self._a(0x22)
                    m[0x0481]=r.a
                    self._a(m[CITY])
                    yield from self._external(0xCBA9,0xF2AF,0xCBAC,"call",None)
                    if r.pc!=0xCBAC:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    m[WORLD_CURSOR]=r.a
                    self._x(0x00)
                    m[0x0010]=r.x
                    while True:  # natural loop $CBBA
                        self._a(0xFF)
                        m[(0x0490+r.x)&65535]=r.a
                        self._a(r.x)
                        yield from self._external(0xCBC0,0xF368,0xCBC3,"call",None)
                        if r.pc!=0xCBC3:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xCBC9)
                        if r.p&Z:
                            pass
                        else:
                            m[0x0010]=self._nz(m[0x0010]+1)
                            pass
                        self._x(r.x+1)
                        self._compare(r.x,0x07)
                        self._mark(0xCBD1)
                        if not r.p&C:
                            continue
                        else:
                            pass
                        self._a(m[0x0010])
                        self._compare(r.a,0x02)
                        self._mark(0xCBD8)
                        if not r.p&C:
                            self._a(0xFF)
                            m[0x0473]=r.a
                            self._a(0x0E)
                            m[PHASE]=r.a
                            self._a(0xA8)
                            self._mark(0xCBEB)
                            yield from self._external(0xCBEB,0xF26D,None,"tail")
                            return
                        else:
                            self._a(0x3C)
                            self._mark(0xCBDC)
                            yield from self._external(0xCBDC,0xF26D,None,"tail")
                            return
                else:
                    self._compare(r.a,0x02)
                    self._mark(0xCB5A)
                    if r.p&Z:
                        self._a(m[CITY])
                        m[WORLD_CURSOR]=r.a
                        self._a(0x01)
                        m[0x0472]=r.a
                        self._a(0x07)
                        m[PHASE]=r.a
                        self._mark(0xCB8B)
                        self._rts();return
                    else:
                        self._a(m[CITY])
                        m[WORLD_CURSOR]=r.a
                        self._a(m[0x0012])
                        self._compare(r.a,0x01)
                        self._mark(0xCB67)
                        if not r.p&Z:
                            self._a(m[CITY])
                            m[WORLD_CURSOR]=r.a
                            self._a(0x01)
                            m[0x0472]=r.a
                            self._a(0x07)
                            m[PHASE]=r.a
                            self._mark(0xCB8B)
                            self._rts();return
                        else:
                            self._a(0x00)
                            m[0x0472]=r.a
                            if not (yield from self._local_call(self.city_helper_d568,0xCB6E,0xCB71)):return
                            self._a(0x08)
                            m[PHASE]=r.a
                            self._a(0x3E)
                            self._mark(0xCB78)
                            yield from self._external(0xCB78,0xF26D,None,"tail")
                            return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xCB41)
                if not r.p&C:
                    pass
                else:
                    self._a(0x02)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    pass
                self._mark(0xCB4D)
                self._rts();return

    def city_helper_cbff(self):
        """$CBFF: city helper cbff; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCBFF)
        self._y(0x30)
        yield from self._external(0xCC01,0xF25F,0xCC04,"call",None)
        if r.pc!=0xCC04:return  # preserve nonlocal stack return
        self._a(m[PPU_JOBS])
        self._a(r.a & 0x03)
        self._mark(0xCC09)
        if not r.p&Z:
            self._mark(0xCC81)
            self._rts();return
        else:
            self._a(m[CURRENT_CITY])
            self._mark(0xCC0E)
            if not r.p&Z:
                self._y(0x00)
                self._a(0x01)
                while True:  # natural loop $CC1E
                    m[(0x0160+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._compare(r.y,0x40)
                    self._mark(0xCC24)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(0x00)
                    m[0x0010]=r.a
                    while True:  # natural loop $CC2B
                        self._a(m[0x0472])
                        self._compare(r.a,0x07)
                        self._mark(0xCC30)
                        if r.p&C:
                            pass
                        else:
                            self._compare(r.a,m[WORLD_CURSOR])
                            self._mark(0xCC35)
                            if r.p&Z:
                                m[0x0472]=self._nz(m[0x0472]+1)
                                continue
                            else:
                                if not (yield from self._local_call(self.city_helper_dd56,0xCC37,0xCC3A)):return
                                self._compare(r.a,0xFF)
                                self._mark(0xCC3C)
                                if r.p&Z:
                                    m[0x0472]=self._nz(m[0x0472]+1)
                                    continue
                                else:
                                    self._push(r.a)
                                    self._y(m[0x048B])
                                    self._a(m[0x0472])
                                    m[(0x0490+r.y)&65535]=r.a
                                    m[0x048B]=self._nz(m[0x048B]+1)
                                    self._a(self._pop())
                                    yield from self._external(0xCC4C,0xF308,0xCC4F,"call",None)
                                    if r.pc!=0xCC4F:return  # preserve nonlocal stack return
                                    if not (yield from self._local_call(self.city_helper_d472,0xCC4F,0xCC52)):return
                                    pass
                                pass
                            pass
                        self._a(m[0x0010])
                        self._mark(0xCC55)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x10)
                            m[0x0010]=r.a
                            m[0x0472]=self._nz(m[0x0472]+1)
                            continue
                        m[CURRENT_CITY]=self._nz(m[CURRENT_CITY]-1)
                        m[0x0472]=self._nz(m[0x0472]+1)
                        self._a(m[0x0480])
                        self._flag(C,False)
                        self._add(0x40)
                        m[0x0480]=r.a
                        self._a(m[0x0481])
                        self._add(0x00)
                        m[0x0481]=r.a
                        self._a(m[PPU_JOBS])
                        self._a(r.a | 0x02)
                        m[PPU_JOBS]=r.a
                        self._mark(0xCC81)
                        self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                if not (yield from self._local_call(self.city_helper_dd70,0xCC13,0xCC16)):return
                m[0x046C]=r.a
                self._mark(0xCC19)
                self._rts();return

    def city_helper_cc82(self):
        """$CC82: city helper cc82; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCC82)
        self._a(m[0x0424])
        m[0x0013]=r.a
        self._a(m[0x0425])
        m[0x0014]=r.a
        self._a(0x33)
        m[0x0010]=r.a
        self._a(0xCD)
        m[0x0011]=r.a
        self._a(0x01)
        m[0x0012]=r.a
        yield from self._external(0xCC9D,0xED1E,0xCCA0,"call",None)
        if r.pc!=0xCCA0:return  # preserve nonlocal stack return
        self._y(r.a)
        self._a(m[(0x0490+r.y)&65535])
        self._mark(0xCCA4)
        if not r.p&N:
            pass
        else:
            self._a(m[0x0013])
            m[0x0424]=r.a
            self._a(m[0x0014])
            m[0x0425]=r.a
            self._a(m[0x046C])
            m[0x0012]=r.a
            pass
        self._a(0x3B)
        m[0x0010]=r.a
        self._a(0xCD)
        m[0x0011]=r.a
        self._a(0x47)
        m[0x0000]=r.a
        self._a(0xCD)
        m[0x0001]=r.a
        self._a(m[0x0012])
        m[0x046C]=r.a
        yield from self._external(0xCCD2,0xEDF5,0xCCD5,"call",None)
        if r.pc!=0xCCD5:return  # preserve nonlocal stack return
        self._a(m[NEW_BUTTONS])
        self._a(r.a & 0x03)
        self._mark(0xCCDA)
        if r.p&Z:
            self._mark(0xCCF7)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_dd70,0xCCDC,0xCCDF)):return
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xCCE3)
            if r.p&C:
                self._y(m[0x0012])
                self._a(m[(0x0490+r.y)&65535])
                m[CURRENT_CITY]=r.a
                self._a(m[WORLD_CURSOR])
                if not (yield from self._local_call(self.city_helper_dd56,0xCD04,0xCD07)):return
                self._a(m[CURRENT_CITY])
                if not (yield from self._local_call(self.city_helper_d4ed,0xCD0A,0xCD0D)):return
                self._mark(0xCD0D)
                if not r.p&Z:
                    self._a(0x05)
                    m[PHASE]=r.a
                    self._a(0x29)
                    m[0x042C]=r.a
                    self._a(0x00)
                    m[0x046C]=r.a
                    self._mark(0xCD30)
                    yield from self._external(0xCD30,0xF28B,None,"tail")
                    return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x80)
                    m[0x0478]=r.a
                    self._a(0x0F)
                    m[0x047C]=r.a
                    self._a(0x27)
                    self._mark(0xCD1E)
                    yield from self._external(0xCD1E,0xF28B,None,"tail")
                    return
            else:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xCCE6)
                if not r.p&C:
                    self._mark(0xCCF7)
                    self._rts();return
                else:
                    self._a(0x05)
                    m[PHASE]=r.a
                    self._a(0x3B)
                    m[0x042C]=r.a
                    self._a(0x00)
                    self._mark(0xCCF4)
                    yield from self._external(0xCCF4,0xF28B,None,"tail")
                    return

    def city_helper_cd4c(self):
        """$CD4C: city helper cd4c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD4C)
        self._a(m[0x0478])
        self._mark(0xCD4F)
        if not r.p&Z:
            self._mark(0xCD88)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xCD51,0xCD54)):return
            self._a(m[0x047C])
            self._mark(0xCD57)
            if not r.p&N:
                self._mark(0xCD88)
                self._rts();return
            else:
                self._compare(r.a,0x81)
                self._mark(0xCD5B)
                if not r.p&Z:
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_d7a8,0xCD5D,0xCD60)):return
                    pass
                self._y(0x3D)
                yield from self._external(0xCD62,0xEE07,0xCD67,"far_call",40996)
                if r.pc!=0xCD67:return  # preserve nonlocal stack return
                if not (yield from self._local_call(self.city_helper_dd70,0xCD67,0xCD6A)):return
                self._a(m[0x047C])
                self._compare(r.a,0x90)
                self._mark(0xCD6F)
                if r.p&Z:
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x3B)
                    self._mark(0xCD85)
                    yield from self._external(0xCD85,0xF26D,None,"tail")
                    return
                else:
                    m[PHASE]=self._nz(m[PHASE]+1)
                    self._a(0x00)
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xCD7B)
                    yield from self._external(0xCD7B,0xF26D,None,"tail")
                    return

    def city_helper_cd89(self):
        """$CD89: city helper cd89; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCD89)
        if not (yield from self._local_call(self.city_helper_d5bd,0xCD89,0xCD8C)):return
        self._a(m[0x0013])
        self._mark(0xCD8F)
        if r.p&Z:
            self._mark(0xCDA0)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xCD93)
            if not r.p&Z:
                self._a(0x19)
                m[0x04A2]=r.a
                self._a(m[CURRENT_CITY])
                if not (yield from self._local_call(self.city_helper_dd56,0xCDA9,0xCDAC)):return
                m[0x042C]=r.a
                self._y(0x03)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xCDB5)
                if r.p&Z:
                    self._a(m[CURRENT_CITY])
                    m[0x0010]=r.a
                    if not (yield from self._local_call(self.city_helper_ddbf,0xCDC0,0xCDC3)):return
                    self._a(m[0x0011])
                    m[0x000A]=r.a
                    self._a(m[0x6F03])
                    m[0x0010]=r.a
                    if not (yield from self._local_call(self.city_helper_ddbf,0xCDCF,0xCDD2)):return
                    self._a(m[0x0011])
                    self._flag(C,True)
                    self._add(m[0x000A],subtract=True)
                    self._mark(0xCDD9)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    m[0x000A]=r.a
                    self._a(m[0x042C])
                    yield from self._external(0xCDE3,0xF2D7,0xCDE6,"call",None)
                    if r.pc!=0xCDE6:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0010]=r.a
                    self._a(m[0x0481])
                    yield from self._external(0xCDF0,0xF2D7,0xCDF3,"call",None)
                    if r.pc!=0xCDF3:return  # preserve nonlocal stack return
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0011]=r.a
                    self._y(0x04)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._flag(C,False)
                    self._add(m[0x0011])
                    self._flag(C,True)
                    self._add(m[0x0010],subtract=True)
                    self._mark(0xCE06)
                    if r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    m[0x0004]=r.a
                    self._a(0x04)
                    m[0x0003]=r.a
                    yield from self._external(0xCE1A,0xEA7C,0xCE1D,"call",None)
                    if r.pc!=0xCE1D:return  # preserve nonlocal stack return
                    self._a(m[0x0001])
                    self._flag(C,False)
                    self._add(m[0x000A])
                    self._mark(0xCE24)
                    if not r.p&N:
                        pass
                    else:
                        self._a(0x00)
                        pass
                    m[0x042F]=r.a
                    yield from self._external(0xCE2B,0xE843,0xCE2E,"call",None)
                    if r.pc!=0xCE2E:return  # preserve nonlocal stack return
                    self._compare(r.a,m[0x042F])
                    self._mark(0xCE31)
                    if not r.p&C:
                        self._y(0x39)
                        yield from self._external(0xCE4C,0xEE07,0xCE51,"far_call",40999)
                        if r.pc!=0xCE51:return  # preserve nonlocal stack return
                        self._a(0x03)
                        m[0x0473]=r.a
                        self._a(m[WORLD_CURSOR])
                        m[0x0472]=r.a
                        self._a(0xEC)
                        m[WORLD_CURSOR]=r.a
                        if not (yield from self._local_call(self.city_helper_d568,0xCE61,0xCE64)):return
                        self._a(0x0C)
                        m[PHASE]=r.a
                        self._a(0x00)
                        self._mark(0xCE6B)
                        yield from self._external(0xCE6B,0xF29B,None,"tail")
                        return
                    else:
                        self._a(0x04)
                        m[0x00A4]=r.a
                        if not (yield from self._local_call(self.city_helper_d568,0xCE38,0xCE3B)):return
                        self._a(0x0C)
                        m[PHASE]=r.a
                        self._a(0x43)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x00)
                        self._mark(0xCE47)
                        yield from self._external(0xCE47,0xF29B,None,"tail")
                        return
                else:
                    self._a(m[CURRENT_CITY])
                    m[0x0483]=r.a
                    self._a(m[WORLD_CURSOR])
                    m[0x0482]=r.a
                    if not (yield from self._local_call(self.city_helper_dd56,0xCE7A,0xCE7D)):return
                    m[0x042D]=r.a
                    self._a(m[0x0481])
                    m[0x042E]=r.a
                    self._a(0x01)
                    m[0x0473]=r.a
                    if not (yield from self._local_call(self.city_helper_d568,0xCE61,0xCE64)):return
                    self._a(0x0C)
                    m[PHASE]=r.a
                    self._a(0x00)
                    self._mark(0xCE6B)
                    yield from self._external(0xCE6B,0xF29B,None,"tail")
                    return
            else:
                self._a(0x02)
                m[STATE]=r.a
                if not (yield from self._local_call(self.city_helper_dd70,0xCD9A,0xCD9D)):return
                m[PHASE]=r.a
                self._mark(0xCDA0)
                self._rts();return

    def city_helper_ce8e(self):
        """$CE8E: city helper ce8e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCE8E)
        if not (yield from self._local_call(self.text_request_readiness,0xCE8E,0xCE91)):return
        self._mark(0xCE91)
        if not r.p&C:
            self._mark(0xCEAC)
            self._rts();return
        else:
            self._y(0x3D)
            yield from self._external(0xCE95,0xEE07,0xCE9A,"far_call",40996)
            if r.pc!=0xCE9A:return  # preserve nonlocal stack return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(m[0x042C])
            self._compare(r.a,0x29)
            self._mark(0xCEA2)
            if r.p&Z:
                pass
            else:
                self._y(0x00)
                m[PHASE]=r.y
                pass
            self._mark(0xCEA9)
            yield from self._external(0xCEA9,0xF26D,None,"tail")
            return

    def city_helper_cead(self):
        """$CEAD: city helper cead; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCEAD)
        if not (yield from self._local_call(self.city_helper_d5bd,0xCEAD,0xCEB0)):return
        self._a(m[0x0013])
        self._mark(0xCEB3)
        if r.p&Z:
            self._mark(0xCEC6)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xCEB7)
            if not r.p&Z:
                self._a(m[WORLD_CURSOR])
                if not (yield from self._local_call(self.city_helper_dd56,0xCECA,0xCECD)):return
                self._a(m[CURRENT_CITY])
                if not (yield from self._local_call(self.city_helper_d508,0xCED0,0xCED3)):return
                self._a(m[CURRENT_CITY])
                if not (yield from self._local_call(self.city_helper_dd56,0xCED6,0xCED9)):return
                self._a(m[WORLD_CURSOR])
                if not (yield from self._local_call(self.city_helper_d508,0xCEDC,0xCEDF)):return
                self._a(m[CURRENT_CITY])
                if not (yield from self._local_call(self.city_helper_dd56,0xCEE2,0xCEE5)):return
                m[0x042C]=r.a
                self._a(0x80)
                m[0x0473]=r.a
                self._a(0x0E)
                m[PHASE]=r.a
                self._a(0x44)
                self._mark(0xCEF4)
                yield from self._external(0xCEF4,0xF26D,None,"tail")
                return
            else:
                if not (yield from self._local_call(self.city_helper_dd70,0xCEB9,0xCEBC)):return
                self._a(0x02)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xCEC6)
                self._rts();return

    def city_helper_cef7(self):
        """$CEF7: city helper cef7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCEF7)
        self._a(m[WORLD_CURSOR])
        yield from self._external(0xCEFA,0xF2AF,0xCEFD,"call",None)
        if r.pc!=0xCEFD:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.city_helper_dc6b,0xCEFD,0xCF00)):return
        self._compare(r.x,0x0A)
        self._mark(0xCF02)
        if r.p&Z:
            self._a(0x0E)
            m[PHASE]=r.a
            self._a(0x80)
            m[0x0473]=r.a
            self._a(0x47)
            self._mark(0xCF1B)
            yield from self._external(0xCF1B,0xF26D,None,"tail")
            return
        else:
            if not (yield from self._local_call(self.city_helper_d568,0xCF04,0xCF07)):return
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x3E)
            self._mark(0xCF0C)
            yield from self._external(0xCF0C,0xF26D,None,"tail")
            return

    def city_helper_cf1e(self):
        """$CF1E: city helper cf1e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF1E)
        if not (yield from self._local_call(self.world_selection_portrait,0xCF1E,0xCF21)):return
        if not (yield from self._local_call(self.text_request_readiness,0xCF21,0xCF24)):return
        self._mark(0xCF24)
        if not r.p&C:
            self._mark(0xCF8C)
            self._rts();return
        else:
            self._a(m[NEW_BUTTONS])
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xCF2A)
            if not r.p&C:
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xCF5F)
                if not r.p&C:
                    pass
                else:
                    if not (yield from self._local_call(self.text_request_readiness,0xCF61,0xCF64)):return
                    self._mark(0xCF64)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0xFF)
                        m[0x04E4]=r.a
                        self._a(0x02)
                        m[STATE]=r.a
                        self._a(0x00)
                        m[PHASE]=r.a
                        self._a(0x02)
                        if not (yield from self._local_call(self.city_helper_d58c,0xCF77,0xCF7A)):return
                        pass
                    pass
                self._mark(0xCF8C)
                self._rts();return
            else:
                if not (yield from self._local_call(self.city_at_cursor,0xCF2C,0xCF2F)):return
                self._compare(r.y,0xFF)
                self._mark(0xCF31)
                if r.p&Z:
                    self._a(0x24)
                    self._mark(0xCF84)
                    yield from self._external(0xCF84,0xF26D,None,"tail")
                    return
                else:
                    m[CITY]=r.y
                    self._a(r.y)
                    m[CURRENT_CITY]=r.a
                    yield from self._external(0xCF3A,0xF2AF,0xCF3D,"call",None)
                    if r.pc!=0xCF3D:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    self._compare(r.a,0x07)
                    self._mark(0xCF45)
                    if r.p&Z:
                        self._a(0x46)
                        self._mark(0xCF7F)
                        yield from self._external(0xCF7F,0xF26D,None,"tail")
                        return
                    else:
                        self._compare(r.a,m[0x6F03])
                        self._mark(0xCF4A)
                        if r.p&Z:
                            self._a(0x40)
                            self._mark(0xCF89)
                            yield from self._external(0xCF89,0xF26D,None,"tail")
                            return
                        else:
                            m[PHASE]=self._nz(m[PHASE]+1)
                            self._a(0x80)
                            m[0x0478]=r.a
                            self._a(0x0F)
                            m[0x047C]=r.a
                            self._a(0x48)
                            self._mark(0xCF5B)
                            yield from self._external(0xCF5B,0xF26D,None,"tail")
                            return

    def city_helper_cf8d(self):
        """$CF8D: city helper cf8d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCF8D)
        self._a(m[0x0478])
        self._mark(0xCF90)
        if not r.p&Z:
            self._mark(0xCFE3)
            self._rts();return
        else:
            self._a(0xFF)
            m[0x04E4]=r.a
            if not (yield from self._local_call(self.city_helper_d64a,0xCF97,0xCF9A)):return
            self._a(m[0x047C])
            self._mark(0xCF9D)
            if not r.p&N:
                self._mark(0xCFE3)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xCFA1)
                if r.p&Z:
                    self._a(0x02)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x02)
                    if not (yield from self._local_call(self.city_helper_d58c,0xCFE0,0xCFE3)):return
                    self._mark(0xCFE3)
                    self._rts();return
                else:
                    self._compare(r.a,0x81)
                    self._mark(0xCFA5)
                    if r.p&Z:
                        self._a(0x0F)
                        m[0x047C]=r.a
                        self._a(0x80)
                        m[0x0478]=r.a
                        self._a(0x4A)
                        self._mark(0xCFD1)
                        yield from self._external(0xCFD1,0xF26D,None,"tail")
                        return
                    else:
                        self._a(m[0x0481])
                        m[0x042C]=r.a
                        m[PHASE]=self._nz(m[PHASE]+1)
                        self._a(m[WORLD_CURSOR])
                        m[CITY]=r.a
                        self._a(0x80)
                        m[0x0478]=r.a
                        self._a(0x0F)
                        m[0x047C]=r.a
                        self._a(0x27)
                        self._mark(0xCFC2)
                        yield from self._external(0xCFC2,0xF26D,None,"tail")
                        return

    def city_helper_cfe4(self):
        """$CFE4: city helper cfe4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCFE4)
        self._a(m[0x0478])
        self._mark(0xCFE7)
        if not r.p&Z:
            self._mark(0xD01E)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d64a,0xCFE9,0xCFEC)):return
            self._a(m[0x047C])
            self._mark(0xCFEF)
            if not r.p&N:
                self._mark(0xD01E)
                self._rts();return
            else:
                self._compare(r.a,0x90)
                self._mark(0xCFF3)
                if r.p&Z:
                    self._a(0x02)
                    m[STATE]=r.a
                    self._a(0x00)
                    m[PHASE]=r.a
                    self._a(0x02)
                    if not (yield from self._local_call(self.city_helper_d58c,0xD01B,0xD01E)):return
                    self._mark(0xD01E)
                    self._rts();return
                else:
                    self._compare(r.a,0x81)
                    self._mark(0xCFF7)
                    if not r.p&Z:
                        pass
                    else:
                        if not (yield from self._local_call(self.city_helper_d7a8,0xCFF9,0xCFFC)):return
                        pass
                    self._a(0x02)
                    if not (yield from self._local_call(self.city_helper_d58c,0xCFFE,0xD001)):return
                    m[PHASE]=self._nz(m[PHASE]+1)
                    if not (yield from self._local_call(self.city_helper_dd70,0xD004,0xD007)):return
                    m[0x046C]=r.a
                    self._a(0x29)
                    self._mark(0xD00C)
                    yield from self._external(0xD00C,0xF26D,None,"tail")
                    return

    def city_helper_d01f(self):
        """$D01F: city helper d01f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD01F)
        if not (yield from self._local_call(self.city_helper_d5bd,0xD01F,0xD022)):return
        self._a(m[0x0013])
        self._mark(0xD025)
        if r.p&Z:
            self._mark(0xD035)
            self._rts();return
        else:
            self._compare(r.a,0xFF)
            self._mark(0xD029)
            if not r.p&Z:
                self._a(m[0x0472])
                self._mark(0xD039)
                if not r.p&Z:
                    self._a(0x13)
                    m[0x04A2]=r.a
                    if not (yield from self._local_call(self.city_helper_d2e3,0xD043,0xD046)):return
                    yield from self._external(0xD046,0xE843,0xD049,"call",None)
                    if r.pc!=0xD049:return  # preserve nonlocal stack return
                    self._compare(r.a,m[0x0001])
                    self._mark(0xD04C)
                    if not r.p&C:
                        if not (yield from self._local_call(self.city_helper_d41b,0xD051,0xD054)):return
                        self._a(0x4B)
                        m[WORLD_CURSOR]=r.a
                        self._a(0x02)
                        m[0x0473]=r.a
                        self._a(0x03)
                        m[0x00A4]=r.a
                        pass
                    else:
                        self._a(0x04)
                        m[0x00A4]=r.a
                        self._a(0x4C)
                        m[WORLD_CURSOR]=r.a
                        pass
                    pass
                else:
                    self._a(0x04)
                    m[0x04A2]=r.a
                    if not (yield from self._local_call(self.city_helper_d3c5,0xD06B,0xD06E)):return
                    yield from self._external(0xD06E,0xE843,0xD071,"call",None)
                    if r.pc!=0xD071:return  # preserve nonlocal stack return
                    self._compare(r.a,m[0x0001])
                    self._mark(0xD074)
                    if not r.p&C:
                        self._a(m[0x0481])
                        yield from self._external(0xD07C,0xF2D7,0xD07F,"call",None)
                        if r.pc!=0xD07F:return  # preserve nonlocal stack return
                        self._y(0x02)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0001]=r.a
                        self._a(0x14)
                        m[0x0003]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        m[0x0004]=r.a
                        yield from self._external(0xD093,0xEA7C,0xD096,"call",None)
                        if r.pc!=0xD096:return  # preserve nonlocal stack return
                        yield from self._external(0xD096,0xE850,0xD099,"call",None)
                        if r.pc!=0xD099:return  # preserve nonlocal stack return
                        self._flag(C,False)
                        self._add(m[0x0001])
                        self._mark(0xD09D)
                        if r.p&Z:
                            self._a(0x04)
                            m[0x00A4]=r.a
                            self._a(0x4C)
                            m[WORLD_CURSOR]=r.a
                            pass
                        else:
                            m[0x0010]=r.a
                            self._a(m[0x042C])
                            yield from self._external(0xD0A5,0xF2D7,0xD0A8,"call",None)
                            if r.pc!=0xD0A8:return  # preserve nonlocal stack return
                            self._y(0x03)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            self._flag(C,True)
                            self._add(m[0x0010],subtract=True)
                            self._mark(0xD0B0)
                            if r.p&C:
                                pass
                            else:
                                self._a(0x00)
                                pass
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            self._a(0x4E)
                            m[WORLD_CURSOR]=r.a
                            self._a(0x03)
                            m[0x00A4]=r.a
                            pass
                        pass
                    else:
                        self._a(0x04)
                        m[0x00A4]=r.a
                        self._a(0x4C)
                        m[WORLD_CURSOR]=r.a
                        pass
                    pass
                if not (yield from self._local_call(self.city_helper_d568,0xD0DB,0xD0DE)):return
                self._a(0x0C)
                m[PHASE]=r.a
                self._a(0x00)
                self._mark(0xD0E5)
                yield from self._external(0xD0E5,0xF29B,None,"tail")
                return
            else:
                self._a(0x02)
                m[STATE]=r.a
                self._a(0x00)
                m[PHASE]=r.a
                self._mark(0xD035)
                self._rts();return

    def city_helper_d0e8(self):
        """$D0E8: city helper d0e8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0E8)
        self._a(m[0x0140])
        self._mark(0xD0EB)
        if not r.p&Z:
            pass
        else:
            self._a(m[0x04A2])
            m[0x04A0]=r.a
            m[PHASE]=self._nz(m[PHASE]+1)
            self._a(0x60)
            m[0x046C]=r.a
            pass
        self._mark(0xD0FB)
        self._rts();return

    def city_helper_d0fc(self):
        """$D0FC: city helper d0fc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD0FC)
        self._a(m[0x04A0])
        self._mark(0xD0FF)
        if not r.p&Z:
            self._mark(0xD13E)
            self._rts();return
        else:
            self._a(0x02)
            if not (yield from self._local_call(self.city_helper_d58c,0xD103,0xD106)):return
            self._a(m[0x0473])
            self._compare(r.a,0x01)
            self._mark(0xD10B)
            if not r.p&Z:
                self._compare(r.a,0x03)
                self._mark(0xD121)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x10)
                    m[PHASE]=r.a
                    pass
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(m[0x0481])
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xD133,0xEE07,0xD138,"far_call",41002)
                if r.pc!=0xD138:return  # preserve nonlocal stack return
                self._a(m[WORLD_CURSOR])
                self._mark(0xD13B)
                yield from self._external(0xD13B,0xF26D,None,"tail")
                return
            else:
                self._a(0x0F)
                m[PHASE]=r.a
                self._a(m[0x6F44])
                self._a(r.a ^ 0x01)
                m[0x6F44]=r.a
                self._a(0xE2)
                self._mark(0xD11C)
                yield from self._external(0xD11C,0xF28B,None,"tail")
                return

    def city_helper_d13f(self):
        """$D13F: city helper d13f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD13F)
        if not (yield from self._local_call(self.text_request_readiness,0xD13F,0xD142)):return
        self._mark(0xD142)
        if not r.p&C:
            pass
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xD144,0xD147)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xD14C)
            if r.p&Z:
                pass
            else:
                if not (yield from self._local_call(self.city_helper_d568,0xD14E,0xD151)):return
                self._a(0x00)
                m[STATE]=r.a
                m[PHASE]=r.a
                self._a(m[0x0473])
                self._compare(r.a,0x81)
                self._mark(0xD15E)
                if not r.p&Z:
                    self._compare(r.a,0x02)
                    self._mark(0xD16D)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[CURRENT_CITY])
                        yield from self._external(0xD172,0xF2AF,0xD175,"call",None)
                        if r.pc!=0xD175:return  # preserve nonlocal stack return
                        self._y(0x11)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._compare(r.a,0xFF)
                        self._mark(0xD17B)
                        if not r.p&Z:
                            pass
                        else:
                            self._y(0x00)
                            self._a(0x07)
                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                            pass
                        pass
                    pass
                else:
                    self._a(m[0x6F44])
                    self._a(r.a ^ 0x01)
                    m[0x6F44]=r.a
                    pass
                pass
            pass
        self._a(m[0x0473])
        self._mark(0xD186)
        if r.p&N:
            pass
        else:
            self._a(m[0x0481])
            if not (yield from self._local_call(self.city_helper_dd5e,0xD18B,0xD18E)):return
            pass
        self._mark(0xD18E)
        self._rts();return

    def city_helper_d18f(self):
        """$D18F: city helper d18f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD18F)
        if not (yield from self._local_call(self.text_request_readiness,0xD18F,0xD192)):return
        self._mark(0xD192)
        if not r.p&C:
            self._a(m[0x0473])
            self._mark(0xD186)
            if r.p&N:
                pass
            else:
                self._a(m[0x0481])
                if not (yield from self._local_call(self.city_helper_dd5e,0xD18B,0xD18E)):return
                pass
            self._mark(0xD18E)
            self._rts();return
        else:
            if not (yield from self._local_call(self.city_helper_d543,0xD194,0xD197)):return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            self._mark(0xD19C)
            if r.p&Z:
                self._mark(0xD1B8)
                self._rts();return
            else:
                m[PHASE]=self._nz(m[PHASE]+1)
                self._a(0x00)
                m[0x00A4]=r.a
                self._a(m[0x0481])
                m[0x0000]=r.a
                self._y(0x3D)
                yield from self._external(0xD1AE,0xEE07,0xD1B3,"far_call",41002)
                if r.pc!=0xD1B3:return  # preserve nonlocal stack return
                self._a(0xEF)
                self._mark(0xD1B5)
                yield from self._external(0xD1B5,0xF26D,None,"tail")
                return

    def city_helper_d1b9(self):
        """$D1B9: city helper d1b9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1B9)
        self._a(m[0x0481])
        if not (yield from self._local_call(self.city_helper_dd5e,0xD1BC,0xD1BF)):return
        if not (yield from self._local_call(self.text_request_readiness,0xD1BF,0xD1C2)):return
        self._mark(0xD1C2)
        if not r.p&C:
            self._mark(0xD22E)
            self._rts();return
        else:
            self._a(0x2F)
            m[0x0010]=r.a
            self._a(0xD2)
            m[0x0011]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            yield from self._external(0xD1D3,0xED1E,0xD1D6,"call",None)
            if r.pc!=0xD1D6:return  # preserve nonlocal stack return
            self._a(0x33)
            m[0x0010]=r.a
            self._a(0xD2)
            m[0x0011]=r.a
            self._a(0x37)
            m[0x0000]=r.a
            self._a(0xD2)
            m[0x0001]=r.a
            self._a(m[0x0012])
            yield from self._external(0xD1ED,0xEDF5,0xD1F0,"call",None)
            if r.pc!=0xD1F0:return  # preserve nonlocal stack return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD1F5)
            if r.p&Z:
                self._mark(0xD22E)
                self._rts();return
            else:
                self._a(0x0E)
                m[PHASE]=r.a
                self._a(0x81)
                m[0x0473]=r.a
                self._a(m[0x042D])
                m[0x042C]=r.a
                self._a(m[0x0012])
                self._mark(0xD20A)
                if not r.p&Z:
                    self._a(0xE5)
                    self._mark(0xD22B)
                    yield from self._external(0xD22B,0xF28B,None,"tail")
                    return
                else:
                    self._a(m[0x0482])
                    if not (yield from self._local_call(self.city_helper_dd56,0xD20F,0xD212)):return
                    self._a(m[0x0483])
                    if not (yield from self._local_call(self.city_helper_d508,0xD215,0xD218)):return
                    self._a(m[0x0483])
                    if not (yield from self._local_call(self.city_helper_dd56,0xD21B,0xD21E)):return
                    self._a(m[0x0482])
                    if not (yield from self._local_call(self.city_helper_d508,0xD221,0xD224)):return
                    self._a(0xE4)
                    self._mark(0xD226)
                    yield from self._external(0xD226,0xF28B,None,"tail")
                    return

    def city_helper_d23c(self):
        """$D23C: city helper d23c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD23C)
        self._a(m[0x0481])
        if not (yield from self._local_call(self.city_helper_dd5e,0xD23F,0xD242)):return
        if not (yield from self._local_call(self.text_request_readiness,0xD242,0xD245)):return
        self._mark(0xD245)
        if not r.p&C:
            self._mark(0xD22E)
            self._rts();return
        else:
            self._a(0xD6)
            m[0x0010]=r.a
            self._a(0xD2)
            m[0x0011]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            yield from self._external(0xD256,0xED1E,0xD259,"call",None)
            if r.pc!=0xD259:return  # preserve nonlocal stack return
            self._a(0xDA)
            m[0x0010]=r.a
            self._a(0xD2)
            m[0x0011]=r.a
            self._a(0xDE)
            m[0x0000]=r.a
            self._a(0xD2)
            m[0x0001]=r.a
            self._a(m[0x0012])
            yield from self._external(0xD270,0xEDF5,0xD273,"call",None)
            if r.pc!=0xD273:return  # preserve nonlocal stack return
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x01)
            self._mark(0xD278)
            if not r.p&Z:
                self._a(0x80)
                m[0x0473]=r.a
                self._a(0x0E)
                m[PHASE]=r.a
                self._a(m[0x0012])
                self._mark(0xD288)
                if r.p&Z:
                    self._y(0x39)
                    yield from self._external(0xD291,0xEE07,0xD296,"far_call",41008)
                    if r.pc!=0xD296:return  # preserve nonlocal stack return
                    self._a(m[0x042D])
                    self._mark(0xD299)
                    if r.p&Z:
                        self._x(0x2A)
                        self._a(m[0x042E])
                        self._compare(r.a,0xF0)
                        self._mark(0xD2CE)
                        if r.p&Z:
                            pass
                        else:
                            self._x(0xED)
                            pass
                        self._a(r.x)
                        self._mark(0xD2D3)
                        yield from self._external(0xD2D3,0xF28B,None,"tail")
                        return
                    else:
                        self._a(m[0x0472])
                        if not (yield from self._local_call(self.city_helper_dd56,0xD29E,0xD2A1)):return
                        self._a(m[CURRENT_CITY])
                        if not (yield from self._local_call(self.city_helper_d508,0xD2A4,0xD2A7)):return
                        self._a(m[CURRENT_CITY])
                        if not (yield from self._local_call(self.city_helper_dd56,0xD2AA,0xD2AD)):return
                        self._a(m[0x0472])
                        if not (yield from self._local_call(self.city_helper_d508,0xD2B0,0xD2B3)):return
                        self._a(0x00)
                        m[0x0473]=r.a
                        self._a(0x03)
                        m[0x00A4]=r.a
                        self._a(0x02)
                        if not (yield from self._local_call(self.city_helper_d58c,0xD2BF,0xD2C2)):return
                        self._a(0xE4)
                        self._mark(0xD2C4)
                        yield from self._external(0xD2C4,0xF28B,None,"tail")
                        return
                else:
                    self._a(0xE5)
                    self._mark(0xD28C)
                    yield from self._external(0xD28C,0xF28B,None,"tail")
                    return
            else:
                self._mark(0xD27A)
                self._rts();return

    def city_helper_d2e3(self):
        """$D2E3: city helper d2e3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2E3)
        self._a(m[0x042C])
        yield from self._external(0xD2E6,0xF2D7,0xD2E9,"call",None)
        if r.pc!=0xD2E9:return  # preserve nonlocal stack return
        self._y(0x03)
        self._x(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x1F)
        self._mark(0xD2F1)
        if not r.p&C:
            self._a(m[(0xD3AD+r.x)&65535])
            m[0x0010]=r.a
            self._a(m[(0xD3AE+r.x)&65535])
            m[0x0011]=r.a
            self._a(m[(0xD3AF+r.x)&65535])
            m[0x0012]=r.a
            self._a(m[(0xD3B0+r.x)&65535])
            m[0x0013]=r.a
            self._a(m[0x0481])
            yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
            if r.pc!=0xD335:return  # preserve nonlocal stack return
            self._y(0x0B)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._push(r.a)
            self._y(0x02)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0003]=r.a
            self._y(0x04)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            m[0x0002]=r.a
            yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
            if r.pc!=0xD357:return  # preserve nonlocal stack return
            self._a(m[0x0006])
            self._flag(C,False)
            self._add(m[0x0010])
            m[0x0010]=r.a
            self._a(m[0x0007])
            self._add(m[0x0011])
            m[0x0011]=r.a
            self._a(self._pop())
            m[0x0000]=r.a
            self._a(0x00)
            m[0x0001]=r.a
            m[0x0002]=r.a
            self._a(0x64)
            m[0x0003]=r.a
            yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
            if r.pc!=0xD37E:return  # preserve nonlocal stack return
            self._a(m[0x0006])
            self._flag(C,False)
            self._add(m[0x0010])
            m[0x0010]=r.a
            self._a(m[0x0007])
            self._add(m[0x0011])
            m[0x0011]=r.a
            self._a(m[0x0010])
            m[0x0001]=r.a
            self._a(m[0x0011])
            m[0x0002]=r.a
            self._a(m[0x0012])
            m[0x0003]=r.a
            self._a(m[0x0013])
            m[0x0004]=r.a
            yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
            if r.pc!=0xD3AC:return  # preserve nonlocal stack return
            self._mark(0xD3AC)
            self._rts();return
        else:
            self._x(0x04)
            self._compare(r.a,0x29)
            self._mark(0xD2F7)
            if not r.p&C:
                self._a(m[(0xD3AD+r.x)&65535])
                m[0x0010]=r.a
                self._a(m[(0xD3AE+r.x)&65535])
                m[0x0011]=r.a
                self._a(m[(0xD3AF+r.x)&65535])
                m[0x0012]=r.a
                self._a(m[(0xD3B0+r.x)&65535])
                m[0x0013]=r.a
                self._a(m[0x0481])
                yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
                if r.pc!=0xD335:return  # preserve nonlocal stack return
                self._y(0x0B)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._push(r.a)
                self._y(0x02)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0003]=r.a
                self._y(0x04)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
                if r.pc!=0xD357:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                self._flag(C,False)
                self._add(m[0x0010])
                m[0x0010]=r.a
                self._a(m[0x0007])
                self._add(m[0x0011])
                m[0x0011]=r.a
                self._a(self._pop())
                m[0x0000]=r.a
                self._a(0x00)
                m[0x0001]=r.a
                m[0x0002]=r.a
                self._a(0x64)
                m[0x0003]=r.a
                yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
                if r.pc!=0xD37E:return  # preserve nonlocal stack return
                self._a(m[0x0006])
                self._flag(C,False)
                self._add(m[0x0010])
                m[0x0010]=r.a
                self._a(m[0x0007])
                self._add(m[0x0011])
                m[0x0011]=r.a
                self._a(m[0x0010])
                m[0x0001]=r.a
                self._a(m[0x0011])
                m[0x0002]=r.a
                self._a(m[0x0012])
                m[0x0003]=r.a
                self._a(m[0x0013])
                m[0x0004]=r.a
                yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
                if r.pc!=0xD3AC:return  # preserve nonlocal stack return
                self._mark(0xD3AC)
                self._rts();return
            else:
                self._x(0x08)
                self._compare(r.a,0x33)
                self._mark(0xD2FD)
                if not r.p&C:
                    self._a(m[(0xD3AD+r.x)&65535])
                    m[0x0010]=r.a
                    self._a(m[(0xD3AE+r.x)&65535])
                    m[0x0011]=r.a
                    self._a(m[(0xD3AF+r.x)&65535])
                    m[0x0012]=r.a
                    self._a(m[(0xD3B0+r.x)&65535])
                    m[0x0013]=r.a
                    self._a(m[0x0481])
                    yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
                    if r.pc!=0xD335:return  # preserve nonlocal stack return
                    self._y(0x0B)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    r.a=self._shift(r.a,False,rotate=False)
                    self._push(r.a)
                    self._y(0x02)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0003]=r.a
                    self._y(0x04)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    m[0x0000]=r.a
                    self._a(0x00)
                    m[0x0001]=r.a
                    m[0x0002]=r.a
                    yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
                    if r.pc!=0xD357:return  # preserve nonlocal stack return
                    self._a(m[0x0006])
                    self._flag(C,False)
                    self._add(m[0x0010])
                    m[0x0010]=r.a
                    self._a(m[0x0007])
                    self._add(m[0x0011])
                    m[0x0011]=r.a
                    self._a(self._pop())
                    m[0x0000]=r.a
                    self._a(0x00)
                    m[0x0001]=r.a
                    m[0x0002]=r.a
                    self._a(0x64)
                    m[0x0003]=r.a
                    yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
                    if r.pc!=0xD37E:return  # preserve nonlocal stack return
                    self._a(m[0x0006])
                    self._flag(C,False)
                    self._add(m[0x0010])
                    m[0x0010]=r.a
                    self._a(m[0x0007])
                    self._add(m[0x0011])
                    m[0x0011]=r.a
                    self._a(m[0x0010])
                    m[0x0001]=r.a
                    self._a(m[0x0011])
                    m[0x0002]=r.a
                    self._a(m[0x0012])
                    m[0x0003]=r.a
                    self._a(m[0x0013])
                    m[0x0004]=r.a
                    yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
                    if r.pc!=0xD3AC:return  # preserve nonlocal stack return
                    self._mark(0xD3AC)
                    self._rts();return
                else:
                    self._x(0x0C)
                    self._compare(r.a,0x3D)
                    self._mark(0xD303)
                    if not r.p&C:
                        self._a(m[(0xD3AD+r.x)&65535])
                        m[0x0010]=r.a
                        self._a(m[(0xD3AE+r.x)&65535])
                        m[0x0011]=r.a
                        self._a(m[(0xD3AF+r.x)&65535])
                        m[0x0012]=r.a
                        self._a(m[(0xD3B0+r.x)&65535])
                        m[0x0013]=r.a
                        self._a(m[0x0481])
                        yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
                        if r.pc!=0xD335:return  # preserve nonlocal stack return
                        self._y(0x0B)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._push(r.a)
                        self._y(0x02)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0003]=r.a
                        self._y(0x04)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0000]=r.a
                        self._a(0x00)
                        m[0x0001]=r.a
                        m[0x0002]=r.a
                        yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
                        if r.pc!=0xD357:return  # preserve nonlocal stack return
                        self._a(m[0x0006])
                        self._flag(C,False)
                        self._add(m[0x0010])
                        m[0x0010]=r.a
                        self._a(m[0x0007])
                        self._add(m[0x0011])
                        m[0x0011]=r.a
                        self._a(self._pop())
                        m[0x0000]=r.a
                        self._a(0x00)
                        m[0x0001]=r.a
                        m[0x0002]=r.a
                        self._a(0x64)
                        m[0x0003]=r.a
                        yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
                        if r.pc!=0xD37E:return  # preserve nonlocal stack return
                        self._a(m[0x0006])
                        self._flag(C,False)
                        self._add(m[0x0010])
                        m[0x0010]=r.a
                        self._a(m[0x0007])
                        self._add(m[0x0011])
                        m[0x0011]=r.a
                        self._a(m[0x0010])
                        m[0x0001]=r.a
                        self._a(m[0x0011])
                        m[0x0002]=r.a
                        self._a(m[0x0012])
                        m[0x0003]=r.a
                        self._a(m[0x0013])
                        m[0x0004]=r.a
                        yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
                        if r.pc!=0xD3AC:return  # preserve nonlocal stack return
                        self._mark(0xD3AC)
                        self._rts();return
                    else:
                        self._x(0x10)
                        self._compare(r.a,0x47)
                        self._mark(0xD309)
                        if not r.p&C:
                            self._a(m[(0xD3AD+r.x)&65535])
                            m[0x0010]=r.a
                            self._a(m[(0xD3AE+r.x)&65535])
                            m[0x0011]=r.a
                            self._a(m[(0xD3AF+r.x)&65535])
                            m[0x0012]=r.a
                            self._a(m[(0xD3B0+r.x)&65535])
                            m[0x0013]=r.a
                            self._a(m[0x0481])
                            yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
                            if r.pc!=0xD335:return  # preserve nonlocal stack return
                            self._y(0x0B)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            self._push(r.a)
                            self._y(0x02)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0003]=r.a
                            self._y(0x04)
                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                            m[0x0000]=r.a
                            self._a(0x00)
                            m[0x0001]=r.a
                            m[0x0002]=r.a
                            yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
                            if r.pc!=0xD357:return  # preserve nonlocal stack return
                            self._a(m[0x0006])
                            self._flag(C,False)
                            self._add(m[0x0010])
                            m[0x0010]=r.a
                            self._a(m[0x0007])
                            self._add(m[0x0011])
                            m[0x0011]=r.a
                            self._a(self._pop())
                            m[0x0000]=r.a
                            self._a(0x00)
                            m[0x0001]=r.a
                            m[0x0002]=r.a
                            self._a(0x64)
                            m[0x0003]=r.a
                            yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
                            if r.pc!=0xD37E:return  # preserve nonlocal stack return
                            self._a(m[0x0006])
                            self._flag(C,False)
                            self._add(m[0x0010])
                            m[0x0010]=r.a
                            self._a(m[0x0007])
                            self._add(m[0x0011])
                            m[0x0011]=r.a
                            self._a(m[0x0010])
                            m[0x0001]=r.a
                            self._a(m[0x0011])
                            m[0x0002]=r.a
                            self._a(m[0x0012])
                            m[0x0003]=r.a
                            self._a(m[0x0013])
                            m[0x0004]=r.a
                            yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
                            if r.pc!=0xD3AC:return  # preserve nonlocal stack return
                            self._mark(0xD3AC)
                            self._rts();return
                        else:
                            self._x(0x14)
                            self._compare(r.a,0x4C)
                            self._mark(0xD30F)
                            if not r.p&C:
                                self._a(m[(0xD3AD+r.x)&65535])
                                m[0x0010]=r.a
                                self._a(m[(0xD3AE+r.x)&65535])
                                m[0x0011]=r.a
                                self._a(m[(0xD3AF+r.x)&65535])
                                m[0x0012]=r.a
                                self._a(m[(0xD3B0+r.x)&65535])
                                m[0x0013]=r.a
                                self._a(m[0x0481])
                                yield from self._external(0xD332,0xF2D7,0xD335,"call",None)
                                if r.pc!=0xD335:return  # preserve nonlocal stack return
                                self._y(0x0B)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                r.a=self._shift(r.a,False,rotate=False)
                                self._push(r.a)
                                self._y(0x02)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x0003]=r.a
                                self._y(0x04)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                m[0x0000]=r.a
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                yield from self._external(0xD354,0xEBE9,0xD357,"call",None)
                                if r.pc!=0xD357:return  # preserve nonlocal stack return
                                self._a(m[0x0006])
                                self._flag(C,False)
                                self._add(m[0x0010])
                                m[0x0010]=r.a
                                self._a(m[0x0007])
                                self._add(m[0x0011])
                                m[0x0011]=r.a
                                self._a(self._pop())
                                m[0x0000]=r.a
                                self._a(0x00)
                                m[0x0001]=r.a
                                m[0x0002]=r.a
                                self._a(0x64)
                                m[0x0003]=r.a
                                yield from self._external(0xD37B,0xEBE9,0xD37E,"call",None)
                                if r.pc!=0xD37E:return  # preserve nonlocal stack return
                                self._a(m[0x0006])
                                self._flag(C,False)
                                self._add(m[0x0010])
                                m[0x0010]=r.a
                                self._a(m[0x0007])
                                self._add(m[0x0011])
                                m[0x0011]=r.a
                                self._a(m[0x0010])
                                m[0x0001]=r.a
                                self._a(m[0x0011])
                                m[0x0002]=r.a
                                self._a(m[0x0012])
                                m[0x0003]=r.a
                                self._a(m[0x0013])
                                m[0x0004]=r.a
                                yield from self._external(0xD3A9,0xEA7C,0xD3AC,"call",None)
                                if r.pc!=0xD3AC:return  # preserve nonlocal stack return
                                self._mark(0xD3AC)
                                self._rts();return
                            else:
                                self._a(0x00)
                                m[0x0001]=r.a
                                self._mark(0xD316)
                                self._rts();return

    def city_helper_d3c5(self):
        """$D3C5: city helper d3c5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD3C5)
        self._a(m[0x042C])
        yield from self._external(0xD3C8,0xF2D7,0xD3CB,"call",None)
        if r.pc!=0xD3CB:return  # preserve nonlocal stack return
        self._y(0x03)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0003]=r.a
        self._a(0x62)
        self._flag(C,True)
        self._add(m[0x0003],subtract=True)
        self._mark(0xD3D8)
        if r.p&C:
            pass
        else:
            self._a(0x00)
            pass
        m[0x0003]=r.a
        self._a(m[0x0481])
        yield from self._external(0xD3E2,0xF2D7,0xD3E5,"call",None)
        if r.pc!=0xD3E5:return  # preserve nonlocal stack return
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        m[0x0004]=r.a
        self._y(0x04)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0004])
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        yield from self._external(0xD3FF,0xEBE9,0xD402,"call",None)
        if r.pc!=0xD402:return  # preserve nonlocal stack return
        self._a(m[0x0006])
        m[0x0001]=r.a
        self._a(m[0x0007])
        m[0x0002]=r.a
        self._a(0x64)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        self._mark(0xD418)
        yield from self._external(0xD418,0xEA7C,None,"tail")
        return

    def city_helper_d41b(self):
        """$D41B: city helper d41b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD41B)
        self._a(m[WORLD_CURSOR])
        yield from self._external(0xD41E,0xF2AF,0xD421,"call",None)
        if r.pc!=0xD421:return  # preserve nonlocal stack return
        self._y(0x10)
        while True:  # natural loop $D423
            self._y(r.y+1)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xD428)
            if not r.p&Z:
                continue
            else:
                pass
            self._a(m[0x042C])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._a(m[CURRENT_CITY])
            yield from self._external(0xD432,0xF2AF,0xD435,"call",None)
            if r.pc!=0xD435:return  # preserve nonlocal stack return
            self._y(0x10)
            while True:  # natural loop $D437
                self._y(r.y+1)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,m[0x042C])
                self._mark(0xD43D)
                if not r.p&Z:
                    continue
                else:
                    pass
                while True:  # natural loop $D43F
                    self._y(r.y+1)
                    self._compare(r.y,0x1B)
                    self._mark(0xD442)
                    if r.p&Z:
                        pass
                    else:
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._y(r.y-1)
                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                        self._y(r.y+1)
                        continue
                    self._y(r.y-1)
                    self._a(0xFF)
                    m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                    self._a(m[0x042C])
                    m[0x0031]=r.a
                    self._a(m[WORLD_CURSOR])
                    if not (yield from self._local_call(self.city_helper_dd4f,0xD45B,0xD45E)):return
                    m[0x0030]=r.a
                    self._a(m[CURRENT_CITY])
                    if not (yield from self._local_call(self.city_helper_dd4f,0xD464,0xD467)):return
                    m[0x0032]=r.a
                    self._y(0x2A)
                    yield from self._external(0xD46C,0xEE07,0xD471,"far_call",40966)
                    if r.pc!=0xD471:return  # preserve nonlocal stack return
                    self._mark(0xD471)
                    self._rts();return

    def city_helper_d472(self):
        """$D472: city helper d472; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD472)
        self._y(0x00)
        self._x(m[0x0010])
        while True:  # natural loop $D477
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._mark(0xD479)
            if r.p&Z:
                pass
            else:
                self._compare(r.a,0x39)
                self._mark(0xD47D)
                if r.p&Z:
                    self._x(r.x-1)
                    m[(0x0162+r.x)&65535]=r.a
                    pass
                else:
                    self._compare(r.a,0x3A)
                    self._mark(0xD481)
                    if r.p&Z:
                        self._x(r.x-1)
                        m[(0x0162+r.x)&65535]=r.a
                        pass
                    else:
                        m[(0x0182+r.x)&65535]=r.a
                        pass
                    pass
                self._x(r.x+1)
                self._y(r.y+1)
                continue
            self._x(m[0x0010])
            self._a(m[WORLD_CURSOR])
            if not (yield from self._local_call(self.city_helper_dd56,0xD498,0xD49B)):return
            self._a(m[0x0472])
            if not (yield from self._local_call(self.city_helper_d4ed,0xD49E,0xD4A1)):return
            self._mark(0xD4A1)
            if not r.p&Z:
                m[0x0001]=r.a
                self._a(0x00)
                m[0x0002]=r.a
                m[0x0003]=r.a
                yield from self._external(0xD4C0,0xE9BA,0xD4C3,"call",None)
                if r.pc!=0xD4C3:return  # preserve nonlocal stack return
                self._a(m[0x0007])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xD4CA)
                if r.p&Z:
                    pass
                else:
                    self._flag(C,False)
                    self._add(0x76)
                    m[(0x018D+r.x)&65535]=r.a
                    pass
                self._a(m[0x0007])
                self._a(r.a & 0x0F)
                self._flag(C,False)
                self._add(0x76)
                m[(0x018E+r.x)&65535]=r.a
                self._a(0x1C)
                m[(0x018A+r.x)&65535]=r.a
                self._a(0x0D)
                m[(0x018B+r.x)&65535]=r.a
                self._a(0x2B)
                m[(0x018C+r.x)&65535]=r.a
                self._mark(0xD4EC)
                self._rts();return
            else:
                self._a(0x32)
                m[(0x018A+r.x)&65535]=r.a
                m[(0x018B+r.x)&65535]=r.a
                m[(0x018C+r.x)&65535]=r.a
                m[(0x018D+r.x)&65535]=r.a
                m[(0x018E+r.x)&65535]=r.a
                self._mark(0xD4B4)
                self._rts();return

    def city_helper_d4ed(self):
        """$D4ED: city helper d4ed; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD4ED)
        m[0x0002]=r.a
        r.a=self._shift(r.a,False,rotate=False)
        self._flag(C,False)
        self._add(0x04)
        self._y(r.a)
        self._a(m[0x0002])
        self._a(r.a & 0x01)
        self._mark(0xD4FA)
        if not r.p&Z:
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            self._mark(0xD507)
            self._rts();return
        else:
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x0F)
            self._mark(0xD500)
            self._rts();return

    def city_helper_d508(self):
        """$D508: city helper d508; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD508)
        m[0x0010]=r.a
        r.a=self._shift(r.a,False,rotate=False)
        self._flag(C,False)
        self._add(0x04)
        self._y(r.a)
        self._a(m[PHASE])
        self._compare(r.a,0x06)
        self._mark(0xD515)
        if r.p&Z:
            self._x(0xF0)
            self._a(m[0x0010])
            self._a(r.a & 0x01)
            self._mark(0xD534)
            if r.p&Z:
                pass
            else:
                self._x(0x0F)
                pass
            m[0x0010]=r.x
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & m[0x0010])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._mark(0xD542)
            self._rts();return
        else:
            self._x(0x0C)
            self._a(m[0x0010])
            self._a(r.a & 0x01)
            self._mark(0xD51E)
            if r.p&Z:
                pass
            else:
                self._x(0xC0)
                pass
            m[0x0010]=r.x
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a | m[0x0010])
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._mark(0xD52C)
            self._rts();return

    def city_helper_d543(self):
        """$D543: city helper d543; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD543)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xD548)
        if r.p&Z:
            self._mark(0xD562)
            self._rts();return
        else:
            self._a(0x00)
            m[0x0002]=r.a
            m[0x000A]=r.a
            m[0x000C]=r.a
            self._a(0x63)
            m[0x0000]=r.a
            self._a(0xD5)
            m[0x0001]=r.a
            self._mark(0xD55F)
            yield from self._external(0xD55F,0xF1AD,None,"tail")
            return

    def city_helper_d568(self):
        """$D568: city helper d568; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD568)
        self._a(0x80)
        m[0x0140]=r.a
        self._x(0x00)
        self._a(m[0x6F3F])
        self._mark(0xD572)
        if r.p&N:
            pass
        else:
            self._x(0x80)
            pass
        m[0x0150]=r.x
        self._a(m[0x6F3F])
        m[0x046D]=r.a
        self._a(m[0x6F41])
        m[0x046E]=r.a
        self._a(m[CITY])
        m[0x046F]=r.a
        self._mark(0xD58B)
        self._rts();return

    def city_helper_d58c(self):
        """$D58C: city helper d58c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD58C)
        m[0x0150]=r.a
        self._a(m[0x046D])
        m[0x6F3F]=r.a
        self._a(m[0x046E])
        m[0x6F41]=r.a
        if not (yield from self._local_call(self.update_cursor_repeat,0xD59B,0xD59E)):return
        self._a(m[0x046F])
        m[CITY]=r.a
        yield from self._external(0xD5A4,0xF2AF,0xD5A7,"call",None)
        if r.pc!=0xD5A7:return  # preserve nonlocal stack return
        self._y(0x80)
        m[0x0140]=r.y
        self._x(0x00)
        self._a(m[0x6F3F])
        self._mark(0xD5B1)
        if r.p&N:
            pass
        else:
            self._x(0x80)
            pass
        self._a(r.x)
        self._a(r.a | m[0x0150])
        m[0x0150]=r.a
        self._mark(0xD5BC)
        self._rts();return

    def city_helper_d5bd(self):
        """$D5BD: city helper d5bd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD5BD)
        self._a(m[0x046C])
        self._mark(0xD5C0)
        if not r.p&Z:
            self._a(m[0x046C])
            self._compare(r.a,0x01)
            self._mark(0xD619)
            if not r.p&Z:
                self._y(0x3D)
                yield from self._external(0xD62A,0xEE07,0xD62F,"far_call",41005)
                if r.pc!=0xD62F:return  # preserve nonlocal stack return
                self._a(m[0x046C])
                self._compare(r.a,0x40)
                self._mark(0xD634)
                if not r.p&Z:
                    pass
                else:
                    m[0x6F05]=self._nz(m[0x6F05]-1)
                    pass
                m[0x046C]=self._nz(m[0x046C]-1)
                self._mark(0xD63C)
                self._rts();return
            else:
                self._a(0x80)
                m[0x0013]=r.a
                self._y(0x3D)
                yield from self._external(0xD622,0xEE07,0xD627,"far_call",40996)
                if r.pc!=0xD627:return  # preserve nonlocal stack return
                self._mark(0xD627)
                self._rts();return
        else:
            self._a(0x3D)
            m[0x0010]=r.a
            self._a(0xD6)
            m[0x0011]=r.a
            self._a(0x00)
            m[0x0012]=r.a
            yield from self._external(0xD5D1,0xED1E,0xD5D4,"call",None)
            if r.pc!=0xD5D4:return  # preserve nonlocal stack return
            self._a(0x41)
            m[0x0010]=r.a
            self._a(0xD6)
            m[0x0011]=r.a
            self._a(0x45)
            m[0x0000]=r.a
            self._a(0xD6)
            m[0x0001]=r.a
            self._a(m[0x0012])
            yield from self._external(0xD5EB,0xEDF5,0xD5EE,"call",None)
            if r.pc!=0xD5EE:return  # preserve nonlocal stack return
            self._a(0x00)
            m[0x0013]=r.a
            if not (yield from self._local_call(self.text_request_readiness,0xD5F3,0xD5F6)):return
            self._mark(0xD5F6)
            if not r.p&C:
                self._mark(0xD606)
                self._rts();return
            else:
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xD5FC)
                if r.p&C:
                    self._a(m[0x0012])
                    self._mark(0xD60A)
                    if not r.p&Z:
                        self._a(0xFF)
                        m[0x0013]=r.a
                        self._mark(0xD606)
                        self._rts();return
                    else:
                        self._a(0x80)
                        m[0x046C]=r.a
                        self._y(0x3D)
                        yield from self._external(0xD62A,0xEE07,0xD62F,"far_call",41005)
                        if r.pc!=0xD62F:return  # preserve nonlocal stack return
                        self._a(m[0x046C])
                        self._compare(r.a,0x40)
                        self._mark(0xD634)
                        if not r.p&Z:
                            pass
                        else:
                            m[0x6F05]=self._nz(m[0x6F05]-1)
                            pass
                        m[0x046C]=self._nz(m[0x046C]-1)
                        self._mark(0xD63C)
                        self._rts();return
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xD5FF)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0xFF)
                        m[0x0013]=r.a
                        pass
                    self._mark(0xD606)
                    self._rts();return

    def city_helper_d64a(self):
        """$D64A: city helper d64a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD64A)
        self._a(m[0x0425])
        m[0x0013]=r.a
        self._a(0x4C)
        m[0x0010]=r.a
        self._a(0xD7)
        m[0x0011]=r.a
        self._a(0x00)
        m[0x0012]=r.a
        yield from self._external(0xD65F,0xED19,0xD662,"call",None)
        if r.pc!=0xD662:return  # preserve nonlocal stack return
        self._a(m[0x0012])
        self._compare(r.a,m[0x047B])
        self._mark(0xD668)
        if r.p&Z:
            pass
        else:
            self._mark(0xD66A)
            if not r.p&C:
                pass
            else:
                self._x(m[0x047B])
                self._a(m[0x0013])
                self._mark(0xD672)
                if r.p&Z:
                    pass
                else:
                    self._x(0x00)
                    pass
                m[0x0012]=r.x
                m[0x0425]=r.x
                pass
            pass
        self._a(0x58)
        m[0x0010]=r.a
        self._a(0xD7)
        m[0x0011]=r.a
        self._a(0x6E)
        m[0x0000]=r.a
        self._a(0xD7)
        m[0x0001]=r.a
        self._a(m[0x0012])
        m[0x047A]=r.a
        yield from self._external(0xD696,0xEDF5,0xD699,"call",None)
        if r.pc!=0xD699:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.text_request_readiness,0xD699,0xD69C)):return
        self._mark(0xD69C)
        if not r.p&C:
            self._mark(0xD6B9)
            self._rts();return
        else:
            self._a(m[0x047C])
            self._compare(r.a,0x10)
            self._mark(0xD6A3)
            if not r.p&Z:
                self._a(m[NEW_BUTTONS])
                r.a=self._shift(r.a,False,rotate=False)
                self._mark(0xD6AC)
                if r.p&C:
                    self._a(m[0x047C])
                    self._compare(r.a,0x0F)
                    self._mark(0xD6BF)
                    if r.p&Z:
                        self._y(m[0x0012])
                        self._a(m[0x047C])
                        self._compare(r.a,0x0F)
                        self._mark(0xD6FE)
                        if r.p&Z:
                            self._a(m[(0x0151+r.y)&65535])
                            m[0x0481]=r.a
                            self._a(m[CITY])
                            if not (yield from self._local_call(self.city_helper_dd4f,0xD736,0xD739)):return
                            self._compare(r.a,m[0x0481])
                            self._mark(0xD73C)
                            if r.p&Z:
                                self._a(0x81)
                                m[0x047C]=r.a
                                self._mark(0xD74B)
                                self._rts();return
                            else:
                                self._a(0x80)
                                m[0x047C]=r.a
                                return (yield from self.city_helper_d7a8())
                        else:
                            self._a(m[(0x0481+r.y)&65535])
                            self._compare(r.a,0xFF)
                            self._mark(0xD705)
                            if not r.p&Z:
                                self._a(0xFF)
                                m[(0x0481+r.y)&65535]=r.a
                                m[0x047C]=self._nz(m[0x047C]+1)
                                self._a(0x01)
                                if not (yield from self._local_call(self.city_helper_d773,0xD727,0xD72A)):return
                                pass
                            else:
                                self._a(m[0x047C])
                                self._mark(0xD70A)
                                if r.p&Z:
                                    pass
                                else:
                                    self._a(m[(0x0151+r.y)&65535])
                                    m[(0x0481+r.y)&65535]=r.a
                                    m[0x047C]=self._nz(m[0x047C]-1)
                                    self._a(0x3E)
                                    if not (yield from self._local_call(self.city_helper_d773,0xD717,0xD71A)):return
                                    pass
                                pass
                            self._mark(0xD6B9)
                            self._rts();return
                    else:
                        self._a(m[0x0012])
                        self._compare(r.a,m[0x047B])
                        self._mark(0xD6C7)
                        if not r.p&Z:
                            self._y(m[0x0012])
                            self._a(m[0x047C])
                            self._compare(r.a,0x0F)
                            self._mark(0xD6FE)
                            if r.p&Z:
                                self._a(m[(0x0151+r.y)&65535])
                                m[0x0481]=r.a
                                self._a(m[CITY])
                                if not (yield from self._local_call(self.city_helper_dd4f,0xD736,0xD739)):return
                                self._compare(r.a,m[0x0481])
                                self._mark(0xD73C)
                                if r.p&Z:
                                    self._a(0x81)
                                    m[0x047C]=r.a
                                    self._mark(0xD74B)
                                    self._rts();return
                                else:
                                    self._a(0x80)
                                    m[0x047C]=r.a
                                    return (yield from self.city_helper_d7a8())
                            else:
                                self._a(m[(0x0481+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xD705)
                                if not r.p&Z:
                                    self._a(0xFF)
                                    m[(0x0481+r.y)&65535]=r.a
                                    m[0x047C]=self._nz(m[0x047C]+1)
                                    self._a(0x01)
                                    if not (yield from self._local_call(self.city_helper_d773,0xD727,0xD72A)):return
                                    pass
                                else:
                                    self._a(m[0x047C])
                                    self._mark(0xD70A)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(m[(0x0151+r.y)&65535])
                                        m[(0x0481+r.y)&65535]=r.a
                                        m[0x047C]=self._nz(m[0x047C]-1)
                                        self._a(0x3E)
                                        if not (yield from self._local_call(self.city_helper_d773,0xD717,0xD71A)):return
                                        pass
                                    pass
                                self._mark(0xD6B9)
                                self._rts();return
                        else:
                            self._x(0x00)
                            self._y(0x00)
                            while True:  # natural loop $D6CD
                                self._a(m[(0x0481+r.y)&65535])
                                self._compare(r.a,0xFF)
                                self._mark(0xD6D2)
                                if r.p&Z:
                                    pass
                                else:
                                    m[(0x0481+r.x)&65535]=r.a
                                    m[0x0000]=r.x
                                    self._compare(r.y,m[0x0000])
                                    self._mark(0xD6DD)
                                    if r.p&Z:
                                        pass
                                    else:
                                        self._a(0xFF)
                                        m[(0x0481+r.y)&65535]=r.a
                                        pass
                                    self._x(r.x+1)
                                    pass
                                self._y(r.y+1)
                                self._compare(r.y,0x0A)
                                self._mark(0xD6E8)
                                if not r.p&C:
                                    continue
                                else:
                                    pass
                                self._compare(r.x,0x00)
                                self._mark(0xD6EC)
                                if r.p&Z:
                                    self._mark(0xD6B9)
                                    self._rts();return
                                else:
                                    self._a(0x81)
                                    m[0x047C]=r.a
                                    return (yield from self.city_helper_d7a8())
                else:
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xD6AF)
                    if not r.p&C:
                        self._mark(0xD6B9)
                        self._rts();return
                    else:
                        self._a(0x90)
                        m[0x047C]=r.a
                        return (yield from self.city_helper_d7a8())
            else:
                self._a(m[0x0012])
                self._compare(r.a,m[0x047B])
                self._mark(0xD7CB)
                if r.p&Z:
                    self._a(m[NEW_BUTTONS])
                    r.a=self._shift(r.a,False,rotate=False)
                    self._mark(0xD7DB)
                    if r.p&C:
                        self._a(0x80)
                        m[0x047C]=r.a
                        self._a(0x00)
                        m[0x0090]=r.a
                        m[0x008F]=r.a
                        self._a(0x03)
                        m[0x0061]=r.a
                        self._a(m[0x00C2])
                        self._a(0x00)
                        m[0x00B2]=r.a
                        self._a(0x05)
                        m[0x00B3]=r.a
                        self._a(0x09)
                        m[0x00B4]=r.a
                        self._mark(0xD804)
                        self._rts();return
                    else:
                        self._a(m[0x042C])
                        m[0x0001]=r.a
                        self._a(m[0x042D])
                        m[0x0002]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        yield from self._external(0xD919,0xE9BA,0xD91C,"call",None)
                        if r.pc!=0xD91C:return  # preserve nonlocal stack return
                        self._x(0x00)
                        self._y(0x01)
                        m[0x000A]=r.y
                        self._a(m[0x0009])
                        self._a(r.a & 0x0F)
                        if not (yield from self._local_call(self.city_helper_d96f,0xD928,0xD92B)):return
                        if not (yield from self._local_call(self.city_helper_d94e,0xD92B,0xD92E)):return
                        self._a(0x80)
                        m[(0x031E+r.x)&65535]=r.a
                        self._a(0x3A)
                        m[0x031C]=r.a
                        self._a(0x27)
                        m[0x031D]=r.a
                        self._a(0x01)
                        m[0x0303]=r.a
                        m[0x030C]=r.a
                        self._a(m[PPU_JOBS])
                        self._a(r.a | 0x01)
                        m[PPU_JOBS]=r.a
                        self._mark(0xD94D)
                        self._rts();return
                else:
                    self._a(m[NEW_BUTTONS])
                    self._a(r.a & 0xC0)
                    self._mark(0xD7D2)
                    if not r.p&Z:
                        self._a(m[CITY])
                        yield from self._external(0xD808,0xF2AF,0xD80B,"call",None)
                        if r.pc!=0xD80B:return  # preserve nonlocal stack return
                        self._a(m[0x0012])
                        self._flag(C,False)
                        self._add(0x11)
                        self._y(r.a)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        yield from self._external(0xD814,0xF2D7,0xD817,"call",None)
                        if r.pc!=0xD817:return  # preserve nonlocal stack return
                        self._y(0x08)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0002]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0003]=r.a
                        self._a(m[NEW_BUTTONS])
                        r.a=self._shift(r.a,True,rotate=False)
                        self._mark(0xD828)
                        if not r.p&C:
                            self._a(m[0x0003])
                            self._mark(0xD877)
                            if not r.p&Z:
                                if not (yield from self._local_call(self.city_helper_d987,0xD87E,0xD881)):return
                                self._a(m[0x0005])
                                self._mark(0xD884)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(m[0x042C])
                                    self._flag(C,True)
                                    self._add(0xAD,subtract=True)
                                    self._a(m[0x042D])
                                    self._add(0x26,subtract=True)
                                    self._mark(0xD891)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._y(0x08)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._flag(C,True)
                                        self._add(0x64,subtract=True)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._y(r.y+1)
                                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                        self._add(0x00,subtract=True)
                                        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                        self._a(m[0x042C])
                                        self._flag(C,False)
                                        self._add(0x64)
                                        m[0x042C]=r.a
                                        self._a(m[0x042D])
                                        self._add(0x00)
                                        m[0x042D]=r.a
                                        pass
                                    pass
                                pass
                            else:
                                self._a(m[0x0002])
                                self._mark(0xD87C)
                                if r.p&Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.city_helper_d987,0xD87E,0xD881)):return
                                    self._a(m[0x0005])
                                    self._mark(0xD884)
                                    if not r.p&Z:
                                        pass
                                    else:
                                        self._a(m[0x042C])
                                        self._flag(C,True)
                                        self._add(0xAD,subtract=True)
                                        self._a(m[0x042D])
                                        self._add(0x26,subtract=True)
                                        self._mark(0xD891)
                                        if r.p&C:
                                            pass
                                        else:
                                            self._y(0x08)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._flag(C,True)
                                            self._add(0x64,subtract=True)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._y(r.y+1)
                                            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                            self._add(0x00,subtract=True)
                                            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                            self._a(m[0x042C])
                                            self._flag(C,False)
                                            self._add(0x64)
                                            m[0x042C]=r.a
                                            self._a(m[0x042D])
                                            self._add(0x00)
                                            m[0x042D]=r.a
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        else:
                            self._a(0xE7)
                            self._flag(C,True)
                            self._add(m[0x0002],subtract=True)
                            self._a(0x03)
                            self._add(m[0x0003],subtract=True)
                            self._mark(0xD835)
                            if not r.p&C:
                                pass
                            else:
                                if not (yield from self._local_call(self.city_helper_d987,0xD837,0xD83A)):return
                                self._x(0x64)
                                self._a(m[0x042D])
                                self._mark(0xD83F)
                                if not r.p&Z:
                                    pass
                                else:
                                    self._a(m[0x042C])
                                    self._compare(r.a,0x64)
                                    self._mark(0xD846)
                                    if r.p&C:
                                        pass
                                    else:
                                        self._x(m[0x042C])
                                        pass
                                    pass
                                m[0x0002]=r.x
                                self._y(0x08)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._flag(C,False)
                                self._add(m[0x0002])
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._y(r.y+1)
                                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                                self._add(0x00)
                                m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
                                self._a(m[0x042C])
                                self._flag(C,True)
                                self._add(m[0x0002],subtract=True)
                                m[0x042C]=r.a
                                self._a(m[0x042D])
                                self._add(0x00,subtract=True)
                                m[0x042D]=r.a
                                pass
                            pass
                        self._y(0x08)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0003]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        m[0x0002]=r.a
                        self._a(m[0x0003])
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        yield from self._external(0xD8CC,0xE9BA,0xD8CF,"call",None)
                        if r.pc!=0xD8CF:return  # preserve nonlocal stack return
                        self._y(0x01)
                        m[0x000A]=r.y
                        self._x(0x00)
                        if not (yield from self._local_call(self.city_helper_d94e,0xD8D6,0xD8D9)):return
                        self._a(0x80)
                        m[(0x031E+r.x)&65535]=r.a
                        self._a(0x40)
                        m[0x0000]=r.a
                        self._a(0x00)
                        m[0x0001]=r.a
                        m[0x0002]=r.a
                        self._a(m[0x0012])
                        m[0x0003]=r.a
                        yield from self._external(0xD8F1,0xEBE9,0xD8F4,"call",None)
                        if r.pc!=0xD8F4:return  # preserve nonlocal stack return
                        self._a(m[0x0006])
                        self._flag(C,False)
                        self._add(0xBB)
                        m[0x031C]=r.a
                        self._a(m[0x0007])
                        self._add(0x24)
                        m[0x031D]=r.a
                        pass
                    else:
                        self._a(m[0x042C])
                        m[0x0001]=r.a
                        self._a(m[0x042D])
                        m[0x0002]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        yield from self._external(0xD919,0xE9BA,0xD91C,"call",None)
                        if r.pc!=0xD91C:return  # preserve nonlocal stack return
                        self._x(0x00)
                        self._y(0x01)
                        m[0x000A]=r.y
                        self._a(m[0x0009])
                        self._a(r.a & 0x0F)
                        if not (yield from self._local_call(self.city_helper_d96f,0xD928,0xD92B)):return
                        if not (yield from self._local_call(self.city_helper_d94e,0xD92B,0xD92E)):return
                        self._a(0x80)
                        m[(0x031E+r.x)&65535]=r.a
                        self._a(0x3A)
                        m[0x031C]=r.a
                        self._a(0x27)
                        m[0x031D]=r.a
                        pass
                    self._a(0x01)
                    m[0x0303]=r.a
                    m[0x030C]=r.a
                    self._a(m[PPU_JOBS])
                    self._a(r.a | 0x01)
                    m[PPU_JOBS]=r.a
                    self._mark(0xD94D)
                    self._rts();return

    def city_helper_d773(self):
        """$D773: city helper d773; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD773)
        m[0x031E]=r.a
        self._a(0x80)
        m[0x031F]=r.a
        self._a(0x40)
        m[0x0000]=r.a
        self._a(0x00)
        m[0x0001]=r.a
        m[0x0002]=r.a
        m[0x0003]=r.y
        yield from self._external(0xD78B,0xEBE9,0xD78E,"call",None)
        if r.pc!=0xD78E:return  # preserve nonlocal stack return
        self._a(0xA2)
        self._flag(C,False)
        self._add(m[0x0006])
        m[0x031C]=r.a
        self._a(0x24)
        self._add(m[0x0007])
        m[0x031D]=r.a
        self._a(m[PPU_JOBS])
        self._a(r.a | 0x01)
        m[PPU_JOBS]=r.a
        self._mark(0xD7A7)
        self._rts();return

    def city_helper_d7a8(self):
        """$D7A8: city helper d7a8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD7A8)
        self._a(0x00)
        m[0x008F]=r.a
        self._a(0x03)
        m[0x0061]=r.a
        self._a(m[0x00C2])
        self._a(0x00)
        m[0x00B2]=r.a
        self._a(0x05)
        m[0x00B3]=r.a
        self._a(0x09)
        m[0x00B4]=r.a
        self._mark(0xD7C4)
        self._rts();return

    def city_helper_d94e(self):
        """$D94E: city helper d94e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $D94E
            self._mark(0xD94E)
            self._a(m[(0x0007+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            if not (yield from self._local_call(self.city_helper_d96f,0xD955,0xD958)):return
            self._compare(r.y,0x00)
            self._mark(0xD95A)
            if not r.p&Z:
                pass
            else:
                self._a(0x76)
                m[0x000A]=r.a
                pass
            self._a(m[(0x0007+r.y)&65535])
            self._a(r.a & 0x0F)
            if not (yield from self._local_call(self.city_helper_d96f,0xD966,0xD969)):return
            self._y(r.y-1)
            self._compare(r.y,0xFF)
            self._mark(0xD96C)
            if not r.p&Z:
                continue
            else:
                pass
            self._mark(0xD96E)
            self._rts();return

    def city_helper_d96f(self):
        """$D96F: city helper d96f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD96F)
        if r.p&Z:
            self._a(m[0x000A])
            m[(0x031E+r.x)&65535]=r.a
            pass
        else:
            self._flag(C,False)
            self._add(0x76)
            m[(0x031E+r.x)&65535]=r.a
            self._a(0x76)
            m[0x000A]=r.a
            pass
        self._x(r.x+1)
        self._mark(0xD986)
        self._rts();return

    def city_helper_d987(self):
        """$D987: city helper d987; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD987)
        self._a(m[0x0000])
        m[0x0010]=r.a
        self._a(m[0x0001])
        m[0x0011]=r.a
        self._a(m[0x0002])
        m[0x0001]=r.a
        self._a(m[0x0003])
        m[0x0002]=r.a
        self._a(0x64)
        m[0x0003]=r.a
        self._a(0x00)
        m[0x0004]=r.a
        yield from self._external(0xD9A9,0xEA7C,0xD9AC,"call",None)
        if r.pc!=0xD9AC:return  # preserve nonlocal stack return
        self._a(m[0x0005])
        self._mark(0xD9AF)
        if r.p&Z:
            pass
        else:
            self._flag(C,False)
            self._add(m[0x042C])
            m[0x042C]=r.a
            self._a(0x00)
            self._add(m[0x042D])
            m[0x042D]=r.a
            self._a(m[0x042C])
            self._flag(C,True)
            self._add(0x10,subtract=True)
            m[0x0006]=r.a
            self._a(m[0x042D])
            self._add(0x27,subtract=True)
            self._mark(0xD9CE)
            if not r.p&C:
                pass
            else:
                self._a(0x10)
                m[0x042C]=r.a
                self._a(0x27)
                m[0x042D]=r.a
                self._a(m[0x0005])
                self._flag(C,True)
                self._add(m[0x0006],subtract=True)
                m[0x0005]=r.a
                pass
            pass
        self._a(m[0x0010])
        m[0x0000]=r.a
        self._a(m[0x0011])
        m[0x0001]=r.a
        self._y(0x08)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0005],subtract=True)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(0x00,subtract=True)
        m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
        self._mark(0xDA01)
        self._rts();return

    def city_helper_da02(self):
        """$DA02: city helper da02; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA02)
        self._a(0x03)
        return (yield from self.city_helper_da04())

    def city_helper_da04(self):
        """$DA04: city helper da04; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDA04)
        m[0x001F]=r.a
        self._a(m[0x048E])
        m[0x0014]=r.a
        self._a(m[0x048F])
        m[0x0015]=r.a
        self._a(m[NEW_BUTTONS])
        r.a=self._shift(r.a,True,rotate=False)
        self._mark(0xDA17)
        if not r.p&C:
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xDA25)
            if not r.p&C:
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xDA36)
                if not r.p&C:
                    r.a=self._shift(r.a,True,rotate=False)
                    self._mark(0xDA52)
                    if not r.p&C:
                        pass
                    else:
                        if not (yield from self._local_call(self.city_helper_db09,0xDA54,0xDA57)):return
                        self._a(m[0x048E])
                        self._flag(C,False)
                        self._add(m[0x0000])
                        m[0x048E]=r.a
                        self._a(m[0x048F])
                        self._add(m[0x0001])
                        m[0x048F]=r.a
                        self._a(m[0x048E])
                        m[0x0000]=r.a
                        self._a(m[0x048F])
                        m[0x0001]=r.a
                        self._a(m[0x0490])
                        self._flag(C,True)
                        self._add(m[0x0000],subtract=True)
                        self._a(m[0x0491])
                        self._add(m[0x0001],subtract=True)
                        self._mark(0xDA83)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x0014])
                            m[0x048E]=r.a
                            self._a(m[0x0015])
                            m[0x048F]=r.a
                            pass
                        pass
                    pass
                else:
                    if not (yield from self._local_call(self.city_helper_db09,0xDA38,0xDA3B)):return
                    self._a(m[0x048E])
                    self._flag(C,True)
                    self._add(m[0x0000],subtract=True)
                    m[0x048E]=r.a
                    self._a(m[0x048F])
                    self._add(m[0x0001],subtract=True)
                    m[0x048F]=r.a
                    self._a(m[0x048E])
                    m[0x0000]=r.a
                    self._a(m[0x048F])
                    m[0x0001]=r.a
                    self._a(m[0x0490])
                    self._flag(C,True)
                    self._add(m[0x0000],subtract=True)
                    self._a(m[0x0491])
                    self._add(m[0x0001],subtract=True)
                    self._mark(0xDA83)
                    if r.p&C:
                        pass
                    else:
                        self._a(m[0x0014])
                        m[0x048E]=r.a
                        self._a(m[0x0015])
                        m[0x048F]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x048B])
                self._compare(r.a,m[0x001F])
                self._mark(0xDA2D)
                if r.p&Z:
                    pass
                else:
                    m[0x048B]=self._nz(m[0x048B]+1)
                    pass
                pass
            pass
        else:
            self._a(m[0x048B])
            self._mark(0xDA1C)
            if r.p&Z:
                pass
            else:
                m[0x048B]=self._nz(m[0x048B]-1)
                pass
            pass
        if not (yield from self._local_call(self.text_request_readiness,0xDA91,0xDA94)):return
        self._mark(0xDA94)
        if not r.p&C:
            pass
        else:
            self._a(m[NEW_BUTTONS])
            self._a(r.a & 0x03)
            m[0x0013]=r.a
            self._a(m[0x048E])
            m[0x0001]=r.a
            self._a(m[0x048F])
            m[0x0002]=r.a
            self._a(0x00)
            m[0x0003]=r.a
            yield from self._external(0xDAAF,0xE9BA,0xDAB2,"call",None)
            if r.pc!=0xDAB2:return  # preserve nonlocal stack return
            self._a(m[0x0007])
            m[0x048C]=r.a
            self._a(m[0x0008])
            m[0x048D]=r.a
            self._a(0x03)
            self._flag(C,True)
            self._add(m[0x048B],subtract=True)
            m[0x0011]=r.a
            self._a(0x01)
            m[0x0010]=r.a
            self._y(0x02)
            self._x(0x00)
            while True:  # natural loop $DAD0
                self._a(m[(0x048B+r.y)&65535])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                if not (yield from self._local_call(self.city_helper_db35,0xDAD7,0xDADA)):return
                self._compare(r.y,0x01)
                self._mark(0xDADC)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x76)
                    m[0x0010]=r.a
                    pass
                self._a(m[(0x048B+r.y)&65535])
                self._a(r.a & 0x0F)
                if not (yield from self._local_call(self.city_helper_db35,0xDAE8,0xDAEB)):return
                self._y(r.y-1)
                self._compare(r.y,0x00)
                self._mark(0xDAEE)
                if not r.p&Z:
                    continue
                else:
                    pass
                self._a(0x80)
                m[(0x031E+r.x)&65535]=r.a
                self._a(0x01)
                m[0x0303]=r.a
                m[0x030C]=r.a
                m[0x046C]=self._nz(m[0x046C]+1)
                self._a(m[PPU_JOBS])
                self._a(r.a | 0x01)
                m[PPU_JOBS]=r.a
                self._mark(0xDB08)
                self._rts();return
        self._mark(0xDB08)
        self._rts();return

    def city_helper_db09(self):
        """$DB09: city helper db09; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB09)
        self._a(0x00)
        m[0x0001]=r.a
        self._a(m[0x048B])
        self._mark(0xDB11)
        if not r.p&Z:
            self._compare(r.a,0x01)
            self._mark(0xDB1A)
            if not r.p&Z:
                self._compare(r.a,0x02)
                self._mark(0xDB23)
                if not r.p&Z:
                    self._a(0x03)
                    m[0x0001]=r.a
                    self._a(0xE8)
                    pass
                else:
                    self._a(0x64)
                    pass
                pass
            else:
                self._a(0x0A)
                pass
            pass
        else:
            self._a(0x01)
            pass
        m[0x0000]=r.a
        self._mark(0xDB34)
        self._rts();return

    def city_helper_db35(self):
        """$DB35: city helper db35; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB35)
        if r.p&Z:
            self._a(m[0x0013])
            self._mark(0xDB48)
            if not r.p&Z:
                pass
            else:
                self._compare(r.x,m[0x0011])
                self._mark(0xDB4D)
                if not r.p&C:
                    pass
                else:
                    self._a(0x76)
                    m[0x0010]=r.a
                    pass
                pass
            self._a(m[0x0010])
            m[(0x031E+r.x)&65535]=r.a
            pass
        else:
            self._flag(C,False)
            self._add(0x76)
            m[(0x031E+r.x)&65535]=r.a
            self._a(0x76)
            m[0x0010]=r.a
            pass
        self._a(m[0x0013])
        self._mark(0xDB5D)
        if not r.p&Z:
            pass
        else:
            self._compare(r.x,m[0x0011])
            self._mark(0xDB62)
            if not r.p&Z:
                pass
            else:
                self._a(m[0x046C])
                self._a(r.a & 0x08)
                self._mark(0xDB69)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x01)
                    m[(0x031E+r.x)&65535]=r.a
                    pass
                pass
            pass
        self._x(r.x+1)
        self._mark(0xDB71)
        self._rts();return

    def city_helper_db72(self):
        """$DB72: city helper db72; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB72)
        self._a(m[0x0006])
        m[0x0000]=r.a
        self._a(m[0x0007])
        m[0x0001]=r.a
        self._a(m[0x0008])
        m[0x0002]=r.a
        self._mark(0xDB84)
        yield from self._external(0xDB84,0xEAA5,None,"tail")
        return

    def city_helper_db87(self):
        """$DB87: city helper db87; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB87)
        self._a(0x00)
        m[0x048B]=r.a
        m[0x048C]=r.a
        m[0x048D]=r.a
        m[0x048E]=r.a
        m[0x048F]=r.a
        self._mark(0xDB98)
        self._rts();return

    def city_helper_db99(self):
        """$DB99: city helper db99; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDB99)
        self._a(0x00)
        m[0x0011]=r.a
        self._a(m[CITY])
        yield from self._external(0xDBA1,0xF2AF,0xDBA4,"call",None)
        if r.pc!=0xDBA4:return  # preserve nonlocal stack return
        if not (yield from self._local_call(self.city_helper_dc6b,0xDBA4,0xDBA7)):return
        self._compare(r.x,0x0A)
        self._mark(0xDBA9)
        if not r.p&Z:
            pass
        else:
            self._a(0x80)
            m[0x0011]=r.a
            pass
        yield from self._external(0xDBB0,0xE856,0xDBB3,"call",None)
        if r.pc!=0xDBB3:return  # preserve nonlocal stack return
        m[0x0010]=r.a
        self._a(m[0x0481])
        yield from self._external(0xDBB9,0xF2D7,0xDBBC,"call",None)
        if r.pc!=0xDBBC:return  # preserve nonlocal stack return
        self._y(0x04)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x29)
        self._mark(0xDBC2)
        if not r.p&C:
            pass
        else:
            self._x(0x18)
            self._compare(r.a,0x51)
            self._mark(0xDBC8)
            if not r.p&C:
                pass
            else:
                self._x(0x30)
                pass
            pass
        self._y(0x02)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._compare(r.a,0x29)
        self._mark(0xDBD2)
        if not r.p&C:
            pass
        else:
            self._compare(r.a,0x51)
            self._mark(0xDBD6)
            if r.p&C:
                self._a(r.x)
                self._flag(C,False)
                self._add(0x10)
                self._x(r.a)
                pass
            else:
                self._a(r.x)
                self._flag(C,False)
                self._add(0x08)
                self._x(r.a)
                pass
            pass
        while True:  # natural loop $DBE5
            self._a(r.x)
            self._flag(C,False)
            self._add(m[0x0010])
            self._y(r.a)
            self._a(m[(0xDC23+r.y)&65535])
            m[WORLD_CURSOR]=r.a
            self._a(m[0x0011])
            self._mark(0xDBF4)
            if r.p&Z:
                self._a(m[WORLD_CURSOR])
                self._compare(r.a,0x05)
                self._mark(0xDC0C)
                if not r.p&C:
                    self._mark(0xDC15)
                    self._rts();return
                else:
                    self._compare(r.a,0x08)
                    self._mark(0xDC10)
                    if r.p&Z:
                        self._mark(0xDC15)
                        self._rts();return
                    else:
                        self._y(0x39)
                        yield from self._external(0xDC18,0xEE07,0xDC1D,"far_call",40987)
                        if r.pc!=0xDC1D:return  # preserve nonlocal stack return
                        self._a(m[0x0011])
                        self._mark(0xDC20)
                        if r.p&N:
                            yield from self._external(0xDBFE,0xE856,0xDC01,"call",None)
                            if r.pc!=0xDC01:return  # preserve nonlocal stack return
                            m[0x0010]=r.a
                            continue
                        else:
                            self._mark(0xDC22)
                            self._rts();return
            else:
                self._a(m[WORLD_CURSOR])
                self._compare(r.a,0x05)
                self._mark(0xDBFB)
                if r.p&C:
                    yield from self._external(0xDBFE,0xE856,0xDC01,"call",None)
                    if r.pc!=0xDC01:return  # preserve nonlocal stack return
                    m[0x0010]=r.a
                    continue
                else:
                    self._mark(0xDBFD)
                    self._rts();return

    def city_helper_dc6b(self):
        """$DC6B: city helper dc6b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC6B)
        self._y(0x11)
        self._x(0x00)
        while True:  # natural loop $DC6F
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._compare(r.a,0xFF)
            self._mark(0xDC73)
            if r.p&Z:
                pass
            else:
                self._x(r.x+1)
                pass
            self._y(r.y+1)
            self._compare(r.y,0x1B)
            self._mark(0xDC79)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xDC7B)
            self._rts();return

    def city_helper_dc7c(self):
        """$DC7C: city helper dc7c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDC7C)
        self._y(0x11)
        self._a(0xFF)
        while True:  # natural loop $DC80
            m[(0x0140+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x1B)
            self._mark(0xDC86)
            if not r.p&C:
                continue
            else:
                pass
            self._a(m[CITY])
            yield from self._external(0xDC8B,0xF2AF,0xDC8E,"call",None)
            if r.pc!=0xDC8E:return  # preserve nonlocal stack return
            self._a(m[0x0000])
            m[0x0010]=r.a
            self._a(m[0x0001])
            m[0x0011]=r.a
            self._x(0x11)
            m[0x0012]=r.x
            while True:  # natural loop $DC9F
                self._y(m[0x0012])
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535])
                m[0x000A]=r.a
                yield from self._external(0xDCA7,0xF387,0xDCAA,"call",None)
                if r.pc!=0xDCAA:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                m[0x000B]=r.a
                self._a(m[0x000A])
                yield from self._external(0xDCB4,0xF2D7,0xDCB7,"call",None)
                if r.pc!=0xDCB7:return  # preserve nonlocal stack return
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._compare(r.a,m[0x000B])
                self._mark(0xDCBC)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x000A])
                    m[(0x0140+r.x)&65535]=r.a
                    self._x(r.x+1)
                    pass
                m[0x0012]=self._nz(m[0x0012]+1)
                self._a(m[0x0012])
                self._compare(r.a,0x1B)
                self._mark(0xDCCD)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xDCCF)
                self._rts();return

    def city_helper_dcd0(self):
        """$DCD0: city helper dcd0; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDCD0)
        self._a(m[WORLD_CURSOR])
        self._compare(r.a,0x06)
        self._mark(0xDCD5)
        if not r.p&C:
            self._a(0x25)
            m[0x0010]=r.a
            self._a(0xDD)
            m[0x0011]=r.a
            self._a(0x3D)
            m[0x0013]=r.a
            self._a(0xDD)
            m[0x0014]=r.a
            pass
        else:
            self._compare(r.a,0x09)
            self._mark(0xDCD9)
            if not r.p&C:
                self._a(0x2D)
                m[0x0010]=r.a
                self._a(0xDD)
                m[0x0011]=r.a
                self._a(0x41)
                m[0x0013]=r.a
                self._a(0xDD)
                m[0x0014]=r.a
                pass
            else:
                self._a(0x35)
                m[0x0010]=r.a
                self._a(0xDD)
                m[0x0011]=r.a
                self._a(0x47)
                m[0x0013]=r.a
                self._a(0xDD)
                m[0x0014]=r.a
                pass
            pass
        self._a(0x00)
        m[0x0012]=r.a
        self._mark(0xDD22)
        yield from self._external(0xDD22,0xED28,None,"tail")
        return

    def city_helper_dd4f(self):
        """$DD4F: city helper dd4f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD4F)
        yield from self._external(0xDD4F,0xF2AF,0xDD52,"call",None)
        if r.pc!=0xDD52:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        return (yield from self.city_helper_dd56())

    def city_helper_dd56(self):
        """$DD56: city helper dd56; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD56)
        yield from self._external(0xDD56,0xF368,0xDD59,"call",None)
        if r.pc!=0xDD59:return  # preserve nonlocal stack return
        self._y(0x00)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._mark(0xDD5D)
        self._rts();return

    def city_helper_dd5e(self):
        """$DD5E: city helper dd5e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD5E)
        m[0x0000]=r.a
        self._x(0x00)
        self._a(0xA7)
        m[0x000A]=r.a
        self._y(0x39)
        yield from self._external(0xDD6A,0xEE07,0xDD6F,"far_call",40960)
        if r.pc!=0xDD6F:return  # preserve nonlocal stack return
        self._mark(0xDD6F)
        self._rts();return

    def city_helper_dd70(self):
        """$DD70: city helper dd70; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD70)
        self._a(0x00)
        m[0x0424]=r.a
        m[0x0425]=r.a
        self._mark(0xDD78)
        self._rts();return

    def city_helper_dd79(self):
        """$DD79: city helper dd79; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDD79)
        self._y(0x30)
        yield from self._external(0xDD7B,0xF25F,0xDD7E,"call",None)
        if r.pc!=0xDD7E:return  # preserve nonlocal stack return
        self._a(m[WORLD_CURSOR])
        self._compare(r.a,m[CITY])
        self._mark(0xDD84)
        if r.p&Z:
            self._a(0x80)
            m[CITY]=r.a
            self._mark(0xDD9F)
            self._rts();return
        else:
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            while True:  # natural loop $DD8A
                self._a(m[(0x9D72+r.y)&65535])
                self._compare(r.a,0xFF)
                self._mark(0xDD8F)
                if r.p&Z:
                    self._a(0x80)
                    m[CITY]=r.a
                    self._mark(0xDD9F)
                    self._rts();return
                else:
                    self._compare(r.a,m[CITY])
                    self._mark(0xDD94)
                    if r.p&Z:
                        yield from self._external(0xDDA0,0xF2AF,0xDDA3,"call",None)
                        if r.pc!=0xDDA3:return  # preserve nonlocal stack return
                        self._y(0x00)
                        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                        self._a(r.a & 0x07)
                        m[0x0010]=r.a
                        self._mark(0xDDAC)
                        self._rts();return
                    else:
                        self._y(r.y+1)
                        continue

    def text_request_readiness(self):
        """$DDAD: text request readiness; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDDAD)
        self._a(m[0x0304])
        self._compare(r.a,0xFF)
        self._mark(0xDDB2)
        if not r.p&Z:
            self._flag(C,False)
            self._mark(0xDDBE)
            self._rts();return
        else:
            self._a(m[0x0300])
            self._compare(r.a,0xFF)
            self._mark(0xDDB9)
            if not r.p&Z:
                self._flag(C,False)
                self._mark(0xDDBE)
                self._rts();return
            else:
                self._flag(C,True)
                self._mark(0xDDBC)
                self._rts();return

    def city_helper_ddbf(self):
        """$DDBF: city helper ddbf; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDDBF)
        self._x(0x00)
        m[0x0011]=r.x
        while True:  # natural loop $DDC4
            self._a(r.x)
            yield from self._external(0xDDC5,0xF2AF,0xDDC8,"call",None)
            if r.pc!=0xDDC8:return  # preserve nonlocal stack return
            self._y(0x00)
            self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
            self._a(r.a & 0x07)
            self._compare(r.a,m[0x0010])
            self._mark(0xDDD1)
            if not r.p&Z:
                pass
            else:
                m[0x0011]=self._nz(m[0x0011]+1)
                pass
            self._x(r.x+1)
            self._compare(r.x,0x1E)
            self._mark(0xDDD9)
            if not r.p&C:
                continue
            else:
                pass
            self._mark(0xDDDB)
            self._rts();return

    def city_helper_dddc(self):
        """$DDDC: city helper dddc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDDDC)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(0x10,subtract=True)
        self._y(r.y+1)
        self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
        self._add(0x27,subtract=True)
        self._mark(0xDDE6)
        if not r.p&C:
            pass
        else:
            self._a(0x27)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            self._y(r.y-1)
            self._a(0x0F)
            m[((m[0x00]|m[0x01]<<8)+r.y)&65535]=r.a
            pass
        self._mark(0xDDF1)
        self._rts();return

    def world_selection_portrait(self):
        """$DDF2: world selection portrait; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDDF2)
        self._a(0x00)
        m[0x04E4]=r.a
        self._a(m[0x0318])
        m[0x0000]=r.a
        self._a(m[0x0083])
        self._a(r.a & 0xF0)
        m[0x0318]=r.a
        self._mark(0xDE05)
        if r.p&Z:
            self._a(0x00)
            m[0x0319]=r.a
            self._mark(0xDE28)
            self._rts();return
        else:
            self._compare(r.a,m[0x0000])
            self._mark(0xDE0A)
            if not r.p&Z:
                self._a(0x00)
                m[0x0319]=r.a
                self._a(m[0x0083])
                self._mark(0xDE31)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0xF8)
                    self._mark(0xDE38)
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
                self._mark(0xDE46)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F3F])
                    self._compare(r.x,0x10)
                    self._mark(0xDE4D)
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
                self._mark(0xDE5B)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x94)
                    self._mark(0xDE62)
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
                self._mark(0xDE70)
                if not r.p&N:
                    pass
                else:
                    self._x(m[0x6F41])
                    self._compare(r.x,0x10)
                    self._mark(0xDE77)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(0x08,subtract=True)
                        m[0x6F41]=r.a
                        pass
                    pass
                self._mark(0xDE82)
                self._rts();return
            else:
                m[0x0319]=self._nz(m[0x0319]+1)
                self._a(m[0x0319])
                self._compare(r.a,0x0F)
                self._mark(0xDE14)
                if not r.p&C:
                    self._mark(0xDE22)
                    self._rts();return
                else:
                    self._a(0x0F)
                    m[0x0319]=r.a
                    self._a(m[0x005E])
                    self._a(r.a & 0x03)
                    self._mark(0xDE20)
                    if r.p&Z:
                        self._a(m[0x0083])
                        self._mark(0xDE31)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0xF8)
                            self._mark(0xDE38)
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
                        self._mark(0xDE46)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F3F])
                            self._compare(r.x,0x10)
                            self._mark(0xDE4D)
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
                        self._mark(0xDE5B)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x94)
                            self._mark(0xDE62)
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
                        self._mark(0xDE70)
                        if not r.p&N:
                            pass
                        else:
                            self._x(m[0x6F41])
                            self._compare(r.x,0x10)
                            self._mark(0xDE77)
                            if not r.p&C:
                                pass
                            else:
                                self._a(m[0x6F41])
                                self._flag(C,True)
                                self._add(0x08,subtract=True)
                                m[0x6F41]=r.a
                                pass
                            pass
                        self._mark(0xDE82)
                        self._rts();return
                    else:
                        self._mark(0xDE22)
                        self._rts();return

    def update_cursor_repeat(self):
        """$DE83: update cursor repeat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDE83)
        self._a(m[0x008F])
        self._mark(0xDE86)
        if not r.p&Z:
            self._mark(0xDEB0)
            self._rts();return
        else:
            self._a(m[0x04E4])
            self._mark(0xDE8B)
            if not r.p&Z:
                self._mark(0xDEB0)
                self._rts();return
            else:
                self._a(m[0x04A0])
                self._mark(0xDE90)
                if not r.p&Z:
                    self._mark(0xDEB0)
                    self._rts();return
                else:
                    self._a(m[0x6F41])
                    m[0x000A]=r.a
                    self._a(m[0x6F3F])
                    m[0x000C]=r.a
                    self._a(0xB1)
                    m[0x0000]=r.a
                    self._a(0xDE)
                    m[0x0001]=r.a
                    self._a(0x00)
                    m[0x0002]=r.a
                    self._mark(0xDEAD)
                    yield from self._external(0xDEAD,0xF1AD,None,"tail")
                    return

    def city_at_cursor(self):
        """$DEBA: city at cursor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDEBA)
        self._a(m[0x6F3F])
        self._compare(r.a,0x20)
        self._mark(0xDEBF)
        if r.p&C:
            self._y(0x1E)
            while True:  # natural loop $DECD
                self._a(m[0x6F3F])
                self._flag(C,True)
                self._add(m[(0xDEE9+r.y)&65535],subtract=True)
                self._compare(r.a,0x10)
                self._mark(0xDED6)
                if r.p&C:
                    self._y(r.y-1)
                    self._mark(0xDEE4)
                    if not r.p&N:
                        continue
                    else:
                        self._y(0xFF)
                        pass
                    pass
                else:
                    self._a(m[0x6F41])
                    self._flag(C,True)
                    self._add(m[(0xDF07+r.y)&65535],subtract=True)
                    self._compare(r.a,0x10)
                    self._mark(0xDEE1)
                    if not r.p&C:
                        pass
                    else:
                        self._y(r.y-1)
                        self._mark(0xDEE4)
                        if not r.p&N:
                            continue
                        else:
                            self._y(0xFF)
                            pass
                        pass
                    pass
                self._mark(0xDEE8)
                self._rts();return
        else:
            self._a(m[0x6F41])
            self._compare(r.a,0x20)
            self._mark(0xDEC6)
            if r.p&C:
                self._y(0x1E)
                while True:  # natural loop $DECD
                    self._a(m[0x6F3F])
                    self._flag(C,True)
                    self._add(m[(0xDEE9+r.y)&65535],subtract=True)
                    self._compare(r.a,0x10)
                    self._mark(0xDED6)
                    if r.p&C:
                        self._y(r.y-1)
                        self._mark(0xDEE4)
                        if not r.p&N:
                            continue
                        else:
                            self._y(0xFF)
                            pass
                        pass
                    else:
                        self._a(m[0x6F41])
                        self._flag(C,True)
                        self._add(m[(0xDF07+r.y)&65535],subtract=True)
                        self._compare(r.a,0x10)
                        self._mark(0xDEE1)
                        if not r.p&C:
                            pass
                        else:
                            self._y(r.y-1)
                            self._mark(0xDEE4)
                            if not r.p&N:
                                continue
                            else:
                                self._y(0xFF)
                                pass
                            pass
                        pass
                    self._mark(0xDEE8)
                    self._rts();return
            else:
                self._y(0xFF)
                self._mark(0xDECA)
                self._rts();return

    def city_callback_preparation(self):
        """$DF35: city callback preparation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF35)
        self._a(m[0x0420])
        m[0x000E]=r.a
        self._a(0x1D)
        m[0x000F]=r.a
        self._a(m[0x008F])
        self._mark(0xDF43)
        if not r.p&Z:
            pass
        else:
            self._x(m[0x007C])
            while True:  # natural loop $DF48
                if not (yield from self._local_call(self.city_helper_df62,0xDF48,0xDF4B)):return
                m[0x000F]=self._nz(m[0x000F]-1)
                self._mark(0xDF4E)
                if not r.p&N:
                    continue
                else:
                    pass
                m[0x007C]=r.x
                self._a(0x00)
                m[0x04E0]=r.a
                m[0x04E1]=r.a
                m[0x04E2]=r.a
                m[0x04E3]=r.a
                self._mark(0xDF61)
                self._rts();return
        self._a(0x00)
        m[0x04E0]=r.a
        m[0x04E1]=r.a
        m[0x04E2]=r.a
        m[0x04E3]=r.a
        self._mark(0xDF61)
        self._rts();return

    def city_helper_df62(self):
        """$DF62: city helper df62; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xDF62)
        self._a(m[0x000F])
        self._a(r.a & 0x07)
        self._y(r.a)
        self._a(m[(0xDFEE+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[0x000F])
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        r.a=self._shift(r.a,False,rotate=False)
        self._y(r.a)
        self._a(m[(0x04E0+r.y)&65535])
        self._a(r.a & m[0x0000])
        self._mark(0xDF7B)
        if r.p&Z:
            self._y(m[0x000F])
            self._a(m[(0xDFD0+r.y)&65535])
            self._a(r.a & m[0x000E])
            self._mark(0xDF8D)
            if not r.p&Z:
                self._mark(0xDFBF)
                self._rts();return
            else:
                self._a(m[0x000F])
                yield from self._external(0xDF92,0xF2AF,0xDF95,"call",None)
                if r.pc!=0xDF95:return  # preserve nonlocal stack return
                self._y(0x00)
                self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                self._a(r.a & 0x07)
                self._y(r.a)
                self._a(m[(0xDFC0+r.y)&65535])
                m[(0x0201+r.x)&65535]=r.a
                self._a(m[(0xDFC8+r.y)&65535])
                m[(0x0202+r.x)&65535]=r.a
                self._a(m[0x000F])
                self._a(r.a & 0x1F)
                self._y(r.a)
                self._a(m[(0xDEE9+r.y)&65535])
                m[(0x0203+r.x)&65535]=r.a
                self._a(m[(0xDF07+r.y)&65535])
                m[(0x0200+r.x)&65535]=r.a
                self._x(r.x+1)
                self._x(r.x+1)
                self._x(r.x+1)
                self._x(r.x+1)
                self._mark(0xDFBE)
                self._rts();return
        else:
            self._a(m[0x005E])
            self._a(r.a & 0x08)
            self._mark(0xDF82)
            if not r.p&Z:
                self._mark(0xDFBF)
                self._rts();return
            else:
                self._y(m[0x000F])
                self._a(m[(0xDFD0+r.y)&65535])
                self._a(r.a & m[0x000E])
                self._mark(0xDF8D)
                if not r.p&Z:
                    self._mark(0xDFBF)
                    self._rts();return
                else:
                    self._a(m[0x000F])
                    yield from self._external(0xDF92,0xF2AF,0xDF95,"call",None)
                    if r.pc!=0xDF95:return  # preserve nonlocal stack return
                    self._y(0x00)
                    self._a(m[((m[0x00]|m[0x01]<<8)+r.y)&65535])
                    self._a(r.a & 0x07)
                    self._y(r.a)
                    self._a(m[(0xDFC0+r.y)&65535])
                    m[(0x0201+r.x)&65535]=r.a
                    self._a(m[(0xDFC8+r.y)&65535])
                    m[(0x0202+r.x)&65535]=r.a
                    self._a(m[0x000F])
                    self._a(r.a & 0x1F)
                    self._y(r.a)
                    self._a(m[(0xDEE9+r.y)&65535])
                    m[(0x0203+r.x)&65535]=r.a
                    self._a(m[(0xDF07+r.y)&65535])
                    m[(0x0200+r.x)&65535]=r.a
                    self._x(r.x+1)
                    self._x(r.x+1)
                    self._x(r.x+1)
                    self._x(r.x+1)
                    self._mark(0xDFBE)
                    self._rts();return

