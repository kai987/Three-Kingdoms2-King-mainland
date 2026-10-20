"""Additive phase18 front door to exact city-auxiliary domestic source.

Earlier source modules remain byte-for-byte historical. This composition routes
physical10/11 domestic calls through the new named recruitment methods while
retaining genuine suspended owners, caller PC/SP and explicit hardware inputs.
"""
from .game_engine import GameEngine
from .scene_coordinator import SceneCoordinator
from .city_auxiliary_services import CityAuxiliaryServices
from .city_field_contracts import CityAuxiliaryContract

class CityAuxiliarySceneCoordinator(SceneCoordinator):
    def _resolve_call(self,call):
        pair=tuple(call.entry_banks[1:3]);target=call.target;key=id(call)
        if pair!=(10,11)or target not in CityAuxiliaryServices.PUBLIC_ENTRIES:
            return super()._resolve_call(call)
        if key in self._owners:
            owner,kind=self._owners[key]
            if not isinstance(owner,CityAuxiliaryServices):return super()._resolve_call(call)
            result=owner.resume()
        else:
            owner=CityAuxiliaryServices(self.memory,self.rom,services=self)
            kind='city_auxiliary_domestic';result=owner(call);self._owners[key]=(owner,kind)
        self.calls.append(dict(target=target,kind=kind,status=result.get('status'),banks=list(call.entry_banks)))
        if result.get('status')=='reset_boundary':
            self._reset_transfer={'status':'reset_boundary','source_owner':kind,'body':result}
            return self._reset_transfer
        if result.get('status')=='returned'and call.registers.pc==call.return_pc and call.registers.sp==call.expected_sp:
            self._owners.pop(key,None)
            return {'status':'returned','source_owner':kind,'body':result}
        return {'status':'dependency','source_owner':kind,'body':result,
                'reason':'Callee has not completed its actual caller PC/SP'}

class CityAuxiliaryGameEngine(GameEngine):
    """Use existing campaign/NMI APIs with the new domestic source owner."""
    def readable_scene_rules(self):
        if self._scene_coordinator is None:self._scene_coordinator=CityAuxiliarySceneCoordinator(self)
        return self._scene_coordinator
    def city_auxiliary_services(self):
        return CityAuxiliaryServices(self.memory,self._require_rom(),services=self.readable_scene_rules())
    def city_auxiliary_record(self,city_id):
        """Raw byte names remain opaque; the exact AI overlap is exposed."""
        record=CityAuxiliaryContract.from_memory(self.memory,city_id)
        return dict(city_id=city_id,raw_byte1=record.raw[1],raw_tail28_31=list(record.tail28_31),
                    overlapping_AI_threshold_word=record.overlapping_AI_threshold_word,
                    passes_AI_threshold_300=record.passes_AI_threshold_300,
                    official_byte1_name=None,official_tail28_31_names=None,
                    tail_unused_or_padding_proved=False)
