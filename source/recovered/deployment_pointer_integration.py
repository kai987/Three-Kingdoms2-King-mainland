"""Compose exact formation-pointer services with the frozen campaign owners.

Only the physical8/9 deployment entries select the new owner. The established
strategy distribution is inherited; the two pointer constructors are readable
refactors. Pending calls keep their own real register and stack context.
"""
from .appearance_pointer_integration import (
    AppearancePointerGameEngine, AppearancePointerSceneCoordinator,
)
from .deployment_pointer_services import DeploymentPointerServices


class DeploymentPointerSceneCoordinator(AppearancePointerSceneCoordinator):
    def _resolve_call(self, call):
        if (tuple(call.entry_banks[1:3]) != (8, 9)
                or call.target not in DeploymentPointerServices.PUBLIC_ENTRIES):
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_deployment_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal deployment result belongs to another caller')
            return reply
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, DeploymentPointerServices):
                raise RuntimeError('Deployment owner changed while suspended')
            result = owner.resume()
        else:
            owner = DeploymentPointerServices(self.memory, self.rom, services=self)
            kind = 'named_deployment_pointer'
            result = owner(call)
            self._owners[key] = (owner, kind)
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            if not hasattr(self, '_deployment_nonlocal_results'):
                self._deployment_nonlocal_results = {}
            reply = dict(status='nonlocal_return', source_owner=kind, body=result,
                         terminal=True, reason='The original deployment caller did not return')
            self._deployment_nonlocal_results[key] = (call, reply)
            return reply
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='The deployment owner is suspended on its declared service')

    def _reset_result(self, result):
        reply = super()._reset_result(result)
        if reply.get('retired_pending_callers'):
            self._deployment_nonlocal_results = {}
        return reply


class DeploymentPointerGameEngine(AppearancePointerGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = DeploymentPointerSceneCoordinator(self)
        return self._scene_coordinator

    def deployment_pointer_services(self):
        return DeploymentPointerServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )
