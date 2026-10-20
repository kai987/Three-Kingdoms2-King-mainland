#!/usr/bin/env python3
"""Phase32 static/model audit and optional Root-only original-CPU contracts.

Default execution is static/model only. `--execute-original-cpu` is an explicit
separate mode intended for the Root execution owner; this file never runs any
Native core, production Source or old generator.
"""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_inline_dispatch_contracts_phase32 as model

OUT = model.OUT


def register_input(pc, a, x, y, sp, p):
    return dict(pc=pc, a=a, x=x, y=y, sp=sp, p=p)


def specifications(quick=False):
    """Finite independent axes; no claim of exhaustive full-state Cartesian tests."""
    raw = [0, 7, 8, 15, 16, 127, 128, 255] if quick else range(256)
    sps = [0, 1, 127, 254, 255] if quick else range(256)
    ys = [0, 127, 128, 255] if quick else range(256)
    for pc, info in model.CALLS.items():
        for index in raw:
            yield dict(group='actual_JSR_all_raw_A_axis', key=f'raw/{pc:04X}/{index:02X}',
                entry=pc, call_pc=pc, index=index, data_bank=index & 31,
                registers=register_input(pc, index, 0xA7, (index * 17) & 255,
                                         (index * 13) & 255, index))
        for index in info['legal_indices']:
            for sp in sps:
                yield dict(group='actual_JSR_legal_index_all_SP_axis', key=f'sp/{pc:04X}/{index}/{sp}',
                    entry=pc, call_pc=pc, index=index, data_bank=sp & 31,
                    registers=register_input(pc, index, 0xC3, 0xB6, sp, 0xEF))
            for y in ys:
                yield dict(group='actual_JSR_legal_index_all_incoming_Y_axis', key=f'y/{pc:04X}/{index}/{y}',
                    entry=pc, call_pc=pc, index=index, data_bank=y & 31,
                    registers=register_input(pc, index, 0x93, y, 201, 0x20))
    for raw_byte in raw:
        yield dict(group='complete_A099_raw_strategy_prologue', key=f'A099/{raw_byte}',
            entry=0xA099, call_pc=0xA09E, strategy_raw=raw_byte, index=raw_byte & 15,
            data_bank=raw_byte & 31,
            registers=register_input(0xA099, 0xD1, 0x8D, 5, 253, 0x24))
    for x in raw:
        for coordinate in (0, 15, 16, 31):
            yield dict(group='complete_AC7B_saved_2C_two_terrain_calls', key=f'AC7B/{x}/{coordinate}',
                entry=0xAC7B, call_pc=0xACAB, index=x, coordinate=coordinate,
                data_bank=(x + coordinate) & 31,
                registers=register_input(0xAC7B, 0xCA, x, 0xA5, (x * 7) & 255, 0x21))
    for pc in model.CALLS:
        for sp in (0, 253):
            yield dict(group='actual_JSR_replaces_stale_stackword_6000',
                key=f'current-generation/{pc:04X}/{sp}', entry=pc, call_pc=pc,
                index=3, stale_stack_word=0x6000, data_bank=5,
                registers=register_input(pc, 3, 0x35, 0x89, sp, 0x20))
    for index in (0, 13, 14, 15):
        yield dict(group='bare_B517_arbitrary_stack_counterexample', key=f'bare-stack/{index}',
            entry=0xB517, index=index, raw_stack_word=0x6000, data_bank=5,
            registers=register_input(0xB517, index, 91, 57, 253, 0x20))
    for pc, y in ((0xB525, 1), (0xB52B, 28), (0xB525, 29), (0xB52B, 30), (0xB525, 31)):
        yield dict(group='bare_selected_access_counterexample', key=f'bare-access/{pc:04X}/{y}',
            entry=pc, pointer=0x6000, data_bank=5,
            registers=register_input(pc, 0x3B, 29, y, 251, 0x20))


