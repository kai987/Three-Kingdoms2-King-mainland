"""Executable reconstruction of the complete bounded duel control handlers.

The 22 main states and every valid nested table are in state_machine.json.
program.json is a lifted instruction IR, not a list of opaque ROM calls. This
executor implements its control/ALU/memory effects without fetching ROM code.
Rendering and helper semantics outside this recovered region are explicit hooks.
Missing hooks raise an explicit dependency exception rather than finishing.
"""
from dataclasses import dataclass
import json
from pathlib import Path

ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
STATE=0x04A8
SUBSTATE=0x04A9
ACTOR=0x04AA
ROOT=Path(__file__).resolve().parents[2]
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128


class UnresolvedDependency(RuntimeError):
    def __init__(self, target, call_pc, kind):
        self.target,self.call_pc,self.kind=target,call_pc,kind
        super().__init__(f"Unresolved {kind} helper ${target:04X} at ${call_pc:04X}")


class InvalidState(RuntimeError): pass


@dataclass
class Registers:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xB100


def commit_duel_hp(memory):
    """Bank24 $D060..$D073: write both temporary HP bytes to real records.

    Writes slot0 then slot1. If IDs alias, slot1 overwrites slot0. Upper fields
    are untouched. This operation happens after attacks as well as setup.
    """
    writes=[]
    for side in (0,1):
        officer_id=memory[0x04AD+side]
        address=0x63C0+12*officer_id
        value=memory[0x04B1+side]
        memory[address]=value
        writes.append({"side":side,"officer_id":officer_id,"address":address,"value":value})
    return writes


def _duel_side(memory):
    side=memory[ACTOR]
    if side not in (0,1):
        raise InvalidState('These semantic functions require duel actor 0 or 1')
    return side


def prepare_duel_handoff_header(memory):
    """Bank15 $CD61..$CDCE, after $CD59 fade wait and $E768 cleanup.

    The ordinary attack scene's state5 enters this routine. Control code3 is
    converted to80 for the duel's computer-control bit. The code can swap the
    two sides before setting duel IDs. This is the header's complete game write
    effect, not an implementation of the preceding rendering cleanup.
    """
    memory[0x0541]=(memory[0x0541]+1)&255
    memory[0x7A]=7;memory[STATE]=0;memory[SUBSTATE]=0;memory[ACTOR]=0
    controls=[memory[0x0562],memory[0x0563]]
    swap=controls[0]!=0 and controls[1] in (0,1)
    for side in (0,1):
        destination=side^int(swap)
        memory[0x04AD+destination]=memory[0x0560+side]
        memory[0x04AB+destination]=0x80 if controls[side]==3 else controls[side]
    return {'swapped_sides':swap,'global_state':7,'next_setup_entry':0xE2E8,
            'prerequisites':['0087 bit7 set','E768 cleanup actually completed']}


def initialize_duel_records(memory):
    """Readable game effects of $B15A..$B183, before the sprite tail call.

    Wait for $0087 bit7, copy both permanent body bytes into temporary HP,
    and classify the equipped weapon for animation: IDs <8 ->2, 8..15 ->0,
    >=16 ->1. Those numbers are sprite categories, not invented item names.
    Does not reproduce CPU flags or pointer scratch; use DuelMachine for those.
    The returned dependency must actually run before a complete display tick.
    """
    if not memory[0x87]&0x80:return {'waiting':'palette_transition'}
    memory[SUBSTATE]=(memory[SUBSTATE]+1)&255
    for side in (0,1):
        address=0x63C0+12*memory[0x04AD+side]
        memory[0x04B1+side]=memory[address]
        weapon=memory[address+10]&31
        memory[0x04AF+side]=2 if weapon<8 else 0 if weapon<16 else 1
    memory[0]=0x43
    return {'dependency':0xCDFD,'kind':'tail','a':(memory[0x04AF]+1)&255,
            'sprite_destination':0x43}


