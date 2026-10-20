"""Independent fixed-bank global control, with explicit missing dependencies.

One main update goes E066 -> selected007A handler -> next E066. An NMI
cooperation window goes F862 -> selected0078 callback -> F88D, before IRQ
bookkeeping/RTI. Neither contract advances a complete NES frame. Original
instructions are lifted into separate IR; ROM is read only as table data.
Missing PPU/audio/banked helpers retain their partial effects and remain
dependencies. Nothing seeds a fake return address or marks rendering complete.
"""
from pathlib import Path
import json,re
from .battle_state_machine import BattleStateMachine,Registers,UnresolvedDependency,C,Z,I,D,B,U,V,N
from .controller_helpers import MissingSharedHelper
from .runtime_services import RuntimeServices
from .mapped_memory import UnsupportedHardware

ROOT=Path(__file__).resolve().parents[2]
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MAIN=0x7a;SCENE=0x78
MAIN_TARGETS=(0xe09a,0xe0da,0xe17d,0xe18b,0xe221,0xe22f,0xe2e2,0xe2e8,
              0xe36a,0xe37c,0xe3eb,0xe3ee,0xe3eb,0xe46a,0xe3eb)
NMI_TARGETS=(0xfa97,0xfa97,0xf8b5,0xf8fe,0xf96a,0xf9a0,0xf9e4,0xfa13,0xfa53)

class InvalidGlobalIndex(ValueError):pass
class GlobalDependency(RuntimeError):
    """An explicit host/lower-layer boundary; all partial effects are retained."""
    def __init__(self,details):self.details=details;super().__init__(str(details))

def main_target(memory):
    index=memory[MAIN]&31
    if index>=len(MAIN_TARGETS):raise InvalidGlobalIndex(f'Unproven main index{index}; legal0..14')
    return MAIN_TARGETS[index]

def nmi_target(memory):
    index=memory[SCENE]&15
    if index>=len(NMI_TARGETS):raise InvalidGlobalIndex(f'Unproven NMI index{index}; legal0..8')
    return NMI_TARGETS[index]

def reset_scene_working_state(memory):
    """Exact RAM/OAM effects of E4E9..E51C -> E823..E82F.

    This cancels the old scene's queued work (0300/0304=FF) and hides OAM;
    it does not service a queued message or synthesize graphics. The earlier
    E4DA hardware-disable/audio-reset/nametable-fill prerequisites are separate.
    CPU flags/stack are intentionally outside this high-level RAM contract.
    """
    for address in (0x90,0x91,0x8e,0x8f,0x98,0x99,0x96,0x97,
                    0x7e,0x5e,0x5f,0x8d,0xa4):memory[address]=0
    memory[0x300]=memory[0x304]=255
    for address in range(0x200,0x300):memory[address]=0xf0
    return {'working_state_cleared':True,'old_jobs_cancelled':True,
            'graphics_completed':False,'hardware_prerequisites_executed':False}

def finish_nmi_bookkeeping(memory):
    """Exact memory/mapper effects F88D..F8AF, before saved-register pops.

    Restore DE/DF/E0 main-thread windows, advance four RNG cursors and the
    16-bit frame counter. This API does not execute RTI or advance real time.
    """
    memory[0x7b]=(memory[0x7b]-1)&255
    memory[0xe000]=memory[0xde]
    memory[0xe800]=memory[0xdf]|0xc0
    memory[0xf000]=memory[0xe0]
    for address in (0x50,0x52,0x54,0x55):memory[address]=(memory[address]+1)&255
    memory[0x5e]=(memory[0x5e]+1)&255
    if memory[0x5e]==0:memory[0x5f]=(memory[0x5f]+1)&255
    return {'restored_main_selectors':[memory[0xde],memory[0xdf],memory[0xe0]],
            'frame_counter':memory[0x5e]|memory[0x5f]<<8,'interrupt_return_executed':False}

