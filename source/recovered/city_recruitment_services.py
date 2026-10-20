"""Named city appearance and unaffiliated recruitment, physical11 C5B9..C794.

The original owner/status/year/capacity/probability and location checks execute
in their original order. An existing caller stack is mandatory. Exact fixed
services remain real dependencies; no CPU, IR, fake RNG or reply runs here.
The ordinary no-interrupt E89A contract preserves X via0053. The source retains
the actual returned X and byte-index loop rather than assuming IRQ timing.
"""
from dataclasses import dataclass
from .negotiation_services import NegotiationServices
from .domestic_cooperation_controller import UIRegisters, ROM_SHA256, C, Z, N, RULER, DIFFICULTY, YEAR
from .battle_nmi_services import ServiceWait
from .domestic_secondary_services import SecondaryRequestWait

@dataclass
class RecruitmentRosterWait(ServiceWait):
    """One complete eight-bit Y search found no FF; no terminator is invented."""

class CityRecruitmentServices(NegotiationServices):
    PUBLIC_ENTRIES=NegotiationServices.PUBLIC_ENTRIES+(0xC5B9,0xC5D2,0xC66F,0xC6CC)
    LOCAL_ENTRIES=NegotiationServices.LOCAL_ENTRIES+(0xC71A,0xC765)

    def _entry(self,entry):
        if entry==0xC5B9:return self.search_and_recruit_preparation()
        if entry==0xC5D2:return self.recruit_appearing_officers()
        if entry==0xC66F:return self.recruitment_probability()
        if entry==0xC6CC:return self.recruit_unaffiliated_officers()
        if entry==0xC71A:return self.scan_unaffiliated_officers()
        if entry==0xC765:return self.commit_unaffiliated_recruitment()
        return super()._entry(entry)

    def _drive(self):
        if isinstance(self.pending,RecruitmentRosterWait):self.pending=None
        while True:
            if self.pending is not None:
                call=self.pending
                if isinstance(call,SecondaryRequestWait):
                    value=self.memory[call.address]
                    blocked=value==call.value if call.condition=='not_equal'else value!=call.value
                    if blocked:return self._result('waiting')
                    self.pending=None
                elif isinstance(call,ServiceWait):
                    if self.memory[call.address]!=call.value:return self._result('waiting')
                    self.pending=None
                else:
                    if self.services is None:return self._result('dependency')
                    result=self.services(call)
                    if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                    if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                    self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                return self._result('returned'if(self.registers.pc,self.registers.sp)==(self._return_pc,self._return_sp)else'nonlocal_return')
            if isinstance(self.pending,RecruitmentRosterWait):return self._result('waiting')

    def search_and_recruit_preparation(self):
        """C5B9: scan30 cities; success in C6CC skips the remaining city scan."""
        r,m=self.registers,self.memory;self._mark(0xC5B9);self._a(0);m[0x36]=r.a
        while True:
            self._mark(0xC5BE)
            if not(yield from self._local_call(self.recruit_appearing_officers,0xC5BE,0xC5C1)):return
            if not(yield from self._local_call(self.recruit_unaffiliated_officers,0xC5C1,0xC5C4)):return
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        if not(yield from self._local_call(self.find_ruler_city,0xC5CE,0xC5D1)):return
        self._mark(0xC5D1);self._rts()

    def recruitment_probability(self):
        """C66F:90 for listed officer/ruler pair, otherwise10; X is untouched."""
        r,m=self.registers,self.memory;self._mark(0xC66F);self._y(m[RULER]);self._compare(r.y,4)
        if r.p&Z:preferred=(109,112,55,183,144)
        else:
            self._y(m[RULER]);self._compare(r.y,2)
            if r.p&Z:preferred=(86,99,57,165,156)
            else:
                self._y(m[RULER]);self._compare(r.y,3)
                if not r.p&Z:
                    self._a(10);self._mark(0xC68C);self._rts();return
                preferred=(107,234,235,213,47)
        for officer in preferred:
            self._compare(r.a,officer)
            if r.p&Z:
                self._a(90);self._mark(0xC68F);self._rts();return
        self._a(10);self._mark(0xC68C);self._rts()
        if False:yield None

    def recruit_appearing_officers(self):
        """C5D2: owned city,10% gate, prefix capacity, original year/ID table.

        Table pairs are read from the actual mapped bank17 data window. The
        year gate is CMP against(raw yearbyte-100)&255; there is no guessed
        ten-pair terminator. Status1 is changed to2 and ID appended at firstFF.
        """
        r,m=self.registers,self.memory;self._mark(0xC5D2);self._y(49)
        yield from self._external(0xC5D4,0xF266,0xC5D7,'call')
        if r.pc!=0xC5D7:return
        self._a(m[0x36])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xC5DA,0xC5DD)):return
        self._a(r.a&7);self._compare(r.a,m[RULER])
        if not r.p&Z:self._mark(0xC5ED);self._rts();return
        self._a(100)
        if not(yield from self._local_call(self.random_below,0xC5E6,0xC5E9)):return
        self._compare(r.a,10)
        if r.p&C:self._mark(0xC5ED);self._rts();return
        self._a(m[0x36])
        if not(yield from self._local_call(self.count_prefix_officers,0xC5F1,0xC5F4)):return
        self._compare(r.a,10)
        if r.p&C:self._mark(0xC5ED);self._rts();return
        self._a(m[0x36]);m[0x20]=r.a;self._a(20);m[0x21]=r.a
        if not(yield from self._local_call(self.domesticcooperationcontroller_d471,0xC601,0xC604)):return
        self._a(0);m[0x37]=r.a;self._a(m[0x2A]);self._flag(C,False);self._add(28);m[0x22]=r.a
        self._a(m[0x2B]);self._add(139);m[0x23]=r.a
        while True:
            self._mark(0xC616);self._y(m[0x37]);m[0x37]=self._nz(m[0x37]+1);m[0x37]=self._nz(m[0x37]+1)
            self._a(self._officer_byte(r.y));m[0x24]=r.a;self._y(r.y+1)
            self._a(self._officer_byte(r.y));self._flag(C,True);self._add(100,subtract=True);m[0x20]=r.a
            self._a(m[YEAR]);self._compare(r.a,m[0x20])
            if not r.p&C:self._mark(0xC66E);self._rts();return
            self._a(m[0x24]);self._y(11)
            if not(yield from self._local_call(self.domesticcooperationcontroller_d283,0xC636,0xC639)):return
            self._a(r.a&3);self._compare(r.a,1)
            if not r.p&Z:continue
            self._a(m[0x24])
            if not(yield from self._local_call(self.recruitment_probability,0xC641,0xC644)):return
            m[0x2A]=r.a
            while True:
                self._mark(0xC646);yield from self._external(0xC646,0xE89A,0xC649,'call')
                if r.pc!=0xC649:return
                self._compare(r.a,100)
                if not r.p&C:break
            self._compare(r.a,m[0x2A])
            if r.p&C:continue
            self._y(11);self._a(self._city_byte(r.y));self._a(r.a&252);self._a(r.a|2)
            self._write_city_byte(r.y,r.a)
            self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xC65E,0xC661)):return
            self._y(16)
            yield from self._find_roster_vacancy(0xC663)
            self._a(m[0x24]);self._write_city_byte(r.y,r.a);self._mark(0xC66E);self._rts();return

    def recruit_unaffiliated_officers(self):
        """C6CC: capacity and difficulty chance before map-neighbor preparation."""
        r,m=self.registers,self.memory;self._mark(0xC6CC);self._a(m[0x36])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xC6CF,0xC6D2)):return
        self._a(r.a&7);self._compare(r.a,m[RULER])
        if not r.p&Z:self._mark(0xC6D9);self._rts();return
        self._a(100)
        if not(yield from self._local_call(self.random_below,0xC6DC,0xC6DF)):return
        self._y(m[DIFFICULTY]);self._compare(r.a,m[0xC795+r.y])
        if r.p&C:self._mark(0xC6D9);self._rts();return
        self._a(m[0x36])
        if not(yield from self._local_call(self.count_prefix_officers,0xC6EA,0xC6ED)):return
        self._compare(r.a,10)
        if r.p&C:self._mark(0xC6D9);self._rts();return
        self._a(0);m[0x37]=r.a;self._y(48)
        yield from self._external(0xC6F8,0xF266,0xC6FB,'call')
        if r.pc!=0xC6FB:return
        self._y(15);self._a(255)
        while True:
            m[0x6F73+r.y]=r.a;self._y(r.y-1)
            if r.p&N:break
        self._a(m[0x36])
        for _ in range(3):r.a=self._shift(r.a,True)
        self._y(r.a);self._x(0)
        while True:
            self._a(m[0x9D72+r.y]);m[0x6F73+r.x]=r.a;self._y(r.y+1);self._x(r.x+1);self._compare(r.x,8)
            if r.p&C:break
        return(yield from self.scan_unaffiliated_officers())

    def scan_unaffiliated_officers(self):
        """C71A: normally237 records; preserve raw X after actual RNG service.

        Pointer22 advances12 independently of X. With the ordinary no-IRQ
        callee contract, X visits0..236 and no outside-record scan is needed.
        The loop is written in returned byte X, not an invented unconditional
        for237 bound. HP and residence are not modified by the success path.
        """
        r,m=self.registers,self.memory;self._mark(0xC71A);self._a(192);m[0x22]=r.a;self._a(99);m[0x23]=r.a;self._x(0)
        while True:
            self._mark(0xC724);self._y(11);self._a(self._officer_byte(r.y));self._a(r.a&3)
            if r.p&Z:
                self._a(r.x)
                if not(yield from self._local_call(self.recruitment_probability,0xC72D,0xC730)):return
                m[0x2A]=r.a
                while True:
                    self._mark(0xC732);yield from self._external(0xC732,0xE89A,0xC735,'call')
                    if r.pc!=0xC735:return
                    self._compare(r.a,100)
                    if not r.p&C:break
                self._compare(r.a,m[0x2A])
                if not r.p&C:
                    self._y(5);self._a(self._officer_byte(r.y));self._compare(r.a,m[0x36])
                    qualifies=bool(r.p&Z)
                    if not qualifies:
                        self._y(0)
                        while True:
                            self._compare(r.a,m[0x6F73+r.y])
                            if r.p&Z:qualifies=True;break
                            self._y(r.y+1);self._compare(r.y,8)
                            if r.p&C:break
                    if qualifies:return(yield from self.commit_unaffiliated_recruitment())
            self._a(m[0x22]);self._flag(C,False);self._add(12);m[0x22]=r.a
            self._a(m[0x23]);self._add(0);m[0x23]=r.a;self._x(r.x+1);self._compare(r.x,237)
            if r.p&C:self._mark(0xC764);self._rts();return

    def _find_roster_vacancy(self,pc):
        r=self.registers
        while True:
            for _ in range(256):
                self._mark(pc);self._y(r.y+1);self._a(self._city_byte(r.y));self._compare(r.a,255)
                if r.p&Z:return
            r.pc=pc
            yield RecruitmentRosterWait('city_roster_without_FF',pc,reason='A complete original Y cycle found no FF; no capacity or terminator is fabricated',expected_sp=r.sp)

    def commit_unaffiliated_recruitment(self):
        """C765: status2, firstFF append, loyalty, discard C6CC caller frame."""
        r,m=self.registers,self.memory;self._mark(0xC765);self._y(11);self._a(self._officer_byte(r.y));self._a(r.a&252);self._a(r.a|2)
        self._write_officer_byte(r.y,r.a);self._a(m[0x36])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xC772,0xC775)):return
        self._y(16);yield from self._find_roster_vacancy(0xC777)
        self._a(r.x);self._write_city_byte(r.y,r.a);m[0x31]=r.a
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xC786,0xC789)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x30]=r.a
        if not(yield from self._local_call(self.recalculate_recruited_loyalty,0xC78F,0xC792)):return
        self._a(self._pop());self._a(self._pop());self._mark(0xC794);self._rts()

    # Ordinary bound-method aliases, for the corresponding recovered callers.
    domesticcooperationcontroller_c5b9=search_and_recruit_preparation
    domesticcooperationcontroller_c5d2=recruit_appearing_officers
    domesticcooperationcontroller_c66f=recruitment_probability
    domesticcooperationcontroller_c6cc=recruit_unaffiliated_officers
