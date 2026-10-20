"""Executable reconstruction of the bounded battle control handlers.

The 16 main states and 101 legal main/sub combinations are in state-catalog.json.
98 expand local pair12/13 dispatches; state15 adds three bank8 aliases.
Eight bounded fixed-bank math, pointer and RNG-wrapper helpers are also lifted.
program.json is a lifted instruction IR, not a list of opaque ROM calls. This
executor implements its control/ALU/memory effects without fetching ROM code.
Rendering and helper semantics outside this recovered region are explicit hooks.
Missing hooks raise UnresolvedDependency rather than pretending to finish.
"""
from dataclasses import dataclass
import json
from pathlib import Path

ROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
STATE=0x0500
SUBSTATE=0x0501
ACTOR=0x050A
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
    pc:int=0xA028




class BattleStateMachine:
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
            program=json.loads((ROOT/'analysis/battle_fsm/program.json').read_text())
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

    def run_entry(self,entry=0xA028,*,max_instructions=20000,registers=None,
                  seed_return=True,return_pc=0x0200):
        """One cooperative update; does not invent a completed animation frame.

        Default direct-entry fixtures seed the historical0200 sentinel. A real
        nested source call must pass the caller's register object, disable
        seeding, and supply its actual return PC, preserving the caller's stack.
        """
        if not isinstance(return_pc,int) or not 0<=return_pc<=65535:
            raise ValueError('An explicit CPU return address is required')
        if seed_return and return_pc!=0x0200:
            raise ValueError('Disable synthetic return seeding for a caller-owned return address')
        before=(self.memory[STATE],self.memory[SUBSTATE],self.memory[ACTOR])
        self.registers=registers or Registers(pc=entry)
        r=self.registers;r.pc=entry
        if seed_return:
            self.memory[0x1FE]=0xFF;self.memory[0x1FF]=0x01
        self.events=[];self.executed=[]
        for count in range(max_instructions):
            if r.pc==return_pc:
                return {'before':before,'after':(self.memory[STATE],self.memory[SUBSTATE],self.memory[ACTOR]),'instructions':count,'hooks':list(self.events),'events':list(self.events)}
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
        raise RuntimeError(f'Battle handler instruction budget exhausted at ${r.pc:04X}')

    def step(self,**kwargs):
        return self.run_entry(0xA028,**kwargs)

    def phase(self,state,substate,**kwargs):
        """Explicit state handler entry, useful for fixtures and engine adapters.

        This executes the recovered body's IR, including every branch/write;
        it is not a hook that blindly calls its original ROM entry.
        """
        self.memory[STATE]=state&255;self.memory[SUBSTATE]=substate&255
        return self.step(**kwargs)


# Public enum/catalog front door for source integration and visual state browsers.
CATALOG=json.loads((ROOT/'analysis/battle_fsm/state-catalog.json').read_text())
MAIN_STATES={state['state']:state for state in CATALOG['states']}
SUB_STATES={(state['state'],sub['substate']):sub for state in CATALOG['states'] for sub in state['substates']}
UnresolvedBattleHook=UnresolvedDependency


def _word(memory,address):
    return memory[address] | (memory[address+1]<<8)


def _store_word(memory,address,value):
    value &= 0xFFFF
    memory[address],memory[address+1]=value&255,value>>8


def _ruler_address(ruler):
    if not 0 <= ruler < 7:
        raise ValueError('Only ruler indices 0..6 have proven F379 pointers')
    return 0x6F07+8*ruler


def commander_outcome(memory):
    """Readable bank13 DD72..DE9D (file $1BD82) victory-routing logic.

    This API recovers gameplay writes, not CPU flags/stack or the message queue.
    `abort_frame` represents the two PLA instructions that discard a caller's
    return address. A message event must be serviced by the engine's text hook.
    Slot signs are the actual $0628 array convention; no status-name inference.
    """
    if memory[0x0664]==255 or memory[0x0628]&128:
        outcome=0
    elif memory[0x066E]==255 or not memory[0x0632]&128:
        outcome=1
    else:
        return {'outcome':None,'abort_frame':False,'events':[]}
    memory[0x0514]=outcome
    if memory[0x052B]!=255:
        memory[STATE],memory[SUBSTATE]=12,0
        return {'outcome':outcome,'abort_frame':True,'events':[]}
    memory[STATE],memory[SUBSTATE]=7,2
    low=memory[0x0507]&15;high=memory[0x0507]>>4
    losing_ruler=low if outcome==0 else high
    winning_ruler=high if outcome==0 else low
    memory[0x042C]=losing_ruler
    side=128 if outcome else 0
    remaining=next((slot for slot in range(20)
                    if memory[0x0628+slot]!=255 and memory[0x0628+slot]&128==side),None)
    if remaining is None:
        memory[0x042C]=memory[_ruler_address(losing_ruler)]
        memory[SUBSTATE]=3
        return {'outcome':outcome,'abort_frame':True,'events':[{'kind':'message','id':0x55}]}
    memory[0x0509]=remaining
    controller=memory[_ruler_address(winning_ruler)+3]
    if controller==3:
        memory[0x00A4],memory[ACTOR]=4,0x54
    else:
        memory[0x6F44]=controller;memory[0x042C]=winning_ruler
        memory[0x0509]=0 if outcome else 10
        memory[0x00A4],memory[ACTOR]=3,0x53
    return {'outcome':outcome,'abort_frame':True,'events':[]}


def promote_city_leader(memory,city_id):
    """Bank8 BC00..BC45: move a city's ruler to roster position 0 if present."""
    address=0x6000+32*city_id;owner=memory[address]&15
    if owner==7:return None
    leader=memory[_ruler_address(owner)]
    found=next((address+offset for offset in range(17,27)
                if memory[address+offset]==leader),None)
    if found is None:return None
    first=address+17;memory[first],memory[found]=memory[found],memory[first]
    return (city_id,found-address-17)


def finalize_city_ownership(memory,adjacency):
    """Bank8 BBB8..BC45 (file $11BC8): ownership and neighboring roster repair.

    adjacency is the original bank16 $9D72 byte table, 8 bytes per city, including
    the $FF terminators. It is ROM data supplied explicitly, not fetched code.
    Only outcome $0514==0 transfers the city to high-nibble ruler $0507.
    """
    city=memory[0x050E];address=0x6000+32*city
    if memory[0x0514]==0:
        memory[address]=(memory[address]&240)|(memory[0x0507]>>4)
    swaps=[]
    swap=promote_city_leader(memory,city)
    if swap is not None:swaps.append(swap)
    # The original shifts city index three times in an 8-bit accumulator.
    index=(city*8)&255
    while index<len(adjacency) and adjacency[index]!=255:
        swap=promote_city_leader(memory,adjacency[index])
        if swap is not None:swaps.append(swap)
        index=(index+1)&255
        if index==((city*8)&255):raise ValueError('Unterminated adjacency row')
    return {'city_id':city,'owner':memory[address]&15,'leader_swaps':swaps}


def postbattle_city_losses(memory,random_byte):
    """Bank8/9 BF0A..C026 (file $11F1A), exact town-resource reduction.

    Parameter random_byte is the next E87A draw, consumed only for outcome 0.
    Public city field names remain numeric until their UI mapping is confirmed.
    The original discards product bits above 16 before dividing by ten. Its
    ascending threshold table actually yields rate 9 for values <=501, rate 5
    for values >501; this unusual comparison direction is retained.
    """
    if memory[0x0514]!=0:return {'draw_consumed':False,'changes':[]}
    address=0x6000+32*memory[0x050E];changes=[]
    def reduce(offset,rate,byte=False):
        old=memory[address+offset] if byte else _word(memory,address+offset)
        value=((old*(10-rate))&65535)//10
        if byte:memory[address+offset]=value&255
        else:_store_word(memory,address+offset,value)
        changes.append({'offset':offset,'before':old,'after':value&255 if byte else value,'rate':rate})
    reduce(6,(random_byte&1)+1)
    turn=memory[0x0506]
    rate=1 if turn<6 else 2 if turn<11 else 3 if turn<16 else 4 if turn<21 else 6
    reduce(8,rate);reduce(14,rate);reduce(11,rate,True)
    for offset in (2,4):
        value=_word(memory,address+offset)
        reduce(offset,5 if value>501 else 9)
    return {'draw_consumed':True,'changes':changes}


