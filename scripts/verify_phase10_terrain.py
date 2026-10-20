#!/usr/bin/env python3
"""Small original-CPU check of DB46 and the presentation terrain overlay.

The ROM is read only. ROM-descriptor cases are explicit typed CPU fixtures,
not claims that these four-byte windows were naturally used as map headers.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.game_engine import GameEngine, ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_graphics_services import GraphicsData

# DB46 uses arithmetic/pointer scratch 0000..0008 and the real stack. The
# terrain API does not expose them or returned CPU registers other than A.
RAM_SCOPE = [*range(0x10, 0x100), *range(0x200, 0x800)]
PIN_FILES = (
    'source/recovered/tactic_presentation_effects.py',
    'source/recovered/battle_presentation_services.py',
    'source/recovered/battle_graphics_services.py',
    'source/recovered/tactic_area_conversion.py',
    'source/recovered/tactical_decisions.py',
    'source/recovered/tactical_effects_complete.py',
    'source/recovered/tactical_effects.py',
    'source/recovered/tactic_individual_effects.py',
    'source/recovered/battle.py',
    'source/recovered/game_algorithms.py',
    'source/recovered/officer_transfer.py',
    'source/recovered/officers.py',
    'source/recovered/service_memory.py',
    'source/recovered/mapped_memory.py',
    'source/recovered/game_engine.py',
    'scripts/verify_battle_graphics_services.py',
    'scripts/trace_startup.py',
    'scripts/verify_phase10_terrain.py',
)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def verify(rom, out):
    if sha(rom) != ROM_SHA256:
        raise ValueError('Terrain comparison requires the pinned original ROM')
    graphics = GraphicsData.from_rom(rom)
    counts, samples, failures, guards = Counter(), [], [], []
    coverage = Counter()
    base = ROOT / 'analysis/phase9/runtime/tactic-09-levelup/cast-confirmation'
    ram_path, sram_path = Path(str(base) + '-ram.bin'), Path(str(base) + '-sram.bin')
    base_ram, base_sram = ram_path.read_bytes(), sram_path.read_bytes()

    def fresh(bank, pointer, x, y, descriptor=None):
        b = PortBus(rom)
        b.ram[:] = base_ram
        b.sram[:] = base_sram
        b.banks = [bank, 12, 13, 31]
        b.bank_initialized = [True] * 4
        b.protect = 0x4C
        b.ram[0xDE:0xE4] = bytes([38, 44, 45, bank + 32, 44, 45])
        b.ram[0x1FE:0x200] = bytes([255, 1])
        b.ram[0xA8:0xAA] = pointer.to_bytes(2, 'little')
        b.ram[0x10:0x12] = bytes([x, y])
        if descriptor is not None:
            b.ram[pointer:pointer + 4] = bytes(descriptor)
        return b

    def compare(kind, bank, pointer, xy, descriptor=None):
        x, y = xy
        b = fresh(bank, pointer, x, y, descriptor)
        initial_descriptor = bytes(b[pointer + i] for i in range(4))
        quadrant = int(x >= 16) | 2 * int(y >= 16)
        captured = initial_descriptor[quadrant]
        m = ServiceMemory(rom, b.ram, b.sram, tuple(b.banks))
        game = GameEngine(m, rom=rom, mapped=True, data_window_bank=bank)
        area = game.presentation_rules().effects.area_conversion
        cpu = MPU(memory=b, pc=0xDB46)
        cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp = 17, 23, 31, 33, 0xFD
        b.cpu, b.record_ports = cpu, True
        meta = dict(kind=kind, initial_data_bank=bank, descriptor_pointer=pointer,
                    descriptor_hex=initial_descriptor.hex(), x=x, y=y,
                    quadrant=quadrant, captured_chunk=captured)
        try:
            terrain = area.terrain_at(x, y)
            for n in range(20000):
                if cpu.pc == 0x200:
                    break
                b.pc, b.step_no = cpu.pc, n
                physical, offset = b.origin(cpu.pc)
                coverage[(physical, cpu.pc, offset + 16)] += 1
                cpu.step()
            else:
                raise RuntimeError(f'Original DB46 did not return at ${cpu.pc:04X}')
            assert terrain == cpu.a, (terrain, cpu.a)
            # DB84 explicitly LDX #0; DB93 leaves Y as the unnormalized tile.
            tile = rom[16 + (graphics.chunk_selectors[captured] & 63) % 32 * 8192
                                + graphics.chunk_pointers[captured] - 0x8000
                                + (((y << 4) & 255) | (x & 15))]
            assert cpu.x == 0 and cpu.y == tile, (cpu.x, cpu.y, tile)
            rd = [(hex(a), b.peek(a), m[a]) for a in RAM_SCOPE if b.peek(a) != m[a]]
            sd = [(hex(0x6000 + i), v, w) for i, (v, w) in enumerate(zip(b.sram, m.sram)) if v != w]
            assert not rd and not sd, (rd[:8], sd[:8])
            assert b.ports == m.io_writes, (b.ports, m.io_writes)
            assert b.banks == m.banks, (b.banks, m.banks)
            assert m[0x59] | m[0x5A] << 8 == 0xDB71
            counts[kind] += 1
            samples.append(dict(**meta, returned_terrain=terrain, original_tile=tile,
                                original_return_registers={k: getattr(cpu, k) for k in ('a', 'x', 'y', 'p', 'sp', 'pc')},
                                original_instructions=n, ordered_ports=m.io_writes,
                                final_banks=m.banks[:],
                                descriptor_byte_after_bank_switch=m[pointer + quadrant],
                                captured_chunk_differs_from_later_read=m[pointer + quadrant] != captured,
                                SRAM_equal=True, declared_RAM_equal=True))
        except Exception as exc:
            failures.append(dict(**meta, error=str(exc)))

    layouts = [(0, 16, 60, 119), (16, 18, 17, 19), (99, 1, 34, 83), (119, 0, 16, 60)]
    for descriptor in layouts:
        for xy in [(0, 0), (15, 15), (16, 0), (0, 16), (16, 16), (255, 255)]:
            compare('RAM_descriptor_full_DB46', 6, 0xAA, xy, descriptor)

    # Select four actual, unmodified bank17 byte windows with four legal
    # chunk IDs. At least one byte differs when the helper selects its tile
    # bank; this specifically detects the old post-switch descriptor reread.
    candidates, seen = [], set()
    raw = rom[16 + 17 * 8192:16 + 18 * 8192]
    for offset in range(0, 8189, 4):
        descriptor = tuple(raw[offset:offset + 4])
        if max(descriptor) >= 120 or descriptor in seen:
            continue
        differences = [rom[16 + (graphics.chunk_selectors[c] & 63) % 32 * 8192 + offset + q] != c
                       for q, c in enumerate(descriptor)]
        if not any(differences):
            continue
        seen.add(descriptor)
        candidates.append(dict(physical_bank=17, cpu_pointer=0x8000 + offset,
                               rom_offset=16 + 17 * 8192 + offset,
                               raw_hex=bytes(descriptor).hex(), sha256=sha(bytes(descriptor))))
        if len(candidates) == 4:
            break
    assert len(candidates) == 4
    for candidate in candidates:
        for xy in [(1, 1), (17, 1), (1, 17), (17, 17)]:
            compare('ROM_descriptor_full_DB46', 17, candidate['cpu_pointer'], xy)
    assert any(s['kind'].startswith('ROM_') and s['captured_chunk_differs_from_later_read'] for s in samples)

    # Invalid indices are source guards only. We do not run original code
    # beyond the 120-entry table, or promise a transactional invalid call.
    for chunk in (120, 255):
        b = fresh(6, 0xAA, 0, 0, (chunk, 0, 0, 0))
        m = ServiceMemory(rom, b.ram, b.sram, tuple(b.banks))
        area = GameEngine(m, rom=rom, mapped=True, data_window_bank=6).presentation_rules().effects.area_conversion
        try:
            area.terrain_at(0, 0)
        except ValueError as exc:
            guards.append(dict(chunk=chunk, exception=str(exc), original_CPU_run=False,
                               port_writes_before_rejection=m.io_writes))
        else:
            raise AssertionError(f'Invalid chunk {chunk} was not rejected')

    proof_start, proof_end = 0xDB46, 0xDB9E
    proof_offset = 16 + 13 * 8192 + proof_start - 0xC000
    source_pins = {p: sha((ROOT / p).read_bytes()) for p in PIN_FILES}
    result = dict(status='passed' if not failures else 'failed', rom_sha256=ROM_SHA256,
                  actual_ROM_CPU_comparison_count=sum(counts.values()), rom_cpu_case_count=sum(counts.values()),
                  counts=dict(counts), source_guard_count=len(guards), source_guard_case_count=len(guards),
                  failed_count=len(failures), failures=failures, source_guards=guards, samples=samples,
                  entry=dict(physical_bank=13, CPU=0xDB46, original_stop_PC=0x200,
                             input='0010=x,0011=y;A8/A9 four-chunk descriptor pointer;current E000 bank supplies ROM descriptor',
                             output='A=terrain0..5; original X=0,Y=raw tile recorded; source returns terrain only',
                             inline_JSR_PC=0xDB6D, inline_word_PC=0xDB70, final_EE07_pointer_59_5A=0xDB71),
                  original_range=dict(physical_bank=13, cpu_start=proof_start, cpu_end_exclusive=proof_end,
                                      rom_offset=proof_offset, byte_count=proof_end-proof_start,
                                      raw_hex=rom[proof_offset:proof_offset + proof_end - proof_start].hex(),
                                      sha256=sha(rom[proof_offset:proof_offset + proof_end - proof_start])),
                  ROM_descriptor_fixtures=candidates,
                  fixture_provenance=dict(base=str(base.relative_to(ROOT)), RAM_sha256=sha(base_ram), SRAM_sha256=sha(base_sram),
                                          RAM_changes='A8/A9,0010/11,DE..E3,synthetic caller return;RAM cases AA..AD replaced by legal chunk IDs',
                                          ROM_changed=False, ROM_descriptors_are_typed_fixtures_not_native_observation=True),
                  compared_RAM_bytes=len(RAM_SCOPE), declared_RAM_addresses=RAM_SCOPE,
                  all_SRAM_compared_bytes=8192, ordered_ports_compared=True, final_banks_compared=True,
                  source_terrain_matches_original_A=True, source_CPU_XYP_SP_PC_contract=False,
                  excluded_RAM_ranges=[[0, 16], [0x100, 0x200]],
                  limits=['No original invalid-table lookup executed; invalid source guards can emit pair-selection writes before rejection.',
                          'ROM descriptor remains readable only in its caller-supplied initial data window; later separate calls must supply their own valid context.',
                          'No PPU input, completion acknowledgement, emulator frame, or asynchronous interruption synthesized.',
                          'All original calls reach RTS; this is a 40-case targeted descriptor regression, not complete terrain/graphics coverage.'],
                  source_sha256=source_pins, validator_sha256=sha(Path(__file__).read_bytes()),
                  original_instruction_locations=[dict(physical_bank=b, cpu_address=pc, rom_offset=o, count=n)
                                                  for (b, pc, o), n in sorted(coverage.items())],
                  source_original_code_calls=0, source_IR_interpretation=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'rom_cpu_case_count', 'source_guard_case_count', 'failed_count', 'counts')}, ensure_ascii=False))
    if failures:
        print(json.dumps(failures[:4], ensure_ascii=False, indent=2))
        raise SystemExit(1)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    p.add_argument('--out', type=Path, default=ROOT / 'analysis/phase10/terrain-validation.json')
    args = p.parse_args()
    verify(args.rom.read_bytes(), args.out)
