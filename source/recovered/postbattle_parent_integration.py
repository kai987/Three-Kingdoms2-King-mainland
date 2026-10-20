"""Compose the exact postbattle stage2 parent and its real far caller.

Only stage2 has a new exact parent body; other dispatches remain dependencies.
The D4F5 bridge begins after the historical CC29 draw and keeps the actualY,
stack and inline far-call protocol. EE07 is inherited named source. It restores
the code pair while the callee data-window side effect remains observable.
"""
from .postbattle_resource_integration import (
    PostbattleResourceGameEngine, PostbattleResourceSceneCoordinator,
)
from .postbattle_parent_services import PostbattleParentServices
from .postbattle_release_services import PostbattleReleaseController


class PostbattleReturnBridge(PostbattleReleaseController):
    """Expose the real D4F5 midpoint; CC29 and D4F3 are outside this entry.

    The actual input already carries Y28 from the earlier LDY instruction.
    This reuses the frozen return_to_city suffix, without inventing its draw,
    original JSR frame or an acknowledgement of palette completion.
    """
    ENTRY = 0xD4F5

    def run_entry(self,entry=ENTRY,**kwargs):
        registers=kwargs.get('registers')
        if registers is None or registers.pc!=entry or entry!=self.ENTRY:
            raise ValueError('The return bridge requires the actual D4F5 midpoint context')
        return super().run_entry(entry,**kwargs)

    def __call__(self,call):
        if call.memory is not self.memory or tuple(call.entry_banks[1:3])!=(12,13):
            raise ValueError('The far return bridge requires its actual shared bus and code pair')
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

    def _entry(self,entry):
        if entry==self.ENTRY:return self.finish_return_after_draw()
        raise ValueError('The return bridge does not implement the preceding CC29 draw')

    def finish_return_after_draw(self):
        r=self.registers;self._mark(0xD4F5)
        yield from self._external(0xD4F5,0xEE07,0xD4FA,'far_call',0xA006)
        if r.pc!=0xD4FA:return
        self._mark(0xD4FA);self._rts()


class PostbattleParentSceneCoordinator(PostbattleResourceSceneCoordinator):
    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        parent = pair == (8, 9) and call.target in PostbattleParentServices.NEW_ENTRIES
        bridge = pair == (12, 13) and call.target == 0xD4F5
        if not (parent or bridge):
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_parent_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal postbattle parent result belongs to another caller')
            return reply
        if key in self._owners:
            registered_call = getattr(self, '_parent_pending_calls', {}).get(key)
            if registered_call is not call:
                raise RuntimeError('A pending postbattle parent belongs to its original call object')
            owner, kind = self._owners[key]
            if not isinstance(owner, (PostbattleParentServices, PostbattleReturnBridge)):
                raise RuntimeError('Postbattle parent owner changed while suspended')
            result = owner.resume()
        else:
            owner_type = PostbattleParentServices if parent else PostbattleReturnBridge
            owner = owner_type(self.memory, self.rom, services=self)
            kind = 'named_postbattle_stage2' if parent else 'post_draw_far_return_bridge'
            result = owner(call)
            self._owners[key] = (owner, kind)
            if not hasattr(self, '_parent_pending_calls'):
                self._parent_pending_calls = {}
            self._parent_pending_calls[key] = call
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            if not hasattr(self, '_parent_nonlocal_results'):
                self._parent_nonlocal_results = {}
            reply = dict(status='nonlocal_return', source_owner=kind, body=result,
                         terminal=True, reason='The original postbattle parent caller did not return')
            self._parent_nonlocal_results[key] = (call, reply)
            return reply
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            self._parent_pending_calls.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='The postbattle parent owner is suspended on its declared service')

    def _reset_result(self, result):
        reply = super()._reset_result(result)
        if reply.get('retired_pending_callers'):
            self._parent_nonlocal_results = {}
            self._parent_pending_calls = {}
        return reply


class PostbattleParentGameEngine(PostbattleResourceGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = PostbattleParentSceneCoordinator(self)
        return self._scene_coordinator

    def postbattle_parent_services(self):
        return PostbattleParentServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )
