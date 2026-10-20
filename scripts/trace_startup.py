#!/usr/bin/env python3
"""Bounded synchronous 6502 startup trace, NOT a complete NES emulator.

Dependency: py65==1.2.0. See analysis/trace/README.md for limitations.
Only input ROM is read; all output is written to the selected output directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
from collections import Counter, deque
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler


class Bus:
    def __init__(self, rom: bytes, status_mode: str):
        if rom[:4] != b"NES\x1a":
            raise ValueError("Not an iNES file")
        self.mapper = (rom[6] >> 4) | (rom[7] & 0xF0)
        if self.mapper != 19:
            raise ValueError(f"This trace only models mapper 19; got {self.mapper}")
        offset = 16 + (512 if rom[6] & 4 else 0)
        self.prg_file_offset = offset
        self.prg = rom[offset:offset + rom[4] * 16384]
        self.bank_count = len(self.prg) // 8192
        self.ram = bytearray(2048)
        self.sram = bytearray(8192)
        self.sound = bytearray(128)
        # Switchable power-on banks are deliberately assumed. Startup code
        # selects banks before executing in these windows in the default run.
        self.banks = [0, 1, self.bank_count - 2, self.bank_count - 1]
        self.bank_initialized = [False, False, False, True]
        self.regs = bytearray(32)
        self.ppu = bytearray(8)
        self.ppu_address = 0
        self.ppu_latch = 0
        self.vram = bytearray(16384)
        self.status_mode = status_mode
        self.status_reads = 0
        self.sound_address = 0
        self.sound_increment = False
        self.protect = 0
        self.irq_regs = bytearray(2)
        self.step_no = 0
        self.pc = 0
        self.cpu = None
        self.mapper_events = []
        self.io_events = []
        self.state_events = []
        self.ram_zero_coverage = set()
        self.ram_writes = Counter()
        self.sram_writes = Counter()
        self.blocked_sram_writes = 0
        self.rom_reads = Counter()
        self.uninitialized_bank_reads = Counter()

    def origin(self, address):
        if address < 0x8000:
            return None
        window = (address - 0x8000) // 8192
        bank = self.banks[window]
        prg_offset = bank * 8192 + (address & 8191)
        return bank, prg_offset

    def peek(self, address):
        """Read for instruction display without IO side effects."""
        address &= 0xFFFF
        if address >= 0x8000:
            return self.prg[self.origin(address)[1]]
        if address < 0x2000:
            return self.ram[address & 0x7FF]
        if 0x6000 <= address < 0x8000:
            return self.sram[address - 0x6000]
        return 0

    def __getitem__(self, address):
        if isinstance(address, slice):
            return [self[i] for i in range(address.start or 0, address.stop, address.step or 1)]
        address &= 0xFFFF
        if address < 0x2000:
            return self.ram[address & 0x7FF]
        if address < 0x4000:
            reg = address & 7
            if reg == 2:
                self.ppu_latch = 0
                self.status_reads += 1
                # Deliberately synthetic vblank handshake: this lets both BPL
                # and BMI wait loops progress without pretending to render.
                return (0x80 if self.status_reads & 1 else 0) if self.status_mode == "alternating" else 0
            if reg == 7:
                result = self.vram[self.ppu_address & 0x3FFF]
                self.ppu_address = (self.ppu_address + (32 if self.ppu[0] & 4 else 1)) & 0x3FFF
                return result
            return 0
        if address in (0x4015, 0x4016, 0x4017):
            # No active APU channels, no controller buttons. This is an input
            # assumption; actual NES open bus bits are not emulated.
            return 0
        if 0x4800 <= address < 0x5000:
            value = self.sound[self.sound_address]
            if self.sound_increment:
                self.sound_address = min(self.sound_address + 1, 0x7F)
            return value
        if 0x5000 <= address < 0x6000:
            return self.irq_regs[(address - 0x5000) // 0x800]
        if 0x6000 <= address < 0x8000:
            return self.sram[address - 0x6000]
        if address >= 0x8000:
            bank, offset = self.origin(address)
            self.rom_reads[(bank, offset & 8191)] += 1
            window = (address - 0x8000) // 8192
            if not self.bank_initialized[window]:
                self.uninitialized_bank_reads[(bank, address)] += 1
            return self.prg[offset]
        return 0

    def event(self, address, value, **extra):
        return {"step": self.step_no, "pc": self.pc, "cpu_address": address,
                "value": value, "cycles": self.cpu.processorCycles if self.cpu else 0, **extra}

    def __setitem__(self, address, value):
        address &= 0xFFFF
        value &= 0xFF
        if address < 0x2000:
            index = address & 0x7FF
            previous = self.ram[index]
            self.ram[index] = value
            self.ram_writes[index] += 1
            if value == 0 and self.pc == 0xE04D:
                self.ram_zero_coverage.add(index)
            if index == 0x7A:
                self.state_events.append(self.event(address, value, previous=previous))
        elif address < 0x4000:
            reg = address & 7
            self.ppu[reg] = value
            if reg in (0, 1):
                self.io_events.append(self.event(0x2000 + reg, value))
            if reg == 6:
                if self.ppu_latch == 0:
                    self.ppu_address = (value & 0x3F) << 8
                else:
                    self.ppu_address = (self.ppu_address & 0x3F00) | value
                self.ppu_latch ^= 1
            elif reg == 5:
                self.ppu_latch ^= 1
            elif reg == 7:
                self.vram[self.ppu_address & 0x3FFF] = value
                self.ppu_address = (self.ppu_address + (32 if self.ppu[0] & 4 else 1)) & 0x3FFF
        elif address < 0x4020:
            self.regs[address - 0x4000] = value
            self.io_events.append(self.event(address, value))
        elif 0x4800 <= address < 0x5000:
            self.sound[self.sound_address] = value
            if self.sound_increment:
                self.sound_address = min(self.sound_address + 1, 0x7F)
        elif 0x5000 <= address < 0x6000:
            self.irq_regs[(address - 0x5000) // 0x800] = value
            self.mapper_events.append(self.event(address, value, kind="irq_register_no_clock"))
        elif 0x6000 <= address < 0x8000:
            if self.protect & 0xF0 == 0x40 and not (self.protect & (1 << ((address - 0x6000) // 2048))):
                self.sram[address - 0x6000] = value
                self.sram_writes[address] += 1
            else:
                self.blocked_sram_writes += 1
        elif address >= 0x8000:
            register = address & 0xF800
            if register in (0xE000, 0xE800, 0xF000):
                index = (register - 0xE000) // 0x800
                previous = self.banks[index]
                self.banks[index] = (value & 0x3F) % self.bank_count
                self.bank_initialized[index] = True
                self.mapper_events.append(self.event(address, value, kind="prg_bank",
                    window_start=0x8000 + index * 8192, previous_bank=previous, bank=self.banks[index]))
            elif register == 0xF800:
                self.protect = value
                self.sound_address = value & 0x7F
                self.sound_increment = bool(value & 0x80)
                self.mapper_events.append(self.event(address, value, kind="ram_protect_and_sound_address"))
            else:
                self.mapper_events.append(self.event(address, value, kind="chr_or_nametable_selection_recorded_only"))


class PeekBus:
    def __init__(self, bus):
        self.bus = bus

    def __getitem__(self, address):
        return self.bus.peek(address)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--out", type=Path, default=Path("analysis/trace"))
    parser.add_argument("--max-instructions", type=int, default=250_000)
    parser.add_argument("--ppustatus", choices=("alternating", "zero"), default="alternating")
    parser.add_argument("--repeat-limit", type=int, default=2000)
    parser.add_argument("--entry-case", choices=("startup", "sram-init"), default="startup")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rom = args.rom.read_bytes()
    bus = Bus(rom, args.ppustatus)
    cpu = MPU(memory=bus, pc=None)
    bus.cpu = cpu
    # 2A03 power-on I flag is set; startup immediately executes SEI as well.
    cpu.p |= cpu.INTERRUPT
    if args.entry_case == "sram-init":
        # An isolated subroutine harness, explicitly not a power-on path.
        # $DD8B in physical bank 30 receives writable SRAM and RTS -> $0200.
        bus.banks = [0, 29, 30, 31]
        bus.bank_initialized = [False, True, True, True]
        bus.protect = 0x4C
        bus.sram[:] = b"\xA5" * 8192
        bus.sram[0xF43] = 0x37
        cpu.pc = 0xDD8B
        cpu.sp = 0xFD
        bus.ram[0x1FE:0x200] = b"\xFF\x01"
    display_cpu = MPU(memory=PeekBus(bus))
    disassembler = Disassembler(display_cpu)
    records = {}
    entry_counts = Counter()
    edges = Counter()
    recent = deque(maxlen=64)
    last_instruction = None
    checkpoints = []
    reason = "instruction_budget"
    repeated = Counter()
    unknown = None
    initial_zero_clear = None
    for step in range(args.max_instructions):
        pc = cpu.pc
        if args.entry_case == "sram-init" and pc == 0x0200:
            reason = "isolated_subroutine_returned"
            break
        bus.step_no, bus.pc = step, pc
        origin = bus.origin(pc)
        bank = origin[0] if origin else -1
        key = (bank, pc)
        if pc == 0xE05E and initial_zero_clear is None:
            initial_zero_clear = {"step": step, "zeroed_unique_ram_addresses": len(bus.ram_zero_coverage),
                "zeroed_ranges": compact_ranges(sorted(bus.ram_zero_coverage)),
                "ram_sha256": hashlib.sha256(bus.ram).hexdigest()}
        if pc == 0xE066:
            state = bus.ram[0x7A] & 0x1F
            pointer = 0xE07C + state * 2
            target = bus.peek(pointer) | bus.peek(pointer + 1) << 8
            if checkpoints and checkpoints[-1]["state"] == state and checkpoints[-1]["target"] == target and checkpoints[-1]["banks"] == bus.banks:
                checkpoints[-1]["count"] += 1
                checkpoints[-1]["last_step"] = step
            else:
                checkpoints.append({"step": step, "last_step": step, "count": 1,
                    "kind": "state_dispatch", "state": state, "target": target, "banks": list(bus.banks)})
        opcode = bus.peek(pc)
        if cpu.disassemble[opcode][0] == "???":
            reason = "unsupported_opcode"
            unknown = {"pc": pc, "bank": bank, "opcode": opcode}
            break
        length, mnemonic = disassembler.instruction_at(pc)
        if key not in records:
            records[key] = {"bank": bank, "physical_bank": bank, "cpu_pc": pc, "cpu_address": pc,
                "prg_offset": origin[1] if origin else None,
                "file_offset": origin[1] + bus.prg_file_offset if origin else None,
                "rom_offset": origin[1] + bus.prg_file_offset if origin else None, "size": length,
                "bytes": bytes(bus.peek(pc + i) for i in range(length)).hex(),
                "instruction": mnemonic, "first_step": step, "count": 0,
                "banks_at_first_execution": list(bus.banks)}
        records[key]["count"] += 1
        if last_instruction is not None:
            edges[(last_instruction[0], last_instruction[1], bank, pc)] += 1
        if last_instruction is None or last_instruction[2] in (0x20, 0x4C, 0x6C, 0x40):
            entry_counts[key] += 1
        last_instruction = (bank, pc, opcode)
        recent.append({"step": step, "bank": bank, "pc": pc, "instruction": mnemonic,
            "a": cpu.a, "x": cpu.x, "y": cpu.y, "sp": cpu.sp, "p": cpu.p})
        cpu.step()
        # A high repeat count only terminates an unchanging register/state
        # configuration. The RAM-clear loop changes X/Y or its pointer.
        signature = (bank, pc, cpu.a, cpu.x, cpu.y, cpu.sp, tuple(bus.banks), bus.ram[0x7A], bus.ram[1], bus.ram[2], bus.ram[0x7B])
        repeated[signature] += 1
        if repeated[signature] >= args.repeat_limit:
            reason = "repeated_cpu_configuration_no_interrupts"
            break
    count = sum(r["count"] for r in records.values())
    executed_banks = Counter()
    for record in records.values():
        executed_banks[record["bank"]] += record["count"]
    summary = {"format": "bounded_6502_trace_v1", "entry_case": args.entry_case,
        "rom_sha256": hashlib.sha256(rom).hexdigest(),
        "py65_version": importlib.metadata.version("py65"), "mapper": bus.mapper,
        "reset_vector": rom[bus.prg_file_offset + len(bus.prg) - 4] | rom[bus.prg_file_offset + len(bus.prg) - 3] << 8,
        "instruction_count": count, "cpu_cycles_py65": cpu.processorCycles, "stop_reason": reason,
        "stop_pc": cpu.pc, "stop_bank": bus.origin(cpu.pc)[0] if bus.origin(cpu.pc) else None,
        "final_banks": bus.banks, "executed_banks_instruction_counts": dict(sorted(executed_banks.items())),
        "unique_instruction_starts": len(records), "unsupported_opcode": unknown,
        "ppustatus_reads": bus.status_reads, "ppustatus_model": args.ppustatus,
        "initial_zero_clear": initial_zero_clear, "state_writes_007a": bus.state_events,
        "dispatch_checkpoints": checkpoints, "blocked_sram_writes": bus.blocked_sram_writes,
        "sram_written_unique_bytes": len(bus.sram_writes),
        "switchable_prg_reads_before_register_initialization": len(bus.uninitialized_bank_reads),
        "assumptions": ["Not a complete NES emulator; no PPU renderer, NMI/IRQ injection, DMA timing, APU audio or cycle-accurate IO.",
            "All RAM and SRAM start at zero; power-on switchable PRG banks assumed 0, 1, 30 for this 32-bank ROM.",
            "Controller inputs and APU status return zero; no buttons are pressed.",
            "PPUSTATUS alternates vblank bit on consecutive reads when alternating mode is selected; this is synthetic, not measured NES timing.",
            "PPU writes are stored for inspection, without CHR/nametable banking or read buffering semantics.",
            "N163 PRG banking uses low six register bits modulo PRG bank count; external RAM protection is modeled.",
            "N163 internal RAM is modeled with a saturating auto-increment address; expansion audio and IRQ counter clocks are not implemented.",
            "py65 NMOS 6502 executes documented opcodes; this trace stops on unsupported opcodes. Decimal arithmetic is not disabled in the core, but startup clears decimal mode."],
        "sources": ["https://www.nesdev.org/wiki/Namco_163", "https://www.nesdev.org/wiki/Namco_163_audio",
            "https://github.com/mnaberez/py65"], "recent_instructions": list(recent)}
    if args.entry_case == "sram-init":
        checks = []
        for bank, source, destination, size in [(16, 0x8C00, 0x6000, 960), (17, 0x8000, 0x63C0, 2880)]:
            source_offset = bank * 8192 + (source & 8191)
            expected = bus.prg[source_offset:source_offset + size]
            actual = bus.sram[destination - 0x6000:destination - 0x6000 + size]
            checks.append({"physical_bank": bank, "raw_selector": bank + 32,
                "source_cpu_address": source, "source_prg_offset": source_offset,
                "destination_cpu_address": destination, "size": size,
                "bytewise_equal": actual == expected,
                "expected_sha256": hashlib.sha256(expected).hexdigest(),
                "actual_sha256": hashlib.sha256(actual).hexdigest()})
        summary["isolated_sram_copy_checks"] = checks
        summary["preserved_sram_6f43"] = bus.sram[0xF43]
        summary["harness_initialization"] = "PC=$DD8B in physical bank 30; banks=[0,29,30,31]; SRAM writable via assumed $F800=$4C; SRAM filled $A5 except $6F43=$37; stack return=$0200. No claim that reset reached this routine."
    write_json(args.out / "summary.json", summary)
    write_json(args.out / "mapper_writes.json", bus.mapper_events)
    write_json(args.out / "io_writes.json", bus.io_events)
    write_json(args.out / "executed_instructions.json", sorted(records.values(), key=lambda r: (r["bank"], r["cpu_pc"])))
    write_json(args.out / "entry_seeds.json", [{"bank": b, "cpu_address": pc, "count": n,
        "prg_offset": b * 8192 + (pc & 8191) if b >= 0 else None} for (b, pc), n in sorted(entry_counts.items())])
    write_json(args.out / "executed_byte_ranges.json", executed_ranges(records.values()))
    write_json(args.out / "rom_read_ranges.json", [{"bank": b,
        "bank_offset_ranges_inclusive": compact_ranges(sorted(offset for bank, offset in bus.rom_reads if bank == b)),
        "read_count": sum(n for (bank, offset), n in bus.rom_reads.items() if bank == b)} for b in sorted({bank for bank, offset in bus.rom_reads})])
    with (args.out / "executed_instructions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bank", "cpu_pc_hex", "file_offset_hex", "bytes", "instruction", "first_step", "count"])
        for record in sorted(records.values(), key=lambda r: (r["bank"], r["cpu_pc"])):
            writer.writerow([record["bank"], f'{record["cpu_pc"]:04X}', f'{record["file_offset"]:06X}' if record["file_offset"] is not None else "", record["bytes"], record["instruction"], record["first_step"], record["count"]])
    with (args.out / "control_flow_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["from_bank", "from_pc_hex", "to_bank", "to_pc_hex", "count"])
        for (fb, fp, tb, tp), n in sorted(edges.items()):
            writer.writerow([fb, f"{fp:04X}", tb, f"{tp:04X}", n])
    (args.out / "final_ram.bin").write_bytes(bus.ram)
    (args.out / "final_sram.bin").write_bytes(bus.sram)
    (args.out / "final_n163_internal_ram.bin").write_bytes(bus.sound)
    print(json.dumps({k: summary[k] for k in ("entry_case", "instruction_count", "stop_reason", "stop_pc", "final_banks", "executed_banks_instruction_counts", "unique_instruction_starts", "initial_zero_clear", "state_writes_007a", "dispatch_checkpoints", "switchable_prg_reads_before_register_initialization")}, ensure_ascii=False, indent=2))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_ranges(values):
    result = []
    for value in values:
        if result and result[-1][1] + 1 == value:
            result[-1][1] = value
        else:
            result.append([value, value])
    return result


def executed_ranges(records):
    per_bank = {}
    for record in records:
        if record["bank"] < 0:
            continue
        per_bank.setdefault(record["bank"], set()).update(range(record["prg_offset"], record["prg_offset"] + len(bytes.fromhex(record["bytes"]))))
    return [{"bank": b, "prg_offset_ranges_inclusive": compact_ranges(sorted(values)), "byte_count": len(values)} for b, values in sorted(per_bank.items())]


if __name__ == "__main__":
    main()
