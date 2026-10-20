"""Actual captured entry guard and retained ownership for readable Source.

No CPU, IR, original core, snapshot advance, ready acknowledgement or missing
service implementation lives here. All gameplay and interrupt owners are the
frozen recovered programs. The caller must separately declare device inputs.
"""
import hashlib
from .postbattle_continuity_phase32 import PostbattleContinuity


class ActualE066PostbattleContinuity(PostbattleContinuity):
    def __init__(self, game, registers, *, actual_context):
        expected=actual_context['actual_registers']
        if any(getattr(registers,key)!=expected[key] for key in ('a','x','y','p','sp','pc')):
            raise ValueError('Use the actual captured registers without overrides')
        if expected['pc']!=0xE066 or list(game.memory.banks)!=actual_context['actual_PRG_banks']:
            raise ValueError('Use the actual E066 entry and actual four PRG pages')
        for raw,key in ((bytes(game.memory.ram),'RAM_sha256'),(bytes(game.memory.sram),'SRAM_sha256')):
            if hashlib.sha256(raw).hexdigest()!=actual_context[key]:
                raise ValueError('The single initial memory import differs from its actual capture')
        super().__init__(game,registers)
        self.actual_entry=dict(registers=dict(expected),banks=list(game.memory.banks),
                               RAM_sha256=actual_context['RAM_sha256'],SRAM_sha256=actual_context['SRAM_sha256'])

    def ownership(self):
        result=super().ownership()
        inner=[]
        for owner,kind in self.coordinator._owners.values():
            pending=getattr(owner,'pending',None)
            inner.append(dict(owner_identity=self._reference(owner),kind=kind,
                pending_identity=self._reference(pending)if pending is not None else None,
                generator_identity=self._reference(getattr(owner,'_program',None)),
                target=getattr(pending,'target',None)))
        result['retained_inner_owners']=inner
        return result