def route_duel_action(memory,*,is_ruler=None):
    """Game effects of $B47E..$B551, preserving numeric action categories.

    Category3 needs the actual $D262 predicate, supplied as is_ruler. Returned
    dialogue requests are explicit work for the host, not completed messages.
    Category4 is intercepted by $B447 in normal menu flow; entering this exact
    router with 4 follows its real default branch to state8.
    """
    side=_duel_side(memory);category=memory[0x04BF]
    if category in (0,2,6):
        memory[0x04BD]=3;memory[0x04BE]=0
        memory[STATE]={0:16,2:17,6:18}[category];memory[SUBSTATE]=0
        memory[0x042C]=memory[0x04AD+side]
        return {'dependency':0xF28B,'kind':'tail','dialogue_id':{0:0x23,2:0x21,6:0x24}[category]}
    if category==1:
        memory[STATE]=4;memory[SUBSTATE]=0
        return {'dependency':0xF28B,'kind':'tail','dialogue_id':0}
    if category==3:
        if is_ruler is None:raise UnresolvedDependency(0xD262,0xB4E2,'ruler predicate')
        if is_ruler:
            memory[SUBSTATE]=(memory[SUBSTATE]-1)&255
            return {'rejected':'ruler_cannot_take_this_branch'}
        memory[STATE]=6;memory[SUBSTATE]=0
        return {'dependency':0xF28B,'kind':'tail','dialogue_id':0}
    if category==5:
        memory[STATE]=5;memory[SUBSTATE]=0
        memory[0x04BE]=side;memory[0x04BF]=side
        return {'dependency':None}
    memory[STATE]=7 if category==7 else 8;memory[SUBSTATE]=0
    return {'dependency':None}


def check_duel_strike_end(memory):
    """Complete game effects of $B9C8..$BA14, after display work completes.

    Current actor is checked first; if both HP bytes are zero, that actor is
    selected first for the defeat path. Battle result bytes are separate
    from the officer record's status bits. This function never deletes records.
    """
    if memory[0x7E]&4:return {'waiting':'display_update'}
    side=_duel_side(memory)
    defeated=side if memory[0x04B1+side]==0 else side^1 if memory[0x04B1+(side^1)]==0 else None
    if defeated is None:
        memory[STATE]=1;memory[SUBSTATE]=0
        return {'next':'next_action'}
    memory[ACTOR]=defeated;memory[0x042C]=memory[0x04AD+defeated]
    memory[0x0515+2*defeated]=2;memory[0x0515+2*(defeated^1)]=0
    memory[STATE]=13;memory[SUBSTATE]=0
    return {'next':'zero_hp_animation','defeated_side':defeated}


def prepare_duel_return(memory):
    """$C30E..$C33A: copy result IDs, select the reward path or begin fade."""
    memory[0x0514]=memory[0x04AD];memory[0x0516]=memory[0x04AE]
    defeated=0 if memory[0x0515]==2 else 1 if memory[0x0517]==2 else None
    if defeated is not None:
        memory[0x04BD]=2*defeated;memory[SUBSTATE]=2
        return {'next':'equipment_reward_check','defeated_side':defeated}
    memory[SUBSTATE]=(memory[SUBSTATE]+1)&255
    return {'dependency':0xECEE,'kind':'tail','next':'palette_fade'}


def finish_duel_return(memory,*,restart_attack=False):
    """$C33B/$C480: finish fade and return to battle or the attack display.

    restart_attack=False reproduces $C33B writes: battle state11/sub0 and
    global state3. True reproduces $C480: global state5, without those battle
    state writes. Owner code3 leaves $6F44 as it was in both real paths.
    $ECBF is still a required scene-transition helper.
    """
    if not memory[0x87]&0x80:return {'waiting':'palette_transition'}
    if not restart_attack:memory[0x0500]=11;memory[0x0501]=0
    if memory[0x050F]!=3:memory[0x6F44]=memory[0x050F]
    memory[0x7A]=5 if restart_attack else 3
    return {'dependency':0xECBF,'kind':'tail','global_state':memory[0x7A]}


