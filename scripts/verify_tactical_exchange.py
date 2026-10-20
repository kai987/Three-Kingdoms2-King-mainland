#!/usr/bin/env python3
"""Compare bounded tactical proposal-consumer effects with original bank12."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.game_engine import snapshot_memory
from source.recovered.tactical_exchange import TacticalBattleBridge, TacticalExchangeData, ROM_SHA256

RANGES = [(0xBEA6, 0xBEBA), (0xBF01, 0xBF0A), (0xBF14, 0xBF19),
          (0xBF26, 0xBF7C), (0xBF83, 0xBF98), (0xA51F, 0xA535)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    data = TacticalExchangeData.from_rom(rom)
    prefix = ROOT / 'analysis/runtime/phase3/attack-intro-7'
    ram = Path(str(prefix) + '-ram.bin').read_bytes()
    sram = Path(str(prefix) + '-sram.bin').read_bytes()
    counts, failures = Counter(), []

    def case(group, changes, method, entry, stop=None):
        bus = Bus(rom, 'zero')
        bus.ram[:] = ram; bus.sram[:] = sram
        bus.banks = [2, 12, 13, 31]; bus.bank_initialized = [True]*4
        bus.protect = 0x4C
        for address, value in changes.items():
            if 0x6000 <= address < 0x8000:
                bus.sram[address - 0x6000] = value
            else:
                assert 0 <= address < 0x800
                bus.ram[address] = value
        bus.ram[0x1FE:0x200] = bytes((255, 1))
        memory = snapshot_memory(bytes(bus.ram), bytes(bus.sram))
        logic = TacticalBattleBridge(memory, data)
        try:
            getattr(logic, method)()
            cpu = MPU(memory=bus); bus.cpu = cpu
            cpu.pc = entry; cpu.sp = 0xFD; cpu.p = 32
            destination = stop or 0x200
            for step in range(1000):
                if step and cpu.pc == destination: break
                bus.pc = cpu.pc; bus.step_no = step; cpu.step()
            else: raise AssertionError(f'Original did not reach{destination:04X}')
            assert bytes(bus.ram) == bytes(memory[:2048]), (group, 'RAM', changes,
                [(hex(i), bus.ram[i], memory[i]) for i in range(2048) if bus.ram[i] != memory[i]][:8])
            assert bytes(bus.sram) == bytes(memory[0x6000:0x8000]), (group, 'SRAM', changes)
            counts[group] += 1
        except Exception as exc:
            failures.append({'group': group, 'changes': changes, 'error': f'{type(exc).__name__}: {exc}'})

    for flag in range(256):
        case('request_decision_all0087', {0x87: flag, 0x501: flag, 0x6F8B: 77, 0x6F8D: 88, 0x6F8E: 99},
             'request_decision', 0xBEA6)
        case('request_secondary_exactFF', {0x6F8B: flag, 0x509: flag % 20, 0x501: flag},
             'request_secondary', 0xA51F)
    for kind in range(5):
        case('proposal_route_prefix', {0x6F8F: kind}, 'route_proposal', 0xBF01, 0xBF0A)
    for direction in range(4):
        for y in (0, 14, 15, 16, 31, 255):
            for x in (0, 255):
                for sub in (3, 255):
                    slot = (x + y) % 20
                    case('movement_coordinate_suffix', {0x509: slot, 0x6F8D: direction,
                         0x600 + slot: x, 0x614 + slot: y, 0x501: sub},
                         'commit_movement_coordinates', 0xBF26)
    for ap in (0, 1, 3, 127, 128, 255):
        for cost in (0, 1, 3, 6, 127, 128, 255):
            case('movement_cost_suffix', {0x505: ap, 0x6F97: cost}, 'apply_movement_cost', 0xBF83)
    guards = []
    m = snapshot_memory(ram, sram); bridge = TacticalBattleBridge(m, data)
    for bad in (5, 255):
        m[0x6F8F] = bad
        try: bridge.route_proposal()
        except ValueError: guards.append({'kind': 'route', 'value': bad})
        else: failures.append({'group': 'route_guard', 'value': bad})
    m[0x509] = 20
    try: bridge.commit_movement_coordinates()
    except ValueError: guards.append({'kind': 'slot', 'value': 20})
    else: failures.append({'group': 'slot_guard', 'value': 20})
    out = ROOT / 'analysis/phase7/exchange'; out.mkdir(parents=True, exist_ok=True)
    ranges = []
    for start, end in RANGES:
        offset = 16 + 12 * 8192 + start - 0xA000; raw = rom[offset:offset + end - start]
        ranges.append({'bank': 12, 'cpu_start': start, 'cpu_end_exclusive': end,
                       'file': offset, 'raw_hex': raw.hex(' '), 'sha256': hashlib.sha256(raw).hexdigest()})
    result = {'status': 'passed' if not failures else 'failed', 'rom_sha256': ROM_SHA256,
              'case_count': sum(counts.values()), 'counts': dict(counts), 'failures': failures,
              'source_only_guard_count': len(guards), 'source_only_guards': guards,
              'code_ranges': ranges,
              'source_sha256': hashlib.sha256((ROOT / 'source/recovered/tactical_exchange.py').read_bytes()).hexdigest(),
              'validator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'All2K RAM and all8K SRAM effects only, excluding CPU registers/flags/stack and renderer request prerequisites.',
              'limits': ['BF26 and BF83 are suffix entries after real graphics requests; no graphics helper is substituted.',
                         'BF01 is checked only until BF0A, before the no-action message request.',
                         'This is not a complete NMI or a full action animation.']}
    (out / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'case_count', 'counts', 'source_only_guard_count', 'failures')}, ensure_ascii=False))
    if failures: sys.exit(1)

if __name__ == '__main__':
    main()
