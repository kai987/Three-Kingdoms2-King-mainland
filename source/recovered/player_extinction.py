"""Player extinction and mode-zero ending, as direct readable rules.

The frozen postbattle and ending controllers supply the already recovered
surrounding display, selection and dispatch procedures. These overrides run
inside their original local JSR frames. They neither interpret control IR nor
execute ROM instructions, create interrupts, or acknowledge unfinished text.
"""
from .battle_succession import (
    BattleSuccession, SuccessionRegisters, SuccessionBlockBudget,
    AFFECTED_RULER, POSTBATTLE_PHASE, SUCCESSION_PHASE, NO_SUCCESSOR_PHASE,
    NOTICE_TIMER, RETURN_MAIN, RETURN_MAIN_PHASE, CITY_MAIN, NEW_BUTTONS,
    GLOBAL, C, Z, N,
)
from .global_ui_controller import EndingUIController

OTHER_RULER_DURING_RETIREMENT = 0x40C
OPENING_PLAYER_MODE = 0x6F43
LOSS_MODE, LOSS_ANIMATION, LOSS_MARKER = 0x541, 0x4CA, 0x4CB
TEXT_JOBS = (0x300, 0x304)


class PlayerExtinction(BattleSuccession):
    """Exact A00C/AD81 parent, with named player-extinction core rules.

    Local BE2E/C386/C3C2/C41E keep all registers, scratch, SRAM, original
    caller stack and port effects. No new broad routing of local entry points
    is necessary: the original parent calls these overridden methods itself.
    """

    def candidate_city_report(self, ruler=None):
        """Read-only explanation of BE2E; not an execution/eligibility patch.

        The first roster slot alone establishes a candidate city. In
        particular, a hole at slot zero hides later officers, and a dead
        officer at slot zero qualifies. This report deliberately never reads
        officer HP, condition, location or family records.
        """
        m = self.memory
        if ruler is None:
            ruler = m[AFFECTED_RULER]
        if not isinstance(ruler, int) or not 0 <= ruler < 7:
            raise ValueError('Typed ruler index must be 0..6')
        owned = []
        candidates = []
        for city in range(30):
            base = 0x6000 + 32 * city
            if m[base] & 7 == ruler:
                owned.append(city)
                if m[base + 17] != 255:
                    candidates.append(city)
        return dict(ruler=ruler, owned_cities=owned, candidate_cities=candidates,
                    no_candidate_city=not candidates, first_candidate=candidates[0] if candidates else None,
                    predicate='owner low3 equals ruler AND roster[0] != FF',
                    record_HP_status_location_checked=False)

    def fields(self):
        fields = super().fields()
        fields.update(opening_player_mode=self.memory[OPENING_PLAYER_MODE],
                      other_ruler_during_retirement=self.memory[OTHER_RULER_DURING_RETIREMENT],
                      loss_mode=self.memory[LOSS_MODE])
        return fields

    def check_player_candidate_cities(self):
        """25 BE2E..BE82: wait for text and A/B, then scan city heads.

        A failed scan changes the postbattle phase to its saved no-candidate
        phase. It does not immediately delete a ruler or start the ending.
        """
        r, m = self.registers, self.memory
        yield from self._checkpoint(0xBE2E)
        self._a(m[0x300]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        self._a(m[0x304]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        if not (yield from self._local_call(self.draw_current_city_focus, 0xBE3C, 0xBE3F)):
            return
        self._a(m[NEW_BUTTONS]); self._a(r.a & 3)
        if not r.p & Z:
            self._x(0)
            while True:
                yield from self._checkpoint(0xBE48)
                self._a(r.x)
                yield from self._external(0xBE49, 0xF2AF, 0xBE4C, 'call')
                if r.pc != 0xBE4C:
                    return
                self._y(0); self._a(m[m[0] | m[1] << 8]); self._a(r.a & 7)
                self._compare(r.a, m[AFFECTED_RULER])
                if r.p & Z:
                    self._y(17); self._a(m[((m[0] | m[1] << 8) + r.y) & 65535])
                    self._compare(r.a, 255)
                    if not r.p & Z:
                        m[SUCCESSION_PHASE] = self._nz(m[SUCCESSION_PHASE] + 1)
                        self._a(128); m[0x6F3F] = r.a
                        self._a(65); m[0x6F41] = r.a
                        self._a(208)
                        yield from self._external(0xBE7F, 0xF28B, None, 'tail')
                        return
                self._x(r.x + 1); self._compare(r.x, 30)
                if r.p & C:
                    self._a(m[NO_SUCCESSOR_PHASE]); m[POSTBATTLE_PHASE] = r.a
                    self._a(0); m[SUCCESSION_PHASE] = r.a
                    self._rts(); return
        self._rts()

    def commit_leader_absence(self):
        """26 C386..C3BA: leader-only FF, then human or AI notice.

        This controller low2 test differs from the whole-byte controller==3
        test in the earlier ADAA/AE0D routing. No cities, rosters, residence,
        controller, diplomacy or officer bytes are cleared by this body.
        """
        r, m = self.registers, self.memory
        yield from self._checkpoint(0xC386)
        self._y(m[AFFECTED_RULER]); self._a(m[(0xC3BB + r.y) & 65535]); m[0x42D] = r.a
        self._a(195)
        yield from self._external(0xC391, 0xF28B, 0xC394, 'call')
        if r.pc != 0xC394:
            return
        self._a(m[AFFECTED_RULER])
        yield from self._external(0xC397, 0xF368, 0xC39A, 'call')
        if r.pc != 0xC39A:
            return
        self._y(0); self._a(m[m[0] | m[1] << 8]); m[0x42C] = r.a
        self._a(255); m[m[0] | m[1] << 8] = r.a
        self._y(3); self._a(m[((m[0] | m[1] << 8) + r.y) & 65535])
        self._a(r.a & 3); self._compare(r.a, 3)
        if r.p & Z:
            m[SUCCESSION_PHASE] = self._nz(m[SUCCESSION_PHASE] + 1)
            self._a(0); m[NOTICE_TIMER] = r.a
        m[SUCCESSION_PHASE] = self._nz(m[SUCCESSION_PHASE] + 1)
        self._rts()

    def await_player_gameover(self):
        """26 C3C2..C41D: text/A-or-B gate, loss payload, global13.

        Here 040C denotes the other ruler, not the selected successor city
        used by earlier player-selection phases. FF selects message D9 later;
        a valid other-ruler index supplies its leader for message D8.
        """
        r, m = self.registers, self.memory
        yield from self._checkpoint(0xC3C2)
        self._a(m[0x300]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        self._a(m[0x304]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        if not (yield from self._local_call(self.draw_current_city_focus, 0xC3D0, 0xC3D3)):
            return
        self._a(m[NEW_BUTTONS]); self._a(r.a & 3)
        if r.p & Z:
            self._rts(); return
        self._a(m[OTHER_RULER_DURING_RETIREMENT]); self._compare(r.a, 255)
        if not r.p & Z:
            yield from self._external(0xC3E2, 0xF368, 0xC3E5, 'call')
            if r.pc != 0xC3E5:
                return
            self._y(0); self._a(m[m[0] | m[1] << 8])
        m[0x42E] = r.a
        self._a(m[0x6F00]); self._flag(C, False); self._add(100); m[0x42F] = r.a
        self._a(0); self._add(0); m[0x430] = r.a
        self._a(m[0x6F01]); self._flag(C, False); self._add(1); m[0x432] = r.a
        self._a(0); m[0x431] = r.a; m[0x433] = r.a; m[0x434] = r.a
        self._a(13); m[GLOBAL] = r.a
        self._a(0); m[LOSS_MODE] = r.a; m[LOSS_ANIMATION] = r.a
        self._rts()

    def wait_computer_retirement_notice(self):
        """26 C41E..C434: byte-counter wrap, not player ending.

        Counting calls must not be described as counting video frames.
        """
        r, m = self.registers, self.memory
        yield from self._checkpoint(0xC41E)
        m[NOTICE_TIMER] = self._nz(m[NOTICE_TIMER] + 1)
        if r.p & Z:
            self._a(m[RETURN_MAIN]); m[CITY_MAIN] = r.a
            self._a(m[RETURN_MAIN_PHASE]); m[POSTBATTLE_PHASE] = r.a
            self._a(0); m[SUCCESSION_PHASE] = r.a
        self._rts()


class PlayerLossEnding(EndingUIController):
    """NMI8 A01E parent, with direct mode0 ending/reset rules.

    Other ending modes remain the already recovered original parent methods.
    No CPU/IR fallback is present. New local-entry tests require a real caller
    stack and physical23/24; an E000 tail remains a nonlocal reset dependency.
    """
    LOCAL_ENTRIES = (0xA01E, 0xD693, 0xD6AA, 0xD76D)

    def __init__(self, memory, rom, services=None):
        super().__init__(memory, rom, services)
        self._call_owner = None

    def fields(self):
        fields = super().fields()
        fields.update(opening_player_mode=self.memory[OPENING_PLAYER_MODE],
                      winning_leader=self.memory[0x42E])
        return fields

    def run_entry(self, entry=0xA01E, *, registers=None, return_pc=None, max_blocks=200000):
        if registers is None:
            raise ValueError('Actual caller registers and existing stack are required')
        if entry not in self.LOCAL_ENTRIES:
            raise ValueError('Entry outside the original loss-ending closure')
        if tuple(getattr(self.memory, 'banks', ())[1:3]) != self.PAIR:
            raise ValueError('Loss ending requires physical23/24 caller context')
        if not isinstance(max_blocks, int) or max_blocks <= 0:
            raise ValueError('Positive explicit source block budget required')
        word = ((self.memory[0x100 + ((registers.sp + 1) & 255)] |
                 self.memory[0x100 + ((registers.sp + 2) & 255)] << 8) + 1) & 65535
        if return_pc is not None and return_pc != word:
            raise ValueError('Caller return PC differs from the existing stack word')
        return super().run_entry(entry, registers=registers, return_pc=return_pc, max_blocks=max_blocks)

    def _drive(self):
        while True:
            if self.pending is not None:
                call = self.pending
                if self.services is None:
                    return self._result('dependency')
                result = self.services(call)
                if not isinstance(result, dict):
                    return self._result('dependency')
                # E000 replaces the stack. Its actual E066 boundary cannot be
                # mistaken for an RTS to the retired ending callback.
                if call.target == 0xE000 and result.get('status') == 'reset_boundary':
                    if self.registers.pc != 0xE066 or self.registers.sp != 255:
                        return self._result('dependency')
                    self.pending = None; self._program = None
                    return {**self._result('reset_boundary'),
                            'registers': vars(self.registers).copy(),
                            'nonlocal_transfer': True,
                            'boundary': 'Actual E000 reset to E066/SPFF; no caller RTS'}
                if result.get('status') != 'returned':
                    return self._result('dependency')
                if self.registers.pc != call.return_pc or self.registers.sp != call.expected_sp:
                    return self._result('dependency')
                self.pending = None
            try:
                self.pending = next(self._program)
            except StopIteration:
                self._program = None
                status = 'returned' if (self.registers.pc == self._return_pc and
                                         self.registers.sp == self._return_sp) else 'nonlocal_return'
                return self._result(status)

    def loss_or_extinction_notice(self):
        """24 D6AA..D754: initial notice, sprites, genuine clock and exit.

        Initial mode0 queues D8 if a winner leader exists, D9 if it is FF.
        Both text jobs must truly finish before the marker clock advances.
        Once marker FE is reached, only new A exits. Opening mode6F43 is a
        title-setting residue, not a live count of surviving human rulers.
        """
        r, m = self.registers, self.memory
        if False: yield None
        self._mark(0xD6AA); self._a(m[LOSS_ANIMATION])
        if r.p & Z:
            self._a(0); m[0x4CD] = r.a; m[0x4CE] = r.a
            m[LOSS_ANIMATION] = self._nz(m[LOSS_ANIMATION] + 1)
            self._a(255); m[LOSS_MARKER] = r.a
            if not (yield from self._local_call(self.loss_palette, 0xD6BF, 0xD6C2)):
                return
            self._a(217); self._x(m[0x42E]); self._compare(r.x, 255)
            if not r.p & Z:
                self._a(216)
            yield from self._external(0xD6CD, 0xF28B, 0xD6D0, 'call')
            if r.pc != 0xD6D0:
                return
            yield from self._external(0xD6D0, 0xECBF, 0xD6D3, 'call')
            if r.pc != 0xD6D3:
                return
            self._rts(); return

        m[0x4CD] = self._nz(m[0x4CD] + 1)
        self._a(126); m[0x10] = r.a
        self._a(154); m[0x11] = r.a
        self._y(m[LOSS_MARKER])
        if not r.p & N:
            if not (yield from self._local_call(self.ending_frame_sprites, 0xD6E4, 0xD6E7)):
                return
        self._y(m[LOSS_ANIMATION])
        if not (yield from self._local_call(self.ending_frame_sprites, 0xD6EA, 0xD6ED)):
            return
        self._a(m[LOSS_ANIMATION]); self._flag(C, False); self._add(4); self._y(r.a)
        if not (yield from self._local_call(self.ending_frame_sprites, 0xD6F4, 0xD6F7)):
            return
        self._a(m[0x4CD])
        for _ in range(3):
            r.a = self._shift(r.a, False)
        self._a(r.a & 3); self._flag(C, False); self._add(1); m[LOSS_ANIMATION] = r.a
        self._a(m[LOSS_MARKER]); self._compare(r.a, 254)
        if r.p & Z:
            self._a(m[NEW_BUTTONS]); self._a(r.a & 1)
            if not r.p & Z:
                self._a(m[OPENING_PLAYER_MODE])
                if r.p & Z:
                    yield from self._external(0xD752, 0xE000, None, 'tail')
                    return
                self._a(0); m[OPENING_PLAYER_MODE] = r.a
                self._a(m[RETURN_MAIN]); m[0x400] = r.a
                self._a(m[RETURN_MAIN_PHASE]); m[0x401] = r.a
                self._a(0); m[0x402] = r.a
                self._a(1); m[GLOBAL] = r.a
            self._rts(); return

        self._a(m[0x300]); self._compare(r.a, 255)
        if r.p & Z:
            self._a(m[0x304]); self._compare(r.a, 255)
            if r.p & Z:
                m[0x4CE] = self._nz(m[0x4CE] + 1)
                self._a(m[0x4CE])
                r.a = self._shift(r.a, False)
                r.a = self._shift(r.a, False)
                self._y(r.a); self._a(m[(0xD755 + r.y) & 65535]); m[LOSS_MARKER] = r.a
        self._rts()

    def loss_palette(self):
        """24 D76D..D77A: request the actual 32-byte loss palette image."""
        r, m = self.registers, self.memory
        if False: yield None
        self._mark(0xD76D); self._y(0)
        while True:
            self._a(m[(0xD77B + r.y) & 65535]); m[0x100 + r.y] = r.a
            self._y(r.y + 1); self._compare(r.y, 32)
            if r.p & C:
                break
        self._rts()