def return_campaign_supplies(memory):
    """Bank9 C027..C0BA (file $12037): two-sided supply return and cap9999.

    The low-level addition wraps at 65536 before checking the 10000 cap. The
    second return goes to escape city $052C only for a non-FF escape officer
    whose packed status ($0B &3) is 1 or2; otherwise it goes to current city.
    """
    outcome=memory[0x0514]
    if outcome not in (0,1):raise ValueError('Only outcome 0/1 is a proven domain')
    current=memory[0x050E];events=[]
    def add(city,index):
        address=0x6000+32*city
        for offset,source in ((2,0x0526),(4,0x0522)):
            before=_word(memory,address+offset)
            added=_word(memory,source+index)
            after=min((before+added)&65535,9999)
            _store_word(memory,address+offset,after)
            events.append({'city_id':city,'offset':offset,'before':before,'added':added,'after':after})
    add(current,(outcome<<1)^2)
    escaped=memory[0x052B]
    status=memory[0x63C0+12*escaped+11]&3 if escaped!=255 else 0
    destination=memory[0x052C] if status in (1,2) else current
    add(destination,outcome<<1)
    return events


def finalization_phase(memory,adjacency,*,rng_draw=None,ai_officer_processing=None,render_barrier=None):
    """Bank8 BAB3..BBB7 four-stage end-of-battle controller.

    Human/AI routing, settlement arithmetic and the real return to city control
    are recovered source. BC46 allocation is supplied by the independently
    recovered postbattle.process_ai_officers API in GameEngine; callers may
    also provide a different explicitly verified adapter. The display barrier
    remains a dependency. Callbacks receive memory (and AI selection mode).
    This can be used as a far bank8 A006 hook adapter; the lifted caller still
    handles its CPU calling convention separately.
    """
    stage=memory[SUBSTATE];events=[]
    if stage in (0,1):
        if stage==0:
            for address in (0xB2,0xC2,0xCA,0xD2,0xDA):memory[address]=8
            for address in (0xB3,0xC3,0xCB,0xD3,0xDB):memory[address]=9
        ruler=memory[0x0507]>>4 if stage==0 else memory[0x0507]&15
        controller=memory[_ruler_address(ruler)+3]
        outcome=memory[0x0514]
        if controller!=3:
            memory[0x6F44]=controller
            memory[STATE]=13 if ((outcome!=0) if stage==0 else (outcome==0)) else 14
            memory[SUBSTATE]=0;memory[0x050B]=0x11 if stage==0 else 2
        else:
            memory[0x0504]=128 if stage==0 else 0
            mode=(2 if outcome!=0 else 0) if stage==0 else (1 if outcome==0 else 0)
            memory[0x6F91]=mode
            if ai_officer_processing is None:raise UnresolvedDependency(0xBC46,0xBB37 if stage==0 else 0xBB8D,'AI postbattle officer processing')
            ai_officer_processing(memory,mode);memory[SUBSTATE]=(memory[SUBSTATE]+1)&255
    elif stage==2:
        if render_barrier is None:raise UnresolvedDependency(0xECEE,0xBB93,'NMI render barrier')
        render_barrier(memory)
        if memory[0x0514]==0 and rng_draw is None:raise UnresolvedDependency(0xE87A,0xBF27,'settlement RNG provider')
        events.append(postbattle_city_losses(memory,rng_draw() if memory[0x0514]==0 else 0))
        events.extend(return_campaign_supplies(memory));memory[SUBSTATE]=(memory[SUBSTATE]+1)&255
    elif stage==3:
        if memory[0x87]&128:
            events.append(finalize_city_ownership(memory,adjacency))
            memory[0x7A]=1;memory[0x0400]=13;memory[0x0401]=0
    else:raise InvalidState(f'Finalization substate {stage} is outside 0..3')
    return {'before':stage,'after':memory[SUBSTATE],'events':events}


