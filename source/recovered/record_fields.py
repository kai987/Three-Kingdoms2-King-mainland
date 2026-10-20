"""Evidence-bound city auxiliary fields and monthly event gate.

The functions below directly implement game rules and retain observable CPU
flags, scratch and caller stack where requested. ROM is immutable data only;
no CPU, opcodes, control IR, fabricated readiness or acknowledgement execute.
The auxiliary record view deliberately leaves unproven bytes unnamed.
"""
from dataclasses import dataclass
from .global_ui_controller import UIControlBase, UIRegisters, C, Z, V, N

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CITY_BASE, CITY_STRIDE, CITY_COUNT = 0x6000, 32, 30
MONTH, MONTHLY_EVENT_LATCH = 0x6F01, 0x6F06
TURN_EVENT_PHASE, EVENT_SUBPHASE = 0x0401, 0x0402


def city_address(city):
    if not isinstance(city, int) or not 0 <= city < CITY_COUNT:
        raise ValueError('Proven city record IDs 0..29 are required')
    return CITY_BASE + CITY_STRIDE * city


def adverse_event_threshold(governance):
    """AB70..AB8A: accepted RNG byte must be strictly below this threshold.

    This is the rejection-sampled E862 stream, not an assertion that arbitrary
    cursors/calls produce independent, unbiased percentages.
    """
    if not isinstance(governance, int) or not 0 <= governance < 256:
        raise ValueError('Governance must be an original byte')
    return 50 if governance < 20 else 30 if governance < 30 else 10 if governance < 40 else 5 if governance < 50 else 0


@dataclass(frozen=True)
class CityAuxiliaryFields:
    """Read-only view; +1 and +28..31 have no proven official names."""
    raw: bytes

    def __post_init__(self):
        if len(self.raw) != CITY_STRIDE:
            raise ValueError('An exact original 32-byte city record is required')

    @property
    def byte1_unresolved(self):
        return self.raw[1]

    @property
    def assignment_gate_word_01_02(self):
        """BD97/BD9D really overlap +1 and the LOW byte of gold at +2."""
        return self.raw[1] | self.raw[2] << 8

    @property
    def assignment_gate_at_least_300(self):
        return self.assignment_gate_word_01_02 >= 300

    @property
    def adverse_event_cooldown(self):
        """+27 counts eligible scanner invocations, not independently months."""
        return self.raw[27]

    @property
    def unresolved_tail(self):
        return self.raw[28:32]

    @property
    def recruitment_append_offset(self):
        """ACF6/DC6B count occupied slots, rather than find the first hole."""
        return 17 + sum(value != 255 for value in self.raw[17:27])

    @property
    def full_roster_recruitment_overwrites_cooldown(self):
        """A boundary alias, normally excluded by the human menu capacity gate."""
        return self.recruitment_append_offset == 27

    @classmethod
    def from_memory(cls, memory, city):
        address = city_address(city)
        return cls(bytes(memory[address:address + CITY_STRIDE]))


