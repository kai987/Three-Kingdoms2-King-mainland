#!/usr/bin/env python3
"""Phase21 independent byte, equality-model, original-RNG and loop checks.

Original CPU executions below are validators of original contracts, not source
CPU comparisons, native internal traces, or proof of interrupt atomicity.
"""
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase21/fields-static'
SPEC = importlib.util.spec_from_file_location('phase21_semantics_model', ROOT / 'scripts/analyze_city_auxiliary_semantics.py')
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)
base = model.base
BUS_SPEC = importlib.util.spec_from_file_location('frozen_phase20_contract_validator', ROOT / 'scripts/verify_city_auxiliary_contexts.py')
old_validator = importlib.util.module_from_spec(BUS_SPEC)
sys.modules[BUS_SPEC.name] = old_validator
BUS_SPEC.loader.exec_module(old_validator)
OriginalBus = old_validator.OriginalBus


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text())


def seed_return(memory, cpu, return_pc=0x7FF0):
    cpu.sp = 0xF0
    memory.ram[0x1F1] = (return_pc - 1) & 255
    memory.ram[0x1F2] = (return_pc - 1) >> 8
    return return_pc


def rng_checks(rom):
    from py65.devices.mpu6502 import MPU
    expected_bytes = bytes.fromhex('8E 53 00 AE 54 00 BD BA E8 EE 54 00 AE 53 00 60')
    offset = base.original(31, 0xE89A)
    assert rom[offset:offset + len(expected_bytes)] == expected_bytes
    cases = 0
    # Exhaustive complete inputX × cursor54; A/Y/P vary with both dimensions.
    # No interrupt or helper callback is injected.
    for x in range(256):
        for cursor in range(256):
            memory = OriginalBus(rom, 31, 0xE89A)
            memory.ram[:] = bytes((x ^ cursor,)) * 2048
            memory.sram[:] = bytes((cursor,)) * 8192
            memory.ram[0x54] = cursor
            cpu = MPU(memory=memory, pc=0xE89A)
            cpu.a, cpu.x, cpu.y, cpu.p = cursor ^ 0xA5, x, x ^ cursor, 0x20 | ((x + cursor) & 0x7D)
            initial_p, initial_y = cpu.p, cpu.y
            stop = seed_return(memory, cpu)
            before_ram, before_sram = bytearray(memory.ram), bytes(memory.sram)
            before_banks = list(memory.banks)
            steps = 0
            while cpu.pc != stop:
                cpu.step()
                steps += 1
                assert steps <= 6
            expected = bytearray(before_ram)
            expected[0x53], expected[0x54] = x, (cursor + 1) & 255
            assert memory.ram == expected and bytes(memory.sram) == before_sram
            assert cpu.x == x and cpu.y == initial_y
            assert cpu.a == rom[base.original(31, 0xE8BA + cursor)]
            assert cpu.p == (initial_p & ~0x82) | (0x80 if x & 0x80 else 0) | (2 if x == 0 else 0)
            assert cpu.sp == 0xF2 and memory.banks == before_banks
            assert memory.writes == [(0x53, x), (0x54, (cursor + 1) & 255)]
            cases += 1
    # Explicit external clobber counterexample. This is NOT an observed NMI.
    memory = OriginalBus(rom, 31, 0xE89A)
    cpu = MPU(memory=memory, pc=0xE89A)
    cpu.x = 37
    stop = seed_return(memory, cpu)
    cpu.step()  # STX53
    memory.ram[0x53] = 99  # Deliberately external model intervention.
    while cpu.pc != stop:
        cpu.step()
    assert cpu.x == 99 and cpu.x != 37
    return dict(case_count=cases, input_domain='Exhaustive inputX0..255 × initialcursor0054=0..255; initialA/Y/P vary. Every case executes original six instructions through actual caller RTS.',
        complete_return_count=cases, ordinary_no_interrupt=True, original_helper_CPU_callbacks=0,
        comparison_scope=dict(RAM_bytes=2048, SRAM_bytes=8192, AXY_P_SP_PC=True, ordered_memory_writes=True, PRG_banks=True,
                              hardware_port_reads='none requested by original code', hardware_port_writes='none'),
        external_scratch_clobber_counterexample=dict(model_case_count=1, observed_original_NMI=False,
            input_X=37, deliberately_injected_0053=99, output_X=99,
            purpose='Demonstrates why this normal-return contract cannot silently claim interrupt atomicity.'))


