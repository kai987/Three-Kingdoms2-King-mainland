"""Exact early postbattle routing and AI allocation, physical8 BAC1..BF09.

The gameplay allocation was already recovered in postbattle.process_ai_officers.
This owner adds the actual registers, scratch, caller stack and data-window
protocol. It neither executes original instructions nor interprets an IR.
"""
from .postbattle_completion_services import PostbattleCompletionServices
from .battle_setup_ai import C,Z,N


class PostbattleEarlyServices(PostbattleCompletionServices):
    NEW_ENTRIES=(0xA006,0xBAB3,0xBAC1,0xBB3D,0xBC46)
    ALLOCATION_HELPERS=(0xBC52,0xBD59,0xBD67,0xBD96,0xBDCD,0xBE55,0xBE90)
    PUBLIC_ENTRIES=PostbattleCompletionServices.PUBLIC_ENTRIES+(0xBAC1,0xBB3D,0xBC46)+ALLOCATION_HELPERS
    LOCAL_ENTRIES=PUBLIC_ENTRIES

    def run_entry(self,entry=0xA006,**kwargs):
        if entry==0xBC46 and self.memory[0x6F91]>=3:
            raise ValueError('Original BC46 inline dispatch requires mode0..2')
        return super().run_entry(entry,**kwargs)

    def _entry(self,entry):
        if entry==0xBAC1:return self.route_attacking_side_disposition()
        if entry==0xBB3D:return self.route_defending_side_disposition()
        if entry==0xBC46:return self.allocate_AI_officers()
        if entry==0xBC52:return self.allocate_winning_army()
        if entry==0xBD59:return self.allocate_defeated_defender()
        if entry==0xBD67:return self.allocate_defeated_attacker()
        if entry==0xBD96:return self.fill_pointed_city_roster()
        if entry==0xBDCD:return self.collect_side_officers_and_captives()
        if entry==0xBE55:return self.prioritize_original_commander()
        if entry==0xBE90:return self.enumerate_eligible_neighbor_cities()
        return super()._entry(entry)

    def postbattle_stage_dispatch(self):
        r,m=self.registers,self.memory;self._mark(0xBAB3);self._a(m[0x501])
        index=self._dispatch(0xBAB6,(0xBAC1,0xBB3D,0xBB93,0xBBA0))
        if index==0:return(yield from self.route_attacking_side_disposition())
        if index==1:return(yield from self.route_defending_side_disposition())
        if index==2:return(yield from self.settle_and_return_supplies())
        return(yield from self.complete_after_palette_transition())

    def route_attacking_side_disposition(self):
        """BAC1: CHR pairs8/9, whole controller byte, human/AI handoff.

        Only controller==3 takes the AI branch. Human outcome!=0 requests
        main13, otherwise14; both clear substate and set050B=17. The dead
        LDA#10 atBAFD is retained before LDA#13. AI mode2/0 runs through
        the real BB36 JSR and returns toBB39 before incrementing0501.
        """
        r,m=self.registers,self.memory;self._mark(0xBAC1);self._a(8)
        for address in(0xB2,0xC2,0xCA,0xD2,0xDA):m[address]=r.a
        self._a(9)
        for address in(0xB3,0xC3,0xCB,0xD3,0xDB):m[address]=r.a
        self._a(m[0x507])
        for _ in range(4):r.a=self._shift(r.a,False)
        yield from self._external(0xBAEA,0xF368,0xBAED,'call')
        if r.pc!=0xBAED:return
        self._y(3);self._a((yield from self._read_pointed(0,r.y,0xBAEF)));self._compare(r.a,3)
        if not r.p&Z:
            m[0x6F44]=r.a;self._a(m[0x514])
            if not r.p&Z:self._a(10);self._a(13)
            else:self._a(14)
            m[0x500]=r.a;self._a(0);m[0x501]=r.a;self._a(17);m[0x50B]=r.a
            self._mark(0xBB0E if m[0x500]==13 else 0xBB1E);self._rts();return
        self._a(128);m[0x504]=r.a;self._a(m[0x514]);self._a(0 if r.p&Z else 2);m[0x6F91]=r.a
        if not(yield from self._local_call(self.allocate_AI_officers,0xBB36,0xBB39)):return
        m[0x501]=self._nz(m[0x501]+1);self._mark(0xBB3C);self._rts()

    def route_defending_side_disposition(self):
        """BB3D: low ruler nibble; humanmain13/14 or AI mode1/0.

        The actual AI JSR isBB8C and returnBB8F. No return atBB8D or
        BB37 is invented; old high-level dependency labels are historical.
        """
        r,m=self.registers,self.memory;self._mark(0xBB3D);self._a(m[0x507]);self._a(r.a&15)
        yield from self._external(0xBB42,0xF368,0xBB45,'call')
        if r.pc!=0xBB45:return
        self._y(3);self._a((yield from self._read_pointed(0,r.y,0xBB47)));self._compare(r.a,3)
        if not r.p&Z:
            m[0x6F44]=r.a;self._a(m[0x514]);self._a(14 if not r.p&Z else 13)
            m[0x500]=r.a;self._a(0);m[0x501]=r.a;self._a(2);m[0x50B]=r.a
            self._mark(0xBB74 if m[0x500]==14 else 0xBB64);self._rts();return
        self._a(0);m[0x504]=r.a;self._a(m[0x514]);self._a(0 if not r.p&Z else 1);m[0x6F91]=r.a
        if not(yield from self._local_call(self.allocate_AI_officers,0xBB8C,0xBB8F)):return
        m[0x501]=self._nz(m[0x501]+1);self._mark(0xBB92);self._rts()

    def allocate_AI_officers(self):
        """BC46: true EADE inline3 table; never manufacture a fourth mode."""
        r,m=self.registers,self.memory;self._mark(0xBC46);self._a(m[0x6F91])
        mode=self._dispatch(0xBC49,(0xBC52,0xBD59,0xBD67))
        if mode==0:return(yield from self.allocate_winning_army())
        if mode==1:return(yield from self.allocate_defeated_defender())
        return(yield from self.allocate_defeated_attacker())

    def allocate_winning_army(self):
        """BC52: collect, fill current city from17, then eligible neighbors."""
        r,m=self.registers,self.memory;self._mark(0xBC52)
        if not(yield from self._local_call(self.collect_side_officers_and_captives,0xBC52,0xBC55)):return
        self._a(m[0x50E]);m[2]=r.a;self._a(17);m[3]=r.a;self._a(0);m[4]=r.a
        if not(yield from self._local_call(self.fill_pointed_city_roster,0xBC65,0xBC68)):return
        self._compare(r.x,255)
        if r.p&Z:self._mark(0xBC6C);self._rts();return
        return(yield from self.allocate_neighbor_cities_and_release_overflow())

    def allocate_defeated_defender(self):
        """BD59: commander first, then only neighboring destinations."""
        self._mark(0xBD59)
        if not(yield from self._local_call(self.collect_side_officers_and_captives,0xBD59,0xBD5C)):return
        if not(yield from self._local_call(self.prioritize_original_commander,0xBD5C,0xBD5F)):return
        self._a(0);self.memory[4]=self.registers.a
        return(yield from self.allocate_neighbor_cities_and_release_overflow())

    def allocate_defeated_attacker(self):
        """BD67: source-city vacancies first; full city retains scratch04.

        In full-source fallback04 is not reset: the original EADE target's
        high byteBD may remain. This anomaly is kept, not normalized to0.
        """
        r,m=self.registers,self.memory;self._mark(0xBD67)
        if not(yield from self._local_call(self.collect_side_officers_and_captives,0xBD67,0xBD6A)):return
        if not(yield from self._local_call(self.prioritize_original_commander,0xBD6A,0xBD6D)):return
        self._a(m[0x52A]);m[2]=r.a
        yield from self._external(0xBD73,0xF2AF,0xBD76,'call')
        if r.pc!=0xBD76:return
        self._y(17)
        while True:
            self._a((yield from self._read_pointed(0,r.y,0xBD78)));self._compare(r.a,255)
            if r.p&Z:break
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:return(yield from self.allocate_neighbor_cities_and_release_overflow())
        m[3]=r.y;self._a(0);m[4]=r.a
        if not(yield from self._local_call(self.fill_pointed_city_roster,0xBD8E,0xBD91)):return
        self._compare(r.x,255)
        if not r.p&Z:return(yield from self.allocate_neighbor_cities_and_release_overflow())
        self._mark(0xBD95);self._rts()

    def fill_pointed_city_roster(self):
        """BD96: live city pointer, cursor04 and raw offset03, cap27.

        A first write always occurs before the CPY27 check, even for a bare
        raw offset>=27. Each id is tested only againstFF. Escaped officer
        matches write052C before the roster store using real PHA/PLA.
        """
        r,m=self.registers,self.memory;self._mark(0xBD96);self._a(m[2])
        yield from self._external(0xBD99,0xF2AF,0xBD9C,'call')
        if r.pc!=0xBD9C:return
        self._y(m[3]);self._x(m[4])
        while True:
            self._mark(0xBDA2);self._a(m[0x6FA1+r.x]);self._compare(r.a,255)
            if r.p&Z:self._x(r.a);self._mark(0xBDAA);self._rts();return
            self._compare(r.a,m[0x52B])
            if r.p&Z:self._push(r.a);self._a(m[2]);m[0x52C]=r.a;self._a(self._pop())
            self._mark(0xBDB8);self._write_pointed(0,r.y,r.a);self._x(r.x+1);self._y(r.y+1);self._compare(r.y,27)
            if not r.p&C:continue
            self._a(m[0x6FA1+r.x]);self._compare(r.a,255)
            if r.p&Z:self._x(r.a);self._mark(0xBDC8);self._rts();return
            m[4]=r.x;self._mark(0xBDCC);self._rts();return

    def collect_side_officers_and_captives(self):
        """BDCD: own original half, transferred other half,20 captives.

        sidebyteFF is skipped, but active officerIDFF is not rejected. The
        terminator fill is do-while: it writes at least oneFF even when Y
        already exceeds21. All byte counters retain their original wrap.
        """
        r,m=self.registers,self.memory;self._mark(0xBDCD);self._y(0);self._x(0);self._a(m[0x504])
        if r.p&N:self._y(128);self._x(10)
        m[0x10]=r.y;self._a(r.x);self._flag(C,False);self._add(10);m[0x11]=r.a;self._y(0)
        while True:
            self._mark(0xBDE6);self._a(m[0x628+r.x]);self._compare(r.a,255)
            if not r.p&Z:
                self._a(r.a&128);self._compare(r.a,m[0x10])
                if r.p&Z:self._a(m[0x664+r.x]);m[0x6FA1+r.y]=r.a;self._y(r.y+1)
            self._x(r.x+1);self._compare(r.x,m[0x11])
            if r.p&C:break
        self._compare(r.x,10)
        if not r.p&Z:self._x(0)
        self._a(r.x);self._flag(C,False);self._add(10);m[0x11]=r.a
        while True:
            self._mark(0xBE0E);self._a(m[0x628+r.x]);self._compare(r.a,255)
            if not r.p&Z:
                self._a(r.a&128);self._compare(r.a,m[0x10])
                if r.p&Z:self._a(m[0x664+r.x]);m[0x6FA1+r.y]=r.a;self._y(r.y+1)
            self._x(r.x+1);self._compare(r.x,m[0x11])
            if r.p&C:break
        self._x(0);self._a(m[0x504])
        if r.p&N:self._x(20)
        self._a(r.x);self._flag(C,False);self._add(20);m[0x11]=r.a
        while True:
            self._mark(0xBE39);self._a(m[0x6F47+r.x]);self._compare(r.a,255)
            if not r.p&Z:m[0x6FA1+r.y]=r.a;self._y(r.y+1)
            self._x(r.x+1);self._compare(r.x,m[0x11])
            if r.p&C:break
        self._a(255)
        while True:
            m[0x6FA1+r.y]=r.a;self._y(r.y+1);self._compare(r.y,21)
            if r.p&C:break
        self._mark(0xBE54);self._rts()
        if False:yield None

    def prioritize_original_commander(self):
        """BE55: bounded20 search;FF inside list does not end the search."""
        r,m=self.registers,self.memory;self._mark(0xBE55);self._y(0);self._a(m[0x504])
        if r.p&N:self._y(10)
        self._a(m[0x664+r.y]);self._compare(r.a,255)
        if r.p&Z:self._mark(0xBE65);self._rts();return
        m[2]=r.a;self._y(0)
        while True:
            self._a(m[0x6FA1+r.y]);self._compare(r.a,255)
            if not r.p&Z:
                self._compare(r.a,m[2])
                if r.p&Z:
                    self._a(m[0x6FA1]);m[3]=r.a;self._a(m[2]);m[0x6FA1]=r.a;self._a(m[3]);m[0x6FA1+r.y]=r.a;self._mark(0xBE89);self._rts();return
            self._y(r.y+1);self._compare(r.y,20)
            if r.p&C:self._mark(0xBE8F);self._rts();return
        if False:yield None

    def enumerate_eligible_neighbor_cities(self):
        """BE90: owner&7 equal side ruler or7; firstFF roster count.

        The adjacency iterator is byteX and stops on a negative table byte,
        not an invented eight-neighbor bound. Cache arrays clear offsets0..10.
        """
        r,m=self.registers,self.memory;self._mark(0xBE90);self._y(10);self._a(255)
        while True:
            m[0x42C+r.y]=r.a;m[0x550+r.y]=r.a;self._y(r.y-1)
            if r.p&N:break
        self._a(m[0x507]);self._y(m[0x504])
        if r.p&N:
            for _ in range(4):r.a=self._shift(r.a,False)
        self._a(r.a&15);m[0x12]=r.a;self._y(0x30)
        yield from self._external(0xBEB0,0xF25F,0xBEB3,'call')
        if r.pc!=0xBEB3:return
        self._a(m[0x50E])
        for _ in range(3):r.a=self._shift(r.a,True)
        self._x(r.a);self._a(0);m[0x15]=r.a;m[0x16]=r.a
        while True:
            self._mark(0xBEC2);self._a(m[0x9D72+r.x])
            if r.p&N:self._mark(0xBEC7);self._rts();return
            m[0x13]=r.a;m[0x14]=r.x
            yield from self._external(0xBECE,0xF2AF,0xBED1,'call')
            if r.pc!=0xBED1:return
            self._y(0);self._a((yield from self._read_pointed(0,r.y,0xBED3)));self._a(r.a&7);self._compare(r.a,7)
            eligible=bool(r.p&Z)
            if not eligible:self._compare(r.a,m[0x12]);eligible=bool(r.p&Z)
            if eligible:
                self._a(m[0x13]);self._y(m[0x16]);m[0x42C+r.y]=r.a;self._y(17);self._x(0)
                while True:
                    self._a((yield from self._read_pointed(0,r.y,0xBEED)));self._compare(r.a,255)
                    if r.p&Z:break
                    self._x(r.x+1);self._y(r.y+1);self._compare(r.y,27)
                    if r.p&C:break
                self._y(m[0x16]);self._a(r.x);m[0x550+r.y]=r.a;m[0x16]=self._nz(m[0x16]+1)
            self._x(m[0x14]);self._x(r.x+1)

    def allocate_neighbor_cities_and_release_overflow(self):
        """BC6D: nonempty neighbors, empty neighbors, then status overflow.

        Filling a neutral/empty destination replaces the whole owner byte;
        no recruitment/status2 is added for rostered records. Only overflow
        clears low2 to0, except special comparisons that OR3. Scratch02 is
        first the ruler's leader but later becomes u8(city<<3), so following
        officer IDs may compare against the row byte instead of the leader.
        """
        r,m=self.registers,self.memory;self._mark(0xBC6D)
        if not(yield from self._local_call(self.enumerate_eligible_neighbor_cities,0xBC6D,0xBC70)):return
        self._y(0)
        while True:
            self._mark(0xBC72);self._a(m[0x42C+r.y]);self._compare(r.a,255)
            if r.p&Z:break
            m[2]=r.a;self._a(m[0x550+r.y])
            if not r.p&Z:
                self._compare(r.a,10)
                if not r.p&Z:
                    self._flag(C,False);self._add(17);m[3]=r.a;m[5]=r.y
                    if not(yield from self._local_call(self.fill_pointed_city_roster,0xBC8E,0xBC91)):return
                    self._compare(r.x,255)
                    if r.p&Z:self._mark(0xBC95);self._rts();return
                    self._y(m[5])
            self._y(r.y+1);self._compare(r.y,8)
            if r.p&C:break
        self._a(m[0x507]);self._y(m[0x504])
        if r.p&N:
            for _ in range(4):r.a=self._shift(r.a,False)
        self._a(r.a&15);m[0x0A]=r.a;self._y(0)
        while True:
            self._mark(0xBCB1);self._a(m[0x42C+r.y]);self._compare(r.a,255)
            if r.p&Z:break
            m[2]=r.a;self._a(m[0x550+r.y])
            if r.p&Z:
                self._flag(C,False);self._add(17);m[3]=r.a;m[5]=r.y
                if not(yield from self._local_call(self.fill_pointed_city_roster,0xBCC9,0xBCCC)):return
                self._y(17);self._a((yield from self._read_pointed(0,r.y,0xBCCE)));self._compare(r.a,255)
                if not r.p&Z:self._y(0);self._a(m[0x0A]);self._mark(0xBCD9);self._write_pointed(0,r.y,r.a)
                self._compare(r.x,255)
                if r.p&Z:self._mark(0xBCDF);self._rts();return
                self._y(m[5])
            self._y(r.y+1);self._compare(r.y,8)
            if r.p&C:break
        self._a(m[0x507]);self._y(m[0x504])
        if r.p&N:
            for _ in range(4):r.a=self._shift(r.a,False)
        self._a(r.a&15)
        yield from self._external(0xBCF6,0xF368,0xBCF9,'call')
        if r.pc!=0xBCF9:return
        self._y(0);self._a((yield from self._read_pointed(0,r.y,0xBCFB)));m[2]=r.a;self._x(m[4])
        while True:
            self._mark(0xBD03);self._a(m[0x6FA1+r.x]);m[3]=r.a;self._compare(r.a,255)
            if r.p&Z:self._mark(0xBD0D);self._rts();return
            self._a(m[3]);self._compare(r.a,m[2])
            if r.p&Z:
                self._a(m[3])
                yield from self._external(0xBD19,0xF2D7,0xBD1C,'call')
                if r.pc!=0xBD1C:return
                self._y(11);self._a((yield from self._read_pointed(0,r.y,0xBD1E)));self._a(r.a|3);self._mark(0xBD22);self._write_pointed(0,r.y,r.a);self._x(r.x+1);continue
            yield from self._external(0xBD28,0xF2D7,0xBD2B,'call')
            if r.pc!=0xBD2B:return
            self._y(11);self._a((yield from self._read_pointed(0,r.y,0xBD2D)));self._a(r.a&252);self._mark(0xBD31);self._write_pointed(0,r.y,r.a)
            self._y(0x30)
            yield from self._external(0xBD35,0xF266,0xBD38,'call')
            if r.pc!=0xBD38:return
            self._a(m[0x50E])
            for _ in range(3):r.a=self._shift(r.a,True)
            m[2]=r.a
            yield from self._external(0xBD41,0xE856,0xBD44,'call')
            if r.pc!=0xBD44:return
            self._flag(C,False);self._add(m[2]);self._y(r.a);self._a(m[0x9D72+r.y])
            if r.p&N:self._a(m[0x50E])
            self._y(5);self._mark(0xBD53);self._write_pointed(0,r.y,r.a);self._x(r.x+1)
