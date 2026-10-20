"""Named postbattle release/allocation, physical13 D1F9..D2CC.

Destination30 is an actual UI-created special value, not a real city record.
The same selected-officer loop handles ordinary destinations and releases.
Existing battle parents call the aliases below, preserving their genuine
JSR frames. No status, location, RNG or readiness is prepared on their behalf.
"""
from .battle_scene_controller import BattleSceneController,BattleRegisters,C,Z,N,ROM_SHA256

SELECTED_FLAGS=0x580
OFFICER_LIST=0x42C
DESTINATION=0x540
BATTLE_CITY=0x50E
ACTIVE_IDS=0x664
CAPTIVE_IDS=0x6F47

class PostbattleReleaseController(BattleSceneController):
    """Exact caller form plus named source for selected release/allocation.

    The ordinary battle wrapper and phases remain independently recovered
    source from the frozen parent. This module replaces only212 original
    code bytes; BC11 and E856 are existing direct-source local helpers.
    """
    NEW_ENTRIES=(0xD1F9,0xD20D,0xD299)
    def _entry(self,entry):
        if entry==0xD299:return self.remove_departed_unit_or_captive()
        return super()._entry(entry)

    def run_entry(self,entry=0xA028,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Actual battle caller registers and existing software frame required')
        if seed_return:raise ValueError('A postbattle caller must not be seeded')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(12,13):raise ValueError('Postbattle release requires actual physical12/13 mapping')
        actual=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual:raise ValueError('ReturnPC differs from the actual caller stack')
        return super().run_entry(entry,registers=registers,seed_return=False,return_pc=actual,max_blocks=max_blocks)

    def settle_selected_officers(self):
        """D1F9: process20 selection bytes; negative means unselected.

        Original PHA/PLA protects the row across each allocation/release.
        The selected list and flags remain in RAM until the real parent
        rebuilds them; this procedure does not clear their UI requests.
        """
        r,m=self.registers,self.memory;self._mark(0xD1F9);self._y(0)
        while True:
            self._mark(0xD1FB);self._a(m[SELECTED_FLAGS+r.y])
            if not r.p&N:
                self._a(r.y);self._push(r.a)
                if not(yield from self._local_call(self.settle_one_selected_officer,0xD202,0xD205)):return
                self._a(self._pop());self._y(r.a)
            self._y(r.y+1);self._compare(r.y,20)
            if r.p&C:self._mark(0xD20C);self._rts();return

    def settle_one_selected_officer(self):
        """D20D: release at destination30, otherwise append to a real city.

        The real UI has already selected the row and destination. A bare
        direct entry deliberately does not rerun UI eligibility: caller
        fixtures must distinguish valid rows from raw alias experiments.
        """
        r,m=self.registers,self.memory;self._mark(0xD20D);self._a(m[DESTINATION]);self._compare(r.a,30)
        if r.p&Z:
            self._a(m[OFFICER_LIST+r.y]);self._push(r.a)
            yield from self._external(0xD218,0xF2D7,0xD21B,'call',None)
            if r.pc!=0xD21B:return
            self._y(11);self._a(self._pointed(r.y));self._a(r.a&252);self._write_pointed(r.y,r.a)
            self._y(48)
            yield from self._external(0xD225,0xF266,0xD228,'call',None)
            if r.pc!=0xD228:return
            self._a(m[BATTLE_CITY])
            for _ in range(3):r.a=self._shift(r.a,True)
            m[2]=r.a
            if not(yield from self._local_call(self.random_eight,0xD231,0xD234)):return
            self._flag(C,False);self._add(m[2]);self._y(r.a);self._a(m[0x9D72+r.y])
            if r.p&N:self._a(m[BATTLE_CITY])
            self._y(5);self._write_pointed(r.y,r.a);self._a(self._pop())
        else:
            # BC11 returns the actual destination pointer00 and firstFF Y.
            # Its parent context uses050B temporarily, and must restore it.
            self._a(r.y);self._push(r.a);self._a(m[0x50B]);self._push(r.a)
            self._a(m[DESTINATION]);m[0x50B]=r.a
            if not(yield from self._local_call(self.local_bc11,0xD255,0xD258)):return
            self._a(self._pop());m[0x50B]=r.a;self._a(self._pop());self._x(r.a)
            self._a(m[OFFICER_LIST+r.x]);self._compare(r.a,m[0x52B])
            if r.p&Z:self._x(m[DESTINATION]);m[0x52C]=r.x
            self._write_pointed(r.y,r.a);self._push(r.a)
            self._y(0);self._a(self._pointed(r.y));self._a(r.a&7);self._compare(r.a,7)
            if r.p&Z:
                self._y(m[0x507]);self._a(m[0x50B]);self._a(r.a&240)
                if not r.p&Z:
                    self._a(r.y)
                    for _ in range(4):r.a=self._shift(r.a,False)
                    self._y(r.a)
                self._a(r.y);self._a(r.a&15);m[2]=r.a
                self._y(0);self._a(self._pointed(r.y));self._a(r.a&240);self._a(r.a|m[2]);self._write_pointed(r.y,r.a)
            self._a(self._pop())
        return(yield from self.remove_departed_unit_or_captive())

    def remove_departed_unit_or_captive(self):
        """D299: remove only the first matching active slot or captive entry.

        Active IDs take priority. A match clears six20-byte battle arrays;
        otherwise scan the contiguous40-byte captive pools and clear only
        that ID byte. It does not remove the officer from city rosters.
        """
        r,m=self.registers,self.memory;self._mark(0xD299);self._x(0)
        while True:
            self._compare(r.a,m[ACTIVE_IDS+r.x])
            if r.p&Z:
                self._a(255)
                for base in(0x600,0x614,0x628,0x63C,0x650,0x664):m[base+r.x]=r.a
                self._mark(0xD2C6);self._rts();return
            self._x(r.x+1);self._compare(r.x,20)
            if r.p&C:break
        self._x(0)
        while True:
            self._compare(r.a,m[CAPTIVE_IDS+r.x])
            if r.p&Z:
                self._a(255);m[CAPTIVE_IDS+r.x]=r.a;self._mark(0xD2CC);self._rts();return
            self._x(r.x+1);self._compare(r.x,40)
            if r.p&C:self._mark(0xD2B1);self._rts();return
        if False:yield None

    def _pointed(self,y):
        m=self.memory;return m[((m[0]|m[1]<<8)+y)&65535]
    def _write_pointed(self,y,value):
        m=self.memory;m[((m[0]|m[1]<<8)+y)&65535]=value

    # Bind original local-call names so the actual battle parent uses these
    # methods without a new JSR frame or a runtime PC/opcode dispatcher.
    local_d1f9=settle_selected_officers
    local_d20d=settle_one_selected_officer
