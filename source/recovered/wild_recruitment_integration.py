"""Compose readable postbattle release and campaign recruitment on one bus.

The battle controller keeps its real scene and caller ownership. The inherited
campaign owner handles appearance and unaffiliated recruitment; no CPU, IR,
synthetic RNG or completion acknowledgement runs in this composition.
"""
from .city_recruitment_integration import (
    CityRecruitmentGameEngine, CityRecruitmentSceneCoordinator,
)
from .postbattle_release_services import PostbattleReleaseController


class WildRecruitmentSceneCoordinator(CityRecruitmentSceneCoordinator):
    def _new_controller(self, scene):
        if scene == 3:
            return PostbattleReleaseController(self.memory, self.rom, services=self)
        return super()._new_controller(scene)


class WildRecruitmentGameEngine(CityRecruitmentGameEngine):
    def readable_scene_rules(self):
        if self._scene_coordinator is None:
            self._scene_coordinator = WildRecruitmentSceneCoordinator(self)
        return self._scene_coordinator

    def postbattle_release_services(self):
        return PostbattleReleaseController(
            self.memory, self._require_rom(), services=self.readable_scene_rules()
        )
