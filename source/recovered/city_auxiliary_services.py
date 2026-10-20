"""Exact city-assignment and recruitment source for physical10/11.

City byte1 stays opaque. The original recruitment gate reads the overlapping
little-endian word at city+1/+2, then scans all ten roster bytes. This source
preserves CPU flags, scratch, caller stack, side effects and nonlocal budget
returns; it neither executes ROM code nor acknowledges other services.
"""
from .domestic_cooperation_controller import (
    DomesticCooperationController, UIRegisters, ROM_SHA256,
    C, Z, N, RULER, DIFFICULTY, AI_BUDGET, AI_REQUEST, AI_PHASE,
)

from .domestic_cooperation_controller import _ContinueLoop_B5FC, _ContinueLoop_B639, _ContinueLoop_B68A, _ContinueLoop_B78B, _ContinueLoop_B99B, _ContinueLoop_B9E5, _ContinueLoop_BA95, _ContinueLoop_BAC0, _ContinueLoop_BB1C, _ContinueLoop_BB40, _ContinueLoop_BBC1, _ContinueLoop_BBE6, _ContinueLoop_BC28, _ContinueLoop_BC3E, _ContinueLoop_BD16, _ContinueLoop_BD36

CITY_SCAN, BEST_SCORE, CHOSEN_OFFICER, CHOSEN_CITY = 0x36, 0x37, 0x38, 0x39
NEEDED_LOW, NEEDED_HIGH, DEFICIT_LOW, DEFICIT_HIGH = 0x3A, 0x3B, 0x3C, 0x3D


