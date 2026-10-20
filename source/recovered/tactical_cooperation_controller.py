"""Readable, bounded bank8/9 tactical cooperation controller.

Offline control-flow structuring produced named procedures and phase handlers.
Production reads immutable game data, never opcodes, control IR or PC->operation
tables. Services retain their real caller stack and explicit pending boundary.
CPU-register form is retained where flags/scratch/aliasing are observable.
"""
class _ContinueLoop_A03C(Exception):pass
class _ContinueLoop_A12C(Exception):pass
class _ContinueLoop_A18A(Exception):pass
class _ContinueLoop_A237(Exception):pass
class _ContinueLoop_A25E(Exception):pass
class _ContinueLoop_A2CE(Exception):pass
class _ContinueLoop_A5C9(Exception):pass
class _ContinueLoop_A680(Exception):pass
class _ContinueLoop_A6D2(Exception):pass
class _ContinueLoop_A807(Exception):pass
class _ContinueLoop_A873(Exception):pass
class _ContinueLoop_A8B7(Exception):pass
class _ContinueLoop_A8EA(Exception):pass
class _ContinueLoop_A993(Exception):pass
class _ContinueLoop_AA6F(Exception):pass
class _ContinueLoop_AB2C(Exception):pass
class _ContinueLoop_AC39(Exception):pass
class _ContinueLoop_AD0F(Exception):pass
class _ContinueLoop_AD33(Exception):pass
class _ContinueLoop_AD78(Exception):pass
class _ContinueLoop_ADA1(Exception):pass
class _ContinueLoop_AE0D(Exception):pass
class _ContinueLoop_AE2F(Exception):pass
class _ContinueLoop_AE97(Exception):pass
class _ContinueLoop_AEBA(Exception):pass
class _ContinueLoop_AEBC(Exception):pass
class _ContinueLoop_AF9C(Exception):pass
class _ContinueLoop_B01D(Exception):pass
class _ContinueLoop_B045(Exception):pass
class _ContinueLoop_B075(Exception):pass
class _ContinueLoop_B543(Exception):pass
class _ContinueLoop_B59B(Exception):pass
class _ContinueLoop_B9E2(Exception):pass
class _ContinueLoop_BA07(Exception):pass

from dataclasses import dataclass
import hashlib
from .battle_nmi_services import ServiceCall, ServiceWait
from .mapped_memory import UnsupportedHardware

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
REQUEST=0x6F8B
ACTOR_SLOT=0x6F8C
PROPOSAL_ACTION=0x6F8D
PROPOSAL_TARGET=0x6F8E
PROPOSAL_STATUS=0x6F8F
RNG_CURSOR=0x6F92
RNG_SAVED_X=0x6F93
SCAN_SLOT=0x6F94
NO_ACTION_COUNT=0x6F95
ATTEMPTED_COUNT=0x6F96
MOVE_COST=0x6F97
SIDE=0x504
AP=0x505
CITY=0x50E
UNIT_X=0x600
UNIT_Y=0x614
UNIT_CONDITION=0x628
UNIT_IDS=0x664
UNIT_STRATEGY=0x6FA1
CONTROL_FIELDS=(('request', 28555), ('actor_slot', 28556), ('proposal_action', 28557), ('proposal_target', 28558), ('proposal_status', 28559), ('rng_cursor', 28562), ('rng_saved_x', 28563), ('scan_slot', 28564), ('no_action_count', 28565), ('attempted_count', 28566), ('move_cost', 28567), ('side', 1284), ('ap', 1285), ('city', 1294), ('unit_x', 1536), ('unit_y', 1556), ('unit_condition', 1576), ('unit_ids', 1636), ('unit_strategy', 28577))

@dataclass
class TacticalRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA000

