"""Compose early postbattle stages with the frozen completion owners.

The new physical8/9 owner adds BAC1/BB3D and the BC46 officer controller.
Existing stages2/3, CC29, D4F0 and the far bridge keep frozen source. Human
13/14 handoffs are original state writes, not automatic UI completion.
No originalCPU, IR, readiness acknowledgement or return frame is invented.
"""
from .postbattle_completion_integration import (
    PostbattleCompletionGameEngine, PostbattleCompletionSceneCoordinator,
)
from .postbattle_early_services import PostbattleEarlyServices


class PostbattleEarlySceneCoordinator(PostbattleCompletionSceneCoordinator):
    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        if pair != (8, 9) or call.target not in PostbattleEarlyServices.NEW_ENTRIES:
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_early_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal postbattle early-stage result belongs to another caller')
            return reply
        if key in self._owners:
            registered_call = getattr(self, '_early_pending_calls', {}).get(key)
            if registered_call is not call:
                raise RuntimeError('A pending postbattle early-stage belongs to its original call object')
            owner, kind = self._owners[key]
            if not isinstance(owner, PostbattleEarlyServices):
                raise RuntimeError('Postbattle early-stage owner changed while suspended')
            result = owner.resume()
        else:
            owner = PostbattleEarlyServices(self.memory, self.rom, services=self)
            kind = 'named_postbattle_early'
            result = owner(call)
            self._owners[key] = (owner, kind)
            if not hasattr(self, '_early_pending_calls'):
                self._early_pending_calls = {}
            self._early_pending_calls[key] = call
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            if not hasattr(self, '_early_nonlocal_results'):
                self._early_nonlocal_results = {}
            reply = dict(status='nonlocal_return', source_owner=kind, body=result,
                         terminal=True, reason='The original postbattle early-stage caller did not return')
            self._early_nonlocal_results[key] = (call, reply)
            return reply
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            self._early_pending_calls.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='The postbattle early-stage owner is suspended on its declared service')

    def _reset_result(self, result):
        reply = super()._reset_result(result)
        if reply.get('retired_pending_callers'):
            self._early_nonlocal_results = {}
            self._early_pending_calls = {}
        return reply


class PostbattleEarlyGameEngine(PostbattleCompletionGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = PostbattleEarlySceneCoordinator(self)
        return self._scene_coordinator

    def postbattle_early_services(self):
        return PostbattleEarlyServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )
