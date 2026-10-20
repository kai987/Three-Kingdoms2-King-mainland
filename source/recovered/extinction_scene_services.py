"""Compose the actual loss ending with existing exact main-loop services."""
from .integrated_scene_services import IntegratedGlobalUI
from .player_extinction import PlayerLossEnding


class ExtinctionGlobalUI(IntegratedGlobalUI):
    """Keep the original main/audio frames and use the readable loss owner."""
    def __init__(self, memory, rom, services=None):
        super().__init__(memory, rom, services=services)
        self.ending = PlayerLossEnding(memory, rom, services=services)