class ContractBus:
    """Ordinary original address space; no implicit hardware read samples."""
    def __init__(self, rom, data_bank=5):
        self.rom = rom
        self.ram = bytearray((index * 29 + 17) & 255 for index in range(2048))
        self.sram = bytearray((index * 11 + 23) & 255 for index in range(8192))
        self.banks = [data_bank, 8, 9, 31]
        self.writes = []
        self.mapper_writes = []

    def __len__(self):
        return 65536

    def __getitem__(self, address):
        address &= 65535
        if address < 8192:
            return self.ram[address & 2047]
        if 0x6000 <= address < 0x8000:
            return self.sram[address - 0x6000]
        if address >= 0x8000:
            bank = self.banks[(address - 0x8000) // 8192]
            return self.rom[model.off(bank, address)]
        raise RuntimeError(f'Explicit hardware input unavailable at {address:04X}')

    def __setitem__(self, address, value):
        address &= 65535
        value &= 255
        if address < 8192:
            target = address & 2047
            before = self.ram[target]
            self.ram[target] = value
            self.writes.append(dict(address=address, physical_address=target,
                                    before=before, value=value, after=value))
        elif 0x6000 <= address < 0x8000:
            before = self.sram[address - 0x6000]
            self.sram[address - 0x6000] = value
            self.writes.append(dict(address=address, physical_address=address,
                                    before=before, value=value, after=value))
        elif address in (0xE000, 0xE800, 0xF000):
            window = {0xE000: 0, 0xE800: 1, 0xF000: 2}[address]
            self.banks[window] = value & 31
            self.mapper_writes.append(dict(address=address, value=value, physical_bank=value & 31))
        else:
            raise RuntimeError(f'Unexpected hardware write at {address:04X}')


def static_checks(rom):
    proof = model.prepared_contract(rom)
    checks = []

    def check(name, value):
        assert value, name
        checks.append(dict(name=name, passed=True))

    good = dict(entry=0xA09E, call_PC=0xA09E, code_pair=[8, 9],
        actual_JSR_executed=True, current_frame_unmodified=True,
        stack_word_from_this_dynamic_JSR=True, no_external_or_interrupt_mutation=True,
        bare_or_middle_entry=False, original_code_and_inline_data=True)
    check('accept_real_current_dynamic_JSR_context', model.admissible_context(good))
    for key, value in [('entry', 0xB517), ('call_PC', 0xB516), ('code_pair', [10, 11]),
        ('actual_JSR_executed', False), ('current_frame_unmodified', False),
        ('stack_word_from_this_dynamic_JSR', False), ('no_external_or_interrupt_mutation', False),
        ('bare_or_middle_entry', True), ('original_code_and_inline_data', False)]:
        wrong = copy.deepcopy(good)
        wrong[key] = value
        check('reject_' + key, not model.admissible_context(wrong))
    contexts = [model.address_contract(pc) for _, pc in model.SELECTED]
    check('both_authoritative_domains_recompute_disjoint', all(
        not ({model.normal(pointer + y) for pointer in row['whole_pointer_values']
              for y in row['Y_values']} & model.AUX) for row in contexts))
    check('top_pointer_Y_equals_authoritative_domain', all(
        set(row['whole_pointer_values']) == {value for part in row['address_cases'] for value in part['whole_pointer_values']}
        and set(row['Y_values']) == {value for part in row['address_cases'] for value in part['Y_values']}
        for row in contexts))
    check('each_relational_case_independently_disjoint', all(not (
        {model.normal(pointer + y) for pointer in part['whole_pointer_values'] for y in part['Y_values']} & model.AUX)
        for row in contexts for part in row['address_cases']))
    check('all_raw_A_addresses_remain_code_ROM', all(
        0xA000 <= model.model_transfer(rom, call_pc, value, 0, 0)[key] < 0xC000
        for call_pc in model.CALLS for value in range(256)
        for key in ('first_logical_address', 'second_logical_address')))
    check('raw255_second_Y_wraps_without_false_word_increment', all(
        model.model_transfer(rom, call_pc, 255, 0, 0)['second_Y'] == 0
        for call_pc in model.CALLS))
    check('AND0F_does_not_prove_strategy_less_than8',
          {value & 15 for value in range(256)} == set(range(16))
          and not model.model_transfer(rom, 0xA09E, 8, 0, 253)['legal_inline_index'])
    check('predicate15_still_legal_but16_not_legal',
          model.model_transfer(rom, 0xACAB, 15, 0, 253)['legal_inline_index']
          and not model.model_transfer(rom, 0xACAB, 16, 0, 253)['legal_inline_index'])
    check('current_JSR_pages_disjoint_from_scratch_for_all_SP', all(
        0x100 <= 0x100 + sp <= 0x1FF and 0x100 + sp not in proof['write_domain']
        for sp in range(256)))
    check('raw_return_comes_from_immutable_actual_JSR_bytes', all(
        info['raw_return'] == pc + 2
        and rom[model.off(8, pc):model.off(8, pc) + 3] == bytes.fromhex('20 17 B5')
        for pc, info in model.CALLS.items()))
    helper = [row for row in proof['original_instructions'] if row['physical_bank'] == 8 and 0xB517 <= row['cpu'] < 0xB536]
    check('helper_has_no_nested_call_or_conditional_branch', all(
        row['op'] not in ('JSR', 'RTS', 'BRK') and not row['op'].startswith('B')
        for row in helper))
    check('helper_only_fixed_ZP_stores_then_indirect_JMP',
          {row['operand'] for row in helper
           if row['op'] in ('STA', 'STY', 'STX')} == set(proof['write_domain'])
          and helper[-1]['op'] == 'JMP')
    terrain = [row for row in proof['original_instructions'] if row['physical_bank'] == 8 and 0xB6E5 <= row['cpu'] <= 0xB74A]
    check('two_terrain_helpers_do_not_write_saved2C', all(
        row['mode'] == 'ab' and row['operand'] in (0x22, 0x23, 0x24, 0x25, 0x26)
        for row in terrain if row['op'] in ('STA', 'STX', 'STY')))
    check('terrain_only_calls_bounded_local_B6EF_and_fixed_F266',
          {row['operand'] for row in terrain if row['op'] == 'JSR'} == {0xB6EF, 0xF266})
    check('fixed_F266_real_bytes_write_DE_mapper_not_2C',
          rom[model.off(31, 0xF266):model.off(31, 0xF266) + 7] == bytes.fromhex('8C DE 00 8C 00 E0 60'))
    check('fourteen_caller_X_premises_are_complete_immediate_LDX_JSR_prefixes',
          len(proof['AC7B_live_2C_lifecycle']['actual_adjacent_LDX_JSR_prefixes']) == 14
          and all(row['input_X'] in range(16) for row in proof['AC7B_live_2C_lifecycle']['actual_adjacent_LDX_JSR_prefixes']))
    check('arbitrary_bare_stack_can_hit_all_five_aux_offsets',
          {model.normal(0x6000 + y) for y in (1, 28, 29, 30, 31)} <= model.AUX)
    check('stop_is_transfer_prefix_never_RTS', proof['stop_boundary']['actual_caller_RTS'] is False)
    check('no_new_semantic_or_official_field_name_credit', proof['source_CPU_cases'] == 0
          and proof['Native_runs'] == 0 and all(value is None for value in proof['official_city_auxiliary_names'].values()))
    return checks


def execute_original_contracts(rom, quick=False):
    # Import is intentionally inside this explicit execution mode only.
    from py65.devices.mpu6502 import MPU
    cases, visits, counts = [], Counter(), Counter()
    bare_hits, raw_target_examples, generation_examples = [], [], []
    known_instructions = {(row['physical_bank'], row['cpu']): row
                          for row in model.prepared_contract(rom)['original_instructions']}
    for spec in specifications(quick):
        memory = ContractBus(rom, spec['data_bank'])
        registers = spec['registers']
        if 'stale_stack_word' in spec:
            memory[0x100 + registers['sp']] = spec['stale_stack_word'] >> 8
            memory[0x100 + ((registers['sp'] - 1) & 255)] = spec['stale_stack_word'] & 255
        if spec['entry'] == 0xA099:
            memory[0x6FA1 + registers['y']] = spec['strategy_raw']
        if spec['entry'] == 0xAC7B:
            memory[0x2B] = 5
            memory[0x6F8C] = 10
            memory[0xA8] = 0xAA
            memory[0xA9] = 0
            for address in range(0xAA, 0xAE):
                memory[address] = 0  # Legal immutable chunk0; not a result/ready sample.
            for slot in (5, 10):
                memory[0x600 + slot] = spec['coordinate']
                memory[0x614 + slot] = spec['coordinate']
        if spec['entry'] == 0xB517:
            pointer = spec['raw_stack_word']
            memory[0x100 + ((registers['sp'] + 1) & 255)] = pointer & 255
            memory[0x100 + ((registers['sp'] + 2) & 255)] = pointer >> 8
        if spec['entry'] in (0xB525, 0xB52B):
            memory[0x21] = spec['pointer'] & 255
            memory[0x22] = spec['pointer'] >> 8
        # Preparation, including literal bare stack words, is disclosed above.
        before_RAM = bytes(memory.ram)
        before_SRAM = bytes(memory.sram)
        memory.writes.clear()
        cpu = MPU(memory=memory)
        for key, value in registers.items():
            setattr(cpu, key, value)
        selected_reads, stack_call, terrain_calls, instruction_count = [], None, [], 0
        for step in range(1000):
            pc, sp, write_start = cpu.pc, cpu.sp, len(memory.writes)
            assert 0x8000 <= pc <= 0xFFFF, (spec['key'], 'unexpected non-ROM opcode', pc)
            bank = memory.banks[(pc - 0x8000) // 8192]
            visits[bank, pc] += 1
            if pc == spec.get('call_pc'):
                assert bank == 8 and cpu.a == spec['index']
                if spec['entry'] == 0xAC7B:
                    assert memory[0x2C] == registers['x'], (spec['key'], 'live2C changed')
                stack_call = dict(pc=pc, a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp,
                    before_current_JSR_stack=[memory[0x100 + cpu.sp], memory[0x100 + ((cpu.sp - 1) & 255)]])
            if bank == 8 and pc in (0xAC8D, 0xACA2):
                terrain_calls.append(dict(call_PC=pc, live_2C=memory[0x2C]))
            if bank == 8 and pc in (0xB525, 0xB52B):
                pointer = memory[0x21] | memory[0x22] << 8
                address = (pointer + cpu.y) & 65535
                selected_reads.append(dict(physical_bank=8, opcode_PC=pc, SP=cpu.sp,
                    live_21_22=pointer, Y=cpu.y, logical_effective_address=address,
                    normalized_address=model.normal(address), value=memory[address],
                    auxiliary_address=model.normal(address) in model.AUX))
            cpu.step()
            instruction_count += 1
            if pc == spec.get('call_pc'):
                assert cpu.pc == 0xB517 and cpu.sp == (sp - 2) & 255
                assert memory.writes[write_start:] == [
                    dict(address=0x100 + sp, physical_address=0x100 + sp,
                         before=stack_call['before_current_JSR_stack'][0], value=(pc + 2) >> 8, after=(pc + 2) >> 8),
                    dict(address=0x100 + ((sp - 1) & 255), physical_address=0x100 + ((sp - 1) & 255),
                         before=stack_call['before_current_JSR_stack'][1], value=(pc + 2) & 255, after=(pc + 2) & 255),
                ], (spec['key'], 'real current JSR write order')
            if spec['entry'] in (0xB525, 0xB52B) or (bank == 8 and pc == 0xB533):
                break
        else:
            raise AssertionError((spec['key'], 'unexpected budget boundary', cpu.pc))
        assert bytes(memory.sram) == before_SRAM
        selected = spec['entry'] in (0xB525, 0xB52B)
        bare = spec['entry'] == 0xB517 or selected
        allowed_RAM = set() if selected else set(range(0x20, 0x25))
        if spec['entry'] == 0xAC7B:
            allowed_RAM |= set(range(0x100, 0x200)) | set(range(0x20, 0x2A)) | {0x2C, 0xDE}
        elif not bare:
            allowed_RAM |= {0x100 + stack_call['sp'], 0x100 + ((stack_call['sp'] - 1) & 255)}
        assert all(value == before_RAM[address] for address, value in enumerate(memory.ram)
                   if address not in allowed_RAM), (spec['key'], 'write outside complete original fixed-store/stack domain')
        expected = None
        if not bare:
            assert stack_call is not None
            expected = model.model_transfer(rom, spec['call_pc'], spec['index'], stack_call['y'], stack_call['sp'])
            assert [(row['opcode_PC'], row['live_21_22'], row['Y'], row['logical_effective_address'], row['value'])
                    for row in selected_reads] == [
                (0xB525, expected['pointer'], expected['first_Y'], expected['first_logical_address'], expected['table_low']),
                (0xB52B, expected['pointer'], expected['second_Y'], expected['second_logical_address'], expected['table_high'])]
            assert all(not row['auxiliary_address'] for row in selected_reads)
            assert cpu.pc == expected['transfer_PC'] and cpu.sp == stack_call['sp']
            assert cpu.y == stack_call['y'] and cpu.x == stack_call['x']
            assert [memory[address] for address in range(0x20, 0x25)] == [
                stack_call['y'], expected['pointer'] & 255, expected['pointer'] >> 8,
                expected['table_low'], expected['table_high']]
            expected_p = (stack_call['p'] & ~(0x80 | 2 | 1)) | (1 if spec['index'] & 128 else 0)
            expected_p |= 2 if stack_call['y'] == 0 else 0
            expected_p |= 0x80 if stack_call['y'] & 128 else 0
            assert cpu.p == expected_p and cpu.a == expected['table_high']
            if spec['entry'] == 0xAC7B:
                assert len(terrain_calls) == 2 and all(row['live_2C'] == registers['x'] for row in terrain_calls)
                assert memory[0x2C] == registers['x'] and cpu.x == 0
            if not expected['legal_inline_index'] and len(raw_target_examples) < 32:
                raw_target_examples.append(dict(case=spec['key'], expected=expected,
                                               target_first_opcode_not_executed=True))
            if 'stale_stack_word' in spec:
                generation_examples.append(dict(case=spec['key'],
                    stale_stack_word=spec['stale_stack_word'], actual_current_JSR=stack_call,
                    current_pointer=memory[0x21] | memory[0x22] << 8,
                    overwritten_by_this_actual_JSR=True, not_inferred_from_same_static_call_PC=True))
        else:
            assert any(row['auxiliary_address'] for row in selected_reads)
            bare_hits.extend(dict(case=spec['key'], **row) for row in selected_reads if row['auxiliary_address'])
        counts[spec['group']] += 1
        cases.append(dict(case_key=spec['key'], group=spec['group'], comparison='explicit_prefix',
            completion_kind='bare_selected_access_prefix' if selected else 'original_indirect_JMP_transfer_prefix',
            actual_caller_RTS=False, synthetic_bare_stack_or_middle_entry=bare,
            input_registers=registers, actual_dynamic_JSR=stack_call,
            observed_logical_reads=selected_reads, final_registers={key: getattr(cpu, key) for key in registers},
            final_banks=list(memory.banks), original_instruction_count=instruction_count,
            logical_address_contract_matches=True, whole_SRAM_unchanged=True,
            all_2048_RAM_addresses_checked_against_declared_write_domain=True,
            exact_selected_scratch_and_current_stack_postcondition=not bare,
            target_first_opcode_not_executed=not selected, terrain_calls=terrain_calls))
    assert {address for row in bare_hits for address in [row['normalized_address']]} >= {0x6001, 0x601C, 0x601D, 0x601E, 0x601F}
    return dict(cases=cases, group_case_counts=dict(counts),
                executed_instruction_positions=[dict(**known_instructions[bank, pc], visits=count)
                    for (bank, pc), count in sorted(visits.items())],
                bare_auxiliary_counterexamples=bare_hits, raw_outside_inline_target_examples=raw_target_examples,
                dynamic_generation_examples=generation_examples)


def final_audit(rom, receipt, checks):
    result = model.generate(rom, receipt)
    prior = model.read(model.BASE_LEDGER)['accesses']
    rows = model.read('analysis/phase32/fields-static/all-indirect-accesses.json')['accesses']
    for old, row in zip(prior, rows):
        selected = (row['physical_bank'], row['cpu']) in model.SELECTED
        assert row['physical_bank'] == old['physical_bank'] and row['cpu'] == old['cpu']
        if not selected:
            assert row['classification'] == old['classification'] and row.get('address_contract') == old.get('address_contract')
        if row['classification'] == 'proved_disjoint_auxiliary_address_domain' and selected:
            authority = row['address_contract']
            actual = {model.normal(pointer + y) for pointer in authority['whole_pointer_values'] for y in authority['Y_values']}
            assert not actual & model.AUX and authority['auxiliary_address_intersection_count'] == 0
            assert row['whole_pointer_values'] == authority['whole_pointer_values']
            assert row['Y_values'] == authority['Y_values']
    assert result['all_indirect_classification_counts'] == dict(
        proved_disjoint_auxiliary_address_domain=1203, possible_city_auxiliary_alias=80,
        unresolved_pointer_or_index_contract=243)
    assert result['remaining_access_count'] == 323
    assert model.read('analysis/phase32/fields-static/raw345-executability-ledger.json') == model.read(
        'analysis/phase31/fields-static/raw345-executability-ledger.json')
    for group in ('source_and_validator_sha256', 'artifact_sha256'):
        for path, digest in result[group].items():
            assert model.sha(ROOT / path) == digest, ('stale final evidence', path)
    final = dict(schema='phase32-inline-dispatch-field-verification-v1', status='passed', quick=False,
        ROM_sha256=model.ROM_SHA, old_phase31_audit_sha256=model.BASE_AUDIT_SHA,
        original_CPU_contract_cases=receipt['original_CPU_contract_cases'],
        actual_caller_RTS_CPU_cases=0,
        explicit_prefix_CPU_cases=receipt['original_CPU_contract_cases'],
        Source_CPU_cases=0, Native_runs=0, model_guard_check_count=len(checks),
        newly_proved_disjoint_all_count=2, all_indirect_access_count=1526,
        classification_counts=result['all_indirect_classification_counts'], remaining_access_count=323,
        failed_count=0, failures=[], checks=checks,
        source_and_validator_sha256=result['source_and_validator_sha256'],
        artifact_sha256={**result['artifact_sha256'],
            'analysis/phase32/fields-static/analysis-summary.json': model.sha(OUT / 'analysis-summary.json'),
            'analysis/phase32/fields-static/evidence.json': model.sha(OUT / 'evidence.json'),
            'analysis/phase32/fields-static/README.md': model.sha(OUT / 'README.md')},
        limits=receipt['limits'])
    model.save('verification.json', final)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--execute-original-cpu', action='store_true', help='Explicit Root execution-owner mode; imports py65 only here.')
    parser.add_argument('--quick', action='store_true', help='Small Root CPU subset; never promotes classification or writes final verification.')
    parser.add_argument('--audit-only', action='store_true', help='Recheck existing full CPU receipt and regenerate only new32 evidence/audit.')
    args = parser.parse_args()
    assert not (args.audit_only and args.execute_original_cpu)
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == model.ROM_SHA
    assert model.sha(ROOT / 'analysis/phase31/verification.json') == model.BASE_AUDIT_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    checks = static_checks(rom)
    if args.audit_only:
        receipt = model.read('analysis/phase32/fields-static/cpu-contract-validation.json')
        assert receipt['quick'] is False and model.receipt_usable(receipt)
        result = final_audit(rom, receipt, checks)
    elif args.execute_original_cpu:
        model.generate(rom)
        cpu = execute_original_contracts(rom, args.quick)
        scripts = ['scripts/analyze_inline_dispatch_contracts_phase32.py',
                   'scripts/verify_inline_dispatch_contracts_phase32.py']
        receipt = dict(schema='phase32-Root-original-CPU-inline-dispatch-contracts-v1',
            status='passed', quick=args.quick, ROM_sha256=model.ROM_SHA,
            original_CPU_contract_cases=len(cpu['cases']), actual_caller_RTS_CPU_cases=0,
            explicit_prefix_CPU_cases=len(cpu['cases']), source_CPU_cases=0, Native_runs=0,
            failed_count=0, failures=[], model_guard_check_count=len(checks), checks=checks,
            all_contract_cases_stop_at_inline_transfer_or_selected_access_prefix=True,
            contract_sha256=model.sha(OUT / 'current-frame-dispatch-contract.json'),
            source_and_validator_sha256={path: model.sha(ROOT / path) for path in scripts},
            execution_owner='Root explicit --execute-original-cpu mode; not analyzer agent, Native or Source execution.',
            comparison_scope=dict(RAM_environment_bytes=2048, all_RAM_nonwrite_domain_invariants_checked=True,
                full_SRAM_unchanged_bytes=8192,
                interpretation='Current-frame logical read/address/stack/register postconditions and whole-RAM nonwrite invariants, not a Source diff or hardware bus trace.',
                bare_inputs='Explicit synthetic stack words or middle pointer/Y; no legal-caller provenance claim.'),
            limits=model.prepared_contract(rom)['limits'], **cpu)
        model.save('quick-validation.json' if args.quick else 'cpu-contract-validation.json', receipt)
        result = receipt if args.quick else final_audit(rom, receipt, checks)
    else:
        result = dict(schema='phase32-inline-dispatch-static-model-checks-v1',
            status='static_model_checks_passed_CPU_not_executed', ROM_sha256=model.ROM_SHA,
            original_CPU_contract_cases=0, source_CPU_cases=0, Native_runs=0,
            planned_full_original_CPU_cases=sum(1 for _ in specifications(False)),
            planned_quick_original_CPU_cases=sum(1 for _ in specifications(True)),
            model_guard_check_count=len(checks), checks=checks,
            CPU_contract_receipt_required=True,
            source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)): model.sha(Path(__file__))})
        model.save('static-verification.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'original_CPU_contract_cases', 'model_guard_check_count')
                      if key in result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
