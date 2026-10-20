"""Readable integration of the recovered game records and scene controllers.

This layer shares CPU-addressed RAM/SRAM between battle, attack and duel. It dispatches
the controllers from $0078, as the original NMI does, rather than confusing the
global main-loop state $007A with the scene's own state bytes.

It is a control/logic model, not an NES emulator: PPU, IRQ, audio and global
scene setup remain explicit dependencies. No absent dependency silently succeeds.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable

from .officers import OfficerRecord
from .controller_helpers import ControlHelpers
from .mapped_memory import PrgDataMemory
from .runtime_services import RuntimeServices

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'

NMI_SCENE_TABLE = (0xFA97, 0xFA97, 0xF8B5, 0xF8FE, 0xF96A,
                   0xF9A0, 0xF9E4, 0xFA13, 0xFA53)
BATTLE_SCENE = 3
ATTACK_SCENE = 4
DUEL_SCENE = 5
ENDING_SCENE = 8


class UnresolvedScene(RuntimeError):
    """The original scene needs a controller not yet reconstructed here."""


@dataclass(frozen=True)
class BattleUnit:
    slot: int
    officer_id: int
    x: int
    y: int
    faction_and_flags: int
    hundred_troops_cache: int
    officer: OfficerRecord


def snapshot_memory(ram: bytes, sram: bytes) -> bytearray:
    """Import the two libretro memory regions without changing saved files."""
    if len(ram) != 0x800 or len(sram) != 0x2000:
        raise ValueError('Expected 2 KiB CPU RAM and 8 KiB SRAM')
    memory = bytearray(0x10000)
    for start in range(0, 0x2000, 0x800):
        memory[start:start+0x800] = ram
    memory[0x6000:0x8000] = sram
    return memory


class GameEngine:
    """A shared-memory front door to the readable recovered modules.

    Hooks are supplied explicitly to each controller. Other scenes can be
    connected via ``scene_hooks``. Missing helpers raise an explicit error.
    ``mapped=True`` enables read-only PRG data windows and independently
    recovered fixed services. Calls do not advance PPU or global scene setup.
    Readable gameplay APIs expose effects with their narrower stated contracts.
    """
    def __init__(self, memory=None, *, rom=None, data_window_bank=None, mapped=False,
                 battle_hooks=None, attack_hooks=None, duel_hooks=None, map_service_hooks=None,
                 domestic_hooks=None, ruler_turn_hooks=None,
                 global_hooks=None, ending_hooks=None, tactical_hooks=None,
                 service_io=None,
                 scene_hooks: dict[int, Callable] | None = None):
        self.rom = bytes(rom) if rom is not None else None
        if self.rom is not None and hashlib.sha256(self.rom).hexdigest() != ROM_SHA256:
            raise ValueError('ROM identity differs from the recovered program')
        if data_window_bank is not None and not 0<=data_window_bank<32:
            raise ValueError('data_window_bank is a physical PRG bank0..31')
        self.data_window_bank = data_window_bank
        if mapped and self.rom is None:
            raise ValueError('Mapped read-only data windows require this ROM')
        if service_io is not None:
            if not mapped:raise ValueError('Explicit presentation IO requires mapped=True')
            from .service_memory import ServiceMemory
            if isinstance(memory,PrgDataMemory):
                memory=ServiceMemory(self.rom,memory.ram,memory.sram,tuple(memory.banks),**service_io)
            else:
                memory=ServiceMemory(self.rom,None if memory is None else memory[:0x800],
                                     None if memory is None else memory[0x6000:0x8000],**service_io)
        if mapped and not isinstance(memory,PrgDataMemory):
            memory = PrgDataMemory(self.rom, None if memory is None else memory[:0x800],
                                   None if memory is None else memory[0x6000:0x8000])
        self.memory = bytearray(0x10000) if memory is None else memory
        if len(self.memory) != 0x10000:
            raise ValueError('Controllers share a 64 KiB CPU-addressed memory')
        self.services = {}
        def connect(scene, fallback):
            if not isinstance(self.memory,PrgDataMemory):return fallback
            service=RuntimeServices(fallback)
            self.services[scene]=service
            return service
        self.battle_hooks = connect(BATTLE_SCENE,battle_hooks)
        self.attack_hooks = connect(ATTACK_SCENE,attack_hooks)
        self.duel_hooks = ControlHelpers(connect(DUEL_SCENE,duel_hooks))
        self.map_service_hooks = connect('village',map_service_hooks)
        self.domestic_hooks = connect('domestic-global',domestic_hooks)
        self.ruler_turn_hooks = connect('ruler-turn',ruler_turn_hooks)
        self.ending_hooks = connect(ENDING_SCENE,ending_hooks)
        self.tactical_hooks = connect('tactical-global',tactical_hooks)
        self._global_user_hooks = global_hooks
        self.global_hooks = connect('global-main',self._global_source_call)
        self.scene_hooks = scene_hooks or {}
        self._battle = self._attack = self._duel = None
        self._duel_rules = self._postbattle_rules = self._postbattle_data = None
        self._map_service = None
        self._transfer_rules = self._troop_rules = self._domestic_control = self._ruler_turn_control = None
        self._terrain_semantics_data = None
        self._ownership_rules = self._faction_rules = self._global = self._ending = None
        self._tactical_control = self._tactical_rules = self._tactical_bridge = None
        self._tactical_strategy = self._tactical_effects = None
        self._player_tactic_targeting = None
        self._presentation = None
        self._scene_coordinator = None

    @classmethod
    def from_snapshot(cls, prefix: str | Path, **kwargs):
        prefix = Path(prefix)
        ram = Path(str(prefix)+'-ram.bin').read_bytes()
        sram = Path(str(prefix)+'-sram.bin').read_bytes()
        return cls(snapshot_memory(ram, sram), **kwargs)

    @property
    def scene(self):
        return self.memory[0x78] & 0x0F

    def officer(self, officer_id: int) -> OfficerRecord:
        if not 0 <= officer_id < 237:
            raise ValueError('Valid officer IDs are 0..236')
        address = 0x63C0 + 12*officer_id
        return OfficerRecord(bytes(self.memory[address:address+12]))

    def city(self,city_id):
        """Confirmed32-byte city fields, preserving raw/display/income views."""
        from .domestic_ai import CityRecord
        return CityRecord.from_memory(self.memory,city_id)

    def city_auxiliary_fields(self,city_id):
        """Evidence-bound auxiliary bytes, including unresolved boundary aliases."""
        from .record_fields import CityAuxiliaryFields
        return CityAuxiliaryFields.from_memory(self.memory,city_id)

    def postbattle_loyalty_rules(self):
        """Exact A009/CF7C caller owner; retain it for any pending operation."""
        from .postbattle_loyalty_bridge import PostbattleLoyaltyBridge
        return PostbattleLoyaltyBridge(self.memory,self._require_rom(),self.readable_scene_rules())

    def postbattle_graphics_rules(self):
        """Exact year/month packet owner; upload remains a separate consumer."""
        from .postbattle_graphics import PostbattleGraphics
        return PostbattleGraphics(self.memory,self._require_rom(),self.readable_scene_rules())

    def battle_succession_rules(self):
        """Real city13 player/AI succession; caller owns registers and waits."""
        from .battle_succession import BattleSuccession
        return BattleSuccession(self.memory,self._require_rom(),self.readable_scene_rules())

    def city_unresolved_fields(self,city_id):
        """Raw byte1/tail with the original overlapping assignment word."""
        from .field_semantics import CityUnresolvedFields
        return CityUnresolvedFields.from_memory(self.memory,city_id)

    def affinity_field_services(self):
        """Explicit affinity consumers; partial B64D keeps its prefix boundary."""
        from .field_semantics import AffinityFieldServices
        return AffinityFieldServices(self.memory,self._require_rom(),self.readable_scene_rules())

    def transfer_rules(self):
        """Roster membership, loyalty and succession; no implicit host ack."""
        from .officer_transfer import OfficerTransfer,TransferData
        if self._transfer_rules is None:
            self._transfer_rules=OfficerTransfer(self.memory,TransferData.from_rom(self._require_rom()))
        return self._transfer_rules

    def troop_rules(self):
        """Word writers with path-specific preservation/clearing/overflow."""
        from .troop_fields import TroopFieldRules
        if self._troop_rules is None:self._troop_rules=TroopFieldRules(self.memory)
        return self._troop_rules

    def presentation_rules(self):
        """Real graphics/text/audio/NMI/IRQ software services on explicit IO.

        Give service_io to from_snapshot(...mapped=True), or supply a
        ServiceMemory yourself. Status reads and buttons are actual host
        inputs; no helper fabricates a completed job or an interrupt edge.
        """
        from .battle_presentation_services import BattlePresentationServices
        if self._presentation is None:self._presentation=BattlePresentationServices(self)
        return self._presentation

    def tick_nmi_services(self,registers=None,*,hardware_entry=False,external_callback=None):
        return self.presentation_rules().run_nmi(registers,hardware_entry=hardware_entry,
                                               external_callback=external_callback)

    def tick_irq_services(self,registers=None,*,hardware_entry=False):
        return self.presentation_rules().run_irq(registers,hardware_entry=hardware_entry)

    def readable_scene_rules(self):
        """Independent named controllers/setup on the explicit service bus.

        Legacy control-IR APIs retain their historical evidence contracts.
        These new calls use actual caller registers, pending service owners and
        source bodies; they do not synthesize a hardware frame or input edge.
        """
        from .scene_coordinator import SceneCoordinator
        if self._scene_coordinator is None:self._scene_coordinator=SceneCoordinator(self)
        return self._scene_coordinator

    def tick_readable_scene(self,registers,*,scene=None):
        return self.readable_scene_rules().tick(registers,scene=scene)

    def resume_readable_scene(self,*,scene=None):
        return self.readable_scene_rules().resume(scene=scene)

    def initialize_readable_scene(self,entry,registers=None):
        return self.readable_scene_rules().run_setup(entry,registers)

    def tick_readable_nmi(self,registers=None,*,hardware_entry=False):
        return self.readable_scene_rules().run_nmi(registers,hardware_entry=hardware_entry)

    def resume_readable_nmi(self):
        return self.readable_scene_rules().resume_nmi()

    def tick_readable_irq(self,registers=None,*,hardware_entry=False):
        return self.readable_scene_rules().run_irq(registers,hardware_entry=hardware_entry)

    def resume_readable_irq(self):
        return self.readable_scene_rules().resume_irq()

    def readable_campaign(self,registers):
        """Explicit main/NMI/IRQ event continuations with one real context."""
        from .campaign_session import CampaignSession
        return CampaignSession(self,registers)

    def tick_readable_main(self,registers,*,entry=0xE066):
        """One named fixed-bank main update, ending at its real E066 boundary."""
        return self.readable_scene_rules().run_main(entry,registers)

    def resume_readable_main(self):
        return self.readable_scene_rules().resume_main()

    def initialize_readable_boot(self,registers):
        """Original E000 software reset through its nonreturning E066 handoff."""
        return self.readable_scene_rules().run_boot(registers)

    def resume_readable_boot(self):
        return self.readable_scene_rules().resume_boot()

    def city_ownership_rules(self):
        """Independent capture, colonization, withdrawal and actual transfer effects."""
        from .city_ownership import CityOwnership,OwnershipData
        if self._ownership_rules is None:
            self._ownership_rules=CityOwnership(self.memory,OwnershipData.from_rom(self._require_rom()))
        return self._ownership_rules

    def faction_rules(self):
        """Independent ruler retirement, loss/30-city victory and ending effects."""
        from .faction_lifecycle import FactionLifecycle,FactionTables
        if self._faction_rules is None:
            self._faction_rules=FactionLifecycle(self.memory,FactionTables.from_rom(self._require_rom()))
        return self._faction_rules

    def _domestic_machine(self):
        from .domestic_ai import DomesticAIControl
        if self._domestic_control is None:
            self._domestic_control=DomesticAIControl(self.memory,hooks=self.domestic_hooks)
        return self._domestic_control

    def _ending_machine(self):
        from .faction_lifecycle import EndingControl
        if self._ending is None:self._ending=EndingControl(self.memory,hooks=self.ending_hooks)
        return self._ending

    def _tactical_machine(self):
        from .tactical_ai_control import TacticalAIControl
        if self._tactical_control is None:
            self._tactical_control=TacticalAIControl(self.memory,hooks=self.tactical_hooks)
        return self._tactical_control

    def tactical_rules(self):
        """Readable actor scan, movement proposal and secondary game effects."""
        from .tactical_decisions import TacticalDecisions,TacticalData
        if self._tactical_rules is None:
            self._tactical_rules=TacticalDecisions(self.memory,TacticalData.from_rom(self._require_rom()))
        return self._tactical_rules

    def tactical_bridge_rules(self):
        """Proposal-consumer memory prefixes/suffixes; real graphics external."""
        from .tactical_exchange import TacticalBattleBridge,TacticalExchangeData
        if self._tactical_bridge is None:
            self._tactical_bridge=TacticalBattleBridge(self.memory,TacticalExchangeData.from_rom(self._require_rom()))
        return self._tactical_bridge

    def tactical_strategy_rules(self):
        """All eight readable strategy bodies and cooperative proposal scan.

        This semantic API shares game memory, but does not borrow the CPU
        controller's registers, stack or mapper writes. A ROM map descriptor
        needs the caller's current physical data bank; mapped memory supplies
        its current bank automatically.
        """
        from .tactical_strategy_ai import TacticalStrategyAI,StrategyData
        if self._tactical_strategy is None:
            self._tactical_strategy=TacticalStrategyAI(
                self.memory,StrategyData.from_rom(self._require_rom()),
                data_window_bank=None if isinstance(self.memory,PrgDataMemory) else self.data_window_bank)
        return self._tactical_strategy

    def tactical_effect_rules(self):
        """All sixteen readable tactic bodies and settlement memory effects.

        Each after_* method requires its documented real graphics/audio/input
        prelude. It never completes those services on the caller's behalf.
        A lethal HP effect retains an explicit death-map refresh continuation.
        """
        from .tactical_effects_complete import CompleteTacticalEffects,CompleteEffectData
        if self._tactical_effects is None:
            self._tactical_effects=CompleteTacticalEffects(self.memory,CompleteEffectData.from_rom(self._require_rom()))
        return self._tactical_effects

    def player_tactic_targeting_rules(self):
        """Original player qualification, separately from AI and probability.

        eligible() uses the already selected actor/target. can_target() also
        describes the cursor's enemy/range check. These rules neither debit
        AP nor cast an effect or complete the UI; original player and AI
        terrain predicates intentionally differ for some tactic IDs.
        """
        from .player_tactic_targeting import PlayerTacticTargeting,TargetingData
        if self._player_tactic_targeting is None:
            self._player_tactic_targeting=PlayerTacticTargeting(
                self.memory,TargetingData.from_rom(self._require_rom()),
                data_window_bank=None if isinstance(self.memory,PrgDataMemory) else self.data_window_bank)
        return self._player_tactic_targeting

    def commit_tactical_retreat(self):
        """BC2A..BC92 game-data commit after the real retreat selection.

        The caller supplies the original selected slot0509 and destination
        city050B. Account for its signed side and low10 troop total before
        moving the roster and clearing battlefield/cache references. Text,
        confirmation and rendering preceding this commit remain caller-owned.
        """
        slot=self.memory[0x509];city=self.memory[0x50B]
        if not 0<=slot<20 or not 0<=city<30:
            raise ValueError('Retreat commit requires selected slot0..19 and city0..29')
        accounting=self.tactical_effect_rules().detach_unit_accounting()
        commit=self.city_ownership_rules().retreat_unit_to_city(slot,city)
        commit['preceding_C91E_helper_external']=False
        return {'status':'returned','accounting':accounting,'commit':commit,
                'graphics_or_confirmation_completed':False}

    def _global_source_call(self,context,target,return_pc,kind):
        """Borrow a recovered banked callee with the actual caller stack/registers.

        Address A000 alone is not an identity: physical8/9 and10/11 A000,
        and physical23/24 A01E have separate proven source bridges. No original
        ROM instructions execute, and no graphics/NMI completion is assumed.
        """
        from .controller_helpers import MissingSharedHelper
        if isinstance(self.memory,PrgDataMemory) and return_pc is not None:
            pair=tuple(self.memory.banks[1:3])
            routes={(10,11,0xA000):(0xA00F,self._domestic_machine,b'\x4c\x0f\xa0'),
                    (8,9,0xA000):(0xA02D,self._tactical_machine,b'\x4c\x2d\xa0'),
                    (23,24,0xA01E):(0xD693,self._ending_machine,b'\x4c\x93\xd6')}
            route=routes.get((*pair,target))
            if route is not None:
                entry,factory,trampoline=route
                offset=16+pair[0]*8192+target-0xA000
                if self._require_rom()[offset:offset+3]!=trampoline:
                    raise ValueError('Recovered banked trampoline identity differs')
                controller=factory()
                # The original trampoline is a flag-preserving JMP. Its
                # instruction effects are the explicit new callee entry PC.
                return controller.run_entry(entry,max_instructions=200000,
                        registers=context.registers,seed_return=False,return_pc=return_pc)
        if self._global_user_hooks is not None:
            return self._global_user_hooks(context,target,return_pc,kind)
        raise MissingSharedHelper(f'Unrecovered global {kind} at ${target:04X}; actual banks {getattr(self.memory,"banks",None)}')

    def _global_context(self,entry_banks):
        from .global_main_loop import GlobalMainLoop
        self._require_rom()
        if not isinstance(self.memory,PrgDataMemory):raise UnresolvedScene('Global control requires mapped=True')
        banks=tuple(entry_banks)
        if len(banks)!=4 or banks[3]!=31 or any(not isinstance(b,int) or not 0<=b<32 for b in banks):
            raise ValueError('Provide four actual physical PRG banks, with fixed bank31')
        self.memory.banks[:]=banks
        if self._global is None:self._global=GlobalMainLoop(self.memory,hooks=self.global_hooks)
        return self._global

    def tick_global(self,*,entry_banks,**kwargs):
        """One real main-loop dispatch through the next E066 boundary.

        entry_banks is the caller's explicit physical four-window mapping;
        supplying it prepares a fixture context, not a mapper instruction.
        Global code itself updates main-thread DE/DF/E0 shadows. Other scene
        and NMI graphics, audio, IRQ and timing remain explicit dependencies.
        """
        return self._global_context(entry_banks).step(**kwargs)

    def tick_nmi_cooperation(self,*,entry_banks,**kwargs):
        """F862 callback window to F88D, after a caller-owned real NMI prelude.

        No hardware interrupt stack, DMA or completed rendering is fabricated.
        Initial mapping and registers are explicit; main-bank restoration is a
        separate suffix and is never invoked automatically after a dependency.
        """
        return self._global_context(entry_banks).nmi_step(**kwargs)

    def nmi_bookkeeping_effects(self):
        """Independent F88D..F8AF restoration/counters; excludes saved pops/RTI."""
        from .global_main_loop import finish_nmi_bookkeeping
        self._require_rom()
        if not isinstance(self.memory,PrgDataMemory):raise UnresolvedScene('Mapper restoration requires mapped=True')
        return finish_nmi_bookkeeping(self.memory)

    def cancel_scene_working_state(self):
        """Original RAM/OAM cancellation suffix; excludes hardware reset prelude."""
        from .global_main_loop import reset_scene_working_state
        return reset_scene_working_state(self.memory)

    def tick_ending(self,**kwargs):
        """Direct D693 ending controller update, excluding full NMI preparation."""
        self._map_global_controller(23)
        return self._ending_machine().step(**kwargs)

    def tick_tactical_ai(self,**kwargs):
        """Direct bank8 A02D decision update, separate from NMI battle actions.

        Uses caller-supplied data_window_bank and current6F8B request/scan
        fields. It returns a proposal or secondary effects; the existing
        battlefield controller consumes the proposal on its own schedule.
        It does not advance a video frame or invent action/renderer completion.
        """
        self._map_global_controller(8)
        return self._tactical_machine().step(**kwargs)

    def tick_tactical_strategy(self,**kwargs):
        """Readable A02D game-data update; produces a proposal, no video frame.

        tick_global/tick_tactical_ai retain the independent CPU-contract model
        for exact caller registers/stack. This method executes the full strategy
        rules directly, without IR or original ROM instruction execution.
        """
        return self.tactical_strategy_rules().step(**kwargs)

    def domestic_development(self):
        """One independent development decision/effect, with exact RNG cursors."""
        from .domestic_ai import domestic_development_once
        return domestic_development_once(self.memory,self._require_rom())

    def choose_domestic_attack(self,ruler):
        from .domestic_ai import choose_attack_target
        return choose_attack_target(self.memory,self._require_rom(),ruler)

    def _map_global_controller(self,pair):
        self._require_rom()
        if not isinstance(self.memory,PrgDataMemory):raise UnresolvedScene('Use mapped=True for banked global controllers')
        if self.data_window_bank is None:raise UnresolvedScene('Supply the actual controller-entry data_window_bank explicitly')
        self.memory.activate_scene(pair,self.data_window_bank)

    def tick_domestic_ai(self,**kwargs):
        """Direct pair10/11 A00F global-AI update, separate from NMI city UI.

        Entry-bank mapping is explicit. This does not run fixedE17D preparation,
        NMI78=2 city UI, display barriers or caller-owned register setup.
        Mapping does not synchronize E1/E2/E3 bank caches or OAM7C. Hooks
        that consume them require matching explicit caller-entry context.
        """
        self._map_global_controller(10)
        return self._domestic_machine().step(**kwargs)

    def tick_ruler_turn(self,controller,**kwargs):
        """Direct pair25/26 calendar, turnevents or rulerAI-scene update.

        As with domesticAI, mapping does not prepare E1/E2/E3 bank caches,
        OAM7C, renderer objects or the original global caller prelude.
        """
        from .domestic_ai import RulerTurnControl
        self._map_global_controller(25)
        if self._ruler_turn_control is None:self._ruler_turn_control=RulerTurnControl(self.memory,hooks=self.ruler_turn_hooks)
        return self._ruler_turn_control.tick(controller,**kwargs)

    def ai_movement_quote(self,slot,x,y):
        """AI uses the real repeated-byte8 selector, unlike player cache063C."""
        from .terrain_rules import city_chunks,map_cell
        from .terrain_semantics import TerrainSemanticsData,ai_movement_quote
        if not 0<=slot<20:raise ValueError('Battle slots0..19')
        m=self.memory;officer=m[0x664+slot]
        if officer==255:raise ValueError('Empty battle slot')
        rom=self._require_rom();cell=map_cell(rom,city_chunks(rom,m[0x50E]),x,y)
        if not cell['legal_cell']:raise ValueError('AI movement quote requires a playable cell')
        if self._terrain_semantics_data is None:self._terrain_semantics_data=TerrainSemanticsData.from_rom(rom)
        return {**ai_movement_quote(cell['ai_class'],m[0x63C0+12*officer+11],
                                   m[0x63C0+12*officer+8],m[0x650+slot],data=self._terrain_semantics_data),
                'cell':cell}

    def battle_units(self):
        result = []
        for slot in range(20):
            officer_id = self.memory[0x664+slot]
            if officer_id == 255:
                continue
            result.append(BattleUnit(slot, officer_id, self.memory[0x600+slot],
                          self.memory[0x614+slot], self.memory[0x628+slot],
                          self.memory[0x63C+slot], self.officer(officer_id)))
        return result

    def _require_rom(self):
        if self.rom is None:raise UnresolvedScene('This gameplay API needs pinned read-only ROM tables')
        return self.rom

    def prepare_scene_callback(self):
        """Apply verified callback-entry bank/OAM preconditions explicitly.

        This is not an NMI, does not advance queued display work, and must not
        be used to claim a complete frame. Data bank is caller-supplied.
        """
        if not isinstance(self.memory,PrgDataMemory):raise UnresolvedScene('Use mapped=True for callback preparation')
        if self.data_window_bank is None:raise UnresolvedScene('Supply data_window_bank explicitly')
        if self.scene not in (BATTLE_SCENE,ATTACK_SCENE,DUEL_SCENE,ENDING_SCENE):raise UnresolvedScene('Only the four recovered callbacks are supported')
        pair={BATTLE_SCENE:12,ATTACK_SCENE:14,DUEL_SCENE:23,ENDING_SCENE:23}[self.scene]
        self.memory.prepare_callback(pair,self.data_window_bank)

    def duel_rules(self):
        """Independent AI, strike, retreat, surrender and reward game effects."""
        from .duel_logic import DuelLogic,DuelTables
        if self._duel_rules is None:self._duel_rules=DuelLogic(self.memory,DuelTables.from_rom(self._require_rom()))
        return self._duel_rules

    def postbattle_rules(self):
        """Main13/14 semantic controller with explicit UI readiness/cursors."""
        from .postbattle import PostbattleData,PostbattleEngine
        if self._postbattle_data is None:self._postbattle_data=PostbattleData.from_rom(self._require_rom())
        if self._postbattle_rules is None:self._postbattle_rules=PostbattleEngine(self.memory,data=self._postbattle_data)
        return self._postbattle_rules

    def process_ai_officers(self,mode):
        """Independent BC46 allocation; does not set rostered status bits."""
        from .postbattle import process_ai_officers
        self.postbattle_rules()
        return process_ai_officers(self.memory,mode,data=self._postbattle_data)

    def settlement_rules(self,*,render_barrier=None):
        """Main15 game effects, including independently recovered allocation.

        Stage2 still requires a real caller-provided display barrier. RNG data
        and all allocation writes use the recovered source; no ROM code runs.
        """
        from .battle_state_machine import finalization_phase
        self.postbattle_rules();data=self._postbattle_data
        return finalization_phase(self.memory,data.adjacency,
                    rng_draw=lambda:data.rng_byte(self.memory),
                    ai_officer_processing=lambda memory,mode:self.process_ai_officers(mode),
                    render_barrier=render_barrier)

    def movement_quote(self,slot,x,y):
        from .terrain_rules import city_chunks,movement_quote
        if not 0<=slot<20:raise ValueError('Battle slots0..19')
        m=self.memory;officer_id=m[0x664+slot]
        if officer_id==255:raise ValueError('Empty battle slot')
        rom=self._require_rom()
        return movement_quote(rom,city_chunks(rom,m[0x50E]),x,y,
                              m[0x63C0+12*officer_id+11],m[0x63C+slot],m[0x650+slot])

    def enter_map_service(self,renderer_hook=None):
        from .terrain_rules import enter_map_service
        return enter_map_service(self.memory,self._require_rom(),renderer_hook)

    def tick_map_service(self,**kwargs):
        """One direct C0BB service update for battle9/sub0..9.

        Maps pair8/9 read-only data explicitly. This direct-entry API excludes
        the parent's EE07 far-call/return protocol and its NMI preparation;
        missing graphics/text/political dependencies remain errors.
        """
        from .map_service_machine import MapServiceMachine
        if not isinstance(self.memory,PrgDataMemory):raise UnresolvedScene('Use mapped=True for the village controller')
        if self.data_window_bank is None:raise UnresolvedScene('Supply data_window_bank explicitly')
        if self.memory[0x500]!=9:raise UnresolvedScene('Village controller requires battle main9')
        self.memory.activate_scene(8,self.data_window_bank)
        if self._map_service is None:self._map_service=MapServiceMachine(self.memory,hooks=self.map_service_hooks)
        return self._map_service.step(**kwargs)

    def control_state(self):
        m = self.memory
        return {'global_main_state':m[0x7A], 'nmi_scene':self.scene,
                'battle_state':m[0x500], 'battle_substate':m[0x501],
                'attack_state':m[0x540], 'attack_substate':m[0x541],
                'attack_officers':list(m[0x560:0x562]),
                'attack_control_flags':list(m[0x562:0x564]),
                'duel_state':m[0x4A8], 'duel_substate':m[0x4A9],
                'battle_slot_050a':m[0x50A], 'battle_slot_0509':m[0x509],
                'duel_actor':m[0x4AA], 'duel_officers':list(m[0x4AD:0x4AF]),
                'duel_health':list(m[0x4B1:0x4B3]),
                'ruler_turn_main_0400':m[0x400],'ruler_turn_sub_0401':m[0x401],
                'ai_phase_6f5b':m[0x6F5B],'ai_event_6f8b':m[0x6F8B],
                'ending_mode_0541':m[0x541],'ending_sub_0542':m[0x542],
                'tactical_actor_6f8c':m[0x6F8C],'tactical_action_6f8d':m[0x6F8D],
                'tactical_target_6f8e':m[0x6F8E],'tactical_result_6f8f':m[0x6F8F],
                'tactical_rng_6f92':m[0x6F92],'tactical_scan_6f94':m[0x6F94],
                'tactical_no_action_6f95':m[0x6F95],'tactical_attempted_6f96':m[0x6F96],
                'tactical_move_cost_6f97':m[0x6F97]}

    def tick_scene(self):
        """Execute one recovered scene-controller call, not one video frame."""
        if self.scene in (BATTLE_SCENE, ATTACK_SCENE, DUEL_SCENE, ENDING_SCENE):
            if self.rom is None:
                raise UnresolvedScene('Controller table reads require the original read-only ROM data')
            if self.data_window_bank is None:
                raise UnresolvedScene('Supply the controller-entry $8000 data_window_bank explicitly; RAM $DE is the NMI restore bank')
            pair = {BATTLE_SCENE:12,ATTACK_SCENE:14,DUEL_SCENE:23,ENDING_SCENE:23}[self.scene]
            # Mapper windows used when the NMI enters this scene. External
            # bank-changing dependencies must be implemented by a hook.
            if isinstance(self.memory,PrgDataMemory):
                self.memory.activate_scene(pair,self.data_window_bank)
            else:
                for start, bank in ((0x8000,self.data_window_bank),
                                    (0xA000,pair),(0xC000,pair+1),(0xE000,31)):
                    offset = 16+8192*bank
                    self.memory[start:start+8192] = self.rom[offset:offset+8192]
        if self.scene == BATTLE_SCENE:
            from .battle_state_machine import BattleStateMachine
            if self._battle is None:
                self._battle = BattleStateMachine(self.memory, hooks=self.battle_hooks)
            return self._battle.step()
        if self.scene == DUEL_SCENE:
            from .duel_state_machine import DuelMachine
            if self._duel is None:
                self._duel = DuelMachine(self.memory, hooks=self.duel_hooks)
            return self._duel.tick()
        if self.scene == ATTACK_SCENE:
            from .attack_state_machine import AttackStateMachine
            if self._attack is None:
                self._attack = AttackStateMachine(self.memory, hooks=self.attack_hooks)
            return self._attack.step()
        if self.scene == ENDING_SCENE:
            return self._ending_machine().step()
        if self.scene in self.scene_hooks:
            return self.scene_hooks[self.scene](self)
        target = NMI_SCENE_TABLE[self.scene] if self.scene < len(NMI_SCENE_TABLE) else None
        raise UnresolvedScene(f'NMI scene {self.scene}, target {target}, requires an explicit controller')
