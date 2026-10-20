"""Phase20 campaign composition with named negotiation helpers.

Physical10/11 calls retain their true caller, suspended owner and reply
predicate. Existing main/NMI/IRQ and UI consumers provide later progress.
Snapshot import preserves saved registers; hardware inputs remain explicit.
"""
from .domestic_secondary_integration import DomesticSecondaryGameEngine, DomesticSecondarySceneCoordinator
from .negotiation_services import NegotiationServices


class NegotiationSceneCoordinator(DomesticSecondarySceneCoordinator):
    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        if pair != (10, 11) or call.target not in NegotiationServices.PUBLIC_ENTRIES:
            return super()._resolve_call(call)
        key = id(call)
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, NegotiationServices):
                return super()._resolve_call(call)
            result = owner.resume()
        else:
            owner = NegotiationServices(self.memory, self.rom, services=self)
            kind = 'named_negotiation'
            result = owner(call)
            self._owners[key] = (owner, kind)
        self.calls.append(dict(target=call.target, kind=kind,
                               status=result.get('status'), banks=list(call.entry_banks)))
        if result.get('status') == 'reset_boundary':
            self._reset_transfer = dict(status='reset_boundary', source_owner=kind, body=result)
            return self._reset_transfer
        if (result.get('status') == 'returned' and
                call.registers.pc == call.return_pc and
                call.registers.sp == call.expected_sp):
            self._owners.pop(key, None)
            return dict(status='returned', source_owner=kind, body=result)
        return dict(status='dependency', source_owner=kind, body=result,
                    reason='Actual caller is suspended until its dependency or reply completes')


class NegotiationGameEngine(DomesticSecondaryGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = NegotiationSceneCoordinator(self)
        return self._scene_coordinator

    def negotiation_services(self):
        return NegotiationServices(self.memory, self._require_rom(),
                                         services=self.readable_scene_rules())

    def domestic_secondary_services(self):
        return self.negotiation_services()
