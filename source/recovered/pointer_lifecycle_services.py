"""Named city-selection/garrison pointer lifetime, physical27/28.

The selected city roster and the selected officer record are distinct pointer
generations in00/01. Division temporarily borrows that pair; D987 saves it in
10/11 and restores it before the raw troop-word writes. This module restores
the actual selection/input/packet protocol, not a new discovery of the frozen
phase5 allocation arithmetic. Production executes no ROM/IR or CPU fallback.
"""
from .city_ui_controller import CityUIController, C, Z, N, CITY, NEW_BUTTONS, PPU_JOBS


class PointerLifecycleServices(CityUIController):
    PUBLIC_ENTRIES=CityUIController.LOCAL_ENTRIES
    NAMED_ENTRIES=(0xD64A,0xD773,0xD7A8,0xD94E,0xD96F,0xD987)

    def run_entry(self,entry=0xA000,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Actual caller registers and existing frame are required')
        if seed_return:raise ValueError('Pointer lifecycle services never plant a caller frame')
        if tuple(getattr(self.memory,'banks',())[1:3])!=(27,28):raise ValueError('Physical27/28 must own the city service')
        if registers.pc!=entry:raise ValueError('Entry must equal the actual caller PC')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)

    def _pointed_byte(self,index):
        m=self.memory;return m[((m[0]|m[1]<<8)+index)&65535]

    def _write_pointed_byte(self,index,value):
        m=self.memory;m[((m[0]|m[1]<<8)+index)&65535]=value

    def select_and_allocate_officers(self):
        """D64A: common list navigation, membership selection and troop editor.

        047C selects the original list mode:15 city choice,16 troop allocation,
        other values selected-count allowance. Real text readiness is checked
        before input. A/B/end-row behavior and every local caller frame remain.
        """
        r,m=self.registers,self.memory;self._mark(0xD64A)
        self._a(m[0x425]);m[0x13]=r.a
        self._a(0x4C);m[0x10]=r.a;self._a(0xD7);m[0x11]=r.a;self._a(0);m[0x12]=r.a
        yield from self._external(0xD65F,0xED19,0xD662,'call')
        if r.pc!=0xD662:return
        self._a(m[0x12]);self._compare(r.a,m[0x47B])
        if not r.p&Z and r.p&C:
            self._x(m[0x47B]);self._a(m[0x13])
            if not r.p&Z:self._x(0)
            m[0x12]=r.x;m[0x425]=r.x
        self._a(0x58);m[0x10]=r.a;self._a(0xD7);m[0x11]=r.a
        self._a(0x6E);m[0]=r.a;self._a(0xD7);m[1]=r.a
        self._a(m[0x12]);m[0x47A]=r.a
        yield from self._external(0xD696,0xEDF5,0xD699,'call')
        if r.pc!=0xD699:return
        if not(yield from self._local_call(self.text_request_readiness,0xD699,0xD69C)):return
        if not r.p&C:self._mark(0xD6B9);self._rts();return
        self._a(m[0x47C]);self._compare(r.a,16)
        if r.p&Z:
            yield from self._allocation_mode_input();return
        self._a(m[NEW_BUTTONS]);r.a=self._shift(r.a,False)
        if r.p&C:
            self._a(m[0x47C]);self._compare(r.a,15)
            if not r.p&Z:
                self._a(m[0x12]);self._compare(r.a,m[0x47B])
                if r.p&Z:
                    # End-row compaction reads all10 entries, including holes.
                    self._x(0);self._y(0)
                    while True:
                        self._a(m[0x481+r.y]);self._compare(r.a,255)
                        if not r.p&Z:
                            m[0x481+r.x]=r.a;m[0]=r.x;self._compare(r.y,m[0])
                            if not r.p&Z:self._a(255);m[0x481+r.y]=r.a
                            self._x(r.x+1)
                        self._y(r.y+1);self._compare(r.y,10)
                        if r.p&C:break
                    self._compare(r.x,0)
                    if r.p&Z:self._mark(0xD6B9);self._rts();return
                    self._a(0x81);m[0x47C]=r.a
                    yield from self.restore_list_window();return
            self._y(m[0x12]);self._a(m[0x47C]);self._compare(r.a,15)
            if r.p&Z:
                self._a(m[0x151+r.y]);m[0x481]=r.a;self._a(m[CITY])
                if not(yield from self._local_call(self.city_helper_dd4f,0xD736,0xD739)):return
                self._compare(r.a,m[0x481])
                if r.p&Z:self._a(0x81);m[0x47C]=r.a;self._mark(0xD74B);self._rts();return
                self._a(0x80);m[0x47C]=r.a;yield from self.restore_list_window();return
            self._a(m[0x481+r.y]);self._compare(r.a,255)
            if not r.p&Z:
                self._a(255);m[0x481+r.y]=r.a;m[0x47C]=self._nz(m[0x47C]+1);self._a(1)
                if not(yield from self._local_call(self.queue_selection_marker,0xD727,0xD72A)):return
            else:
                self._a(m[0x47C])
                if not r.p&Z:
                    self._a(m[0x151+r.y]);m[0x481+r.y]=r.a;m[0x47C]=self._nz(m[0x47C]-1);self._a(0x3E)
                    if not(yield from self._local_call(self.queue_selection_marker,0xD717,0xD71A)):return
            self._mark(0xD6B9);self._rts();return
        r.a=self._shift(r.a,False)
        if r.p&C:self._a(0x90);m[0x47C]=r.a;yield from self.restore_list_window();return
        self._mark(0xD6B9);self._rts()

    def _allocation_mode_input(self):
        """D7C5: end-row A exits; other rows act only on original C0 bits."""
        r,m=self.registers,self.memory;self._a(m[0x12]);self._compare(r.a,m[0x47B])
        if r.p&Z:
            self._a(m[NEW_BUTTONS]);r.a=self._shift(r.a,False)
            if r.p&C:
                self._a(0x80);m[0x47C]=r.a;self._a(0);m[0x90]=r.a;m[0x8F]=r.a
                self._a(3);m[0x61]=r.a;self._a(m[0xC2]);self._a(0);m[0xB2]=r.a
                self._a(5);m[0xB3]=r.a;self._a(9);m[0xB4]=r.a;self._mark(0xD804);self._rts();return
        else:
            self._a(m[NEW_BUTTONS]);self._a(r.a&0xC0)
            if not r.p&Z:
                yield from self._allocate_selected_roster_member();return
        yield from self._queue_working_reserve_number()

    def _allocate_selected_roster_member(self):
        """D805: city pointer→roster ID→raw officer pointer, then right/left.

        Neither the selector nor raw troop word is silently masked to legal
        game bounds. The old999 guard precedes normalization and is not rerun.
        """
        r,m=self.registers,self.memory;self._mark(0xD805);self._a(m[CITY])
        yield from self._external(0xD808,0xF2AF,0xD80B,'call')
        if r.pc!=0xD80B:return
        self._a(m[0x12]);self._flag(C,False);self._add(17);self._y(r.a);self._a(self._pointed_byte(r.y))
        yield from self._external(0xD814,0xF2D7,0xD817,'call')
        if r.pc!=0xD817:return
        self._y(8);self._a(self._pointed_byte(r.y));m[2]=r.a;self._y(r.y+1);self._a(self._pointed_byte(r.y));m[3]=r.a
        self._a(m[NEW_BUTTONS]);r.a=self._shift(r.a,True)
        if r.p&C:
            self._a(0xE7);self._flag(C,True);self._add(m[2],subtract=True);self._a(3);self._add(m[3],subtract=True)
            if r.p&C:
                if not(yield from self._local_call(self.normalize_selected_troops,0xD837,0xD83A)):return
                self._x(100);self._a(m[0x42D])
                if r.p&Z:
                    self._a(m[0x42C]);self._compare(r.a,100)
                    if not r.p&C:self._x(m[0x42C])
                m[2]=r.x;self._y(8);self._a(self._pointed_byte(r.y));self._flag(C,False);self._add(m[2]);self._write_pointed_byte(r.y,r.a)
                self._y(r.y+1);self._a(self._pointed_byte(r.y));self._add(0);self._write_pointed_byte(r.y,r.a)
                self._a(m[0x42C]);self._flag(C,True);self._add(m[2],subtract=True);m[0x42C]=r.a
                self._a(m[0x42D]);self._add(0,subtract=True);m[0x42D]=r.a
        else:
            self._a(m[3])
            if not r.p&Z:has_troops=True
            else:self._a(m[2]);has_troops=not bool(r.p&Z)
            if has_troops:
                if not(yield from self._local_call(self.normalize_selected_troops,0xD87E,0xD881)):return
                self._a(m[5])
                if r.p&Z:
                    self._a(m[0x42C]);self._flag(C,True);self._add(0xAD,subtract=True);self._a(m[0x42D]);self._add(0x26,subtract=True)
                    if not r.p&C:
                        self._y(8);self._a(self._pointed_byte(r.y));self._flag(C,True);self._add(100,subtract=True);self._write_pointed_byte(r.y,r.a)
                        self._y(r.y+1);self._a(self._pointed_byte(r.y));self._add(0,subtract=True);self._write_pointed_byte(r.y,r.a)
                        self._a(m[0x42C]);self._flag(C,False);self._add(100);m[0x42C]=r.a;self._a(m[0x42D]);self._add(0);m[0x42D]=r.a
        # The packet re-reads the current pointed word after all mutations.
        self._y(8);self._a(self._pointed_byte(r.y));m[3]=r.a;self._y(r.y+1);self._a(self._pointed_byte(r.y));m[2]=r.a
        self._a(m[3]);m[1]=r.a;self._a(0);m[3]=r.a
        yield from self._external(0xD8CC,0xE9BA,0xD8CF,'call')
        if r.pc!=0xD8CF:return
        self._y(1);m[0xA]=r.y;self._x(0)
        if not(yield from self._local_call(self.queue_BCD_digits,0xD8D6,0xD8D9)):return
        self._a(0x80);m[0x31E+r.x]=r.a;self._a(64);m[0]=r.a;self._a(0);m[1]=r.a;m[2]=r.a
        self._a(m[0x12]);m[3]=r.a
        yield from self._external(0xD8F1,0xEBE9,0xD8F4,'call')
        if r.pc!=0xD8F4:return
        self._a(m[6]);self._flag(C,False);self._add(0xBB);m[0x31C]=r.a;self._a(m[7]);self._add(0x24);m[0x31D]=r.a
        self._finish_number_packet()
        if False:yield None

    def _queue_working_reserve_number(self):
        r,m=self.registers,self.memory;self._a(m[0x42C]);m[1]=r.a;self._a(m[0x42D]);m[2]=r.a;self._a(0);m[3]=r.a
        yield from self._external(0xD919,0xE9BA,0xD91C,'call')
        if r.pc!=0xD91C:return
        self._x(0);self._y(1);m[0xA]=r.y;self._a(m[9]);self._a(r.a&15)
        if not(yield from self._local_call(self.queue_one_BCD_digit,0xD928,0xD92B)):return
        if not(yield from self._local_call(self.queue_BCD_digits,0xD92B,0xD92E)):return
        self._a(0x80);m[0x31E+r.x]=r.a;self._a(0x3A);m[0x31C]=r.a;self._a(0x27);m[0x31D]=r.a
        self._finish_number_packet()

    def _finish_number_packet(self):
        m=self.memory;self._a(1);m[0x303]=self.registers.a;m[0x30C]=self.registers.a
        self._a(m[PPU_JOBS]);self._a(self.registers.a|1);m[PPU_JOBS]=self.registers.a;self._mark(0xD94D);self._rts()

    def queue_selection_marker(self):
        """D773: one selected-row marker packet, no ready/PPU completion."""
        r,m=self.registers,self.memory;self._mark(0xD773);m[0x31E]=r.a;self._a(0x80);m[0x31F]=r.a
        self._a(64);m[0]=r.a;self._a(0);m[1]=r.a;m[2]=r.a;m[3]=r.y
        yield from self._external(0xD78B,0xEBE9,0xD78E,'call')
        if r.pc!=0xD78E:return
        self._a(0xA2);self._flag(C,False);self._add(m[6]);m[0x31C]=r.a;self._a(0x24);self._add(m[7]);m[0x31D]=r.a
        self._a(m[PPU_JOBS]);self._a(r.a|1);m[PPU_JOBS]=r.a;self._mark(0xD7A7);self._rts()

    def restore_list_window(self):
        r,m=self.registers,self.memory;self._mark(0xD7A8);self._a(0);m[0x8F]=r.a;self._a(3);m[0x61]=r.a
        self._a(m[0xC2]);self._a(0);m[0xB2]=r.a;self._a(5);m[0xB3]=r.a;self._a(9);m[0xB4]=r.a;self._mark(0xD7C4);self._rts()
        if False:yield None

    def queue_BCD_digits(self):
        """D94E: high/low nibble packet, retaining Y0 separator behavior."""
        r,m=self.registers,self.memory
        while True:
            self._mark(0xD94E);self._a(m[(7+r.y)&65535])
            for _ in range(4):r.a=self._shift(r.a,False)
            if not(yield from self._local_call(self.queue_one_BCD_digit,0xD955,0xD958)):return
            self._compare(r.y,0)
            if r.p&Z:self._a(0x76);m[0xA]=r.a
            self._a(m[(7+r.y)&65535]);self._a(r.a&15)
            if not(yield from self._local_call(self.queue_one_BCD_digit,0xD966,0xD969)):return
            self._y(r.y-1);self._compare(r.y,255)
            if r.p&Z:break
        self._mark(0xD96E);self._rts()

    def queue_one_BCD_digit(self):
        r,m=self.registers,self.memory;self._mark(0xD96F)
        if r.p&Z:self._a(m[0xA]);m[(0x31E+r.x)&65535]=r.a
        else:
            self._flag(C,False);self._add(0x76);m[(0x31E+r.x)&65535]=r.a;self._a(0x76);m[0xA]=r.a
        self._x(r.x+1);self._mark(0xD986);self._rts()
        if False:yield None

    def normalize_selected_troops(self):
        """D987: save00/01 in10/11, divide raw word by100, restore pointer.

        D996..D99C borrow01/02 before EA7C; EA7C itself does not write00.
        The raw100 remainder is offered to the working reserve. The10000 cap
        adjusts only the overage's low byte; a nonzero resulting remainder is
        subtracted from the restored pointer's full troop word. All accesses
        remain ordered; arbitrary aliasing is not silently replaced by a pure
        formula. Legal officer records cannot alias the zero-page save cells.
        """
        r,m=self.registers,self.memory;self._mark(0xD987)
        self._a(m[0]);m[0x10]=r.a;self._a(m[1]);m[0x11]=r.a
        self._a(m[2]);m[1]=r.a;self._a(m[3]);m[2]=r.a;self._a(100);m[3]=r.a;self._a(0);m[4]=r.a
        yield from self._external(0xD9A9,0xEA7C,0xD9AC,'call')
        if r.pc!=0xD9AC:return
        self._a(m[5])
        if not r.p&Z:
            self._flag(C,False);self._add(m[0x42C]);m[0x42C]=r.a;self._a(0);self._add(m[0x42D]);m[0x42D]=r.a
            self._a(m[0x42C]);self._flag(C,True);self._add(0x10,subtract=True);m[6]=r.a;self._a(m[0x42D]);self._add(0x27,subtract=True)
            if r.p&C:
                self._a(0x10);m[0x42C]=r.a;self._a(0x27);m[0x42D]=r.a;self._a(m[5]);self._flag(C,True);self._add(m[6],subtract=True);m[5]=r.a
        self._a(m[0x10]);m[0]=r.a;self._a(m[0x11]);m[1]=r.a
        self._y(8);self._a(self._pointed_byte(r.y));self._flag(C,True);self._add(m[5],subtract=True);self._write_pointed_byte(r.y,r.a)
        self._y(r.y+1);self._a(self._pointed_byte(r.y));self._add(0,subtract=True);self._write_pointed_byte(r.y,r.a)
        self._mark(0xDA01);self._rts()

    # The frozen parent calls these exact virtual names. No caller frame is
    # added by the alias; its original _local_call already owns that frame.
    city_helper_d64a=select_and_allocate_officers
    city_helper_d773=queue_selection_marker
    city_helper_d7a8=restore_list_window
    city_helper_d94e=queue_BCD_digits
    city_helper_d96f=queue_one_BCD_digit
    city_helper_d987=normalize_selected_troops