def refresh_movement_selectors(memory):
    """Bank13 DB03..DB45: $063C[slot] = masked10bit troops //100.

    Empty $0664 slots write $FF (DB0F branches directly to DB3F STA). This establishes the
    selector's exact scaling without assigning a speculative weapon/troop type.
    """
    changed=[]
    for slot in range(19,-1,-1):
        officer=memory[0x0664+slot]
        if officer==255:
            memory[0x063C+slot]=255;continue
        address=0x63C0+12*officer
        troops=memory[address+8]|((memory[address+9]&3)<<8)
        memory[0x063C+slot]=troops//100;changed.append(slot)
    return changed


ACTION_POINT_REFILL=(10,16,20,24,28,32,35,37,40,42,42,42,42)
ACTION_POINT_CAP=(20,26,32,36,42,46,51,53,58,60,60,60,60)


def restore_side_action_budgets(memory):
    """Bank13 C5A0..C605 (file $1A5B0), per-round action-point refill.

    Sum masked10bit troops by sign of $0628, including only non-FF officer IDs.
    Index = floor(sum/1000), not officer count. Addition wraps at 8bits BEFORE
    capping at the corresponding C613 table. Normal gameplay has index <=12;
    anomalous larger armies read subsequent ROM data just as the original does.
    """
    refresh_movement_selectors(memory);events=[]
    for sign,resource in ((0,0x050C),(128,0x050D)):
        total=0
        for slot in range(20):
            officer=memory[0x0664+slot]
            if officer==255 or memory[0x0628+slot]&128!=sign:continue
            address=0x63C0+12*officer
            total=(total+memory[address+8]+((memory[address+9]&3)<<8))&65535
        index=total//1000
        increment=ACTION_POINT_REFILL[index] if index<13 else memory[0xC606+index]
        cap=ACTION_POINT_CAP[index] if index<13 else memory[0xC613+index]
        before=memory[resource];after=min((before+increment)&255,cap)
        memory[resource]=after
        events.append({'side_sign':sign,'troop_sum':total,'index':index,
            'before':before,'increment':increment,'cap':cap,'after':after})
    return events


def finish_side_turn(memory,*,ai_turn_reset=None,ai_side_initialize=None):
    """Bank12 BDC0..BE7D (file $19DD0), change side and advance full rounds.

    Side0->128 advances $0506 and refills BOTH reserves; side128->0 only swaps
    the active reserve. The two bank8 calls are named explicit dependencies.
    No rendering or controller poll is synthesized by this gameplay-level API.
    """
    if memory[0x0505]&128:memory[0x0505]=0
    for address in (0x6F94,0x6F95,0x6F96,0x052C,0x052E):memory[address]=0
    memory[0x0504]^=128;high_side=bool(memory[0x0504]&128)
    ruler=memory[0x0507]>>4 if high_side else memory[0x0507]&15
    memory[0x050F]=memory[_ruler_address(ruler)+3]
    events=[]
    if high_side:
        memory[0x050C]=memory[0x0505]
        events.extend(restore_side_action_budgets(memory))
        memory[0x0506]=(memory[0x0506]+1)&255;memory[0x0505]=memory[0x050D]
        if ai_turn_reset is None:raise UnresolvedDependency(0xA00F,0xBE0C,'bank8 turn reset')
        ai_turn_reset(memory)
        if memory[ACTOR]!=0:
            memory[STATE],memory[SUBSTATE]=7,2
            return {'events':events,'branch':'turn-reset-special-result'}
        refresh_movement_selectors(memory)
        memory[0x0470],memory[0x0471]=memory[0x060A],memory[0x061E]
    else:
        memory[0x050D]=memory[0x0505];memory[0x0505]=memory[0x050C]
        memory[0x0470],memory[0x0471]=memory[0x0600],memory[0x0614]
    if memory[0x050F]==3:
        if ai_side_initialize is None:raise UnresolvedDependency(0xA00C,0xBE69,'bank8 side initialize')
        ai_side_initialize(memory)
    else:memory[0x6F44]=memory[0x050F]
    memory[STATE],memory[SUBSTATE],memory[0x0509]=7,4,0
    return {'events':events,'branch':'refresh-twenty-unit-graphics'}