class GlobalMainLoop(BattleStateMachine):
    """Bounded control executor sharing the existing register/CPU-bus protocol.

    hooks(context,target,return_pc,kind) must implement its real CPU protocol.
    JSR has already pushed call_pc+2. A banked hook must inspect actual memory
    bank selectors; a common CPU address does not identify one global function.
    Existing RuntimeServices and ControlHelpers are independent source helpers.
    No original-ROM CPU executor is imported or called by this source module.
    """
    def __init__(self,memory,hooks=None,program=None):
        if program is None:program=json.loads((ROOT/'analysis/phase6/global/program.json').read_text())
        if program['rom_sha256']!=ROM_SHA256:raise ValueError('Wrong global IR identity')
        if tuple(program['main_targets'])!=MAIN_TARGETS or tuple(program['nmi_targets'])!=NMI_TARGETS:
            raise ValueError('Wrong original dispatch-table identity')
        self.services=RuntimeServices(hooks)
        super().__init__(memory,hooks=self.services,program=program)

    def mapper_context(self):
        m=self.memory
        return {'physical_banks':list(m.banks)if hasattr(m,'banks')else None,
                'main_bank_shadows':{'DE':m[0xde],'DF':m[0xdf],'E0':m[0xe0]},
                'nmi_bank_shadows':{'E1':m[0xe1],'E2':m[0xe2],'E3':m[0xe3]}}

    def run_entry(self,entry=0xe066,*,seed_return=False,return_pc=None,stop_pcs=None,**kwargs):
        """Compatibility entry with the global caller-owned stack contract.

        The BattleStateMachine superclass has a different standalone contract;
        its synthetic-return option must never leak into global/NMI execution.
        """
        if seed_return:raise ValueError('Global caller owns the real stack; seed_return is unsupported')
        if stop_pcs is None:stop_pcs=(0xe066,)if return_pc is None else()
        return self.run_window(entry,stop_pcs=stop_pcs,return_pc=return_pc,**kwargs)

    def phase(self,*args,**kwargs):
        raise TypeError('Global uses007A/0078; use step or nmi_step with caller-owned state')

    def external(self,item,target,return_pc,kind):
        mapping=self.mapper_context();banks=mapping['physical_banks']
        event={'call_pc':item['pc'],'target':target,'kind':kind,'return_pc':return_pc,
               'target_physical_bank':banks[(target-0x8000)//8192]if banks and target>=0x8000 else None,
               'mapper':mapping,'registers':vars(self.registers).copy()}
        self.events.append(event)
        try:self.hooks(self,target,return_pc,kind)
        except (MissingSharedHelper,UnresolvedDependency) as e:
            raise GlobalDependency({'category':'external_cpu_helper','target':getattr(e,'target',target),'call_pc':getattr(e,'call_pc',item['pc']),
                                    'pc':self.registers.pc,'kind':kind,'message':str(e),'mapper':self.mapper_context()})from e

    def run_window(self,entry,*,stop_pcs=(),return_pc=None,max_instructions=50000,registers=None):
        """Caller owns registers/SP and the real stack; no sentinel is written."""
        before={'main':self.memory[MAIN],'scene':self.memory[SCENE],'mapper':self.mapper_context()}
        self.registers=registers if registers is not None else Registers(pc=entry)
        self.registers.pc=entry;self.events=[];self.executed=[];r=self.registers
        def result(status,count,**extra):
            return {'status':status,'before':before,'after':{'main':self.memory[MAIN],'scene':self.memory[SCENE],'mapper':self.mapper_context()},
                    'registers':vars(r).copy(),'instructions':count,'events':list(self.events),**extra}
        for count in range(max_instructions):
            if count and r.pc in stop_pcs:return result('boundary',count,boundary_pc=r.pc)
            if return_pc is not None and r.pc==return_pc:return result('returned',count,return_pc=return_pc)
            if r.pc==0xfb28 and self.memory[0x62]!=0:
                return result('dependency',count,dependency={'category':'irq_wait','pc':r.pc,'flag_address':0x62,'flag_value':self.memory[0x62],
                    'message':'Original FB28 polls0062; this cooperative update cannot invent IRQ completion'})
            if r.pc not in self.instructions:
                return result('dependency',count,dependency={'category':'unlifted_control_destination','pc':r.pc,'mapper':self.mapper_context()})
            item=self.instructions[r.pc];self.executed.append(r.pc)
            op=item['op'];pc=item['pc'];nxt=item['next_pc']
            try:
                if op in ('GLOBAL_DISPATCH','NMI_DISPATCH'):
                    expected=main_target(self.memory)if op=='GLOBAL_DISPATCH'else nmi_target(self.memory)
                    pointer=item['operand'];target=self.memory[pointer]|self.memory[(pointer&0xff00)|((pointer+1)&255)]<<8
                    if target!=expected:raise InvalidGlobalIndex(f'Computed dispatch pointer{target:04X} differs from the proven table{expected:04X}')
                    r.pc=target;continue
                if op=='JSR':
                    self.push((pc+2)>>8);self.push(pc+2);r.pc=item['operand']
                    if 'hook'in item:self.external(item,r.pc,nxt,'call')
                    continue
                if op=='JMP':
                    r.pc=item['operand']
                    if 'hook'in item:self.external(item,r.pc,None,'tail')
                    continue
                if op=='RTS':r.pc=((self.pop()|self.pop()<<8)+1)&65535;continue
                if op=='RTI':r.p=self.pop()|B|U;r.pc=self.pop()|self.pop()<<8;continue
                if op in ('BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'):
                    bit={'BCC':C,'BCS':C,'BEQ':Z,'BNE':Z,'BMI':N,'BPL':N,'BVC':V,'BVS':V}[op]
                    r.pc=item['operand']if bool(r.p&bit)==(op in('BCS','BEQ','BMI','BVS'))else nxt;continue
                if op in ('LDA','LDX','LDY'):setattr(r,op[-1].lower(),self.nz(self.operand(item)))
                elif op in ('STA','STX','STY'):self.memory[self.address(item)]=getattr(r,op[-1].lower())
                elif op in ('AND','ORA','EOR'):
                    value=self.operand(item);r.a=self.nz(r.a&value if op=='AND'else r.a|value if op=='ORA'else r.a^value)
                elif op in ('CMP','CPX','CPY'):
                    value=self.operand(item);left=r.a if op=='CMP'else r.x if op=='CPX'else r.y;self.flag(C,left>=value);self.nz((left-value)&255)
                elif op in ('ADC','SBC'):
                    value=self.operand(item);old=r.a;carry=int(bool(r.p&C));total=old+value+carry if op=='ADC'else old-value-(1-carry)
                    self.flag(C,total>255 if op=='ADC'else total>=0);self.flag(V,bool((~(old^value)&(old^total)&128)if op=='ADC'else((old^value)&(old^total)&128)));r.a=self.nz(total&255)
                elif op in ('CLC','SEC','CLI','SEI','CLD','SED','CLV'):
                    bit=C if op in('CLC','SEC')else I if op in('CLI','SEI')else D if op in('CLD','SED')else V;self.flag(bit,op in('SEC','SEI','SED'))
                elif op in ('INC','DEC'):
                    address=self.address(item);self.memory[address]=self.nz((self.memory[address]+(1 if op=='INC'else-1))&255)
                elif op in ('INX','INY','DEX','DEY'):
                    reg=op[-1].lower();setattr(r,reg,self.nz((getattr(r,reg)+(1 if op.startswith('IN')else-1))&255))
                elif op in ('TAX','TAY','TXA','TYA'):setattr(r,op[2].lower(),self.nz(getattr(r,op[1].lower())))
                elif op=='TXS':r.sp=r.x
                elif op=='TSX':r.x=self.nz(r.sp)
                elif op in ('LSR','ASL','ROL','ROR'):
                    address=None if item['mode']=='acc'else self.address(item);value=r.a if address is None else self.memory[address];carry=int(bool(r.p&C));self.flag(C,bool(value&1)if op in('LSR','ROR')else bool(value&128))
                    value=self.nz(value>>1 if op=='LSR'else(value>>1)|(carry<<7)if op=='ROR'else((value<<1)|(carry if op=='ROL'else 0))&255)
                    if address is None:r.a=value
                    else:self.memory[address]=value
                elif op=='PHA':self.push(r.a)
                elif op=='PLA':r.a=self.nz(self.pop())
                elif op=='PHP':self.push(r.p|B|U)
                elif op=='PLP':r.p=self.pop()|B|U
                elif op=='BIT':
                    value=self.operand(item);self.flag(Z,(r.a&value)==0);self.flag(N,bool(value&128));self.flag(V,bool(value&64))
                elif op=='NOP':pass
                else:raise NotImplementedError(f'{op} in global control{pc:04X}')
                r.pc=nxt
            except GlobalDependency as e:return result('dependency',count+1,dependency=e.details)
            except UnsupportedHardware as e:
                match=re.search(r'\$([0-9a-fA-F]{4})',str(e))
                return result('dependency',count+1,dependency={'category':'hardware_access','pc':r.pc,'address':int(match.group(1),16)if match else None,'message':str(e)})
        return result('budget',max_instructions,budget_pc=r.pc)

    def step(self,*,entry=0xe066,**kwargs):
        main_target(self.memory)
        return self.run_window(entry,stop_pcs=(0xe066,),**kwargs)

    def cold_post_reset(self,**kwargs):
        """E05E begins after RAM reset. F3BD is an explicit unresolved helper."""
        return self.run_window(0xe05e,stop_pcs=(0xe066,),**kwargs)

    def nmi_step(self,**kwargs):
        """F862 callback window; caller has already performed real F800 prelude.

        Caller must provide the actual E1/E2/E3 mapping, busy flag and stack.
        This method resets7C like the original F862, dispatches, and stops at
        F88D. DMA, IRQ timing, queued graphics and banked audio remain external.
        """
        nmi_target(self.memory)
        return self.run_window(0xf862,stop_pcs=(0xf88d,),**kwargs)

    def nmi_prefix(self,**kwargs):
        """Actual F800 control until F88D/F8AF; IRQ/PPU access may block.

        This entry requires the real hardware-pushed interrupt stack supplied
        by its caller. It never constructs an interrupt stack on their behalf.
        """
        nmi_target(self.memory)
        return self.run_window(0xf800,stop_pcs=(0xf88d,0xf8af),**kwargs)
