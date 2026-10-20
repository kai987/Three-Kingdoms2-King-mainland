"""Behavior reconstructed from the supplied NES ROM; NOT original game source.

ROM SHA256: 26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82
Fixed-bank CPU addresses and file offsets are recorded in ROUTINES.
The functions use Python integers to express tested unsigned 6502 behavior.
This module is analysis output, not a complete engine or cycle-accurate emulator.
"""
from dataclasses import dataclass, field

ROUTINES = {
    "table_a_ram_address": {"cpu":0xF2AF,"rom_offset":0x3F2BF,"size":40},
    "table_b_ram_address": {"cpu":0xF2D7,"rom_offset":0x3F2E7,"size":49},
    "table_b_initial_cpu_address": {"cpu":0xF387,"rom_offset":0x3F397,"size":54},
    "divide_u16": {"cpu":0xEA7C,"rom_offset":0x3EA8C,"size":41},
    "divide_u24_by_u16": {"cpu":0xEAA5,"rom_offset":0x3EAB5,"size":57},
    "packed_bcd6": {"cpu":0xE9BA,"rom_offset":0x3E9CA,"size":194},
    "bounded_rng": {"cpu":0xE862,"rom_offset":0x3E872,"size":24},
    "rng_next": {"cpu":0xE87A,"rom_offset":0x3E88A,"size":16},
}

def table_a_ram_address(record_id: int) -> int:
    """$F2AF: input A -> zero-page pointer $00/$01 = $6000 + A*32.

    First initial table has 30 records. Address formula is defined for all u8 A.
    """
    return 0x6000 + (record_id & 0xFF) * 32

def table_b_ram_address(record_id: int) -> int:
    """$F2D7: input A -> $00/$01 = $63C0 + A*12; 237 valid records."""
    return 0x63C0 + (record_id & 0xFF) * 12

def table_b_initial_cpu_address(record_id: int) -> int:
    """$F387: selects PRG register $31 (physical bank17), returns $8000+A*12."""
    return 0x8000 + (record_id & 0xFF) * 12

def divide_u16(dividend: int, divisor: int) -> tuple[int, int]:
    """$EA7C: $01/$02 dividend, $03/$04 divisor -> quotient $01/$02,
    remainder $05/$06. Includes the ROM's observed divisor-zero behavior.
    """
    dividend &= 0xFFFF; divisor &= 0xFFFF
    return divmod(dividend, divisor) if divisor else (0xFFFF, dividend)

def divide_u24_by_u16(dividend: int, divisor: int) -> tuple[int, int]:
    """$EAA5: $00/$01/$02 dividend, $03/$04 divisor -> quotient $00..$02,
    remainder $05..$07. Includes the ROM's observed divisor-zero behavior.
    """
    dividend &= 0xFFFFFF; divisor &= 0xFFFF
    return divmod(dividend, divisor) if divisor else (0xFFFFFF, dividend)

def packed_bcd6(value: int) -> tuple[int, int, int]:
    """$E9BA: unsigned $01..$03 -> packed BCD bytes $07,$08,$09.

    Each byte stores two decimal digits. High millions are discarded, so the
    result represents value modulo 1,000,000. Return order is least significant.
    """
    text=f"{(value & 0xFFFFFF) % 1_000_000:06d}"
    return int(text[4:6],16), int(text[2:4],16), int(text[0:2],16)

@dataclass
class PermutationRng:
    """Reconstruction of only the ROM RNG's observed state changes.

    A 256-byte permutation at CPU $E8BA, ROM $03E8CA, supplies bytes.
    Four u8 cursors correspond to RAM $50,$52,$54,$55. Each sample increments
    its cursor; NMI at CPU $F8A1 increments all four once per handled NMI.
    Timing, game state, and controller input therefore matter to reproducibility.
    """
    table: bytes
    cursors: list[int] = field(default_factory=lambda: [0,0,0,0])

    def __post_init__(self):
        if len(self.table)!=256: raise ValueError("RNG table must contain 256 bytes")
        if len(self.cursors)!=4: raise ValueError("RNG has four cursors")
        self.cursors=[v & 255 for v in self.cursors]

    def next_u8(self, cursor: int=0) -> int:
        index=self.cursors[cursor]
        self.cursors[cursor]=(index+1)&255
        return self.table[index]

    def bounded(self, bound: int) -> int:
        """$E862: rejection-sample [0,bound) from cursor0.

        bound<15 samples only the low nibble, matching the code. The real ROM
        loops forever for bound=0. This analysis API rejects that invalid bound.
        """
        if not 1<=bound<=255: raise ValueError("bound must be 1..255")
        mask=15 if bound<15 else 255
        while True:
            value=self.next_u8() & mask
            if value<bound: return value

    def tick_nmi(self):
        self.cursors=[(v+1)&255 for v in self.cursors]
