"""Explicit host events on one frozen readable campaign session.

This module adds ownership checks and an event journal, not another gameplay
implementation.  One game, coordinator, memory, register object and campaign
session survive all main/NMI/IRQ operations.  Neither this module nor the
campaign session schedules video, advances a CPU, loads a later snapshot,
completes a queue, writes a fade acknowledgement or repairs a caller PC/SP.
"""
from .campaign_session import CampaignSession


class PostbattleContinuity:
    """Keep explicit UI/software events on one caller-owned context.

    The host supplies interrupt arrivals and controller bytes.  A main event
    requires the actual E066 boundary.  A resumed operation retains the
    original CampaignSession pending phase and its original source owner.
    Interrupt entry/RTI, real calls and reset retirement remain the frozen
    source implementations' responsibility.
    """

    def __init__(self, game, registers):
        self.game = game
        self.memory = game.memory
        self.registers = registers
        self.coordinator = game.readable_scene_rules()
        if self.coordinator.external_callback is not None:
            raise ValueError('Continuity requires source owners without an external fallback')
        self.session = CampaignSession(game, registers)
        self.journal = []
        self._identity = (game, self.memory, registers, self.coordinator, self.session)
        self._global_ui = self.coordinator.global_ui
        self._global_ui_epoch = self.coordinator.reset_epoch
        # Keep strong references while reporting identities.  Monotone serials
        # cannot accidentally equate two different objects after Python id reuse.
        self._references = {}

    def _reference(self, obj):
        key = id(obj)
        if key not in self._references:
            self._references[key] = (obj, len(self._references)+1)
        original, serial = self._references[key]
        if original is not obj:
            raise RuntimeError('A source ownership identity was reused')
        return serial

    def _check_identity(self):
        actual = (self.game, self.game.memory, self.registers,
                  self.game.readable_scene_rules(), self.session)
        if any(a is not b for a, b in zip(actual, self._identity)):
            raise RuntimeError('Do not replace a live continuity game, bus, registers or session')
        if self.session.registers is not self.registers or self.session.memory is not self.memory:
            raise RuntimeError('The retained campaign context changed')
        if self.coordinator.external_callback is not None:
            raise RuntimeError('An external source fallback was installed after entry')
        if self.coordinator.reset_epoch != self._global_ui_epoch:
            if self.coordinator.reset_epoch < self._global_ui_epoch:
                raise RuntimeError('The source reset epoch moved backwards')
            self._global_ui = self.coordinator.global_ui
            self._global_ui_epoch = self.coordinator.reset_epoch
        elif self.coordinator.global_ui is not self._global_ui:
            raise RuntimeError('The live global UI owner changed without a real reset')

    def set_buttons(self, first, second=0):
        """Supply physical-controller inputs, without writing controller RAM.

        The ordinary E6C6 software reader creates new/held button fields.
        Existing serial-controller index/strobe state is deliberately retained.
        """
        self._check_identity()
        if any(type(v) is not int or not 0 <= v < 256 for v in (first, second)):
            raise ValueError('Supply two integer physical-controller bytes')
        self.memory.controller_buttons = (first, second)

    def ownership(self):
        """Inspection only: identify live phases and their existing programs."""
        self._check_identity()
        self.session._sync_reset()
        phases = []
        for phase in self.session.pending:
            owner = (self.coordinator.global_ui if phase.kind == 'main' else
                     self.session._interrupt_owners[phase.token])
            phases.append(dict(kind=phase.kind, phase_identity=self._reference(phase),
                               owner_identity=self._reference(owner),
                               generator_identity=self._reference(owner._program),
                               token=phase.token, wait_pc=phase.wait_pc,
                               wait_sp=phase.wait_sp))
        return dict(game_identity=self._reference(self.game), memory_identity=self._reference(self.memory),
                    registers_identity=self._reference(self.registers),
                    coordinator_identity=self._reference(self.coordinator),
                    session_identity=self._reference(self.session),
                    global_UI_identity=self._reference(self.coordinator.global_ui),
                    reset_epoch=self.coordinator.reset_epoch, phases=phases)

    def advance(self, operation, *, label=None):
        """Execute exactly one declared software operation; never auto-resume.

        ``dependency`` is an honest suspension.  A host may explicitly deliver
        an interrupt, supply a missing port input, or restore a real source
        service before requesting ``resume``.  This layer does none of those
        actions on the host's behalf.  A fake returned service without actual
        caller PC/SP completion remains a dependency in the underlying owner.
        """
        self._check_identity()
        if operation not in ('main', 'nmi', 'irq', 'resume'):
            raise ValueError('Explicit operation must be main, nmi, irq or resume')
        before = self.ownership()
        result = getattr(self.session, operation)()
        self._check_identity()
        if result['status'] not in ('returned', 'dependency', 'waiting', 'budget',
                                    'reset_boundary'):
            raise RuntimeError('Unrecognized campaign boundary; original context retained')
        after = self.ownership()
        row = dict(sequence=len(self.journal), operation=operation, label=label,
                   status=result['status'], before=before, after=after,
                   registers={k:getattr(self.registers, k)
                              for k in ('a', 'x', 'y', 'p', 'sp', 'pc')})
        self.journal.append(row)
        return result

    def main(self, *, label=None):
        return self.advance('main', label=label)

    def nmi(self, *, label=None):
        return self.advance('nmi', label=label)

    def irq(self, *, label=None):
        return self.advance('irq', label=label)

    def resume(self, *, label=None):
        return self.advance('resume', label=label)

    def state(self):
        self._check_identity()
        return dict(campaign=self.session.state(), ownership=self.ownership(),
                    declared_operations=len(self.journal),
                    controller_buttons=self.memory.controller_buttons)
