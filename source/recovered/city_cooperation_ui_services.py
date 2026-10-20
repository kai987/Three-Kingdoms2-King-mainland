"""Actual ruler/AI-turn badge OAM and two-line header producer (29 A042).

Immutable graphics records are data. This module neither executes original
code nor consumes/acknowledges the produced PPU job. The existing caller stack,
scratch, registers, bank writes and ordered OAM writes are preserved.
"""
from dataclasses import dataclass
import hashlib
from .scene_shared_services import SceneSharedServices
from .battle_nmi_services import C,Z,N,D
from .officers import ROM_SHA256

@dataclass(frozen=True)
class CityCooperationData:
    captions:bytes
    sprite_y:bytes
    sprite_x:bytes
    badge_records:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned city cooperation UI ROM required')
        def raw(bank,address,size):
            offset=16+bank*8192+(address&8191);return bytes(rom[offset:offset+size])
        return cls(raw(29,0xAB08,48),raw(29,0xABB8,13),raw(29,0xABC5,13),raw(17,0x8DB4,13*256))

class CityCooperationUIServices(SceneSharedServices):
    """Physical29/30 A042 -> AA37, including local AB38 badge producer.

    Scratch0A is caption0..3 orFF (blank),0B is raw badge ID orFF (none),
    and0C nonzero suppresses the header producer. Every raw badge byte is
    addressable;237..254 are not asserted to be normal officer identities.
    OAM7C wraps as the original byte cursor. Only actual PPU-request7E|4
    is written; job completion is left to the real text/PPU consumers.
    """
    PUBLIC_ENTRIES=(0xA042,0xAA37,0xAB38)
    FIXED=SceneSharedServices.FIXED+PUBLIC_ENTRIES
    def __init__(self,memory,rom_or_data,services=None):
        if isinstance(rom_or_data,CityCooperationData):
            # Shared fixed helpers retain their own independently pinned ROM
            # data; caller must supply the original ROM via explicit memory.
            rom=memory.rom;self.data=rom_or_data
        else:rom=rom_or_data;self.data=CityCooperationData.from_rom(rom)
        super().__init__(memory,rom,callbacks=services)
        self._owner_call=None
    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(29,30)or call.target not in self.PUBLIC_ENTRIES:
            return {'status':'dependency','reason':'Not an owned city cooperation UI pair/entry'}
        if self._program is not None:
            if self._owner_call is not call:return {'status':'dependency','reason':'Actual caller already owns pending UI service'}
            result=self.resume()
        else:
            self._owner_call=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':self._owner_call=None
        return result
    def run_entry(self,entry=0xA042,registers=None):
        if registers is None:raise ValueError('Supply actual caller registers and existing stack')
        if entry not in self.PUBLIC_ENTRIES:raise ValueError('Unowned city cooperation UI entry')
        if registers.p&D:raise ValueError('CPU oracle contract requires decimal flag clear')
        if entry!=0xAB38 and self.memory[0xC]==0 and self.memory[0xA]not in(0,1,2,3,255):
            raise ValueError('Caption selector is0..3 orFF; reject original table-external access')
        def body():
            self.registers.pc=entry
            yield from self.routine(entry)
            self.rts()
        return self._start(body,registers,'city_cooperation_UI')
    def routine(self,entry):
        if entry in(0xA042,0xAA37):yield from self.prepare_turn_header()
        elif entry==0xAB38:yield from self.draw_ruler_badge()
        else:yield from super().routine(entry)
    def prepare_turn_header(self):
        """AA37..AB07: preserve inputs, draw badge and produce two tile rows."""
        r=self.registers;m=self.memory
        for address in(0xA,0xB,0xC):self.a(m[address]);self.push(r.a)
        self.a(m[0xB]);self.cmp(r.a,255)
        if not r.p&Z:yield from self.call(0xAA4A,0xAB38)
        for address in(0xC,0xB,0xA):self.a(self.pop());m[address]=r.a
        self.a(m[0xC])
        if not r.p&Z:return
        self.y(48);self.a(1)
        while True:
            m[0x380+r.y]=r.a;self.y(r.y-1)
            if r.p&N:break
        self.a(m[0xA]);self.cmp(r.a,255)
        if not r.p&Z:
            self.shift_a('asl');self.flag(C,False);self.add(m[0xA]);self.shift_a('asl');self.shift_a('asl');self.y(r.a)
            for source,destination in((0,0x38D),(1,0x38E),(2,0x38F),(3,0x390),(4,0x391),(5,0x392),
                    (6,0x3A0),(7,0x3A1),(8,0x3A2),(9,0x3A3),(10,0x3A4),(11,0x3A5)):
                self.a(self.data.captions[r.y+source]);m[destination]=r.a
            for value,address in((118,0xBD),(192,0x389),(193,0x38A),(208,0x39C),(209,0x39D)):
                self.a(value);m[address]=r.a
            self.a(255)  # real AADC overwritten by AADE
        for value,address in((16,0x380),(16,0x393),(34,0x381),(200,0x382),(34,0x394),(232,0x395),(255,0x3A6)):
            self.a(value);m[address]=r.a
        self.a(m[0x7E]);self.a(r.a|4);m[0x7E]=r.a
        yield from ()
    def draw_ruler_badge(self):
        """AB38..ABB7:13-byte data record, centered12-tile OAM badge.

        Original EBE9 computes13*rawID in6/7; F25F selects17 for the record.
        Four-tile empty columns shift the centering byte by16. The second loop
        stops at its firstFF tile, then preserves the byte OAM cursor exactly.
        """
        r=self.registers;m=self.memory;self.y(49);yield from self.call(0xAB3A,0xF25F)
        self.a(m[0xB]);m[0]=r.a;self.a(0);m[1]=r.a;m[2]=r.a;self.a(13);m[3]=r.a
        yield from self.call(0xAB50,0xEBE9)
        self.a(m[6]);self.flag(C,False);self.add(180);m[0]=r.a;self.a(m[7]);self.add(141);m[1]=r.a
        pointer=m[0]|m[1]<<8;offset=pointer-0x8DB4
        self.y(0);self.a(self.data.badge_records[offset]);m[0xB9]=r.a
        self.x(48);self.y(1)
        while True:
            self.a(self.data.badge_records[offset+r.y]);self.cmp(r.a,255)
            if r.p&Z:break
            self.a(r.x);self.flag(C,True);self.add(16,subtract=True);self.x(r.a)
            for _ in range(4):self.y(r.y+1)
            self.cmp(r.y,13)
            if r.p&C:break
        m[2]=r.x;self.x(m[0x7C]);self.y(1)
        while True:
            self.a(self.data.badge_records[offset+r.y]);self.cmp(r.a,255)
            if r.p&Z:break
            self.flag(C,False);self.add(192);m[0x201+r.x]=r.a
            self.a(self.data.sprite_y[r.y]);m[0x200+r.x]=r.a
            self.a(self.data.sprite_x[r.y]);self.flag(C,False);self.add(m[2]);m[0x203+r.x]=r.a
            self.a(1);m[0x202+r.x]=r.a
            for _ in range(4):self.x(r.x+1)
            self.y(r.y+1);self.cmp(r.y,13)
            if r.p&C:break
        m[0x7C]=r.x
