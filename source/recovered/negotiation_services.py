"""Named resource, envoy, border and alliance services for original F8 flow.

These additive algorithms retain original scratch bytes, flags and real call
frames. They never choose a random sample, clear a request, or synthesize UI
readiness. Historical phase19 decision and waiting owners remain unchanged.
"""
from .domestic_secondary_services import DomesticSecondaryServices, UIRegisters, ROM_SHA256
from .domestic_cooperation_controller import C, Z, N, RULER


class NegotiationServices(DomesticSecondaryServices):
    PUBLIC_ENTRIES = DomesticSecondaryServices.PUBLIC_ENTRIES + (
        0xB7A2, 0xB7CE, 0xB837, 0xB85F, 0xB898, 0xB90A, 0xB923, 0xB955, 0xD080, 0xD307)

    def _entry(self, entry):
        if entry == 0xB7A2: return self.check_full_quoted_resource()
        if entry == 0xB7CE: return self.transfer_committed_resource()
        if entry == 0xB837: return self.choose_negotiation_envoy()
        if entry == 0xB85F: return self.consider_city_envoys()
        if entry == 0xB898: return self.collect_neighboring_rulers()
        if entry == 0xB90A: return self.set_reciprocal_alliance_nibbles()
        if entry == 0xB923: return self.set_target_alliance_nibble()
        if entry == 0xB955: return self.find_leaders_city()
        if entry == 0xD080: return self.count_owned_cities_and_prefix_officers()
        if entry == 0xD307: return self.count_current_city_prefix()
        return super()._entry(entry)

    def check_full_quoted_resource(self):
        """B7A2: current leader's city must afford full 042F/0430 quote.

        Mode zero selects gold+2; every nonzero raw mode selects grain+4.
        The read-only subtraction leaves the original final carry and A/Y.
        D105 still caps selected cities as the original pointer service does.
        """
        r, m = self.registers, self.memory
        self._mark(0xB7A2); self._a(m[RULER])
        if not (yield from self._local_call(self.find_leaders_city, 0xB7A5, 0xB7A8)): return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB7A8, 0xB7AB)): return
        self._a(m[0x39]); self._y(4 if not r.p & Z else 2)
        self._a(self._city_byte(r.y)); self._flag(C, True)
        self._add(m[0x42F], subtract=True); self._y(r.y + 1)
        self._a(self._city_byte(r.y)); self._add(m[0x430], subtract=True)
        self._mark(0xB7CD if m[0x39] else 0xB7BE); self._rts()

    def transfer_committed_resource(self):
        """B7CE: debit own leader city, then credit chosen ruler's leader city.

        This uses 003A/003B, which F8's producer populated with the quote's
        low byte and zero0431. It does not repair that original truncation.
        Neither side is recapped after the actual 16bit subtraction/addition.
        """
        r, m = self.registers, self.memory
        self._mark(0xB7CE); self._a(m[RULER])
        if not (yield from self._local_call(self.find_leaders_city, 0xB7D1, 0xB7D4)): return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB7D4, 0xB7D7)): return
        self._a(m[0x39]); self._y(4 if not r.p & Z else 2)
        self._a(self._city_byte(r.y)); self._flag(C, True)
        self._add(m[0x3A], subtract=True); self._write_city_byte(r.y, r.a)
        self._y(r.y + 1); self._a(self._city_byte(r.y))
        self._add(m[0x3B], subtract=True); self._write_city_byte(r.y, r.a)
        self._a(m[0x38])
        if not (yield from self._local_call(self.find_leaders_city, 0xB806, 0xB809)): return
        if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB809, 0xB80C)): return
        self._a(m[0x39]); self._y(4 if not r.p & Z else 2)
        self._a(self._city_byte(r.y)); self._flag(C, False)
        self._add(m[0x3A]); self._write_city_byte(r.y, r.a)
        self._y(r.y + 1); self._a(self._city_byte(r.y))
        self._add(m[0x3B]); self._write_city_byte(r.y, r.a)
        self._mark(0xB836 if m[0x39] else 0xB823); self._rts()

    def choose_negotiation_envoy(self):
        """B837: scan 30 owned cities; later ties in loyalty win."""
        r, m = self.registers, self.memory
        self._mark(0xB837); self._a(0); m[0x36] = r.a
        self._a(255); m[0x3D] = r.a; self._a(0); m[0x3E] = r.a
        while True:
            self._mark(0xB846); self._a(m[0x36])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB849, 0xB84C)): return
            self._compare(r.a, m[RULER])
            if r.p & Z:
                if not (yield from self._local_call(self.consider_city_envoys, 0xB851, 0xB854)): return
            m[0x36] = self._nz(m[0x36] + 1); self._a(m[0x36]); self._compare(r.a, 30)
            if r.p & C: break
        self._mark(0xB85E); self._rts()

    def consider_city_envoys(self):
        """B85F: all ten slots, FF holes skipped; leader40 is excluded."""
        r, m = self.registers, self.memory
        self._mark(0xB85F); self._a(m[0x36])
        if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB862, 0xB865)): return
        self._a(17); m[0x3C] = r.a
        while True:
            self._mark(0xB86A); self._y(m[0x3C]); self._a(self._city_byte(r.y)); self._compare(r.a, 255)
            if not r.p & Z:
                self._compare(r.a, m[0x40])
                if not r.p & Z:
                    self._y(3)
                    if not (yield from self._local_call(self.officer_field_pointer, 0xB87A, 0xB87D)): return
                    self._compare(r.a, m[0x3E])
                    if r.p & C:
                        m[0x3E] = r.a; self._y(m[0x3C]); self._a(self._city_byte(r.y)); m[0x3D] = r.a
            m[0x3C] = self._nz(m[0x3C] + 1); self._a(m[0x3C]); self._compare(r.a, 27)
            if r.p & C: break
        self._mark(0xB897); self._rts()

    def collect_neighboring_rulers(self):
        """B898: 8-wide ROM adjacency table; seven owner flags and count X.

        The first negative neighbor byte terminates that city's list. Neutral
        owner7 and own ruler are ignored. Scratch39 counts entries of each
        city; flag6F73+owner is zero exactly for a neighboring foreign ruler.
        """
        r, m = self.registers, self.memory
        self._mark(0xB898); self._y(0x30)
        yield from self._external(0xB89A, 0xF266, 0xB89D, 'call')
        if r.pc != 0xB89D: return
        self._y(7)
        while True:
            self._a(255); m[0x6F73 + r.y] = r.a; self._y(r.y - 1)
            if r.p & N: break
        self._a(0); m[0x36] = r.a; m[0x37] = r.a
        while True:
            self._mark(0xB8AF); self._a(0); m[0x39] = r.a; self._a(m[0x36])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB8B7, 0xB8BA)): return
            self._compare(r.a, m[RULER])
            if r.p & Z:
                self._a(m[0x36])
                for _ in range(3): r.a = self._shift(r.a, True)
                self._y(r.a)
                while True:
                    self._mark(0xB8C6); self._a(m[0x9D72 + r.y])
                    if r.p & N: break
                    m[0x23] = r.a; m[0x24] = r.y
                    if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB8CF, 0xB8D2)): return
                    self._compare(r.a, 7)
                    if not r.p & Z:
                        self._compare(r.a, m[RULER])
                        if not r.p & Z:
                            self._y(r.a); self._a(0); m[0x6F73 + r.y] = r.a
                    self._a(m[0x23]); self._y(m[0x24]); self._y(r.y + 1)
                    m[0x39] = self._nz(m[0x39] + 1); self._x(m[0x39]); self._compare(r.x, 8)
                    if r.p & C: break
            m[0x36] = self._nz(m[0x36] + 1); self._a(m[0x36]); self._compare(r.a, 30)
            if r.p & C: break
        self._y(0); self._x(0)
        while True:
            self._mark(0xB8FE); self._a(m[0x6F73 + r.y])
            if r.p & Z: self._x(r.x + 1)
            self._y(r.y + 1); self._compare(r.y, 7)
            if r.p & C: break
        self._mark(0xB909); self._rts()

    def set_reciprocal_alliance_nibbles(self):
        """B90A: set each ruler's packed alliance counter toward the other to10."""
        r, m = self.registers, self.memory
        self._mark(0xB90A); self._a(m[RULER])
        if not (yield from self._local_call(self.ruler_pointer, 0xB90D, 0xB910)): return
        self._a(m[0x38])
        if not (yield from self._local_call(self.set_target_alliance_nibble, 0xB913, 0xB916)): return
        self._a(m[0x38])
        if not (yield from self._local_call(self.ruler_pointer, 0xB919, 0xB91C)): return
        self._a(m[RULER])
        if not (yield from self._local_call(self.set_target_alliance_nibble, 0xB91F, 0xB922)): return
        self._mark(0xB922); self._rts()

    def set_target_alliance_nibble(self):
        """B923: valid targets0..6 pack two per byte; raw>=6 uses low7."""
        r, m = self.registers, self.memory
        self._mark(0xB923); self._y(4)
        for even in (0, 2, 4):
            self._compare(r.a, even)
            if r.p & Z: break
            self._compare(r.a, even + 1)
            if r.p & Z:
                self._a(self._ruler_byte(r.y)); self._a(r.a & 15); self._a(r.a | 160)
                m[((m[0x24] | m[0x25] << 8) + r.y) & 65535] = r.a
                self._mark(0xB954); self._rts(); return
            self._y(r.y + 1)
        self._a(self._ruler_byte(r.y)); self._a(r.a & 240); self._a(r.a | 10)
        m[((m[0x24] | m[0x25] << 8) + r.y) & 65535] = r.a
        self._mark(0xB94B); self._rts()
        if False: yield None

    def find_leaders_city(self):
        """B955: leader belongs to a ten-slot roster of a matching owner."""
        r, m = self.registers, self.memory
        self._mark(0xB955); m[0x2C] = r.a; self._y(0); m[0x2B] = r.y
        if not (yield from self._local_call(self.ruler_pointer, 0xB95B, 0xB95E)): return
        self._y(0); self._a(self._ruler_byte(r.y)); m[0x2A] = r.a
        while True:
            self._mark(0xB964); self._a(m[0x2B])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xB966, 0xB969)): return
            self._a(r.a & 7); self._compare(r.a, m[0x2C])
            if r.p & Z:
                self._y(17)
                while True:
                    self._a(self._city_byte(r.y)); self._compare(r.a, m[0x2A])
                    if r.p & Z:
                        self._a(m[0x2B]); self._mark(0xB979); self._rts(); return
                    self._y(r.y + 1); self._compare(r.y, 27)
                    if r.p & C: break
            m[0x2B] = self._nz(m[0x2B] + 1); self._a(m[0x2B]); self._compare(r.a, 30)
            if r.p & C: break
        self._a(255); self._flag(C, False); self._mark(0xB98A); self._rts()

    def count_owned_cities_and_prefix_officers(self):
        """D080: owner low3 equals raw input; count cities2B and prefix total2C."""
        r, m = self.registers, self.memory
        self._mark(0xD080); m[0x2F] = r.a; self._a(0); m[0x2A] = m[0x2B] = m[0x2C] = r.a
        while True:
            self._mark(0xD08A); self._a(m[0x2A])
            if not (yield from self._local_call(self.city_pointer_and_resource_caps, 0xD08C, 0xD08F)): return
            self._a(r.a & 7); self._compare(r.a, m[0x2F])
            if r.p & Z:
                if not (yield from self._local_call(self.count_current_city_prefix, 0xD095, 0xD098)): return
                self._flag(C, False); self._add(m[0x2C]); m[0x2C] = r.a; m[0x2B] = self._nz(m[0x2B] + 1)
            m[0x2A] = self._nz(m[0x2A] + 1); self._a(m[0x2A]); self._compare(r.a, 30)
            if r.p & C: break
        self._a(m[0x2B]); self._mark(0xD0A9); self._rts()

    def count_current_city_prefix(self):
        """D307: stop at first FF, otherwise all ten slots; return A=X."""
        r = self.registers
        self._mark(0xD307); self._x(0); self._y(17)
        while True:
            self._a(self._city_byte(r.y)); self._compare(r.a, 255)
            if r.p & Z: break
            self._x(r.x + 1); self._y(r.y + 1); self._compare(r.y, 27)
            if r.p & C: break
        self._a(r.x); self._mark(0xD318); self._rts()
        if False: yield None

    # Compatibility names are direct method aliases, not a runtime PC/IR table.
    domesticcooperationcontroller_b7a2 = check_full_quoted_resource
    domesticcooperationcontroller_b7ce = transfer_committed_resource
    domesticcooperationcontroller_b837 = choose_negotiation_envoy
    domesticcooperationcontroller_b85f = consider_city_envoys
    domesticcooperationcontroller_b898 = collect_neighboring_rulers
    domesticcooperationcontroller_b90a = set_reciprocal_alliance_nibbles
    domesticcooperationcontroller_b923 = set_target_alliance_nibble
    domesticcooperationcontroller_b955 = find_leaders_city
    domesticcooperationcontroller_d080 = count_owned_cities_and_prefix_officers
    domesticcooperationcontroller_d307 = count_current_city_prefix