def recruitment_checks(rom, contract):
    from py65.devices.mpu6502 import MPU
    rows = []
    sites = {row['cpu']: row for row in contract['sites']}
    table = rom[base.original(31, 0xE8BA):base.original(31, 0xE8BA) + 256]
    success_cursor = next(i for i, value in enumerate(table) if value < 10)
    scenarios = [(kind, fill, index) for kind in ('all_status_nonzero', 'all_free_but_nonadjacent')
                 for fill in (0, 1, 127, 255) for index in (None,)]
    scenarios += [('one_eligible_success', 0, index) for index in (0, 1, 31, 32, 63, 127, 236)]
    for kind, fill, chosen in scenarios:
        memory = OriginalBus(rom, 11, 0xC71A)
        memory.ram[:] = bytes((fill,)) * 2048
        memory.sram[:] = bytes((fill,)) * 8192
        memory.ram[0x36] = 4
        memory.sram[0xF03] = 0  # Nonfavored ruler; real threshold=10.
        memory.sram[0xF73:0xF7B] = bytes(range(8))
        memory.ram[0x54] = success_cursor
        for officer in range(237):
            start = 0x3C0 + 12 * officer
            memory.sram[start + 11] = (fill & 0xFC) | (0 if kind != 'all_status_nonzero' else 1)
            memory.sram[start + 5] = 40  # Neither city4 nor any0..7 neighbor.
        if chosen is not None:
            for officer in range(237):
                memory.sram[0x3C0 + 12 * officer + 11] = 1
            memory.sram[0x3C0 + 12 * chosen + 11] = 0xFC
            memory.sram[0x3C0 + 12 * chosen + 5] = 4
        cpu = MPU(memory=memory, pc=0xC71A)
        cpu.a, cpu.x, cpu.y, cpu.p = fill, fill, fill, 0x20
        return_pc = seed_return(memory, cpu)
        stop = 0xC76F if chosen is not None else return_pc
        seen = {pc: [] for pc in sites}
        steps = 0
        while cpu.pc != stop:
            if cpu.pc in sites:
                pointer = memory[0x22] | memory[0x23] << 8
                address = (pointer + cpu.y) & 65535
                assert pointer == 0x63C0 + 12 * cpu.x and 0 <= cpu.x < 237
                assert pointer in contract['whole_pointer_values'] and cpu.y in sites[cpu.pc]['Y_values']
                assert address not in base.AUX
                seen[cpu.pc].append(dict(officer_index=cpu.x, effective_address=address))
            cpu.step()
            steps += 1
            assert steps < 100000
        count = 237 if chosen is None else chosen + 1
        assert len(seen[0xC726]) == count
        assert [v['officer_index'] for v in seen[0xC726]] == list(range(count))
        if chosen is None:
            assert cpu.x == 237 and memory[0x22] | memory[0x23] << 8 == 0x6EDC
            assert cpu.sp == 0xF2
            assert not seen[0xC767] and not seen[0xC76D]
        else:
            assert cpu.x == chosen and cpu.sp == 0xF0
            assert memory.sram[0x3C0 + 12 * chosen + 11] == 0xFE
            assert [r['officer_index'] for r in seen[0xC767]] == [chosen]
            assert [r['officer_index'] for r in seen[0xC76D]] == [chosen]
        rows.append(dict(scenario=kind, initial_fill=fill, chosen_index=chosen, original_instruction_count=steps,
            comparison='original_recruitment_loop_normal_RTS' if chosen is None else 'original_recruitment_success_prefix_boundary',
            initial_P=0x20,
            stop_pc=stop, exact_primary_scan_count=count,
            indirect_address_observations={f'{pc:04X}': values for pc, values in seen.items()},
            source_CPU_comparison=False, original_helper_CPU_callbacks=0,
            scope='Original continuous CPU execution, normal IRQ/NMI-free call. Success stops before D105/city roster side effects; no claim of full recruitment settlement.'))
    return rows


