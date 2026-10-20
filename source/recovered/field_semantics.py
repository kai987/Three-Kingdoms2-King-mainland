"""Evidence-bound affinity consumers and unresolved city bytes.

Code 3 has no identified official name or initial-record producer. Its display
and formation lookups really spill into adjoining immutable ROM bytes. These
functions preserve that behavior; they do not create a fourth named ability.
Production runs direct rules and real service continuations, never 6502/IR.
"""
from dataclasses import dataclass
from .global_ui_controller import UIControlBase, UIRegisters, C, Z, N

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OFFICER_BASE, OFFICER_STRIDE, CITY_BASE, CITY_STRIDE = 0x63C0, 12, 0x6000, 32

def affinity_code(flags):
    if not isinstance(flags, int) or not 0 <= flags <= 255:
        raise ValueError('An original officer flag byte is required')
    return (flags >> 2) & 3

@dataclass(frozen=True)
class CityUnresolvedFields:
    """Read-only raw view. Generic record copies are accesses, not field names."""
    raw: bytes
    def __post_init__(self):
        if len(self.raw) != 32: raise ValueError('An exact 32-byte city record is required')
    @property
    def byte1(self): return self.raw[1]
    @property
    def overlapping_assignment_word(self): return self.raw[1] | self.raw[2] << 8
    @property
    def tail28_31(self): return self.raw[28:32]
    @classmethod
    def from_memory(cls, memory, city):
        if not isinstance(city, int) or not 0 <= city < 30: raise ValueError('City0..29 is required')
        base = CITY_BASE + CITY_STRIDE * city
        return cls(bytes(memory[base:base+32]))

