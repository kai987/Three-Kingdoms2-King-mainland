"""Compose readable scene controllers and initialization on one explicit bus.

Every pending call has its own owner. A nested mapper/setup call cannot borrow
the suspended parent's generator, and a returned status alone cannot satisfy
its original stack/PC contract. Unknown scene services remain dependencies.
"""
from .scene_initialization import SceneInitialization
from .battle_scene_controller import BattleSceneController
from .attack_scene_controller import AttackSceneController
from .duel_scene_controller import DuelSceneController,DuelSceneData
from .battle_setup_ai import BattleSetupAI
from .battle_background_initialization import BattleBackgroundInitialization
from .portrait_ui_services import PortraitUIServices,PortraitData
from .officer_ui_services import OfficerUIServices
from .text_scene_services import TextSceneServices
from .officer_details_ui_services import OfficerDetailsUIServices,OfficerDetailsData
from .city_ui_controller import CityUIController
from .city_panel_services import CityPanelServices
from .global_ui_controller import GlobalUIController,CityUIWorkers,TitleUIController,RulerSelectionUIController,EndingUIController
from .city_action_bridges import CityActionBridges,CityActionData
from .ui_arithmetic_services import UIArithmeticServices
from .city_menu_navigation import CityMenuNavigation
from .boot_initialization import BootInitialization
from .domestic_cooperation_controller import DomesticCooperationController
from .tactical_cooperation_controller import TacticalCooperationController
from .city_cooperation_ui_services import CityCooperationUIServices
from .audio_scene_services import AudioSceneServices
from .postbattle_loyalty_bridge import PostbattleLoyaltyBridge
from .postbattle_graphics import PostbattleGraphics
from .exact_audio_requests import ExactAudioRequests
from .battle_succession import BattleSuccession
from .player_extinction import PlayerExtinction,PlayerLossEnding
from .extinction_scene_services import ExtinctionGlobalUI
from .integrated_scene_services import IntegratedSceneInitialization,IntegratedGlobalUI
from .ui_graphics_initialization import UIGraphicsInitialization,UIGraphicsData
from .scenario_initialization import ScenarioInitialization,ScenarioData
from .city_officer_details_controller import CityOfficerDetailsController,CityOfficerData
from .title_intro_graphics import TitleIntroGraphics,TitleIntroData
from .battle_nmi_services import NMIRegisters
from .service_memory import ServiceMemory