def model_checks():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(dict(name=name, passed=True))
    def row(op, mode='i', operand=0):
        return dict(op=op, mode=mode, operand=operand)
    s = model.ReturnState()
    s = model.return_transfer(row('STX', 'ab', 0x53), s)
    s = model.return_transfer(row('LDX', 'ab', 0x54), s)
    s = model.return_transfer(row('LDX', 'ab', 0x53), s)
    check('saved inputX restored after transient load', s.registers[1] == 'input_X')
    for mirror in (0x53, 0x853, 0x1053, 0x1853):
        s = model.return_transfer(row('STX', 'zp', 0x53), model.ReturnState())
        s = model.return_transfer(row('STA', 'ab', mirror), s)
        s = model.return_transfer(row('LDX', 'zp', 0x53), s)
        check(f'partial or mirrored write{mirror:04X} removes savedX equality', s.registers[1] != 'input_X')
    for address in (0xFF80, 0x0754, 0x0F54, 0x1754):
        s = model.return_transfer(row('STX', 'zp', 0x53), model.ReturnState())
        s = model.return_transfer(row('STA', 'abx', address), s)
        s = model.return_transfer(row('LDX', 'zp', 0x53), s)
        check(f'raw indexed wrap/mirror{address:04X} conservatively invalidates', s.registers[1] is None)
    s = model.return_transfer(row('STX', 'zp', 0x53), model.ReturnState())
    s = model.return_transfer(row('STA', 'iy', 0x20), s)
    s = model.return_transfer(row('LDX', 'zp', 0x53), s)
    check('unknown indirect store kills possible saved input', s.registers[1] is None)
    left = model.return_transfer(row('STX', 'zp', 0x53), model.ReturnState())
    joined = model.return_join(left, model.ReturnState())
    check('missing predecessor save is not recovered by join', 0x53 not in joined.cells)
    s = model.return_transfer(row('PHA'), model.ReturnState())
    s = model.return_transfer(row('TXS'), s)
    s = model.return_transfer(row('PLA'), s)
    check('TXS destroys saved-stack proof', s.registers[0] is None)
    s = model.return_transfer(row('PHA'), model.ReturnState())
    s = model.return_transfer(row('STA', 'ab', 0x1900), s)
    s = model.return_transfer(row('PLA'), s)
    check('stack RAM mirror writes destroy PHA proof', s.registers[0] is None)
    s = model.return_transfer(row('STX', 'zp', 0x53), model.ReturnState())
    s = model.return_transfer(row('STA', 'ab', 0x6001), s)
    s = model.return_transfer(row('LDX', 'zp', 0x53), s)
    check('disjoint SRAM write preserves independent savedX equality', s.registers[1] == 'input_X')
    check('unknown register load never becomes input equality', model.return_transfer(row('LDX', 'ab', 0x54), model.ReturnState()).registers[1] is None)
    return checks


