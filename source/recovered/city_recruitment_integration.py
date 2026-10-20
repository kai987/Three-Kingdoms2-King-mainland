"""Campaign composition with named city appearance and recruitment services.

The normal campaign enters through its real A000/C5B9 owner. A deliberately
separate bare C6CC call can discard its caller frame; that result is terminal,
never a fabricated local RTS or a resumable service. Hardware timing remains
an explicit input to the inherited source NMI/IRQ coordinator.
"""
from .negotiation_integration import NegotiationGameEngine, NegotiationSceneCoordinator
from .city_recruitment_services import CityRecruitmentServices


class CityRecruitmentSceneCoordinator(NegotiationSceneCoordinator):
    def _reset_result(self, result):
        result = super()._reset_result(result)
        if result.get('status') == 'reset_boundary':
            # Reset retires the original callers together with their owners.
            self._recruitment_nonlocal_results = {}
        return result

    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        if pair != (10, 11) or call.target not in CityRecruitmentServices.PUBLIC_ENTRIES:
            return super()._resolve_call(call)
        key = id(call)
        terminal = getattr(self, '_recruitment_nonlocal_results', {})
        if key in terminal:
            registered_call, reply = terminal[key]
            if registered_call is not call:
                raise RuntimeError('Terminal recruitment result belongs to a different caller')
            return reply
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, CityRecruitmentServices):
                return super()._resolve_call(call)
            result = owner.resume()
        else:
            owner = CityRecruitmentServices(self.memory, self.rom, services=self)
            kind = 'named_city_recruitment'
            result = owner(call)
            self._owners[key] = (owner, kind)
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if result.get('status') == 'nonlocal_return':
            # The actual registers/stack already contain the outer return.
            # Retain the owner identity and stored terminal result so a
            # mistaken retry cannot restart the callee or pop another frame.
            if not hasattr(self, '_recruitment_nonlocal_results'):
                self._recruitment_nonlocal_results = {}
            terminal_result = dict(status='nonlocal_return', source_owner=kind,
                                   body=result, terminal=True,
                                   reason='The original double PLA returned beyond this caller; use its C5B9 campaign owner')
            self._recruitment_nonlocal_results[key] = (call, terminal_result)
            return terminal_result
        if (result.get('status') == 'returned' and
                call.registers.pc == call.return_pc and
                call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='The actual caller remains suspended on a declared dependency or original wait')


class CityRecruitmentGameEngine(NegotiationGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = CityRecruitmentSceneCoordinator(self)
        return self._scene_coordinator

    def city_recruitment_services(self):
        return CityRecruitmentServices(self.memory, self._require_rom(),
                                       services=self.readable_scene_rules())

    def negotiation_services(self):
        return self.city_recruitment_services()

    def domestic_secondary_services(self):
        return self.city_recruitment_services()
