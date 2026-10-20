#!/usr/bin/env python3
"""Read-only phase19 relational-domain and original constructor validation.

CPU checks execute original constructor bytes to a declared prefix boundary
(or D304's real caller RTS). They are not recovered-source comparisons.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase19/fields-static'
SPEC = importlib.util.spec_from_file_location('phase19_pointer_model', ROOT / 'scripts/analyze_city_pointer_provenance.py')
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_checks():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(dict(name=name, passed=True))
    pair = model.Pair(frozenset((0x63C0, 0x6408)), 1)
    a = model.State(pairs={0: pair})
    model.copy_store(a, 0x10, model.byte_refs(a, 0))
    model.copy_store(a, 0x11, model.byte_refs(a, 1))
    check('two intact halves make complete copy', a.pairs[0x10] == pair)
    b = model.State(pairs={0: pair})
    model.copy_store(b, 0x11, model.byte_refs(b, 1))
    model.copy_store(b, 0x10, model.byte_refs(b, 0))
    check('high-first copy remains joint', b.pairs[0x10] == pair)
    a = model.State(pairs={0: model.Pair(frozenset((0xA0F2,)))})
    model.copy_store(a, 0x10, model.byte_refs(a, 0))
    a.registers = (model.byte_refs(a, 0), frozenset(), frozenset())
    a.stack = (model.byte_refs(a, 0),)
    # SAME producer PC is irrelevant. Real low=F2 from old word, high=5F
    # from new word could make 5FF2+15=6001; no pair may be invented here.
    model.atomic_pair(a, 0, model.Pair(frozenset((0x5F20,))))
    check('source reassignment kills register half capabilities', not any(a.registers))
    check('source reassignment kills saved PHA half capability', not any(a.stack))
    check('source reassignment kills pending half copies', not a.pending)
    model.copy_store(a, 0x11, model.byte_refs(a, 1))
    check('same-PC different dynamic generations cannot join', 0x10 not in a.pairs)
    check('mixed-generation counterexample actually aliases city1', ((0xA0F2 & 255) | (0x5F20 & 0xFF00)) + 15 == 0x6001)
    a = model.State(pairs={0: pair, 0x10: pair}, pending={0x20: frozenset(((0, 0),))})
    model.kill(a, {1})
    check('partial high write kills source pair', 0 not in a.pairs)
    check('old completed destination independently survives', a.pairs.get(0x10) == pair)
    check('partial write kills pending refs even at another byte', not a.pending)
    a = model.State(pairs={0: pair})
    b = model.State(pairs={0: model.Pair(frozenset((0x65C0,)), 2)})
    merged = model.join(a, b)
    check('merge unions complete words only', merged.pairs[0].addresses == frozenset((0x63C0, 0x6408, 0x65C0)))
    check('merge does not invent low/high cross product', 0x6308 not in merged.pairs[0].addresses)
    check('a predecessor without pair makes merge unknown', not model.join(a, model.State()).pairs)
    a = model.State(pairs={0: pair, 0x20: model.Pair(frozenset((0x9000,)))})
    model.copy_store(a, 0x10, model.byte_refs(a, 0))
    model.copy_store(a, 0x11, model.byte_refs(a, 0x21))
    check('halves from different live pairs cannot join', 0x10 not in a.pairs)
    for address in (0, 1, 0x800, 0x801, 0x1000, 0x1001, 0x1800, 0x1801):
        a = model.State(pairs={0: pair})
        model.kill(a, {model.normalized_ram(address)})
        check(f'RAM mirror partial write {address:04X} kills pair', not a.pairs)
    check('indexed wrap example includes zero-page', any(model.normalized_ram((0xFFF0 + i) & 65535) == 0 for i in range(256)))
    a = model.State(pairs={0: pair}, registers=(frozenset(((0, 0),)),) * 3,
                    stack=(frozenset(((0, 1),)),), pending={0x20: frozenset(((0, 0),))})
    model.kill(a, model.ZP)
    check('unknown store/call cannot retain pairs or half references', not a.pairs and not a.pending and not any(a.registers) and not any(a.stack))
    # Exercise the actual instruction/call transfer, not just the primitive
    # kill function, for the memory alias cases most likely to be missed.
    engine = model.Analysis.__new__(model.Analysis)
    engine.known, engine.indexed, engine.access_index, engine.old_safe = {}, {}, {}, {}
    engine.factories, engine.factory_ids, engine.markers = {}, {}, {}
    engine.copies, engine.copy_details, engine.effects = set(), {}, {}
    engine.leaf_contract = lambda entry, state: None
    sample_key = (8, 0xA100)
    def instruction(op, mode, operand):
        engine.known[sample_key] = dict(physical_bank=8, cpu=0xA100, rom_offset=0,
                                       raw_hex='', op=op, mode=mode, operand=operand)
    for mode, operand in (('ab', 0x801), ('abx', 0xFFF0), ('aby', 0x1800), ('zpx', 0), ('zpy', 0)):
        instruction('STA', mode, operand)
        state = engine.transfer(sample_key, model.State(pairs={0: pair}))
        check(f'actual {mode} write transfer kills all possible pair aliases', 0 not in state.pairs)
    instruction('STA', 'iy', 0x20)
    state = engine.transfer(sample_key, model.State(pairs={0: pair}))
    check('actual unknown indirect store kills pair', not state.pairs)
    state = engine.apply_call(model.State(pairs={0: pair}), None, sample_key)
    check('actual unknown call kills pair', not state.pairs)
    instruction('STA', 'ab', 0x900)
    state = model.State(pairs={0: pair}, stack=(frozenset(((0, 0),)),))
    state = engine.transfer(sample_key, state)
    check('actual RAM-stack mirror store invalidates saved half refs', not state.stack)
    # Enumerate short traces with differing original/current source values.
    # These concrete finite counterexamples test generation invalidation, not
    # a claim that every possible whole-program abstract transfer was proved.
    exhaustive = 0
    for old in (0, 0xFF, 0x100, 0x5FF2, 0x63C0, 0xFFFF):
        for new in (0, 0xFF, 0x100, 0x5F20, 0x6408, 0xFFFF):
            for high_first in (False, True):
                a = model.State(pairs={0: model.Pair(frozenset((old,)))})
                first, second = (1, 0) if high_first else (0, 1)
                model.copy_store(a, 0x10 + first, model.byte_refs(a, first))
                model.atomic_pair(a, 0, model.Pair(frozenset((new,))))
                model.copy_store(a, 0x10 + second, model.byte_refs(a, second))
                assert 0x10 not in a.pairs
                exhaustive += 1
    checks.append(dict(name='cross-generation short traces', passed=True, finite_trace_count=exhaustive))
    return checks


class OriginalMemory:
    """Small original-byte oracle: ROM reads, writable RAM/SRAM, mapper ports.

    Constructors only use the mapped pair and fixed bank; their mapper calls
    write the 8000 data-window selector, not the executing A000/E000 code.
    Prefix stops before F308/F387 start reading that switched data window.
    """
    def __init__(self, rom, bank):
        self.data = bytearray(65536)
        pair = 8 if bank == 8 else 10
        self.data[0xA000:0xC000] = rom[16 + pair * 8192:16 + (pair + 1) * 8192]
        self.data[0xC000:0xE000] = rom[16 + (pair + 1) * 8192:16 + (pair + 2) * 8192]
        self.data[0xE000:0x10000] = rom[16 + 31 * 8192:16 + 32 * 8192]
        self.writes = []

    def __getitem__(self, address):
        address &= 65535
        physical = model.normalized_ram(address)
        return self.data[physical if physical is not None else address]

    def __setitem__(self, address, value):
        address, value = address & 65535, value & 255
        self.writes.append((address, value))
        physical = model.normalized_ram(address)
        if physical is not None:
            self.data[physical] = value
        elif address < 0x8000:
            self.data[address] = value


def original_factory_checks(rom):
    from py65.devices.mpu6502 import MPU
    rows = []
    for key, descriptor in model.factory_specs(rom).items():
        values = []
        kind = descriptor['kind']
        for raw_a in range(256):
            memory = OriginalMemory(rom, key[0])
            cpu = MPU(memory=memory, pc=key[1])
            cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp = raw_a, (raw_a * 13 + 7) & 255, (raw_a * 29 + 11) & 255, 0x20 | (raw_a & 1), 0xF0
            # Real caller stack for D304's actual RTS; other cases are strict
            # constructor prefixes and do not pretend to have returned.
            memory[0x1F1], memory[0x1F2] = 0xFF, 4
            memory.writes.clear()
            end = descriptor['marker'][1] + (2 if key[0] == 11 else 3) if descriptor['marker'] else 0x500
            steps = 0
            while cpu.pc != end:
                cpu.step()
                steps += 1
                assert steps <= 1000, (key, raw_a, hex(cpu.pc))
            base = descriptor['base']
            actual = memory[base] | (memory[(base + 1) & 255] << 8)
            if kind == 'city':
                expected = 0x6000 + 32 * raw_a
            elif kind == 'officer':
                expected = 0x63C0 + 12 * raw_a
            elif kind == 'name_ROM':
                expected = 0x901A + 10 * raw_a
            elif kind == 'initial_officer_ROM':
                expected = 0x8000 + 12 * raw_a
            else:
                table = 0xF379 if key[0] == 31 else 0xB4D3 if key[0] == 8 else 0xD328
                offset = model.original(key[0], table + 2 * (raw_a & 15))
                expected = rom[offset] | (rom[offset + 1] << 8)
            assert actual == expected and actual in descriptor['addresses'], (key, raw_a, actual, expected)
            zp_writes = {model.normalized_ram(address) for address, _ in memory.writes
                         if (model.normalized_ram(address) is not None and model.normalized_ram(address) < 256)}
            assert zp_writes <= descriptor['writes'], (key, raw_a, zp_writes, descriptor['writes'])
            if not descriptor['marker']:
                assert cpu.sp == 0xF2
            values.append(actual)
        rows.append(dict(physical_bank=key[0], cpu=key[1], raw_A_count=256,
                         boundary='constructor_complete_prefix' if descriptor['marker'] else 'actual_caller_RTS',
                         stop_pc=end, exact_pointer_and_ZP_footprint=True,
                         addresses_sha256=hashlib.sha256(bytes(v & 255 for v in values) + bytes(v >> 8 for v in values)).hexdigest()))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == model.ROM_SHA256
    summary = json.loads((OUT / 'analysis-summary.json').read_text())
    assert summary['analyzer_sha256'] == sha(ROOT / summary['analyzer_path'])
    for path, expected in summary['artifact_sha256'].items():
        assert sha(ROOT / path) == expected, path
        assert not any(part.startswith('exploratory') for part in Path(path).parts)
    raw_count = 0
    for path in OUT.glob('*.json'):
        if path.name in ('verification.json', 'evidence.json'):
            continue
        def visit(obj):
            nonlocal raw_count
            if isinstance(obj, dict):
                if all(name in obj for name in ('physical_bank', 'cpu', 'rom_offset', 'raw_hex')):
                    raw = bytes.fromhex(obj['raw_hex'])
                    offset = model.original(obj['physical_bank'], obj['cpu'])
                    assert obj['rom_offset'] == offset
                    assert rom[offset:offset + len(raw)] == raw
                    raw_count += 1
                for value in obj.values():
                    visit(value)
            elif isinstance(obj, list):
                for value in obj:
                    visit(value)
        visit(json.loads(path.read_text()))
    models = model_checks()
    original = original_factory_checks(rom)
    all_rows = json.loads((OUT / 'all-indirect-accesses.json').read_text())['accesses']
    old = json.loads((OUT / 'access-contracts.json').read_text())['accesses']
    added = json.loads((OUT / 'new-indirect-accesses.json').read_text())['accesses']
    assert (len(all_rows), len(old), len(added)) == (1526, 589, 45)
    for rows, key in ((all_rows, 'all_indirect_classification_counts'), (old, 'classification_counts'), (added, 'new_indirect_classification_counts')):
        assert dict(Counter(r['classification'] for r in rows)) == summary[key]
        for row in rows:
            proof = row['address_contract']
            if proof:
                expected = sorted({(base + y) & 65535 for base in proof['whole_pointer_values'] for y in proof['Y_values']} & model.AUX)
                assert proof['possible_auxiliary_effective_addresses'] == expected
                assert proof['auxiliary_address_intersection_count'] == len(expected)
                if row['classification'] == 'proved_disjoint_auxiliary_address_domain' and row['proof_basis'] == 'whole_pointer_relation':
                    assert not expected
    result = dict(schema='phase19-city-pointer-provenance-validation-v1', status='passed', failed_count=0,
                  ROM_sha256=model.ROM_SHA256, source_CPU_cases=0,
                  model_guard_check_count=len(models), model_checks=models,
                  original_factory_contract_CPU_checks=sum(r['raw_A_count'] for r in original),
                  original_factory_constructor_prefix_checks=sum(r['raw_A_count'] for r in original if r['boundary'] == 'constructor_complete_prefix'),
                  original_factory_actual_caller_RTS_checks=sum(r['raw_A_count'] for r in original if r['boundary'] == 'actual_caller_RTS'),
                  original_factory_checks=original,
                  original_factory_CPU_scope='Original-byte pointer/declared-ZP-write contract oracle only; no recovered gameplay source comparison, Native CPU trace, or whole-program execution claim.',
                  original_nested_byte_ranges_verified=raw_count,
                  full_CFG_instruction_bytes_verified=summary['original_instruction_bytes_verified'],
                  source_and_validator_sha256={
                      'scripts/analyze_city_pointer_provenance.py': sha(ROOT / 'scripts/analyze_city_pointer_provenance.py'),
                      'scripts/verify_city_pointer_provenance.py': sha(__file__),
                  },
                  artifact_sha256={str(path.relative_to(ROOT)): sha(path) for path in OUT.glob('*.json') if path.name not in ('verification.json', 'evidence.json')} |
                                  {'analysis/phase19/fields-static/README.md': sha(OUT / 'README.md')},
                  classifications=dict(old589=summary['classification_counts'], all1526=summary['all_indirect_classification_counts'], new45=summary['new_indirect_classification_counts']),
                  limitations=['Finite model counterexamples and exhaustive raw-A constructors validate key invariants, not a formal proof of the complete analyzer.',
                               'All pointer exclusions remain scoped to the frozen trusted CFG and inherited conservative index/write contracts.'])
    model.save('verification.json', result)
    model.save('evidence.json', dict(schema='phase19-whole-pointer-static-evidence-v1', status='passed',
        ROM_sha256=model.ROM_SHA256, analyzer_path='scripts/analyze_city_pointer_provenance.py',
        analyzer_sha256=sha(ROOT / 'scripts/analyze_city_pointer_provenance.py'),
        validator_path='scripts/verify_city_pointer_provenance.py', validator_sha256=sha(__file__),
        source_and_validator_sha256=result['source_and_validator_sha256'],
        artifact_sha256=summary['artifact_sha256'] | result['artifact_sha256'] |
                        {'analysis/phase19/fields-static/verification.json': sha(OUT / 'verification.json')},
        baseline_candidate_count=589, all_indirect_access_count=1526, new_indirect_access_count=45,
        classifications=result['classifications'], source_CPU_cases=0,
        original_factory_contract_CPU_checks=result['original_factory_contract_CPU_checks'],
        original_factory_constructor_prefix_checks=result['original_factory_constructor_prefix_checks'],
        original_factory_actual_caller_RTS_checks=result['original_factory_actual_caller_RTS_checks'],
        model_guard_check_count=result['model_guard_check_count'],
        target_official_names=dict(city_plus1=None, city_plus28=None, city_plus29=None, city_plus30=None, city_plus31=None),
        separately_confirmed_original_UI_label=dict(city_plus16=['宝', 'タカラ']),
        methods=['Must-paired whole-address union; no low/high Cartesian recombination.',
                 'Source-pair partial/indexed/indirect/mirror/callee writes invalidate all register/stack/pending half capabilities.',
                 'Conditional call-free leaf contracts record required whole pointer sets and every local RTS exit.',
                 'Frozen phase18 independent disjoint proofs retain their original conditions when the new relation is unknown.'],
        limits=summary['limitations']))
    print(json.dumps({key: result[key] for key in ('status', 'model_guard_check_count', 'original_factory_contract_CPU_checks', 'original_nested_byte_ranges_verified')}))


if __name__ == '__main__':
    main()
