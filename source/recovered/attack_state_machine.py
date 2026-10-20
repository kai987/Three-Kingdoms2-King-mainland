"""Executable reconstruction of the bounded normal-attack control handlers.

This is recovered source from machine bytes, not the original game source.

The 11 main states and legal expanded entries are in state-catalog.json.
program.json is a lifted instruction IR, not a list of opaque ROM calls. This
executor implements its control/ALU/memory effects without fetching ROM code.
Rendering and helper semantics outside this recovered region are explicit hooks.
Missing hooks raise an explicit dependency error rather than finishing a frame.
"""
from dataclasses import dataclass
import json
from pathlib import Path

ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
STATE=0x0540
SUBSTATE=0x0541
CONTROL_BYTE=0x0542
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
    pc:int=0xA069




class AttackStateMachine:
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
            program=json.loads((ROOT/'analysis/attack_fsm/program.json').read_text())
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
            'registers':vars(self.registers).copy(),'inline_target':item.get('inline_target')})
        if self.hooks is None:raise UnresolvedDependency(target,item['pc'],kind)
        self.hooks(self,target,return_pc,kind)

    def run_entry(self,entry=0xA069,*,max_instructions=20000,registers=None,stop_pc=0x0200):
        """One cooperative update; does not invent a completed animation frame."""
        before=(self.memory[STATE],self.memory[SUBSTATE],self.memory[CONTROL_BYTE])
        self.registers=registers or Registers(pc=entry)
        r=self.registers;r.pc=entry
        self.memory[0x1FE]=0xFF;self.memory[0x1FF]=0x01
        self.events=[];self.executed=[]
        for count in range(max_instructions):
            if r.pc==stop_pc:
                return {'before':before,'after':(self.memory[STATE],self.memory[SUBSTATE],self.memory[CONTROL_BYTE]),'instructions':count,'hooks':list(self.events),'events':list(self.events)}
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
            elif op in ('LSR','ASL','ROL','ROR'):
                address=None if item['mode']=='acc' else self.address(item)
                value=r.a if address is None else self.memory[address]
                old_c=int(bool(r.p&C));self.flag(C,bool(value&1) if op in ('LSR','ROR') else bool(value&128))
                value=self.nz(value>>1 if op=='LSR' else ((value>>1)|(old_c<<7)) if op=='ROR' else ((value<<1)|(old_c if op=='ROL' else 0))&255)
                if address is None:r.a=value
                else:self.memory[address]=value
            elif op=='PHA':self.push(r.a)
            elif op=='PLA':r.a=self.nz(self.pop())
            elif op=='PHP':self.push(r.p|B|U)
            elif op=='PLP':r.p=(self.pop()|U)&~B
            elif op=='BIT':
                value=self.operand(item);self.flag(Z,(r.a&value)==0);self.flag(N,bool(value&128));self.flag(V,bool(value&64))
            elif op=='NOP':pass
            else:raise NotImplementedError(f'{op} at ${pc:04X}')
            r.pc=next_pc
        raise RuntimeError(f'Normal-attack handler instruction budget exhausted at ${r.pc:04X}')

    def step(self,**kwargs):
        return self.run_entry(0xA069,**kwargs)

    def phase(self,state,substate,**kwargs):
        """Explicit state handler entry, useful for fixtures and engine adapters.

        This executes the recovered body's IR, including every branch/write;
        it is not a hook that blindly calls its original ROM entry.
        """
        self.memory[STATE]=state&255;self.memory[SUBSTATE]=substate&255
        return self.step(**kwargs)


# Public catalog: names describe control structure; semantics remain evidenced separately.
CATALOG=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
STATES={entry['state']:entry for entry in CATALOG['states']}


def initialize_attack_control(memory):
    """Readable $A095-$A0CE prefix; $C926 stat preparation is a required next call.

    Returns False while the fade flag is not ready. This function only applies
    the declared control writes and does not simulate the subsequent helper.
    """
    if not memory[0x87]&0x80:return False
    memory[STATE]=6;memory[SUBSTATE]=0
    for address in [*range(0x550,0x558),*range(0x574,0x578),0x548]:memory[address]=0
    return {'next_helper':0xC926,'scope':'Control initialization prefix only'}


def handoff_to_duel(memory):
    """Readable $CD61-$CDCE writes after the fade/scene helper $E768.

    Party encoding3 becomes $80 for the duel. Depending on the two party codes,
    IDs/party codes exchange positions. No officer status or HP is written here.
    """
    memory[SUBSTATE]=(memory[SUBSTATE]+1)&255;memory[0x7a]=7
    memory[0x4a8]=memory[0x4a9]=memory[0x4aa]=0
    first_id,second_id=memory[0x560],memory[0x561]
    first_party,second_party=memory[0x562],memory[0x563]
    first_code=128 if first_party==3 else first_party
    second_code=128 if second_party==3 else second_party
    swap=first_party!=0 and second_party in(0,1)
    memory[0x4ad],memory[0x4ae]=(second_id,first_id)if swap else(first_id,second_id)
    memory[0x4ab],memory[0x4ac]=(second_code,first_code)if swap else(first_code,second_code)
    return {'global_state':7,'ids':[memory[0x4ad],memory[0x4ae]],'party_codes':[memory[0x4ab],memory[0x4ac]],'swapped':swap}


def return_to_battle(memory):
    """Exact declared effects of $A3F2-$A406; fade flag gates the handoff.

    Attack mainstate4/substate2 (also alias6) returns to battle mainstate11/sub0.
    """
    if not memory[0x87]&0x80:return False
    memory[0x500]=11;memory[0x501]=0;memory[0x7a]=3
    return {'battle_state':11,'battle_substate':0,'global_state':3}
