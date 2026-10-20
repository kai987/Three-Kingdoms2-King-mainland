"""Compose the named appearance-pointer helper with frozen campaign owners.

The phase24 allocation and earlier battle factories remain inherited. Exact
bank/entry/caller ownership, nonlocal recruitment and strict pending services
are retained; hardware timing and controller ports stay explicit inputs.
"""
from .pointer_lifecycle_integration import (
    PointerLifecycleGameEngine, PointerLifecycleSceneCoordinator,
)
from .appearance_pointer_services import AppearancePointerServices


class AppearancePointerSceneCoordinator(PointerLifecycleSceneCoordinator):
    def _resolve_call(self, call):
        if (tuple(call.entry_banks[1:3]) != (10, 11)
                or call.target not in AppearancePointerServices.PUBLIC_ENTRIES):
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_recruitment_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal city result belongs to another caller')
            return reply
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, AppearancePointerServices):
                raise RuntimeError('Appearance pointer owner changed while suspended')
            result = owner.resume()
        else:
            owner = AppearancePointerServices(self.memory, self.rom, services=self)
            kind = 'named_appearance_table_pointer'
            result = owner(call)
            self._owners[key] = (owner, kind)
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            if not hasattr(self, '_recruitment_nonlocal_results'):
                self._recruitment_nonlocal_results = {}
            reply = dict(status='nonlocal_return', source_owner=kind, body=result,
                         terminal=True,
                         reason='Original caller was discarded; retain the complete campaign owner')
            self._recruitment_nonlocal_results[key] = (call, reply)
            return reply
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='Actual caller is suspended on its declared dependency or wait')


class AppearancePointerGameEngine(PointerLifecycleGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = AppearancePointerSceneCoordinator(self)
        return self._scene_coordinator

    def appearance_pointer_services(self):
        return AppearancePointerServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )

    city_recruitment_services = appearance_pointer_services
    negotiation_services = appearance_pointer_services
    domestic_secondary_services = appearance_pointer_services
    city_auxiliary_services = appearance_pointer_services

    city_threshold_services = appearance_pointer_services
