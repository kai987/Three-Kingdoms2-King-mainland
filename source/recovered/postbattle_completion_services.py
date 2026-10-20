"""Exact postbattle stage3 gate and city chief protocol, physical8.

Existing finalize_city_ownership/promote_city_leader already recover gameplay.
This module makes original registers/scratch/stack/mapper effects explicit.
A nonnegative87 returns immediately on each invocation; only its sign bit
allows city cleanup. It neither waits inside ECEE nor writes a fade ack.
"""
from .postbattle_parent_services import PostbattleParentServices
from .battle_setup_ai import C,Z,N
from .battle_nmi_services import ServiceCall,ServiceWait
from .mapped_memory import UnsupportedHardware


class PostbattleCompletionServices(PostbattleParentServices):
    NEW_ENTRIES=(0xA006,0xBAB3,0xBBA0,0xBBB8,0xBC00)
    PUBLIC_ENTRIES=PostbattleParentServices.PUBLIC_ENTRIES+(0xBBA0,0xBBB8,0xBC00)
    LOCAL_ENTRIES=PUBLIC_ENTRIES

    def run_entry(self,entry=0xA006,**kwargs):
        return super().run_entry(entry,**kwargs)

    def _entry(self,entry):
        if entry==0xBBA0:return self.complete_after_palette_transition()
        if entry==0xBBB8:return self.finalize_current_city_and_neighbor_chiefs()
        if entry==0xBC00:return self.promote_city_ruler_in_roster()
        return super()._entry(entry)

    def _drive(self):
        """Keep real ServiceCall identity and explicit missing-read boundary."""
        while True:
            if isinstance(self.pending,ServiceWait):
                if self.registers.pc!=self.pending.pc or self.registers.sp!=self.pending.expected_sp:
                    return self._result('dependency')
                self.pending=None
            elif self.pending is not None:
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                same=(self.registers.pc,self.registers.sp)==(self._return_pc,self._expected_return_sp)
                return self._result('returned'if same else'nonlocal_return')
            if isinstance(self.pending,ServiceWait):return self._result('dependency')

    def _read_pointed(self,zp,index,pc):
        while True:
            self._mark(pc);r,m=self.registers,self.memory;address=((m[zp]|m[(zp+1)&255]<<8)+index)&65535
            try:return m[address]
            except UnsupportedHardware as exc:
                yield ServiceWait('explicit_hardware_read',pc,address,reason=str(exc),expected_sp=r.sp)

    def _write_pointed(self,zp,index,value):
        m=self.memory;m[((m[zp]|m[(zp+1)&255]<<8)+index)&65535]=value&255

    def postbattle_stage_dispatch(self):
        """Only0/1 remain external dispatch dependencies;2 is inherited."""
        r,m=self.registers,self.memory;self._mark(0xBAB3);self._a(m[0x501])
        index=self._dispatch(0xBAB6,(0xBAC1,0xBB3D,0xBB93,0xBBA0))
        if index==2:return(yield from self.settle_and_return_supplies())
        if index==3:return(yield from self.complete_after_palette_transition())
        self.events.append(dict(kind='unimplemented_original_dispatch',dispatch_pc=0xBAB6,target=r.pc,stage=index,adds_frame=False))
        yield ServiceCall(r.pc,self._return_pc,'dispatch',r,m,tuple(m.banks),(r.sp+2)&255)

    def complete_after_palette_transition(self):
        """BBA0: sign-only gate, normal RTS while not completed.

        Each callback is a new invocation. There is no cooperative fade wait
        suspended here and no readiness/87 write. On sign set, originalBBB8
        runs before global1/city13/sub0 are written.0501 is not incremented.
        """
        r,m=self.registers,self.memory;self._mark(0xBBA0);self._a(m[0x87])
        if r.p&N:
            if not(yield from self._local_call(self.finalize_current_city_and_neighbor_chiefs,0xBBA5,0xBBA8)):return
            self._a(1);m[0x7A]=r.a;self._a(13);m[0x400]=r.a;self._a(0);m[0x401]=r.a
        self._mark(0xBBB7);self._rts()

    def finalize_current_city_and_neighbor_chiefs(self):
        """BBB8: optional owner write, then chief swaps for city+neighbors.

        The unchanged bank16 table is byte-indexed by u8(city<<3); onlyFF
        stops the original loop. There is no injected8-neighbor cap, signed
        sentinel rule, owner normalization or inferred city eligibility.
        """
        r,m=self.registers,self.memory;self._mark(0xBBB8);self._y(0x30)
        yield from self._external(0xBBBA,0xF25F,0xBBBD,'call')
        if r.pc!=0xBBBD:return
        self._a(m[0x50E])
        yield from self._external(0xBBC0,0xF2AF,0xBBC3,'call')
        if r.pc!=0xBBC3:return
        self._a(m[0x514])
        if r.p&Z:
            self._a(m[0x507])
            for _ in range(4):r.a=self._shift(r.a,False)
            self._a(r.a&15);m[2]=r.a;self._y(0)
            self._a((yield from self._read_pointed(0,r.y,0xBBD6)));self._a(r.a&240);self._a(r.a|m[2]);self._mark(0xBBDD);self._write_pointed(0,r.y,r.a)
        if not(yield from self._local_call(self.promote_city_ruler_in_roster,0xBBDF,0xBBE2)):return
        self._a(m[0x50E])
        for _ in range(3):r.a=self._shift(r.a,True)
        self._y(r.a)
        while True:
            self._mark(0xBBE9);self._a(r.y);self._push(r.a);self._a(m[0x9D72+r.y]);self._compare(r.a,255)
            if r.p&Z:
                self._a(self._pop());self._mark(0xBBF3);self._rts();return
            yield from self._external(0xBBF4,0xF2AF,0xBBF7,'call')
            if r.pc!=0xBBF7:return
            if not(yield from self._local_call(self.promote_city_ruler_in_roster,0xBBF7,0xBBFA)):return
            self._a(self._pop());self._y(r.a);self._y(r.y+1)

    def promote_city_ruler_in_roster(self):
        """BC00: retain cityptr0A while F368 replaces00 with rulerptr.

        owner&0F==7 alone skips. The complete raw16 table is preserved.
        All10 roster slots17..26 are tested until first matching leader;
        a priorFF is not a terminator. A match performs both original stores
        even at slot17 or when both values are equal. No record/status/city
        validation is silently inserted. Each access uses the live pointer.
        """
        r,m=self.registers,self.memory;self._mark(0xBC00);self._a(m[0]);m[0x0A]=r.a;self._a(m[1]);m[0x0B]=r.a;self._y(0)
        self._a((yield from self._read_pointed(0x0A,r.y,0xBC0E)));self._a(r.a&15);self._compare(r.a,7)
        if r.p&Z:self._mark(0xBC16);self._rts();return
        yield from self._external(0xBC17,0xF368,0xBC1A,'call')
        if r.pc!=0xBC1A:return
        self._y(0);self._a((yield from self._read_pointed(0,r.y,0xBC1C)));m[2]=r.a;self._y(17)
        while True:
            self._a((yield from self._read_pointed(0x0A,r.y,0xBC23)));self._compare(r.a,m[2])
            if r.p&Z:break
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:self._mark(0xBC2F);self._rts();return
        self._a(r.y);self._push(r.a);self._y(17);self._a((yield from self._read_pointed(0x0A,r.y,0xBC34)));m[3]=r.a
        self._a(m[2]);self._mark(0xBC3C);self._write_pointed(0x0A,r.y,r.a);self._a(self._pop());self._y(r.a);self._a(m[3]);self._mark(0xBC43);self._write_pointed(0x0A,r.y,r.a)
        self._mark(0xBC45);self._rts()