class CityAuxiliaryServices(DomesticCooperationController):
    """Readable B49C assignment and BD7A recruitment in the real main2 context.

    Existing pure source owns shared pointers, neighbor/roster assignment and
    the eventual BEC7 development tail. Public A000/A00F use this new B49C via
    normal virtual calls; B49C/BD7A can be checked with an already present real
    caller frame. No synthetic return, RNG sample or completion is supplied.
    """
    PUBLIC_ENTRIES = (0xA000, 0xA00F, 0xB49C, 0xBD7A)

    def _entry(self, entry):
        if entry == 0xBD7A:
            return self.recruitment_then_development()
        if entry not in self.PUBLIC_ENTRIES:
            raise ValueError('Entry outside the new city auxiliary public domain')
        return super()._entry(entry)

    def _city_byte(self, offset):
        m = self.memory
        return m[((m[0x20] | m[0x21] << 8) + offset) & 65535]

    def _officer_byte(self, offset):
        m = self.memory
        return m[((m[0x22] | m[0x23] << 8) + offset) & 65535]

    def _write_city_byte(self, offset, value):
        m = self.memory
        m[((m[0x20] | m[0x21] << 8) + offset) & 65535] = value

    def _write_officer_byte(self, offset, value):
        m = self.memory
        m[((m[0x22] | m[0x23] << 8) + offset) & 65535] = value

    def city_assignment_strategy(self):
        """B49C: sampled assignment branch; two redistribution passes then fill.

        Rejection sampling consumes actual E8AA cursor values. The first pass
        excludes the ruler city and selects owned cities without enemy neighbors
        with at least three prefix officers. The second requires enemy neighbors
        and the original average/count threshold+2. A successful relocation
        retries the same city before advancing; no extra call frame is created
        for the BD7A tail. Sample<10 enters the original secondary branch.
        """
        r, m = self.registers, self.memory
        while True:
            self._mark(0xB49C)
            yield from self._external(0xB49C, 0xE8AA, 0xB49F, 'call')
            if r.pc != 0xB49F:
                return
            self._a(r.a & 0x7F)
            self._compare(r.a, 50)
            self._mark(0xB4A3)
            if not r.p & C:
                break
        self._compare(r.a, 10)
        self._mark(0xB4A7)
        if not r.p & C:
            return (yield from self.secondary_assignment_strategy())
        if not (yield from self._local_call(self.find_ruler_city, 0xB4AC, 0xB4AF)):
            return
        m[0x45] = r.a
        if not (yield from self._local_call(self.domesticcooperationcontroller_d03a, 0xB4B2, 0xB4B5)):
            return
        self._a(3)
        m[0x41] = r.a
        self._a(0)
        m[CITY_SCAN] = r.a
        # Preserve the distinct JSR return words of the two original passes.
        if not (yield from self.redistribute_owned_rosters(False)):
            return
        self._a(m[0x40])
        self._flag(C, False)
        self._add(2)
        m[0x41] = r.a
        self._a(0)
        m[CITY_SCAN] = r.a
        if not (yield from self.redistribute_owned_rosters(True)):
            return
        return (yield from self.recruitment_then_development())

    def redistribute_owned_rosters(self, enemy_frontier):
        """B4BF/B504: semantic loop retaining the two original call-site words."""
        r, m = self.registers, self.memory
        loop_pc, pointer_pc, neighbor_pc, count_pc, move_pc, end_pc = (
            (0xB504, 0xB50C, 0xB514, 0xB51C, 0xB524, 0xB539)
            if enemy_frontier else
            (0xB4BF, 0xB4C7, 0xB4CF, 0xB4D7, 0xB4DF, 0xB4F4)
        )
        while True:
            self._mark(loop_pc)
            self._a(m[CITY_SCAN])
            self._compare(r.a, m[0x45])
            retry = False
            if not r.p & Z:
                if not (yield from self._local_call(self.city_pointer_and_resource_caps, pointer_pc, pointer_pc + 3)):
                    return False
                self._compare(r.a, m[RULER])
                if r.p & Z:
                    if not (yield from self._local_call(self.build_enemy_neighbor_list, neighbor_pc, neighbor_pc + 3)):
                        return False
                    frontier_matches = not bool(r.p & Z) if enemy_frontier else bool(r.p & Z)
                    if frontier_matches:
                        self._a(m[CITY_SCAN])
                        if not (yield from self._local_call(self.count_prefix_officers, count_pc, count_pc + 3)):
                            return False
                        self._compare(r.a, m[0x41])
                        if r.p & C:
                            if not (yield from self._local_call(self.domesticcooperationcontroller_b53e, move_pc, move_pc + 3)):
                                return False
                            self._a(m[0x3D])
                            self._compare(r.a, 255)
                            retry = not bool(r.p & Z)
            if retry:
                continue
            m[CITY_SCAN] = self._nz(m[CITY_SCAN] + 1)
            self._a(m[CITY_SCAN])
            self._compare(r.a, 30)
            self._mark(end_pc)
            if r.p & C:
                return True

    def recruitment_then_development(self):
        """BD7A..BEC6: select a deficient officer and fill the raw word to1000.

        The overlapping city+1/+2 gate>=300 is eligibility, not a300gold bill.
        Heads score100; other officers score武力; later equal scores replace.
        FF holes are skipped while scanning all ten entries. Low10 bits detect
        1000 and compute need; the commit writes the complete word03E8. Reserve
        shortage buys100 blocks at a wrapping byte cost20 per iteration. Exact
        reserve==need also buys one block. Resource-payment failure is ignored
        by this original caller, which still adds reserve and fills the officer.
        Budget charge2 can discard the current caller frame and end main2.
        """
        r, m = self.registers, self.memory
        while True:
            self._mark(0xBD7A)
            self._a(0)
            m[CITY_SCAN] = r.a
            m[BEST_SCORE] = r.a
            self._a(255)
            m[CHOSEN_OFFICER] = r.a
            m[CHOSEN_CITY] = r.a
            while True:
                self._mark(0xBD8A)
                self._a(m[CITY_SCAN])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xBD8D, 0xBD90)):
                    return
                self._compare(r.a, m[RULER])
                if r.p & Z:
                    self._y(1)
                    self._a(self._city_byte(r.y))
                    self._flag(C, True)
                    self._add(44, subtract=True)
                    self._y(r.y + 1)
                    self._a(self._city_byte(r.y))
                    self._add(1, subtract=True)
                    self._mark(0xBDA1)
                    if r.p & C:
                        self._y(17)
                        m[0x24] = r.y
                        while True:
                            self._mark(0xBDA7)
                            self._y(m[0x24])
                            self._a(self._city_byte(r.y))
                            self._compare(r.a, 255)
                            deficient = False
                            if not r.p & Z:
                                self._y(9)
                                if not (yield from self._local_call(self.officer_field_pointer, 0xBDB1, 0xBDB4)):
                                    return
                                self._a(r.a & 3)
                                self._compare(r.a, 3)
                                deficient = not bool(r.p & Z)
                                if not deficient:
                                    self._y(8)
                                    self._a(self._officer_byte(r.y))
                                    self._compare(r.a, 232)
                                    deficient = not bool(r.p & Z)
                            if deficient:
                                self._y(m[0x24])
                                self._compare(r.y, 17)
                                if r.p & Z:
                                    self._a(100)
                                else:
                                    self._y(1)
                                    self._a(self._officer_byte(r.y))
                                self._compare(r.a, m[BEST_SCORE])
                                if r.p & C:
                                    m[BEST_SCORE] = r.a
                                    self._y(m[0x24])
                                    self._a(self._city_byte(r.y))
                                    m[CHOSEN_OFFICER] = r.a
                                    self._a(m[CITY_SCAN])
                                    m[CHOSEN_CITY] = r.a
                            m[0x24] = self._nz(m[0x24] + 1)
                            self._a(m[0x24])
                            self._compare(r.a, 27)
                            if r.p & C:
                                break
                m[CITY_SCAN] = self._nz(m[CITY_SCAN] + 1)
                self._a(m[CITY_SCAN])
                self._compare(r.a, 30)
                if r.p & C:
                    break
            self._a(m[CHOSEN_OFFICER])
            self._compare(r.a, 255)
            if r.p & Z:
                return (yield from self.city_development_strategy())
            self._a(m[CHOSEN_CITY])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xBE05, 0xBE08)):
                return
            self._a(m[CHOSEN_OFFICER])
            self._y(8)
            if not (yield from self._local_call(self.officer_field_pointer, 0xBE0D, 0xBE10)):
                return
            m[0x2A] = r.a
            self._y(r.y + 1)
            self._a(self._officer_byte(r.y))
            self._a(r.a & 3)
            m[0x2B] = r.a
            self._a(232)
            self._flag(C, True)
            self._add(m[0x2A], subtract=True)
            m[NEEDED_LOW] = r.a
            m[0x2C] = r.a
            self._a(3)
            self._add(m[0x2B], subtract=True)
            m[NEEDED_HIGH] = r.a
            m[0x2D] = r.a
            self._y(12)
            self._a(m[NEEDED_LOW])
            self._flag(C, True)
            self._add(self._city_byte(r.y), subtract=True)
            m[DEFICIT_LOW] = r.a
            self._y(r.y + 1)
            self._a(m[NEEDED_HIGH])
            self._add(self._city_byte(r.y), subtract=True)
            m[DEFICIT_HIGH] = r.a
            self._mark(0xBE40)
            if r.p & C:
                self._y(0)
                m[0x28] = r.y
                m[0x29] = r.y
                while True:
                    self._mark(0xBE48)
                    self._a(r.y)
                    self._flag(C, False)
                    self._add(20)
                    self._y(r.a)
                    self._a(m[0x28])
                    self._flag(C, False)
                    self._add(100)
                    m[0x28] = r.a
                    self._a(m[0x29])
                    self._add(0)
                    m[0x29] = r.a
                    self._a(m[DEFICIT_LOW])
                    self._flag(C, True)
                    self._add(100, subtract=True)
                    m[DEFICIT_LOW] = r.a
                    self._a(m[DEFICIT_HIGH])
                    self._add(0, subtract=True)
                    m[DEFICIT_HIGH] = r.a
                    if not r.p & C:
                        break
                self._a(r.y)
                m[0x22] = r.a
                self._a(0)
                m[0x23] = r.a
                self._a(0)
                m[0x24] = r.a
                self._a(m[CHOSEN_CITY])
                if not (yield from self._local_call(self.pay_city_gold, 0xBE7B, 0xBE7E)):
                    return
                self._a(m[CHOSEN_CITY])
                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xBE81, 0xBE84)):
                    return
                self._y(12)
                self._a(m[0x28])
                self._flag(C, False)
                self._add(self._city_byte(r.y))
                self._write_city_byte(r.y, r.a)
                self._y(r.y + 1)
                self._a(m[0x29])
                self._add(self._city_byte(r.y))
                self._write_city_byte(r.y, r.a)
            if not (yield from self._local_call(self.cap_city_word, 0xBE94, 0xBE97)):
                return
            self._y(12)
            self._a(self._city_byte(r.y))
            self._flag(C, True)
            self._add(m[NEEDED_LOW], subtract=True)
            self._write_city_byte(r.y, r.a)
            self._y(r.y + 1)
            self._a(self._city_byte(r.y))
            self._add(m[NEEDED_HIGH], subtract=True)
            self._write_city_byte(r.y, r.a)
            if not (yield from self._local_call(self.cap_city_word, 0xBEA9, 0xBEAC)):
                return
            self._a(m[CHOSEN_OFFICER])
            self._y(8)
            if not (yield from self._local_call(self.officer_field_pointer, 0xBEB1, 0xBEB4)):
                return
            self._y(8)
            self._a(232)
            self._write_officer_byte(r.y, r.a)
            self._y(r.y + 1)
            self._a(3)
            self._write_officer_byte(r.y, r.a)
            self._a(2)
            if not (yield from self._local_call(self.charge_task_budget, 0xBEC1, 0xBEC4)):
                return

    def secondary_assignment_strategy(self):
        """B5FC: reused frozen direct secondary-assignment branches; no new frame."""
        r = self.registers
        m = self.memory
        if False:
            yield None
        while True:
            try:
                yield from self._external(46588, 59546, 46591, 'call', None)
                if r.pc != 46591:
                    return
                self._a(r.a & 127)
                self._compare(r.a, 90)
                self._mark(46595)
                if r.p & C:
                    continue
                else:
                    pass
                self._compare(r.a, 30)
                self._mark(46599)
                if not r.p & C:
                    self._a(0)
                    m[54] = r.a
                    self._a(255)
                    m[61] = r.a
                    self._a(0)
                    m[62] = r.a
                    while True:
                        try:
                            self._a(m[54])
                            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 48068, 48071)):
                                return
                            self._compare(r.a, m[RULER])
                            self._mark(48074)
                            if not r.p & Z:
                                pass
                            else:
                                if not (yield from self._local_call(self.domesticcooperationcontroller_bd3e, 48076, 48079)):
                                    return
                                pass
                            m[54] = self._nz(m[54] + 1)
                            self._a(m[54])
                            self._compare(r.a, 30)
                            self._mark(48087)
                            if not r.p & C:
                                continue
                            else:
                                pass
                            self._a(0)
                            m[54] = r.a
                            m[55] = r.a
                            self._a(255)
                            m[56] = r.a
                            while True:
                                try:
                                    self._a(m[54])
                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps, 48105, 48108)):
                                        return
                                    self._compare(r.a, m[RULER])
                                    self._mark(48111)
                                    if r.p & Z:
                                        pass
                                    else:
                                        if not (yield from self._local_call(self.ruler_pointer, 48113, 48116)):
                                            return
                                        self._y(3)
                                        self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                        self._compare(r.a, 3)
                                        self._mark(48122)
                                        if r.p & Z:
                                            pass
                                        else:
                                            self._a(m[54])
                                            if not (yield from self._local_call(self.count_prefix_officers, 48127, 48130)):
                                                return
                                            self._compare(r.a, m[55])
                                            self._mark(48133)
                                            if not r.p & C:
                                                pass
                                            else:
                                                m[55] = r.a
                                                self._a(m[54])
                                                m[56] = r.a
                                                pass
                                            pass
                                        pass
                                    m[54] = self._nz(m[54] + 1)
                                    self._a(m[54])
                                    self._compare(r.a, 30)
                                    self._mark(48152)
                                    if not r.p & C:
                                        continue
                                    else:
                                        pass
                                    self._a(m[55])
                                    self._compare(r.a, 6)
                                    self._mark(48159)
                                    if r.p & C:
                                        self._y(15)
                                        self._a(255)
                                        while True:
                                            try:
                                                m[28531 + r.y & 65535] = r.a
                                                self._y(r.y - 1)
                                                self._mark(48172)
                                                if not r.p & N:
                                                    continue
                                                else:
                                                    pass
                                                self._a(m[56])
                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 48177, 48180)):
                                                    return
                                                self._a(17)
                                                m[54] = r.a
                                                self._a(0)
                                                m[55] = r.a
                                                while True:
                                                    try:
                                                        self._y(m[54])
                                                        self._a(m[(m[32] | m[33] << 8) + r.y & 65535])
                                                        self._compare(r.a, 255)
                                                        self._mark(48197)
                                                        if r.p & Z:
                                                            pass
                                                        else:
                                                            self._y(3)
                                                            if not (yield from self._local_call(self.officer_field_pointer, 48201, 48204)):
                                                                return
                                                            self._compare(r.a, 50)
                                                            self._mark(48206)
                                                            if not r.p & C:
                                                                pass
                                                            else:
                                                                self._compare(r.a, 90)
                                                                self._mark(48210)
                                                                if r.p & C:
                                                                    pass
                                                                else:
                                                                    self._y(m[54])
                                                                    self._a(m[(m[32] | m[33] << 8) + r.y & 65535])
                                                                    self._y(m[55])
                                                                    m[28531 + r.y & 65535] = r.a
                                                                    m[55] = self._nz(m[55] + 1)
                                                                    pass
                                                                pass
                                                            pass
                                                        m[54] = self._nz(m[54] + 1)
                                                        self._a(m[54])
                                                        self._compare(r.a, 27)
                                                        self._mark(48234)
                                                        if not r.p & C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[55])
                                                        self._mark(48239)
                                                        if r.p & Z:
                                                            pass
                                                        else:
                                                            self._compare(r.a, 1)
                                                            self._mark(48243)
                                                            if r.p & Z:
                                                                pass
                                                            else:
                                                                if not (yield from self._local_call(self.random_low_nibble_below, 48245, 48248)):
                                                                    return
                                                                self._flag(C, False)
                                                                self._add(1)
                                                                pass
                                                            self._y(r.a)
                                                            self._a(m[28530 + r.y & 65535])
                                                            m[55] = r.a
                                                            self._a(m[55])
                                                            self._y(2)
                                                            if not (yield from self._local_call(self.officer_field_pointer, 48263, 48266)):
                                                                return
                                                            m[0] = r.a
                                                            self._a(m[62])
                                                            self._flag(C, True)
                                                            self._add(m[0], subtract=True)
                                                            self._mark(48274)
                                                            if r.p & C:
                                                                pass
                                                            else:
                                                                self._a(0)
                                                                pass
                                                            self._y(m[DIFFICULTY])
                                                            self._flag(C, False)
                                                            self._add(m[48299 + r.y & 65535])
                                                            m[42] = r.a
                                                            self._a(100)
                                                            if not (yield from self._local_call(self.random_below, 48289, 48292)):
                                                                return
                                                            self._compare(r.a, m[42])
                                                            self._mark(48294)
                                                            if not r.p & C:
                                                                self._a(m[62])
                                                                m[33] = r.a
                                                                self._a(20)
                                                                m[35] = r.a
                                                                self._a(0)
                                                                m[34] = r.a
                                                                m[36] = r.a
                                                                if not (yield from self._local_call(self.divide_domestic_word, 48317, 48320)):
                                                                    return
                                                                self._a(7)
                                                                if not (yield from self._local_call(self.random_low_nibble_below, 48322, 48325)):
                                                                    return
                                                                self._flag(C, False)
                                                                self._add(1)
                                                                self._flag(C, False)
                                                                self._add(m[33])
                                                                m[57] = r.a
                                                                self._a(m[55])
                                                                self._y(3)
                                                                if not (yield from self._local_call(self.officer_field_pointer, 48339, 48342)):
                                                                    return
                                                                self._flag(C, True)
                                                                self._add(m[57], subtract=True)
                                                                self._mark(48346)
                                                                if r.p & C:
                                                                    pass
                                                                else:
                                                                    self._a(0)
                                                                    pass
                                                                m[(m[34] | m[35] << 8) + r.y & 65535] = r.a
                                                                self._a(m[RULER])
                                                                if not (yield from self._local_call(self.ruler_pointer, 48355, 48358)):
                                                                    return
                                                                self._y(0)
                                                                self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                m[57] = r.a
                                                                self._a(m[56])
                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 48368, 48371)):
                                                                    return
                                                                m[59] = r.a
                                                                if not (yield from self._local_call(self.ruler_pointer, 48374, 48377)):
                                                                    return
                                                                self._y(0)
                                                                self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                m[58] = r.a
                                                                self._y(3)
                                                                self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                m[28484] = r.a
                                                                self._a(0)
                                                                m[54] = r.a
                                                                self._a(255)
                                                                m[61] = r.a
                                                                self._a(0)
                                                                m[62] = r.a
                                                                while True:
                                                                    try:
                                                                        self._a(m[54])
                                                                        if not (yield from self._local_call(self.city_pointer_and_resource_caps, 48409, 48412)):
                                                                            return
                                                                        self._compare(r.a, m[59])
                                                                        self._mark(48415)
                                                                        if not r.p & Z:
                                                                            pass
                                                                        else:
                                                                            self._a(m[58])
                                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_bd40, 48420, 48423)):
                                                                                return
                                                                            pass
                                                                        m[54] = self._nz(m[54] + 1)
                                                                        self._a(m[54])
                                                                        self._compare(r.a, 30)
                                                                        self._mark(48431)
                                                                        if not r.p & C:
                                                                            continue
                                                                        else:
                                                                            pass
                                                                        self._a(249)
                                                                        m[AI_REQUEST] = r.a
                                                                        while True:
                                                                            try:
                                                                                self._a(m[AI_REQUEST])
                                                                                self._mark(48441)
                                                                                if not r.p & Z:
                                                                                    continue
                                                                                else:
                                                                                    pass
                                                                                return (yield from self.city_development_strategy())
                                                                            except _ContinueLoop_BD36:
                                                                                continue
                                                                    except _ContinueLoop_BD16:
                                                                        continue
                                                            else:
                                                                pass
                                                            pass
                                                        return (yield from self.city_development_strategy())
                                                    except _ContinueLoop_BC3E:
                                                        continue
                                            except _ContinueLoop_BC28:
                                                continue
                                    else:
                                        pass
                                    return (yield from self.city_development_strategy())
                                except _ContinueLoop_BBE6:
                                    continue
                        except _ContinueLoop_BBC1:
                            continue
                else:
                    self._compare(r.a, 60)
                    self._mark(46603)
                    if not r.p & C:
                        self._a(0)
                        m[54] = r.a
                        m[57] = r.a
                        self._a(255)
                        m[55] = r.a
                        m[56] = r.a
                        while True:
                            try:
                                self._a(m[54])
                                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47518, 47521)):
                                    return
                                self._compare(r.a, m[RULER])
                                self._mark(47524)
                                if not r.p & Z:
                                    pass
                                else:
                                    if not (yield from self._local_call(self.domesticcooperationcontroller_bb82, 47526, 47529)):
                                        return
                                    self._a(m[54])
                                    if not (yield from self._local_call(self.count_prefix_officers, 47532, 47535)):
                                        return
                                    self._compare(r.a, 10)
                                    self._mark(47537)
                                    if r.p & C:
                                        pass
                                    else:
                                        self._compare(r.a, m[55])
                                        self._mark(47542)
                                        if r.p & C:
                                            pass
                                        else:
                                            m[55] = r.a
                                            self._a(m[54])
                                            m[56] = r.a
                                            pass
                                        pass
                                    pass
                                m[54] = self._nz(m[54] + 1)
                                self._a(m[54])
                                self._compare(r.a, 30)
                                self._mark(47561)
                                if not r.p & C:
                                    continue
                                else:
                                    pass
                                self._a(m[56])
                                self._compare(r.a, 255)
                                self._mark(47568)
                                if not r.p & Z:
                                    self._a(0)
                                    m[54] = r.a
                                    self._a(255)
                                    m[61] = r.a
                                    m[62] = r.a
                                    m[63] = r.a
                                    while True:
                                        try:
                                            self._a(m[54])
                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47592, 47595)):
                                                return
                                            self._compare(r.a, m[RULER])
                                            self._mark(47598)
                                            if r.p & Z:
                                                pass
                                            else:
                                                if not (yield from self._local_call(self.domesticcooperationcontroller_bb48, 47600, 47603)):
                                                    return
                                                pass
                                            m[54] = self._nz(m[54] + 1)
                                            self._a(m[54])
                                            self._compare(r.a, 30)
                                            self._mark(47611)
                                            if not r.p & C:
                                                continue
                                            else:
                                                pass
                                            self._a(m[62])
                                            self._compare(r.a, 70)
                                            self._mark(47618)
                                            if not r.p & C:
                                                self._a(m[61])
                                                self._y(4)
                                                if not (yield from self._local_call(self.officer_field_pointer, 47628, 47631)):
                                                    return
                                                m[33] = r.a
                                                self._y(11)
                                                self._a(m[(m[34] | m[35] << 8) + r.y & 65535])
                                                r.a = self._shift(r.a, False, rotate=False)
                                                r.a = self._shift(r.a, False, rotate=False)
                                                r.a = self._shift(r.a, False, rotate=False)
                                                r.a = self._shift(r.a, False, rotate=False)
                                                m[32] = r.a
                                                self._a(m[57])
                                                self._flag(C, True)
                                                self._add(m[32], subtract=True)
                                                m[57] = r.a
                                                self._y(2)
                                                self._a(m[(m[34] | m[35] << 8) + r.y & 65535])
                                                self._flag(C, False)
                                                self._add(m[33])
                                                self._a(20)
                                                m[35] = r.a
                                                self._a(0)
                                                m[34] = r.a
                                                m[36] = r.a
                                                if not (yield from self._local_call(self.divide_domestic_word, 47669, 47672)):
                                                    return
                                                self._a(m[62])
                                                self._y(0)
                                                self._compare(r.a, 31)
                                                self._mark(47679)
                                                if not r.p & C:
                                                    pass
                                                else:
                                                    self._y(r.y + 1)
                                                    self._compare(r.a, 51)
                                                    self._mark(47684)
                                                    if not r.p & C:
                                                        pass
                                                    else:
                                                        self._y(r.y + 1)
                                                        pass
                                                    pass
                                                m[32] = r.y
                                                self._a(m[DIFFICULTY])
                                                r.a = self._shift(r.a, True, rotate=False)
                                                r.a = self._shift(r.a, True, rotate=False)
                                                self._a(r.a | m[32])
                                                self._y(r.a)
                                                self._a(m[47745 + r.y & 65535])
                                                self._flag(C, False)
                                                self._add(m[33])
                                                m[42] = r.a
                                                self._a(m[57])
                                                self._mark(47708)
                                                if not r.p & N:
                                                    self._flag(C, False)
                                                    self._add(m[42])
                                                    m[42] = r.a
                                                    pass
                                                else:
                                                    self._a(r.a ^ 255)
                                                    self._flag(C, False)
                                                    self._add(1)
                                                    r.a = self._shift(r.a, True, rotate=False)
                                                    m[32] = r.a
                                                    self._a(m[42])
                                                    self._flag(C, True)
                                                    self._add(m[32], subtract=True)
                                                    m[42] = r.a
                                                    pass
                                                self._a(100)
                                                if not (yield from self._local_call(self.random_below, 47735, 47738)):
                                                    return
                                                self._compare(r.a, m[42])
                                                self._mark(47740)
                                                if not r.p & C:
                                                    self._a(m[56])
                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47760, 47763)):
                                                        return
                                                    self._y(16)
                                                    while True:
                                                        try:
                                                            self._y(r.y + 1)
                                                            self._a(m[(m[32] | m[33] << 8) + r.y & 65535])
                                                            self._compare(r.a, 255)
                                                            self._mark(47770)
                                                            if not r.p & Z:
                                                                continue
                                                            else:
                                                                pass
                                                            self._a(m[61])
                                                            m[(m[32] | m[33] << 8) + r.y & 65535] = r.a
                                                            self._a(m[RULER])
                                                            if not (yield from self._local_call(self.ruler_pointer, 47780, 47783)):
                                                                return
                                                            self._y(0)
                                                            self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                            m[48] = r.a
                                                            self._a(m[61])
                                                            m[49] = r.a
                                                            if not (yield from self._local_call(self.recalculate_recruited_loyalty, 47794, 47797)):
                                                                return
                                                            self._a(m[63])
                                                            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47800, 47803)):
                                                                return
                                                            m[66] = r.a
                                                            self._y(16)
                                                            while True:
                                                                try:
                                                                    self._y(r.y + 1)
                                                                    self._a(m[(m[32] | m[33] << 8) + r.y & 65535])
                                                                    self._compare(r.a, m[61])
                                                                    self._mark(47814)
                                                                    if not r.p & Z:
                                                                        continue
                                                                    else:
                                                                        pass
                                                                    self._a(255)
                                                                    m[(m[32] | m[33] << 8) + r.y & 65535] = r.a
                                                                    self._a(m[63])
                                                                    if not (yield from self._local_call(self.compact_city_roster, 47823, 47826)):
                                                                        return
                                                                    self._a(m[63])
                                                                    if not (yield from self._local_call(self.count_prefix_officers, 47829, 47832)):
                                                                        return
                                                                    self._compare(r.a, 0)
                                                                    self._mark(47834)
                                                                    if not r.p & Z:
                                                                        pass
                                                                    else:
                                                                        self._y(0)
                                                                        self._a(7)
                                                                        m[(m[32] | m[33] << 8) + r.y & 65535] = r.a
                                                                        pass
                                                                    self._a(m[61])
                                                                    m[67] = r.a
                                                                    self._a(m[56])
                                                                    if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47851, 47854)):
                                                                        return
                                                                    if not (yield from self._local_call(self.ruler_pointer, 47854, 47857)):
                                                                        return
                                                                    self._y(0)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    m[64] = r.a
                                                                    self._a(m[66])
                                                                    if not (yield from self._local_call(self.ruler_pointer, 47867, 47870)):
                                                                        return
                                                                    self._y(0)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    m[65] = r.a
                                                                    self._y(3)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    self._compare(r.a, 3)
                                                                    self._mark(47883)
                                                                    if r.p & Z:
                                                                        pass
                                                                    else:
                                                                        self._a(0)
                                                                        m[54] = r.a
                                                                        self._a(255)
                                                                        m[61] = r.a
                                                                        self._a(0)
                                                                        m[62] = r.a
                                                                        while True:
                                                                            try:
                                                                                self._a(m[54])
                                                                                if not (yield from self._local_call(self.city_pointer_and_resource_caps, 47903, 47906)):
                                                                                    return
                                                                                self._compare(r.a, 7)
                                                                                self._mark(47908)
                                                                                if r.p & Z:
                                                                                    pass
                                                                                else:
                                                                                    self._compare(r.a, m[66])
                                                                                    self._mark(47913)
                                                                                    if not r.p & Z:
                                                                                        pass
                                                                                    else:
                                                                                        self._a(m[65])
                                                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_bd40, 47918, 47921)):
                                                                                            return
                                                                                        pass
                                                                                    pass
                                                                                m[54] = self._nz(m[54] + 1)
                                                                                self._a(m[54])
                                                                                self._compare(r.a, 30)
                                                                                self._mark(47929)
                                                                                if not r.p & C:
                                                                                    continue
                                                                                else:
                                                                                    pass
                                                                                self._a(250)
                                                                                m[AI_REQUEST] = r.a
                                                                                while True:
                                                                                    try:
                                                                                        self._a(m[AI_REQUEST])
                                                                                        self._mark(47939)
                                                                                        if not r.p & Z:
                                                                                            continue
                                                                                        else:
                                                                                            pass
                                                                                        return (yield from self.city_development_strategy())
                                                                                    except _ContinueLoop_BB40:
                                                                                        continue
                                                                            except _ContinueLoop_BB1C:
                                                                                continue
                                                                    return (yield from self.city_development_strategy())
                                                                except _ContinueLoop_BAC0:
                                                                    continue
                                                        except _ContinueLoop_BA95:
                                                            continue
                                                else:
                                                    pass
                                                pass
                                            else:
                                                pass
                                            return (yield from self.city_development_strategy())
                                        except _ContinueLoop_B9E5:
                                            continue
                                else:
                                    pass
                                return (yield from self.city_development_strategy())
                            except _ContinueLoop_B99B:
                                continue
                    else:
                        self._a(m[RULER])
                        if not (yield from self._local_call(self.ruler_pointer, 46620, 46623)):
                            return
                        self._y(0)
                        self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                        m[64] = r.a
                        if not (yield from self._local_call(self.domesticcooperationcontroller_b837, 46630, 46633)):
                            return
                        self._a(m[61])
                        self._compare(r.a, 255)
                        self._mark(46638)
                        if r.p & Z:
                            pass
                        else:
                            m[66] = r.a
                            self._a(0)
                            m[42] = r.a
                            m[43] = r.a
                            while True:
                                try:
                                    self._a(m[42])
                                    if not (yield from self._local_call(self.ruler_pointer, 46651, 46654)):
                                        return
                                    self._y(0)
                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                    self._compare(r.a, 255)
                                    self._mark(46660)
                                    if r.p & Z:
                                        pass
                                    else:
                                        m[43] = self._nz(m[43] + 1)
                                        pass
                                    m[42] = self._nz(m[42] + 1)
                                    self._a(m[42])
                                    self._compare(r.a, 7)
                                    self._mark(46670)
                                    if not r.p & C:
                                        continue
                                    else:
                                        pass
                                    self._a(m[43])
                                    self._compare(r.a, 3)
                                    self._mark(46676)
                                    if r.p & C:
                                        self._a(m[RULER])
                                        if not (yield from self._local_call(self.ruler_pointer, 46684, 46687)):
                                            return
                                        self._x(0)
                                        self._y(4)
                                        self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                        self._y(5)
                                        self._flag(C, False)
                                        self._add(m[(m[36] | m[37] << 8) + r.y & 65535])
                                        self._y(6)
                                        self._flag(C, False)
                                        self._add(m[(m[36] | m[37] << 8) + r.y & 65535])
                                        self._y(7)
                                        self._flag(C, False)
                                        self._add(m[(m[36] | m[37] << 8) + r.y & 65535])
                                        self._compare(r.a, 0)
                                        self._mark(46710)
                                        if not r.p & Z:
                                            pass
                                        else:
                                            if not (yield from self._local_call(self.domesticcooperationcontroller_b898, 46712, 46715)):
                                                return
                                            self._compare(r.x, 2)
                                            self._mark(46717)
                                            if not r.p & C:
                                                pass
                                            else:
                                                self._y(0)
                                                m[54] = r.y
                                                m[55] = r.y
                                                m[56] = r.y
                                                while True:
                                                    try:
                                                        self._y(m[54])
                                                        self._a(m[28531 + r.y & 65535])
                                                        self._mark(46736)
                                                        if not r.p & Z:
                                                            pass
                                                        else:
                                                            self._a(m[54])
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d080, 46741, 46744)):
                                                                return
                                                            self._a(m[43])
                                                            self._compare(r.a, m[55])
                                                            self._mark(46749)
                                                            if not r.p & C:
                                                                pass
                                                            else:
                                                                m[55] = r.a
                                                                self._a(m[54])
                                                                m[56] = r.a
                                                                pass
                                                            pass
                                                        m[54] = self._nz(m[54] + 1)
                                                        self._a(m[54])
                                                        self._compare(r.a, 7)
                                                        self._mark(46768)
                                                        if not r.p & C:
                                                            continue
                                                        else:
                                                            pass
                                                        self._a(m[RULER])
                                                        if not (yield from self._local_call(self.domesticcooperationcontroller_d080, 46773, 46776)):
                                                            return
                                                        self._a(m[43])
                                                        self._flag(C, False)
                                                        self._add(2)
                                                        self._compare(r.a, m[55])
                                                        self._mark(46784)
                                                        if not r.p & C:
                                                            self._a(m[55])
                                                            m[32] = r.a
                                                            self._a(30)
                                                            m[33] = r.a
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_d471, 46798, 46801)):
                                                                return
                                                            self._a(m[42])
                                                            self._flag(C, False)
                                                            self._add(70)
                                                            m[33] = r.a
                                                            self._a(m[43])
                                                            self._add(0)
                                                            m[34] = r.a
                                                            self._a(10)
                                                            m[35] = r.a
                                                            self._a(0)
                                                            m[36] = r.a
                                                            if not (yield from self._local_call(self.divide_domestic_word, 46822, 46825)):
                                                                return
                                                            self._a(m[33])
                                                            m[1071] = r.a
                                                            self._a(m[34])
                                                            m[1072] = r.a
                                                            m[1071] = self._shift(m[1071], True, rotate=False)
                                                            m[1072] = self._shift(m[1072], True, rotate=True)
                                                            m[1071] = self._shift(m[1071], True, rotate=False)
                                                            m[1072] = self._shift(m[1072], True, rotate=True)
                                                            self._a(0)
                                                            m[1073] = r.a
                                                            self._a(0)
                                                            m[57] = r.a
                                                            self._a(100)
                                                            if not (yield from self._local_call(self.random_below, 46859, 46862)):
                                                                return
                                                            self._compare(r.a, 50)
                                                            self._mark(46864)
                                                            if not r.p & C:
                                                                pass
                                                            else:
                                                                self._a(1)
                                                                m[57] = r.a
                                                                self._a(m[33])
                                                                m[32] = r.a
                                                                self._a(m[34])
                                                                m[33] = r.a
                                                                self._a(0)
                                                                m[34] = r.a
                                                                self._a(6)
                                                                m[35] = r.a
                                                                if not (yield from self._local_call(self.multiply_domestic_word, 46887, 46890)):
                                                                    return
                                                                self._a(m[38])
                                                                m[1071] = r.a
                                                                self._a(m[39])
                                                                m[1072] = r.a
                                                                self._a(0)
                                                                m[1073] = r.a
                                                                pass
                                                            self._a(m[1071])
                                                            m[58] = r.a
                                                            self._a(m[1073])
                                                            m[59] = r.a
                                                            if not (yield from self._local_call(self.domesticcooperationcontroller_b7a2, 46918, 46921)):
                                                                return
                                                            self._mark(46921)
                                                            if r.p & C:
                                                                self._a(m[56])
                                                                if not (yield from self._local_call(self.ruler_pointer, 46929, 46932)):
                                                                    return
                                                                self._y(3)
                                                                self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                self._compare(r.a, 3)
                                                                self._mark(46938)
                                                                if not r.p & Z:
                                                                    self._a(m[RULER])
                                                                    if not (yield from self._local_call(self.ruler_pointer, 46952, 46955)):
                                                                        return
                                                                    self._y(0)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    m[64] = r.a
                                                                    self._a(m[56])
                                                                    if not (yield from self._local_call(self.ruler_pointer, 46965, 46968)):
                                                                        return
                                                                    self._y(0)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    m[65] = r.a
                                                                    self._y(3)
                                                                    self._a(m[(m[36] | m[37] << 8) + r.y & 65535])
                                                                    m[28484] = r.a
                                                                    self._a(248)
                                                                    m[AI_REQUEST] = r.a
                                                                    while True:
                                                                        try:
                                                                            self._a(m[AI_REQUEST])
                                                                            self._compare(r.a, 248)
                                                                            self._mark(46992)
                                                                            if r.p & Z:
                                                                                continue
                                                                            else:
                                                                                pass
                                                                            self._compare(r.a, 0)
                                                                            self._mark(46996)
                                                                            if r.p & Z:
                                                                                if not (yield from self._local_call(self.domesticcooperationcontroller_b90a, 47001, 47004)):
                                                                                    return
                                                                                if not (yield from self._local_call(self.domesticcooperationcontroller_b7ce, 47004, 47007)):
                                                                                    return
                                                                                pass
                                                                            else:
                                                                                pass
                                                                            return (yield from self.city_development_strategy())
                                                                        except _ContinueLoop_B78B:
                                                                            continue
                                                                else:
                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b90a, 46940, 46943)):
                                                                        return
                                                                    if not (yield from self._local_call(self.domesticcooperationcontroller_b7ce, 46943, 46946)):
                                                                        return
                                                                    pass
                                                                pass
                                                            else:
                                                                pass
                                                            pass
                                                        else:
                                                            pass
                                                        return (yield from self.city_development_strategy())
                                                    except _ContinueLoop_B68A:
                                                        continue
                                            pass
                                        pass
                                    else:
                                        pass
                                    return (yield from self.city_development_strategy())
                                except _ContinueLoop_B639:
                                    continue
                        pass
                    pass
                return (yield from self.city_development_strategy())
            except _ContinueLoop_B5FC:
                continue