class TacticalCooperationController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned tactical ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=TacticalRegisters();self.events=[];self.pending=None;self._program=None
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
    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:
            yield ServiceWait('control_budget',pc,value=self._limit,reason='Source block budget; no gameplay field or caller return is manufactured')
        self._blocks+=1
    def _dispatch(self,pc,targets):
        """Original B517 protocol; static inline words are immutable data."""
        r=self.registers;m=self.memory;index=r.a
        if index>=len(targets):raise ValueError(f'Original B517 bounded index {index} at ${pc:04X}')
        self._push((pc+2)>>8);self._push(pc+2);m[0x20]=r.y
        self._a(self._shift(r.a,True));self._y(r.a);self._y(r.y+1)
        self._a(self._pop());m[0x21]=r.a;self._a(self._pop());m[0x22]=r.a
        target=targets[index];self._a(target&255);m[0x23]=r.a;self._y(r.y+1)
        self._a(target>>8);m[0x24]=r.a;self._y(m[0x20]);r.pc=target
        return index
    def _external(self,pc,target,return_pc,kind,inline_target=None):
        r=self.registers;caller_sp=r.sp
        if kind!='tail':self._push((pc+2)>>8);self._push(pc+2)
        else:caller_sp=(r.sp+2)&255
        r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        self.events.append(dict(call_pc=pc,target=target,return_pc=return_pc,kind=kind))
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),caller_sp)
    def decision_state(self):
        m=self.memory
        return {name:m[address]for name,address in CONTROL_FIELDS}
    def _drive(self):
        while True:
            if isinstance(self.pending,ServiceWait):
                if self.pending.category=='control_budget':return self._result('budget')
                return self._result('dependency')
            if isinstance(self.pending,ServiceCall):
                call=self.pending
                if self.services is None:return self._result('dependency')
                try:result=self.services(call)
                except UnsupportedHardware:return self._result('dependency')
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                self._call_owner=None;return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=self.decision_state(),registers=vars(self.registers).copy(),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self,*,max_blocks=None):
        if self._program is None:raise RuntimeError('No pending tactical invocation')
        if isinstance(self.pending,ServiceWait)and self.pending.category=='control_budget':
            if max_blocks is None:return self._result('budget')
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Explicit positive continuation budget required')
            self._limit=max_blocks;self._blocks=0;self.pending=None
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA000,*,registers=None,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing tactical invocation first')
        if registers is None:raise ValueError('Supply actual caller registers and existing RTS frame')
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry outside original tactical closure')
        if registers.p&D:raise ValueError('Binary CPU comparison requires D=0')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative source block budget required')
        self.registers=registers;r=registers
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc
        self._return_sp=(r.sp+2)&255;self._before=self.decision_state()
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry);return self._drive()
    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(8,9)or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No tactical body owns this exact physical pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns pending tactical update'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

    LOCAL_ENTRIES=(40960, 41005, 41020, 41107, 41113, 41137, 41197, 41221, 41255, 41284, 41306, 41315, 41318, 41402, 41430, 41439, 41445, 41478, 41488, 41515, 41603, 41624, 41639, 41645, 41727, 41748, 41763, 41769, 41803, 41839, 41853, 41901, 41924, 42004, 42097, 42247, 42284, 42323, 42337, 42388, 42411, 42424, 42501, 42502, 42508, 42534, 42547, 42567, 42601, 42622, 42695, 42745, 42751, 42792, 42803, 42811, 42816, 42839, 42871, 43063, 43079, 43121, 43176, 43217, 43219, 43237, 43240, 43332, 43353, 43356, 43395, 43464, 43471, 43493, 43523, 43545, 43567, 43594, 43621, 43714, 43741, 43761, 43768, 43873, 43880, 43917, 43944, 43976, 44008, 44040, 44079, 44081, 44096, 44109, 44129, 44155, 44238, 44249, 44251, 44262, 44264, 44275, 44286, 44288, 44318, 44322, 44331, 44353, 44357, 44385, 44389, 44400, 44423, 44434, 44491, 44495, 44522, 44531, 44538, 44542, 44572, 44576, 44633, 44637, 44648, 44672, 44687, 44691, 44813, 44825, 44862, 44913, 44990, 45010, 45012, 45045, 45046, 45159, 45240, 45307, 46185, 46225, 46274, 46305, 46390, 46469, 46549, 46821, 46830, 46831, 46842, 46853, 47411, 47425, 47469, 47482, 47501, 47580, 47750, 47789)
    def _entry(self,entry):
        if entry==0xA000:return self.tactical_entry()
        elif entry==0xA02D:return self.cooperative_update()
        elif entry==0xA03C:return self.scan_eligible_actors()
        elif entry==0xA093:return self.tactical_helper_a093()
        elif entry==0xA099:return self.dispatch_actor_strategy()
        elif entry==0xA0B1:return self.strategy_00_tactics_and_advance()
        elif entry==0xA0ED:return self.tactical_helper_a0ed()
        elif entry==0xA105:return self.strategy_01_opposite_commander()
        elif entry==0xA127:return self.tactical_helper_a127()
        elif entry==0xA144:return self.tactical_helper_a144()
        elif entry==0xA15A:return self.tactical_helper_a15a()
        elif entry==0xA163:return self.tactical_helper_a163()
        elif entry==0xA166:return self.strategy_02_near_actor()
        elif entry==0xA1BA:return self.tactical_helper_a1ba()
        elif entry==0xA1D6:return self.tactical_helper_a1d6()
        elif entry==0xA1DF:return self.tactical_helper_a1df()
        elif entry==0xA1E5:return self.tactical_helper_a1e5()
        elif entry==0xA206:return self.tactical_helper_a206()
        elif entry==0xA210:return self.strategy_03_escort_own_commander()
        elif entry==0xA22B:return self.tactical_helper_a22b()
        elif entry==0xA283:return self.tactical_helper_a283()
        elif entry==0xA298:return self.tactical_helper_a298()
        elif entry==0xA2A7:return self.tactical_helper_a2a7()
        elif entry==0xA2AD:return self.strategy_04_actor_radius_three()
        elif entry==0xA2FF:return self.tactical_helper_a2ff()
        elif entry==0xA314:return self.tactical_helper_a314()
        elif entry==0xA323:return self.tactical_helper_a323()
        elif entry==0xA329:return self.strategy_05_resupply()
        elif entry==0xA34B:return self.tactical_helper_a34b()
        elif entry==0xA36F:return self.tactical_helper_a36f()
        elif entry==0xA37D:return self.tactical_helper_a37d()
        elif entry==0xA3AD:return self.tactical_helper_a3ad()
        elif entry==0xA3C4:return self.tactical_helper_a3c4()
        elif entry==0xA414:return self.tactical_helper_a414()
        elif entry==0xA471:return self.tactical_helper_a471()
        elif entry==0xA507:return self.strategy_06_heal()
        elif entry==0xA52C:return self.tactical_helper_a52c()
        elif entry==0xA553:return self.tactical_helper_a553()
        elif entry==0xA561:return self.tactical_helper_a561()
        elif entry==0xA594:return self.tactical_helper_a594()
        elif entry==0xA5AB:return self.tactical_helper_a5ab()
        elif entry==0xA5B8:return self.tactical_helper_a5b8()
        elif entry==0xA605:return self.tactical_helper_a605()
        elif entry==0xA606:return self.strategy_07_no_action()
        elif entry==0xA60C:return self.plan_two_axis_movement()
        elif entry==0xA626:return self.tactical_helper_a626()
        elif entry==0xA633:return self.tactical_helper_a633()
        elif entry==0xA647:return self.tactical_helper_a647()
        elif entry==0xA669:return self.tactical_helper_a669()
        elif entry==0xA67E:return self.tactical_helper_a67e()
        elif entry==0xA6C7:return self.tactical_helper_a6c7()
        elif entry==0xA6F9:return self.tactical_helper_a6f9()
        elif entry==0xA6FF:return self.tactical_helper_a6ff()
        elif entry==0xA728:return self.tactical_helper_a728()
        elif entry==0xA733:return self.tactical_helper_a733()
        elif entry==0xA73B:return self.tactical_helper_a73b()
        elif entry==0xA740:return self.quote_direction_ap_cost()
        elif entry==0xA757:return self.tactical_helper_a757()
        elif entry==0xA777:return self.tactical_helper_a777()
        elif entry==0xA837:return self.find_orthogonal_neighbors()
        elif entry==0xA847:return self.tactical_helper_a847()
        elif entry==0xA871:return self.tactical_helper_a871()
        elif entry==0xA8A8:return self.propose_adjacent_attack()
        elif entry==0xA8D1:return self.tactical_helper_a8d1()
        elif entry==0xA8D3:return self.tactical_helper_a8d3()
        elif entry==0xA8E5:return self.tactical_helper_a8e5()
        elif entry==0xA8E8:return self.tactical_helper_a8e8()
        elif entry==0xA944:return self.opposing_side_marker()
        elif entry==0xA959:return self.tactical_helper_a959()
        elif entry==0xA95C:return self.choose_basic_tactic()
        elif entry==0xA983:return self.tactical_helper_a983()
        elif entry==0xA9C8:return self.tactical_helper_a9c8()
        elif entry==0xA9CF:return self.prioritize_basic_tactics()
        elif entry==0xA9E5:return self.tactical_helper_a9e5()
        elif entry==0xAA03:return self.tactical_helper_aa03()
        elif entry==0xAA19:return self.tactical_helper_aa19()
        elif entry==0xAA2F:return self.tactical_helper_aa2f()
        elif entry==0xAA4A:return self.tactical_helper_aa4a()
        elif entry==0xAA65:return self.tactical_helper_aa65()
        elif entry==0xAAC2:return self.tactical_helper_aac2()
        elif entry==0xAADD:return self.tactical_helper_aadd()
        elif entry==0xAAF1:return self.tactical_helper_aaf1()
        elif entry==0xAAF8:return self.choose_special_tactic()
        elif entry==0xAB61:return self.tactical_helper_ab61()
        elif entry==0xAB68:return self.prioritize_special_tactics()
        elif entry==0xAB8D:return self.tactical_helper_ab8d()
        elif entry==0xABA8:return self.tactical_helper_aba8()
        elif entry==0xABC8:return self.tactical_helper_abc8()
        elif entry==0xABE8:return self.tactical_helper_abe8()
        elif entry==0xAC08:return self.tactical_helper_ac08()
        elif entry==0xAC2F:return self.tactical_helper_ac2f()
        elif entry==0xAC31:return self.scan_special_officer_whitelist()
        elif entry==0xAC40:return self.tactical_helper_ac40()
        elif entry==0xAC4D:return self.tactical_helper_ac4d()
        elif entry==0xAC61:return self.tactical_helper_ac61()
        elif entry==0xAC7B:return self.check_tactic_target()
        elif entry==0xACCE:return self.predicate_tactics_00()
        elif entry==0xACD9:return self.tactical_helper_acd9()
        elif entry==0xACDB:return self.predicate_tactics_01_02_03()
        elif entry==0xACE6:return self.tactical_helper_ace6()
        elif entry==0xACE8:return self.predicate_tactics_04()
        elif entry==0xACF3:return self.predicate_tactics_05()
        elif entry==0xACFE:return self.tactical_helper_acfe()
        elif entry==0xAD00:return self.predicate_tactics_06()
        elif entry==0xAD1E:return self.tactical_helper_ad1e()
        elif entry==0xAD22:return self.predicate_tactics_07()
        elif entry==0xAD2B:return self.tactical_helper_ad2b()
        elif entry==0xAD41:return self.tactical_helper_ad41()
        elif entry==0xAD45:return self.predicate_tactics_08()
        elif entry==0xAD61:return self.tactical_helper_ad61()
        elif entry==0xAD65:return self.predicate_tactics_09()
        elif entry==0xAD70:return self.tactical_helper_ad70()
        elif entry==0xAD87:return self.tactical_helper_ad87()
        elif entry==0xAD92:return self.predicate_tactics_10_12()
        elif entry==0xADCB:return self.tactical_helper_adcb()
        elif entry==0xADCF:return self.predicate_tactics_11()
        elif entry==0xADEA:return self.tactical_helper_adea()
        elif entry==0xADF3:return self.tactical_helper_adf3()
        elif entry==0xADFA:return self.tactical_helper_adfa()
        elif entry==0xADFE:return self.predicate_tactics_13()
        elif entry==0xAE1C:return self.tactical_helper_ae1c()
        elif entry==0xAE20:return self.predicate_tactics_14()
        elif entry==0xAE59:return self.tactical_helper_ae59()
        elif entry==0xAE5D:return self.predicate_tactics_15()
        elif entry==0xAE68:return self.tactical_helper_ae68()
        elif entry==0xAE80:return self.tactical_helper_ae80()
        elif entry==0xAE8F:return self.tactical_helper_ae8f()
        elif entry==0xAE93:return self.rank_candidate_troops()
        elif entry==0xAF0D:return self.propose_retreat()
        elif entry==0xAF19:return self.tactical_helper_af19()
        elif entry==0xAF3E:return self.tactical_helper_af3e()
        elif entry==0xAF71:return self.tactical_helper_af71()
        elif entry==0xAFBE:return self.tactical_helper_afbe()
        elif entry==0xAFD2:return self.tactical_helper_afd2()
        elif entry==0xAFD4:return self.tactical_helper_afd4()
        elif entry==0xAFF5:return self.tactical_helper_aff5()
        elif entry==0xAFF6:return self.choose_retreat_city()
        elif entry==0xB067:return self.sum_army_troops()
        elif entry==0xB0B8:return self.tactical_helper_b0b8()
        elif entry==0xB0FB:return self.officer_record_pointer()
        elif entry==0xB469:return self.tactical_helper_b469()
        elif entry==0xB491:return self.tactical_helper_b491()
        elif entry==0xB4C2:return self.tactical_helper_b4c2()
        elif entry==0xB4E1:return self.initial_officer_record_pointer()
        elif entry==0xB536:return self.divide_u24_by_u16()
        elif entry==0xB585:return self.multiply_u24_by_u8()
        elif entry==0xB5D5:return self.draw_ai_rng_byte()
        elif entry==0xB6E5:return self.normalized_terrain_at_scratch_xy()
        elif entry==0xB6EE:return self.tactical_helper_b6ee()
        elif entry==0xB6EF:return self.tactical_helper_b6ef()
        elif entry==0xB6FA:return self.tactical_helper_b6fa()
        elif entry==0xB705:return self.read_terrain_chunk()
        elif entry==0xB933:return self.consume_opposite_ambush_cache()
        elif entry==0xB941:return self.tactical_helper_b941()
        elif entry==0xB96D:return self.tactical_helper_b96d()
        elif entry==0xB97A:return self.tactical_helper_b97a()
        elif entry==0xB98D:return self.tactical_helper_b98d()
        elif entry==0xB9DC:return self.tactical_helper_b9dc()
        elif entry==0xBA86:return self.tactical_helper_ba86()
        elif entry==0xBAAD:return self.tactical_helper_baad()
        raise ValueError("Entry outside original tactical closure")

    def tactical_entry(self):
        """$A000: tactical entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA000)
        return (yield from self.cooperative_update())

    def cooperative_update(self):
        """$A02D: cooperative update; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA02D)
        self._a(m[REQUEST])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xA032)
        if not r.p&Z:
            self._compare(r.a,0x01)
            yield from self._checkpoint(0xA037)
            if not r.p&Z:
                return (yield from self.scan_eligible_actors())
            else:
                return (yield from self.consume_opposite_ambush_cache())
        else:
            yield from self._checkpoint(0xA034)
            self._rts();return

    def scan_eligible_actors(self):
        """$A03C: scan eligible actors; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        while True:  # natural loop $A03C
            try:
                yield from self._checkpoint(0xA03C)
                self._y(m[SCAN_SLOT])
                self._compare(r.y,0x14)
                yield from self._checkpoint(0xA041)
                if r.p&C:
                    self._a(m[ATTEMPTED_COUNT])
                    self._compare(r.a,m[NO_ACTION_COUNT])
                    yield from self._checkpoint(0xA079)
                    if r.p&Z:
                        self._a(0x03)
                        m[PROPOSAL_STATUS]=r.a
                        self._a(0x00)
                        m[SCAN_SLOT]=r.a
                        pass
                    else:
                        self._a(0x00)
                        m[SCAN_SLOT]=r.a
                        m[NO_ACTION_COUNT]=r.a
                        m[ATTEMPTED_COUNT]=r.a
                        continue
                    pass
                else:
                    m[SCAN_SLOT]=self._nz(m[SCAN_SLOT]+1)
                    self._a(m[(UNIT_STRATEGY+r.y)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xA04B)
                    if r.p&Z:
                        self._a(m[SCAN_SLOT])
                        self._compare(r.a,0x14)
                        yield from self._checkpoint(0xA071)
                        if not r.p&C:
                            continue
                        else:
                            self._a(m[ATTEMPTED_COUNT])
                            self._compare(r.a,m[NO_ACTION_COUNT])
                            yield from self._checkpoint(0xA079)
                            if r.p&Z:
                                self._a(0x03)
                                m[PROPOSAL_STATUS]=r.a
                                self._a(0x00)
                                m[SCAN_SLOT]=r.a
                                pass
                            else:
                                self._a(0x00)
                                m[SCAN_SLOT]=r.a
                                m[NO_ACTION_COUNT]=r.a
                                m[ATTEMPTED_COUNT]=r.a
                                continue
                            pass
                        pass
                    else:
                        if not (yield from self._local_call(self.opposing_side_marker,0xA04D,0xA050)):return
                        yield from self._checkpoint(0xA050)
                        if r.p&N:
                            self._a(m[SCAN_SLOT])
                            self._compare(r.a,0x14)
                            yield from self._checkpoint(0xA071)
                            if not r.p&C:
                                continue
                            else:
                                self._a(m[ATTEMPTED_COUNT])
                                self._compare(r.a,m[NO_ACTION_COUNT])
                                yield from self._checkpoint(0xA079)
                                if r.p&Z:
                                    self._a(0x03)
                                    m[PROPOSAL_STATUS]=r.a
                                    self._a(0x00)
                                    m[SCAN_SLOT]=r.a
                                    pass
                                else:
                                    self._a(0x00)
                                    m[SCAN_SLOT]=r.a
                                    m[NO_ACTION_COUNT]=r.a
                                    m[ATTEMPTED_COUNT]=r.a
                                    continue
                                pass
                            pass
                        else:
                            self._a(m[(UNIT_IDS+r.y)&65535])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xA057)
                            if r.p&Z:
                                self._a(m[SCAN_SLOT])
                                self._compare(r.a,0x14)
                                yield from self._checkpoint(0xA071)
                                if not r.p&C:
                                    continue
                                else:
                                    self._a(m[ATTEMPTED_COUNT])
                                    self._compare(r.a,m[NO_ACTION_COUNT])
                                    yield from self._checkpoint(0xA079)
                                    if r.p&Z:
                                        self._a(0x03)
                                        m[PROPOSAL_STATUS]=r.a
                                        self._a(0x00)
                                        m[SCAN_SLOT]=r.a
                                        pass
                                    else:
                                        self._a(0x00)
                                        m[SCAN_SLOT]=r.a
                                        m[NO_ACTION_COUNT]=r.a
                                        m[ATTEMPTED_COUNT]=r.a
                                        continue
                                    pass
                                pass
                            else:
                                m[ATTEMPTED_COUNT]=self._nz(m[ATTEMPTED_COUNT]+1)
                                m[ACTOR_SLOT]=r.y
                                if not (yield from self._local_call(self.dispatch_actor_strategy,0xA05F,0xA062)):return
                                self._a(m[PROPOSAL_STATUS])
                                self._compare(r.a,0x03)
                                yield from self._checkpoint(0xA067)
                                if not r.p&Z:
                                    pass
                                else:
                                    m[NO_ACTION_COUNT]=self._nz(m[NO_ACTION_COUNT]+1)
                                    self._a(m[SCAN_SLOT])
                                    self._compare(r.a,0x14)
                                    yield from self._checkpoint(0xA071)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._a(m[ATTEMPTED_COUNT])
                                        self._compare(r.a,m[NO_ACTION_COUNT])
                                        yield from self._checkpoint(0xA079)
                                        if r.p&Z:
                                            self._a(0x03)
                                            m[PROPOSAL_STATUS]=r.a
                                            self._a(0x00)
                                            m[SCAN_SLOT]=r.a
                                            pass
                                        else:
                                            self._a(0x00)
                                            m[SCAN_SLOT]=r.a
                                            m[NO_ACTION_COUNT]=r.a
                                            m[ATTEMPTED_COUNT]=r.a
                                            continue
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                return (yield from self.tactical_helper_a093())
            except _ContinueLoop_A03C:
                continue

    def tactical_helper_a093(self):
        """$A093: tactical helper a093; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA093)
        self._a(0xFF)
        m[REQUEST]=r.a
        yield from self._checkpoint(0xA098)
        self._rts();return

    def dispatch_actor_strategy(self):
        """$A099: dispatch actor strategy; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA099)
        self._a(m[(UNIT_STRATEGY+r.y)&65535])
        self._a(r.a & 0x0F)
        yield from self._checkpoint(0xA09E)
        index=self._dispatch(0xA09E,(41137, 41221, 41318, 41488, 41645, 41769, 42247, 42502))
        return (yield from (self.strategy_00_tactics_and_advance,self.strategy_01_opposite_commander,self.strategy_02_near_actor,self.strategy_03_escort_own_commander,self.strategy_04_actor_radius_three,self.strategy_05_resupply,self.strategy_06_heal,self.strategy_07_no_action,)[index]())

    def strategy_00_tactics_and_advance(self):
        """$A0B1: strategy 00 tactics and advance; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA0B1)
        self._a(m[SIDE])
        yield from self._checkpoint(0xA0B4)
        if r.p&N:
            if not (yield from self._local_call(self.propose_retreat,0xA0B9,0xA0BC)):return
            yield from self._checkpoint(0xA0BC)
            if not r.p&C:
                if not (yield from self._local_call(self.choose_special_tactic,0xA0BF,0xA0C2)):return
                yield from self._checkpoint(0xA0C2)
                if not r.p&C:
                    if not (yield from self._local_call(self.propose_adjacent_attack,0xA0C5,0xA0C8)):return
                    yield from self._checkpoint(0xA0C8)
                    if not r.p&C:
                        if not (yield from self._local_call(self.choose_basic_tactic,0xA0CB,0xA0CE)):return
                        yield from self._checkpoint(0xA0CE)
                        if not r.p&C:
                            if not (yield from self._local_call(self.draw_ai_rng_byte,0xA0D1,0xA0D4)):return
                            self._a(r.a & 0x03)
                            yield from self._checkpoint(0xA0D6)
                            if not r.p&Z:
                                self._a(m[UNIT_X])
                                m[0x0020]=r.a
                                self._a(m[UNIT_Y])
                                self._compare(r.a,0x10)
                                yield from self._checkpoint(0xA0E9)
                                if not r.p&C:
                                    pass
                                else:
                                    self._add(0x01,subtract=True)
                                    pass
                                return (yield from self.tactical_helper_a0ed())
                            else:
                                self._a(0x03)
                                m[PROPOSAL_STATUS]=r.a
                                yield from self._checkpoint(0xA0DD)
                                self._rts();return
                        else:
                            yield from self._checkpoint(0xA0D0)
                            self._rts();return
                    else:
                        yield from self._checkpoint(0xA0CA)
                        self._rts();return
                else:
                    yield from self._checkpoint(0xA0C4)
                    self._rts();return
            else:
                yield from self._checkpoint(0xA0BE)
                self._rts();return
        else:
            if not (yield from self._local_call(self.propose_retreat,0xA0F6,0xA0F9)):return
            yield from self._checkpoint(0xA0F9)
            if not r.p&C:
                if not (yield from self._local_call(self.choose_special_tactic,0xA0FC,0xA0FF)):return
                yield from self._checkpoint(0xA0FF)
                if not r.p&C:
                    return (yield from self.choose_basic_tactic())
                else:
                    yield from self._checkpoint(0xA101)
                    self._rts();return
            else:
                yield from self._checkpoint(0xA0FB)
                self._rts();return

    def tactical_helper_a0ed(self):
        """$A0ED: tactical helper a0ed; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA0ED)
        m[0x0021]=r.a
        self._y(m[ACTOR_SLOT])
        return (yield from self.plan_two_axis_movement())

    def strategy_01_opposite_commander(self):
        """$A105: strategy 01 opposite commander; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA105)
        if not (yield from self._local_call(self.propose_retreat,0xA105,0xA108)):return
        yield from self._checkpoint(0xA108)
        if not r.p&C:
            if not (yield from self._local_call(self.choose_special_tactic,0xA10B,0xA10E)):return
            yield from self._checkpoint(0xA10E)
            if not r.p&C:
                self._a(m[AP])
                self._compare(r.a,0x02)
                yield from self._checkpoint(0xA116)
                if not r.p&C:
                    return (yield from self.tactical_helper_a144())
                else:
                    self._y(m[ACTOR_SLOT])
                    if not (yield from self._local_call(self.find_orthogonal_neighbors,0xA11B,0xA11E)):return
                    self._x(0x0A)
                    self._a(m[SIDE])
                    yield from self._checkpoint(0xA123)
                    if not r.p&N:
                        pass
                    else:
                        self._x(0x00)
                        pass
                    return (yield from self.tactical_helper_a127())
            else:
                yield from self._checkpoint(0xA110)
                self._rts();return
        else:
            yield from self._checkpoint(0xA10A)
            self._rts();return

    def tactical_helper_a127(self):
        """$A127: tactical helper a127; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA127)
        m[0x0020]=r.x
        self._y(0x00)
        while True:  # natural loop $A12C
            try:
                self._a(m[(0x6FDD+r.y)&65535])
                self._a(r.a & 0x7F)
                self._compare(r.a,m[0x0020])
                yield from self._checkpoint(0xA134)
                if not r.p&Z:
                    self._y(r.y+1)
                    self._compare(r.y,0x04)
                    yield from self._checkpoint(0xA142)
                    if not r.p&C:
                        continue
                    else:
                        return (yield from self.tactical_helper_a144())
                else:
                    m[PROPOSAL_ACTION]=r.a
                    self._a(0x01)
                    m[PROPOSAL_STATUS]=r.a
                    yield from self._checkpoint(0xA13E)
                    self._rts();return
            except _ContinueLoop_A12C:
                continue

    def tactical_helper_a144(self):
        """$A144: tactical helper a144; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA144)
        self._x(0x0A)
        self._a(m[SIDE])
        yield from self._checkpoint(0xA149)
        if r.p&N:
            if not (yield from self._local_call(self.tactical_helper_a1e5,0xA160,0xA163)):return
            return (yield from self.tactical_helper_a163())
        else:
            self._a(m[(UNIT_X+r.x)&65535])
            m[0x0020]=r.a
            self._a(m[(UNIT_Y+r.x)&65535])
            self._compare(r.a,0x10)
            yield from self._checkpoint(0xA156)
            if not r.p&C:
                pass
            else:
                self._add(0x01,subtract=True)
                pass
            return (yield from self.tactical_helper_a15a())

    def tactical_helper_a15a(self):
        """$A15A: tactical helper a15a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA15A)
        m[0x0021]=r.a
        return (yield from self.tactical_helper_a163())

    def tactical_helper_a163(self):
        """$A163: tactical helper a163; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA163)
        return (yield from self.plan_two_axis_movement())

    def strategy_02_near_actor(self):
        """$A166: strategy 02 near actor; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA166)
        if not (yield from self._local_call(self.propose_retreat,0xA166,0xA169)):return
        yield from self._checkpoint(0xA169)
        if not r.p&C:
            if not (yield from self._local_call(self.choose_special_tactic,0xA16C,0xA16F)):return
            yield from self._checkpoint(0xA16F)
            if not r.p&C:
                self._y(m[ACTOR_SLOT])
                if not (yield from self._local_call(self.propose_adjacent_attack,0xA175,0xA178)):return
                yield from self._checkpoint(0xA178)
                if not r.p&C:
                    self._y(m[ACTOR_SLOT])
                    self._a(0x02)
                    if not (yield from self._local_call(self.tactical_helper_a8d3,0xA180,0xA183)):return
                    self._a(0xFF)
                    m[0x0020]=r.a
                    self._y(0x00)
                    while True:  # natural loop $A18A
                        try:
                            self._a(m[(0x6FC9+r.y)&65535])
                            yield from self._checkpoint(0xA18D)
                            if not r.p&N:
                                pass
                            else:
                                self._a(r.a & 0x7F)
                                self._compare(r.a,m[0x0020])
                                yield from self._checkpoint(0xA194)
                                if r.p&C:
                                    pass
                                else:
                                    m[0x0020]=r.a
                                    m[0x0021]=r.y
                                    pass
                                pass
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            yield from self._checkpoint(0xA19F)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(m[0x0020])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xA1A6)
                            if r.p&Z:
                                self._x(0x0A)
                                self._a(m[SIDE])
                                yield from self._checkpoint(0xA1C5)
                                if r.p&N:
                                    if not (yield from self._local_call(self.tactical_helper_a1e5,0xA1DC,0xA1DF)):return
                                    return (yield from self.tactical_helper_a1df())
                                else:
                                    self._a(m[(UNIT_X+r.x)&65535])
                                    m[0x0020]=r.a
                                    self._a(m[(UNIT_Y+r.x)&65535])
                                    self._compare(r.a,0x10)
                                    yield from self._checkpoint(0xA1D2)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._add(0x01,subtract=True)
                                        pass
                                    return (yield from self.tactical_helper_a1d6())
                            else:
                                self._y(m[0x0021])
                                self._a(m[(UNIT_X+r.y)&65535])
                                m[0x0020]=r.a
                                self._a(m[(UNIT_Y+r.y)&65535])
                                self._compare(r.a,0x10)
                                yield from self._checkpoint(0xA1B6)
                                if not r.p&C:
                                    pass
                                else:
                                    self._add(0x01,subtract=True)
                                    pass
                                return (yield from self.tactical_helper_a1ba())
                        except _ContinueLoop_A18A:
                            continue
                else:
                    yield from self._checkpoint(0xA17A)
                    self._rts();return
            else:
                yield from self._checkpoint(0xA171)
                self._rts();return
        else:
            yield from self._checkpoint(0xA16B)
            self._rts();return

    def tactical_helper_a1ba(self):
        """$A1BA: tactical helper a1ba; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1BA)
        m[0x0021]=r.a
        return (yield from self.tactical_helper_a1df())

    def tactical_helper_a1d6(self):
        """$A1D6: tactical helper a1d6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1D6)
        m[0x0021]=r.a
        return (yield from self.tactical_helper_a1df())

    def tactical_helper_a1df(self):
        """$A1DF: tactical helper a1df; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1DF)
        self._y(m[ACTOR_SLOT])
        return (yield from self.plan_two_axis_movement())

    def tactical_helper_a1e5(self):
        """$A1E5: tactical helper a1e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA1E5)
        self._y(0x26)
        yield from self._external(0xA1E7,0xF266,0xA1EA,"call",None)
        if r.pc!=0xA1EA:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0x8C52+r.y)&65535])
        m[0x0022]=r.a
        self._a(m[(0x8C53+r.y)&65535])
        m[0x0023]=r.a
        self._y(0x00)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA201)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a206())

    def tactical_helper_a206(self):
        """$A206: tactical helper a206; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA206)
        m[0x0021]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        m[0x0020]=r.a
        yield from self._checkpoint(0xA20F)
        self._rts();return

    def strategy_03_escort_own_commander(self):
        """$A210: strategy 03 escort own commander; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA210)
        if not (yield from self._local_call(self.propose_retreat,0xA210,0xA213)):return
        yield from self._checkpoint(0xA213)
        if not r.p&C:
            if not (yield from self._local_call(self.choose_special_tactic,0xA216,0xA219)):return
            yield from self._checkpoint(0xA219)
            if not r.p&C:
                if not (yield from self._local_call(self.propose_adjacent_attack,0xA21C,0xA21F)):return
                yield from self._checkpoint(0xA21F)
                if not r.p&C:
                    self._y(0x00)
                    self._a(m[SIDE])
                    yield from self._checkpoint(0xA227)
                    if not r.p&N:
                        pass
                    else:
                        self._y(0x0A)
                        pass
                    return (yield from self.tactical_helper_a22b())
                else:
                    yield from self._checkpoint(0xA221)
                    self._rts();return
            else:
                yield from self._checkpoint(0xA21B)
                self._rts();return
        else:
            yield from self._checkpoint(0xA215)
            self._rts();return

    def tactical_helper_a22b(self):
        """$A22B: tactical helper a22b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA22B)
        self._a(0x02)
        if not (yield from self._local_call(self.tactical_helper_a8d3,0xA22D,0xA230)):return
        self._a(0xFF)
        m[0x0020]=r.a
        self._y(0x00)
        while True:  # natural loop $A237
            try:
                self._a(m[(0x6FC9+r.y)&65535])
                yield from self._checkpoint(0xA23A)
                if not r.p&N:
                    pass
                else:
                    self._compare(r.a,m[0x0020])
                    yield from self._checkpoint(0xA23F)
                    if r.p&C:
                        pass
                    else:
                        m[0x0020]=r.a
                        m[0x0021]=r.y
                        pass
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                yield from self._checkpoint(0xA24A)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0020])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xA251)
                if r.p&Z:
                    if not (yield from self._local_call(self.choose_basic_tactic,0xA289,0xA28C)):return
                    yield from self._checkpoint(0xA28C)
                    if not r.p&C:
                        self._x(0x00)
                        self._a(m[SIDE])
                        yield from self._checkpoint(0xA294)
                        if not r.p&N:
                            pass
                        else:
                            self._x(0x0A)
                            pass
                        return (yield from self.tactical_helper_a298())
                    else:
                        yield from self._checkpoint(0xA28E)
                        self._rts();return
                else:
                    self._y(m[0x0021])
                    m[PROPOSAL_TARGET]=r.y
                    if not (yield from self._local_call(self.find_orthogonal_neighbors,0xA259,0xA25C)):return
                    self._y(0x00)
                    while True:  # natural loop $A25E
                        try:
                            self._a(m[(0x6FDD+r.y)&65535])
                            yield from self._checkpoint(0xA261)
                            if r.p&N:
                                self._y(r.y+1)
                                self._compare(r.y,0x04)
                                yield from self._checkpoint(0xA26F)
                                if not r.p&C:
                                    continue
                                else:
                                    self._y(m[PROPOSAL_TARGET])
                                    self._a(m[(UNIT_X+r.y)&65535])
                                    m[0x0020]=r.a
                                    self._a(m[(UNIT_Y+r.y)&65535])
                                    self._compare(r.a,0x10)
                                    yield from self._checkpoint(0xA27F)
                                    if not r.p&C:
                                        pass
                                    else:
                                        self._add(0x01,subtract=True)
                                        pass
                                    return (yield from self.tactical_helper_a283())
                            else:
                                yield from self._checkpoint(0xA263)
                                if r.p&Z:
                                    self._y(r.y+1)
                                    self._compare(r.y,0x04)
                                    yield from self._checkpoint(0xA26F)
                                    if not r.p&C:
                                        continue
                                    else:
                                        self._y(m[PROPOSAL_TARGET])
                                        self._a(m[(UNIT_X+r.y)&65535])
                                        m[0x0020]=r.a
                                        self._a(m[(UNIT_Y+r.y)&65535])
                                        self._compare(r.a,0x10)
                                        yield from self._checkpoint(0xA27F)
                                        if not r.p&C:
                                            pass
                                        else:
                                            self._add(0x01,subtract=True)
                                            pass
                                        return (yield from self.tactical_helper_a283())
                                else:
                                    self._compare(r.a,0x0A)
                                    yield from self._checkpoint(0xA267)
                                    if r.p&Z:
                                        self._y(r.y+1)
                                        self._compare(r.y,0x04)
                                        yield from self._checkpoint(0xA26F)
                                        if not r.p&C:
                                            continue
                                        else:
                                            self._y(m[PROPOSAL_TARGET])
                                            self._a(m[(UNIT_X+r.y)&65535])
                                            m[0x0020]=r.a
                                            self._a(m[(UNIT_Y+r.y)&65535])
                                            self._compare(r.a,0x10)
                                            yield from self._checkpoint(0xA27F)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._add(0x01,subtract=True)
                                                pass
                                            return (yield from self.tactical_helper_a283())
                                    else:
                                        return (yield from self.choose_basic_tactic())
                        except _ContinueLoop_A25E:
                            continue
            except _ContinueLoop_A237:
                continue

    def tactical_helper_a283(self):
        """$A283: tactical helper a283; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA283)
        m[0x0021]=r.a
        return (yield from self.plan_two_axis_movement())

    def tactical_helper_a298(self):
        """$A298: tactical helper a298; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA298)
        self._a(m[(UNIT_X+r.x)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.x)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA2A3)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a2a7())

    def tactical_helper_a2a7(self):
        """$A2A7: tactical helper a2a7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA2A7)
        m[0x0021]=r.a
        return (yield from self.plan_two_axis_movement())

    def strategy_04_actor_radius_three(self):
        """$A2AD: strategy 04 actor radius three; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA2AD)
        if not (yield from self._local_call(self.propose_retreat,0xA2AD,0xA2B0)):return
        yield from self._checkpoint(0xA2B0)
        if not r.p&C:
            if not (yield from self._local_call(self.choose_special_tactic,0xA2B3,0xA2B6)):return
            yield from self._checkpoint(0xA2B6)
            if not r.p&C:
                if not (yield from self._local_call(self.propose_adjacent_attack,0xA2B9,0xA2BC)):return
                yield from self._checkpoint(0xA2BC)
                if not r.p&C:
                    self._y(m[ACTOR_SLOT])
                    self._a(0x03)
                    if not (yield from self._local_call(self.tactical_helper_a8d3,0xA2C4,0xA2C7)):return
                    self._a(0xFF)
                    m[0x0020]=r.a
                    self._y(0x00)
                    while True:  # natural loop $A2CE
                        try:
                            self._a(m[(0x6FC9+r.y)&65535])
                            yield from self._checkpoint(0xA2D1)
                            if not r.p&N:
                                pass
                            else:
                                self._compare(r.a,m[0x0020])
                                yield from self._checkpoint(0xA2D6)
                                if r.p&C:
                                    pass
                                else:
                                    m[0x0020]=r.a
                                    m[0x0021]=r.y
                                    pass
                                pass
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            yield from self._checkpoint(0xA2E1)
                            if not r.p&C:
                                continue
                            else:
                                pass
                            self._a(m[0x0020])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xA2E8)
                            if r.p&Z:
                                if not (yield from self._local_call(self.choose_basic_tactic,0xA305,0xA308)):return
                                yield from self._checkpoint(0xA308)
                                if not r.p&C:
                                    self._x(0x00)
                                    self._a(m[SIDE])
                                    yield from self._checkpoint(0xA310)
                                    if not r.p&N:
                                        pass
                                    else:
                                        self._x(0x0A)
                                        pass
                                    return (yield from self.tactical_helper_a314())
                                else:
                                    yield from self._checkpoint(0xA30A)
                                    self._rts();return
                            else:
                                self._y(m[0x0021])
                                m[PROPOSAL_TARGET]=r.y
                                self._a(m[(UNIT_X+r.y)&65535])
                                m[0x0020]=r.a
                                self._a(m[(UNIT_Y+r.y)&65535])
                                self._compare(r.a,0x10)
                                yield from self._checkpoint(0xA2FB)
                                if not r.p&C:
                                    pass
                                else:
                                    self._add(0x01,subtract=True)
                                    pass
                                return (yield from self.tactical_helper_a2ff())
                        except _ContinueLoop_A2CE:
                            continue
                else:
                    yield from self._checkpoint(0xA2BE)
                    self._rts();return
            else:
                yield from self._checkpoint(0xA2B8)
                self._rts();return
        else:
            yield from self._checkpoint(0xA2B2)
            self._rts();return

    def tactical_helper_a2ff(self):
        """$A2FF: tactical helper a2ff; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA2FF)
        m[0x0021]=r.a
        return (yield from self.plan_two_axis_movement())

    def tactical_helper_a314(self):
        """$A314: tactical helper a314; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA314)
        self._a(m[(UNIT_X+r.x)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.x)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA31F)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a323())

    def tactical_helper_a323(self):
        """$A323: tactical helper a323; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA323)
        m[0x0021]=r.a
        return (yield from self.plan_two_axis_movement())

    def strategy_05_resupply(self):
        """$A329: strategy 05 resupply; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA329)
        self._y(0x31)
        yield from self._external(0xA32B,0xF266,0xA32E,"call",None)
        if r.pc!=0xA32E:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0020]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0020])
        self._y(r.a)
        self._a(m[(0x9BA4+r.y)&65535])
        m[0x0020]=r.a
        self._y(r.y+1)
        self._a(m[(0x9BA4+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA347)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a34b())

    def tactical_helper_a34b(self):
        """$A34B: tactical helper a34b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA34B)
        m[0x0021]=r.a
        if not (yield from self._local_call(self.plan_two_axis_movement,0xA34E,0xA351)):return
        self._a(m[PROPOSAL_STATUS])
        yield from self._checkpoint(0xA354)
        if not r.p&Z:
            return (yield from self.tactical_helper_a3ad())
        else:
            self._y(m[ACTOR_SLOT])
            self._a(m[(UNIT_X+r.y)&65535])
            m[0x0020]=r.a
            self._a(m[(UNIT_Y+r.y)&65535])
            m[0x0021]=r.a
            self._y(0x00)
            self._a(m[PROPOSAL_ACTION])
            self._a(r.a & 0x02)
            yield from self._checkpoint(0xA36C)
            if not r.p&Z:
                pass
            else:
                self._y(r.y+1)
                pass
            return (yield from self.tactical_helper_a36f())

    def tactical_helper_a36f(self):
        """$A36F: tactical helper a36f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA36F)
        self._a(m[PROPOSAL_ACTION])
        self._a(r.a & 0x01)
        yield from self._checkpoint(0xA374)
        if r.p&Z:
            self._a(0xFF)
            pass
        else:
            self._a(0x01)
            pass
        return (yield from self.tactical_helper_a37d())

    def tactical_helper_a37d(self):
        """$A37D: tactical helper a37d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA37D)
        m[0x0022]=r.a
        self._a(m[(0x0020+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0022])
        m[(0x0020+r.y)&65535]=r.a
        self._y(0x31)
        yield from self._external(0xA38C,0xF266,0xA38F,"call",None)
        if r.pc!=0xA38F:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0022]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0022])
        self._y(r.a)
        self._a(m[(0x9BA4+r.y)&65535])
        self._compare(r.a,m[0x0020])
        yield from self._checkpoint(0xA3A2)
        if not r.p&Z:
            return (yield from self.tactical_helper_a3ad())
        else:
            self._y(r.y+1)
            self._a(m[(0x9BA4+r.y)&65535])
            self._compare(r.a,m[0x0021])
            yield from self._checkpoint(0xA3AB)
            if r.p&Z:
                self._y(m[ACTOR_SLOT])
                self._a(m[(UNIT_STRATEGY+r.y)&65535])
                self._a(r.a & 0xF0)
                self._a(r.a | 0x07)
                m[(UNIT_STRATEGY+r.y)&65535]=r.a
                self._x(0x00)
                self._a(m[SIDE])
                yield from self._checkpoint(0xA3C0)
                if not r.p&N:
                    pass
                else:
                    self._x(0x02)
                    pass
                return (yield from self.tactical_helper_a3c4())
            else:
                return (yield from self.tactical_helper_a3ad())

    def tactical_helper_a3ad(self):
        """$A3AD: tactical helper a3ad; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA3AD)
        self._rts();return

    def tactical_helper_a3c4(self):
        """$A3C4: tactical helper a3c4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA3C4)
        self._a(m[(0x0526+r.x)&65535])
        m[0x0020]=r.a
        self._a(m[(0x0527+r.x)&65535])
        m[0x0021]=r.a
        self._a(0x00)
        m[0x0022]=r.a
        self._a(0x07)
        m[0x0023]=r.a
        if not (yield from self._local_call(self.multiply_u24_by_u8,0xA3DA,0xA3DD)):return
        self._a(m[0x0026])
        m[0x0020]=r.a
        self._a(m[0x0027])
        m[0x0021]=r.a
        self._a(m[0x0028])
        m[0x0022]=r.a
        self._a(0x0A)
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_u24_by_u16,0xA3F9,0xA3FC)):return
        self._a(m[0x0020])
        m[0x0036]=r.a
        self._a(m[0x0021])
        m[0x0037]=r.a
        if not (yield from self._local_call(self.tactical_helper_b0b8,0xA408,0xA40B)):return
        self._x(0x00)
        self._a(m[SIDE])
        yield from self._checkpoint(0xA410)
        if not r.p&N:
            pass
        else:
            self._x(0x02)
            pass
        return (yield from self.tactical_helper_a414())

    def tactical_helper_a414(self):
        """$A414: tactical helper a414; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA414)
        self._a(m[0x002A])
        self._flag(C,True)
        self._add(m[(0x0522+r.x)&65535],subtract=True)
        m[0x0038]=r.a
        m[0x0020]=r.a
        self._a(m[0x002B])
        self._add(m[(0x0523+r.x)&65535],subtract=True)
        m[0x0039]=r.a
        m[0x0021]=r.a
        self._a(0x00)
        m[0x0022]=r.a
        self._a(0x64)
        m[0x0023]=r.a
        if not (yield from self._local_call(self.multiply_u24_by_u8,0xA437,0xA43A)):return
        self._a(m[0x0026])
        m[0x0020]=r.a
        self._a(m[0x0027])
        m[0x0021]=r.a
        self._a(m[0x0028])
        m[0x0022]=r.a
        self._y(0x30)
        yield from self._external(0xA44E,0xF266,0xA451,"call",None)
        if r.pc!=0xA451:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._y(r.y+1)
        self._a(m[(0x8FC0+r.y)&65535])
        m[0x003A]=r.a
        m[0x0023]=r.a
        self._a(0x00)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_u24_by_u16,0xA465,0xA468)):return
        self._x(0x00)
        self._a(m[SIDE])
        yield from self._checkpoint(0xA46D)
        if not r.p&N:
            pass
        else:
            self._x(0x02)
            pass
        return (yield from self.tactical_helper_a471())

    def tactical_helper_a471(self):
        """$A471: tactical helper a471; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA471)
        self._a(m[0x0036])
        self._flag(C,True)
        self._add(m[0x0020],subtract=True)
        self._a(m[0x0037])
        self._add(m[0x0021],subtract=True)
        yield from self._checkpoint(0xA47E)
        if not r.p&C:
            self._a(m[0x0036])
            m[0x0020]=r.a
            self._a(m[0x0037])
            m[0x0021]=r.a
            self._a(0x00)
            m[0x0022]=r.a
            self._a(m[0x003A])
            m[0x0023]=r.a
            if not (yield from self._local_call(self.multiply_u24_by_u8,0xA4BE,0xA4C1)):return
            self._a(m[0x0026])
            m[0x0020]=r.a
            self._a(m[0x0027])
            m[0x0021]=r.a
            self._a(m[0x0028])
            m[0x0022]=r.a
            self._a(0x00)
            m[0x0024]=r.a
            self._a(0x64)
            m[0x0023]=r.a
            if not (yield from self._local_call(self.divide_u24_by_u16,0xA4DD,0xA4E0)):return
            self._a(m[(0x0526+r.x)&65535])
            self._flag(C,True)
            self._add(m[0x0036],subtract=True)
            m[(0x0526+r.x)&65535]=r.a
            self._a(m[(0x0527+r.x)&65535])
            self._add(m[0x0037],subtract=True)
            m[(0x0527+r.x)&65535]=r.a
            self._a(m[(0x0522+r.x)&65535])
            self._flag(C,False)
            self._add(m[0x0020])
            m[(0x0522+r.x)&65535]=r.a
            self._a(m[(0x0523+r.x)&65535])
            self._add(m[0x0021])
            m[(0x0523+r.x)&65535]=r.a
            yield from self._checkpoint(0xA506)
            self._rts();return
        else:
            self._a(m[(0x0526+r.x)&65535])
            self._flag(C,True)
            self._add(m[0x0020],subtract=True)
            m[(0x0526+r.x)&65535]=r.a
            self._a(m[(0x0527+r.x)&65535])
            self._add(m[0x0021],subtract=True)
            m[(0x0527+r.x)&65535]=r.a
            self._a(m[(0x0522+r.x)&65535])
            self._flag(C,False)
            self._add(m[0x0038])
            m[(0x0522+r.x)&65535]=r.a
            self._a(m[(0x0523+r.x)&65535])
            self._add(m[0x0039])
            m[(0x0523+r.x)&65535]=r.a
            yield from self._checkpoint(0xA4A6)
            self._rts();return

    def strategy_06_heal(self):
        """$A507: strategy 06 heal; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA507)
        self._y(0x31)
        yield from self._external(0xA509,0xF266,0xA50C,"call",None)
        if r.pc!=0xA50C:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0020]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0020])
        self._flag(C,False)
        self._add(0x04)
        self._y(r.a)
        self._a(m[(0x9BA4+r.y)&65535])
        m[0x0020]=r.a
        self._y(r.y+1)
        self._a(m[(0x9BA4+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA528)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a52c())

    def tactical_helper_a52c(self):
        """$A52C: tactical helper a52c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA52C)
        m[0x0021]=r.a
        m[0x0021]=r.a
        if not (yield from self._local_call(self.plan_two_axis_movement,0xA532,0xA535)):return
        self._a(m[PROPOSAL_STATUS])
        yield from self._checkpoint(0xA538)
        if not r.p&Z:
            return (yield from self.tactical_helper_a594())
        else:
            self._y(m[ACTOR_SLOT])
            self._a(m[(UNIT_X+r.y)&65535])
            m[0x0020]=r.a
            self._a(m[(UNIT_Y+r.y)&65535])
            m[0x0021]=r.a
            self._y(0x00)
            self._a(m[PROPOSAL_ACTION])
            self._a(r.a & 0x02)
            yield from self._checkpoint(0xA550)
            if not r.p&Z:
                pass
            else:
                self._y(r.y+1)
                pass
            return (yield from self.tactical_helper_a553())

    def tactical_helper_a553(self):
        """$A553: tactical helper a553; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA553)
        self._a(m[PROPOSAL_ACTION])
        self._a(r.a & 0x01)
        yield from self._checkpoint(0xA558)
        if r.p&Z:
            self._a(0xFF)
            pass
        else:
            self._a(0x01)
            pass
        return (yield from self.tactical_helper_a561())

    def tactical_helper_a561(self):
        """$A561: tactical helper a561; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA561)
        m[0x0022]=r.a
        self._a(m[(0x0020+r.y)&65535])
        self._flag(C,False)
        self._add(m[0x0022])
        m[(0x0020+r.y)&65535]=r.a
        self._y(0x31)
        yield from self._external(0xA570,0xF266,0xA573,"call",None)
        if r.pc!=0xA573:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        m[0x0022]=r.a
        r.a=self._shift(r.a,True,rotate=False)
        self._flag(C,False)
        self._add(m[0x0022])
        self._flag(C,False)
        self._add(0x04)
        self._y(r.a)
        self._a(m[(0x9BA4+r.y)&65535])
        self._compare(r.a,m[0x0020])
        yield from self._checkpoint(0xA589)
        if not r.p&Z:
            return (yield from self.tactical_helper_a594())
        else:
            self._y(r.y+1)
            self._a(m[(0x9BA4+r.y)&65535])
            self._compare(r.a,m[0x0021])
            yield from self._checkpoint(0xA592)
            if r.p&Z:
                self._y(m[ACTOR_SLOT])
                self._a(m[(UNIT_STRATEGY+r.y)&65535])
                self._a(r.a & 0xF0)
                self._a(r.a | 0x07)
                m[(UNIT_STRATEGY+r.y)&65535]=r.a
                self._x(0x00)
                self._a(m[SIDE])
                yield from self._checkpoint(0xA5A7)
                if not r.p&N:
                    pass
                else:
                    self._x(0x02)
                    pass
                return (yield from self.tactical_helper_a5ab())
            else:
                return (yield from self.tactical_helper_a594())

    def tactical_helper_a594(self):
        """$A594: tactical helper a594; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA594)
        self._rts();return

    def tactical_helper_a5ab(self):
        """$A5AB: tactical helper a5ab; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA5AB)
        self._a(m[(0x0527+r.x)&65535])
        yield from self._checkpoint(0xA5AE)
        if not r.p&Z:
            return (yield from self.tactical_helper_a5b8())
        else:
            self._a(m[(0x0526+r.x)&65535])
            self._compare(r.a,0x32)
            yield from self._checkpoint(0xA5B5)
            if r.p&C:
                return (yield from self.tactical_helper_a5b8())
            else:
                yield from self._checkpoint(0xA5B7)
                self._rts();return

    def tactical_helper_a5b8(self):
        """$A5B8: tactical helper a5b8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA5B8)
        self._a(m[(0x0526+r.x)&65535])
        self._flag(C,True)
        self._add(0x32,subtract=True)
        m[(0x0526+r.x)&65535]=r.a
        self._a(m[(0x0527+r.x)&65535])
        self._add(0x00,subtract=True)
        m[(0x0527+r.x)&65535]=r.a
        while True:  # natural loop $A5C9
            try:
                if not (yield from self._local_call(self.draw_ai_rng_byte,0xA5C9,0xA5CC)):return
                self._a(r.a & 0x0F)
                self._compare(r.a,0x0B)
                yield from self._checkpoint(0xA5D0)
                if r.p&C:
                    continue
                else:
                    pass
                self._flag(C,False)
                self._add(0x23)
                m[0x002A]=r.a
                self._y(m[ACTOR_SLOT])
                self._a(m[(UNIT_IDS+r.y)&65535])
                m[0x002C]=r.a
                if not (yield from self._local_call(self.initial_officer_record_pointer,0xA5E1,0xA5E4)):return
                self._y(0x00)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                m[0x002B]=r.a
                self._a(m[0x002C])
                if not (yield from self._local_call(self.tactical_helper_b491,0xA5EE,0xA5F1)):return
                self._y(0x00)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._flag(C,False)
                self._add(m[0x002A])
                m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                self._compare(r.a,m[0x002B])
                yield from self._checkpoint(0xA5FE)
                if not r.p&C:
                    pass
                else:
                    self._a(m[0x002B])
                    m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
                    pass
                return (yield from self.tactical_helper_a605())
            except _ContinueLoop_A5C9:
                continue

    def tactical_helper_a605(self):
        """$A605: tactical helper a605; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA605)
        self._rts();return

    def strategy_07_no_action(self):
        """$A606: strategy 07 no action; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA606)
        self._a(0x03)
        m[PROPOSAL_STATUS]=r.a
        yield from self._checkpoint(0xA60B)
        self._rts();return

    def plan_two_axis_movement(self):
        """$A60C: plan two axis movement; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA60C)
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.find_orthogonal_neighbors,0xA60F,0xA612)):return
        self._y(m[ACTOR_SLOT])
        self._a(m[0x0020])
        self._flag(C,True)
        self._add(m[(UNIT_X+r.y)&65535],subtract=True)
        m[0x0020]=r.a
        yield from self._checkpoint(0xA61F)
        if not r.p&N:
            pass
        else:
            self._a(r.a ^ 0xFF)
            self._flag(C,False)
            self._add(0x01)
            pass
        return (yield from self.tactical_helper_a626())

    def tactical_helper_a626(self):
        """$A626: tactical helper a626; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA626)
        m[0x0022]=r.a
        self._a(m[(UNIT_Y+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA62E)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a633())

    def tactical_helper_a633(self):
        """$A633: tactical helper a633; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA633)
        m[0x0023]=r.a
        self._a(m[0x0021])
        self._flag(C,True)
        self._add(m[0x0023],subtract=True)
        m[0x0021]=r.a
        yield from self._checkpoint(0xA640)
        if not r.p&N:
            pass
        else:
            self._a(r.a ^ 0xFF)
            self._flag(C,False)
            self._add(0x01)
            pass
        return (yield from self.tactical_helper_a647())

    def tactical_helper_a647(self):
        """$A647: tactical helper a647; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA647)
        m[0x0023]=r.a
        self._y(0x00)
        self._a(m[0x0023])
        self._compare(r.a,m[0x0022])
        yield from self._checkpoint(0xA652)
        if r.p&C:
            if not (yield from self._local_call(self.tactical_helper_a733,0xA660,0xA663)):return
            self._y(r.y+1)
            if not (yield from self._local_call(self.tactical_helper_a728,0xA664,0xA667)):return
            self._y(0x00)
            pass
        else:
            if not (yield from self._local_call(self.tactical_helper_a728,0xA654,0xA657)):return
            self._y(r.y+1)
            if not (yield from self._local_call(self.tactical_helper_a733,0xA658,0xA65B)):return
            self._y(0x01)
            pass
        return (yield from self.tactical_helper_a669())

    def tactical_helper_a669(self):
        """$A669: tactical helper a669; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA669)
        self._a(m[(0x0022+r.y)&65535])
        yield from self._checkpoint(0xA66C)
        if not r.p&Z:
            pass
        else:
            self._a(0xFF)
            m[0x002B]=r.a
            self._a(r.y)
            self._a(r.a ^ 0x01)
            self._y(r.a)
            self._a(m[(0x0022+r.y)&65535])
            self._compare(r.a,0x01)
            yield from self._checkpoint(0xA67C)
            if not r.p&Z:
                pass
            else:
                pass
            pass
        return (yield from self.tactical_helper_a67e())

    def tactical_helper_a67e(self):
        """$A67E: tactical helper a67e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA67E)
        self._y(0x00)
        while True:  # natural loop $A680
            try:
                self._a(m[(0x002A+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xA685)
                if r.p&Z:
                    pass
                else:
                    self._x(r.a)
                    self._a(r.y)
                    self._push(r.a)
                    if not (yield from self._local_call(self.quote_direction_ap_cost,0xA68A,0xA68D)):return
                    yield from self._checkpoint(0xA68D)
                    if r.p&C:
                        pass
                    else:
                        self._y(0x0F)
                        pass
                    self._a(r.y)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    m[0x0022]=r.a
                    self._a(self._pop())
                    self._y(r.a)
                    self._a(m[(0x002A+r.y)&65535])
                    self._a(r.a | m[0x0022])
                    m[(0x002A+r.y)&65535]=r.a
                    self._a(m[0x0022])
                    pass
                m[(0x002C+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x02)
                yield from self._checkpoint(0xA6AD)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x002C])
                self._compare(r.a,m[0x002D])
                yield from self._checkpoint(0xA6B5)
                if r.p&Z:
                    pass
                else:
                    yield from self._checkpoint(0xA6B7)
                    if not r.p&C:
                        pass
                    else:
                        self._a(m[0x002B])
                        self._x(r.a)
                        self._a(m[0x002A])
                        m[0x002B]=r.a
                        self._a(r.x)
                        m[0x002A]=r.a
                        pass
                    pass
                return (yield from self.tactical_helper_a6c7())
            except _ContinueLoop_A680:
                continue

    def tactical_helper_a6c7(self):
        """$A6C7: tactical helper a6c7; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA6C7)
        self._y(m[ACTOR_SLOT])
        self._a(m[(0x6FB5+r.y)&65535])
        m[0x002F]=r.a
        self._y(0x00)
        while True:  # natural loop $A6D2
            try:
                self._a(m[(0x002A+r.y)&65535])
                self._compare(r.a,0xF0)
                yield from self._checkpoint(0xA6D7)
                if r.p&C:
                    self._y(r.y+1)
                    self._compare(r.y,0x02)
                    yield from self._checkpoint(0xA6E9)
                    if not r.p&C:
                        continue
                    else:
                        self._y(m[ACTOR_SLOT])
                        self._a(m[(UNIT_STRATEGY+r.y)&65535])
                        self._compare(r.a,0x01)
                        yield from self._checkpoint(0xA6F3)
                        if r.p&Z:
                            return (yield from self.tactical_helper_a6ff())
                        else:
                            self._compare(r.a,0x05)
                            yield from self._checkpoint(0xA6F7)
                            if r.p&Z:
                                return (yield from self.tactical_helper_a6ff())
                            else:
                                return (yield from self.tactical_helper_a6f9())
                else:
                    m[0x0020]=r.a
                    self._a(r.a & 0x0F)
                    self._x(r.a)
                    self._a(m[(0x6FDD+r.x)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xA6E4)
                    if r.p&Z:
                        self._y(m[ACTOR_SLOT])
                        self._a(m[(0x0650+r.y)&65535])
                        yield from self._checkpoint(0xA708)
                        if not r.p&Z:
                            return (yield from self.tactical_helper_a6f9())
                        else:
                            m[PROPOSAL_ACTION]=r.x
                            self._a(0x00)
                            m[PROPOSAL_STATUS]=r.a
                            self._a(m[0x0020])
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            r.a=self._shift(r.a,False,rotate=False)
                            m[MOVE_COST]=r.a
                            self._y(m[ACTOR_SLOT])
                            self._a(m[PROPOSAL_ACTION])
                            self._a(r.a ^ 0x01)
                            m[(0x6FB5+r.y)&65535]=r.a
                            yield from self._checkpoint(0xA727)
                            self._rts();return
                    else:
                        self._y(r.y+1)
                        self._compare(r.y,0x02)
                        yield from self._checkpoint(0xA6E9)
                        if not r.p&C:
                            continue
                        else:
                            self._y(m[ACTOR_SLOT])
                            self._a(m[(UNIT_STRATEGY+r.y)&65535])
                            self._compare(r.a,0x01)
                            yield from self._checkpoint(0xA6F3)
                            if r.p&Z:
                                return (yield from self.tactical_helper_a6ff())
                            else:
                                self._compare(r.a,0x05)
                                yield from self._checkpoint(0xA6F7)
                                if r.p&Z:
                                    return (yield from self.tactical_helper_a6ff())
                                else:
                                    return (yield from self.tactical_helper_a6f9())
            except _ContinueLoop_A6D2:
                continue

    def tactical_helper_a6f9(self):
        """$A6F9: tactical helper a6f9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA6F9)
        self._a(0x03)
        m[PROPOSAL_STATUS]=r.a
        yield from self._checkpoint(0xA6FE)
        self._rts();return

    def tactical_helper_a6ff(self):
        """$A6FF: tactical helper a6ff; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA6FF)
        self._y(0x00)
        while True:  # natural loop $A807
            try:
                self._a(m[(0x002A+r.y)&65535])
                self._compare(r.a,0xF0)
                yield from self._checkpoint(0xA80C)
                if r.p&C:
                    self._y(r.y+1)
                    self._compare(r.y,0x02)
                    yield from self._checkpoint(0xA82F)
                    if not r.p&C:
                        continue
                    else:
                        self._a(0x03)
                        m[PROPOSAL_STATUS]=r.a
                        yield from self._checkpoint(0xA836)
                        self._rts();return
                else:
                    self._a(r.a & 0x0F)
                    self._x(r.a)
                    self._a(m[(0x6FDD+r.x)&65535])
                    yield from self._checkpoint(0xA814)
                    if not r.p&N:
                        self._y(r.y+1)
                        self._compare(r.y,0x02)
                        yield from self._checkpoint(0xA82F)
                        if not r.p&C:
                            continue
                        else:
                            self._a(0x03)
                            m[PROPOSAL_STATUS]=r.a
                            yield from self._checkpoint(0xA836)
                            self._rts();return
                    else:
                        self._compare(r.a,0xFF)
                        yield from self._checkpoint(0xA818)
                        if r.p&Z:
                            self._y(r.y+1)
                            self._compare(r.y,0x02)
                            yield from self._checkpoint(0xA82F)
                            if not r.p&C:
                                continue
                            else:
                                self._a(0x03)
                                m[PROPOSAL_STATUS]=r.a
                                yield from self._checkpoint(0xA836)
                                self._rts();return
                        else:
                            self._a(r.a & 0x7F)
                            m[PROPOSAL_ACTION]=r.a
                            self._a(m[AP])
                            self._compare(r.a,0x02)
                            yield from self._checkpoint(0xA824)
                            if not r.p&C:
                                self._y(r.y+1)
                                self._compare(r.y,0x02)
                                yield from self._checkpoint(0xA82F)
                                if not r.p&C:
                                    continue
                                else:
                                    self._a(0x03)
                                    m[PROPOSAL_STATUS]=r.a
                                    yield from self._checkpoint(0xA836)
                                    self._rts();return
                            else:
                                self._a(0x01)
                                m[PROPOSAL_STATUS]=r.a
                                yield from self._checkpoint(0xA82B)
                                self._rts();return
            except _ContinueLoop_A807:
                continue

    def tactical_helper_a728(self):
        """$A728: tactical helper a728; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA728)
        self._x(0x02)
        self._a(m[0x0020])
        yield from self._checkpoint(0xA72D)
        if r.p&N:
            pass
        else:
            self._x(r.x+1)
            pass
        return (yield from self.tactical_helper_a73b())

    def tactical_helper_a733(self):
        """$A733: tactical helper a733; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA733)
        self._x(0x00)
        self._a(m[0x0021])
        yield from self._checkpoint(0xA738)
        if r.p&N:
            pass
        else:
            self._x(r.x+1)
            pass
        return (yield from self.tactical_helper_a73b())

    def tactical_helper_a73b(self):
        """$A73B: tactical helper a73b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA73B)
        self._a(r.x)
        m[(0x002A+r.y)&65535]=r.a
        yield from self._checkpoint(0xA73F)
        self._rts();return

    def quote_direction_ap_cost(self):
        """$A740: quote direction ap cost; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA740)
        self._a(0x00)
        m[0x0020]=r.a
        m[0x0021]=r.a
        self._a(0x01)
        m[0x0022]=r.a
        self._a(r.x)
        self._a(r.a & 0x01)
        yield from self._checkpoint(0xA750)
        if not r.p&Z:
            pass
        else:
            self._a(0xFF)
            m[0x0022]=r.a
            pass
        return (yield from self.tactical_helper_a757())

    def tactical_helper_a757(self):
        """$A757: tactical helper a757; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA757)
        self._a(r.x)
        r.a=self._shift(r.a,False,rotate=False)
        self._a(r.a & 0x01)
        self._a(r.a ^ 0x01)
        self._x(r.a)
        self._a(m[0x0022])
        m[(0x0020+r.x)&65535]=r.a
        self._x(m[ACTOR_SLOT])
        self._a(m[(UNIT_X+r.x)&65535])
        self._flag(C,False)
        self._add(m[0x0020])
        m[0x0020]=r.a
        yield from self._checkpoint(0xA771)
        if r.p&N:
            return (yield from self.tactical_helper_a777())
        else:
            self._compare(r.a,0x1F)
            yield from self._checkpoint(0xA775)
            if not r.p&C:
                self._a(m[(UNIT_Y+r.x)&65535])
                self._flag(C,False)
                self._add(m[0x0021])
                m[0x0021]=r.a
                yield from self._checkpoint(0xA783)
                if r.p&N:
                    return (yield from self.tactical_helper_a777())
                else:
                    self._compare(r.a,0x14)
                    yield from self._checkpoint(0xA787)
                    if r.p&C:
                        return (yield from self.tactical_helper_a777())
                    else:
                        if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xA789,0xA78C)):return
                        self._push(r.a)
                        self._y(m[ACTOR_SLOT])
                        self._a(m[(UNIT_IDS+r.y)&65535])
                        if not (yield from self._local_call(self.tactical_helper_b491,0xA793,0xA796)):return
                        self._y(0x0B)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._a(r.a & 0x03)
                        m[0x0022]=r.a
                        self._a(self._pop())
                        r.a=self._shift(r.a,True,rotate=False)
                        r.a=self._shift(r.a,True,rotate=False)
                        self._a(r.a | m[0x0022])
                        self._x(r.a)
                        self._y(0x08)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._flag(C,True)
                        self._add(0x59,subtract=True)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._add(0x02,subtract=True)
                        yield from self._checkpoint(0xA7B3)
                        if not r.p&C:
                            self._a(m[(0xA7E9+r.x)&65535])
                            self._y(r.a)
                            self._a(m[AP])
                            self._flag(C,True)
                            self._add(m[(0xA7E9+r.x)&65535],subtract=True)
                            yield from self._checkpoint(0xA7CC)
                            self._rts();return
                        else:
                            self._a(m[(0xA7CD+r.x)&65535])
                            self._y(r.a)
                            self._a(m[AP])
                            self._flag(C,True)
                            self._add(m[(0xA7CD+r.x)&65535],subtract=True)
                            yield from self._checkpoint(0xA7C0)
                            self._rts();return
            else:
                return (yield from self.tactical_helper_a777())

    def tactical_helper_a777(self):
        """$A777: tactical helper a777; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA777)
        self._flag(C,False)
        yield from self._checkpoint(0xA778)
        self._rts();return

    def find_orthogonal_neighbors(self):
        """$A837: find orthogonal neighbors; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA837)
        self._a(m[(UNIT_X+r.y)&65535])
        m[0x0022]=r.a
        self._a(m[(UNIT_Y+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA842)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a847())

    def tactical_helper_a847(self):
        """$A847: tactical helper a847; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA847)
        m[0x0023]=r.a
        m[0x0023]=self._nz(m[0x0023]-1)
        self._x(0x00)
        if not (yield from self._local_call(self.tactical_helper_a871,0xA84F,0xA852)):return
        m[0x0023]=self._nz(m[0x0023]+1)
        m[0x0023]=self._nz(m[0x0023]+1)
        self._x(r.x+1)
        if not (yield from self._local_call(self.tactical_helper_a871,0xA859,0xA85C)):return
        m[0x0023]=self._nz(m[0x0023]-1)
        m[0x0022]=self._nz(m[0x0022]-1)
        self._x(r.x+1)
        if not (yield from self._local_call(self.tactical_helper_a871,0xA863,0xA866)):return
        m[0x0022]=self._nz(m[0x0022]+1)
        m[0x0022]=self._nz(m[0x0022]+1)
        self._x(r.x+1)
        if not (yield from self._local_call(self.tactical_helper_a871,0xA86D,0xA870)):return
        yield from self._checkpoint(0xA870)
        self._rts();return

    def tactical_helper_a871(self):
        """$A871: tactical helper a871; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA871)
        self._y(0x00)
        while True:  # natural loop $A873
            try:
                self._a(m[(UNIT_IDS+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xA878)
                if r.p&Z:
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    yield from self._checkpoint(0xA8A0)
                    if not r.p&C:
                        continue
                    else:
                        self._a(0xFF)
                        m[(0x6FDD+r.x)&65535]=r.a
                        yield from self._checkpoint(0xA8A7)
                        self._rts();return
                else:
                    self._a(m[(UNIT_X+r.y)&65535])
                    self._compare(r.a,m[0x0022])
                    yield from self._checkpoint(0xA880)
                    if not r.p&Z:
                        self._y(r.y+1)
                        self._compare(r.y,0x14)
                        yield from self._checkpoint(0xA8A0)
                        if not r.p&C:
                            continue
                        else:
                            self._a(0xFF)
                            m[(0x6FDD+r.x)&65535]=r.a
                            yield from self._checkpoint(0xA8A7)
                            self._rts();return
                    else:
                        self._a(m[(UNIT_Y+r.y)&65535])
                        self._compare(r.a,0x10)
                        yield from self._checkpoint(0xA887)
                        if not r.p&C:
                            pass
                        else:
                            self._add(0x01,subtract=True)
                            pass
                        self._compare(r.a,m[0x0023])
                        yield from self._checkpoint(0xA88E)
                        if not r.p&Z:
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            yield from self._checkpoint(0xA8A0)
                            if not r.p&C:
                                continue
                            else:
                                self._a(0xFF)
                                m[(0x6FDD+r.x)&65535]=r.a
                                yield from self._checkpoint(0xA8A7)
                                self._rts();return
                        else:
                            m[0x0024]=r.y
                            if not (yield from self._local_call(self.opposing_side_marker,0xA893,0xA896)):return
                            self._a(r.a | m[0x0024])
                            m[(0x6FDD+r.x)&65535]=r.a
                            yield from self._checkpoint(0xA89C)
                            self._rts();return
            except _ContinueLoop_A873:
                continue

    def propose_adjacent_attack(self):
        """$A8A8: propose adjacent attack; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA8A8)
        self._a(m[AP])
        self._compare(r.a,0x02)
        yield from self._checkpoint(0xA8AD)
        if not r.p&C:
            return (yield from self.tactical_helper_a8d1())
        else:
            self._y(m[ACTOR_SLOT])
            if not (yield from self._local_call(self.find_orthogonal_neighbors,0xA8B2,0xA8B5)):return
            self._x(0x00)
            while True:  # natural loop $A8B7
                try:
                    self._a(m[(0x6FDD+r.x)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xA8BC)
                    if r.p&Z:
                        self._x(r.x+1)
                        self._compare(r.x,0x04)
                        yield from self._checkpoint(0xA8CF)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_a8d1())
                    else:
                        yield from self._checkpoint(0xA8BE)
                        if not r.p&N:
                            self._x(r.x+1)
                            self._compare(r.x,0x04)
                            yield from self._checkpoint(0xA8CF)
                            if not r.p&C:
                                continue
                            else:
                                return (yield from self.tactical_helper_a8d1())
                        else:
                            self._a(r.a & 0x7F)
                            m[PROPOSAL_ACTION]=r.a
                            self._a(0x01)
                            m[PROPOSAL_STATUS]=r.a
                            self._flag(C,True)
                            yield from self._checkpoint(0xA8CB)
                            self._rts();return
                except _ContinueLoop_A8B7:
                    continue

    def tactical_helper_a8d1(self):
        """$A8D1: tactical helper a8d1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA8D1)
        self._flag(C,False)
        yield from self._checkpoint(0xA8D2)
        self._rts();return

    def tactical_helper_a8d3(self):
        """$A8D3: tactical helper a8d3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA8D3)
        m[0x0022]=r.a
        self._a(m[(UNIT_X+r.y)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.y)&65535])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xA8E1)
        if not r.p&C:
            pass
        else:
            self._add(0x01,subtract=True)
            pass
        return (yield from self.tactical_helper_a8e5())

    def tactical_helper_a8e5(self):
        """$A8E5: tactical helper a8e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA8E5)
        m[0x0021]=r.a
        return (yield from self.tactical_helper_a8e8())

    def tactical_helper_a8e8(self):
        """$A8E8: tactical helper a8e8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA8E8)
        self._y(0x00)
        while True:  # natural loop $A8EA
            try:
                self._a(0x00)
                m[(0x6FC9+r.y)&65535]=r.a
                self._a(m[(UNIT_IDS+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xA8F4)
                if r.p&Z:
                    pass
                else:
                    self._a(m[(UNIT_X+r.y)&65535])
                    self._flag(C,True)
                    self._add(m[0x0020],subtract=True)
                    yield from self._checkpoint(0xA8FD)
                    if not r.p&N:
                        pass
                    else:
                        self._a(r.a ^ 0xFF)
                        self._flag(C,False)
                        self._add(0x01)
                        pass
                    self._compare(r.a,m[0x0022])
                    yield from self._checkpoint(0xA907)
                    if r.p&Z:
                        m[0x0023]=r.a
                        self._a(m[(UNIT_Y+r.y)&65535])
                        self._compare(r.a,0x10)
                        yield from self._checkpoint(0xA916)
                        if not r.p&C:
                            pass
                        else:
                            self._add(0x01,subtract=True)
                            pass
                        self._flag(C,True)
                        self._add(m[0x0021],subtract=True)
                        yield from self._checkpoint(0xA91E)
                        if not r.p&N:
                            pass
                        else:
                            self._a(r.a ^ 0xFF)
                            self._flag(C,False)
                            self._add(0x01)
                            pass
                        self._compare(r.a,m[0x0022])
                        yield from self._checkpoint(0xA928)
                        if r.p&Z:
                            self._add(m[0x0023])
                            m[0x0023]=r.a
                            if not (yield from self._local_call(self.opposing_side_marker,0xA935,0xA938)):return
                            self._a(r.a | m[0x0023])
                            m[(0x6FC9+r.y)&65535]=r.a
                            pass
                        else:
                            yield from self._checkpoint(0xA92A)
                            if not r.p&C:
                                self._add(m[0x0023])
                                m[0x0023]=r.a
                                if not (yield from self._local_call(self.opposing_side_marker,0xA935,0xA938)):return
                                self._a(r.a | m[0x0023])
                                m[(0x6FC9+r.y)&65535]=r.a
                                pass
                            else:
                                pass
                            pass
                        pass
                    else:
                        yield from self._checkpoint(0xA909)
                        if not r.p&C:
                            m[0x0023]=r.a
                            self._a(m[(UNIT_Y+r.y)&65535])
                            self._compare(r.a,0x10)
                            yield from self._checkpoint(0xA916)
                            if not r.p&C:
                                pass
                            else:
                                self._add(0x01,subtract=True)
                                pass
                            self._flag(C,True)
                            self._add(m[0x0021],subtract=True)
                            yield from self._checkpoint(0xA91E)
                            if not r.p&N:
                                pass
                            else:
                                self._a(r.a ^ 0xFF)
                                self._flag(C,False)
                                self._add(0x01)
                                pass
                            self._compare(r.a,m[0x0022])
                            yield from self._checkpoint(0xA928)
                            if r.p&Z:
                                self._add(m[0x0023])
                                m[0x0023]=r.a
                                if not (yield from self._local_call(self.opposing_side_marker,0xA935,0xA938)):return
                                self._a(r.a | m[0x0023])
                                m[(0x6FC9+r.y)&65535]=r.a
                                pass
                            else:
                                yield from self._checkpoint(0xA92A)
                                if not r.p&C:
                                    self._add(m[0x0023])
                                    m[0x0023]=r.a
                                    if not (yield from self._local_call(self.opposing_side_marker,0xA935,0xA938)):return
                                    self._a(r.a | m[0x0023])
                                    m[(0x6FC9+r.y)&65535]=r.a
                                    pass
                                else:
                                    pass
                                pass
                            pass
                        else:
                            pass
                        pass
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                yield from self._checkpoint(0xA941)
                if not r.p&C:
                    continue
                else:
                    pass
                yield from self._checkpoint(0xA943)
                self._rts();return
            except _ContinueLoop_A8EA:
                continue

    def opposing_side_marker(self):
        """$A944: opposing side marker; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA944)
        self._a(m[SIDE])
        yield from self._checkpoint(0xA947)
        if r.p&N:
            self._a(m[(UNIT_CONDITION+r.y)&65535])
            yield from self._checkpoint(0xA954)
            if not r.p&N:
                return (yield from self.tactical_helper_a959())
            else:
                self._a(0x00)
                yield from self._checkpoint(0xA958)
                self._rts();return
        else:
            self._a(m[(UNIT_CONDITION+r.y)&65535])
            yield from self._checkpoint(0xA94C)
            if r.p&N:
                return (yield from self.tactical_helper_a959())
            else:
                self._a(0x00)
                yield from self._checkpoint(0xA950)
                self._rts();return

    def tactical_helper_a959(self):
        """$A959: tactical helper a959; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA959)
        self._a(0x80)
        yield from self._checkpoint(0xA95B)
        self._rts();return

    def choose_basic_tactic(self):
        """$A95C: choose basic tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA95C)
        self._y(m[ACTOR_SLOT])
        self._a(m[(UNIT_IDS+r.y)&65535])
        if not (yield from self._local_call(self.tactical_helper_b491,0xA962,0xA965)):return
        self._y(0x02)
        self._x(0x01)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._compare(r.a,0x28)
        yield from self._checkpoint(0xA96D)
        if not r.p&C:
            pass
        else:
            self._x(0x03)
            self._compare(r.a,0x3C)
            yield from self._checkpoint(0xA973)
            if not r.p&C:
                pass
            else:
                self._x(0x05)
                self._compare(r.a,0x4B)
                yield from self._checkpoint(0xA979)
                if not r.p&C:
                    pass
                else:
                    self._x(0x07)
                    self._compare(r.a,0x55)
                    yield from self._checkpoint(0xA97F)
                    if not r.p&C:
                        pass
                    else:
                        self._x(0x09)
                        pass
                    pass
                pass
            pass
        return (yield from self.tactical_helper_a983())

    def tactical_helper_a983(self):
        """$A983: tactical helper a983; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA983)
        m[0x002A]=r.x
        self._y(m[ACTOR_SLOT])
        self._a(0x05)
        if not (yield from self._local_call(self.tactical_helper_a8d3,0xA98B,0xA98E)):return
        if not (yield from self._local_call(self.rank_candidate_troops,0xA98E,0xA991)):return
        self._y(0x00)
        while True:  # natural loop $A993
            try:
                self._a(m[(0x6FC9+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xA998)
                if r.p&Z:
                    return (yield from self.tactical_helper_a9c8())
                else:
                    self._x(r.a)
                    self._a(m[(UNIT_IDS+r.x)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xA9A0)
                    if r.p&Z:
                        self._y(r.y+1)
                        self._compare(r.y,0x14)
                        yield from self._checkpoint(0xA9C6)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_a9c8())
                    else:
                        m[0x002B]=r.x
                        m[0x002F]=r.y
                        if not (yield from self._local_call(self.prioritize_basic_tactics,0xA9A8,0xA9AB)):return
                        yield from self._checkpoint(0xA9AB)
                        if not r.p&C:
                            self._y(m[0x002F])
                            self._y(r.y+1)
                            self._compare(r.y,0x14)
                            yield from self._checkpoint(0xA9C6)
                            if not r.p&C:
                                continue
                            else:
                                return (yield from self.tactical_helper_a9c8())
                        else:
                            self._a(m[0x002C])
                            m[PROPOSAL_ACTION]=r.a
                            self._a(m[0x002B])
                            m[PROPOSAL_TARGET]=r.a
                            self._a(0x02)
                            m[PROPOSAL_STATUS]=r.a
                            self._flag(C,True)
                            yield from self._checkpoint(0xA9BF)
                            self._rts();return
            except _ContinueLoop_A993:
                continue

    def tactical_helper_a9c8(self):
        """$A9C8: tactical helper a9c8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA9C8)
        self._a(0x03)
        m[PROPOSAL_STATUS]=r.a
        self._flag(C,False)
        yield from self._checkpoint(0xA9CE)
        self._rts();return

    def prioritize_basic_tactics(self):
        """$A9CF: prioritize basic tactics; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA9CF)
        self._y(m[0x002B])
        self._a(m[(UNIT_IDS+r.y)&65535])
        if not (yield from self._local_call(self.tactical_helper_b491,0xA9D5,0xA9D8)):return
        self._y(0x09)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        yield from self._checkpoint(0xA9DC)
        if not r.p&Z:
            pass
        else:
            self._y(r.y-1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            yield from self._checkpoint(0xA9E1)
            if not r.p&Z:
                pass
            else:
                self._a(0x00)
                pass
            pass
        return (yield from self.tactical_helper_a9e5())

    def tactical_helper_a9e5(self):
        """$A9E5: tactical helper a9e5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xA9E5)
        m[0x002D]=r.a
        self._a(m[0x002A])
        self._compare(r.a,0x06)
        yield from self._checkpoint(0xA9ED)
        if not r.p&C:
            return (yield from self.tactical_helper_aa03())
        else:
            self._a(m[0x002D])
            yield from self._checkpoint(0xA9F2)
            if r.p&Z:
                return (yield from self.tactical_helper_aa03())
            else:
                self._a(m[AP])
                self._compare(r.a,0x08)
                yield from self._checkpoint(0xA9F9)
                if not r.p&C:
                    return (yield from self.tactical_helper_aa03())
                else:
                    self._x(0x06)
                    if not (yield from self._local_call(self.check_tactic_target,0xA9FD,0xAA00)):return
                    yield from self._checkpoint(0xAA00)
                    if not r.p&C:
                        return (yield from self.tactical_helper_aa03())
                    else:
                        yield from self._checkpoint(0xAA02)
                        self._rts();return

    def tactical_helper_aa03(self):
        """$AA03: tactical helper aa03; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAA03)
        self._a(m[0x002A])
        self._compare(r.a,0x05)
        yield from self._checkpoint(0xAA08)
        if not r.p&C:
            return (yield from self.tactical_helper_aa19())
        else:
            self._a(m[AP])
            self._compare(r.a,0x08)
            yield from self._checkpoint(0xAA0F)
            if not r.p&C:
                return (yield from self.tactical_helper_aa19())
            else:
                self._x(0x05)
                if not (yield from self._local_call(self.check_tactic_target,0xAA13,0xAA16)):return
                yield from self._checkpoint(0xAA16)
                if not r.p&C:
                    return (yield from self.tactical_helper_aa19())
                else:
                    yield from self._checkpoint(0xAA18)
                    self._rts();return

    def tactical_helper_aa19(self):
        """$AA19: tactical helper aa19; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAA19)
        self._a(m[0x002A])
        self._compare(r.a,0x08)
        yield from self._checkpoint(0xAA1E)
        if not r.p&C:
            return (yield from self.tactical_helper_aa2f())
        else:
            self._a(m[AP])
            self._compare(r.a,0x0A)
            yield from self._checkpoint(0xAA25)
            if not r.p&C:
                return (yield from self.tactical_helper_aa2f())
            else:
                self._x(0x08)
                if not (yield from self._local_call(self.check_tactic_target,0xAA29,0xAA2C)):return
                yield from self._checkpoint(0xAA2C)
                if not r.p&C:
                    return (yield from self.tactical_helper_aa2f())
                else:
                    yield from self._checkpoint(0xAA2E)
                    self._rts();return

    def tactical_helper_aa2f(self):
        """$AA2F: tactical helper aa2f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAA2F)
        self._a(m[0x002A])
        self._compare(r.a,0x09)
        yield from self._checkpoint(0xAA34)
        if not r.p&C:
            return (yield from self.tactical_helper_aa4a())
        else:
            self._a(m[0x002D])
            yield from self._checkpoint(0xAA39)
            if r.p&Z:
                return (yield from self.tactical_helper_aa4a())
            else:
                self._a(m[AP])
                self._compare(r.a,0x09)
                yield from self._checkpoint(0xAA40)
                if not r.p&C:
                    return (yield from self.tactical_helper_aa4a())
                else:
                    self._x(0x09)
                    if not (yield from self._local_call(self.check_tactic_target,0xAA44,0xAA47)):return
                    yield from self._checkpoint(0xAA47)
                    if not r.p&C:
                        return (yield from self.tactical_helper_aa4a())
                    else:
                        yield from self._checkpoint(0xAA49)
                        self._rts();return

    def tactical_helper_aa4a(self):
        """$AA4A: tactical helper aa4a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAA4A)
        self._a(m[0x002A])
        self._compare(r.a,0x07)
        yield from self._checkpoint(0xAA4F)
        if not r.p&C:
            return (yield from self.tactical_helper_aa65())
        else:
            self._a(m[0x002D])
            yield from self._checkpoint(0xAA54)
            if r.p&Z:
                return (yield from self.tactical_helper_aa65())
            else:
                self._a(m[AP])
                self._compare(r.a,0x08)
                yield from self._checkpoint(0xAA5B)
                if not r.p&C:
                    return (yield from self.tactical_helper_aa65())
                else:
                    self._x(0x07)
                    if not (yield from self._local_call(self.check_tactic_target,0xAA5F,0xAA62)):return
                    yield from self._checkpoint(0xAA62)
                    if not r.p&C:
                        return (yield from self.tactical_helper_aa65())
                    else:
                        yield from self._checkpoint(0xAA64)
                        self._rts();return

    def tactical_helper_aa65(self):
        """$AA65: tactical helper aa65; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAA65)
        self._x(0x01)
        if not (yield from self._local_call(self.check_tactic_target,0xAA67,0xAA6A)):return
        yield from self._checkpoint(0xAA6A)
        if r.p&C:
            while True:  # natural loop $AA6F
                try:
                    if not (yield from self._local_call(self.draw_ai_rng_byte,0xAA6F,0xAA72)):return
                    self._a(r.a & 0x03)
                    yield from self._checkpoint(0xAA74)
                    if r.p&Z:
                        continue
                    else:
                        pass
                    self._compare(r.a,0x01)
                    yield from self._checkpoint(0xAA78)
                    if r.p&Z:
                        self._a(m[0x002A])
                        self._compare(r.a,0x02)
                        yield from self._checkpoint(0xAA9C)
                        if not r.p&C:
                            return (yield from self.tactical_helper_aac2())
                        else:
                            self._y(m[0x002B])
                            self._a(m[(0x0650+r.y)&65535])
                            self._a(r.a & 0x0F)
                            yield from self._checkpoint(0xAAA6)
                            if not r.p&Z:
                                return (yield from self.tactical_helper_aac2())
                            else:
                                self._a(0x02)
                                m[0x002C]=r.a
                                self._a(m[AP])
                                self._compare(r.a,0x04)
                                yield from self._checkpoint(0xAAB2)
                                if not r.p&C:
                                    return (yield from self.tactical_helper_aac2())
                                else:
                                    yield from self._checkpoint(0xAAB4)
                                    self._rts();return
                    else:
                        self._compare(r.a,0x02)
                        yield from self._checkpoint(0xAA7C)
                        if r.p&Z:
                            self._a(0x01)
                            m[0x002C]=r.a
                            self._a(m[AP])
                            self._compare(r.a,0x05)
                            yield from self._checkpoint(0xAABF)
                            if not r.p&C:
                                return (yield from self.tactical_helper_aac2())
                            else:
                                yield from self._checkpoint(0xAAC1)
                                self._rts();return
                        else:
                            self._a(m[0x002D])
                            yield from self._checkpoint(0xAA81)
                            if r.p&Z:
                                continue
                            else:
                                self._a(m[0x002A])
                                self._compare(r.a,0x03)
                                yield from self._checkpoint(0xAA88)
                                if not r.p&C:
                                    return (yield from self.tactical_helper_aac2())
                                else:
                                    self._a(0x03)
                                    m[0x002C]=r.a
                                    self._a(m[AP])
                                    self._compare(r.a,0x06)
                                    yield from self._checkpoint(0xAA94)
                                    if not r.p&C:
                                        return (yield from self.tactical_helper_aac2())
                                    else:
                                        yield from self._checkpoint(0xAA96)
                                        self._rts();return
                except _ContinueLoop_AA6F:
                    continue
        else:
            return (yield from self.tactical_helper_aac2())

    def tactical_helper_aac2(self):
        """$AAC2: tactical helper aac2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAAC2)
        self._a(m[0x002A])
        self._compare(r.a,0x04)
        yield from self._checkpoint(0xAAC7)
        if not r.p&C:
            return (yield from self.tactical_helper_aadd())
        else:
            self._a(m[0x002D])
            yield from self._checkpoint(0xAACC)
            if r.p&Z:
                return (yield from self.tactical_helper_aadd())
            else:
                self._a(m[AP])
                self._compare(r.a,0x07)
                yield from self._checkpoint(0xAAD3)
                if not r.p&C:
                    return (yield from self.tactical_helper_aadd())
                else:
                    self._x(0x04)
                    if not (yield from self._local_call(self.check_tactic_target,0xAAD7,0xAADA)):return
                    yield from self._checkpoint(0xAADA)
                    if not r.p&C:
                        return (yield from self.tactical_helper_aadd())
                    else:
                        yield from self._checkpoint(0xAADC)
                        self._rts();return

    def tactical_helper_aadd(self):
        """$AADD: tactical helper aadd; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAADD)
        self._a(m[0x002D])
        yield from self._checkpoint(0xAAE0)
        if r.p&Z:
            return (yield from self.tactical_helper_aaf1())
        else:
            self._a(m[AP])
            self._compare(r.a,0x06)
            yield from self._checkpoint(0xAAE7)
            if not r.p&C:
                return (yield from self.tactical_helper_aaf1())
            else:
                self._x(0x00)
                if not (yield from self._local_call(self.check_tactic_target,0xAAEB,0xAAEE)):return
                yield from self._checkpoint(0xAAEE)
                if not r.p&C:
                    return (yield from self.tactical_helper_aaf1())
                else:
                    yield from self._checkpoint(0xAAF0)
                    self._rts();return

    def tactical_helper_aaf1(self):
        """$AAF1: tactical helper aaf1; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAAF1)
        self._a(0x03)
        m[PROPOSAL_STATUS]=r.a
        self._flag(C,False)
        yield from self._checkpoint(0xAAF7)
        self._rts();return

    def choose_special_tactic(self):
        """$AAF8: choose special tactic; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAAF8)
        self._y(m[ACTOR_SLOT])
        self._a(m[(UNIT_IDS+r.y)&65535])
        m[0x002A]=r.a
        if not (yield from self._local_call(self.tactical_helper_b491,0xAB01,0xAB04)):return
        self._y(0x02)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._compare(r.a,0x5C)
        yield from self._checkpoint(0xAB0A)
        if r.p&C:
            self._y(0x0B)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            m[0x0036]=r.a
            self._compare(r.a,0x03)
            yield from self._checkpoint(0xAB1B)
            if r.p&C:
                self._y(m[ACTOR_SLOT])
                self._a(0x05)
                if not (yield from self._local_call(self.tactical_helper_a8d3,0xAB24,0xAB27)):return
                if not (yield from self._local_call(self.rank_candidate_troops,0xAB27,0xAB2A)):return
                self._y(0x00)
                while True:  # natural loop $AB2C
                    try:
                        self._a(m[(0x6FC9+r.y)&65535])
                        self._compare(r.a,0xFF)
                        yield from self._checkpoint(0xAB31)
                        if r.p&Z:
                            return (yield from self.tactical_helper_ab61())
                        else:
                            self._x(r.a)
                            self._a(m[(UNIT_IDS+r.x)&65535])
                            self._compare(r.a,0xFF)
                            yield from self._checkpoint(0xAB39)
                            if r.p&Z:
                                self._y(r.y+1)
                                self._compare(r.y,0x14)
                                yield from self._checkpoint(0xAB5F)
                                if not r.p&C:
                                    continue
                                else:
                                    return (yield from self.tactical_helper_ab61())
                            else:
                                m[0x002F]=r.y
                                m[0x002B]=r.x
                                if not (yield from self._local_call(self.prioritize_special_tactics,0xAB41,0xAB44)):return
                                yield from self._checkpoint(0xAB44)
                                if not r.p&C:
                                    self._y(m[0x002F])
                                    self._y(r.y+1)
                                    self._compare(r.y,0x14)
                                    yield from self._checkpoint(0xAB5F)
                                    if not r.p&C:
                                        continue
                                    else:
                                        return (yield from self.tactical_helper_ab61())
                                else:
                                    self._a(m[0x002C])
                                    m[PROPOSAL_ACTION]=r.a
                                    self._a(m[0x002B])
                                    m[PROPOSAL_TARGET]=r.a
                                    self._a(0x02)
                                    m[PROPOSAL_STATUS]=r.a
                                    self._flag(C,True)
                                    yield from self._checkpoint(0xAB58)
                                    self._rts();return
                    except _ContinueLoop_AB2C:
                        continue
            else:
                self._flag(C,False)
                yield from self._checkpoint(0xAB1E)
                self._rts();return
        else:
            self._flag(C,False)
            yield from self._checkpoint(0xAB0D)
            self._rts();return

    def tactical_helper_ab61(self):
        """$AB61: tactical helper ab61; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAB61)
        self._a(0x03)
        m[PROPOSAL_STATUS]=r.a
        self._flag(C,False)
        yield from self._checkpoint(0xAB67)
        self._rts();return

    def prioritize_special_tactics(self):
        """$AB68: prioritize special tactics; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAB68)
        self._y(0x00)
        self._a(0x03)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.scan_special_officer_whitelist,0xAB6F,0xAB72)):return
        yield from self._checkpoint(0xAB72)
        if not r.p&C:
            return (yield from self.tactical_helper_ab8d())
        else:
            self._x(m[0x002B])
            self._a(m[(0x0650+r.x)&65535])
            self._a(r.a & 0x0F)
            yield from self._checkpoint(0xAB7C)
            if not r.p&Z:
                return (yield from self.tactical_helper_ab8d())
            else:
                self._a(m[AP])
                self._compare(r.a,0x09)
                yield from self._checkpoint(0xAB83)
                if not r.p&C:
                    return (yield from self.tactical_helper_ab8d())
                else:
                    self._x(0x0A)
                    if not (yield from self._local_call(self.check_tactic_target,0xAB87,0xAB8A)):return
                    yield from self._checkpoint(0xAB8A)
                    if not r.p&C:
                        return (yield from self.tactical_helper_ab8d())
                    else:
                        yield from self._checkpoint(0xAB8C)
                        self._rts();return

    def tactical_helper_ab8d(self):
        """$AB8D: tactical helper ab8d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAB8D)
        self._y(0x00)
        self._a(0x03)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.scan_special_officer_whitelist,0xAB94,0xAB97)):return
        yield from self._checkpoint(0xAB97)
        if not r.p&C:
            return (yield from self.tactical_helper_aba8())
        else:
            self._a(m[AP])
            self._compare(r.a,0x0A)
            yield from self._checkpoint(0xAB9E)
            if not r.p&C:
                return (yield from self.tactical_helper_aba8())
            else:
                self._x(0x0B)
                if not (yield from self._local_call(self.check_tactic_target,0xABA2,0xABA5)):return
                yield from self._checkpoint(0xABA5)
                if not r.p&C:
                    return (yield from self.tactical_helper_aba8())
                else:
                    yield from self._checkpoint(0xABA7)
                    self._rts();return

    def tactical_helper_aba8(self):
        """$ABA8: tactical helper aba8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xABA8)
        self._y(0x0B)
        self._a(0x04)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.scan_special_officer_whitelist,0xABAF,0xABB2)):return
        yield from self._checkpoint(0xABB2)
        if not r.p&C:
            return (yield from self.tactical_helper_abc8())
        else:
            if not (yield from self._local_call(self.tactical_helper_ac4d,0xABB4,0xABB7)):return
            yield from self._checkpoint(0xABB7)
            if not r.p&C:
                return (yield from self.tactical_helper_abc8())
            else:
                self._a(m[AP])
                self._compare(r.a,0x0A)
                yield from self._checkpoint(0xABBE)
                if not r.p&C:
                    return (yield from self.tactical_helper_abc8())
                else:
                    self._x(0x0C)
                    if not (yield from self._local_call(self.check_tactic_target,0xABC2,0xABC5)):return
                    yield from self._checkpoint(0xABC5)
                    if not r.p&C:
                        return (yield from self.tactical_helper_abc8())
                    else:
                        yield from self._checkpoint(0xABC7)
                        self._rts();return

    def tactical_helper_abc8(self):
        """$ABC8: tactical helper abc8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xABC8)
        self._y(0x0B)
        self._a(0x04)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.scan_special_officer_whitelist,0xABCF,0xABD2)):return
        yield from self._checkpoint(0xABD2)
        if not r.p&C:
            return (yield from self.tactical_helper_abe8())
        else:
            if not (yield from self._local_call(self.tactical_helper_ac4d,0xABD4,0xABD7)):return
            yield from self._checkpoint(0xABD7)
            if not r.p&C:
                return (yield from self.tactical_helper_abe8())
            else:
                self._a(m[AP])
                self._compare(r.a,0x08)
                yield from self._checkpoint(0xABDE)
                if not r.p&C:
                    return (yield from self.tactical_helper_abe8())
                else:
                    self._x(0x0D)
                    if not (yield from self._local_call(self.check_tactic_target,0xABE2,0xABE5)):return
                    yield from self._checkpoint(0xABE5)
                    if not r.p&C:
                        return (yield from self.tactical_helper_abe8())
                    else:
                        yield from self._checkpoint(0xABE7)
                        self._rts();return

    def tactical_helper_abe8(self):
        """$ABE8: tactical helper abe8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xABE8)
        self._y(0x11)
        self._a(0x05)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.scan_special_officer_whitelist,0xABEF,0xABF2)):return
        yield from self._checkpoint(0xABF2)
        if not r.p&C:
            return (yield from self.tactical_helper_ac08())
        else:
            if not (yield from self._local_call(self.tactical_helper_ac4d,0xABF4,0xABF7)):return
            yield from self._checkpoint(0xABF7)
            if not r.p&C:
                return (yield from self.tactical_helper_ac08())
            else:
                self._a(m[AP])
                self._compare(r.a,0x0C)
                yield from self._checkpoint(0xABFE)
                if not r.p&C:
                    return (yield from self.tactical_helper_ac08())
                else:
                    self._x(0x0E)
                    if not (yield from self._local_call(self.check_tactic_target,0xAC02,0xAC05)):return
                    yield from self._checkpoint(0xAC05)
                    if not r.p&C:
                        return (yield from self.tactical_helper_ac08())
                    else:
                        yield from self._checkpoint(0xAC07)
                        self._rts();return

    def tactical_helper_ac08(self):
        """$AC08: tactical helper ac08; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC08)
        self._a(m[0x002A])
        self._compare(r.a,0x6D)
        yield from self._checkpoint(0xAC0D)
        if not r.p&Z:
            return (yield from self.tactical_helper_ac2f())
        else:
            self._a(m[0x0036])
            self._compare(r.a,0x06)
            yield from self._checkpoint(0xAC14)
            if not r.p&C:
                return (yield from self.tactical_helper_ac2f())
            else:
                self._x(m[0x002B])
                self._a(m[(0x0650+r.x)&65535])
                self._a(r.a & 0xF0)
                yield from self._checkpoint(0xAC1E)
                if not r.p&Z:
                    return (yield from self.tactical_helper_ac2f())
                else:
                    self._a(m[AP])
                    self._compare(r.a,0x0A)
                    yield from self._checkpoint(0xAC25)
                    if not r.p&C:
                        return (yield from self.tactical_helper_ac2f())
                    else:
                        self._x(0x0F)
                        if not (yield from self._local_call(self.check_tactic_target,0xAC29,0xAC2C)):return
                        yield from self._checkpoint(0xAC2C)
                        if not r.p&C:
                            return (yield from self.tactical_helper_ac2f())
                        else:
                            yield from self._checkpoint(0xAC2E)
                            self._rts();return

    def tactical_helper_ac2f(self):
        """$AC2F: tactical helper ac2f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC2F)
        self._flag(C,False)
        yield from self._checkpoint(0xAC30)
        self._rts();return

    def scan_special_officer_whitelist(self):
        """$AC31: scan special officer whitelist; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC31)
        self._a(m[0x0036])
        self._compare(r.a,m[0x0022])
        yield from self._checkpoint(0xAC37)
        if not r.p&C:
            return (yield from self.tactical_helper_ac40())
        else:
            while True:  # natural loop $AC39
                try:
                    self._a(m[(0xAC65+r.y)&65535])
                    self._compare(r.a,0xFF)
                    yield from self._checkpoint(0xAC3E)
                    if not r.p&Z:
                        self._compare(r.a,m[0x002A])
                        yield from self._checkpoint(0xAC45)
                        if not r.p&Z:
                            self._y(r.y+1)
                            continue
                        else:
                            self._flag(C,True)
                            yield from self._checkpoint(0xAC48)
                            self._rts();return
                    else:
                        return (yield from self.tactical_helper_ac40())
                except _ContinueLoop_AC39:
                    continue

    def tactical_helper_ac40(self):
        """$AC40: tactical helper ac40; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC40)
        self._flag(C,False)
        yield from self._checkpoint(0xAC41)
        self._rts();return

    def tactical_helper_ac4d(self):
        """$AC4D: tactical helper ac4d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC4D)
        self._y(m[0x002B])
        self._a(m[(UNIT_IDS+r.y)&65535])
        if not (yield from self._local_call(self.tactical_helper_b491,0xAC53,0xAC56)):return
        self._y(0x09)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        yield from self._checkpoint(0xAC5A)
        if not r.p&Z:
            return (yield from self.tactical_helper_ac61())
        else:
            self._y(r.y-1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            yield from self._checkpoint(0xAC5F)
            if r.p&Z:
                self._flag(C,False)
                yield from self._checkpoint(0xAC64)
                self._rts();return
            else:
                return (yield from self.tactical_helper_ac61())

    def tactical_helper_ac61(self):
        """$AC61: tactical helper ac61; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC61)
        self._flag(C,True)
        yield from self._checkpoint(0xAC62)
        self._rts();return

    def check_tactic_target(self):
        """$AC7B: check tactic target; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAC7B)
        m[0x002C]=r.x
        self._y(m[0x002B])
        self._a(m[(UNIT_X+r.y)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.y)&65535])
        m[0x0021]=r.a
        if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xAC8D,0xAC90)):return
        m[0x0028]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(UNIT_X+r.y)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.y)&65535])
        m[0x0021]=r.a
        if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xACA2,0xACA5)):return
        m[0x0029]=r.a
        self._a(m[0x002C])
        yield from self._checkpoint(0xACAB)
        index=self._dispatch(0xACAB,(44238, 44251, 44251, 44251, 44264, 44275, 44288, 44322, 44357, 44389, 44434, 44495, 44434, 44542, 44576, 44637))
        return (yield from (self.predicate_tactics_00,self.predicate_tactics_01_02_03,self.predicate_tactics_01_02_03,self.predicate_tactics_01_02_03,self.predicate_tactics_04,self.predicate_tactics_05,self.predicate_tactics_06,self.predicate_tactics_07,self.predicate_tactics_08,self.predicate_tactics_09,self.predicate_tactics_10_12,self.predicate_tactics_11,self.predicate_tactics_10_12,self.predicate_tactics_13,self.predicate_tactics_14,self.predicate_tactics_15,)[index]())

    def predicate_tactics_00(self):
        """$ACCE: predicate tactics 00; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACCE)
        self._a(m[0x0028])
        yield from self._checkpoint(0xACD1)
        if r.p&Z:
            return (yield from self.tactical_helper_acd9())
        else:
            self._compare(r.a,0x02)
            yield from self._checkpoint(0xACD5)
            if r.p&Z:
                return (yield from self.tactical_helper_acd9())
            else:
                self._flag(C,False)
                yield from self._checkpoint(0xACD8)
                self._rts();return

    def tactical_helper_acd9(self):
        """$ACD9: tactical helper acd9; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACD9)
        self._flag(C,True)
        yield from self._checkpoint(0xACDA)
        self._rts();return

    def predicate_tactics_01_02_03(self):
        """$ACDB: predicate tactics 01 02 03; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACDB)
        self._a(m[0x0028])
        yield from self._checkpoint(0xACDE)
        if r.p&Z:
            return (yield from self.tactical_helper_ace6())
        else:
            self._compare(r.a,0x04)
            yield from self._checkpoint(0xACE2)
            if r.p&Z:
                return (yield from self.tactical_helper_ace6())
            else:
                self._flag(C,False)
                yield from self._checkpoint(0xACE5)
                self._rts();return

    def tactical_helper_ace6(self):
        """$ACE6: tactical helper ace6; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACE6)
        self._flag(C,True)
        yield from self._checkpoint(0xACE7)
        self._rts();return

    def predicate_tactics_04(self):
        """$ACE8: predicate tactics 04; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACE8)
        self._a(m[0x0028])
        self._compare(r.a,0x03)
        yield from self._checkpoint(0xACED)
        if r.p&Z:
            self._flag(C,True)
            yield from self._checkpoint(0xACF2)
            self._rts();return
        else:
            self._flag(C,False)
            yield from self._checkpoint(0xACF0)
            self._rts();return

    def predicate_tactics_05(self):
        """$ACF3: predicate tactics 05; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACF3)
        self._a(m[0x002B])
        yield from self._checkpoint(0xACF6)
        if r.p&Z:
            return (yield from self.tactical_helper_acfe())
        else:
            self._compare(r.a,0x0A)
            yield from self._checkpoint(0xACFA)
            if r.p&Z:
                return (yield from self.tactical_helper_acfe())
            else:
                self._flag(C,False)
                yield from self._checkpoint(0xACFD)
                self._rts();return

    def tactical_helper_acfe(self):
        """$ACFE: tactical helper acfe; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xACFE)
        self._flag(C,True)
        yield from self._checkpoint(0xACFF)
        self._rts();return

    def predicate_tactics_06(self):
        """$AD00: predicate tactics 06; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD00)
        self._a(m[0x0028])
        self._compare(r.a,0x05)
        yield from self._checkpoint(0xAD05)
        if not r.p&Z:
            return (yield from self.tactical_helper_ad1e())
        else:
            self._y(m[0x002B])
            if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAD0A,0xAD0D)):return
            self._y(0x00)
            while True:  # natural loop $AD0F
                try:
                    self._a(m[(0x6FDD+r.y)&65535])
                    self._a(r.a & 0x7F)
                    self._compare(r.a,m[ACTOR_SLOT])
                    yield from self._checkpoint(0xAD17)
                    if r.p&Z:
                        self._flag(C,True)
                        yield from self._checkpoint(0xAD21)
                        self._rts();return
                    else:
                        self._y(r.y+1)
                        self._compare(r.y,0x04)
                        yield from self._checkpoint(0xAD1C)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_ad1e())
                except _ContinueLoop_AD0F:
                    continue

    def tactical_helper_ad1e(self):
        """$AD1E: tactical helper ad1e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD1E)
        self._flag(C,False)
        yield from self._checkpoint(0xAD1F)
        self._rts();return

    def predicate_tactics_07(self):
        """$AD22: predicate tactics 07; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD22)
        self._a(m[0x0028])
        yield from self._checkpoint(0xAD25)
        if r.p&Z:
            return (yield from self.tactical_helper_ad2b())
        else:
            self._compare(r.a,0x04)
            yield from self._checkpoint(0xAD29)
            if not r.p&Z:
                return (yield from self.tactical_helper_ad41())
            else:
                return (yield from self.tactical_helper_ad2b())

    def tactical_helper_ad2b(self):
        """$AD2B: tactical helper ad2b; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD2B)
        self._y(m[0x002B])
        if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAD2E,0xAD31)):return
        self._y(0x00)
        while True:  # natural loop $AD33
            try:
                self._a(m[(0x6FDD+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xAD38)
                if r.p&Z:
                    self._y(r.y+1)
                    self._compare(r.y,0x04)
                    yield from self._checkpoint(0xAD3F)
                    if not r.p&C:
                        continue
                    else:
                        return (yield from self.tactical_helper_ad41())
                else:
                    yield from self._checkpoint(0xAD3A)
                    if r.p&N:
                        self._flag(C,True)
                        yield from self._checkpoint(0xAD44)
                        self._rts();return
                    else:
                        self._y(r.y+1)
                        self._compare(r.y,0x04)
                        yield from self._checkpoint(0xAD3F)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_ad41())
            except _ContinueLoop_AD33:
                continue

    def tactical_helper_ad41(self):
        """$AD41: tactical helper ad41; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD41)
        self._flag(C,False)
        yield from self._checkpoint(0xAD42)
        self._rts();return

    def predicate_tactics_08(self):
        """$AD45: predicate tactics 08; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD45)
        self._a(m[0x0028])
        self._compare(r.a,0x05)
        yield from self._checkpoint(0xAD4A)
        if r.p&Z:
            return (yield from self.tactical_helper_ad61())
        else:
            self._y(m[0x002B])
            self._a(m[(UNIT_IDS+r.y)&65535])
            if not (yield from self._local_call(self.tactical_helper_b491,0xAD52,0xAD55)):return
            self._y(0x03)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._compare(r.a,0x64)
            yield from self._checkpoint(0xAD5B)
            if r.p&Z:
                return (yield from self.tactical_helper_ad61())
            else:
                self._compare(r.a,0x32)
                yield from self._checkpoint(0xAD5F)
                if not r.p&C:
                    self._flag(C,True)
                    yield from self._checkpoint(0xAD64)
                    self._rts();return
                else:
                    return (yield from self.tactical_helper_ad61())

    def tactical_helper_ad61(self):
        """$AD61: tactical helper ad61; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD61)
        self._flag(C,False)
        yield from self._checkpoint(0xAD62)
        self._rts();return

    def predicate_tactics_09(self):
        """$AD65: predicate tactics 09; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD65)
        self._a(m[0x0029])
        self._compare(r.a,0x04)
        yield from self._checkpoint(0xAD6A)
        if r.p&Z:
            return (yield from self.tactical_helper_ad70())
        else:
            self._compare(r.a,0x05)
            yield from self._checkpoint(0xAD6E)
            if not r.p&Z:
                return (yield from self.tactical_helper_ad87())
            else:
                return (yield from self.tactical_helper_ad70())

    def tactical_helper_ad70(self):
        """$AD70: tactical helper ad70; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD70)
        self._y(m[ACTOR_SLOT])
        if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAD73,0xAD76)):return
        self._y(0x00)
        while True:  # natural loop $AD78
            try:
                self._a(m[(0x6FDD+r.y)&65535])
                self._a(r.a & 0x7F)
                self._compare(r.a,m[0x002B])
                yield from self._checkpoint(0xAD80)
                if r.p&Z:
                    self._a(m[0x0028])
                    self._compare(r.a,0x05)
                    yield from self._checkpoint(0xAD8E)
                    if not r.p&Z:
                        return (yield from self.tactical_helper_ad87())
                    else:
                        self._flag(C,True)
                        yield from self._checkpoint(0xAD91)
                        self._rts();return
                else:
                    self._y(r.y+1)
                    self._compare(r.y,0x04)
                    yield from self._checkpoint(0xAD85)
                    if not r.p&C:
                        continue
                    else:
                        return (yield from self.tactical_helper_ad87())
            except _ContinueLoop_AD78:
                continue

    def tactical_helper_ad87(self):
        """$AD87: tactical helper ad87; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD87)
        self._flag(C,False)
        yield from self._checkpoint(0xAD88)
        self._rts();return

    def predicate_tactics_10_12(self):
        """$AD92: predicate tactics 10 12; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAD92)
        self._a(m[0x0028])
        self._compare(r.a,0x03)
        yield from self._checkpoint(0xAD97)
        if not r.p&Z:
            return (yield from self.tactical_helper_adcb())
        else:
            self._y(m[0x002B])
            if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAD9C,0xAD9F)):return
            self._y(0x00)
            while True:  # natural loop $ADA1
                try:
                    self._a(m[(0x6FDD+r.y)&65535])
                    yield from self._checkpoint(0xADA4)
                    if not r.p&N:
                        self._y(r.y+1)
                        self._compare(r.y,0x04)
                        yield from self._checkpoint(0xADC9)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_adcb())
                    else:
                        self._compare(r.a,0xFF)
                        yield from self._checkpoint(0xADA8)
                        if r.p&Z:
                            self._y(r.y+1)
                            self._compare(r.y,0x04)
                            yield from self._checkpoint(0xADC9)
                            if not r.p&C:
                                continue
                            else:
                                return (yield from self.tactical_helper_adcb())
                        else:
                            m[0x0027]=r.y
                            self._a(r.a & 0x7F)
                            self._y(r.a)
                            self._a(m[(UNIT_X+r.y)&65535])
                            m[0x0020]=r.a
                            self._a(m[(UNIT_Y+r.y)&65535])
                            m[0x0021]=r.a
                            if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xADBC,0xADBF)):return
                            self._compare(r.a,0x03)
                            yield from self._checkpoint(0xADC1)
                            if r.p&Z:
                                self._flag(C,True)
                                yield from self._checkpoint(0xADCE)
                                self._rts();return
                            else:
                                self._y(m[0x0027])
                                self._y(r.y+1)
                                self._compare(r.y,0x04)
                                yield from self._checkpoint(0xADC9)
                                if not r.p&C:
                                    continue
                                else:
                                    return (yield from self.tactical_helper_adcb())
                except _ContinueLoop_ADA1:
                    continue

    def tactical_helper_adcb(self):
        """$ADCB: tactical helper adcb; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADCB)
        self._flag(C,False)
        yield from self._checkpoint(0xADCC)
        self._rts();return

    def predicate_tactics_11(self):
        """$ADCF: predicate tactics 11; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADCF)
        self._a(m[0x0029])
        yield from self._checkpoint(0xADD2)
        if not r.p&Z:
            return (yield from self.tactical_helper_adfa())
        else:
            self._y(m[ACTOR_SLOT])
            self._a(m[(UNIT_IDS+r.y)&65535])
            if not (yield from self._local_call(self.tactical_helper_b491,0xADDA,0xADDD)):return
            self._y(0x09)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            yield from self._checkpoint(0xADE1)
            if not r.p&Z:
                return (yield from self.tactical_helper_adea())
            else:
                self._y(r.y-1)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0x64)
                yield from self._checkpoint(0xADE8)
                if not r.p&C:
                    return (yield from self.tactical_helper_adfa())
                else:
                    return (yield from self.tactical_helper_adea())

    def tactical_helper_adea(self):
        """$ADEA: tactical helper adea; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADEA)
        self._y(0x00)
        self._a(m[SIDE])
        yield from self._checkpoint(0xADEF)
        if not r.p&N:
            pass
        else:
            self._y(0x04)
            pass
        return (yield from self.tactical_helper_adf3())

    def tactical_helper_adf3(self):
        """$ADF3: tactical helper adf3; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADF3)
        self._a(m[(0x04D8+r.y)&65535])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xADF8)
        if r.p&Z:
            self._flag(C,True)
            yield from self._checkpoint(0xADFD)
            self._rts();return
        else:
            return (yield from self.tactical_helper_adfa())

    def tactical_helper_adfa(self):
        """$ADFA: tactical helper adfa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADFA)
        self._flag(C,False)
        yield from self._checkpoint(0xADFB)
        self._rts();return

    def predicate_tactics_13(self):
        """$ADFE: predicate tactics 13; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xADFE)
        self._y(m[0x0029])
        self._compare(r.y,0x05)
        yield from self._checkpoint(0xAE03)
        if not r.p&Z:
            return (yield from self.tactical_helper_ae1c())
        else:
            self._y(m[ACTOR_SLOT])
            if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAE08,0xAE0B)):return
            self._y(0x00)
            while True:  # natural loop $AE0D
                try:
                    self._a(m[(0x6FDD+r.y)&65535])
                    self._a(r.a ^ 0x80)
                    self._compare(r.a,m[0x002B])
                    yield from self._checkpoint(0xAE15)
                    if r.p&Z:
                        self._flag(C,True)
                        yield from self._checkpoint(0xAE1F)
                        self._rts();return
                    else:
                        self._y(r.y+1)
                        self._compare(r.y,0x04)
                        yield from self._checkpoint(0xAE1A)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_ae1c())
                except _ContinueLoop_AE0D:
                    continue

    def tactical_helper_ae1c(self):
        """$AE1C: tactical helper ae1c; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE1C)
        self._flag(C,False)
        yield from self._checkpoint(0xAE1D)
        self._rts();return

    def predicate_tactics_14(self):
        """$AE20: predicate tactics 14; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE20)
        self._y(m[0x0028])
        self._compare(r.y,0x05)
        yield from self._checkpoint(0xAE25)
        if r.p&Z:
            return (yield from self.tactical_helper_ae59())
        else:
            self._y(m[0x002B])
            if not (yield from self._local_call(self.find_orthogonal_neighbors,0xAE2A,0xAE2D)):return
            self._y(0x00)
            while True:  # natural loop $AE2F
                try:
                    self._a(m[(0x6FDD+r.y)&65535])
                    yield from self._checkpoint(0xAE32)
                    if not r.p&N:
                        self._y(r.y+1)
                        self._compare(r.y,0x04)
                        yield from self._checkpoint(0xAE57)
                        if not r.p&C:
                            continue
                        else:
                            return (yield from self.tactical_helper_ae59())
                    else:
                        self._compare(r.a,0xFF)
                        yield from self._checkpoint(0xAE36)
                        if r.p&Z:
                            self._y(r.y+1)
                            self._compare(r.y,0x04)
                            yield from self._checkpoint(0xAE57)
                            if not r.p&C:
                                continue
                            else:
                                return (yield from self.tactical_helper_ae59())
                        else:
                            m[0x0027]=r.y
                            self._a(r.a & 0x7F)
                            self._y(r.a)
                            self._a(m[(UNIT_X+r.y)&65535])
                            m[0x0020]=r.a
                            self._a(m[(UNIT_Y+r.y)&65535])
                            m[0x0021]=r.a
                            if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xAE4A,0xAE4D)):return
                            self._compare(r.a,0x05)
                            yield from self._checkpoint(0xAE4F)
                            if not r.p&Z:
                                self._flag(C,True)
                                yield from self._checkpoint(0xAE5C)
                                self._rts();return
                            else:
                                self._y(m[0x0027])
                                self._y(r.y+1)
                                self._compare(r.y,0x04)
                                yield from self._checkpoint(0xAE57)
                                if not r.p&C:
                                    continue
                                else:
                                    return (yield from self.tactical_helper_ae59())
                except _ContinueLoop_AE2F:
                    continue

    def tactical_helper_ae59(self):
        """$AE59: tactical helper ae59; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE59)
        self._flag(C,False)
        yield from self._checkpoint(0xAE5A)
        self._rts();return

    def predicate_tactics_15(self):
        """$AE5D: predicate tactics 15; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE5D)
        self._y(m[0x0028])
        self._compare(r.y,0x03)
        yield from self._checkpoint(0xAE62)
        if r.p&Z:
            return (yield from self.tactical_helper_ae68())
        else:
            self._compare(r.y,0x05)
            yield from self._checkpoint(0xAE66)
            if r.p&Z:
                return (yield from self.tactical_helper_ae8f())
            else:
                return (yield from self.tactical_helper_ae68())

    def tactical_helper_ae68(self):
        """$AE68: tactical helper ae68; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE68)
        self._y(m[0x002B])
        self._a(m[(UNIT_IDS+r.y)&65535])
        if not (yield from self._local_call(self.tactical_helper_b491,0xAE6E,0xAE71)):return
        self._y(0x01)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._compare(r.a,0x55)
        yield from self._checkpoint(0xAE77)
        if r.p&C:
            return (yield from self.tactical_helper_ae80())
        else:
            self._y(r.y+1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._compare(r.a,0x55)
            yield from self._checkpoint(0xAE7E)
            if not r.p&C:
                return (yield from self.tactical_helper_ae8f())
            else:
                return (yield from self.tactical_helper_ae80())

    def tactical_helper_ae80(self):
        """$AE80: tactical helper ae80; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE80)
        self._y(0x09)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._compare(r.a,0x02)
        yield from self._checkpoint(0xAE86)
        if not r.p&C:
            return (yield from self.tactical_helper_ae8f())
        else:
            self._y(r.y-1)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._compare(r.a,0xBC)
            yield from self._checkpoint(0xAE8D)
            if r.p&C:
                self._flag(C,True)
                yield from self._checkpoint(0xAE92)
                self._rts();return
            else:
                return (yield from self.tactical_helper_ae8f())

    def tactical_helper_ae8f(self):
        """$AE8F: tactical helper ae8f; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE8F)
        self._flag(C,False)
        yield from self._checkpoint(0xAE90)
        self._rts();return

    def rank_candidate_troops(self):
        """$AE93: rank candidate troops; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAE93)
        self._x(0x00)
        self._y(0x00)
        while True:  # natural loop $AE97
            try:
                self._a(m[(0x6FC9+r.y)&65535])
                m[0x0020]=r.a
                self._a(0xFF)
                m[(0x6FC9+r.y)&65535]=r.a
                self._a(m[0x0020])
                yield from self._checkpoint(0xAEA5)
                if not r.p&N:
                    pass
                else:
                    self._a(r.y)
                    m[(0x6FC9+r.x)&65535]=r.a
                    self._x(r.x+1)
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                yield from self._checkpoint(0xAEAF)
                if not r.p&C:
                    continue
                else:
                    pass
                self._compare(r.x,0x02)
                yield from self._checkpoint(0xAEB3)
                if r.p&C:
                    self._x(r.x-1)
                    m[0x0024]=r.x
                    while True:  # natural loop $AEBA
                        try:
                            self._x(0x00)
                            while True:  # natural loop $AEBC
                                try:
                                    self._a(m[(0x6FC9+r.x)&65535])
                                    self._y(r.a)
                                    self._a(m[(UNIT_IDS+r.y)&65535])
                                    if not (yield from self._local_call(self.tactical_helper_b491,0xAEC3,0xAEC6)):return
                                    self._y(0x08)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[0x0022]=r.a
                                    self._y(r.y+1)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    m[0x0023]=r.a
                                    self._a(m[(0x6FCA+r.x)&65535])
                                    self._y(r.a)
                                    self._a(m[(UNIT_IDS+r.y)&65535])
                                    if not (yield from self._local_call(self.tactical_helper_b491,0xAEDA,0xAEDD)):return
                                    self._y(0x09)
                                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                    self._compare(r.a,m[0x0023])
                                    yield from self._checkpoint(0xAEE4)
                                    if not r.p&C:
                                        pass
                                    else:
                                        yield from self._checkpoint(0xAEE6)
                                        if not r.p&Z:
                                            self._a(m[(0x6FC9+r.x)&65535])
                                            self._y(r.a)
                                            self._a(m[(0x6FCA+r.x)&65535])
                                            m[(0x6FC9+r.x)&65535]=r.a
                                            self._a(r.y)
                                            m[(0x6FCA+r.x)&65535]=r.a
                                            pass
                                        else:
                                            self._y(r.y-1)
                                            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                            self._compare(r.a,m[0x0022])
                                            yield from self._checkpoint(0xAEEE)
                                            if not r.p&C:
                                                pass
                                            else:
                                                self._a(m[(0x6FC9+r.x)&65535])
                                                self._y(r.a)
                                                self._a(m[(0x6FCA+r.x)&65535])
                                                m[(0x6FC9+r.x)&65535]=r.a
                                                self._a(r.y)
                                                m[(0x6FCA+r.x)&65535]=r.a
                                                pass
                                            pass
                                        pass
                                    self._x(r.x+1)
                                    self._compare(r.x,m[0x0024])
                                    yield from self._checkpoint(0xAF02)
                                    if not r.p&C:
                                        continue
                                    else:
                                        pass
                                    m[0x002F]=self._nz(m[0x002F]-1)
                                    self._a(m[0x002F])
                                    yield from self._checkpoint(0xAF0A)
                                    if not r.p&N:
                                        raise _ContinueLoop_AEBA
                                    else:
                                        pass
                                    yield from self._checkpoint(0xAF0C)
                                    self._rts();return
                                except _ContinueLoop_AEBC:
                                    continue
                        except _ContinueLoop_AEBA:
                            continue
                else:
                    yield from self._checkpoint(0xAEB5)
                    self._rts();return
            except _ContinueLoop_AE97:
                continue

    def propose_retreat(self):
        """$AF0D: propose retreat; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAF0D)
        self._a(m[0x0507])
        self._x(m[SIDE])
        yield from self._checkpoint(0xAF13)
        if not r.p&N:
            pass
        else:
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            r.a=self._shift(r.a,False,rotate=False)
            pass
        return (yield from self.tactical_helper_af19())

    def tactical_helper_af19(self):
        """$AF19: tactical helper af19; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAF19)
        self._a(r.a & 0x0F)
        if not (yield from self._local_call(self.tactical_helper_b4c2,0xAF1B,0xAF1E)):return
        self._y(0x00)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        m[0x0022]=r.a
        self._y(m[ACTOR_SLOT])
        self._a(m[(UNIT_IDS+r.y)&65535])
        self._compare(r.a,m[0x0022])
        yield from self._checkpoint(0xAF2E)
        if not r.p&Z:
            self._compare(r.y,0x00)
            yield from self._checkpoint(0xAF35)
            if r.p&Z:
                return (yield from self.tactical_helper_af3e())
            else:
                self._compare(r.y,0x0A)
                yield from self._checkpoint(0xAF39)
                if r.p&Z:
                    return (yield from self.tactical_helper_af3e())
                else:
                    self._a(0xC9)
                    m[0x0022]=r.a
                    self._a(0x00)
                    m[0x0023]=r.a
                    self._a(0x64)
                    m[0x0024]=r.a
                    if not (yield from self._local_call(self.tactical_helper_afd4,0xAF97,0xAF9A)):return
                    yield from self._checkpoint(0xAF9A)
                    if r.p&C:
                        return (yield from self.tactical_helper_afd2())
                    else:
                        while True:  # natural loop $AF9C
                            try:
                                if not (yield from self._local_call(self.draw_ai_rng_byte,0xAF9C,0xAF9F)):return
                                self._compare(r.a,0x64)
                                yield from self._checkpoint(0xAFA1)
                                if r.p&C:
                                    continue
                                else:
                                    pass
                                self._compare(r.a,0x46)
                                yield from self._checkpoint(0xAFA5)
                                if r.p&C:
                                    return (yield from self.tactical_helper_afd2())
                                else:
                                    return (yield from self.tactical_helper_afbe())
                            except _ContinueLoop_AF9C:
                                continue
        else:
            self._a(0x2D)
            m[0x0022]=r.a
            self._a(0x01)
            m[0x0023]=r.a
            self._a(0x33)
            m[0x0024]=r.a
            if not (yield from self._local_call(self.tactical_helper_afd4,0xAFB9,0xAFBC)):return
            yield from self._checkpoint(0xAFBC)
            if r.p&C:
                return (yield from self.tactical_helper_afd2())
            else:
                return (yield from self.tactical_helper_afbe())

    def tactical_helper_af3e(self):
        """$AF3E: tactical helper af3e; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAF3E)
        if not (yield from self._local_call(self.sum_army_troops,0xAF3E,0xAF41)):return
        self._a(m[0x002A])
        self._flag(C,True)
        self._add(0xDD,subtract=True)
        self._a(m[0x002B])
        self._add(0x06,subtract=True)
        yield from self._checkpoint(0xAF4C)
        if r.p&C:
            return (yield from self.tactical_helper_af71())
        else:
            self._a(m[0x002A])
            self._flag(C,False)
            self._add(0xAB)
            m[0x002A]=r.a
            self._a(m[0x002B])
            self._add(0x0D)
            m[0x002B]=r.a
            self._a(m[0x002A])
            self._flag(C,True)
            self._add(m[0x002C],subtract=True)
            self._a(m[0x002B])
            self._add(m[0x002D],subtract=True)
            yield from self._checkpoint(0xAF6C)
            if r.p&C:
                return (yield from self.tactical_helper_af71())
            else:
                return (yield from self.tactical_helper_afbe())

    def tactical_helper_af71(self):
        """$AF71: tactical helper af71; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAF71)
        self._a(0x65)
        m[0x0022]=r.a
        self._a(0x00)
        m[0x0023]=r.a
        self._a(0x29)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.tactical_helper_afd4,0xAF80,0xAF83)):return
        yield from self._checkpoint(0xAF83)
        if r.p&C:
            return (yield from self.tactical_helper_afd2())
        else:
            return (yield from self.tactical_helper_afbe())

    def tactical_helper_afbe(self):
        """$AFBE: tactical helper afbe; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAFBE)
        self._a(0xFF)
        m[PROPOSAL_ACTION]=r.a
        if not (yield from self._local_call(self.choose_retreat_city,0xAFC3,0xAFC6)):return
        self._a(m[PROPOSAL_ACTION])
        yield from self._checkpoint(0xAFC9)
        if r.p&N:
            return (yield from self.tactical_helper_afd2())
        else:
            self._a(0x04)
            m[PROPOSAL_STATUS]=r.a
            self._flag(C,True)
            yield from self._checkpoint(0xAFD1)
            self._rts();return

    def tactical_helper_afd2(self):
        """$AFD2: tactical helper afd2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAFD2)
        self._flag(C,False)
        yield from self._checkpoint(0xAFD3)
        self._rts();return

    def tactical_helper_afd4(self):
        """$AFD4: tactical helper afd4; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAFD4)
        self._y(m[ACTOR_SLOT])
        self._a(m[(UNIT_IDS+r.y)&65535])
        if not (yield from self._local_call(self.tactical_helper_b491,0xAFDA,0xAFDD)):return
        self._y(0x08)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._flag(C,True)
        self._add(m[0x0022],subtract=True)
        self._y(0x09)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._add(m[0x0023],subtract=True)
        yield from self._checkpoint(0xAFEC)
        if r.p&C:
            pass
        else:
            self._y(0x00)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            self._compare(r.a,m[0x0024])
            pass
        return (yield from self.tactical_helper_aff5())

    def tactical_helper_aff5(self):
        """$AFF5: tactical helper aff5; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAFF5)
        self._rts();return

    def choose_retreat_city(self):
        """$AFF6: choose retreat city; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xAFF6)
        self._a(m[SIDE])
        yield from self._checkpoint(0xAFF9)
        if not r.p&N:
            self._a(m[0x0507])
            self._a(r.a & 0x0F)
            m[0x0022]=r.a
            self._y(0x30)
            yield from self._external(0xB00C,0xF266,0xB00F,"call",None)
            if r.pc!=0xB00F:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._x(0x00)
            self._a(0xFF)
            m[0x0025]=r.a
            while True:  # natural loop $B01D
                try:
                    self._a(m[(0x9D72+r.y)&65535])
                    yield from self._checkpoint(0xB020)
                    if r.p&N:
                        self._y(r.y+1)
                        self._x(r.x+1)
                        self._compare(r.x,0x08)
                        yield from self._checkpoint(0xB057)
                        if not r.p&C:
                            continue
                        else:
                            self._a(m[0x0025])
                            m[PROPOSAL_ACTION]=r.a
                            yield from self._checkpoint(0xB05F)
                            self._rts();return
                    else:
                        m[0x0023]=r.a
                        m[0x0024]=r.y
                        if not (yield from self._local_call(self.tactical_helper_b469,0xB028,0xB02B)):return
                        self._y(0x00)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._a(r.a & 0x07)
                        self._compare(r.a,0x07)
                        yield from self._checkpoint(0xB033)
                        if not r.p&Z:
                            self._compare(r.a,m[0x0022])
                            yield from self._checkpoint(0xB041)
                            if not r.p&Z:
                                self._y(m[0x0024])
                                self._y(r.y+1)
                                self._x(r.x+1)
                                self._compare(r.x,0x08)
                                yield from self._checkpoint(0xB057)
                                if not r.p&C:
                                    continue
                                else:
                                    self._a(m[0x0025])
                                    m[PROPOSAL_ACTION]=r.a
                                    yield from self._checkpoint(0xB05F)
                                    self._rts();return
                            else:
                                self._y(0x11)
                                while True:  # natural loop $B045
                                    try:
                                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                                        self._compare(r.a,0xFF)
                                        yield from self._checkpoint(0xB049)
                                        if r.p&Z:
                                            self._a(m[0x0023])
                                            m[PROPOSAL_ACTION]=r.a
                                            yield from self._checkpoint(0xB066)
                                            self._rts();return
                                        else:
                                            self._y(r.y+1)
                                            self._compare(r.y,0x1B)
                                            yield from self._checkpoint(0xB04E)
                                            if not r.p&C:
                                                continue
                                            else:
                                                self._y(m[0x0024])
                                                self._y(r.y+1)
                                                self._x(r.x+1)
                                                self._compare(r.x,0x08)
                                                yield from self._checkpoint(0xB057)
                                                if not r.p&C:
                                                    raise _ContinueLoop_B01D
                                                else:
                                                    self._a(m[0x0025])
                                                    m[PROPOSAL_ACTION]=r.a
                                                    yield from self._checkpoint(0xB05F)
                                                    self._rts();return
                                    except _ContinueLoop_B045:
                                        continue
                        else:
                            self._a(m[0x0023])
                            m[0x0025]=r.a
                            self._y(m[0x0024])
                            self._y(r.y+1)
                            self._x(r.x+1)
                            self._compare(r.x,0x08)
                            yield from self._checkpoint(0xB057)
                            if not r.p&C:
                                continue
                            else:
                                self._a(m[0x0025])
                                m[PROPOSAL_ACTION]=r.a
                                yield from self._checkpoint(0xB05F)
                                self._rts();return
                except _ContinueLoop_B01D:
                    continue
        else:
            self._a(m[0x052A])
            m[PROPOSAL_ACTION]=r.a
            yield from self._checkpoint(0xB001)
            self._rts();return

    def sum_army_troops(self):
        """$B067: sum army troops; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB067)
        self._y(0x00)
        m[0x002A]=r.y
        m[0x002B]=r.y
        m[0x002C]=r.y
        m[0x002D]=r.y
        while True:  # natural loop $B075
            try:
                self._a(m[(UNIT_IDS+r.y)&65535])
                self._compare(r.a,0xFF)
                yield from self._checkpoint(0xB07A)
                if r.p&Z:
                    pass
                else:
                    m[0x0022]=r.a
                    self._a(r.y)
                    self._push(r.a)
                    self._a(m[0x0022])
                    if not (yield from self._local_call(self.tactical_helper_b491,0xB084,0xB087)):return
                    self._y(0x08)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0022]=r.a
                    self._y(r.y+1)
                    self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                    m[0x0023]=r.a
                    self._a(self._pop())
                    self._y(r.a)
                    self._x(0x00)
                    if not (yield from self._local_call(self.opposing_side_marker,0xB098,0xB09B)):return
                    yield from self._checkpoint(0xB09B)
                    if not r.p&N:
                        pass
                    else:
                        self._x(0x02)
                        pass
                    self._a(m[(0x002A+r.x)&65535])
                    self._flag(C,False)
                    self._add(m[0x0022])
                    m[(0x002A+r.x)&65535]=r.a
                    self._a(m[(0x002B+r.x)&65535])
                    self._add(m[0x0023])
                    m[(0x002B+r.x)&65535]=r.a
                    pass
                self._y(r.y+1)
                self._compare(r.y,0x14)
                yield from self._checkpoint(0xB0B5)
                if not r.p&C:
                    continue
                else:
                    pass
                yield from self._checkpoint(0xB0B7)
                self._rts();return
            except _ContinueLoop_B075:
                continue

    def tactical_helper_b0b8(self):
        """$B0B8: tactical helper b0b8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB0B8)
        self._a(0x1E)
        self._flag(C,True)
        self._add(m[0x0506],subtract=True)
        m[0x002E]=r.a
        if not (yield from self._local_call(self.sum_army_troops,0xB0C1,0xB0C4)):return
        self._a(m[0x002A])
        m[0x0020]=r.a
        self._a(m[0x002B])
        m[0x0021]=r.a
        if not (yield from self._local_call(self.officer_record_pointer,0xB0D0,0xB0D3)):return
        self._a(m[0x0026])
        m[0x002A]=r.a
        self._a(m[0x0027])
        m[0x002B]=r.a
        self._a(m[0x002C])
        m[0x0020]=r.a
        self._a(m[0x002D])
        m[0x0021]=r.a
        if not (yield from self._local_call(self.officer_record_pointer,0xB0EB,0xB0EE)):return
        self._a(m[0x0026])
        m[0x002C]=r.a
        self._a(m[0x0027])
        m[0x002D]=r.a
        yield from self._checkpoint(0xB0FA)
        self._rts();return

    def officer_record_pointer(self):
        """$B0FB: officer record pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB0FB)
        self._a(0x00)
        m[0x0022]=r.a
        self._a(0x04)
        m[0x0023]=r.a
        if not (yield from self._local_call(self.multiply_u24_by_u8,0xB105,0xB108)):return
        self._a(m[0x0026])
        m[0x0020]=r.a
        self._a(m[0x0027])
        m[0x0021]=r.a
        self._a(m[0x0028])
        m[0x0022]=r.a
        self._a(0xE8)
        m[0x0023]=r.a
        self._a(0x03)
        m[0x0024]=r.a
        if not (yield from self._local_call(self.divide_u24_by_u16,0xB124,0xB127)):return
        self._a(m[0x002E])
        m[0x0023]=r.a
        return (yield from self.multiply_u24_by_u8())

    def tactical_helper_b469(self):
        """$B469: tactical helper b469; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB469)
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
        yield from self._checkpoint(0xB490)
        self._rts();return

    def tactical_helper_b491(self):
        """$B491: tactical helper b491; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB491)
        self._y(0x00)
        m[0x0021]=r.y
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
        yield from self._checkpoint(0xB4C1)
        self._rts();return

    def tactical_helper_b4c2(self):
        """$B4C2: tactical helper b4c2; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB4C2)
        self._a(r.a & 0x0F)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xB4D3+r.y)&65535])
        m[0x0020]=r.a
        self._a(m[(0xB4D4+r.y)&65535])
        m[0x0021]=r.a
        yield from self._checkpoint(0xB4D2)
        self._rts();return

    def initial_officer_record_pointer(self):
        """$B4E1: initial officer record pointer; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB4E1)
        self._y(0x31)
        yield from self._external(0xB4E3,0xF266,0xB4E6,"call",None)
        if r.pc!=0xB4E6:return  # preserve nonlocal stack return
        self._y(0x00)
        m[0x0021]=r.y
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
        self._add(0x00)
        m[0x0020]=r.a
        self._a(m[0x0021])
        self._add(0x80)
        m[0x0021]=r.a
        yield from self._checkpoint(0xB516)
        self._rts();return

    def divide_u24_by_u16(self):
        """$B536: divide u24 by u16; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB536)
        self._a(0x00)
        m[0x0025]=r.a
        m[0x0026]=r.a
        m[0x0027]=r.a
        self._y(0x17)
        while True:  # natural loop $B543
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
                yield from self._checkpoint(0xB56D)
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
                yield from self._checkpoint(0xB582)
                if not r.p&N:
                    continue
                else:
                    pass
                yield from self._checkpoint(0xB584)
                self._rts();return
            except _ContinueLoop_B543:
                continue

    def multiply_u24_by_u8(self):
        """$B585: multiply u24 by u8; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB585)
        self._y(0x07)
        self._a(0x00)
        m[0x0024]=r.a
        m[0x0025]=r.a
        m[0x0026]=r.a
        m[0x0027]=r.a
        m[0x0028]=r.a
        m[0x0029]=r.a
        while True:  # natural loop $B59B
            try:
                m[0x0023]=self._shift(m[0x0023],False,rotate=False)
                yield from self._checkpoint(0xB59E)
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
                yield from self._checkpoint(0xB5D2)
                if not r.p&N:
                    continue
                else:
                    pass
                yield from self._checkpoint(0xB5D4)
                self._rts();return
            except _ContinueLoop_B59B:
                continue

    def draw_ai_rng_byte(self):
        """$B5D5: draw ai rng byte; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB5D5)
        m[RNG_SAVED_X]=r.x
        self._x(m[RNG_CURSOR])
        self._a(m[(0xB5E5+r.x)&65535])
        m[RNG_CURSOR]=self._nz(m[RNG_CURSOR]+1)
        self._x(m[RNG_SAVED_X])
        yield from self._checkpoint(0xB5E4)
        self._rts();return

    def normalized_terrain_at_scratch_xy(self):
        """$B6E5: normalized terrain at scratch xy; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB6E5)
        if not (yield from self._local_call(self.tactical_helper_b6ef,0xB6E5,0xB6E8)):return
        self._compare(r.a,0x06)
        yield from self._checkpoint(0xB6EA)
        if not r.p&C:
            pass
        else:
            self._a(0x02)
            pass
        return (yield from self.tactical_helper_b6ee())

    def tactical_helper_b6ee(self):
        """$B6EE: tactical helper b6ee; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB6EE)
        self._rts();return

    def tactical_helper_b6ef(self):
        """$B6EF: tactical helper b6ef; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB6EF)
        self._y(0x00)
        self._a(m[0x0020])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xB6F6)
        if not r.p&C:
            pass
        else:
            self._y(0x01)
            pass
        return (yield from self.tactical_helper_b6fa())

    def tactical_helper_b6fa(self):
        """$B6FA: tactical helper b6fa; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB6FA)
        self._a(m[0x0021])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xB6FF)
        if not r.p&C:
            pass
        else:
            self._a(r.y)
            self._a(r.a | 0x02)
            self._y(r.a)
            pass
        return (yield from self.read_terrain_chunk())

    def read_terrain_chunk(self):
        """$B705: read terrain chunk; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB705)
        self._a(m[((m[0xA8]|m[0xA9]<<8)+r.y)&65535])
        self._push(r.a)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xB7CB+r.y)&65535])
        m[0x0022]=r.a
        self._a(m[(0xB7CC+r.y)&65535])
        m[0x0023]=r.a
        self._a(self._pop())
        self._y(r.a)
        self._a(m[(0xB8BB+r.y)&65535])
        self._y(r.a)
        yield from self._external(0xB71C,0xF266,0xB71F,"call",None)
        if r.pc!=0xB71F:return  # preserve nonlocal stack return
        self._a(0x4B)
        m[0x0024]=r.a
        self._a(0xB7)
        m[0x0025]=r.a
        self._a(m[0x0020])
        self._a(r.a & 0x0F)
        m[0x0026]=r.a
        self._x(0x00)
        self._a(m[0x0021])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._a(r.a | m[0x0026])
        self._y(r.a)
        self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])
        self._y(r.a)
        self._compare(r.a,0x80)
        yield from self._checkpoint(0xB743)
        if not r.p&C:
            self._a(m[((m[0x24]|m[0x25]<<8)+r.y)&65535])
            yield from self._checkpoint(0xB74A)
            self._rts();return
        else:
            self._a(0x00)
            yield from self._checkpoint(0xB747)
            self._rts();return

    def consume_opposite_ambush_cache(self):
        """$B933: consume opposite ambush cache; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB933)
        self._a(0xFF)
        m[PROPOSAL_STATUS]=r.a
        self._y(0x04)
        self._a(m[SIDE])
        yield from self._checkpoint(0xB93D)
        if not r.p&N:
            pass
        else:
            self._y(0x00)
            pass
        return (yield from self.tactical_helper_b941())

    def tactical_helper_b941(self):
        """$B941: tactical helper b941; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB941)
        m[0x002A]=r.y
        self._a(m[(0x04D8+r.y)&65535])
        self._compare(r.a,0xFF)
        yield from self._checkpoint(0xB949)
        if not r.p&Z:
            self._a(m[(0x04D9+r.y)&65535])
            m[0x0020]=r.a
            self._a(m[(0x04DA+r.y)&65535])
            m[0x0021]=r.a
            self._x(m[ACTOR_SLOT])
            self._a(m[(UNIT_X+r.x)&65535])
            self._compare(r.a,m[0x0020])
            yield from self._checkpoint(0xB963)
            if not r.p&Z:
                return (yield from self.tactical_helper_b96d())
            else:
                self._a(m[(UNIT_Y+r.y)&65535])
                self._compare(r.a,m[0x0021])
                yield from self._checkpoint(0xB96B)
                if r.p&Z:
                    return (yield from self.tactical_helper_b98d())
                else:
                    return (yield from self.tactical_helper_b96d())
        else:
            return (yield from self.tactical_helper_baad())

    def tactical_helper_b96d(self):
        """$B96D: tactical helper b96d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB96D)
        self._a(m[0x0021])
        self._compare(r.a,0x10)
        yield from self._checkpoint(0xB972)
        if not r.p&C:
            pass
        else:
            self._flag(C,True)
            self._add(0x01,subtract=True)
            m[0x0021]=r.a
            pass
        return (yield from self.tactical_helper_b97a())

    def tactical_helper_b97a(self):
        """$B97A: tactical helper b97a; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB97A)
        self._a(0x02)
        m[0x0022]=r.a
        if not (yield from self._local_call(self.tactical_helper_a8e8,0xB97F,0xB982)):return
        self._x(m[ACTOR_SLOT])
        self._a(m[(0x6FC9+r.x)&65535])
        yield from self._checkpoint(0xB988)
        if not r.p&Z:
            return (yield from self.tactical_helper_b98d())
        else:
            return (yield from self.tactical_helper_baad())

    def tactical_helper_b98d(self):
        """$B98D: tactical helper b98d; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB98D)
        self._x(m[ACTOR_SLOT])
        self._a(m[(UNIT_X+r.x)&65535])
        m[0x0020]=r.a
        self._a(m[(UNIT_Y+r.x)&65535])
        m[0x0021]=r.a
        if not (yield from self._local_call(self.normalized_terrain_at_scratch_xy,0xB99C,0xB99F)):return
        self._compare(r.a,0x00)
        yield from self._checkpoint(0xB9A1)
        if r.p&Z:
            self._y(m[0x002A])
            self._a(m[(0x04D8+r.y)&65535])
            self._x(r.a)
            self._a(m[(UNIT_IDS+r.x)&65535])
            if not (yield from self._local_call(self.tactical_helper_b491,0xB9B0,0xB9B3)):return
            self._y(0x02)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            m[0x0023]=r.a
            self._y(0x0B)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            m[0x0024]=r.a
            self._y(m[ACTOR_SLOT])
            self._a(m[(UNIT_IDS+r.y)&65535])
            if not (yield from self._local_call(self.tactical_helper_b491,0xB9C7,0xB9CA)):return
            self._y(0x02)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
            m[0x0022]=r.a
            self._a(m[0x0023])
            self._flag(C,True)
            self._add(m[0x0022],subtract=True)
            yield from self._checkpoint(0xB9D8)
            if not r.p&N:
                pass
            else:
                self._a(0x00)
                pass
            return (yield from self.tactical_helper_b9dc())
        else:
            return (yield from self.tactical_helper_baad())

    def tactical_helper_b9dc(self):
        """$B9DC: tactical helper b9dc; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xB9DC)
        self._flag(C,False)
        self._add(0x0A)
        m[0x0020]=r.a
        while True:  # natural loop $B9E2
            try:
                if not (yield from self._local_call(self.draw_ai_rng_byte,0xB9E2,0xB9E5)):return
                self._compare(r.a,0x65)
                yield from self._checkpoint(0xB9E7)
                if r.p&C:
                    continue
                else:
                    pass
                self._a(m[0x0024])
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                r.a=self._shift(r.a,True,rotate=False)
                self._flag(C,False)
                self._add(m[0x0024])
                self._add(m[0x0024])
                m[0x002A]=r.a
                self._a(m[0x0023])
                m[0x0020]=r.a
                self._a(0x00)
                m[0x0021]=r.a
                m[0x0022]=r.a
                while True:  # natural loop $BA07
                    try:
                        if not (yield from self._local_call(self.draw_ai_rng_byte,0xBA07,0xBA0A)):return
                        self._compare(r.a,0x0B)
                        yield from self._checkpoint(0xBA0C)
                        if r.p&C:
                            continue
                        else:
                            pass
                        self._flag(C,False)
                        self._add(0x1E)
                        m[0x0023]=r.a
                        if not (yield from self._local_call(self.multiply_u24_by_u8,0xBA14,0xBA17)):return
                        self._a(m[0x0026])
                        m[0x0020]=r.a
                        self._a(m[0x0027])
                        m[0x0021]=r.a
                        self._a(0x0A)
                        m[0x0023]=r.a
                        self._a(0x00)
                        m[0x0022]=r.a
                        m[0x0024]=r.a
                        if not (yield from self._local_call(self.divide_u24_by_u16,0xBA30,0xBA33)):return
                        self._a(m[0x0020])
                        self._flag(C,False)
                        self._add(m[0x002A])
                        m[0x0022]=r.a
                        self._a(m[0x0021])
                        self._add(0x00)
                        m[0x0023]=r.a
                        self._y(m[ACTOR_SLOT])
                        self._a(m[(UNIT_IDS+r.y)&65535])
                        if not (yield from self._local_call(self.tactical_helper_b491,0xBA4B,0xBA4E)):return
                        self._y(0x08)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        m[0x0024]=r.a
                        self._y(r.y+1)
                        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                        self._a(r.a & 0x03)
                        m[0x0025]=r.a
                        self._a(m[0x0024])
                        self._flag(C,True)
                        self._add(m[0x0022],subtract=True)
                        m[0x0026]=r.a
                        self._a(m[0x0025])
                        self._add(m[0x0023],subtract=True)
                        m[0x0027]=r.a
                        yield from self._checkpoint(0xBA70)
                        if r.p&C:
                            pass
                        else:
                            self._a(m[0x0024])
                            m[0x0022]=r.a
                            self._a(m[0x0025])
                            m[0x0023]=r.a
                            self._a(0x00)
                            m[0x0026]=r.a
                            m[0x0027]=r.a
                            pass
                        return (yield from self.tactical_helper_ba86())
                    except _ContinueLoop_BA07:
                        continue
            except _ContinueLoop_B9E2:
                continue

    def tactical_helper_ba86(self):
        """$BA86: tactical helper ba86; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBA86)
        self._y(0x08)
        self._a(m[0x0026])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._y(r.y+1)
        self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
        self._a(r.a & 0xFC)
        self._a(r.a | m[0x0027])
        m[((m[0x20]|m[0x21]<<8)+r.y)&65535]=r.a
        self._a(m[0x0022])
        m[0x042C]=r.a
        self._a(m[0x0023])
        m[0x042D]=r.a
        self._a(0x00)
        m[0x042E]=r.a
        self._a(0x00)
        m[PROPOSAL_STATUS]=r.a
        return (yield from self.tactical_helper_baad())

    def tactical_helper_baad(self):
        """$BAAD: tactical helper baad; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        yield from self._checkpoint(0xBAAD)
        self._a(0xFF)
        m[REQUEST]=r.a
        yield from self._checkpoint(0xBAB2)
        self._rts();return

