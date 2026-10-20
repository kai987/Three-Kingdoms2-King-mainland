"""Exact postbattle stage2 and supply-return protocol, physical8/9.

ECEE requests fade-out and returns immediately. It is not a synchronously
waiting render barrier. The original stage3 palette-completion polling is
outside this owner's implemented stage. Existing gameplay arithmetic is
credited to battle_state_machine.finalization_phase/return_campaign_supplies.
Only the register/stack/mapper protocol is newly made explicit here.
"""
from .postbattle_resource_services import PostbattleResourceServices
from .battle_setup_ai import C,Z
from .battle_nmi_services import ServiceCall


class PostbattleParentServices(PostbattleResourceServices):
    NEW_ENTRIES=(0xA006,0xBAB3,0xBB93,0xC027)
    PUBLIC_ENTRIES=PostbattleResourceServices.PUBLIC_ENTRIES+NEW_ENTRIES
    LOCAL_ENTRIES=PUBLIC_ENTRIES

    def run_entry(self,entry=0xA006,**kwargs):
        if entry in (0xA006,0xBAB3)and self.memory[0x501]>=4:
            raise ValueError('Original four-state inline dispatch requires phase0..3')
        return super().run_entry(entry,**kwargs)

    def _entry(self,entry):
        if entry==0xA006:return self.postbattle_entry()
        if entry==0xBAB3:return self.postbattle_stage_dispatch()
        if entry==0xBB93:return self.settle_and_return_supplies()
        if entry==0xC027:return self.return_campaign_supply_words()
        return super()._entry(entry)

    def postbattle_entry(self):
        """A006 is the original JMP BAB3; no new return frame is pushed."""
        self._mark(0xA006)
        return(yield from self.postbattle_stage_dispatch())

    def postbattle_stage_dispatch(self):
        """BAB3/EADE four-state inline dispatch; only stage2 is implemented.

        Unimplemented0/1/3 stop after the genuine dispatch at their actual
        target and preserve the original parent frame. This is a dispatch
        dependency, not an invented JSR or an automatically completed stage.
        """
        r,m=self.registers,self.memory;self._mark(0xBAB3);self._a(m[0x501])
        index=self._dispatch(0xBAB6,(0xBAC1,0xBB3D,0xBB93,0xBBA0))
        if index==2:return(yield from self.settle_and_return_supplies())
        target=r.pc
        self.events.append(dict(kind='unimplemented_original_dispatch',dispatch_pc=0xBAB6,target=target,stage=index,adds_frame=False))
        yield ServiceCall(target,self._return_pc,'dispatch',r,m,tuple(m.banks),(r.sp+2)&255)
        # A future explicit owner must perform the original remaining body
        # and reach the existing frame's PC/SP; _drive checks both before
        # this generator may finish. No local or synthetic RTS is supplied.

    def settle_and_return_supplies(self):
        """BB93: immediate fade request, losses, supplies, phase increment.

        ECEE copies the palette and requests87=1, then truly returns atBB96.
        No wait for87 is inserted here. Original stage3 later waits for its
        sign bit, driven by real palette services in explicit NMI execution.
        """
        r,m=self.registers,self.memory;self._mark(0xBB93)
        yield from self._external(0xBB93,0xECEE,0xBB96,'call')
        if r.pc!=0xBB96:return
        if not(yield from self._local_call(self.settle_city_resource_losses,0xBB96,0xBB99)):return
        if not(yield from self._local_call(self.return_campaign_supply_words,0xBB99,0xBB9C)):return
        m[0x501]=self._nz(m[0x501]+1)
        self._mark(0xBB9F);self._rts()

    def return_campaign_supply_words(self):
        """C027: two live city allocations, raw byte indices, cap9999.

        The outcome byte is ASL-truncated before indexing0522/0526; legal
        outcomes0/1 and explicit raw domains remain separate. A non-FF
        escape selector uses F2D7's exact rawbyte record pointer. Only packed
        status1/2 routes the second return to052C;0/3 reuse050E.
        """
        r,m=self.registers,self.memory;self._mark(0xC027);self._y(0x30)
        yield from self._external(0xC029,0xF25F,0xC02C,'call')
        if r.pc!=0xC02C:return
        self._a(m[0x50E])
        yield from self._external(0xC02F,0xF2AF,0xC032,'call')
        if r.pc!=0xC032:return
        self._a(m[0x514]);r.a=self._shift(r.a,True);self._a(r.a^2);self._x(r.a)
        if not(yield from self._local_call(self.add_supply_pair_and_cap,0xC039,0xC03C)):return
        self._y(0x31)
        yield from self._external(0xC03E,0xF25F,0xC041,'call')
        if r.pc!=0xC041:return
        self._a(m[0x52B]);self._compare(r.a,255)
        if not r.p&Z:
            yield from self._external(0xC048,0xF2D7,0xC04B,'call')
            if r.pc!=0xC04B:return
            self._y(11);self._a(self._city_byte(r.y));self._a(r.a&3)
            if not r.p&Z:
                self._compare(r.a,3)
                if not r.p&Z:
                    self._y(0x30)
                    yield from self._external(0xC06C,0xF25F,0xC06F,'call')
                    if r.pc!=0xC06F:return
                    self._a(m[0x52C])
                    yield from self._external(0xC072,0xF2AF,0xC075,'call')
                    if r.pc!=0xC075:return
                    self._a(m[0x514]);r.a=self._shift(r.a,True);self._x(r.a)
                    return(yield from self.add_supply_pair_and_cap())
        self._mark(0xC057);self._y(0x30)
        yield from self._external(0xC059,0xF25F,0xC05C,'call')
        if r.pc!=0xC05C:return
        self._a(m[0x50E])
        yield from self._external(0xC05F,0xF2AF,0xC062,'call')
        if r.pc!=0xC062:return
        self._a(m[0x514]);r.a=self._shift(r.a,True);self._x(r.a);self._mark(0xC067)
        return(yield from self.add_supply_pair_and_cap())

    def _city_byte(self,index):
        m=self.memory
        return m[((m[0]|m[1]<<8)+index)&65535]

    def _write_city_byte(self,index,value):
        m=self.memory
        m[((m[0]|m[1]<<8)+index)&65535]=value&255

    def add_supply_pair_and_cap(self):
        """C07A: low/high add with carry, wrap16 first, then unsignedcap.

        The first cap has the real C08E JSR frame. The second is the original
        fallthrough intoC0A5 and pops the caller already owned by this body.
        Every byte access rereads the live00/01 pair; no cached barepointer.
        """
        r,m=self.registers,self.memory;self._mark(0xC07A);self._y(2)
        self._a(self._city_byte(r.y));self._flag(C,False);self._add(m[0x526+r.x]);self._write_city_byte(r.y,r.a)
        self._y(r.y+1);self._a(self._city_byte(r.y));self._add(m[0x527+r.x]);self._write_city_byte(r.y,r.a)
        self._y(2)
        if not(yield from self._local_call(self.cap_supply_field,0xC08E,0xC091)):return
        self._y(4);self._a(self._city_byte(r.y));self._flag(C,False);self._add(m[0x522+r.x]);self._write_city_byte(r.y,r.a)
        self._y(r.y+1);self._a(self._city_byte(r.y));self._add(m[0x523+r.x]);self._write_city_byte(r.y,r.a)
        self._y(4)
        return(yield from self.cap_supply_field())

    def cap_supply_field(self):
        """C0A5: compare word to10000; write high then low onlyif>=10000."""
        r=self.registers;self._mark(0xC0A5);self._a(self._city_byte(r.y));self._flag(C,True);self._add(0x10,subtract=True)
        self._y(r.y+1);self._a(self._city_byte(r.y));self._add(0x27,subtract=True)
        if r.p&C:
            self._a(0x27);self._write_city_byte(r.y,r.a);self._y(r.y-1);self._a(0x0F);self._write_city_byte(r.y,r.a)
        self._mark(0xC0BA);self._rts()
        if False:yield None
