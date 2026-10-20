"""Independent bounded source for message, input, audio-request and mapper services.

These execute lifted source, never original ROM instructions. Message/audio
requests really modify their original queues; they do not mark work completed.
Display synthesis, PPU timing and unknown services stay explicit dependencies.
"""
import json
from pathlib import Path
from .controller_helpers import ControlHelpers,MissingSharedHelper
from .officers import ROM_SHA256

ROOT=Path(__file__).resolve().parents[2]
C,Z,V,N=1,2,64,128

class RuntimeServices:
    def __init__(self,fallback=None,program=None):
        if program is None:program=json.loads((ROOT/'analysis/phase4/services/program.json').read_text())
        if program['rom_sha256']!=ROM_SHA256:raise ValueError('Wrong fixed service IR identity')
        self.instructions={i['pc']:i for i in program['instructions']}
        self.fallback=fallback;self.calls=[]

    def __call__(self,context,target,return_pc,kind):
        if target not in self.instructions:
            if self.fallback is not None:return self.fallback(context,target,return_pc,kind)
            raise MissingSharedHelper(f'Unrecovered {kind} service ${target:04X}')
        r=context.registers;r.pc=target;executed=0
        def external(dest,ret,call_kind):
            ControlHelpers(self.fallback)(context,dest,ret,call_kind)
        for count in range(200000):
            if count and (r.pc==return_pc or (return_pc is None and (r.pc==0x200 or r.pc in context.instructions))):
                self.calls.append({'target':target,'kind':kind,'instructions':executed})
                return
            if r.pc not in self.instructions:
                raise MissingSharedHelper(f'Service destination ${r.pc:04X} is outside recovered source')
            item=self.instructions[r.pc];executed+=1
            op=item['op'];pc=item['pc'];next_pc=item['next_pc'];memory=context.memory
            if op=='JSR':
                context.push((pc+2)>>8);context.push(pc+2);r.pc=item['operand']
                if r.pc not in self.instructions:external(r.pc,next_pc,'call')
                continue
            if op=='JMP':
                r.pc=item['operand']
                if r.pc not in self.instructions:external(r.pc,None,'tail')
                continue
            if op=='RTS':r.pc=((context.pop()|context.pop()<<8)+1)&65535;continue
            if op in ('BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'):
                bit={'BCC':C,'BCS':C,'BEQ':Z,'BNE':Z,'BMI':N,'BPL':N,'BVC':V,'BVS':V}[op]
                r.pc=item['operand'] if bool(r.p&bit)==(op in ('BCS','BEQ','BMI','BVS')) else next_pc
                continue
            if op in ('LDA','LDX','LDY'):setattr(r,op[-1].lower(),context.nz(context.operand(item)))
            elif op in ('STA','STX','STY'):memory[context.address(item)]=getattr(r,op[-1].lower())
            elif op in ('AND','ORA','EOR'):
                value=context.operand(item)
                r.a=context.nz(r.a&value if op=='AND' else r.a|value if op=='ORA' else r.a^value)
            elif op in ('CMP','CPX','CPY'):
                value=context.operand(item);left=r.a if op=='CMP' else r.x if op=='CPX' else r.y
                context.flag(C,left>=value);context.nz((left-value)&255)
            elif op in ('ADC','SBC'):
                value=context.operand(item);old=r.a;carry=int(bool(r.p&C))
                total=old+value+carry if op=='ADC' else old-value-(1-carry)
                context.flag(C,total>255 if op=='ADC' else total>=0)
                context.flag(V,bool((~(old^value)&(old^total)&128) if op=='ADC' else ((old^value)&(old^total)&128)))
                r.a=context.nz(total&255)
            elif op in ('CLC','SEC'):context.flag(C,op=='SEC')
            elif op in ('INC','DEC'):
                address=context.address(item);memory[address]=context.nz((memory[address]+(1 if op=='INC' else -1))&255)
            elif op in ('INX','INY','DEX','DEY'):
                reg=op[-1].lower();setattr(r,reg,context.nz((getattr(r,reg)+(1 if op.startswith('IN') else -1))&255))
            elif op in ('TAX','TAY','TXA','TYA'):
                setattr(r,op[2].lower(),context.nz(getattr(r,op[1].lower())))
            elif op in ('LSR','ASL','ROL'):
                address=None if item['mode']=='acc' else context.address(item)
                value=r.a if address is None else memory[address]
                old_c=int(bool(r.p&C));context.flag(C,bool(value&1) if op=='LSR' else bool(value&128))
                value=context.nz(value>>1 if op=='LSR' else ((value<<1)|(old_c if op=='ROL' else 0))&255)
                if address is None:r.a=value
                else:memory[address]=value
            elif op=='PHA':context.push(r.a)
            elif op=='PLA':r.a=context.nz(context.pop())
            else:raise NotImplementedError(f'{op} in fixed service ${pc:04X}')
            r.pc=next_pc
        raise RuntimeError(f'Fixed service ${target:04X} did not return; PC ${r.pc:04X}')

def queued_message(memory):
    """Inspect original0310..0313 packet and0300 progress; no completion is faked."""
    return {'type':memory[0x310],'id':memory[0x311],
            'arguments':[memory[0x312],memory[0x313]],'progress':memory[0x300]}
