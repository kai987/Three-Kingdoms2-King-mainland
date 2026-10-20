"""Exact city pointer, resource caps and payment around the opaque+1 gate.

The already recovered BD7A consumer remains frozen. Its real virtual calls
use these independently named helpers, including D105's resource caps before
BD97 reads the overlapping LE16(city+1,city+2). No formal name for+1 is assumed.
"""
from .city_recruitment_services import CityRecruitmentServices
from .domestic_cooperation_controller import UIRegisters,ROM_SHA256,C,Z,N

class CityThresholdServices(CityRecruitmentServices):
    PUBLIC_ENTRIES=CityRecruitmentServices.PUBLIC_ENTRIES+(0xD105,0xD36F,0xD69D)

    def _entry(self,entry):
        if entry==0xD105:return self.city_pointer_and_resource_caps()
        if entry==0xD36F:return self.pay_city_gold()
        if entry==0xD69D:return self.cap_city_word()
        return super()._entry(entry)

    def threshold_snapshot(self,city):
        """Read-only explanation of the complete D105-before-BD97 data rule.

        Valid city0..29 only for this inspection API. It neither executes the
        caller nor mutates resource bytes. The CPU-form helpers retain raw8
        indexing and exact side effects, and have separate contracts.
        """
        if not isinstance(city,int)or isinstance(city,bool)or not 0<=city<30:raise ValueError('Inspection requires an actual city0..29')
        m=self.memory;b=0x6000+32*city;aux=m[b+1];gold=m[b+2]|m[b+3]<<8
        after=min(gold,9999);low=after&255;word=aux|(low<<8)
        return dict(city=city,city_base=b,owner_low3=m[b]&7,opaque_byte1=aux,
                    gold_before_D105=gold,gold_after_D105=after,
                    overlapping_word_after_D105=word,BD97_gate_passes=word>=300,
                    predicate='gold_low>=2 or(gold_low==1 and opaque_byte1>=44)',
                    official_name_of_byte1=None,changes_memory=False)

    def city_pointer_and_resource_caps(self):
        """11 D105:6000+32*rawA, cap actual gold/grain, returnowner&7.

        The original five ASL/ROL pairs retain all scratch/flags. D123's real
        JSR frame is preserved even when neither resource needs a write.
        """
        r,m=self.registers,self.memory;self._mark(0xD105);self._y(0);m[0x21]=r.y
        for _ in range(5):
            r.a=self._shift(r.a,True);m[0x21]=self._shift(m[0x21],True,rotate=True)
        self._flag(C,False);self._add(0);m[0x20]=r.a
        self._a(m[0x21]);self._add(0x60);m[0x21]=r.a
        if not(yield from self._local_call(self.cap_city_word,0xD123,0xD126)):return
        self._y(0);self._a(self._city_byte(r.y));self._a(r.a&7);self._mark(0xD12C);self._rts()

    def cap_city_word(self):
        """11 D69D: sequentially clamp gold(+2/3) and grain(+4/5) to9999.

        It reads both bytes and compares against10000. Gold writes finish
        before grain is read; low is written before high. No write touches+1.
        Read/flag/alias effects are retained rather than replacing this with
        a bulk min assignment. In particular, a failed later payment does not
        undo these earlier resource caps.
        """
        r=self.registers;self._mark(0xD69D)
        for field in(2,4):
            self._y(field);self._a(self._city_byte(r.y));self._flag(C,True);self._add(0x10,subtract=True)
            self._y(r.y+1);self._a(self._city_byte(r.y));self._add(0x27,subtract=True)
            if r.p&C:
                self._y(field);self._a(0x0F);self._write_city_byte(r.y,r.a)
                self._y(r.y+1);self._a(0x27);self._write_city_byte(r.y,r.a)
        self._mark(0xD6CF);self._rts()
        if False:yield None

    def pay_city_gold(self):
        """11 D36F: cap, optional random fee, recalc/cap, subtract or refuse.

        A is rawcity,22/23 requestedword,24 optional positive RNG bound. The
        optional sample is added with16bit wrap. Failure preserves the capped
        resource balance and returnsCLC; it still leaves the actual fee/RNG,
        pointer/scratch and stack effects. Success writes high then low, caps
        again and returnsSEC. BD7A itself ignores this returned carry.
        """
        r,m=self.registers,self.memory;self._mark(0xD36F);self._push(r.a)
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xD370,0xD373)):return
        self._a(m[0x24])
        if not r.p&Z:
            if not(yield from self._local_call(self.random_below,0xD377,0xD37A)):return
            self._flag(C,False);self._add(m[0x22]);m[0x22]=r.a
            self._a(m[0x23]);self._add(0);m[0x23]=r.a
        self._a(self._pop())
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xD386,0xD389)):return
        if not(yield from self._local_call(self.cap_city_word,0xD389,0xD38C)):return
        self._y(2);self._a(self._city_byte(r.y));self._flag(C,True);self._add(m[0x22],subtract=True);self._push(r.a)
        self._y(r.y+1);self._a(self._city_byte(r.y));self._add(m[0x23],subtract=True)
        if not r.p&C:
            self._a(self._pop());self._flag(C,False);self._mark(0xD39D);self._rts();return
        self._write_city_byte(r.y,r.a);self._y(r.y-1);self._a(self._pop());self._write_city_byte(r.y,r.a)
        if not(yield from self._local_call(self.cap_city_word,0xD3A4,0xD3A7)):return
        self._flag(C,True);self._mark(0xD3A8);self._rts()
