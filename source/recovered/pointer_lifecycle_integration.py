"""Compose named allocation UI with the frozen campaign and battle owners.

Both the NMI scene factory and actual bank27/28 helper calls use the same
new controller class. Hardware inputs, suspended callers and exact PC/SP
completion remain explicit; no missing callee is acknowledged here.
"""
from .city_threshold_integration import CityThresholdGameEngine, CityThresholdSceneCoordinator
from .pointer_lifecycle_services import PointerLifecycleServices


class PointerLifecycleSceneCoordinator(CityThresholdSceneCoordinator):
    def _new_controller(self, scene):
        if scene == 2:
            return PointerLifecycleServices(self.memory, self.rom, services=self)
        return super()._new_controller(scene)

    def _resolve_call(self, call):
        if (tuple(call.entry_banks[1:3]) != (27, 28)
                or call.target not in PointerLifecycleServices.LOCAL_ENTRIES):
            return super()._resolve_call(call)
        key = id(call)
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, PointerLifecycleServices):
                raise RuntimeError('Allocation UI owner changed while suspended')
            result = owner.resume()
        else:
            owner = PointerLifecycleServices(self.memory, self.rom, services=self)
            kind = 'named_pointer_lifecycle_UI'
            result = owner(call)
            self._owners[key] = (owner, kind)
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if (result.get('status') == 'returned'
                and call.registers.pc == call.return_pc
                and call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='Actual UI caller is suspended on its declared dependency or wait')


class PointerLifecycleGameEngine(CityThresholdGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = PointerLifecycleSceneCoordinator(self)
        return self._scene_coordinator

    def pointer_lifecycle_services(self):
        return PointerLifecycleServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )

    city_ui_services = pointer_lifecycle_services
