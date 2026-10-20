"""Compose exact audio callers inside the existing scene/global software.

Existing local JSR code has already pushed the real caller frame. Exposing
its callee as a ServiceCall preserves that frame and pending continuation;
it does not restart a scene, substitute a CPU/IR or generate an interrupt.
"""
from .battle_nmi_services import ServiceCall
from .exact_audio_requests import ExactAudioRequests
from .scene_initialization import SceneInitialization
from .global_ui_controller import GlobalUIController


class ExactAudioCallers:
    def routine(self,entry):
        if entry not in ExactAudioRequests.PUBLIC_ENTRIES:
            return (yield from super().routine(entry))
        r=self.registers;m=self.memory;r.pc=entry
        return_pc=((m[0x100+((r.sp+1)&255)]|
                    m[0x100+((r.sp+2)&255)]<<8)+1)&65535
        expected_sp=(r.sp+2)&255
        yield ServiceCall(entry,return_pc,'existing_fixed_audio_caller',r,m,
                          tuple(m.banks),expected_sp)
        if r.pc!=return_pc or r.sp!=expected_sp:
            raise RuntimeError('Exact audio has not returned to its real caller')


class IntegratedSceneInitialization(ExactAudioCallers,SceneInitialization):
    """Original setup with existing JSR frames delegated to exact audio."""


class IntegratedGlobalUI(ExactAudioCallers,GlobalUIController):
    """Original main loop with exact fixed audio, including city main1."""