class AffinityFieldServices(UIControlBase):
    """Direct field consumers, selected by the caller's actual physical pair.

    Public entry B630 is a complete upper glyph helper. B64D is deliberately
    only the glyph prefix: the original falls through into troop rendering.
    A796 expects the caller's already-pushed terrain above its RTS frame.
    CB2F is the affinity suffix of the original terrain resolver. D102 is the
    complete formation-parameter helper. DD2F includes its real DB03 refresh.
    All callers supply registers and existing frames; no seed or fake return.
    """
    ENTRIES = {(25,26): (0xB630,0xB64D), (12,13): (0xA7E7,0xDD2F),
               (8,9): (0xA796,), (14,15): (0xCB2F,0xD102)}
    PUBLIC_ENTRIES = (0xB630,0xB64D,0xA7E7,0xDD2F,0xA796,0xCB2F,0xD102)
    def fields(self):
        m=self.memory
        return dict(selected_unit=m[0x509], AP=m[0x505], formation_background=m[0x544],
                    formation_object_index=m[0x545], upper_glyph_pair=list(m[0x38B:0x38D]))
    def run_entry(self,entry=None,*,registers=None,return_pc=None,seed_return=False,max_blocks=200000):
        if registers is None or seed_return: raise ValueError('Actual registers and existing caller stack are required')
        pair=tuple(getattr(self.memory,'banks',())[1:3])
        if entry not in self.ENTRIES.get(pair,()): raise ValueError('Entry/caller physical pair outside the owned field domain')
        self._prefix = entry == 0xB64D
        if entry == 0xA796:
            r=registers
            frame_sp=(r.sp+1)&255
            actual=((self.memory[0x100+((frame_sp+1)&255)]|self.memory[0x100+((frame_sp+2)&255)]<<8)+1)&65535
            if return_pc is not None and return_pc != actual: raise ValueError('The terrain-bearing caller frame must match')
            result=super().run_entry(entry,registers=r,return_pc=actual,max_blocks=max_blocks)
            return result
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def _drive(self):
        # A796 consumes one real caller-owned PHA byte as well as its RTS frame.
        if self._program is not None and getattr(self,'_ai_stack',False):
            self._return_sp=(self._entry_sp+3)&255
        return super()._drive()
    def _entry(self,entry):
        self._entry_sp=self.registers.sp; self._ai_stack=entry==0xA796
        if self._ai_stack: self._return_sp=(self._entry_sp+3)&255
        if entry==0xB630: return self.upper_glyph_pair()
        if entry==0xB64D: return self.lower_glyph_prefix()
        if entry==0xA7E7: return self.player_movement_quote()
        if entry==0xA796: return self.ai_movement_quote_suffix()
        if entry==0xCB2F: return self.terrain_affinity_suffix()
        if entry==0xD102: return self.formation_parameters()
        return self.refresh_unit_affinity_cache()
    def _result(self,status):
        result=super()._result(status)
        if self._prefix and status=='returned': result['status']='bounded_prefix';result['boundary']=0xB663
        return result
    def __call__(self,call):
        pair=tuple(call.entry_banks[1:3])
        if call.target not in self.ENTRIES.get(pair,()): return {'status':'dependency'}
        if self._program is not None:
            if self._call_owner is not call: return {'status':'dependency'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)
    def _rom_byte(self,bank,cpu): return self.rom[16+bank*8192+(cpu&8191)]
    def _read_record(self,pointer,offset):
        m=self.memory;return m[((m[pointer]|m[(pointer+1)&255]<<8)+offset)&65535]
    def _extract_affinity(self,pointer):
        self._y(11);self._a(self._read_record(pointer,11))
        self._a(self._shift(self.registers.a,False));self._a(self._shift(self.registers.a,False))
        self._a(self.registers.a&3)
    def upper_glyph_pair(self):
        """25:B630..B646. Code3 reads A0,0B from next procedure's opcodes."""
        if False: yield None
        r,m=self.registers,self.memory
        self._extract_affinity(0x10);self._a(self._shift(r.a,True));self._y(r.a)
        self._a(self._rom_byte(25,0xB647+r.y));m[0x38B]=r.a
        self._a(self._rom_byte(25,0xB648+r.y));m[0x38C]=r.a
        self._rts()
    def lower_glyph_prefix(self):
        """25:B64D..B662. Code3 reads actual 4A,4A; stop before troop UI."""
        if False: yield None
        r,m=self.registers,self.memory
        self._extract_affinity(0x10);self._a(self._shift(r.a,True));self._y(r.a)
        self._a(self._rom_byte(25,0xB713+r.y));m[0x38B]=r.a
        self._a(self._rom_byte(25,0xB714+r.y));m[0x38C]=r.a
        r.pc=0xB663;self._return_pc=r.pc;self._return_sp=r.sp
    def player_movement_quote(self):
        """12:A7E7..A822; cost0 for code3 in all seven physical table rows."""
        r,m=self.registers,self.memory
        self._push(r.a);self._y(m[0x509]);self._a(m[0x664+r.y])
        yield from self._external(0xA7EE,0xF2D7,0xA7F1,'call')
        if r.pc!=0xA7F1:return
        self._extract_affinity(0);m[0]=r.a
        self._a(self._pop());self._a(self._shift(r.a,True));self._a(self._shift(r.a,True));self._a(r.a|m[0]);self._y(r.a)
        self._x(m[0x509]);self._a(m[0x63C+r.x]);self._compare(r.a,6)
        base=0xA823 if r.p&C else 0xA83F
        self._a(self._rom_byte(12,base+r.y));self._x(r.a)
        self._a(m[0x505]);self._flag(C,True);self._add(self._rom_byte(12,base+r.y),subtract=True)
        self._rts()
    def ai_movement_quote_suffix(self):
        """8:A796..A7CC. Retain the two reads of byte8, not byte8/byte9."""
        if False:yield None
        r,m=self.registers,self.memory
        self._extract_affinity(0x20);m[0x22]=r.a
        self._a(self._pop());self._a(self._shift(r.a,True));self._a(self._shift(r.a,True));self._a(r.a|m[0x22]);self._x(r.a)
        self._y(8);self._a(self._read_record(0x20,8));self._flag(C,True);self._add(0x59,subtract=True)
        self._a(self._read_record(0x20,8));self._add(2,subtract=True)
        base=0xA7CD if r.p&C else 0xA7E9
        self._a(self._rom_byte(8,base+r.x));self._y(r.a);self._a(m[0x505]);self._flag(C,True)
        self._add(self._rom_byte(8,base+r.x),subtract=True);self._rts()
    def terrain_affinity_suffix(self):
        """15:CB2F..CB58. The caller already excludes terrain0/1/5."""
        r,m=self.registers,self.memory
        self._push(r.a);self._y(0);self._a(m[0x545]);self._compare(r.a,11)
        if r.p&C:self._y(r.y+1)
        self._a(m[0x560+r.y])
        yield from self._external(0xCB3D,0xF2D7,0xCB40,'call')
        if r.pc!=0xCB40:return
        self._extract_affinity(0);self._y(r.a);self._a(self._pop());self._x(r.a)
        self._compare(r.a,self._rom_byte(15,0xCBE9+r.y))
        matched=bool(r.p&Z)
        if not matched:
            self._compare(r.a,self._rom_byte(15,0xCBED+r.y));matched=bool(r.p&Z)
        if matched:self._a(0)
        self._y(r.a);self._rts()
    def formation_parameters(self):
        """15:D102..D1AF. Code3 indexes adjoining D1C8 parameter records."""
        r,m=self.registers,self.memory
        m[0xA]=r.a;m[0xB]=r.x;self._a(m[0xC])
        yield from self._external(0xD10B,0xF2D7,0xD10E,'call')
        if r.pc!=0xD10E:return
        self._extract_affinity(0)
        for _ in range(3):self._a(self._shift(r.a,True))
        self._flag(C,False);self._add(m[0x544]);self._y(r.a)
        self._a(self._rom_byte(15,0xD1B0+r.y));m[0xD]=r.a
        self._a(m[0x57A]);self._compare(r.a,4)
        if r.p&C:self._a(m[0xD]);self._flag(C,False);self._add(4);m[0xD]=r.a
        self._x(m[0xD]);self._y(m[0xA]);self._a(m[0x544]);self._compare(r.a,5)
        if not r.p&Z:
            for i in range(4):self._a(self._rom_byte(15,0xD1C8+r.x+i));m[0x550+r.y+i]=r.a
            self._rts();return
        self._compare(r.y,4)
        if not r.p&C:
            self._a(2);m[0x550+r.y]=r.a;self._a(0)
            for i in range(1,4):m[0x550+r.y+i]=r.a
            self._a(m[0x57A]);self._compare(r.a,4)
            if r.p&C:self._a(0);m[0x550+r.y]=r.a
            self._rts();return
        self._a(2)
        for i in range(4):m[0x550+r.y+i]=r.a
        self._a(m[0x57A]);self._compare(r.a,6)
        if r.p&C:self._a(0);m[0x551+r.y]=r.a
        self._y(1);self._x(0)
        while True:
            self._a(m[0x580+r.y]);self._compare(r.a,8)
            if not r.p&C:self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,11)
            if r.p&C:break
        self._compare(r.x,0)
        if r.p&Z:self._a(0);m[0x556]=r.a
        self._rts()
    def refresh_unit_affinity_cache(self):
        """13:DD2F..DD71 plus DB03. Slot side is bit7; affinity is low2."""
        r,m=self.registers,self.memory
        self._x(19)
        while True:
            self._a(m[0x664+r.x]);self._compare(r.a,255)
            if not r.p&Z:
                yield from self._external(0xDD38,0xF2D7,0xDD3B,'call')
                if r.pc!=0xDD3B:return
                self._a(255);m[0x600+r.x]=r.a;m[0x614+r.x]=r.a
                self._extract_affinity(0);self._compare(r.x,10)
                if r.p&C:self._a(r.a|128)
                m[0x628+r.x]=r.a;self._a(0);m[0x650+r.x]=r.a
            else:
                for base in (0x600,0x614,0x628,0x63C,0x650):m[base+r.x]=r.a
            self._x(r.x-1)
            if r.p&N:break
        if not (yield from self._local_call(self.refresh_hundred_troop_cache,0xDD6E,0xDD71)):return
        self._rts()
    def refresh_hundred_troop_cache(self):
        r,m=self.registers,self.memory
        self._y(0x31)
        yield from self._external(0xDB05,0xF25F,0xDB08,'call')
        if r.pc!=0xDB08:return
        self._x(19)
        while True:
            self._a(m[0x664+r.x]);self._compare(r.a,255)
            if not r.p&Z:
                yield from self._external(0xDB11,0xF2D7,0xDB14,'call')
                if r.pc!=0xDB14:return
                self._a(r.x);self._push(r.a);self._y(8);self._a(self._read_record(0,8));self._push(r.a)
                self._y(9);self._a(self._read_record(0,9));self._a(r.a&3);m[1]=r.a
                self._a(self._pop());m[0]=r.a;self._a(0);m[2]=r.a;self._a(100);m[3]=r.a;self._a(0);m[4]=r.a
                yield from self._external(0xDB37,0xEAA5,0xDB3A,'call')
                if r.pc!=0xDB3A:return
                self._a(self._pop());self._x(r.a);self._a(m[0])
            m[0x63C+r.x]=r.a;self._x(r.x-1)
            if r.p&N:break
        self._rts()