class DuelMachine:
    """Tick the actual recovered state handlers against a CPU address-space bus.

    memory supports memory[address] and assignment (a flat 64-KiB list or the
    existing mapper19 Bus). hooks(context, target, return_pc, kind) must execute
    the external helper and update context.registers, including pc/flags.
    A caller may supply recovered shared functions or a real-ROM oracle hook;
    the latter is useful for verification but is not independent source recovery
    of that external helper. Program/data hashes are pinned to this ROM.
    """
    def __init__(self,memory,hooks=None,program=None):
        if program is None:
            program=json.loads((ROOT/'analysis/duel_fsm/program.json').read_text())
        if program['rom_sha256']!=ROM_SHA256:raise ValueError('Wrong IR ROM identity')
        self.instructions={v['pc']:v for v in program['instructions']}
        from .controller_helpers import ControlHelpers
        self.memory,self.hooks=memory,ControlHelpers(hooks)
        self.registers=Registers()
        self.events=[]
        self.executed=[]

    def nz(self,value):
        value &=255
        self.registers.p=(self.registers.p&~(N|Z)) | (N if value&128 else 0) | (Z if value==0 else 0)
        return value

    def flag(self,bit,value):
        self.registers.p=(self.registers.p|bit) if value else (self.registers.p&~bit)

    def push(self,value):
        r=self.registers;self.memory[0x100+r.sp]=value&255;r.sp=(r.sp-1)&255

    def pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]

    def address(self,item):
        r=self.registers;mode=item['mode'];value=item['operand']
        if mode in ('zpg','zpx','zpy'):
            return (value+(r.x if mode=='zpx' else r.y if mode=='zpy' else 0))&255
        if mode in ('abs','abx','aby'):
            return (value+(r.x if mode=='abx' else r.y if mode=='aby' else 0))&65535
        if mode=='inx':
            value=(value+r.x)&255;return self.memory[value]|self.memory[(value+1)&255]<<8
        if mode=='iny':return ((self.memory[value]|self.memory[(value+1)&255]<<8)+r.y)&65535
        raise NotImplementedError(mode)

    def operand(self,item):
        return item['operand'] if item['mode']=='imm' else self.memory[self.address(item)]

    def external(self,item,target,return_pc,kind):
        self.events.append({'call_pc':item['pc'],'target':target,'kind':kind,'state':self.memory[STATE],'substate':self.memory[SUBSTATE],
            'registers':vars(self.registers).copy()})
        if self.hooks is None:raise UnresolvedDependency(target,item['pc'],kind)
        self.hooks(self,target,return_pc,kind)

    def run_entry(self,entry=0xB100,*,max_instructions=20000,registers=None):
        """One cooperative update; does not invent a completed animation frame."""
        before=(self.memory[STATE],self.memory[SUBSTATE],self.memory[ACTOR])
        self.registers=registers or Registers(pc=entry)
        r=self.registers;r.pc=entry
        self.memory[0x1FE]=0xFF;self.memory[0x1FF]=0x01
        self.events=[];self.executed=[]
        for count in range(max_instructions):
            if r.pc==0x0200:
                return {'before':before,'after':(self.memory[STATE],self.memory[SUBSTATE],self.memory[ACTOR]),'instructions':count,'hooks':list(self.events)}
            if r.pc not in self.instructions:raise UnresolvedDependency(r.pc,r.pc,'unlifted control destination')
            item=self.instructions[r.pc];self.executed.append(r.pc)
            op=item['op'];pc=item['pc'];next_pc=item['next_pc']
            if op=='DISPATCH':
                targets=item['targets']
                if r.a>=len(targets):raise InvalidState(f'Index {r.a} exceeds {len(targets)} proven entries at ${pc:04X}')
                # EADE clobbers Y/A/pointer registers; preserve actual convention
                # via a helper hook rather than falsely assuming it preserves CPU.
                self.push((pc+2)>>8);self.push(pc+2)
                self.external(item,0xEADE,targets[r.a],'dispatch')
                continue
            if op in ('JSR','FARCALL'):
                self.push((pc+2)>>8);self.push(pc+2)
                target=item['operand'];r.pc=target
                if op=='FARCALL' or 'hook' in item:self.external(item,target,next_pc,'far_call' if op=='FARCALL' else 'call')
                continue
            if op=='JMP':
                target=item['operand'];r.pc=target
                if 'hook' in item:self.external(item,target,None,'tail')
                continue
            if op=='RTS':r.pc=((self.pop() | self.pop()<<8)+1)&65535;continue
            if op in ('BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'):
                bit={'BCC':C,'BCS':C,'BEQ':Z,'BNE':Z,'BMI':N,'BPL':N,'BVC':V,'BVS':V}[op]
                set_branch=op in ('BCS','BEQ','BMI','BVS')
                r.pc=item['operand'] if bool(r.p&bit)==set_branch else next_pc
                continue
            if op in ('LDA','LDX','LDY'):
                setattr(r,op[-1].lower(),self.nz(self.operand(item)))
            elif op in ('STA','STX','STY'):self.memory[self.address(item)]=getattr(r,op[-1].lower())
            elif op in ('AND','ORA','EOR'):
                value=self.operand(item)
                r.a=self.nz(r.a&value if op=='AND' else r.a|value if op=='ORA' else r.a^value)
            elif op in ('CMP','CPX','CPY'):
                value=self.operand(item);left=r.a if op=='CMP' else r.x if op=='CPX' else r.y
                self.flag(C,left>=value);self.nz((left-value)&255)
            elif op in ('ADC','SBC'):
                value=self.operand(item);old=r.a;carry=int(bool(r.p&C))
                total=old+value+carry if op=='ADC' else old-value-(1-carry)
                self.flag(C,total>255 if op=='ADC' else total>=0)
                self.flag(V,bool((~(old^value)&(old^total)&128) if op=='ADC' else ((old^value)&(old^total)&128)))
                r.a=self.nz(total&255)
            elif op in ('CLC','SEC'):self.flag(C,op=='SEC')
            elif op in ('INC','DEC'):
                address=self.address(item);self.memory[address]=self.nz((self.memory[address]+(1 if op=='INC' else -1))&255)
            elif op in ('INX','INY','DEX','DEY'):
                register=op[-1].lower();setattr(r,register,self.nz((getattr(r,register)+(1 if op.startswith('IN') else -1))&255))
            elif op in ('TAX','TAY','TXA','TYA'):
                source,destination=op[1].lower(),op[2].lower();setattr(r,destination,self.nz(getattr(r,source)))
            elif op in ('LSR','ASL','ROL'):
                address=None if item['mode']=='acc' else self.address(item)
                value=r.a if address is None else self.memory[address]
                old_c=int(bool(r.p&C));self.flag(C,bool(value&1) if op=='LSR' else bool(value&128))
                value=self.nz(value>>1 if op=='LSR' else ((value<<1)|(old_c if op=='ROL' else 0))&255)
                if address is None:r.a=value
                else:self.memory[address]=value
            else:raise NotImplementedError(f'{op} at ${pc:04X}')
            r.pc=next_pc
        raise RuntimeError(f'Duel handler instruction budget exhausted at ${r.pc:04X}')

    def tick(self,**kwargs):
        return self.run_entry(0xB100,**kwargs)

    def phase(self,state,substate,**kwargs):
        """Explicit state handler entry, useful for fixtures and engine adapters.

        This executes the recovered body's IR, including every branch/write;
        it is not a hook that blindly calls its original ROM entry.
        """
        self.memory[STATE]=state&255;self.memory[SUBSTATE]=substate&255
        return self.tick(**kwargs)