class RecordFieldServices(UIControlBase):
    """Bank25/26 monthly gate and adverse-event candidate scanner.

    A2BC and AB25 are complete local procedures with actual caller RTS frames.
    Their fixed F2AF/E862 dependencies must truly return. The separate BD95
    gate is only an explicit bounded prefix of bank10's assignment procedure.
    """
    PAIR = (25, 26)
    PUBLIC_ENTRIES = (0xA2BC, 0xAB25)

    def fields(self):
        m = self.memory
        pair = tuple(getattr(m, 'banks', ())[1:3])
        return dict(month_zero_based=m[MONTH], monthly_event_latch=m[MONTHLY_EVENT_LATCH],
                    turn_event_phase=m[TURN_EVENT_PHASE] if pair == self.PAIR else None,
                    event_subphase=m[EVENT_SUBPHASE] if pair == self.PAIR else None,
                    city_menu_parent_phase=m[0x401] if pair == (27, 28) else None,
                    recruitment_city=m[0x402] if pair == (27, 28) else None,
                    event_city_cursor=m[0x0403], candidate_thresholds=tuple(m[0x042C + i] for i in range(30)))

    def run_entry(self, entry=0xA2BC, *, registers=None, return_pc=None, max_blocks=200000):
        if registers is None:
            raise ValueError('Supply actual caller registers and its existing RTS frame')
        if entry not in self.PUBLIC_ENTRIES:
            raise ValueError('Only A2BC/AB25 complete procedures are owned here')
        if tuple(getattr(self.memory, 'banks', ())[1:3]) != self.PAIR:
            raise ValueError('Physical bank25/26 caller mapping is required')
        self._field_prefix = False
        return super().run_entry(entry, registers=registers, return_pc=return_pc, max_blocks=max_blocks)

    def _result(self, status):
        result = super()._result(status)
        if getattr(self, '_field_prefix', False) and status == 'returned':
            result['status'] = 'bounded_prefix'
            result['no_officer_status_or_loyalty_update_performed'] = True
        return result

    def _entry(self, entry):
        return self.monthly_event_gate() if entry == 0xA2BC else self.scan_adverse_event_candidates()

    def monthly_event_gate(self):
        """A2BC..A30B: defer until text/PPU jobs are idle; claim this month once."""
        r, m = self.registers, self.memory
        if False:
            yield None
        self._a(m[0x0300]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        self._a(m[0x0304]); self._compare(r.a, 255)
        if not r.p & Z:
            self._rts(); return
        self._a(m[0x007E])
        if not r.p & Z:
            self._rts(); return
        self._a(m[MONTHLY_EVENT_LATCH])
        if not r.p & Z:
            self._a(2); m[TURN_EVENT_PHASE] = r.a
            self._rts(); return
        m[MONTHLY_EVENT_LATCH] = self._nz(m[MONTHLY_EVENT_LATCH] + 1)
        self._a(m[MONTH]); self._compare(r.a, 3)
        if r.p & Z:
            self._a(6)
        else:
            self._a(m[MONTH]); self._compare(r.a, 9)
            self._a(7 if r.p & Z else 15)
        m[TURN_EVENT_PHASE] = r.a
        self._a(0); m[EVENT_SUBPHASE] = r.a
        self._rts()

    def scan_adverse_event_candidates(self):
        """AB25..ABA8: scan 30 records once; only form candidates here.

        Later phases choose one of three loss-effect types. This procedure
        neither applies those losses nor emits/acknowledges their messages.
        Year89/month0..3 skips the entire scan, including counter decrement.
        The neutral check is exactly owner_byte &15 ==7, not owner_low3 ==7.
        """
        r, m = self.registers, self.memory
        self._a(m[0x6F00]); self._compare(r.a, 0x59)
        if r.p & Z:
            self._a(m[MONTH]); self._compare(r.a, 4)
            if not r.p & C:
                self._a(1); m[TURN_EVENT_PHASE] = r.a
                self._rts(); return
        self._x(0); self._a(0)
        while True:
            m[0x042C + r.x] = r.a
            self._x(r.x + 1); self._compare(r.x, 30)
            if r.p & C:
                break
        self._x(0)
        while True:
            self._mark(0xAB47)
            self._a(r.x)
            yield from self._external(0xAB48, 0xF2AF, 0xAB4B, 'call')
            if r.pc != 0xAB4B:
                return
            self._y(0); self._a(m[(m[0] | m[1] << 8) + r.y]); self._a(r.a & 15); self._compare(r.a, 7)
            if not r.p & Z:
                self._y(27); self._a(m[(m[0] | m[1] << 8) + r.y])
                if not r.p & Z:
                    self._flag(C, True); self._add(1, subtract=True)
                    m[(m[0] | m[1] << 8) + r.y] = r.a
                else:
                    self._y(11); self._a(m[(m[0] | m[1] << 8) + r.y]); self._compare(r.a, 50)
                    if not r.p & C:
                        self._y(5); self._compare(r.a, 40)
                        if not r.p & C:
                            self._y(10); self._compare(r.a, 30)
                            if not r.p & C:
                                self._y(30); self._compare(r.a, 20)
                                if not r.p & C:
                                    self._y(50)
                        m[0x11] = r.y
                        self._a(100)
                        yield from self._external(0xAB8F, 0xE862, 0xAB92, 'call')
                        if r.pc != 0xAB92:
                            return
                        self._compare(r.a, m[0x11])
                        if not r.p & C:
                            self._a(m[0x11]); m[0x042C + r.x] = r.a
                            self._y(27); self._a(6); m[(m[0] | m[1] << 8) + r.y] = r.a
            self._x(r.x + 1); self._compare(r.x, 30)
            if r.p & C:
                break
        m[EVENT_SUBPHASE] = self._nz(m[EVENT_SUBPHASE] + 1)
        self._a(0); m[0x0403] = r.a
        self._rts()

    def assignment_word_gate_prefix(self, registers):
        """10:BD95..BDA1, stopping at BDA3/BDEE before further assignments.

        The caller has already set20:21 to the city. No pointer setup, resource
        cap, roster scan, assignment or RTS is represented by this prefix.
        """
        if registers is None:
            raise ValueError('Supply actual prefix registers and existing caller stack')
        if self._program is not None:
            raise RuntimeError('A record service is pending')
        if tuple(getattr(self.memory, 'banks', ())[1:3]) != (10, 11):
            raise ValueError('Physical bank10/11 prefix mapping is required')
        if registers.p & 8:
            raise ValueError('NES binary arithmetic requires D=0')
        self.registers = registers; r, m = registers, self.memory
        pointer = m[0x20] | m[0x21] << 8
        if not (0x6000 <= pointer < 0x63C0 and (pointer - 0x6000) % 32 == 0):
            raise ValueError('20:21 must point at a proven city record')
        self._y(1); self._a(m[pointer + r.y]); self._flag(C, True); self._add(44, subtract=True)
        self._y(r.y + 1); self._a(m[pointer + r.y]); self._add(1, subtract=True)
        accepted = bool(r.p & C); r.pc = 0xBDA3 if accepted else 0xBDEE
        return dict(status='bounded_prefix', accepted=accepted, stop_pc=r.pc,
                    composite_word=m[pointer + 1] | m[pointer + 2] << 8,
                    no_city_assignment_performed=True)

    def calendar_turn_scan_prefix(self, registers):
        """25:A041..A067, before diplomacy decrement/next-ruler selection.

        Stop at A068 on month wrap, or A06B otherwise. The original initial
        slotFF increments to0 without advancing the month. No RTS is claimed.
        """
        if registers is None:
            raise ValueError('Supply actual prefix registers and existing caller stack')
        if self._program is not None:
            raise RuntimeError('A record service is pending')
        if tuple(getattr(self.memory, 'banks', ())[1:3]) != self.PAIR:
            raise ValueError('Physical bank25/26 prefix mapping is required')
        if registers.p & 8:
            raise ValueError('NES binary arithmetic requires D=0')
        if self.memory[MONTH] >= 12 or self.memory[0x6F04] not in (*range(7), 255):
            raise ValueError('Proven month0..11 and turn slot0..6/initialFF are required')
        self.registers = registers; r, m = registers, self.memory
        self._a(240); m[0x6F41] = r.a
        m[0x6F04] = self._nz(m[0x6F04] + 1)
        self._a(m[0x6F04]); self._compare(r.a, 7)
        wrapped = bool(r.p & C)
        if wrapped:
            self._a(0); m[0x6F04] = m[MONTHLY_EVENT_LATCH] = r.a
            self._y(m[MONTH]); self._y(r.y + 1); self._compare(r.y, 12)
            if r.p & C:
                self._y(0); m[0x6F00] = self._nz(m[0x6F00] + 1)
            m[MONTH] = r.y
        r.pc = 0xA068 if wrapped else 0xA06B
        return dict(status='bounded_prefix', month_advanced=wrapped, stop_pc=r.pc,
                    no_diplomacy_decrement_or_ruler_selection_performed=True)

    def recruitment_append_prefix(self, registers):
        """27:ACF0..AD02, stopping before leader/status/loyalty processing.

        All10 occupied roster bytes insert at+27, aliasing the cooldown. This
        is an explicitly tested boundary invocation, not a claim that the
        normal capacity-checked menu permits an eleventh officer.
        """
        if registers is None:
            raise ValueError('Supply actual prefix registers and existing caller stack')
        if self._program is not None:
            raise RuntimeError('A record service is pending')
        if tuple(getattr(self.memory, 'banks', ())[1:3]) != (27, 28):
            raise ValueError('Physical bank27/28 prefix mapping is required')
        if registers.p & 8:
            raise ValueError('NES binary arithmetic requires D=0')
        city_address(self.memory[0x402])
        if self.memory[0x472] >= 237:
            raise ValueError('Proven officer ID0..236 is required')
        self.registers = registers; self.events = []; self.pending = None
        self._before = self.fields(); self._blocks = 0; self._limit = 200000
        self._return_pc = 0xAD03; self._return_sp = registers.sp
        self._field_prefix = True; self._program = self.append_recruitment_roster()
        return self._drive()

    def append_recruitment_roster(self):
        r, m = self.registers, self.memory
        self._a(m[0x402])
        yield from self._external(0xACF3, 0xF2AF, 0xACF6, 'call')
        if r.pc != 0xACF6:
            return
        if not (yield from self._local_call(self.count_occupied_roster_slots, 0xACF6, 0xACF9)):
            return
        self._a(r.x); self._flag(C, False); self._add(17); self._y(r.a)
        self._a(m[0x472]); m[(m[0] | m[1] << 8) + r.y] = r.a
        r.pc = 0xAD03

    def count_occupied_roster_slots(self):
        """DC6B..DC7B: exactly10 slots, including occupied bytes after holes."""
        r, m = self.registers, self.memory
        if False:
            yield None
        self._y(17); self._x(0)
        while True:
            self._a(m[(m[0] | m[1] << 8) + r.y]); self._compare(r.a, 255)
            if not r.p & Z:
                self._x(r.x + 1)
            self._y(r.y + 1); self._compare(r.y, 27)
            if r.p & C:
                break
        self._rts()
