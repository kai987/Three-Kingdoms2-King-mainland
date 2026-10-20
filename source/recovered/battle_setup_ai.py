"""Readable bank8/9 battle setup and NMI auxiliary software.

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
class SetupRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA003

class BattleSetupAI:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned battle ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=SetupRegisters();self.events=[];self.pending=None;self._program=None
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
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending,setup_fields=self.setup_state())
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA003,registers=registers,**kwargs)
    def run_entry(self,entry=0xA003,*,registers=None,seed_return=False,return_pc=0x0200,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        self.registers=registers or SetupRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc!=0x0200:raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=return_pc;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

    def setup_state(self):
        m=self.memory
        return dict(side_base=m[0x6F91],noncommander_count_work=m[0x6F94],
                    scan_cursor=m[0x6F94],status3_count=m[0x6F95],qualified_attempts=m[0x6F96],
                    strategy_parameters=list(m[0x6F99+i]for i in range(8)),
                    unit_strategies=list(m[0x6FA1+i]for i in range(20)),
                    auxiliary_cache=list(m[0x6FC9+i]for i in range(20)),
                    ambush_cache=list(m[0x4D8+i]for i in range(8)),
                    camera_request=m[0x508],camera_x=m[0x8E]|m[0x8F]<<8,camera_y=m[0x90]|m[0x91]<<8)
    def initialize(self,**kwargs):return self.run_entry(0xA003,**kwargs)
    def draw_HUD(self,**kwargs):return self.run_entry(0xA012,**kwargs)
    def draw_units(self,**kwargs):return self.run_entry(0xA015,**kwargs)
    def step_camera(self,**kwargs):return self.run_entry(0xA021,**kwargs)

    def _entry(self,entry):
        if entry==0xA003:return self.initialize_entry()
        elif entry==0xA012:return self.HUD_entry()
        elif entry==0xA015:return self.units_entry()
        elif entry==0xA021:return self.camera_entry()
        elif entry==0xB130:return self.initialize_battle_AI()
        elif entry==0xB1B0:return self.assign_strategies_and_positions()
        elif entry==0xB2AE:return self.first_side_formation()
        elif entry==0xB312:return self.second_side_formation()
        elif entry==0xB371:return self.sort_noncommanders_by_martial()
        elif entry==0xB3D2:return self.swap_three_unit_arrays()
        elif entry==0xB491:return self.officer_pointer_20()
        elif entry==0xB4C2:return self.ruler_pointer_20()
        elif entry==0xCFA2:return self.battle_HUD()
        elif entry==0xD126:return self.draw_HUD_digit()
        elif entry==0xD1ED:return self.battle_unit_sprites()
        elif entry==0xD296:return self.local_d296()
        elif entry==0xD2F5:return self.select_unit_CHR()
        elif entry==0xD337:return self.world_viewport_test()
        elif entry==0xD57B:return self.advance_camera()
        raise ValueError("Entry is outside bank8/9 setup procedure catalog")

    def initialize_entry(self):
        """$A003: initialize entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA003)
        return (yield from self.initialize_battle_AI())

    def HUD_entry(self):
        """$A012: HUD entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA012)
        return (yield from self.battle_HUD())

    def units_entry(self):
        """$A015: units entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA015)
        return (yield from self.battle_unit_sprites())

    def camera_entry(self):
        """$A021: camera entry; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xA021)
        return (yield from self.advance_camera())

    def initialize_battle_AI(self):
        """$B130: initialize battle AI; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB130)
        self._y(0x00)
        self._a(0xFF)
        while True:  # natural loop $B134
            m[(0x6FA1+r.y)&65535]=r.a
            self._y(r.y+1)
            self._compare(r.y,0x40)
            self._mark(0xB13A)
            if not r.p&C:
                continue
            else:
                pass
            self._y(0x00)
            self._a(0x00)
            while True:  # natural loop $B140
                m[(0x6FC9+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xB146)
                if not r.p&C:
                    continue
                else:
                    pass
                self._a(m[RULERS])
                self._a(r.a & 0x0F)
                m[0x0022]=r.a
                if not (yield from self._local_call(self.ruler_pointer_20,0xB150,0xB153)):return
                self._y(0x03)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xB159)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x00)
                    m[0x6F91]=r.a
                    m[0x6FA1]=r.a
                    if not (yield from self._local_call(self.sort_noncommanders_by_martial,0xB163,0xB166)):return
                    self._a(0x00)
                    m[0x0020]=r.a
                    if not (yield from self._local_call(self.assign_strategies_and_positions,0xB16B,0xB16E)):return
                    pass
                self._a(m[RULERS])
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                r.a=self._shift(r.a,False,rotate=False)
                m[0x0022]=r.a
                if not (yield from self._local_call(self.ruler_pointer_20,0xB178,0xB17B)):return
                self._y(0x03)
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535])
                self._compare(r.a,0x03)
                self._mark(0xB181)
                if not r.p&Z:
                    pass
                else:
                    self._a(0x0A)
                    m[0x6F91]=r.a
                    self._a(0x00)
                    m[0x6FAB]=r.a
                    if not (yield from self._local_call(self.sort_noncommanders_by_martial,0xB18D,0xB190)):return
                    self._a(0x36)
                    m[0x0020]=r.a
                    if not (yield from self._local_call(self.assign_strategies_and_positions,0xB195,0xB198)):return
                    pass
                self._y(0x00)
                self._a(0xFF)
                while True:  # natural loop $B19C
                    m[(0x04D8+r.y)&65535]=r.a
                    self._y(r.y+1)
                    self._compare(r.y,0x08)
                    self._mark(0xB1A2)
                    if not r.p&C:
                        continue
                    else:
                        pass
                    self._a(0x00)
                    m[0x6F94]=r.a
                    m[0x6F95]=r.a
                    m[0x6F96]=r.a
                    self._mark(0xB1AF)
                    self._rts();return

    def assign_strategies_and_positions(self):
        """B1B0: select one profile, distribute four groups and set formation.

        The commander keeps strategy0. Noncommanders have already undergone
        the exact martial adjacent swaps. Old profile cache survives count0.
        """
        r=self.registers;m=self.memory;self._mark(0xB1B0)
        self._a(m[0x22])
        family=18 if r.a in(1,5)else 36 if r.a in(2,4)else 0
        self._a(family);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
        self._a(m[0x6F94])
        if r.a:
            self._flag(C,True);self._add(1,subtract=True)
            r.a=self._shift(r.a,True);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
            self._a(0xFD);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
            self._a(0xB3);self._add(0);m[0x21]=r.a
            self._x(0);self._a(m[0x6F91])
            if r.a:self._x(4)
            self._y(0)
            # Two bytes unpack into counts for strategy IDs1,2,3,4.
            while True:
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x22]=r.a
                for _ in range(4):r.a=self._shift(r.a,False)
                m[0x6F99+r.x]=r.a
                self._a(m[0x22]);self._a(r.a&15);m[0x6F9A+r.x]=r.a
                self._x(r.x+1);self._x(r.x+1);self._y(r.y+1);self._compare(r.y,2)
                if r.p&C:break
            self._x(0);self._a(m[0x6F91])
            if r.a:self._x(4)
            self._a(r.x);self._flag(C,False);self._add(4);m[0x22]=r.a
            self._a(1);m[0x20]=r.a;self._y(m[0x6F91]);self._y(r.y+1)
            while True:
                self._a(m[0x6F99+r.x])
                if r.a:
                    m[0x21]=r.a
                    while True:
                        self._a(m[0x20]);m[0x6FA1+r.y]=r.a;self._y(r.y+1)
                        m[0x21]=self._nz(m[0x21]-1);self._a(m[0x21])
                        if not r.a:break
                m[0x20]=self._nz(m[0x20]+1);self._x(r.x+1);self._compare(r.x,m[0x22])
                if r.p&C:break
        self._a(m[0x6F91])
        if r.a:
            if not(yield from self._local_call(self.second_side_formation,0xB263,0xB266)):return
        else:
            if not(yield from self._local_call(self.first_side_formation,0xB25D,0xB260)):return
        self._x(m[0x6F91]);self._a(r.x);self._flag(C,False);self._add(10);m[0x2A]=r.a
        self._y(0);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x614+r.x]=r.a
        self._y(r.y+1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x600+r.x]=r.a;self._x(r.x+1)
        while True:
            self._a(m[0x6FA1+r.x]);self._compare(r.a,255)
            if r.p&Z:break
            self._flag(C,True);self._add(1,subtract=True);m[0x2B]=r.a;self._y(r.a)
            self._a(m[0x22+r.y]);self._y(r.a)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x614+r.x]=r.a
            self._y(r.y+1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x600+r.x]=r.a
            self._y(m[0x2B]);self._a(m[0x22+r.y]);self._flag(C,False);self._add(2);m[0x22+r.y]=r.a
            self._x(r.x+1);self._compare(r.x,m[0x2A])
            if r.p&C:break
        self._rts()

    def first_side_formation(self):
        """$B2AE: first side formation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB2AE)
        self._y(0x30)
        yield from self._external(0xB2B0,0xF266,0xB2B3,"call",None)
        if r.pc!=0xB2B3:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        while True:  # natural loop $B2BA
            self._a(m[(0x9D72+r.y)&65535])
            self._mark(0xB2BD)
            if not r.p&N:
                self._compare(r.a,m[0x052A])
                self._mark(0xB2C7)
                if r.p&Z:
                    self._a(r.y)
                    self._push(r.a)
                    self._y(0x31)
                    yield from self._external(0xB2D1,0xF266,0xB2D4,"call",None)
                    if r.pc!=0xB2D4:return  # preserve nonlocal stack return
                    self._a(self._pop())
                    self._y(r.a)
                    self._a(m[(0x9AB4+r.y)&65535])
                    pass
                else:
                    self._y(r.y+1)
                    continue
                pass
            else:
                self._a(0x00)
                pass
            m[0x0020]=r.a
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0020]=r.a
            self._y(0x26)
            yield from self._external(0xB2E6,0xF266,0xB2E9,"call",None)
            if r.pc!=0xB2E9:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x8C52+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0020])
            m[0x0020]=r.a
            self._a(m[(0x8C53+r.y)&65535])
            self._add(0x00)
            m[0x0021]=r.a
            self._y(0x00)
            while True:  # natural loop $B302
                self._a(m[(0xB30E+r.y)&65535])
                m[(0x0022+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x04)
                self._mark(0xB30B)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB30D)
                self._rts();return

    def second_side_formation(self):
        """$B312: second side formation; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB312)
        self._y(0x30)
        yield from self._external(0xB314,0xF266,0xB317,"call",None)
        if r.pc!=0xB317:return  # preserve nonlocal stack return
        self._a(m[CITY])
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        while True:  # natural loop $B31E
            self._a(m[(0x9D72+r.y)&65535])
            self._mark(0xB321)
            if not r.p&N:
                self._compare(r.a,m[0x052A])
                self._mark(0xB32B)
                if r.p&Z:
                    self._a(m[(0x9E62+r.y)&65535])
                    pass
                else:
                    self._y(r.y+1)
                    continue
                pass
            else:
                self._a(0x00)
                pass
            m[0x0020]=r.a
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._flag(C,False)
            self._add(m[0x0020])
            r.a=self._shift(r.a,True,rotate=False)
            m[0x0020]=r.a
            self._y(0x26)
            yield from self._external(0xB345,0xF266,0xB348,"call",None)
            if r.pc!=0xB348:return  # preserve nonlocal stack return
            self._a(m[CITY])
            r.a=self._shift(r.a,True,rotate=False)
            self._y(r.a)
            self._a(m[(0x8000+r.y)&65535])
            self._flag(C,False)
            self._add(m[0x0020])
            m[0x0020]=r.a
            self._a(m[(0x8001+r.y)&65535])
            self._add(0x00)
            m[0x0021]=r.a
            self._y(0x00)
            while True:  # natural loop $B361
                self._a(m[(0xB36D+r.y)&65535])
                m[(0x0022+r.y)&65535]=r.a
                self._y(r.y+1)
                self._compare(r.y,0x04)
                self._mark(0xB36A)
                if not r.p&C:
                    continue
                else:
                    pass
                self._mark(0xB36C)
                self._rts();return

    def sort_noncommanders_by_martial(self):
        """B371: exclude commander, count occupied slots, swap three arrays.

        Adjacent ties also swap. Each outer pass repeats the full comparison
        range; this is deliberately not Python's stable sorted().
        """
        r=self.registers;m=self.memory;self._mark(0xB371)
        self._a(m[0x6F91]);self._y(r.a);self._flag(C,False);self._add(10);m[0x2A]=r.a
        self._x(0)
        while True:
            self._a(m[0x664+r.y]);self._compare(r.a,255)
            if not r.p&Z:self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,m[0x2A])
            if r.p&C:break
        self._x(r.x-1);m[0x6F94]=r.x;self._compare(r.x,2)
        if not r.p&C:self._rts();return
        self._y(1)
        while True:
            self._a(r.y);self._push(r.a);self._x(m[0x6F91]);self._a(r.x)
            self._flag(C,False);self._add(m[0x6F94]);m[0x2B]=r.a;self._x(r.x+1)
            while True:
                self._a(m[0x664+r.x])
                if not(yield from self._local_call(self.officer_pointer_20,0xB3A7,0xB3AA)):return
                self._y(1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x2A]=r.a
                self._a(m[0x665+r.x])
                if not(yield from self._local_call(self.officer_pointer_20,0xB3B4,0xB3B7)):return
                self._y(1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);self._compare(r.a,m[0x2A])
                if r.p&C:
                    if not(yield from self._local_call(self.swap_three_unit_arrays,0xB3C0,0xB3C3)):return
                self._x(r.x+1);self._compare(r.x,m[0x2B])
                if r.p&C:break
            self._a(self._pop());self._y(r.a);self._y(r.y+1);self._compare(r.y,m[0x6F94])
            if r.p&C:break
        self._rts()

    def swap_three_unit_arrays(self):
        """$B3D2: swap three unit arrays; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB3D2)
        self._a(m[(0x0664+r.x)&65535])
        self._y(r.a)
        self._a(m[(0x0665+r.x)&65535])
        m[(0x0664+r.x)&65535]=r.a
        self._a(r.y)
        m[(0x0665+r.x)&65535]=r.a
        self._a(m[(0x0628+r.x)&65535])
        self._y(r.a)
        self._a(m[(0x0629+r.x)&65535])
        m[(0x0628+r.x)&65535]=r.a
        self._a(r.y)
        m[(0x0629+r.x)&65535]=r.a
        self._a(m[(0x063C+r.x)&65535])
        self._y(r.a)
        self._a(m[(0x063D+r.x)&65535])
        m[(0x063C+r.x)&65535]=r.a
        self._a(r.y)
        m[(0x063D+r.x)&65535]=r.a
        self._mark(0xB3FC)
        self._rts();return

    def officer_pointer_20(self):
        """$B491: officer pointer 20; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB491)
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
        self._mark(0xB4C1)
        self._rts();return

    def ruler_pointer_20(self):
        """$B4C2: ruler pointer 20; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xB4C2)
        self._a(r.a & 0x0F)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xB4D3+r.y)&65535])
        m[0x0020]=r.a
        self._a(m[(0xB4D4+r.y)&65535])
        m[0x0021]=r.a
        self._mark(0xB4D2)
        self._rts();return

    def battle_HUD(self):
        """$CFA2: battle HUD; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xCFA2)
        self._a(m[0x008F])
        self._mark(0xCFA5)
        if not r.p&Z:
            self._mark(0xCFBA)
            self._rts();return
        else:
            self._a(m[ANIMATION])
            self._mark(0xCFAA)
            if not r.p&Z:
                self._mark(0xCFBA)
                self._rts();return
            else:
                self._a(m[STATE])
                self._compare(r.a,0x0C)
                self._mark(0xCFB1)
                if r.p&C:
                    self._mark(0xCFBA)
                    self._rts();return
                else:
                    self._a(m[0x005E])
                    self._a(r.a & 0x20)
                    self._mark(0xCFB8)
                    if not r.p&Z:
                        self._a(0x20)
                        m[0x000A]=r.a
                        self._a(0xB0)
                        m[0x000C]=r.a
                        self._a(0x3C)
                        m[0x0000]=r.a
                        self._a(0xD1)
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        yield from self._external(0xCFD4,0xF1AD,0xCFD7,"call",None)
                        if r.pc!=0xCFD7:return  # preserve nonlocal stack return
                        self._a(0x5D)
                        m[0x0000]=r.a
                        self._a(0xD1)
                        m[0x0001]=r.a
                        self._a(m[0x005E])
                        self._a(r.a & 0x40)
                        self._mark(0xCFE6)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(0x6E)
                            m[0x0000]=r.a
                            self._a(0xD1)
                            m[0x0001]=r.a
                            pass
                        yield from self._external(0xCFF2,0xF1AD,0xCFF5,"call",None)
                        if r.pc!=0xCFF5:return  # preserve nonlocal stack return
                        self._a(m[AP])
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        m[0x0003]=r.a
                        yield from self._external(0xD003,0xE9BA,0xD006,"call",None)
                        if r.pc!=0xD006:return  # preserve nonlocal stack return
                        self._a(m[0x0007])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xD00D)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x20)
                            m[0x000A]=r.y
                            self._y(0xE0)
                            m[0x000C]=r.y
                            if not (yield from self._local_call(self.draw_HUD_digit,0xD019,0xD01C)):return
                            pass
                        self._a(m[0x0007])
                        self._a(r.a & 0x0F)
                        self._y(0x20)
                        m[0x000A]=r.y
                        self._y(0xE8)
                        m[0x000C]=r.y
                        if not (yield from self._local_call(self.draw_HUD_digit,0xD02B,0xD02E)):return
                        self._a(m[ROUND])
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        m[0x0003]=r.a
                        yield from self._external(0xD03C,0xE9BA,0xD03F,"call",None)
                        if r.pc!=0xD03F:return  # preserve nonlocal stack return
                        self._a(m[0x0007])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xD046)
                        if r.p&Z:
                            pass
                        else:
                            self._y(0x10)
                            m[0x000A]=r.y
                            self._y(0xD0)
                            m[0x000C]=r.y
                            if not (yield from self._local_call(self.draw_HUD_digit,0xD052,0xD055)):return
                            pass
                        self._a(m[0x0007])
                        self._a(r.a & 0x0F)
                        self._y(0x10)
                        m[0x000A]=r.y
                        self._y(0xD8)
                        m[0x000C]=r.y
                        if not (yield from self._local_call(self.draw_HUD_digit,0xD064,0xD067)):return
                        self._a(m[0x005E])
                        self._a(r.a & 0x40)
                        self._mark(0xD06C)
                        if not r.p&Z:
                            self._x(0x00)
                            self._a(m[SIDE])
                            self._mark(0xD09D)
                            if not r.p&N:
                                pass
                            else:
                                self._x(0x02)
                                pass
                            self._a(m[(0x0526+r.x)&65535])
                            m[0x0001]=r.a
                            self._a(m[(0x0527+r.x)&65535])
                            m[0x0002]=r.a
                            self._a(0x00)
                            m[0x0003]=r.a
                            yield from self._external(0xD0B2,0xE9BA,0xD0B5,"call",None)
                            if r.pc!=0xD0B5:return  # preserve nonlocal stack return
                            self._a(0x40)
                            m[0x0010]=r.a
                            self._a(0x00)
                            m[0x0011]=r.a
                            pass
                        else:
                            self._x(0x00)
                            self._a(m[SIDE])
                            self._mark(0xD073)
                            if not r.p&N:
                                pass
                            else:
                                self._x(0x02)
                                pass
                            self._a(m[(0x0522+r.x)&65535])
                            m[0x0001]=r.a
                            self._a(m[(0x0523+r.x)&65535])
                            m[0x0002]=r.a
                            self._a(0x00)
                            m[0x0003]=r.a
                            yield from self._external(0xD088,0xE9BA,0xD08B,"call",None)
                            if r.pc!=0xD08B:return  # preserve nonlocal stack return
                            self._a(0x40)
                            m[0x0010]=r.a
                            self._a(0x00)
                            m[0x0011]=r.a
                            pass
                        self._a(m[0x0008])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xD0C6)
                        if r.p&Z:
                            pass
                        else:
                            m[0x0011]=self._nz(m[0x0011]+1)
                            self._y(m[0x0010])
                            m[0x000A]=r.y
                            self._y(0xD0)
                            m[0x000C]=r.y
                            if not (yield from self._local_call(self.draw_HUD_digit,0xD0D6,0xD0D9)):return
                            pass
                        self._a(m[0x0008])
                        self._a(r.a & 0x0F)
                        self._mark(0xD0DE)
                        if not r.p&Z:
                            m[0x0011]=self._nz(m[0x0011]+1)
                            self._y(m[0x0010])
                            m[0x000A]=r.y
                            self._y(0xD8)
                            m[0x000C]=r.y
                            if not (yield from self._local_call(self.draw_HUD_digit,0xD0F3,0xD0F6)):return
                            pass
                        else:
                            self._y(m[0x0011])
                            self._mark(0xD0E3)
                            if r.p&Z:
                                pass
                            else:
                                m[0x0011]=self._nz(m[0x0011]+1)
                                self._y(m[0x0010])
                                m[0x000A]=r.y
                                self._y(0xD8)
                                m[0x000C]=r.y
                                if not (yield from self._local_call(self.draw_HUD_digit,0xD0F3,0xD0F6)):return
                                pass
                            pass
                        self._a(m[0x0007])
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        r.a=self._shift(r.a,False,rotate=False)
                        self._mark(0xD0FD)
                        if not r.p&Z:
                            self._y(m[0x0010])
                            m[0x000A]=r.y
                            self._y(0xE0)
                            m[0x000C]=r.y
                            if not (yield from self._local_call(self.draw_HUD_digit,0xD10F,0xD112)):return
                            pass
                        else:
                            self._y(m[0x0011])
                            self._mark(0xD102)
                            if r.p&Z:
                                pass
                            else:
                                self._y(m[0x0010])
                                m[0x000A]=r.y
                                self._y(0xE0)
                                m[0x000C]=r.y
                                if not (yield from self._local_call(self.draw_HUD_digit,0xD10F,0xD112)):return
                                pass
                            pass
                        self._a(m[0x0007])
                        self._a(r.a & 0x0F)
                        self._y(m[0x0010])
                        m[0x000A]=r.y
                        self._y(0xE8)
                        m[0x000C]=r.y
                        if not (yield from self._local_call(self.draw_HUD_digit,0xD122,0xD125)):return
                        self._mark(0xD125)
                        self._rts();return
                    else:
                        self._mark(0xCFBA)
                        self._rts();return

    def draw_HUD_digit(self):
        """$D126: draw HUD digit; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD126)
        r.a=self._shift(r.a,True,rotate=False)
        self._y(r.a)
        self._a(m[(0xD17F+r.y)&65535])
        m[0x0000]=r.a
        self._a(m[(0xD180+r.y)&65535])
        m[0x0001]=r.a
        self._a(0x00)
        m[0x0002]=r.a
        self._mark(0xD139)
        yield from self._external(0xD139,0xF1AD,None,"tail")
        return

    def battle_unit_sprites(self):
        """$D1ED: battle unit sprites; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD1ED)
        self._a(m[0x008F])
        self._mark(0xD1F0)
        if not r.p&Z:
            self._mark(0xD1F9)
            self._rts();return
        else:
            self._a(m[STATE])
            self._compare(r.a,0x0C)
            self._mark(0xD1F7)
            if not r.p&C:
                if not (yield from self._local_call(self.select_unit_CHR,0xD1FA,0xD1FD)):return
                self._a(m[0x0061])
                self._compare(r.a,0x07)
                self._mark(0xD202)
                if r.p&Z:
                    self._mark(0xD1F9)
                    self._rts();return
                else:
                    self._y(0x31)
                    yield from self._external(0xD206,0xF25F,0xD209,"call",None)
                    if r.pc!=0xD209:return  # preserve nonlocal stack return
                    self._a(m[CITY])
                    r.a=self._shift(r.a,True,rotate=False)
                    r.a=self._shift(r.a,True,rotate=False)
                    self._y(r.a)
                    self._a(m[(0x9D58+r.y)&65535])
                    m[0x000A]=r.a
                    self._a(m[(0x9D59+r.y)&65535])
                    m[0x000B]=r.a
                    self._a(m[(0x9D5A+r.y)&65535])
                    m[0x000C]=r.a
                    self._a(m[(0x9D5B+r.y)&65535])
                    m[0x000D]=r.a
                    if not (yield from self._local_call(self.world_viewport_test,0xD227,0xD22A)):return
                    self._mark(0xD22A)
                    if not r.p&C:
                        pass
                    else:
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(0x15)
                        m[0x0000]=r.a
                        self._a(0xD3)
                        m[0x0001]=r.a
                        self._a(0x00)
                        m[0x0002]=r.a
                        self._a(0x00)
                        m[0x0003]=r.a
                        self._a(0x9C)
                        m[0x0004]=r.a
                        yield from self._external(0xD24A,0xF09C,0xD24D,"call",None)
                        if r.pc!=0xD24D:return  # preserve nonlocal stack return
                        pass
                    self._y(0x31)
                    yield from self._external(0xD24F,0xF25F,0xD252,"call",None)
                    if r.pc!=0xD252:return  # preserve nonlocal stack return
                    self._a(m[CITY])
                    r.a=self._shift(r.a,True,rotate=False)
                    self._flag(C,False)
                    self._add(m[CITY])
                    r.a=self._shift(r.a,True,rotate=False)
                    self._push(r.a)
                    self._y(r.a)
                    self._a(m[(0x9BA4+r.y)&65535])
                    self._mark(0xD260)
                    if r.p&N:
                        pass
                    else:
                        m[0x000C]=r.a
                        self._a(m[(0x9BA5+r.y)&65535])
                        m[0x000A]=r.a
                        if not (yield from self._local_call(self.local_d296,0xD26B,0xD26E)):return
                        pass
                    self._a(self._pop())
                    self._push(r.a)
                    self._y(r.a)
                    self._a(m[(0x9BA6+r.y)&65535])
                    self._mark(0xD274)
                    if r.p&N:
                        pass
                    else:
                        m[0x000C]=r.a
                        self._a(m[(0x9BA7+r.y)&65535])
                        m[0x000A]=r.a
                        if not (yield from self._local_call(self.local_d296,0xD27F,0xD282)):return
                        pass
                    self._a(self._pop())
                    self._y(r.a)
                    self._a(m[(0x9BA8+r.y)&65535])
                    self._mark(0xD287)
                    if r.p&N:
                        pass
                    else:
                        m[0x000C]=r.a
                        self._a(m[(0x9BA9+r.y)&65535])
                        m[0x000A]=r.a
                        if not (yield from self._local_call(self.local_d296,0xD292,0xD295)):return
                        pass
                    self._mark(0xD295)
                    self._rts();return
            else:
                self._mark(0xD1F9)
                self._rts();return

    def local_d296(self):
        """$D296: local d296; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD296)
        self._a(0x00)
        m[0x000B]=r.a
        m[0x000D]=r.a
        m[0x000A]=self._shift(m[0x000A],True,rotate=False)
        m[0x000B]=self._shift(m[0x000B],True,rotate=True)
        m[0x000A]=self._shift(m[0x000A],True,rotate=False)
        m[0x000B]=self._shift(m[0x000B],True,rotate=True)
        m[0x000A]=self._shift(m[0x000A],True,rotate=False)
        m[0x000B]=self._shift(m[0x000B],True,rotate=True)
        m[0x000A]=self._shift(m[0x000A],True,rotate=False)
        m[0x000B]=self._shift(m[0x000B],True,rotate=True)
        m[0x000C]=self._shift(m[0x000C],True,rotate=False)
        m[0x000D]=self._shift(m[0x000D],True,rotate=True)
        m[0x000C]=self._shift(m[0x000C],True,rotate=False)
        m[0x000D]=self._shift(m[0x000D],True,rotate=True)
        m[0x000C]=self._shift(m[0x000C],True,rotate=False)
        m[0x000D]=self._shift(m[0x000D],True,rotate=True)
        m[0x000C]=self._shift(m[0x000C],True,rotate=False)
        m[0x000D]=self._shift(m[0x000D],True,rotate=True)
        if not (yield from self._local_call(self.world_viewport_test,0xD2CE,0xD2D1)):return
        self._mark(0xD2D1)
        if not r.p&C:
            self._mark(0xD2F4)
            self._rts();return
        else:
            self._a(0x00)
            m[0x0002]=r.a
            self._a(0x26)
            m[0x0000]=r.a
            self._a(0xD3)
            m[0x0001]=r.a
            self._a(0x00)
            m[0x0002]=r.a
            self._a(0x00)
            m[0x0003]=r.a
            self._a(0x9C)
            m[0x0004]=r.a
            self._mark(0xD2F1)
            yield from self._external(0xD2F1,0xF09C,None,"tail")
            return

    def select_unit_CHR(self):
        """$D2F5: select unit CHR; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD2F5)
        self._x(0x88)
        self._a(m[0x005E])
        self._a(r.a & 0x10)
        self._mark(0xD2FC)
        if r.p&Z:
            pass
        else:
            self._x(0x8B)
            pass
        m[0x00B2]=r.x
        m[0x00D6]=r.x
        self._a(m[ANIMATION])
        self._mark(0xD309)
        if not r.p&Z:
            pass
        else:
            m[0x00C2]=r.x
            m[0x00C6]=r.x
            m[0x00D2]=r.x
            pass
        self._mark(0xD314)
        self._rts();return

    def world_viewport_test(self):
        """$D337: world viewport test; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD337)
        self._a(m[0x000A])
        m[0x0000]=r.a
        self._a(m[0x000B])
        m[0x0001]=r.a
        self._a(m[0x000C])
        m[0x0002]=r.a
        self._a(m[0x000D])
        m[0x0003]=r.a
        m[0x0001]=self._shift(m[0x0001],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=True)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        m[0x0000]=self._shift(m[0x0000],False,rotate=False)
        m[0x0003]=self._shift(m[0x0003],False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=True)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        m[0x0002]=self._shift(m[0x0002],False,rotate=False)
        self._y(0x00)
        while True:  # natural loop $D36F
            self._a(m[(0x0600+r.y)&65535])
            self._compare(r.a,m[0x0002])
            self._mark(0xD375)
            if not r.p&Z:
                self._y(r.y+1)
                self._compare(r.y,0x14)
                self._mark(0xD38D)
                if not r.p&C:
                    continue
                else:
                    self._mark(0xD38F)
                    self._rts();return
            else:
                self._a(m[(0x0614+r.y)&65535])
                self._compare(r.a,m[0x0000])
                self._mark(0xD37D)
                if not r.p&Z:
                    self._y(r.y+1)
                    self._compare(r.y,0x14)
                    self._mark(0xD38D)
                    if not r.p&C:
                        continue
                    else:
                        self._mark(0xD38F)
                        self._rts();return
                else:
                    self._a(m[0x005E])
                    self._a(r.a & 0x40)
                    self._mark(0xD384)
                    if not r.p&Z:
                        self._flag(C,True)
                        self._mark(0xD389)
                        self._rts();return
                    else:
                        self._flag(C,False)
                        self._mark(0xD387)
                        self._rts();return

    def advance_camera(self):
        """$D57B: advance camera; retains flags/aliases/caller stack."""
        r=self.registers;m=self.memory
        if False:yield None
        self._mark(0xD57B)
        self._a(m[STATE])
        self._compare(r.a,0x0C)
        self._mark(0xD580)
        if not r.p&C:
            self._a(0x00)
            m[0x0000]=r.a
            self._a(m[0x0508])
            self._mark(0xD58B)
            if r.p&N:
                self._a(m[0x0508])
                self._a(r.a | 0x80)
                m[0x0508]=r.a
                self._a(m[0x008E])
                self._flag(C,False)
                self._add(0x02)
                self._mark(0xD5A0)
                if r.p&C:
                    self._a(m[0x0508])
                    self._a(r.a & 0x7F)
                    m[0x0508]=r.a
                    pass
                else:
                    m[0x008E]=r.a
                    self._a(m[0x009C])
                    self._a(r.a & 0xBF)
                    self._a(r.a | 0x80)
                    m[0x009C]=r.a
                    self._a(m[0x008E])
                    self._a(r.a & 0x0E)
                    self._mark(0xD5B4)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0508])
                        self._a(r.a & 0x7F)
                        m[0x0508]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x0000])
                self._mark(0xD590)
                if not r.p&N:
                    pass
                else:
                    self._a(m[0x0508])
                    self._a(r.a | 0x80)
                    m[0x0508]=r.a
                    self._a(m[0x008E])
                    self._flag(C,False)
                    self._add(0x02)
                    self._mark(0xD5A0)
                    if r.p&C:
                        self._a(m[0x0508])
                        self._a(r.a & 0x7F)
                        m[0x0508]=r.a
                        pass
                    else:
                        m[0x008E]=r.a
                        self._a(m[0x009C])
                        self._a(r.a & 0xBF)
                        self._a(r.a | 0x80)
                        m[0x009C]=r.a
                        self._a(m[0x008E])
                        self._a(r.a & 0x0E)
                        self._mark(0xD5B4)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0508])
                            self._a(r.a & 0x7F)
                            m[0x0508]=r.a
                            pass
                        pass
                    pass
                pass
            self._a(m[0x0508])
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xD5C2)
            if r.p&N:
                self._a(m[0x0508])
                self._a(r.a | 0x40)
                m[0x0508]=r.a
                self._a(m[0x008E])
                self._flag(C,True)
                self._add(0x02,subtract=True)
                self._mark(0xD5D8)
                if not r.p&C:
                    self._a(m[0x0508])
                    self._a(r.a & 0xBF)
                    m[0x0508]=r.a
                    pass
                else:
                    m[0x008E]=r.a
                    self._a(m[0x009C])
                    self._a(r.a & 0x7F)
                    self._a(r.a | 0x40)
                    m[0x009C]=r.a
                    self._a(m[0x008E])
                    self._a(r.a & 0x0E)
                    self._mark(0xD5EC)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0508])
                        self._a(r.a & 0xBF)
                        m[0x0508]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x0000])
                r.a=self._shift(r.a,True,rotate=False)
                self._mark(0xD5C8)
                if not r.p&N:
                    pass
                else:
                    self._a(m[0x0508])
                    self._a(r.a | 0x40)
                    m[0x0508]=r.a
                    self._a(m[0x008E])
                    self._flag(C,True)
                    self._add(0x02,subtract=True)
                    self._mark(0xD5D8)
                    if not r.p&C:
                        self._a(m[0x0508])
                        self._a(r.a & 0xBF)
                        m[0x0508]=r.a
                        pass
                    else:
                        m[0x008E]=r.a
                        self._a(m[0x009C])
                        self._a(r.a & 0x7F)
                        self._a(r.a | 0x40)
                        m[0x009C]=r.a
                        self._a(m[0x008E])
                        self._a(r.a & 0x0E)
                        self._mark(0xD5EC)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0508])
                            self._a(r.a & 0xBF)
                            m[0x0508]=r.a
                            pass
                        pass
                    pass
                pass
            self._a(m[0x0508])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xD5FB)
            if r.p&N:
                self._a(m[0x0508])
                self._a(r.a | 0x20)
                m[0x0508]=r.a
                self._a(m[0x0090])
                self._flag(C,True)
                self._add(0x02,subtract=True)
                self._mark(0xD612)
                if not r.p&C:
                    self._a(m[0x0508])
                    self._a(r.a & 0xDF)
                    m[0x0508]=r.a
                    pass
                else:
                    m[0x0090]=r.a
                    self._a(m[0x009C])
                    self._a(r.a & 0xDF)
                    self._a(r.a | 0x10)
                    m[0x009C]=r.a
                    self._a(m[0x0090])
                    self._a(r.a & 0x0E)
                    self._mark(0xD626)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0508])
                        self._a(r.a & 0xDF)
                        m[0x0508]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0x10)
                self._mark(0xD602)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x0508])
                    self._a(r.a | 0x20)
                    m[0x0508]=r.a
                    self._a(m[0x0090])
                    self._flag(C,True)
                    self._add(0x02,subtract=True)
                    self._mark(0xD612)
                    if not r.p&C:
                        self._a(m[0x0508])
                        self._a(r.a & 0xDF)
                        m[0x0508]=r.a
                        pass
                    else:
                        m[0x0090]=r.a
                        self._a(m[0x009C])
                        self._a(r.a & 0xDF)
                        self._a(r.a | 0x10)
                        m[0x009C]=r.a
                        self._a(m[0x0090])
                        self._a(r.a & 0x0E)
                        self._mark(0xD626)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0508])
                            self._a(r.a & 0xDF)
                            m[0x0508]=r.a
                            pass
                        pass
                    pass
                pass
            self._a(m[0x0508])
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            r.a=self._shift(r.a,True,rotate=False)
            self._mark(0xD636)
            if r.p&N:
                self._a(m[0x0508])
                self._a(r.a | 0x10)
                m[0x0508]=r.a
                self._a(m[0x0090])
                self._flag(C,False)
                self._add(0x02)
                self._compare(r.a,0x90)
                self._mark(0xD64F)
                if r.p&C:
                    self._a(m[0x0508])
                    self._a(r.a & 0xEF)
                    m[0x0508]=r.a
                    pass
                else:
                    m[0x0090]=r.a
                    self._a(m[0x009C])
                    self._a(r.a & 0xEF)
                    self._a(r.a | 0x20)
                    m[0x009C]=r.a
                    self._a(m[0x0090])
                    self._a(r.a & 0x0E)
                    self._mark(0xD663)
                    if not r.p&Z:
                        pass
                    else:
                        self._a(m[0x0508])
                        self._a(r.a & 0xEF)
                        m[0x0508]=r.a
                        pass
                    pass
                pass
            else:
                self._a(m[0x0000])
                self._a(r.a & 0x20)
                self._mark(0xD63D)
                if r.p&Z:
                    pass
                else:
                    self._a(m[0x0508])
                    self._a(r.a | 0x10)
                    m[0x0508]=r.a
                    self._a(m[0x0090])
                    self._flag(C,False)
                    self._add(0x02)
                    self._compare(r.a,0x90)
                    self._mark(0xD64F)
                    if r.p&C:
                        self._a(m[0x0508])
                        self._a(r.a & 0xEF)
                        m[0x0508]=r.a
                        pass
                    else:
                        m[0x0090]=r.a
                        self._a(m[0x009C])
                        self._a(r.a & 0xEF)
                        self._a(r.a | 0x20)
                        m[0x009C]=r.a
                        self._a(m[0x0090])
                        self._a(r.a & 0x0E)
                        self._mark(0xD663)
                        if not r.p&Z:
                            pass
                        else:
                            self._a(m[0x0508])
                            self._a(r.a & 0xEF)
                            m[0x0508]=r.a
                            pass
                        pass
                    pass
                pass
            self._mark(0xD66D)
            self._rts();return
        else:
            self._mark(0xD582)
            self._rts();return


def strategy_profile(ruler,side_base,noncommander_count,rom):
    """Six original profiles, each with nine two-byte packed count records.

    The four counts allocate strategyIDs1..4; commander uses0. A count of0
    skips the original profile read and leaves its old parameter cache intact.
    """
    if not 0<=ruler<7 or side_base not in(0,10)or not 0<=noncommander_count<=9:
        raise ValueError('Setup domain ruler0..6,side0/10,count0..9')
    if noncommander_count==0:return None
    family=1 if ruler in(1,5)else 2 if ruler in(2,4)else 0
    profile=family+(3 if side_base==10 else 0)
    offset=16+8*8192+(0xB3FD&8191)+18*profile+2*(noncommander_count-1)
    a,b=rom[offset:offset+2];counts=(a>>4,a&15,b>>4,b&15)
    return dict(profile=profile,counts=counts,strategies=tuple(s for s,n in enumerate(counts,1)for _ in range(n)),
                file_offset=offset,raw_bytes=(a,b))

def ordered_noncommander_triplets(triplets,rom_or_records):
    """Exact adjacent swaps, including the original >= equality/tie behavior.

    Each tuple is(officerID,side/affinity,hundredTroops). Other battlefield
    arrays are deliberately not moved. The input is the contiguous nonleader
    prefix after the commander, not arbitrary sparse empty slots.
    """
    items=list(triplets)
    if len(items)>9 or any(not 0<=v[0]<237 for v in items):raise ValueError('At most9 valid officers')
    def martial(ident):
        if isinstance(rom_or_records,(bytes,bytearray))and len(rom_or_records)==524304:
            return rom_or_records[16+17*8192+12*ident+1]
        return rom_or_records[0x63C0+12*ident+1]
    for _ in range(max(0,len(items)-1)):
        for j in range(len(items)-1):
            if martial(items[j+1][0])>=martial(items[j][0]):items[j],items[j+1]=items[j+1],items[j]
    return tuple(items)
