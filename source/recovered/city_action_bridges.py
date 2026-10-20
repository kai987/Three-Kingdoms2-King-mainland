"""Exact bounded city action services: shop offers and recruitment loyalty.

These are newly recovered readable functions. Immutable ROM tables are data;
no original code, opcode interpreter or control IR runs on the source side.
Every entry consumes the existing caller frame. No ready flag, hardware input
or external service is required or synthesized by either bounded body.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,NMIRegisters,C,D

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'


@dataclass(frozen=True)
class CityActionData:
    prices:tuple
    offers:bytes

    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
            raise ValueError('Pinned original city-action ROM required')
        offset=16+9*8192+0x89E
        prices=tuple(int.from_bytes(rom[offset+2*i:offset+2*i+2],'little')for i in range(32))
        offers=bytes(rom[offset+64:offset+160])
        if len(offers)!=96 or any(item>=32 for item in offers):
            raise ValueError('Original bounded equipment table required')
        return cls(prices,offers)


class CityActionBridges(BattleNMIServices):
    """Physical8/9 shop list and physical10/11 loyalty caller protocols.

    Shop input scratch00 is one of six data groups; 0012 is category0..3.
    The observed city caller supplies group0..2 from physical28 C801[city].
    Loyalty uses raw byte IDs in30/31; FF still addresses raw SRAM, without
    asserting it represents a valid officer. Only byte3 is changed. Flags,
    scratch, caller stack residue and actual RTS are part of the contract.
    """
    SHOP_ENTRIES=(0xA01E,0xC851)
    LOYALTY_ENTRIES=(0xA006,0xCF3F,0xD2AB,0xD40F,0xD61E)
    ENTRIES=SHOP_ENTRIES+LOYALTY_ENTRIES

    def __init__(self,memory,rom_or_data,services=None):
        super().__init__(memory,services)
        self.data=rom_or_data if isinstance(rom_or_data,CityActionData)else CityActionData.from_rom(rom_or_data)

    def __call__(self,call):
        pair=(8,9)if call.target in self.SHOP_ENTRIES else(10,11)
        if call.target not in self.ENTRIES or tuple(call.entry_banks[1:3])!=pair:
            return {'status':'dependency','reason':'City action does not own this exact pair/entry'}
        return self.run_entry(call.target,call.registers)

    def run_entry(self,entry=0xA01E,registers=None):
        if entry not in self.ENTRIES:raise ValueError('Unrecovered city-action entry')
        r=registers or NMIRegisters()
        if r.p&D:raise ValueError('CPU oracle contract requires decimal flag clear')
        if entry in self.SHOP_ENTRIES:
            if not 0<=self.memory[0]<6 or not 0<=self.memory[0x12]<4:
                raise ValueError('Shop table requires group0..5 and category0..3')
        self.registers=r;r.pc=entry
        if entry in self.SHOP_ENTRIES:self.prepare_shop_offers()
        elif entry in(0xA006,0xCF3F):self.adjust_recruitment_loyalty()
        elif entry==0xD2AB:self.officer_field_pointer()
        elif entry==0xD40F:self.divide_scratch_word()
        # D61E is the original one-byte RTS hook, not a guessed service.
        self.rts()
        return self.result('returned')

    def local(self,call_pc,method):
        """Preserve a real local JSR frame and its free-stack residue."""
        word=call_pc+2;self.push(word>>8);self.push(word)
        method();self.rts()

    def shift_memory(self,address,rotate=False):
        old=self.memory[address];incoming=bool(self.registers.p&C)
        self.flag(C,old&128)
        self.memory[address]=self.nz((old<<1)|(incoming if rotate else 0))

    def prepare_shop_offers(self):
        """9 C851..C89D: four IDs, four LE16 prices and zero byte tags.

        The two original tables are C89E[32 words] and C8DE[96 bytes].
        Category selects four adjacent offers inside a16-byte group. This
        only prepares selection data: it neither buys nor pays for an item.
        """
        m=self.memory;r=self.registers
        self.a(m[0])
        for _ in range(4):self.shift_a('asl')
        m[0]=r.a;self.a(m[0x12]);self.shift_a('asl');self.shift_a('asl')
        self.flag(C,False);self.add(m[0]);self.y(r.a);self.x(0)
        while True:
            self.a(self.data.offers[r.y]);m[0x44C+r.x]=r.a
            self.shift_a('asl');m[0]=r.a
            self.a(r.y);self.push(r.a);m[1]=r.x
            self.a(r.x);self.shift_a('asl');self.flag(C,False);self.add(m[1]);self.x(r.a)
            self.y(m[0]);price=self.data.prices[r.y>>1]
            self.a(price&255);m[0x42C+r.x]=r.a;self.y(r.y+1)
            self.a(price>>8);m[0x42D+r.x]=r.a
            self.a(0);m[0x42E+r.x]=r.a;self.x(m[1]);self.a(self.pop());self.y(r.a)
            self.y(r.y+1);self.x(r.x+1);self.cmp(r.x,4)
            if r.p&C:return

    def officer_field_pointer(self):
        """11 D2AB..D2D2: $22/23=63C0+12*rawA; read the given Y field."""
        m=self.memory;r=self.registers
        self.x(0);m[0x23]=r.x;m[0x22]=r.a
        self.shift_a('asl');self.shift_memory(0x23,True);self.flag(C,False);self.add(m[0x22])
        self.push(r.a);self.a(m[0x23]);self.add(0);m[0x23]=r.a;self.a(self.pop())
        for _ in range(2):self.shift_a('asl');self.shift_memory(0x23,True)
        self.flag(C,False);self.add(0xC0);m[0x22]=r.a
        self.a(m[0x23]);self.add(0x63);m[0x23]=r.a
        self.a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535])

    def divide_scratch_word(self):
        """11 D40F..D437: 16 restoring steps, quotient21/22, remainder25/26.

        Divisor23/24 is raw LE16; zero follows the original16-step result
        rather than raising or silently substituting a mathematical divisor.
        """
        m=self.memory;r=self.registers;self.a(0);m[0x25]=m[0x26]=r.a;self.y(15)
        while True:
            for address in(0x21,0x22,0x25,0x26):self.shift_memory(address,address!=0x21)
            self.a(m[0x25]);self.flag(C,True);self.add(m[0x23],subtract=True);m[0x27]=r.a
            self.a(m[0x26]);self.add(m[0x24],subtract=True)
            if r.p&C:
                m[0x26]=r.a;self.a(m[0x27]);m[0x25]=r.a;self.inc(0x21)
            self.y(r.y-1)
            if r.y&128:return

    def adjust_recruitment_loyalty(self):
        """11 CF3F..CF7B: virtue//10 +70 minus old loyalty, wrap then clamp.

        Reads leader30 field4 and target31 field3, writes only target byte3.
        It does not alter ownership, city rosters, residence, status or troops.
        The already recovered OfficerTransfer core has this same game rule;
        here its real local pointer/division/caller protocol is also retained.
        """
        m=self.memory;r=self.registers
        self.a(m[0x30]);self.y(4);self.local(0xCF43,self.officer_field_pointer);m[0x21]=r.a
        self.a(10);m[0x23]=r.a;self.a(0);m[0x22]=m[0x24]=r.a
        self.local(0xCF52,self.divide_scratch_word)
        self.a(m[0x21]);self.flag(C,False);self.add(70);self.push(r.a)
        self.a(m[0x31]);self.y(3);self.local(0xCF5F,self.officer_field_pointer);m[0x20]=r.a
        self.a(self.pop());self.flag(C,True);self.add(m[0x20],subtract=True)
        self.cmp(r.a,90)
        if r.p&C:self.a(90)
        self.cmp(r.a,10)
        if not r.p&C:self.a(10)
        self.y(3);m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        # CF78 JSR D61E followed by CF7B RTS. The former is truly empty
        # in this pinned ROM, yet its original stack write still occurs.
        self.local(0xCF78,lambda:None)
