"""Independent bank8 tactical AI cooperation controller.

All reachable bodies execute separate lifted IR. ROM is table/resource data;
this source never calls an original-ROM CPU executor. One update proposes an
action; the battle NMI controller later performs its effect. No frames or IRQ
completion are manufactured. Real nested callers own registers/SP/return PC.
"""
from pathlib import Path
import json
from .battle_state_machine import BattleStateMachine,Registers,UnresolvedDependency,InvalidState
from .controller_helpers import MissingSharedHelper
from .runtime_services import RuntimeServices
from .mapped_memory import UnsupportedHardware

ROOT=Path(__file__).resolve().parents[2]
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
FIELDS={'request':0x6f8b,'actor_slot':0x6f8c,'proposal_action_or_destination':0x6f8d,
        'proposal_target_slot':0x6f8e,'proposal_status':0x6f8f,'rng_cursor':0x6f92,
        'scan_slot':0x6f94,'status3_count':0x6f95,'eligible_attempts':0x6f96,
        'battle_main':0x500,'battle_sub':0x501,'active_side':0x504,'action_budget':0x505}
DOMAINS={0xa09e:8,0xacab:16}
def snapshot(memory):return {name:memory[address]for name,address in FIELDS.items()}

class TacticalDispatch:
    """Exact B517..B535 protocol, including scratch, flags and consumed stack."""
    def __init__(self,fallback=None):self.fallback=RuntimeServices(fallback)
    def __call__(self,context,target,return_pc,kind):
        if target!=0xb517:return self.fallback(context,target,return_pc,kind)
        r=context.registers;pc=context.events[-1]['call_pc'];index=r.a
        if pc not in DOMAINS or index>=DOMAINS[pc]:
            raise InvalidState(f'Index {index} exceeds proven B517 domain at ${pc:04X}')
        m=context.memory;m[0x20]=r.y
        context.flag(1,bool(r.a&128));r.a=context.nz(r.a<<1)
        r.y=context.nz(r.a);r.y=context.nz(r.y+1)
        r.a=context.nz(context.pop());m[0x21]=r.a
        r.a=context.nz(context.pop());m[0x22]=r.a
        pointer=m[0x21]|m[0x22]<<8
        r.a=context.nz(m[(pointer+r.y)&65535]);m[0x23]=r.a
        r.y=context.nz(r.y+1)
        r.a=context.nz(m[(pointer+r.y)&65535]);m[0x24]=r.a
        r.y=context.nz(m[0x20]);r.pc=m[0x23]|m[0x24]<<8

class _TacticalExecutor(BattleStateMachine):
    def external(self,item,target,return_pc,kind):
        self.events.append({'call_pc':item['pc'],'target':target,'return_pc':return_pc,'kind':kind,
                            'control':snapshot(self.memory),'registers':vars(self.registers).copy(),
                            'physical_banks':list(self.memory.banks)if hasattr(self.memory,'banks')else None})
        self.hooks(self,target,return_pc,kind)

class TacticalAIControl:
    """One exact A02D cooperative update, or explicit legal helper entry.

    Direct standalone defaults seed the historical0200 return fixture. A real
    main-loop bridge must pass seed_return=False, the shared register object,
    and its actual E22C return PC. No other stack/frame state is synthesized.
    """
    def __init__(self,memory,hooks=None,program=None):
        if program is None:program=json.loads((ROOT/'analysis/phase7/controller/program.json').read_text())
        self.memory=memory;self.machine=_TacticalExecutor(memory,TacticalDispatch(hooks),program)
    def run_entry(self,entry=0xa02d,**kwargs):
        before=snapshot(self.memory)
        try:
            result=self.machine.run_entry(entry,**kwargs);result['status']='returned'
        except (UnresolvedDependency,MissingSharedHelper,UnsupportedHardware)as exc:
            result={'status':'dependency','instructions':len(self.machine.executed),'events':list(self.machine.events),
                    'dependency':{'target':getattr(exc,'target',None),'call_pc':getattr(exc,'call_pc',None),'pc':self.machine.registers.pc,'message':str(exc)}}
        except RuntimeError as exc:
            if isinstance(exc,InvalidState)or'instruction budget exhausted'not in str(exc):raise
            result={'status':'budget','instructions':len(self.machine.executed),'events':list(self.machine.events),'budget_pc':self.machine.registers.pc}
        result.update(before=before,after=snapshot(self.memory),registers=vars(self.machine.registers).copy(),control_fields=dict(FIELDS))
        return result
    def step(self,**kwargs):return self.run_entry(0xa02d,**kwargs)
    def phase(self,*args,**kwargs):raise TypeError('Tactical AI has no0500/0501 phase setter; supply its actual control fields')
    @property
    def registers(self):return self.machine.registers
    @property
    def executed(self):return self.machine.executed
