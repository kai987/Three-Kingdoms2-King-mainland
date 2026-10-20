"""Compose named city resource helpers with the existing campaign owners.

The city+1 label remains opaque. Original branch operands, caller ownership,
nonlocal recruitment returns, and the phase22 battle factory are preserved.
"""
from .wild_recruitment_integration import (
    WildRecruitmentGameEngine, WildRecruitmentSceneCoordinator,
)
from .city_threshold_services import CityThresholdServices


class CityThresholdSceneCoordinator(WildRecruitmentSceneCoordinator):
    def _resolve_call(self, call):
        if (tuple(call.entry_banks[1:3]) != (10, 11)
                or call.target not in CityThresholdServices.PUBLIC_ENTRIES):
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
            if not isinstance(owner, CityThresholdServices):
                raise RuntimeError('City resource owner changed while suspended')
            result = owner.resume()
        else:
            owner = CityThresholdServices(self.memory, self.rom, services=self)
            kind = 'named_city_threshold_resources'
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


class CityThresholdGameEngine(WildRecruitmentGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = CityThresholdSceneCoordinator(self)
        return self._scene_coordinator

    def city_threshold_services(self):
        return CityThresholdServices(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )

    city_recruitment_services = city_threshold_services
    negotiation_services = city_threshold_services
    domestic_secondary_services = city_threshold_services
    city_auxiliary_services = city_threshold_services
