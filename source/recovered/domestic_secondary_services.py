"""Named direct algorithms for the domestic B5FC secondary branches.

Physical10/11 code is independent readable Python. Existing source owns shared
pointers/math and the eventual development tail; no CPU, IR or fake response
executes here. F8/F9/FA requests suspend the actual caller until another genuine
software consumer changes the request field under its original predicate.
"""
from dataclasses import dataclass
from .city_auxiliary_services import CityAuxiliaryServices
from .domestic_cooperation_controller import UIRegisters,ROM_SHA256,C,Z,N,RULER,DIFFICULTY,AI_REQUEST
from .battle_nmi_services import ServiceWait

@dataclass
class SecondaryRequestWait(ServiceWait):
    condition:str='equal'

class DomesticSecondaryServices(CityAuxiliaryServices):
    PUBLIC_ENTRIES=(0xA000,0xA00F,0xB49C,0xBD7A,0xB5FC,0xB619,0xB98B,0xBBB2)
    LOCAL_ENTRIES=(0xB78B,0xBB40,0xBD36)

    def _entry(self,entry):
        if entry==0xB5FC:return self.secondary_assignment_strategy()
        if entry==0xB619:return self.neighbor_alliance_offer()
        if entry==0xB98B:return self.recruit_low_loyalty_foreign_officer()
        if entry==0xBBB2:return self.reduce_foreign_officer_loyalty()
        if entry==0xB78B:return self.await_alliance_reply()
        if entry==0xBB40:return self.await_recruitment_notice()
        if entry==0xBD36:return self.await_loyalty_notice()
        return super()._entry(entry)

    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if isinstance(call,SecondaryRequestWait):
                    value=self.memory[call.address]
                    blocked=value==call.value if call.condition=='not_equal' else value!=call.value
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
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')

    def _ruler_byte(self,offset):
        m=self.memory
        return m[((m[0x24]|m[0x25]<<8)+offset)&65535]

    def secondary_assignment_strategy(self):
        """B5FC: E89A rejection sample0..89, then three thirty-value bands."""
        r=self.registers
        while True:
            self._mark(0xB5FC)
            yield from self._external(0xB5FC,0xE89A,0xB5FF,'call')
            if r.pc!=0xB5FF:return
            self._a(r.a&127);self._compare(r.a,90);self._mark(0xB603)
            if not r.p&C:break
        self._compare(r.a,30)
        if not r.p&C:return(yield from self.reduce_foreign_officer_loyalty())
        self._compare(r.a,60)
        if not r.p&C:return(yield from self.recruit_low_loyalty_foreign_officer())
        return(yield from self.neighbor_alliance_offer())

    def neighbor_alliance_offer(self):
        """B619: largest neighboring ruler, strict city-count gap, resource offer.

        A nonleader messenger, three active leaders, wrapped diplomacy-byte sum
        zero and two neighboring foreign owners are required. The largest city
        count wins (later tie); target must exceed owncount+2. A controllerbyte3
        exactly3 resolves locally. Other bytes emitF8 and wait for a real reply.
        """
        r,m=self.registers,self.memory;self._mark(0xB619)
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xB61C,0xB61F)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x40]=r.a
        if not(yield from self._local_call(self.domesticcooperationcontroller_b837,0xB626,0xB629)):return
        self._a(m[0x3D]);self._compare(r.a,255)
        if r.p&Z:return(yield from self.city_development_strategy())
        m[0x42]=r.a;self._a(0);m[0x2A]=r.a;m[0x2B]=r.a
        while True:
            self._mark(0xB639);self._a(m[0x2A])
            if not(yield from self._local_call(self.ruler_pointer,0xB63B,0xB63E)):return
            self._y(0);self._a(self._ruler_byte(r.y));self._compare(r.a,255)
            if not r.p&Z:m[0x2B]=self._nz(m[0x2B]+1)
            m[0x2A]=self._nz(m[0x2A]+1);self._a(m[0x2A]);self._compare(r.a,7)
            if r.p&C:break
        self._a(m[0x2B]);self._compare(r.a,3)
        if not r.p&C:return(yield from self.city_development_strategy())
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xB65C,0xB65F)):return
        self._x(0);self._y(4);self._a(self._ruler_byte(r.y))
        for offset in(5,6,7):
            self._y(offset);self._flag(C,False);self._add(self._ruler_byte(r.y))
        self._compare(r.a,0)
        if not r.p&Z:return(yield from self.city_development_strategy())
        if not(yield from self._local_call(self.domesticcooperationcontroller_b898,0xB678,0xB67B)):return
        self._compare(r.x,2)
        if not r.p&C:return(yield from self.city_development_strategy())
        self._y(0);m[0x36]=r.y;m[0x37]=r.y;m[0x38]=r.y
        while True:
            self._mark(0xB68A);self._y(m[0x36]);self._a(m[0x6F73+r.y])
            if r.p&Z:
                self._a(m[0x36])
                if not(yield from self._local_call(self.domesticcooperationcontroller_d080,0xB695,0xB698)):return
                self._a(m[0x2B]);self._compare(r.a,m[0x37])
                if r.p&C:
                    m[0x37]=r.a;self._a(m[0x36]);m[0x38]=r.a
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,7)
            if r.p&C:break
        self._a(m[RULER])
        if not(yield from self._local_call(self.domesticcooperationcontroller_d080,0xB6B5,0xB6B8)):return
        self._a(m[0x2B]);self._flag(C,False);self._add(2);self._compare(r.a,m[0x37])
        if r.p&C:return(yield from self.city_development_strategy())
        if not(yield from self.quote_alliance_offer()):return
        self._a(m[0x38])
        if not(yield from self._local_call(self.ruler_pointer,0xB751,0xB754)):return
        self._y(3);self._a(self._ruler_byte(r.y));self._compare(r.a,3)
        if r.p&Z:
            if not(yield from self._local_call(self.domesticcooperationcontroller_b90a,0xB75C,0xB75F)):return
            if not(yield from self._local_call(self.domesticcooperationcontroller_b7ce,0xB75F,0xB762)):return
            return(yield from self.city_development_strategy())
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xB768,0xB76B)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x40]=r.a
        self._a(m[0x38])
        if not(yield from self._local_call(self.ruler_pointer,0xB775,0xB778)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x41]=r.a
        self._y(3);self._a(self._ruler_byte(r.y));m[0x6F44]=r.a
        self._a(248);m[AI_REQUEST]=r.a
        return(yield from self.await_alliance_reply())

    def quote_alliance_offer(self):
        """B6C5..B74D: exact quantity scratch and fullword affordability check.

        It quotes4q or6q, q=floor((targetcities*30+70)/10). 003B copies0431
        (zero), not0430: committed transfer truncates the quote to its lowbyte.
        The sufficient-resource check still uses the full042F/0430 word.
        """
        r,m=self.registers,self.memory;self._mark(0xB6C5)
        self._a(m[0x37]);m[0x20]=r.a;self._a(30);m[0x21]=r.a
        if not(yield from self._local_call(self.domesticcooperationcontroller_d471,0xB6CE,0xB6D1)):return
        self._a(m[0x2A]);self._flag(C,False);self._add(70);m[0x21]=r.a
        self._a(m[0x2B]);self._add(0);m[0x22]=r.a
        self._a(10);m[0x23]=r.a;self._a(0);m[0x24]=r.a
        if not(yield from self._local_call(self.divide_domestic_word,0xB6E6,0xB6E9)):return
        self._a(m[0x21]);m[0x42F]=r.a;self._a(m[0x22]);m[0x430]=r.a
        for _ in range(2):
            m[0x42F]=self._shift(m[0x42F],True);m[0x430]=self._shift(m[0x430],True,rotate=True)
        self._a(0);m[0x431]=r.a;self._a(0);m[0x39]=r.a
        self._a(100)
        if not(yield from self._local_call(self.random_below,0xB70B,0xB70E)):return
        self._compare(r.a,50)
        if r.p&C:
            self._a(1);m[0x39]=r.a
            self._a(m[0x21]);m[0x20]=r.a;self._a(m[0x22]);m[0x21]=r.a
            self._a(0);m[0x22]=r.a;self._a(6);m[0x23]=r.a
            if not(yield from self._local_call(self.multiply_domestic_word,0xB727,0xB72A)):return
            self._a(m[0x26]);m[0x42F]=r.a;self._a(m[0x27]);m[0x430]=r.a
            self._a(0);m[0x431]=r.a
        self._a(m[0x42F]);m[0x3A]=r.a;self._a(m[0x431]);m[0x3B]=r.a
        if not(yield from self._local_call(self.domesticcooperationcontroller_b7a2,0xB746,0xB749)):return
        if r.p&C:return True
        yield from self.city_development_strategy()
        return False

    def await_alliance_reply(self):
        """B78B: await any reply other thanF8; only zero accepts the offer."""
        r,m=self.registers,self.memory
        while True:
            self._mark(0xB78B);self._a(m[AI_REQUEST]);self._compare(r.a,248)
            if not r.p&Z:break
            r.pc=0xB78B
            yield SecondaryRequestWait('domestic_secondary_reply',0xB78B,AI_REQUEST,248,'Original F8 request waits for another software consumer',r.sp,'not_equal')
        self._compare(r.a,0)
        if r.p&Z:
            if not(yield from self._local_call(self.domesticcooperationcontroller_b90a,0xB799,0xB79C)):return
            if not(yield from self._local_call(self.domesticcooperationcontroller_b7ce,0xB79C,0xB79F)):return
        return(yield from self.city_development_strategy())

    def await_recruitment_notice(self):
        """BB40: foreign roster move already committed; wait for request0."""
        r,m=self.registers,self.memory
        while True:
            self._mark(0xBB40);self._a(m[AI_REQUEST])
            if r.p&Z:break
            r.pc=0xBB40
            yield SecondaryRequestWait('domestic_secondary_notice',0xBB40,AI_REQUEST,0,'Original FA notice completion must come from its consumer',r.sp)
        return(yield from self.city_development_strategy())

    def await_loyalty_notice(self):
        """BD36: loyalty reduction already committed; wait for request0."""
        r,m=self.registers,self.memory
        while True:
            self._mark(0xBD36);self._a(m[AI_REQUEST])
            if r.p&Z:break
            r.pc=0xBD36
            yield SecondaryRequestWait('domestic_secondary_notice',0xBD36,AI_REQUEST,0,'Original F9 notice completion must come from its consumer',r.sp)
        return(yield from self.city_development_strategy())

    def recruit_low_loyalty_foreign_officer(self):
        """B98B: owned destination with shortest prefix, weakest foreign loyalty.

        Owned ten-entry prefix must have capacity; ties keep the first city.
        Foreign target loyalty must be below70; strict-less scan keeps the first
        minimum. Success appends to firstFF, adjusts loyalty, removes/compacts
        source, neutralizes an emptied city with wholebyte7, then emitsFA unless
        that foreign ruler's controller byte is exactly3. HP/status/residence and
        troop words are not rewritten by this body.
        """
        r,m=self.registers,self.memory;self._mark(0xB98B)
        self._a(0);m[0x36]=r.a;m[0x39]=r.a;self._a(255);m[0x37]=r.a;m[0x38]=r.a
        while True:
            self._mark(0xB99B);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xB99E,0xB9A1)):return
            self._compare(r.a,m[RULER])
            if r.p&Z:
                if not(yield from self._local_call(self.domesticcooperationcontroller_bb82,0xB9A6,0xB9A9)):return
                self._a(m[0x36])
                if not(yield from self._local_call(self.count_prefix_officers,0xB9AC,0xB9AF)):return
                self._compare(r.a,10)
                if not r.p&C:
                    self._compare(r.a,m[0x37])
                    if not r.p&C:
                        m[0x37]=r.a;self._a(m[0x36]);m[0x38]=r.a
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(m[0x38]);self._compare(r.a,255)
        if r.p&Z:return(yield from self.city_development_strategy())
        self._a(0);m[0x36]=r.a;self._a(255);m[0x3D]=r.a;m[0x3E]=r.a;m[0x3F]=r.a
        while True:
            self._mark(0xB9E5);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xB9E8,0xB9EB)):return
            self._compare(r.a,m[RULER])
            if not r.p&Z:
                if not(yield from self._local_call(self.domesticcooperationcontroller_bb48,0xB9F0,0xB9F3)):return
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(m[0x3E]);self._compare(r.a,70)
        if r.p&C:return(yield from self.city_development_strategy())
        accepted=yield from self.foreign_recruitment_probability()
        if not accepted:return
        return(yield from self.commit_foreign_recruitment())

    def foreign_recruitment_probability(self):
        """BA07..BA7C: exact signed-byte level adjustment and difficulty table.

        Original IQ+virtue ADC is discarded before division: numerator21 keeps
        targetvirtue, not that sum. No cleaned-up gameplay formula replaces it.
        """
        r,m=self.registers,self.memory;self._mark(0xBA07)
        self._a(m[0x3D]);self._y(4)
        if not(yield from self._local_call(self.officer_field_pointer,0xBA0C,0xBA0F)):return False
        m[0x21]=r.a;self._y(11);self._a(self._officer_byte(r.y))
        for _ in range(4):r.a=self._shift(r.a,False)
        m[0x20]=r.a;self._a(m[0x39]);self._flag(C,True);self._add(m[0x20],subtract=True);m[0x39]=r.a
        self._y(2);self._a(self._officer_byte(r.y));self._flag(C,False);self._add(m[0x21])
        self._a(20);m[0x23]=r.a;self._a(0);m[0x22]=r.a;m[0x24]=r.a
        if not(yield from self._local_call(self.divide_domestic_word,0xBA35,0xBA38)):return False
        self._a(m[0x3E]);self._y(0);self._compare(r.a,31)
        if r.p&C:
            self._y(r.y+1);self._compare(r.a,51)
            if r.p&C:self._y(r.y+1)
        m[0x20]=r.y;self._a(m[DIFFICULTY]);r.a=self._shift(r.a,True);r.a=self._shift(r.a,True)
        self._a(r.a|m[0x20]);self._y(r.a);self._a(m[0xBA81+r.y]);self._flag(C,False);self._add(m[0x21]);m[0x2A]=r.a
        self._a(m[0x39])
        if r.p&N:
            self._a(r.a^255);self._flag(C,False);self._add(1);r.a=self._shift(r.a,True);m[0x20]=r.a
            self._a(m[0x2A]);self._flag(C,True);self._add(m[0x20],subtract=True);m[0x2A]=r.a
        else:
            self._flag(C,False);self._add(m[0x2A]);m[0x2A]=r.a
        self._a(100)
        if not(yield from self._local_call(self.random_below,0xBA77,0xBA7A)):return False
        self._compare(r.a,m[0x2A])
        if r.p&C:
            yield from self.city_development_strategy();return False
        return True

    def commit_foreign_recruitment(self):
        """BA8D..BB45: ordered roster, loyalty, neutralization and FA request."""
        r,m=self.registers,self.memory;self._mark(0xBA8D)
        self._a(m[0x38])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBA90,0xBA93)):return
        self._y(16)
        while True:
            self._mark(0xBA95);self._y(r.y+1);self._a(self._city_byte(r.y));self._compare(r.a,255)
            if r.p&Z:break
        self._a(m[0x3D]);self._write_city_byte(r.y,r.a)
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xBAA4,0xBAA7)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x30]=r.a;self._a(m[0x3D]);m[0x31]=r.a
        if not(yield from self._local_call(self.recalculate_recruited_loyalty,0xBAB2,0xBAB5)):return
        self._a(m[0x3F])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBAB8,0xBABB)):return
        m[0x42]=r.a;self._y(16)
        while True:
            self._mark(0xBAC0);self._y(r.y+1);self._a(self._city_byte(r.y));self._compare(r.a,m[0x3D])
            if r.p&Z:break
        self._a(255);self._write_city_byte(r.y,r.a);self._a(m[0x3F])
        if not(yield from self._local_call(self.compact_city_roster,0xBACF,0xBAD2)):return
        self._a(m[0x3F])
        if not(yield from self._local_call(self.count_prefix_officers,0xBAD5,0xBAD8)):return
        self._compare(r.a,0)
        if r.p&Z:self._y(0);self._a(7);self._write_city_byte(r.y,r.a)
        self._a(m[0x3D]);m[0x43]=r.a;self._a(m[0x38])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBAEB,0xBAEE)):return
        if not(yield from self._local_call(self.ruler_pointer,0xBAEE,0xBAF1)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x40]=r.a;self._a(m[0x42])
        if not(yield from self._local_call(self.ruler_pointer,0xBAFB,0xBAFE)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x41]=r.a;self._y(3);self._a(self._ruler_byte(r.y));self._compare(r.a,3)
        if r.p&Z:return(yield from self.city_development_strategy())
        self._a(0);m[0x36]=r.a;self._a(255);m[0x3D]=r.a;self._a(0);m[0x3E]=r.a
        while True:
            self._mark(0xBB1C);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBB1F,0xBB22)):return
            self._compare(r.a,7)
            if not r.p&Z:
                self._compare(r.a,m[0x42])
                if r.p&Z:
                    self._a(m[0x41])
                    if not(yield from self._local_call(self.domesticcooperationcontroller_bd40,0xBB2E,0xBB31)):return
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(250);m[AI_REQUEST]=r.a
        return(yield from self.await_recruitment_notice())

    def reduce_foreign_officer_loyalty(self):
        """BBB2: own highest IQ vs foreign six-officer city, reduce one loyalty.

        A foreign controller exactly3 is excluded at city selection. City prefix
        count ties replace, selecting later cities, and must be>=6. The final
        target is sampled from allten-slot officers whose loyalty is50..89.
        Mutation precedes F9 notice; no fake text completion is supplied.
        """
        r,m=self.registers,self.memory;self._mark(0xBBB2)
        self._a(0);m[0x36]=r.a;self._a(255);m[0x3D]=r.a;self._a(0);m[0x3E]=r.a
        while True:
            self._mark(0xBBC1);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBBC4,0xBBC7)):return
            self._compare(r.a,m[RULER])
            if r.p&Z:
                if not(yield from self._local_call(self.domesticcooperationcontroller_bd3e,0xBBCC,0xBBCF)):return
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(0);m[0x36]=r.a;m[0x37]=r.a;self._a(255);m[0x38]=r.a
        while True:
            self._mark(0xBBE6);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBBE9,0xBBEC)):return
            self._compare(r.a,m[RULER])
            if not r.p&Z:
                if not(yield from self._local_call(self.ruler_pointer,0xBBF1,0xBBF4)):return
                self._y(3);self._a(self._ruler_byte(r.y));self._compare(r.a,3)
                if not r.p&Z:
                    self._a(m[0x36])
                    if not(yield from self._local_call(self.count_prefix_officers,0xBBFF,0xBC02)):return
                    self._compare(r.a,m[0x37])
                    if r.p&C:m[0x37]=r.a;self._a(m[0x36]);m[0x38]=r.a
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(m[0x37]);self._compare(r.a,6)
        if not r.p&C:return(yield from self.city_development_strategy())
        self._y(15);self._a(255)
        while True:
            self._mark(0xBC28);m[0x6F73+r.y]=r.a;self._y(r.y-1)
            if r.p&N:break
        self._a(m[0x38])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBC31,0xBC34)):return
        self._a(17);m[0x36]=r.a;self._a(0);m[0x37]=r.a
        while True:
            self._mark(0xBC3E);self._y(m[0x36]);self._a(self._city_byte(r.y));self._compare(r.a,255)
            if not r.p&Z:
                self._y(3)
                if not(yield from self._local_call(self.officer_field_pointer,0xBC49,0xBC4C)):return
                self._compare(r.a,50)
                if r.p&C:
                    self._compare(r.a,90)
                    if not r.p&C:
                        self._y(m[0x36]);self._a(self._city_byte(r.y));self._y(m[0x37]);m[0x6F73+r.y]=r.a
                        m[0x37]=self._nz(m[0x37]+1)
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,27)
            if r.p&C:break
        self._a(m[0x37])
        if r.p&Z:return(yield from self.city_development_strategy())
        self._compare(r.a,1)
        if not r.p&Z:
            if not(yield from self._local_call(self.random_low_nibble_below,0xBC75,0xBC78)):return
            self._flag(C,False);self._add(1)
        self._y(r.a);self._a(m[0x6F72+r.y]);m[0x37]=r.a
        self._a(m[0x37]);self._y(2)
        if not(yield from self._local_call(self.officer_field_pointer,0xBC87,0xBC8A)):return
        m[0]=r.a;self._a(m[0x3E]);self._flag(C,True);self._add(m[0],subtract=True)
        if not r.p&C:self._a(0)
        self._y(m[DIFFICULTY]);self._flag(C,False);self._add(m[0xBCAB+r.y]);m[0x2A]=r.a
        self._a(100)
        if not(yield from self._local_call(self.random_below,0xBCA1,0xBCA4)):return
        self._compare(r.a,m[0x2A])
        if r.p&C:return(yield from self.city_development_strategy())
        return(yield from self.commit_loyalty_reduction())

    def commit_loyalty_reduction(self):
        """BCAE..BD3B: reduction uses own bestIQ/20 + original random1..7."""
        r,m=self.registers,self.memory;self._mark(0xBCAE)
        self._a(m[0x3E]);m[0x21]=r.a;self._a(20);m[0x23]=r.a;self._a(0);m[0x22]=r.a;m[0x24]=r.a
        if not(yield from self._local_call(self.divide_domestic_word,0xBCBD,0xBCC0)):return
        self._a(7)
        if not(yield from self._local_call(self.random_low_nibble_below,0xBCC2,0xBCC5)):return
        self._flag(C,False);self._add(1);self._flag(C,False);self._add(m[0x21]);m[0x39]=r.a
        self._a(m[0x37]);self._y(3)
        if not(yield from self._local_call(self.officer_field_pointer,0xBCD3,0xBCD6)):return
        self._flag(C,True);self._add(m[0x39],subtract=True)
        if not r.p&C:self._a(0)
        self._write_officer_byte(r.y,r.a)
        self._a(m[RULER])
        if not(yield from self._local_call(self.ruler_pointer,0xBCE3,0xBCE6)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x39]=r.a;self._a(m[0x38])
        if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBCF0,0xBCF3)):return
        m[0x3B]=r.a
        if not(yield from self._local_call(self.ruler_pointer,0xBCF6,0xBCF9)):return
        self._y(0);self._a(self._ruler_byte(r.y));m[0x3A]=r.a;self._y(3);self._a(self._ruler_byte(r.y));m[0x6F44]=r.a
        self._a(0);m[0x36]=r.a;self._a(255);m[0x3D]=r.a;self._a(0);m[0x3E]=r.a
        while True:
            self._mark(0xBD16);self._a(m[0x36])
            if not(yield from self._local_call(self.city_pointer_and_resource_caps,0xBD19,0xBD1C)):return
            self._compare(r.a,m[0x3B])
            if r.p&Z:
                self._a(m[0x3A])
                if not(yield from self._local_call(self.domesticcooperationcontroller_bd40,0xBD24,0xBD27)):return
            m[0x36]=self._nz(m[0x36]+1);self._a(m[0x36]);self._compare(r.a,30)
            if r.p&C:break
        self._a(249);m[AI_REQUEST]=r.a
        return(yield from self.await_loyalty_notice())
