"""Continue readable campaign software on one caller-owned register context.

Main-loop work, accepted NMI/IRQ arrivals and pending service continuations
are explicit operations. This layer never schedules a video frame, generates
an input, writes an acknowledgement or substitutes a CPU/IR implementation.
"""
from dataclasses import dataclass,asdict
from .service_memory import ServiceMemory
from .battle_nmi_services import BattleNMIServices


@dataclass
class PendingPhase:
    kind:str
    origin_pc:int
    origin_sp:int
    wait_pc:int
    wait_sp:int
    token:int=0


class CampaignSession:
    """One genuine register object shared by cooperating source controllers.

    A pending main call may be interrupted by an explicitly supplied NMI or
    accepted IRQ. The interrupt must actually RTI to its interrupted PC/SP
    before the original pending generator can resume. Every accepted interrupt
    owns its generator, including a busy NMI interrupting a suspended NMI.
    """
    def __init__(self,game,registers):
        if not isinstance(game.memory,ServiceMemory):
            raise ValueError('Campaign session requires explicit ServiceMemory')
        if registers is None or any(not hasattr(registers,k)for k in('a','x','y','p','sp','pc')):
            raise ValueError('Supply the actual caller register object')
        self.game=game;self.memory=game.memory;self.registers=registers
        self.coordinator=game.readable_scene_rules();self.pending=[];self.events=[]
        self.reset_epoch=self.coordinator.reset_epoch
        self._interrupt_owners={};self._next_token=1

    def _sync_reset(self):
        if self.reset_epoch!=self.coordinator.reset_epoch:
            self.pending.clear();self.reset_epoch=self.coordinator.reset_epoch
            self._interrupt_owners.clear()

    def state(self):
        self._sync_reset();m=self.memory;r=self.registers
        return dict(registers={k:getattr(r,k)for k in('a','x','y','p','sp','pc')},
            main_state=m[0x7A],NMI_scene=m[0x78],calendar_raw=[m[0x6F00],m[0x6F01]],
            ruler=m[0x6F03],command_budget=m[0x6F05],cooperation_request=m[0x6F8B],
            pending=[asdict(x)for x in self.pending],reset_epoch=self.reset_epoch)

    def _finish(self,phase,result,*,resume=False):
        if self.coordinator.reset_epoch!=self.reset_epoch or result.get('status')=='reset_boundary':
            self._sync_reset();self.pending.clear()
        elif result.get('status')=='returned':
            r=self.registers
            expected_pc=0xE066 if phase.kind=='main'else phase.origin_pc
            if r.pc!=expected_pc or r.sp!=phase.origin_sp:
                raise RuntimeError('Source did not reach its actual main/interrupt PC/SP boundary')
            if resume:self.pending.pop()
            self._interrupt_owners.pop(phase.token,None)
        elif result.get('status')in('dependency','waiting','budget'):
            phase.wait_pc=self.registers.pc;phase.wait_sp=self.registers.sp
            if not resume:self.pending.append(phase)
        else:
            raise RuntimeError('Unknown source completion status; caller context retained')
        self.events.append(dict(operation=('resume_'if resume else'enter_')+phase.kind,
            status=result['status'],pc=self.registers.pc,sp=self.registers.sp,
            pending_depth=len(self.pending),reset_epoch=self.reset_epoch))
        return dict(status=result['status'],body=result,session=self.state())

    def main(self):
        self._sync_reset();r=self.registers
        if self.pending:raise RuntimeError('Resume the pending source operation first')
        if r.pc!=0xE066:raise ValueError('Main update requires actual E066 entry registers')
        phase=PendingPhase('main',r.pc,r.sp,r.pc,r.sp)
        return self._finish(phase,self.game.tick_readable_main(r))

    def nmi(self):
        self._sync_reset();r=self.registers
        return self._interrupt('nmi')

    def irq(self):
        self._sync_reset();r=self.registers
        if r.p&4:raise ValueError('CPU interrupt-disable flag masks this IRQ arrival')
        return self._interrupt('irq')

    def _interrupt(self,kind):
        r=self.registers;token=self._next_token;self._next_token+=1
        phase=PendingPhase(kind,r.pc,r.sp,r.pc,r.sp,token)
        owner=BattleNMIServices(self.memory,callbacks=self.coordinator)
        self._interrupt_owners[token]=owner
        operation=owner.run_nmi if kind=='nmi'else owner.run_irq
        result=self.coordinator._public(lambda:operation(r,hardware_entry=True))
        return self._finish(phase,result)

    def resume(self):
        self._sync_reset()
        if not self.pending:raise RuntimeError('No pending campaign operation')
        phase=self.pending[-1];r=self.registers
        if(r.pc,r.sp)!=(phase.wait_pc,phase.wait_sp):
            raise ValueError('Restore the actual suspended PC/SP before resuming its owner')
        operation=self.game.resume_readable_main if phase.kind=='main'else lambda:self.coordinator._public(self._interrupt_owners[phase.token].resume)
        return self._finish(phase,operation(),resume=True)
