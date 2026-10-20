"""Exact resource-settlement caller protocol, physical8 BF0A..9 C014.

The gameplay arithmetic was already named in battle_state_machine.py. This
module adds independently readable register/scratch/stack/service protocol;
it does not claim first discovery of the existing settlement rule. Complete
city pointers are copied to1A/1B before arithmetic reuses00..09. Bare helpers
retain live pointer/byte-index aliases rather than assuming a city record.
"""
from .deployment_pointer_services import DeploymentPointerServices
from .battle_setup_ai import C,Z


class PostbattleResourceServices(DeploymentPointerServices):
    NEW_ENTRIES=(0xBF0A,0xBF9E,0xBFB3,0xBFEC)
    PUBLIC_ENTRIES=DeploymentPointerServices.PUBLIC_ENTRIES+NEW_ENTRIES
    LOCAL_ENTRIES=PUBLIC_ENTRIES

    def run_entry(self,entry=0xBF0A,**kwargs):
        return super().run_entry(entry,**kwargs)

    def _entry(self,entry):
        if entry==0xBF0A:return self.settle_city_resource_losses()
        if entry==0xBF9E:return self.reduce_pointed_word()
        if entry==0xBFB3:return self.reduce_pointed_byte()
        if entry==0xBFEC:return self.select_resource_rate()
        return super()._entry(entry)

    def _resource_byte(self,index):
        m=self.memory
        return m[((m[0x1A]|m[0x1B]<<8)+index)&65535]

    def _write_resource_byte(self,index,value):
        m=self.memory
        m[((m[0x1A]|m[0x1B]<<8)+index)&65535]=value&255

    def settle_city_resource_losses(self):
        """BF0A: only outcome0 consumes RNG and changes six city fields.

        F25F selects physical16 through the NMI data-window shadowE1; F2AF
        creates6000+32*rawcity. Its complete00/01 pair is copied to1A/1B.
        The final BF9B→BF9E is a tail jump and shares this actual caller.
        """
        r,m=self.registers,self.memory;self._mark(0xBF0A);self._a(m[0x514])
        if not r.p&Z:self._mark(0xBF0F);self._rts();return
        self._y(0x30)
        yield from self._external(0xBF12,0xF25F,0xBF15,'call')
        if r.pc!=0xBF15:return
        self._a(m[0x50E])
        yield from self._external(0xBF18,0xF2AF,0xBF1B,'call')
        if r.pc!=0xBF1B:return
        self._a(m[0]);m[0x1A]=r.a;self._a(m[1]);m[0x1B]=r.a
        yield from self._external(0xBF27,0xE87A,0xBF2A,'call')
        if r.pc!=0xBF2A:return
        self._a(r.a&1);self._flag(C,False);self._add(1);m[3]=r.a
        self._y(6)
        if not(yield from self._local_call(self.reduce_pointed_word,0xBF34,0xBF37)):return
        self._x(0);self._a(m[0x506])
        for threshold in(6,11,16,21):
            self._compare(r.a,threshold)
            if not r.p&C:break
            self._x(r.x+1)
        self._a(m[0xC015+r.x]);m[0x10]=r.a
        for field,site,return_pc in((8,0xBF5E,0xBF61),(14,0xBF69,0xBF6C)):
            self._a(m[0x10]);m[3]=r.a;self._y(field)
            if not(yield from self._local_call(self.reduce_pointed_word,site,return_pc)):return
        self._a(m[0x10]);m[3]=r.a;self._y(11);self._a(self._resource_byte(r.y));m[0]=r.a
        self._a(0);m[1]=r.a;m[2]=r.a
        if not(yield from self._local_call(self.reduce_pointed_byte,0xBF81,0xBF84)):return
        self._y(2)
        if not(yield from self._local_call(self.select_resource_rate,0xBF86,0xBF89)):return
        m[3]=r.a;self._y(2)
        if not(yield from self._local_call(self.reduce_pointed_word,0xBF8E,0xBF91)):return
        self._y(4)
        if not(yield from self._local_call(self.select_resource_rate,0xBF93,0xBF96)):return
        m[3]=r.a;self._y(4);self._mark(0xBF9B)
        return(yield from self.reduce_pointed_word())

    def reduce_pointed_word(self):
        """BF9E: save rawY; load low/high via the live1A pair; scale/store.

        INY is a byte operation, so rawY255 loads its second byte at offset0.
        No bare helper call is silently treated as a legal city-field call.
        """
        r,m=self.registers,self.memory;self._mark(0xBF9E);self._a(r.y);self._push(r.a)
        self._a(self._resource_byte(r.y));m[0]=r.a;self._y(r.y+1)
        self._a(self._resource_byte(r.y));m[1]=r.a;self._a(0);m[2]=r.a
        return(yield from self._scale_saved_field())

    def reduce_pointed_byte(self):
        """BFB3: byte value00/high01..02 were prepared by the real parent."""
        r=self.registers;self._mark(0xBFB3);self._a(r.y);self._push(r.a)
        return(yield from self._scale_saved_field())

    def _scale_saved_field(self):
        """BFB5: retain low16 product, divide by10, restoreY, write low/high.

        EBE9's full multiply is a real dependency; only06/07 are selected
        afterwards, discarding higher product bytes. EA7C is also real. A
        restoredY11 writes only one byte; all other rawY values write two.
        The pointer is re-read for each store, preserving bare alias quirks.
        """
        r,m=self.registers,self.memory;self._mark(0xBFB5);self._a(10);self._flag(C,True);self._add(m[3],subtract=True);m[3]=r.a
        yield from self._external(0xBFBE,0xEBE9,0xBFC1,'call')
        if r.pc!=0xBFC1:return
        self._a(m[6]);m[1]=r.a;self._a(m[7]);m[2]=r.a
        self._a(10);m[3]=r.a;self._a(0);m[4]=r.a
        yield from self._external(0xBFD7,0xEA7C,0xBFDA,'call')
        if r.pc!=0xBFDA:return
        self._a(self._pop());self._y(r.a);self._a(m[1]);self._write_resource_byte(r.y,r.a)
        self._compare(r.y,11)
        if not r.p&Z:
            self._y(r.y+1);self._a(m[2]);self._write_resource_byte(r.y,r.a)
        self._mark(0xBFEB);self._rts()

    def select_resource_rate(self):
        """BFEC: original ascending unsigned threshold loop, not bisect.

        Under this immutable table, values<=501 traverse all four thresholds
        and return9; values>501 return5 at the first threshold. Intermediate
        table rates6/7/8 remain original bytes but are not selected by this
        ordinary entry/table. Carry, X, Y and all scratch remain exact.
        """
        r,m=self.registers,self.memory;self._mark(0xBFEC);self._a(self._resource_byte(r.y));m[0]=r.a
        self._y(r.y+1);self._a(self._resource_byte(r.y));m[1]=r.a;self._x(0)
        while True:
            self._mark(0xBFF9);self._a(m[0xC01A+r.x]);self._flag(C,True);self._add(m[0],subtract=True)
            self._a(m[0xC01B+r.x]);self._add(m[1],subtract=True)
            if not r.p&C:break
            self._x(r.x+1);self._x(r.x+1);self._compare(r.x,8)
            if r.p&C:break
        self._a(r.x);r.a=self._shift(r.a,False);self._x(r.a);self._a(m[0xC022+r.x]);self._mark(0xC014);self._rts()
        if False:yield None