class SceneCoordinator:
    def __init__(self,game,external_callback=None):
        if not isinstance(game.memory,ServiceMemory):raise ValueError('Readable scene composition requires explicit ServiceMemory inputs')
        self.game=game;self.memory=game.memory;self.rom=game._require_rom();self.external_callback=external_callback
        self.presentation=game.presentation_rules();self._owners={};self.calls=[];self._direct={}
        self.setup=IntegratedSceneInitialization(self.memory,self.rom,callbacks=self)
        self.global_ui=ExtinctionGlobalUI(self.memory,self.rom,services=self)
        self.boot=BootInitialization(self.memory,self.rom,callbacks=self)
        self._callback_depth=0;self._public_depth=0;self._reset_transfer=None;self.reset_epoch=0
    def _public(self,operation):
        self._public_depth+=1
        try:result=operation()
        finally:self._public_depth-=1
        return self._reset_result(result)
    def _reset_result(self,result):
        transfer=self._reset_transfer
        if result.get('status')=='reset_boundary':transfer=result
        if transfer is None:return result
        registers=transfer.get('body',transfer)['registers']
        assert registers['pc']==0xE066 and registers['sp']==255
        self._owners.clear();self._direct.clear();self._reset_transfer=None;self.reset_epoch+=1
        # Reset discards the actual stack. Retire the suspended source callers
        # after the public operation returns, preserving the explicit bus/logs.
        self.game._presentation=None;self.presentation=self.game.presentation_rules()
        self.setup=IntegratedSceneInitialization(self.memory,self.rom,callbacks=self)
        self.global_ui=ExtinctionGlobalUI(self.memory,self.rom,services=self)
        self.boot=BootInitialization(self.memory,self.rom,callbacks=self)
        return {**transfer,'status':'reset_boundary','nonlocal_transfer':True,
                'retired_pending_callers':True,'reset_epoch':self.reset_epoch,
                'boundary':'Original E066 with SPFF; reset did not return to the retired caller'}
    def _new_controller(self,scene):
        if scene==2:return CityUIController(self.memory,self.rom,services=self)
        if scene==3:return BattleSceneController(self.memory,self.rom,services=self)
        if scene==4:return AttackSceneController(self.memory,self.rom,services=self)
        if scene==5:return DuelSceneController(self.memory,DuelSceneData.from_rom(self.rom),services=self)
        if scene==6:return TitleUIController(self.memory,self.rom,services=self)
        if scene==7:return RulerSelectionUIController(self.memory,self.rom,services=self)
        if scene==8:return PlayerLossEnding(self.memory,self.rom,services=self)
        raise ValueError('Direct readable NMI controllers are city2/battle3/attack4/duel5/title6/ruler7/ending8')
    def controller(self,scene=None):
        scene=self.memory[0x78]if scene is None else scene
        if scene not in self._direct:self._direct[scene]=self._new_controller(scene)
        return self._direct[scene]
    def tick(self,registers=None,*,scene=None):
        """One source callback, with an existing genuine caller stack."""
        scene=self.memory[0x78]if scene is None else scene
        controller=self.controller(scene)
        if registers is None:raise ValueError('Supply the real callback registers and existing caller frame')
        if scene==3:
            return_pc=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
            return self._public(lambda:controller.tick(registers=registers,return_pc=return_pc))
        return self._public(lambda:controller.tick(registers=registers))
    def resume(self,*,scene=None):return self._public(lambda:self.controller(scene).resume())
    def run_setup(self,entry,registers=None):return self._public(lambda:self.setup.run_setup(entry,registers))
    def resume_setup(self):return self._public(self.setup.resume)
    def run_main(self,entry,registers):
        if registers is None:raise ValueError('Supply actual main-loop registers and caller context')
        return self._public(lambda:self.global_ui.run_main(entry,registers))
    def resume_main(self):return self._public(self.global_ui.resume)
    def run_boot(self,registers):return self._public(lambda:self.boot.run_reset(registers))
    def resume_boot(self):return self._public(self.boot.resume)
    def run_nmi(self,registers=None,*,hardware_entry=False):
        # Route NMI callees through exact source owners before semantic
        # presentation bridges, so text scratch/stack effects remain visible.
        self.presentation.nmi.callbacks=self
        return self._public(lambda:self.presentation.run_nmi(registers,hardware_entry=hardware_entry,external_callback=self))
    def resume_nmi(self):return self._public(self.presentation.resume_nmi)
    def run_irq(self,registers=None,*,hardware_entry=False):
        self.presentation.irq.callbacks=self
        return self._public(lambda:self.presentation.run_irq(registers,hardware_entry=hardware_entry))
    def resume_irq(self):return self._public(self.presentation.irq.resume)
    def __call__(self,call):
        self._callback_depth+=1
        try:result=self._resolve_call(call)
        finally:self._callback_depth-=1
        return self._reset_result(result)if self._callback_depth==0 and self._public_depth==0 else result
    def _resolve_call(self,call):
        """Resolve an identified callee; never install a CPU/IR fallback."""
        key=id(call);pair=tuple(call.entry_banks[1:3]);target=call.target
        if key in self._owners:
            owner,kind=self._owners[key];result=owner.resume()
        else:
            kind=None;owner=None
            if pair==(27,28)and target in CityUIController.LOCAL_ENTRIES:
                owner=CityUIController(self.memory,self.rom,services=self);kind='city_ui';result=owner(call)
            elif pair==(25,26)and target in BattleSuccession.PUBLIC_ENTRIES:
                owner=PlayerExtinction(self.memory,self.rom,services=self);kind='battle_succession';result=owner(call)
            elif pair==(25,26)and target in CityOfficerDetailsController.LOCAL_ENTRIES:
                owner=CityOfficerDetailsController(self.memory,CityOfficerData.from_rom(self.rom),services=self);kind='city_officer_details';result=owner(call)
            elif pair==(25,26)and target in CityPanelServices.LOCAL_ENTRIES:
                owner=CityPanelServices(self.memory,self.rom,services=self);kind='city_panels';result=owner(call)
            elif pair==(29,30)and target in ScenarioInitialization.LOCAL_ENTRIES:
                owner=ScenarioInitialization(self.memory,ScenarioData.from_rom(self.rom),services=self);kind='scenario_initialization';result=owner(call)
            elif pair==(29,30)and target in CityCooperationUIServices.PUBLIC_ENTRIES:
                owner=CityCooperationUIServices(self.memory,self.rom,services=self);kind='city_cooperation_ui';result=owner(call)
            elif pair==(29,30)and target in PostbattleGraphics.PUBLIC_ENTRIES:
                owner=PostbattleGraphics(self.memory,self.rom,services=self);kind='postbattle_calendar';result=owner(call)
            elif pair==(14,15)and target in AudioSceneServices.PUBLIC_ENTRIES:
                owner=AudioSceneServices(self.memory,self.rom,services=self);kind='audio_scene_exact';result=owner(call)
            elif target in ExactAudioRequests.PUBLIC_ENTRIES:
                owner=ExactAudioRequests(self.memory,self.rom,services=self);kind='audio_request_exact';result=owner(call)
            elif target in UIArithmeticServices.FIXED:
                owner=UIArithmeticServices(self.memory);kind='ui_arithmetic';result=owner(call)
            elif target in CityMenuNavigation.PUBLIC_ENTRIES:
                owner=CityMenuNavigation(self.memory,self.rom,callbacks=self);kind='city_menu_navigation';result=owner(call)
            elif target in (0xE000,*BootInitialization.FIXED):
                owner=BootInitialization(self.memory,self.rom,callbacks=self);kind='boot_initialization';result=owner(call)
            elif pair==(10,11)and target in DomesticCooperationController.PUBLIC_ENTRIES:
                owner=DomesticCooperationController(self.memory,self.rom,services=self);kind='domestic_cooperation';result=owner(call)
            elif pair==(10,11)and target in PostbattleLoyaltyBridge.PUBLIC_ENTRIES:
                owner=PostbattleLoyaltyBridge(self.memory,self.rom,services=self);kind='postbattle_loyalty';result=owner(call)
            elif pair==(8,9)and target in TacticalCooperationController.LOCAL_ENTRIES:
                owner=TacticalCooperationController(self.memory,self.rom,services=self);kind='tactical_cooperation';result=owner(call)
            elif (pair==(8,9)and target in CityActionBridges.SHOP_ENTRIES or
                  pair==(10,11)and target in CityActionBridges.LOYALTY_ENTRIES):
                owner=CityActionBridges(self.memory,CityActionData.from_rom(self.rom),services=self);kind='city_action_bridges';result=owner(call)
            elif pair==(23,24)and target in PlayerLossEnding.PUBLIC_ENTRIES:
                owner=PlayerLossEnding(self.memory,self.rom,services=self);kind='player_loss_ending';result=owner(call)
            elif (pair==(29,30)and target in CityUIWorkers.PUBLIC_ENTRIES or
                  pair==(10,11)and target in TitleUIController.PUBLIC_ENTRIES or
                  pair==(8,9)and target in RulerSelectionUIController.PUBLIC_ENTRIES or
                  pair==(23,24)and target in EndingUIController.PUBLIC_ENTRIES):
                owner=GlobalUIController(self.memory,self.rom,services=self);kind='global_ui';result=owner(call)
            elif pair==(23,24)and target in UIGraphicsInitialization.LOCAL_ENTRIES:
                owner=UIGraphicsInitialization(self.memory,UIGraphicsData.from_rom(self.rom),services=self);kind='ui_graphics_initialization';result=owner(call)
            elif pair==(23,24)and target in TitleIntroGraphics.LOCAL_ENTRIES:
                owner=TitleIntroGraphics(self.memory,TitleIntroData.from_rom(self.rom),services=self);kind='title_intro';result=owner(call)
            elif pair==(25,26)and target in OfficerDetailsUIServices.LOCAL_ENTRIES:
                owner=OfficerDetailsUIServices(self.memory,OfficerDetailsData.from_rom(self.rom),services=self);kind='officer_details_ui';result=owner(call)
            elif target==0xF1B7 or pair==(25,26)and target in(0xA000,0xCE1F):
                owner=PortraitUIServices(self.memory,PortraitData.from_rom(self.rom),services=self);kind='portrait_ui';result=owner(call)
            elif target==0xF308 or pair==(29,30)and target in OfficerUIServices.ENTRIES:
                owner=OfficerUIServices(self.memory,self.rom,services=self);kind='officer_ui';result=owner(call)
            elif target==0xEE72 or pair==(29,30)and target in TextSceneServices.PUBLIC_ENTRIES:
                owner=TextSceneServices(self.memory,self.rom,services=self);kind='text_cpu_protocol';result=owner(call)
            elif target==0xF09C or pair==(23,24)and target in(0xA009,0xA2FF):
                owner=BattleBackgroundInitialization(self.memory,self.rom,services=self);kind='battle_background';result=owner(call)
            elif target in SceneInitialization.FIXED:
                owner=IntegratedSceneInitialization(self.memory,self.rom,callbacks=self);kind='shared'
                result=owner(call)
            elif pair in((8,9),(12,13)):
                owner=BattleSetupAI(self.memory,self.rom,services=self)if pair==(8,9)else self._new_controller(3)
                kind='battle_setup_ai'if pair==(8,9)else'battle'
                try:owner._entry(target)
                except ValueError:owner=None;result=None
                if owner is not None:result=owner.run_entry(target,registers=call.registers,seed_return=False,return_pc=call.return_pc)
            elif pair==(14,15)and target not in(0xA003,0xD8D4):
                owner=self._new_controller(4);kind='attack'
                try:owner._entry(target)
                except ValueError:owner=None;result=None
                if owner is not None:result=owner.run_entry(target,registers=call.registers,seed_return=False,return_pc=call.return_pc)
            elif pair==(23,24)and (target==0xA01B or target in DuelSceneController.LOCAL_ENTRIES):
                owner=self._new_controller(5);kind='duel';result=owner.run_entry(0xB100 if target==0xA01B else target,registers=call.registers)
            else:
                owner=SceneInitialization(self.memory,self.rom,callbacks=self);kind='scene_graphics';result=owner.banked_graphics(call)
                if result['status']=='dependency'and owner._program is None:owner=None;result=None
            if owner is None and self._presentation_owns(pair,target):
                return self.presentation.source_callback(call)
            if owner is not None and result.get('status')=='reset_boundary':
                self._reset_transfer={'status':'reset_boundary','source_owner':kind,'body':result}
                return self._reset_transfer
            if owner is not None:self._owners[key]=(owner,kind)
            elif self.external_callback is not None:
                result=self.external_callback(call)
                if isinstance(result,dict)and result.get('status')=='returned'and call.registers.pc==call.return_pc and call.registers.sp==call.expected_sp:
                    return result
                return {'status':'dependency','target':target,'reason':'External owner has not returned with explicit status and actual PC/SP'}
            else:
                return {'status':'dependency','target':target,'entry_banks':list(call.entry_banks),
                        'reason':'No independent scene/helper body owns this exact entry'}
        self.calls.append(dict(target=target,kind=kind,status=result.get('status'),banks=list(call.entry_banks)))
        if result.get('status')=='reset_boundary':
            self._reset_transfer={'status':'reset_boundary','source_owner':kind,'body':result}
            return self._reset_transfer
        if result.get('status')=='returned' and call.registers.pc==call.return_pc and call.registers.sp==call.expected_sp:
            self._owners.pop(key,None)
            return {'status':'returned','source_owner':kind,'body':result}
        return {'status':'dependency','source_owner':kind,'body':result,
                'reason':'Callee has not completed its actual caller PC/SP'}

    @staticmethod
    def _presentation_owns(pair,target):
        """Exact entries only: the facade's unknown callback points back here."""
        return (pair==(14,15)and target in(0xA003,0xD8D4)or
                pair==(29,30)and target in(0xA000,0xA048,0xA003,0xA154,0xA158,0xA006,0xA11B,0xA027,0xA830)or
                pair==(25,26)and target in(0xA00F,0xCFD6)or
                pair==(23,24)and target in(0xA00C,0xA387,0xA00F,0xAB53)or
                pair==(12,13)and target in(0xD6CC,0xD657,0xDC63,0xDC70))
