#!/usr/bin/env python3
"""Actual original6502 comparisons for faction/end rules and bounded ending IR.

Pure services use no original-code adapters. Their contract is full SRAM plus
declared RAM/control fields, not all CPU scratch/flags. The lifted controller
compares every register/flag/stack/RAM/SRAM/bank; unresolved external helpers
execute original code only in this validator, stopping at explicit boundaries.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import random
import sys
from importlib.metadata import version

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from verify_domestic_ai import fresh, execute, TurnHooks, ValidationBarrier
from source.recovered.faction_lifecycle import FactionLifecycle, FactionTables, EndingControl, ROM_SHA256, city_address, ruler_address, officer_address, word

PACKET = (0x300, 0x310, 0x311, 0x312, 0x313)


def flat(bus):
    m = bytearray(65536); m[:2048] = bus.ram; m[0x6000:0x8000] = bus.sram
    return m


def clear_cities(bus):
    for c in range(30):
        a = city_address(c)
        for s in range(17, 27): bus[a+s] = 255


def copy_bus(rom, bus, pair):
    other = fresh(rom, pair); other.ram[:] = bus.ram; other.sram[:] = bus.sram
    other.banks[:] = bus.banks
    return other


def verify(rom, quick=False):
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    data = FactionTables.from_rom(rom); rng = random.Random(0xFA6706)
    counts = Counter(); failures = []; coverage = set(); samples = []
    def test(name, bus, action, entry, *, stop=0x200, fields=(), registers=None, min_steps=0):
        m = flat(bus); logic = FactionLifecycle(m, data)
        try:
            result = action(logic)
            cpu, steps = execute(bus, entry, stop=stop, registers=registers, min_steps=min_steps)
            assert bytes(m[0x6000:0x8000]) == bytes(bus.sram), (name, 'SRAM',
                [(hex(0x6000+i), bus.sram[i], m[0x6000+i]) for i in range(8192) if bus.sram[i] != m[0x6000+i]][:12])
            assert all(m[a] == bus[a] for a in fields), (name, 'RAM',
                [(hex(a), bus[a], m[a]) for a in fields if m[a] != bus[a]][:12])
            counts[name] += 1
            if len(samples) < 35 or name not in [s['name'] for s in samples]:
                samples.append({'name': name, 'entry': entry, 'stop_cpu': cpu.pc,
                                'original_instructions': steps, 'result': result})
            return result, cpu
        except Exception as error:
            failures.append({'name': name, 'entry': entry, 'error': repr(error)})
            if len(failures) >= 12: raise RuntimeError('Repeated semantic failures: '+repr(failures))
            return None, None

    for i in range(32 if quick else 512):
        b = fresh(rom, 27); ruler = i % 7; wanted = i % 31
        for c in range(30):
            owner = ruler if c < wanted else rng.choice([v for v in range(8) if v != ruler])
            b[city_address(c)] = rng.randrange(32)*8 + owner
        b[0x10] = ruler
        test('owner_low3_city_count', b,
             lambda x, r=ruler: (x.memory.__setitem__(0x11, x.count_owned_cities(r)), x.count_owned_cities(r))[1],
             0xDDBF, fields=(0x11,))
    for ruler in range(7):
        for wanted in ([0, 29, 30] if quick else range(31)):
            b = fresh(rom, 27); b[0x6F03] = ruler; b[0x401] = rng.randrange(256)
            for c in range(30): b[city_address(c)] = 0xB8 | (ruler if c < wanted else 7)
            test('all30_victory_prefix', b, lambda x: x.victory_entry_check(), 0xA089,
                 stop=0x200 if wanted == 30 else 0xA0B0,
                 fields=(0x470, 0x471, 0x472, 0xA4, 0x4E4, 0x10, 0x11, 0x400, 0x401))

    masks = [0, 1, 2, 4, 8, 16, 32, 64, 127]
    for order in range(5):
        for slot in ([255, 6] if quick else [255, *range(7)]):
            for mask in masks:
                b = fresh(rom, 25); b[0x6F45] = order; b[0x6F04] = slot
                b[0x6F00], b[0x6F01] = rng.choice([0, 89, 255]), rng.randrange(12)
                for ruler in range(7):
                    a = ruler_address(ruler); b[a] = 20+ruler if mask & (1 << ruler) else 255
                    for j in range(4, 8): b[a+j] = rng.randrange(256)
                m = flat(b); logic = FactionLifecycle(m, data); result = logic.select_next_active_ruler()
                try:
                    if mask: cpu, steps = execute(b, 0xA041, stop=0xA091)
                    else:
                        steps = 0
                        for _ in range(7): cpu, n = execute(b, 0xA041, stop=0xA041, min_steps=1); steps += n
                    assert bytes(m[0x6000:0x8000]) == bytes(b.sram)
                    assert all(m[a] == b[a] for a in [0x6F00, 0x6F01, 0x6F03, 0x6F04, 0x6F06, 0x6F41, 0xEE, 0xEF])
                    counts['calendar_leaderFF_skip' if mask else 'all_leadersFF_one_scan_prefix'] += 1
                except Exception as error: failures.append({'name': 'calendar_skip', 'order': order, 'slot': slot, 'mask': mask, 'error': repr(error)})

    for i in range(32 if quick else 1024):
        b = fresh(rom, 25); ruler = i % 7; b[0x6F03] = ruler
        for r in range(7): b[ruler_address(r)] = rng.choice([255, rng.randrange(237), 20])
        for officer in range(237): b[officer_address(officer)+11] = rng.randrange(256)
        if i % 8 == 0:
            for officer in range(237): b[officer_address(officer)+11] = (2 if officer < (i % 4)+29 else 3)
        test('surviving_officer_pool237', b, lambda x, r=ruler: x.surviving_officer_pool(r),
             0xA240, fields=(*range(0x42C, 0x433), 0x10, 0x11))
    for count in ([0, 29, 30, 237] if quick else range(238)):
        b = fresh(rom, 25); b[0x11] = count
        test('pool_warning_threshold', b, lambda x: x.prepare_pool_warning(), 0xA094,
             stop=0x200 if count < 30 else 0xA0A5, fields=(0x401, *PACKET))
    for jobs0 in (0, 255):
        for jobs4 in (0, 255):
            for button in (0, 1, 2, 255):
                b = fresh(rom, 25); b[0x300], b[0x304], b[0x81] = jobs0, jobs4, button
                ready = jobs0 == jobs4 == 255 and button & 1
                test('pool_warning_reset_gate', b, lambda x: x.pool_warning_reset_gate(), 0xA186,
                     stop=0xE000 if ready else 0x200)

    for i in range(28 if quick else 896):
        b = fresh(rom, 10); ruler = i % 7; a = ruler_address(ruler)
        b[0x24], b[0x25] = a & 255, a >> 8
        for j in range(8): b[a+j] = rng.randrange(256)
        test('AI_no_successor_commit', b, lambda x, r=ruler: x.commit_no_successor_event(r), 0xCA74,
             stop=0xCA7F)
    for flag in ([0, 1, 2, 251, 252, 255] if quick else range(256)):
        b = fresh(rom, 10); b[0x6F8B] = flag
        result, cpu = test('exact_ack1_wait_gate', b, lambda x: x.successor_wait_gate(), 0xCA7F,
                          stop=0x200 if flag == 1 else 0xCA7F, min_steps=1)
        if cpu: assert result == (cpu.pc == 0x200)
    for ruler in range(7):
        for variant in range(2 if quick else 32):
            for flag in (0, 1, 251, 252):
                b = fresh(rom, 10); b[0x40] = ruler; b[0x6F8B] = flag
                b[ruler_address(ruler)] = 255
                for officer in range(237):
                    b[officer_address(officer)+3] = rng.randrange(256)
                    b[officer_address(officer)+4] = rng.randrange(256)
                for city in range(30):
                    a = city_address(city); b[a] = rng.randrange(32)*8+rng.randrange(8)
                    for j in range(2, 6): b[a+j] = rng.randrange(256)
                    for j in range(17, 27): b[a+j] = rng.choice([255, rng.randrange(237)])
                test('after_actual_ack_city_chief_prefix', b,
                     lambda x, r=ruler: x.repair_after_successor_ack(r),
                     0xCA52 if flag == 1 else 0xCA7F,
                     stop=0xCA58 if flag == 1 else 0xCA7F, min_steps=0 if flag == 1 else 1)
    for i in range(14 if quick else 224):
        b = fresh(rom, 25); ruler = i % 7; b[0x40] = ruler; b[0x38] = rng.randrange(256)
        test('FB_prompt_name_and_packet', b, lambda x, r=ruler: x.no_successor_prompt(r), 0xC91B,
             fields=(0x42C, 0x42D, 0x401, 0x40C, *PACKET))
    for sub in (11, 12):
        for count in ([0, 238, 239, 240, 255] if quick else range(256)):
            for flag in (251, 252):
                b = fresh(rom, 25); b[0x401] = sub; b[0x40C] = count; b[0x6F8B] = flag
                b[0x27] = rng.randrange(237); a = ruler_address(count % 7)
                b[0xEE], b[0xEF] = a & 255, a >> 8
                test('real_successor_timer_step', b, lambda x, s=sub: x.successor_timer_step(s),
                     0xCB7F if sub == 11 else 0xCB9D,
                     fields=(0x401, 0x40C, 0x42C, *PACKET))
    for ruler in range(7):
        for controller in ([0, 3, 7, 255] if quick else range(256)):
            b = fresh(rom, 25); b[0x40A] = ruler; b[0x402] = rng.randrange(256)
            b[0x4D0] = rng.randrange(256); b[ruler_address(ruler)+3] = controller
            test('retire_leader_only_and_controller_low2', b, lambda x, r=ruler: x.retire_faction(r),
                 0xC386, fields=(0x42C, 0x42D, 0x402, 0x4D0, *PACKET))
    for i in range(24 if quick else 384):
        b = fresh(rom, 25); b[0x40C] = (255 if i % 8 == 0 else i % 7)
        b[0x6F00] = rng.choice([0, 89, 99, 155, 255]); b[0x6F01] = i % 12
        test('human_extinction_end_substitutions', b, lambda x: x.human_extinction_end(), 0xC3DB,
             fields=(*range(0x42E, 0x435), 0x7A, 0x541, 0x4CA))

    for i in range(16 if quick else 384):
        b = fresh(rom, 25); ruler = i % 7; a = ruler_address(ruler)
        b[0xEE], b[0xEF] = a & 255, a >> 8; b[0x401] = rng.randrange(256)
        b[0x6F00], b[0x6F01], b[0x6F02] = rng.randrange(256), i % 12, i % 3
        leader = b[a]
        for officer in range(237): b[officer_address(officer)+3] = rng.randrange(256)
        for city in range(30):
            addr = city_address(city); b[addr+11] = rng.randrange(256)
            for slot in range(17, 27):
                b[addr+slot] = 255 if i % 12 == 0 else leader if i % 12 == 1 else rng.choice([255, rng.randrange(237)])
                if i % 12 == 2: b[addr+slot] = (city*10+slot-17) % 237
        test('victory_score_wrap_and_zero_divisor', b, lambda x: x.victory_score(), 0xC441,
             fields=(0x42C, *range(0x42F, 0x438), *range(0x44C, 0x452), 0x401))
    for i in range(32 if quick else 512):
        b = fresh(rom, 25); b[0x6F03] = i % 7
        for officer in range(237): b[officer_address(officer)+2] = rng.randrange(256)
        for city in range(30):
            a = city_address(city); b[a] = rng.randrange(32)*8 + rng.randrange(8)
            for slot in range(17, 27): b[a+slot] = rng.choice([255, rng.randrange(237)])
        if i % 16 == 0: clear_cities(b)
        test('summary_max_intellect_later_ties', b, lambda x: x.best_intellect_for_summary(),
             0xC626, fields=(0x10, 0x11))
    for low in ([0, 39, 40, 69, 70, 255] if quick else range(256)):
        for upper in (0, 255):
            b = fresh(rom, 25); b[0x435], b[0x436], b[0x437] = low, upper, upper
            test('victory_rank_lowbyte_only', b, lambda x: x.accept_victory_summary(), 0xC606,
                 fields=(0x7A, 0x541, 0x4C9, 0x4CA))
    for i in range(8 if quick else 128):
        b = fresh(rom, 23); b[0x42C] = i % 237
        for city in range(30):
            for slot in range(17, 27):
                b[city_address(city)+slot] = rng.randrange(237) if i % 4 == 0 else rng.choice([255, rng.randrange(237)])
        test('credits_byte_buffer_and_aliases', b, lambda x: x.ending_credits_roster(), 0xD9DE,
             fields=(*range(0x400, 0x510), 0x542, 0x543, *PACKET))
    for i in range(16 if quick else 256):
        b = fresh(rom, 23); b[0x81] = rng.randrange(256); b[0x6F43] = 0 if i % 2 else rng.randrange(1, 256)
        b[0x472], b[0x473] = rng.randrange(256), rng.randrange(256)
        reset = bool(b[0x81] & 1) and b[0x6F43] == 0
        test('loss_A_reset_or_restore_parent', b, lambda x: x.ending_loss_exit(), 0xD72A,
             stop=0xE000 if reset else 0x200, fields=(0x400, 0x401, 0x402, 0x7A))

    print(json.dumps({'semantic_cases': sum(counts.values()), 'failures': failures}), flush=True)
    semantic_cases = sum(counts.values())
    catalog = json.loads((ROOT/'analysis/phase6/factions/ending-controller.json').read_text())
    ir_cases = []; outcomes = Counter()
    for mode in catalog['main_modes']:
        for sub in range(len(mode['substates']) if mode['substates'] else 1):
            for variant in range(1 if quick else 4):
                b = fresh(rom, 23); b[0x541], b[0x542] = mode['id'], sub
                b[0x4C9], b[0x4CA] = (0, 0) if variant < 2 else (128, 1)
                b[0x4CB] = 254 if variant == 3 else 255
                b[0x4CD], b[0x4CE] = 255 if variant == 3 else 0, 2 if variant == 3 else 0
                b[0x87] = 128 if variant == 3 else 0
                b[0x81] = 9 if variant == 3 else 0
                b[0x300] = b[0x304] = 255 if variant & 1 else 0
                b[0x7C] = 0; b[0x7E] = 0; b[0x6F43] = 0
                b[0x40D] = 255; b[0x410] = 254; b[0x411] = 131; b[0x412] = 255
                original = copy_bus(rom, b, 23); hooks = TurnHooks(b)
                control = EndingControl(b, hooks=hooks); boundary = None
                try:
                    control.step(max_instructions=100000)
                except ValidationBarrier as error: boundary = str(error)
                except Exception as error:
                    failures.append({'name': 'ending_IR', 'mode': mode['id'], 'sub': sub, 'variant': variant, 'error': repr(error)})
                    continue
                try:
                    cpu, steps = execute(original, 0xD693, stop=control.registers.pc)
                    assert bytes(b.ram) == bytes(original.ram), ('IR_RAM', [(hex(a), original.ram[a], b.ram[a]) for a in range(2048) if original.ram[a] != b.ram[a]][:12])
                    assert bytes(b.sram) == bytes(original.sram), 'IR_SRAM'
                    assert b.banks == original.banks, ('IR_banks', b.banks, original.banks)
                    assert all(getattr(cpu, n) == getattr(control.registers, n) for n in ('a', 'x', 'y', 'sp', 'p', 'pc')), ('IR_registers', vars(control.registers), {n: getattr(cpu, n) for n in ('a', 'x', 'y', 'sp', 'p', 'pc')})
                    coverage.update(control.executed); counts['ending_control_IR'] += 1
                    outcomes['explicit_boundary' if boundary else 'returned'] += 1
                    ir_cases.append({'mode': mode['id'], 'substate': sub, 'variant': variant,
                        'termination_cpu': cpu.pc, 'boundary': boundary, 'original_instructions': steps,
                        'source_instructions_executed': len(control.executed), 'external_original_adapters': hooks.calls})
                except Exception as error: failures.append({'name': 'ending_IR_compare', 'mode': mode['id'], 'sub': sub, 'variant': variant, 'error': repr(error)})
    return {'status': 'failed' if failures else 'passed', 'rom_sha256': ROM_SHA256,
            'quick_matrix': quick, 'case_count': sum(counts.values()), 'counts': dict(counts),
            'semantic_case_count': semantic_cases, 'ending_IR_case_count': counts['ending_control_IR'],
            'ending_terminations': dict(outcomes), 'ending_dynamic_coverage': len(coverage),
            'ending_IR_instruction_count': catalog['instruction_count'], 'failures': failures,
            'samples': samples, 'ending_fixtures': ir_cases,
            'source_sha256': hashlib.sha256((ROOT/'source/recovered/faction_lifecycle.py').read_bytes()).hexdigest(),
            'python_version': sys.version, 'py65_version': version('py65'),
            'contracts': ['Pure services: fullSRAM plus per-entry declared RAM/control fields; no CPU scratch/stack equivalence assertion.',
                          'EndingIR: full CPU registers/flags/stack/all2K RAM/all8K SRAM/mapper windows. Outside helpers use actualROM only in validator.',
                          'AllleadersFF cases stop after one7-slot scan period; original handler has no returning all-absent branch.',
                          'Ending fixtures are direct-entry controlled snapshots, not natural campaign completion or wholevideo frames.',
                          'External globalE46A, PPU/NMI and reset are boundaries, not fabricated completed work.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('rom', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT/'analysis/phase6/factions/validation.json')
    parser.add_argument('--quick', action='store_true'); args = parser.parse_args()
    result = verify(args.rom.read_bytes(), args.quick)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'case_count', 'semantic_case_count', 'ending_IR_case_count', 'ending_terminations', 'ending_dynamic_coverage', 'failures')}, ensure_ascii=False))
    sys.exit(bool(result['failures']))


if __name__ == '__main__': main()
