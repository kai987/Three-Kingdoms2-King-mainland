"""Read original Nestopia snapshots without altering the ROM or save state.

The layout is pinned to libretro/nestopia 135dfa6, NstCpu::SaveState,
NstMemory::SaveState and retro_serialize. This is a snapshot reader, not a CPU
trace, emulator, or replacement for timing/PPU/APU/interrupt state.
"""
from dataclasses import dataclass
import struct
import zlib
from .service_memory import ServiceMemory


class CapturedServiceMemory(ServiceMemory):
    """Explicit service bus with the pinned core's N163 address wrap.

    The frozen historical bus saturates at127. This additive variant follows
    NstBoardNamcot163.cpp: the next address is (address+increase)&127.
    Other hardware reads, timing and interrupt arrivals remain caller inputs.
    """
    def io_read(self, address):
        port = address & 65535
        native = 0x4800 <= port < 0x5000 and 0x4800 not in self.read_ports
        before, increase = self.n163_address, self.n163_autoincrement
        value = super().io_read(address)
        if native and increase:
            self.n163_address = (before + 1) & 127
        return value

    def io_write(self, address, value):
        port = address & 65535
        before, increase = self.n163_address, self.n163_autoincrement
        super().io_write(address, value)
        if 0x4800 <= port < 0x5000 and increase:
            self.n163_address = (before + 1) & 127


@dataclass(frozen=True)
class Chunk:
    tag: bytes
    offset: int
    payload: bytes


def chunks(data, start=0, end=None):
    """Walk one declared container, rejecting partial or escaping children."""
    end = len(data) if end is None else end
    if not 0 <= start <= end <= len(data):
        raise ValueError('Invalid container bounds')
    result = []
    while start < end:
        if end - start < 8:
            raise ValueError('Truncated chunk header')
        size = struct.unpack_from('<I', data, start + 4)[0]
        after = start + 8 + size
        if after > end:
            raise ValueError('Chunk escapes its parent')
        result.append(Chunk(data[start:start + 4], start, data[start + 8:after]))
        start = after
    return tuple(result)


def unique(items, tag):
    selected = [item for item in items if item.tag == tag]
    if len(selected) != 1:
        raise ValueError('Missing or duplicate ' + repr(tag))
    return selected[0]


def uncompress(payload, size):
    if not payload:
        raise ValueError('Missing compression tag')
    if payload[0] == 0:
        result = payload[1:]
    elif payload[0] == 1:
        # Bounded decompression: reject compressed trailing data/oversized output.
        obj = zlib.decompressobj()
        try:
            result = obj.decompress(payload[1:], size + 1)
        except zlib.error as exc:
            raise ValueError('Invalid compressed block') from exc
        if not obj.eof or obj.unused_data or obj.unconsumed_tail:
            raise ValueError('Invalid compressed block')
    else:
        raise ValueError('Unsupported compression tag')
    if len(result) != size:
        raise ValueError('Unexpected uncompressed size')
    return result


@dataclass(frozen=True)
class NestopiaContext:
    registers: dict
    ram: bytes
    sram: bytes
    prg_banks: tuple
    prg_source_indices: tuple
    n163_ram: bytes
    n163_address: int
    n163_autoincrement: bool
    n163_IRQ_saved_bytes: bytes
    stream_bytes: int
    footer: bytes
    register_payload_offset: int
    ram_payload_offset: int
    sram_payload_offset: int

    @classmethod
    def parse(cls, data):
        if len(data) < 8 or data[:4] != b'NST\x1a':
            raise ValueError('Not a Nestopia state')
        end = 8 + struct.unpack_from('<I', data, 4)[0]
        if end > len(data):
            raise ValueError('Truncated state stream')
        top = chunks(data, 8, end)
        cpu = unique(top, b'CPU\0')
        cpu_parts = chunks(data, cpu.offset + 8, cpu.offset + 8 + len(cpu.payload))
        reg = unique(cpu_parts, b'REG\0')
        if len(reg.payload) != 7:
            raise ValueError('Expected seven CPU register bytes')
        lo, hi, sp, a, x, y, p = reg.payload
        registers = dict(a=a, x=x, y=y, p=p, sp=sp, pc=lo | hi << 8)
        ram = unique(cpu_parts, b'RAM\0')
        img = unique(top, b'IMG\0')
        image_parts = chunks(data, img.offset + 8, img.offset + 8 + len(img.payload))
        mapper = unique(image_parts, b'MPR\0')
        mapper_parts = chunks(data, mapper.offset + 8, mapper.offset + 8 + len(mapper.payload))
        sram = unique(mapper_parts, b'WRM\0')
        prg = unique(mapper_parts, b'PRG\0')
        prg_parts = chunks(data, prg.offset + 8, prg.offset + 8 + len(prg.payload))
        banks = unique(prg_parts, b'BNK\0').payload
        if len(banks) != 12:
            raise ValueError('Expected four PRG pages for this N163 ROM')
        sources = tuple(banks[i] for i in range(0, 12, 3))
        pages = tuple(banks[i + 1] | banks[i + 2] << 8 for i in range(0, 12, 3))
        # The pinned ROM has 32 8KiB ROM pages and no PRG-RAM page at $8000.
        if any(sources) or any(bank >= 32 for bank in pages):
            raise ValueError('Unsupported PRG source or page')
        n163 = unique(mapper_parts, b'N63\0')
        n163_parts = chunks(data, n163.offset + 8, n163.offset + 8 + len(n163.payload))
        irq = unique(n163_parts, b'IRQ\0').payload
        sound = unique(n163_parts, b'SND\0')
        sound_parts = chunks(data, sound.offset + 8, sound.offset + 8 + len(sound.payload))
        sound_reg = unique(sound_parts, b'REG\0').payload
        if len(sound_reg) != 1 or len(irq) != 3:
            raise ValueError('Unexpected N163 saved register size')
        sound_ram = uncompress(unique(sound_parts, b'RAM\0').payload, 128)
        footer = data[end:]
        if footer and (len(footer) < 12 or any(footer[8:])):
            raise ValueError('Unexpected tracked-input footer or padding')
        return cls(registers, uncompress(ram.payload, 2048),
                   uncompress(sram.payload, 8192), pages, sources, sound_ram,
                   sound_reg[0] & 127, bool(sound_reg[0] & 128), irq, end, footer,
                   reg.offset + 8, ram.offset + 8, sram.offset + 8)

    def service_memory(self, rom, **hardware_inputs):
        """Copy the captured memory/banks; hardware behavior remains explicit."""
        memory = CapturedServiceMemory(rom, self.ram, self.sram, self.prg_banks, **hardware_inputs)
        memory.n163_ram[:] = self.n163_ram
        memory.n163_address = self.n163_address
        memory.n163_autoincrement = self.n163_autoincrement
        return memory
