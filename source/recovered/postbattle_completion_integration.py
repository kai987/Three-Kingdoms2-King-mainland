"""Compose the exact postbattle completion with the frozen stage2 owners.

The new physical8/9 owner implements stages2/3; stages0/1 remain dependencies.
The existing D4F5 bridge, CC29 drawing and D4F0 parent keep their original
source. Their actual caller comparisons are new evidence, not new algorithms.
No completion flag, return frame, mapper restore or NMI is manufactured here.
"""
from .postbattle_parent_integration import (
    PostbattleParentGameEngine, PostbattleParentSceneCoordinator,
)
from .postbattle_completion_services import PostbattleCompletionServices


class PostbattleCompletionSceneCoordinator(PostbattleParentSceneCoordinator):
    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        if pair != (8, 9) or call.target not in PostbattleCompletionServices.NEW_ENTRIES:
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_completion_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal postbattle completion result belongs to another caller')
            return reply
        if key in self._owners:
            registered_call = getattr(self, '_completion_pending_calls', {}).get(key)
            if registered_call is not call:
                raise RuntimeError('A pending postbattle completion belongs to its original call object')
            owner, kind = self._owners[key]
            if not isinstance(owner, PostbattleCompletionServices):
                raise RuntimeError('Postbattle completion owner changed while suspended')
            result = owner.resume()
        else:
            owner = PostbattleCompletionServices(self.memory, self.rom, services=self)
            kind = 'named_postbattle_completion'
            result = owner(call)
            self._owners[key] = (owner, kind)
            if not hasattr(self, '_completion_pending_calls'):
                self._completion_pending_calls = {}
            self._completion_pending_calls[key] = call
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            if not hasattr(self, '_completion_nonlocal_results'):
                self._completion_nonlocal_results = {}
            reply = dict(status='nonlocal_return', source_owner=kind, body=result,
                         terminal=True, reason='The original postbattle completion caller did not return')
            self._completion_nonlocal_results[key] = (call, reply)
            return reply
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            self._completion_pending_calls.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='The postbattle completion owner is suspended on its declared service')

    def _reset_result(self, result):
        reply = super()._reset_result(result)
        if reply.get('retired_pending_callers'):
            self._completion_nonlocal_results = {}
            self._completion_pending_calls = {}
        return reply


class PostbattleCompletionGameEngine(PostbattleParentGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = PostbattleCompletionSceneCoordinator(self)
        return self._scene_coordinator

    def postbattle_completion_services(self):
        return PostbattleCompletionServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )
