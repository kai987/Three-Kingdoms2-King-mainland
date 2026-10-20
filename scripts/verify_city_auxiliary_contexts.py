#!/usr/bin/env python3
"""Phase20 original constructor-prefix and abstract-context contract checks."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase20/fields-static'
SPEC = importlib.util.spec_from_file_location('phase20_context_model', ROOT / 'scripts/analyze_city_auxiliary_contexts.py')
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)
base = model.base


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OriginalBus:
    def __init__(self, rom, physical_bank, cpu, data_bank=0):
        self.rom, self.ram, self.sram = rom, bytearray(2048), bytearray(8192)
        pair = physical_bank - int(cpu >= 0xC000) if physical_bank != 31 else 10
        self.banks = [data_bank, pair, pair + 1, 31]
        self.writes = []

    def __getitem__(self, address):
        address &= 65535
        if address < 0x2000:
            return self.ram[address & 0x7FF]
        if 0x6000 <= address < 0x8000:
            return self.sram[address - 0x6000]
        if address >= 0x8000:
            return self.rom[base.original(self.banks[(address - 0x8000) // 8192], address)]
        raise AssertionError(f'Undeclared hardware read {address:04X}')

    def __setitem__(self, address, value):
        address, value = address & 65535, value & 255
        self.writes.append((address, value))
        if address < 0x2000:
            self.ram[address & 0x7FF] = value
        elif 0x6000 <= address < 0x8000:
            self.sram[address - 0x6000] = value
        elif address in (0xE000, 0xE800, 0xF000):
            self.banks[(address - 0xE000) // 2048] = (value & 63) % 32
        else:
            raise AssertionError(f'Undeclared hardware write {address:04X}')


def constructor_checks(rom, contracts):
    from py65.devices.mpu6502 import MPU
    rows, count, mapper_count = [], 0, 0
    for descriptor in contracts:
        start, end, pointer = descriptor['loads_start'], descriptor['complete_after'], descriptor['pointer_base']
        observed = set()
        inputs = range(256) if descriptor['index_domain'] is not None else (0, 255)
        for index in inputs:
            memory = OriginalBus(rom, start['physical_bank'], start['cpu'], descriptor['explicit_data_window_bank'] or 0)
            cpu = MPU(memory=memory, pc=start['cpu'])
            cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp = 173, index, index, 0x20 | (index & 1), 0xF0
            stop = end['cpu'] + len(bytes.fromhex(end['raw_hex']))
            steps = 0
            while cpu.pc != stop:
                cpu.step()
                steps += 1
                assert steps <= 8, descriptor
            value = memory[pointer] | (memory[(pointer + 1) & 255] << 8)
            assert value in descriptor['whole_pointer_values']
            observed.add(value)
            count += 1
        assert observed == set(descriptor['whole_pointer_values'])
        if descriptor['explicit_data_window_bank'] is not None:
            for fill in (0, 1, 127, 255):
                entry = descriptor
                memory = OriginalBus(rom, entry['physical_bank'], entry['cpu'])
                memory.ram[:] = bytes((fill,)) * 2048
                cpu = MPU(memory=memory, pc=entry['cpu'])
                cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp = fill, fill, fill, 0x20, 0xF0
                steps = 0
                while cpu.pc != start['cpu']:
                    cpu.step()
                    steps += 1
                    assert steps < 128
                assert memory.banks[0] == descriptor['explicit_data_window_bank']
                mapper_count += 1
        rows.append(dict(physical_bank=start['physical_bank'], cpu=start['cpu'],
                         constructor_entry_cpu=descriptor['cpu'], kind=descriptor['kind'],
                         cases=len(inputs), stop_pc=stop, comparison='original_constructor_complete_prefix',
                         exact_whole_word_output_set=True))
    return rows, count, mapper_count


def model_checks():
    from py65.devices.mpu6502 import MPU
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(dict(name=name, passed=True))
    check('numeric domain exceeding32 widens to unknown', model.finite(frozenset(range(33))) is None)
    check('small numeric domain is retained', model.finite(frozenset(range(32))) == frozenset(range(32)))
    a = model.ContextState(pairs={0: base.Pair(frozenset((0x63C0,)))}, numbers=(None, frozenset((1,)), frozenset((17,))))
    b = model.ContextState(pairs={0: base.Pair(frozenset((0x6408,)))}, numbers=(None, frozenset((2,)), frozenset((26,))))
    joined = model.join(a, b)
    check('numeric join keeps complete pointer relationship independent', joined.pairs[0].addresses == frozenset((0x63C0, 0x6408)))
    check('numeric join is may-union', joined.numbers[2] == frozenset((17, 26)))
    check('unknown predecessor prevents numeric narrowing', model.join(a, model.ContextState()).numbers[2] is None)
    engine = model.Analysis.__new__(model.Analysis)
    compare, branch = (8, 0xA000), (8, 0xA002)
    taken, following = (8, 0xA006), (8, 0xA004)
    engine.predecessors, engine.known, engine.edges = {branch: {compare}}, {}, {branch: [following, taken]}
    cases = 0
    compare_opcodes = {'CMP': 0xC9, 'CPX': 0xE0, 'CPY': 0xC0}
    branch_opcodes = {'BCC': 0x90, 'BCS': 0xB0, 'BEQ': 0xF0, 'BNE': 0xD0, 'BMI': 0x30, 'BPL': 0x10}
    for comparison, code in compare_opcodes.items():
        register = ('CMP', 'CPX', 'CPY').index(comparison)
        for limit in (0, 1, 10, 27, 128, 255):
            engine.known[compare] = dict(op=comparison, mode='im', operand=limit, cpu=0xA000, size=2)
            for operation, opcode in branch_opcodes.items():
                engine.known[branch] = dict(op=operation, mode='rel', operand=2, cpu=0xA002, size=2)
                for raw in range(256):
                    data = [0] * 65536
                    data[0xA000:0xA004] = [code, limit, opcode, 2]
                    cpu = MPU(memory=data, pc=0xA000)
                    cpu.a = cpu.x = cpu.y = raw
                    cpu.p = 0x20
                    cpu.step()
                    cpu.step()
                    numbers = [None, None, None]
                    numbers[register] = frozenset((raw,))
                    state = model.ContextState(numbers=tuple(numbers))
                    successors = engine.branch_successors(branch, state)
                    assert len(successors) == 1 and successors[0][0] == (8, cpu.pc)
                    assert raw in successors[0][1].numbers[register]
                    cases += 1
    checks.append(dict(name='CPx/immediate actual CPU truth-table', passed=True, model_instruction_oracle_cases=cases))
    engine.known[compare] = dict(op='CPY', mode='im', operand=27, cpu=0xA000, size=2)
    engine.known[branch] = dict(op='BCC', mode='rel', operand=0, cpu=0xA002, size=2)
    engine.edges[branch] = [following]
    state = model.ContextState()
    successors = engine.branch_successors(branch, state)
    check('zero-relative common edge is not truth-filtered', len(successors) == 1 and successors[0][1].numbers[2] is None)
    engine.known[branch]['operand'] = 2
    engine.edges[branch] = [following, taken]
    engine.predecessors[branch].add((8, 0xB000))
    check('noncompare alternative entry blocks branch refinement', len(engine.branch_successors(branch, state)) == 2)
    return checks, cases


def constructor_entry_guards(engine):
    checks = []
    tested = 0
    for descriptor in engine.template_catalog:
        if descriptor['kind'] != 'literal_word':
            continue
        state = model.ContextState()
        for row in descriptor['instructions']:
            state = engine.transfer((row['physical_bank'], row['cpu']), state)
        assert state.pairs[descriptor['pointer_base']].addresses == frozenset(descriptor['whole_pointer_values'])
        # Entry after the first half's producer must not acquire the original
        # builder solely because the latter instructions have the same PC.
        state = model.ContextState()
        for row in descriptor['instructions'][2:]:
            state = engine.transfer((row['physical_bank'], row['cpu']), state)
        assert descriptor['pointer_base'] not in state.pairs
        tested += 1
    checks.append(dict(name='literal constructor entry and middle-entry guards', passed=True, constructor_count=tested))
    state = model.ContextState(numbers=(frozenset((1,)), frozenset((2,)), frozenset((3,))))
    actual = engine.apply_call(state, None, (8, 0xA000))
    checks.append(dict(name='unknown call clears numeric registers', passed=all(value is None for value in actual.numbers)))
    assert checks[-1]['passed']
    actual = engine.apply_call(state, (31, 0xF266), (8, 0xA000))
    checks.append(dict(name='exact mapper setter preserves numeric register values', passed=actual.numbers == state.numbers))
    assert checks[-1]['passed']
    return checks


def structured_loop_checks(rom, contracts):
    from py65.devices.mpu6502 import MPU
    sites = {
        'scenario_SRAM_clear': {0xDD9A: (0, range(0x6000, 0x7000))},
        'whole_city_template_copy': {0xDDED: (0, range(0x8C00, 0x8FC0)), 0xDDEF: (2, range(0x6000, 0x63C0))},
        'whole_officer_template_copy': {0xDE32: (0, range(0x8000, 0x8B40)), 0xDE34: (2, range(0x63C0, 0x6F00))},
    }
    rows = []
    for contract in contracts:
        for fill in (0, 1, 127, 255):
            memory = OriginalBus(rom, 30, contract['entry_cpu'])
            memory.ram[:] = bytes((fill,)) * 2048
            memory.sram[:] = bytes((fill,)) * 8192
            cpu = MPU(memory=memory, pc=contract['entry_cpu'])
            cpu.a = cpu.x = cpu.y = fill
            cpu.p, cpu.sp = 0x20, 0xF0
            seen = {pc: [] for pc in sites[contract['name']]}
            steps = 0
            while cpu.pc != contract['stop_cpu']:
                if cpu.pc in seen:
                    pointer, _ = sites[contract['name']][cpu.pc]
                    address = ((memory[pointer] | (memory[(pointer + 1) & 255] << 8)) + cpu.y) & 65535
                    seen[cpu.pc].append(address)
                cpu.step()
                steps += 1
                assert steps < 100000
            for pc, (_, addresses) in sites[contract['name']].items():
                assert seen[pc] == list(addresses), (contract['name'], pc)
            rows.append(dict(name=contract['name'], initial_RAM_SRAM_fill=fill,
                             stop_pc=contract['stop_cpu'], exact_iterations=contract['exact_iterations'],
                             exact_original_read_write_address_sequences=True, actual_instruction_count=steps,
                             comparison='bounded_original_loop_boundary_not_RTS'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == base.ROM_SHA256
    summary = json.loads((OUT / 'analysis-summary.json').read_text())
    assert summary['analyzer_sha256'] == sha(ROOT / summary['analyzer_path'])
    for path, expected in summary['artifact_sha256'].items():
        assert sha(ROOT / path) == expected, path
        assert not any(part.startswith('exploratory') for part in Path(path).parts)
    raw_count = 0
    for path in OUT.glob('*.json'):
        if path.name in ('verification.json', 'evidence.json'):
            continue
        def visit(value):
            nonlocal raw_count
            if isinstance(value, dict):
                if all(key in value for key in ('physical_bank', 'cpu', 'rom_offset', 'raw_hex')):
                    offset = base.original(value['physical_bank'], value['cpu'])
                    raw = bytes.fromhex(value['raw_hex'])
                    assert value['rom_offset'] == offset and rom[offset:offset + len(raw)] == raw
                    raw_count += 1
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(json.loads(path.read_text()))
    contracts = json.loads((OUT / 'constructor-contracts.json').read_text())['contracts']
    rows, original_count, mapper_count = constructor_checks(rom, contracts)
    checks, truth_count = model_checks()
    structured = structured_loop_checks(rom, json.loads((OUT / 'structured-loop-contracts.json').read_text())['contracts'])
    for name, expected in (('all-indirect-accesses.json', 1526), ('access-contracts.json', 589), ('new-indirect-accesses.json', 45)):
        data = json.loads((OUT / name).read_text())
        assert len(data['accesses']) == expected
        assert dict(Counter(r['classification'] for r in data['accesses'])) == data['classification_counts']
        for row in data['accesses']:
            proof = row['address_contract']
            if proof:
                words = model.complete_words(proof)
                matched = model.actual_auxiliary_intersection(proof)
                assert matched == proof['possible_auxiliary_effective_addresses']
                assert len(matched) == proof['auxiliary_address_intersection_count']
                assert row['whole_pointer_values'] == sorted(words)
                assert row['Y_values'] == proof['Y_values']
                if row['proof_basis'] == 'new_whole_pointer_relation':
                    assert not matched
            if row['classification'] == 'proved_disjoint_auxiliary_address_domain':
                assert proof is not None and proof['auxiliary_address_intersection_count'] == 0
                assert not model.actual_auxiliary_intersection(proof)
            origin = row.get('authoritative_contract_origin')
            if origin:
                assert sha(ROOT / origin['path']) == origin['sha256']
                previous = json.loads((ROOT / origin['path']).read_text())['accesses']
                canonical = next(item for item in previous if (item['physical_bank'], item['cpu']) == (row['physical_bank'], row['cpu']))
                assert canonical[origin['contract_field']] == proof
                assert row['candidate_contract_is_authoritative'] is False
                candidate = row['candidate_address_contract']
                assert row['candidate_whole_pointer_values'] == (candidate['whole_pointer_values'] if candidate else None)
                assert row['candidate_Y_values'] == (candidate['Y_values'] if candidate else None)
    all_rows = json.loads((OUT / 'all-indirect-accesses.json').read_text())['accesses']
    inherited = [row for row in all_rows if row.get('authoritative_contract_origin')]
    corrections = json.loads((OUT / 'authoritative-contract-selection.json').read_text())
    assert len(inherited) == corrections['row_count'] == 20
    assert sum(row['candidate_address_contract'] is not None for row in inherited) == corrections['broader_candidate_count'] == 5
    checks.append(dict(name='every disjoint row has a recomputed nonintersecting authoritative domain', passed=True,
                       all_rows=1526, authoritative_disjoint_count=sum(row['classification'] == 'proved_disjoint_auxiliary_address_domain' for row in all_rows)))
    checks.append(dict(name='inherited exact proof object/hash/index synchronized; wider candidates nonauthoritative', passed=True,
                       inherited_authorities=len(inherited), broader_candidates=5, unknown_candidates=15))
    engine = model.Analysis(rom)
    checks.extend(constructor_entry_guards(engine))
    returned = json.loads((OUT / 'return-pair-contracts.json').read_text())['contracts']
    for contract in returned:
        entry = contract['physical_bank'], contract['cpu']
        structure = engine.function_structure(entry)
        assert not structure['barriers'] and structure['exits']
        assert [engine.raw(k) for k in structure['exits']] == contract['RTS_exits']
    result = dict(schema='phase20-city-auxiliary-context-validation-v1', status='passed', failed_count=0,
        ROM_sha256=base.ROM_SHA256, source_CPU_cases=0,
        original_constructor_prefix_CPU_cases=original_count, original_mapper_prefix_CPU_cases=mapper_count,
        original_structured_loop_boundary_CPU_cases=len(structured), original_structured_loop_checks=structured,
        original_constructor_checks=rows, model_guard_check_count=len(checks), model_checks=checks,
        model_instruction_oracle_cases=truth_count,
        model_instruction_oracle_scope='Synthetic immediate compare/branch truth tables executed by CPU; not original-ROM gameplay comparisons.',
        original_prefix_scope='Exhaustive raw X/Y of original literal/immutable-table constructor prefixes; mapper prefixes separately checked at four declared RAM fills. No function RTS or recovered-source comparison claim.',
        declared_local_return_structures_checked=len(returned), original_nested_byte_ranges_verified=raw_count,
        source_and_validator_sha256={path: sha(ROOT / path) for path in ('scripts/analyze_city_auxiliary_contexts.py', 'scripts/verify_city_auxiliary_contexts.py')},
        artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in OUT.glob('*.json') if p.name not in ('verification.json', 'evidence.json')},
        classifications=dict(old589=summary['classification_counts'], all1526=summary['all_indirect_classification_counts'], new45=summary['new_indirect_classification_counts']),
        limitations=['This validates raw-byte contracts and selected abstract-transfer invariants, not a formal proof of the entire analyzer.',
                     'All normal-return/bounded-selector and index/memory-mapping scope limitations remain explicit in the static evidence.'])
    save = model.save
    result['artifact_sha256']['analysis/phase20/fields-static/README.md'] = sha(OUT / 'README.md')
    save('verification.json', result)
    save('evidence.json', dict(schema='phase20-city-auxiliary-context-evidence-v1', status='passed',
        ROM_sha256=base.ROM_SHA256, source_CPU_cases=0,
        analyzer_path='scripts/analyze_city_auxiliary_contexts.py', analyzer_sha256=sha(ROOT / 'scripts/analyze_city_auxiliary_contexts.py'),
        validator_path='scripts/verify_city_auxiliary_contexts.py', validator_sha256=sha(__file__),
        source_and_validator_sha256=result['source_and_validator_sha256'],
        artifact_sha256=summary['artifact_sha256'] | result['artifact_sha256'] |
                        {'analysis/phase20/fields-static/verification.json': sha(OUT / 'verification.json')},
        instruction_count=summary['instruction_count'], all_indirect_access_count=1526, old_candidate_count=589, new_indirect_access_count=45,
        classifications=result['classifications'],
        phase19_remaining_count=401, remaining_access_count=summary['remaining_access_count'],
        newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
        original_constructor_prefix_CPU_cases=original_count, original_mapper_prefix_CPU_cases=mapper_count,
        original_structured_loop_boundary_CPU_cases=len(structured),
        model_instruction_oracle_cases=truth_count, model_guard_check_count=len(checks),
        original_prefix_scope=result['original_prefix_scope'],
        model_instruction_oracle_scope=result['model_instruction_oracle_scope'],
        official_target_field_names=summary['official_target_field_names'],
        limitations=summary['limitations']))
    print(json.dumps({key: result[key] for key in ('status', 'original_constructor_prefix_CPU_cases', 'original_mapper_prefix_CPU_cases', 'model_instruction_oracle_cases', 'original_nested_byte_ranges_verified')}))


if __name__ == '__main__':
    main()
