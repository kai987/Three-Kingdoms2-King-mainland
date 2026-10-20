"""Exact city pointer/scan contracts, without inventing names for raw bytes.

City+1 is one byte of an overlapping word consumed by an AI threshold. The
four trailing bytes have no identified official label. Unbounded record scans
can alias them under explicit capacity/sentinel boundary inputs; the normal
player transfer first enforces its separate ten-slot capacity check.
Production uses direct conditions and loops, never original CPU or control IR.
"""
from dataclasses import dataclass
from .global_ui_controller import UIControlBase, C, Z
from .battle_nmi_services import ServiceWait

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CITY_BASE, CITY_STRIDE, CITY_COUNT = 0x6000, 32, 30
OFFICER_BASE, OFFICER_STRIDE = 0x63C0, 12

def peaceful_transfer_goal(average_byte):
    """10:B144 raw-byte contract; normal mean occupancy0..10 gives goal4..10."""
    if not isinstance(average_byte,int)or not 0<=average_byte<256:
        raise ValueError('Original average occupancy byte required')
    value=(average_byte-2)&255
    if value>=16:value=2
    if value<2:value=2
    return value+2

@dataclass(frozen=True)
class CityAuxiliaryContract:
    """Raw view: behavioral contracts are distinct from official field names."""
    raw: bytes
    def __post_init__(self):
        if len(self.raw) != CITY_STRIDE: raise ValueError('Exactly32 original city bytes required')
    @property
    def overlapping_AI_threshold_word(self): return self.raw[1] | self.raw[2] << 8
    @property
    def passes_AI_threshold_300(self): return self.overlapping_AI_threshold_word >= 300
    @property
    def roster_count(self): return sum(value != 255 for value in self.raw[17:27])
    @property
    def bounded_roster_prefix(self):
        result=[]
        for value in self.raw[17:27]:
            if value == 255: break
            result.append(value)
        return tuple(result)
    @property
    def has_in_record_roster_terminator(self): return 255 in self.raw[17:27]
    @property
    def tail28_31(self): return self.raw[28:32]
    @classmethod
    def from_memory(cls, memory, city):
        if not isinstance(city, int) or not 0 <= city < CITY_COUNT: raise ValueError('Legal city0..29 required')
        address=CITY_BASE+CITY_STRIDE*city
        return cls(bytes(memory[address:address+CITY_STRIDE]))

