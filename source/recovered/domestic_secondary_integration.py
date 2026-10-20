"""Phase19 campaign composition with named secondary domestic decisions.

Physical10/11 calls retain their true caller, suspended owner and reply
predicate. Existing main/NMI/IRQ and UI consumers provide later progress.
Snapshot import preserves saved registers; hardware inputs remain explicit.
"""
from .city_auxiliary_integration import CityAuxiliaryGameEngine, CityAuxiliarySceneCoordinator
from .domestic_secondary_services import DomesticSecondaryServices
from .nestopia_context import NestopiaContext
from .battle_nmi_services import NMIRegisters


class DomesticSecondarySceneCoordinator(CityAuxiliarySceneCoordinator):
    def _resolve_call(self, call):
        pair = tuple(call.entry_banks[1:3])
        if pair != (10, 11) or call.target not in DomesticSecondaryServices.PUBLIC_ENTRIES:
            return super()._resolve_call(call)
        key = id(call)
        if key in self._owners:
            owner, kind = self._owners[key]
            if not isinstance(owner, DomesticSecondaryServices):
                return super()._resolve_call(call)
            result = owner.resume()
        else:
            owner = DomesticSecondaryServices(self.memory, self.rom, services=self)
            kind = 'named_domestic_secondary'
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


class DomesticSecondaryGameEngine(CityAuxiliaryGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = DomesticSecondarySceneCoordinator(self)
        return self._scene_coordinator

    def domestic_secondary_services(self):
        return DomesticSecondaryServices(self.memory, self._require_rom(),
                                         services=self.readable_scene_rules())

    def city_auxiliary_record(self, city_id):
        record = super().city_auxiliary_record(city_id)
        record['treasure_count_plus16'] = self.memory[0x6000 + city_id * 32 + 16]
        record['treasure_original_UI_labels'] = ['宝', 'タカラ']
        return record

    @classmethod
    def from_nestopia_state(cls, rom, state, **hardware_inputs):
        """Return the source engine and exact captured CPU registers.

        A saved midroutine PC is not automatically a campaign main boundary.
        The caller must choose a supported owner or continue original bytes
        in a validation oracle; this constructor never runs original bytes.
        """
        context = NestopiaContext.parse(state)
        game = cls(context.service_memory(rom, **hardware_inputs), rom=rom, mapped=True)
        return game, NMIRegisters(**context.registers)