def output_checks(rom, engine):
    checks, raw_count = [], 0
    def walk(value):
        nonlocal raw_count
        if isinstance(value, dict):
            if all(k in value for k in ('physical_bank', 'cpu', 'rom_offset', 'raw_hex')):
                offset = base.original(value['physical_bank'], value['cpu'])
                raw = bytes.fromhex(value['raw_hex'])
                assert value['rom_offset'] == offset and rom[offset:offset + len(raw)] == raw
                raw_count += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for path in sorted(OUT.glob('*.json')):
        if path.name not in ('verification.json', 'evidence.json'):
            walk(json.loads(path.read_text()))
    atlas = base.read('analysis/phase18/control/instruction-atlas.json')
    for row in atlas['instructions']:
        offset = base.original(row['physical_bank'], row['cpu'])
        assert row['rom_offset'] == offset and rom[offset:offset + row['size']] == bytes.fromhex(row['raw_hex'])
    checks.append(dict(name='all48754 trusted atlas positions include the16-byte iNES header', passed=True, instruction_count=len(atlas['instructions'])))
    rows = read('all-indirect-accesses.json')['accesses']
    origins = {}
    for row in rows:
        proof = row['address_contract']
        if proof:
            matched = model.old.actual_auxiliary_intersection(proof)
            assert matched == proof['possible_auxiliary_effective_addresses']
            assert len(matched) == proof['auxiliary_address_intersection_count']
            assert row['whole_pointer_values'] == sorted(model.old.complete_words(proof))
            assert row['Y_values'] == proof['Y_values']
        if row['classification'] == 'proved_disjoint_auxiliary_address_domain':
            assert proof is not None and not model.old.actual_auxiliary_intersection(proof)
        origin = row.get('authoritative_contract_origin')
        if origin:
            assert sha(ROOT / origin['path']) == origin['sha256']
            if origin['path'] not in origins:
                origins[origin['path']] = {(r['physical_bank'], r['cpu']): r for r in base.read(origin['path'])['accesses']}
            assert origins[origin['path']][row['physical_bank'], row['cpu']][origin['contract_field']] == proof
        assert row['candidate_contract_is_authoritative'] is False
        candidate = row['candidate_address_contract']
        assert row['candidate_whole_pointer_values'] == (sorted(model.old.complete_words(candidate)) if candidate else None)
        assert row['candidate_Y_values'] == (candidate['Y_values'] if candidate else None)
    checks.append(dict(name='all1526 authority intersections and top-level pointer/Y are exact; candidates remain nonauthoritative', passed=True, access_count=len(rows)))
    for filename, expected in (('all-indirect-accesses.json', 1526), ('access-contracts.json', 589), ('new-indirect-accesses.json', 45), ('phase20-remaining380-handling.json', 380)):
        data = read(filename)
        assert len(data['accesses']) == data['access_count'] == expected
        assert dict(Counter(r['classification'] for r in data['accesses'])) == data['classification_counts']
    assert read('city-field-root-inventory.json')['access_count'] == 380
    for row in rows:
        if row['newly_proved_disjoint']:
            requirement = row['address_contract']['required_execution_contract']
            assert requirement['original_entry_physical_bank'] == 11 and requirement['original_entry_cpu'] == 0xC71A
            assert requirement['intervening_interrupts_or_external_mutation'] is False
    preserved = read('normal-return-register-contracts.json')['contracts']
    assert preserved == engine.passthrough_catalog
    checks.append(dict(name='all net-register contracts replay same unknown-input equality derivation/all original RTS exits', passed=True, contracts=len(preserved)))
    direct = read('direct-indexed-accesses.json')
    exact_direct, exact_raw = model.direct_inventory(engine)
    assert direct == exact_direct and read('untrusted-PRG-opcode-windows.json') == exact_raw
    checks.append(dict(name='all trusted direct/indexed domains and all raw PRG opcode windows independently regenerated', passed=True,
        trusted_direct_indexed_positions=direct['instruction_count'], raw_windows=exact_raw['raw_three_byte_windows_examined']))
    for row in exact_raw['windows']:
        offset = 16 + 8192 * row['physical_bank'] + row['bank_offset']
        assert row['rom_offset'] == offset and rom[offset:offset + 3] == bytes.fromhex(row['raw_hex'])
        assert not row['matching_trusted_instructions']
    checks.append(dict(name='raw opcode hypotheses never silently promoted to trusted instructions', passed=True, raw_auxiliary_windows=exact_raw['possible_auxiliary_window_count']))
    return checks, raw_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == base.ROM_SHA256
    summary = read('analysis-summary.json')
    assert sha(ROOT / summary['analyzer_path']) == summary['analyzer_sha256']
    for path, expected in summary['artifact_sha256'].items():
        assert sha(ROOT / path) == expected
        assert not any(part.startswith('exploratory') for part in Path(path).parts)
    engine = model.Analysis(rom)
    checks = model_checks()
    output_guards, raw_count = output_checks(rom, engine)
    checks += output_guards
    rng = rng_checks(rom)
    recruitment = recruitment_checks(rom, read('bounded-recruitment-contract.json'))
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.glob('*.json')) if p.name not in ('verification.json', 'evidence.json')}
    pins['analysis/phase21/fields-static/README.md'] = sha(OUT / 'README.md')
    sources = {p: sha(ROOT / p) for p in ('scripts/analyze_city_auxiliary_semantics.py', 'scripts/verify_city_auxiliary_semantics.py', 'scripts/verify_city_auxiliary_contexts.py')}
    result = dict(schema='phase21-city-auxiliary-semantics-validation-v1', status='passed', failed_count=0,
        ROM_sha256=base.ROM_SHA256, source_CPU_cases=0,
        original_RNG_normal_return_CPU_cases=rng['case_count'], original_RNG_checks=rng,
        external_scratch_clobber_model_counterexample_count=1,
        original_recruitment_loop_CPU_cases=len(recruitment), original_recruitment_loop_checks=recruitment,
        original_recruitment_normal_return_cases=sum(r['comparison'] == 'original_recruitment_loop_normal_RTS' for r in recruitment),
        original_recruitment_success_prefix_cases=sum(r['comparison'] == 'original_recruitment_success_prefix_boundary' for r in recruitment),
        model_guard_check_count=len(checks), model_checks=checks,
        original_nested_byte_ranges_verified=raw_count, original_trusted_atlas_positions_verified=len(engine.known),
        all_indirect_classification_counts=summary['all_indirect_classification_counts'],
        phase20_remaining_count=380, remaining_access_count=summary['remaining_access_count'],
        newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
        source_and_validator_sha256=sources, artifact_sha256=pins,
        limitations=['Original CPU contract executions are separate from recovered-source cases, native frames and synthetic guards.',
            'No original NMI was injected or claimed by the external-clobber counterexample.',
            'The return-equality interpreter and CFG scope are conservative analysis contracts; this finite checker is not a formal proof of the whole analyzer.',
            'Formal names/unused/reserved semantics of city+1/+28..31 remain unproved.'])
    model.save('verification.json', result)
    model.save('evidence.json', dict(schema='phase21-city-auxiliary-semantics-evidence-v1', status='passed',
        ROM_sha256=base.ROM_SHA256, source_CPU_cases=0,
        analyzer_path='scripts/analyze_city_auxiliary_semantics.py', analyzer_sha256=sha(ROOT / 'scripts/analyze_city_auxiliary_semantics.py'),
        validator_path='scripts/verify_city_auxiliary_semantics.py', validator_sha256=sha(__file__),
        source_and_validator_sha256=sources, artifact_sha256=summary['artifact_sha256'] | pins |
            {'analysis/phase21/fields-static/verification.json': sha(OUT / 'verification.json')},
        all_indirect_access_count=1526, old_candidate_count=589, new_indirect_access_count=45,
        classifications=dict(old589=summary['classification_counts'], all1526=summary['all_indirect_classification_counts'], new45=summary['new_indirect_classification_counts']),
        phase20_remaining_count=380, remaining_access_count=summary['remaining_access_count'], newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
        original_RNG_normal_return_CPU_cases=rng['case_count'], original_recruitment_loop_CPU_cases=len(recruitment),
        model_guard_check_count=len(checks), official_target_field_names=summary['official_target_field_names'],
        limitations=summary['limitations']))
    print(json.dumps({k: result[k] for k in ('status', 'original_RNG_normal_return_CPU_cases', 'original_recruitment_loop_CPU_cases', 'model_guard_check_count', 'remaining_access_count')}))


if __name__ == '__main__':
    main()