class CityFieldContracts(UIControlBase):
    """Source services with actual caller registers and existing stack frames.

    F2AF/F2D7 accept raw byte indices, including indices outside legitimate
    city/officer records. D105 includes the original gold/grain cap side effect.
    F368 masks to sixteen pointer slots; only the first seven are ruler records.
    D283/D2AB preserve caller Y and read the selected officer byte. C21D is a
    complete bounded nomination scan. A442, BD95 and A71B are explicit prefixes;
    they do not pop an RTS frame or complete the larger original city command.
    """
    FIXED=(0xF2AF,0xF2D7,0xF368)
    BANKED={(10,11):(0xD105,0xD69D,0xD283,0xD2AB,0xA442,0xBD95,0xB144),
            (25,26):(0xC21D,), (27,28):(0xA71B,)}
    PUBLIC_ENTRIES=FIXED+tuple(entry for values in BANKED.values() for entry in values)
    def fields(self):
        m=self.memory
        return dict(city_pointer_00=m[0]|m[1]<<8,city_pointer_20=m[0x20]|m[0x21]<<8,
                    nomination_ID=m[0x10],nomination_virtue=m[0x11],nomination_city=m[0x40C],
                    transfer_capacity=m[0x47C])
    def run_entry(self,entry=None,*,registers=None,return_pc=None,seed_return=False,max_blocks=200000):
        if registers is None or seed_return: raise ValueError('Actual registers and existing caller frame required')
        pair=tuple(getattr(self.memory,'banks',())[1:3])
        if entry not in self.FIXED and entry not in self.BANKED.get(pair,()):
            raise ValueError('Entry does not belong to the active physical pair')
        self._boundary=None
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def _entry(self,entry):
        if entry==0xF2AF:return self.city_pointer_00()
        if entry==0xF2D7:return self.officer_pointer_00()
        if entry==0xF368:return self.ruler_or_adjoining_pointer_00()
        if entry==0xD105:return self.city_pointer_owner_and_caps()
        if entry==0xD69D:return self.cap_city_gold_grain()
        if entry==0xD283:return self.officer_pointer_read_20()
        if entry==0xD2AB:return self.officer_pointer_read_22()
        if entry==0xA442:return self.append_AI_transfer_prefix()
        if entry==0xBD95:return self.overlapping_AI_threshold_prefix()
        if entry==0xA71B:return self.player_transfer_capacity_prefix()
        if entry==0xB144:return self.peaceful_transfer_goal_prefix()
        return self.nominate_bounded_roster()
    def _drive(self):
        # A cyclic scan remains suspended; resuming only re-reads real memory.
        # No ready byte, terminator or fake caller return is generated here.
        if isinstance(self.pending,ServiceWait):self.pending=None
        while True:
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:
                    return self._result('nonlocal_return')
                return self._result('returned')
            if isinstance(self.pending,ServiceWait):return self._result('waiting')
            # All owned callees are direct local source methods. An unexpected
            # external request remains unresolved instead of being satisfied.
            return self._result('dependency')
    def _result(self,status):
        result=super()._result(status)
        if self._boundary is not None and status=='returned':
            result.update(status='bounded_prefix',boundary=self._boundary)
        return result
    def __call__(self,call):
        pair=tuple(call.entry_banks[1:3])
        if call.target not in self.FIXED and call.target not in self.BANKED.get(pair,()):return {'status':'dependency'}
        if self._program is not None:
            if getattr(self,'_call_owner',None)is not call:return {'status':'dependency'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)
    def _prefix(self,pc):
        r=self.registers;r.pc=pc;self._boundary=pc
        self._return_pc,self._return_sp=pc,r.sp
    def _record(self,z,y):
        m=self.memory;return m[((m[z]|m[(z+1)&255]<<8)+y)&65535]
    def _store_record(self,z,y,value):
        m=self.memory;m[((m[z]|m[(z+1)&255]<<8)+y)&65535]=value
    def city_pointer_00(self):
        if False:yield None
        r,m=self.registers,self.memory;self._y(0);m[1]=r.y
        for _ in range(5):
            r.a=self._shift(r.a,True);m[1]=self._shift(m[1],True,rotate=True)
        self._flag(C,False);self._add(0);m[0]=r.a;self._a(m[1]);self._add(0x60);m[1]=r.a
        self._rts()
    def _officer_pointer(self,z,zero_x=False):
        r,m=self.registers,self.memory
        if zero_x:self._x(0);m[z+1]=r.x
        else:self._y(0);m[z+1]=r.y
        m[z]=r.a;r.a=self._shift(r.a,True);m[z+1]=self._shift(m[z+1],True,rotate=True)
        self._flag(C,False);self._add(m[z]);self._push(r.a);self._a(m[z+1]);self._add(0);m[z+1]=r.a
        self._a(self._pop())
        for _ in range(2):
            r.a=self._shift(r.a,True);m[z+1]=self._shift(m[z+1],True,rotate=True)
        self._flag(C,False);self._add(0xC0);m[z]=r.a;self._a(m[z+1]);self._add(0x63);m[z+1]=r.a
    def officer_pointer_00(self):
        if False:yield None
        self._officer_pointer(0);self._rts()
    def ruler_or_adjoining_pointer_00(self):
        """31:F368..F378: raw indices7..15 read actual adjoining machine bytes."""
        if False:yield None
        r,m=self.registers,self.memory;self._a(r.a&15);r.a=self._shift(r.a,True);self._y(r.a)
        base=16+31*8192+(0xF379&8191)
        self._a(self.rom[base+r.y]);m[0]=r.a;self._a(self.rom[base+1+r.y]);m[1]=r.a
        self._rts()
    def officer_pointer_read_20(self):
        if False:yield None
        self._officer_pointer(0x20,True);self._a(self._record(0x20,self.registers.y));self._rts()
    def officer_pointer_read_22(self):
        if False:yield None
        self._officer_pointer(0x22,True);self._a(self._record(0x22,self.registers.y));self._rts()
    def city_pointer_owner_and_caps(self):
        r,m=self.registers,self.memory;self._y(0);m[0x21]=r.y
        for _ in range(5):
            r.a=self._shift(r.a,True);m[0x21]=self._shift(m[0x21],True,rotate=True)
        self._flag(C,False);self._add(0);m[0x20]=r.a;self._a(m[0x21]);self._add(0x60);m[0x21]=r.a
        if not(yield from self._local_call(self.cap_city_gold_grain,0xD123,0xD126)):return
        self._y(0);self._a(self._record(0x20,0));self._a(r.a&7);self._rts()
    def cap_city_gold_grain(self):
        if False:yield None
        for offset in(2,4):
            self._y(offset);self._a(self._record(0x20,offset));self._flag(C,True);self._add(0x10,subtract=True)
            self._y(offset+1);self._a(self._record(0x20,offset+1));self._add(0x27,subtract=True)
            if self.registers.p&C:
                self._y(offset);self._a(0x0F);self._store_record(0x20,offset,self.registers.a)
                self._y(offset+1);self._a(0x27);self._store_record(0x20,offset+1,self.registers.a)
        self._rts()
    def overlapping_AI_threshold_prefix(self):
        if False:yield None
        self._y(1);self._a(self._record(0x20,1));self._flag(C,True);self._add(0x2C,subtract=True)
        self._y(2);self._a(self._record(0x20,2));self._add(1,subtract=True)
        self._prefix(0xBDA3 if self.registers.p&C else 0xBDEE)
    def peaceful_transfer_goal_prefix(self):
        if False:yield None
        r,m=self.registers,self.memory;self._a(m[0x40]);self._flag(C,True);self._add(2,subtract=True)
        self._compare(r.a,16)
        if r.p&C:self._a(2)
        self._compare(r.a,2)
        if not r.p&C:self._a(2)
        self._flag(C,False);self._add(2);m[0x37]=r.a
        self._prefix(0xB15C)
    def append_AI_transfer_prefix(self):
        """10:A442..A44F. FF search can wrap Y; only this prefix is owned."""
        r,m=self.registers,self.memory;self._y(16)
        while True:
            for _ in range(256):
                self._y(r.y+1);self._a(self._record(0x20,r.y));self._compare(r.a,255)
                if r.p&Z:
                    self._a(m[0x3C]);self._store_record(0x20,r.y,r.a);self._prefix(0xA450);return
            r.pc=0xA444
            yield ServiceWait('roster_scan_without_FF',0xA444,reason='Original eight-bit Y scan returned to the same offset; no terminator has been supplied')
    def _count_ten_slots(self):
        if False:yield None
        r=self.registers;self._y(17);self._x(0)
        while True:
            self._a(self._record(0,r.y));self._compare(r.a,255)
            if not r.p&Z:self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        self._rts()
    def player_transfer_capacity_prefix(self):
        r,m=self.registers,self.memory;self._a(m[0x471])
        if not(yield from self._local_call(self._count_ten_slots,0xA71E,0xA721)):return
        self._compare(r.x,10)
        if r.p&Z:self._prefix(0xA777);return
        m[0x47C]=r.x;self._a(10);self._flag(C,True);self._add(m[0x47C],subtract=True);m[0x47C]=r.a
        self._a(m[0x470])
        if not(yield from self._local_call(self.city_pointer_00,0xA734,0xA737)):return
        if not(yield from self._local_call(self._count_ten_slots,0xA737,0xA73A)):return
        self._compare(r.x,m[0x47C])
        if not r.p&C:m[0x47C]=r.x
        self._prefix(0xA742)
    def nominate_bounded_roster(self):
        """26:C21D..C25C. Early FF or offset27 stops; at most ten members."""
        r,m=self.registers,self.memory;self._a(m[0]);m[2]=r.a;self._a(m[1]);m[3]=r.a
        self._y(17);m[4]=r.y
        while True:
            self._y(m[4]);self._a(self._record(2,r.y));self._compare(r.a,255)
            if r.p&Z:break
            m[0x12]=r.a
            if not(yield from self._local_call(self.officer_pointer_00,0xC23A,0xC23D)):return
            self._y(4);self._a(self._record(0,4));self._compare(r.a,m[0x11])
            if r.p&C:
                m[0x11]=r.a;self._a(m[0x12]);m[0x10]=r.a;m[0x40C]=r.x
            m[4]=self._nz(m[4]+1);self._a(m[4]);self._compare(r.a,27)
            if r.p&C:break
        self._rts()
