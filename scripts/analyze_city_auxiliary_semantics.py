#!/usr/bin/env python3
"""Phase21: net register-return relations, bounded recruitment and direct accesses.

Only writes phase21 outputs. Frozen phase20 may-write summaries are effects,
not net register postconditions. This new layer keeps those concepts separate.
"""
from collections import Counter, deque
from dataclasses import dataclass
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase21/fields-static'
SPEC = importlib.util.spec_from_file_location('frozen_phase20_context', ROOT / 'scripts/analyze_city_auxiliary_contexts.py')
old = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = old
SPEC.loader.exec_module(old)
base = old.base
INPUTS = old.INPUTS + [
    'scripts/analyze_city_auxiliary_contexts.py',
    'analysis/phase20/fields-static/all-indirect-accesses.json',
    'analysis/phase20/fields-static/remaining-accesses.json',
    'analysis/phase20/fields-static/analysis-summary.json',
    'analysis/phase20/fields-static/verification.json',
    'analysis/phase20/fields-static/authoritative-contract-selection.json',
    'analysis/phase20/fields-static/call-effect-summaries.json',
    'analysis/phase20/fields-static/city-field-root-inventory.json',
]
REGS = ('A', 'X', 'Y')


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


@dataclass
class ReturnState:
    registers: tuple = ('input_A', 'input_X', 'input_Y')
    cells: dict = None
    stack: tuple = ()

    def __post_init__(self):
        if self.cells is None:
            self.cells = {}

    def copy(self):
        return ReturnState(self.registers, dict(self.cells), self.stack)


def return_join(left, right):
    return ReturnState(tuple(a if a == b else None for a, b in zip(left.registers, right.registers)),
                       {k: left.cells[k] for k in left.cells.keys() & right.cells.keys() if left.cells[k] == right.cells[k]},
                       tuple(a if a == b else None for a, b in zip(left.stack, right.stack)) if len(left.stack) == len(right.stack) else ())


def direct_addresses(row):
    mode, operand = row['mode'], row['operand']
    if mode in ('zp', 'ab'):
        return frozenset((operand,))
    if mode in ('zpx', 'zpy'):
        return frozenset((operand + i) & 255 for i in range(256))
    if mode in ('abx', 'aby'):
        return frozenset((operand + i) & 65535 for i in range(256))
    return None


def return_transfer(row, state):
    """Universal equality proof; every unknown/mirror/partial write kills cells.

    Values are equalities to caller input registers, not sampled byte values.
    All possible indexed addresses use raw0..255 and 16-bit wrap. Hardware stack
    aliases invalidate saved PHA values. No nested call is accepted here.
    """
    value = state.copy()
    regs, cells, stack = list(value.registers), value.cells, value.stack
    op, mode, operand = row['op'], row['mode'], row['operand']
    if op in ('LDA', 'LDX', 'LDY'):
        addr = base.normalized_ram(operand) if mode in ('zp', 'ab') else None
        regs[('LDA', 'LDX', 'LDY').index(op)] = cells.get(addr) if addr is not None and addr < 256 else None
    elif op in ('TAX', 'TAY', 'TXA', 'TYA'):
        a, b = {'TAX': (0, 1), 'TAY': (0, 2), 'TXA': (1, 0), 'TYA': (2, 0)}[op]
        regs[b] = regs[a]
    elif op in ('ADC', 'SBC', 'AND', 'ORA', 'EOR') or (op in ('ASL', 'LSR', 'ROL', 'ROR') and mode == 'a'):
        regs[0] = None
    elif op in ('INX', 'DEX', 'TSX'):
        regs[1] = None
    elif op in ('INY', 'DEY'):
        regs[2] = None
    elif op in ('PHA', 'PHP'):
        stack = (stack + (regs[0] if op == 'PHA' else None,))[-16:]
    elif op in ('PLA', 'PLP'):
        if op == 'PLA':
            regs[0] = stack[-1] if stack else None
        stack = stack[:-1]
    elif op == 'TXS':
        stack = ()
    if op in base.WRITES and mode != 'a':
        addresses = direct_addresses(row)
        if addresses is None:
            cells.clear()
            stack = ()
        else:
            normalized = {base.normalized_ram(a) for a in addresses}
            touched = {a for a in normalized if a is not None and a < 256}
            for addr in touched:
                cells.pop(addr, None)
            if op in ('STA', 'STX', 'STY') and len(addresses) == 1 and len(touched) == 1:
                ref = regs[('STA', 'STX', 'STY').index(op)]
                if ref is not None:
                    cells[next(iter(touched))] = ref
            if any(a is not None and 256 <= a < 512 for a in normalized):
                stack = ()
    value.registers, value.stack = tuple(regs), stack
    return value


class Analysis(old.Analysis):
    def __init__(self, rom):
        super().__init__(rom)
        self.passthrough, self.passthrough_catalog = {}, []
        self.prove_leaf_passthrough()
        self.recruitment_contract = self.install_recruitment_loop()

    def prove_leaf_passthrough(self):
        for entry in sorted(self.effects):
            structure = self.function_structure(entry)
            if structure['barriers'] or not structure['exits'] or structure['calls']:
                continue
            if any(self.known[k]['op'] == 'JSR' for k in structure['nodes']):
                continue
            states, queue, queued = {entry: ReturnState()}, deque((entry,)), {entry}
            transfers = 0
            while queue:
                key = queue.popleft()
                queued.discard(key)
                after = return_transfer(self.known[key], states[key])
                if self.known[key]['op'] == 'RTS':
                    continue
                for target in self.edges.get(key, ()):
                    if target not in structure['nodes']:
                        continue
                    before = states.get(target)
                    merged = after if before is None else return_join(before, after)
                    if before != merged:
                        states[target] = merged
                        if target not in queued:
                            queue.append(target)
                            queued.add(target)
                transfers += 1
            if any(k not in states for k in structure['exits']):
                continue
            result = states[structure['exits'][0]]
            for key in structure['exits'][1:]:
                result = return_join(result, states[key])
            names = tuple(name for name, ref in zip(REGS, result.registers) if ref == 'input_' + name)
            if not names:
                continue
            self.passthrough[entry] = names
            self.passthrough_catalog.append(dict(**self.raw(entry),
                preserved_input_registers=list(names), RTS_exits=[self.raw(k) for k in structure['exits']],
                original_instructions=[self.raw(k) for k in sorted(structure['nodes'])],
                local_abstract_transfers=transfers,
                contract='For every accepted ordinary original local RTS path, the named output register equals its input. All raw byte inputs, all branch successors and unknown memory are included. May-write is not net clobber.',
                limits='Call-free trusted CFG and no intervening IRQ/NMI/external mutation; not a termination or interrupt-atomicity claim. No sampled call-PC identity is used.'))
        assert 'X' in self.passthrough[31, 0xE89A]
        assert 'X' in self.passthrough[11, 0xC66F]

    def apply_call(self, state, target, key, far=False):
        result = super().apply_call(state, target, key, far)
        names = self.passthrough.get(target, ())
        refs, numbers = list(result.registers), list(result.numbers)
        for index, name in enumerate(REGS):
            if name not in names or (far and name in ('A', 'Y')):
                continue
            refs[index] = base.valid_refs(state.registers[index], result.pairs)
            numbers[index] = state.numbers[index]
        result.registers, result.numbers = tuple(refs), tuple(numbers)
        return result

    def contract(self, key):
        proof = super().contract(key)
        if proof is not None and key in {(11, pc) for pc in (0xC726, 0xC73F, 0xC767, 0xC76D)}:
            proof['required_execution_contract'] = dict(
                path='analysis/phase21/fields-static/bounded-recruitment-contract.json',
                original_entry_physical_bank=11, original_entry_cpu=0xC71A,
                ordinary_normal_return_model=True, intervening_interrupts_or_external_mutation=False,
                scope='The proven initializer-rooted loop invariant; not an interrupt-atomic or arbitrary mid-loop-entry theorem.')
        return proof

    def install_recruitment_loop(self):
        start, last = (11, 0xC71A), (11, 0xC76D)
        nodes = {k for k in self.known if k[0] == 11 and start[1] <= k[1] <= last[1]}
        incoming = [(source, target) for target in nodes for source in self.predecessors.get(target, ()) if source not in nodes]
        assert all(target == start for source, target in incoming), incoming
        assert not any(k in nodes and k != start for k in self.effects), 'External subroutine entry into loop body'
        calls = {base.mapped(k, self.known[k]['operand']) for k in nodes if self.known[k]['op'] == 'JSR'}
        assert calls == {(11, 0xC66F), (31, 0xE89A)}
        for call in calls:
            assert 'X' in self.passthrough[call]
            effect = self.effects[call]
            assert not set(effect['zero_page_may_write']) & {0x22, 0x23}
        assert self.rom[base.original(11, 0xC752):base.original(11, 0xC764)] == bytes.fromhex('A5 22 18 69 0C 85 22 A5 23 69 00 85 23 E8 E0 ED 90 C0')
        contract = dict(schema='phase21-bounded-original-recruitment-loop-v1',
            physical_bank=11, entry_cpu=0xC71A, normal_no_candidate_return_cpu=0xC764,
            success_branch_cpu=0xC765, success_prefix_stop_cpu=0xC76F,
            initializer_pointer=0x63C0, stride=12, counter_start=0, counter_limit_exclusive=237,
            maximum_iterations=237, whole_pointer_values=list(range(0x63C0, 0x63C0 + 12 * 237, 12)),
            sites=[dict(cpu=pc, pointer_zero_page=0x22, Y_values=[index]) for pc, index in
                   ((0xC726, 11), (0xC73F, 5), (0xC767, 11), (0xC76D, 11))],
            incoming_edges=[dict(source=self.raw(a), target_cpu=b[1]) for a, b in incoming],
            original_instructions=[self.raw(k) for k in sorted(nodes)],
            callee_dependencies=[dict(physical_bank=bank, cpu=pc, input_X_equals_output_X=True,
                zero_page_may_write=self.effects[bank, pc]['zero_page_may_write']) for bank, pc in sorted(calls)],
            proof='C71A initializes22/23=63C0 and X=0. C66F/E89A preserve X and do not touch22/23. C752..C75D is an exact carry-propagating16-bit +12; INX then CPX#ED/BCC admits X=0..236. The only success branch leaves this loop before the increment. No external trusted CFG edge or known procedure entry bypasses the initializer.',
            mechanical_meaning='Search status-low2==0 officers whose byte5 equals current city0036 or one of eight6F73 neighbors; success sets low2=2 and later appends the ID to a first-FF city scan. This is recruitment, not HP maintenance.',
            limits='Only original initializer-rooted ordinary execution without intervening interrupts/external memory mutation. Rejection-sampling may loop; this is an iteration-index/address invariant, not a universal time bound. Later unbounded first-FF city-roster scan remains possible auxiliary alias.')
        for site in contract['sites']:
            self.structured_sites[11, site['cpu']] = dict(pointer=0x22,
                addresses=frozenset(contract['whole_pointer_values']), indices=frozenset(site['Y_values']),
                name='normal_return_237_officer_recruitment_scan', entry=start)
        return contract


def memory_kind(op):
    return 'write' if op in ('STA', 'STX', 'STY') else 'read_modify_write' if op in base.WRITES else 'read'


def direct_inventory(engine):
    rows, candidates = [], []
    for key, row in sorted(engine.known.items()):
        if row['mode'] not in ('zp', 'zpx', 'zpy', 'ab', 'abx', 'aby') or row['op'] in ('JSR', 'JMP'):
            continue
        addresses = direct_addresses(row)
        hits = sorted(addresses & base.AUX)
        item = dict(**engine.raw(key), access_kind=memory_kind(row['op']),
                    raw_index_domain=list(range(256)) if row['mode'] in ('abx', 'aby', 'zpx', 'zpy') else [0],
                    address_domain_count=len(addresses), possible_auxiliary_effective_addresses=hits,
                    auxiliary_address_intersection_count=len(hits),
                    classification='possible_direct_auxiliary_access' if hits else 'proved_disjoint_auxiliary_address_domain')
        rows.append(item)
        if hits:
            candidates.append(item)
    # Raw PRG byte windows are candidates, not decoded/reachable instructions.
    absolute = {}
    for operation, codes in {
        'ORA': (0x0D, 0x1D, 0x19), 'AND': (0x2D, 0x3D, 0x39),
        'EOR': (0x4D, 0x5D, 0x59), 'ADC': (0x6D, 0x7D, 0x79),
        'SBC': (0xED, 0xFD, 0xF9), 'LDA': (0xAD, 0xBD, 0xB9),
        'CMP': (0xCD, 0xDD, 0xD9), 'STA': (0x8D, 0x9D, 0x99),
    }.items():
        absolute.update({code: (operation, mode) for code, mode in zip(codes, ('ab', 'abx', 'aby'))})
    for code, operation, mode in (
        (0xAE, 'LDX', 'ab'), (0xBE, 'LDX', 'aby'), (0xAC, 'LDY', 'ab'), (0xBC, 'LDY', 'abx'),
        (0xEC, 'CPX', 'ab'), (0xCC, 'CPY', 'ab'), (0x2C, 'BIT', 'ab'),
        (0x8E, 'STX', 'ab'), (0x8C, 'STY', 'ab'),
        (0x0E, 'ASL', 'ab'), (0x1E, 'ASL', 'abx'), (0x2E, 'ROL', 'ab'), (0x3E, 'ROL', 'abx'),
        (0x4E, 'LSR', 'ab'), (0x5E, 'LSR', 'abx'), (0x6E, 'ROR', 'ab'), (0x7E, 'ROR', 'abx'),
        (0xCE, 'DEC', 'ab'), (0xDE, 'DEC', 'abx'), (0xEE, 'INC', 'ab'), (0xFE, 'INC', 'abx')):
        absolute[code] = operation, mode
    raw_candidates, considered = [], 0
    for bank in range(32):
        for offset in range(8190):
            file_offset = 16 + bank * 8192 + offset
            code = engine.rom[file_offset]
            if code not in absolute:
                continue
            considered += 1
            op, mode = absolute[code]
            operand = int.from_bytes(engine.rom[file_offset + 1:file_offset + 3], 'little')
            addresses = direct_addresses(dict(mode=mode, operand=operand))
            matched = sorted(addresses & base.AUX)
            if not matched:
                continue
            cpu_options = [0x8000 + offset, 0xA000 + offset, 0xC000 + offset] + ([0xE000 + offset] if bank == 31 else [])
            trusted = [dict(physical_bank=bank, cpu=pc) for pc in cpu_options if (bank, pc) in engine.known and engine.known[bank, pc]['raw_hex'] == engine.rom[file_offset:file_offset + 3].hex(' ').upper()]
            raw_candidates.append(dict(physical_bank=bank, bank_offset=offset, rom_offset=file_offset,
                possible_cpu_addresses=cpu_options, raw_hex=engine.rom[file_offset:file_offset + 3].hex(' ').upper(),
                hypothetical_op=op, hypothetical_mode=mode, operand=operand,
                raw_index_domain=[0] if mode == 'ab' else list(range(256)),
                possible_auxiliary_effective_addresses=matched,
                auxiliary_address_intersection_count=len(matched), matching_trusted_instructions=trusted,
                classification='untrusted_raw_opcode_window_not_reachability_or_instruction_proof'))
    return dict(schema='phase21-trusted-direct-indexed-city-auxiliary-inventory-v1', instruction_count=len(rows),
                classification_counts=dict(Counter(r['classification'] for r in rows)),
                possible_auxiliary_access_count=len(candidates), instructions=rows,
                limits='Only the48754 frozen verified instruction positions. Raw absolute indices0..255, RAM mirrors and16-bit wrap are not restricted to legal game IDs. Zero hits here is not a whole-ROM unused/reserved theorem.'), \
           dict(schema='phase21-untrusted-all-PRG-absolute-opcode-window-inventory-v1',
                PRG_bank_count=32, bytes_per_bank=8192, raw_three_byte_windows_examined=32 * 8190,
                documented_absolute_memory_opcode_count=len(absolute), matching_opcode_window_count=considered,
                possible_auxiliary_window_count=len(raw_candidates), windows=raw_candidates,
                limitations=['Every3-byte window wholly inside each PRG bank is considered, even inside data/inline tables.',
                             'A raw opcode match is not an executable instruction or reachable entry. Possible CPU mappings are hypothetical; no arbitrary bank configuration is asserted.',
                             'Cross-bank-boundary3-byte windows, undocumented opcodes and indirect operands are not covered by this raw absolute-opcode inventory.'])


def output_contracts(engine):
    previous = base.read('analysis/phase20/fields-static/all-indirect-accesses.json')['accesses']
    rows, selections = [], []
    for before in previous:
        key = before['physical_bank'], before['cpu']
        candidate = engine.contract(key)
        previous_contract = before['address_contract']
        candidate_disjoint = candidate is not None and not old.actual_auxiliary_intersection(candidate)
        previous_disjoint = before['classification'] == 'proved_disjoint_auxiliary_address_domain'
        if previous_disjoint:
            assert previous_contract is not None and not old.actual_auxiliary_intersection(previous_contract)
        authority = candidate if candidate_disjoint or not previous_disjoint and candidate is not None else previous_contract
        inherited = authority is previous_contract
        classification = 'proved_disjoint_auxiliary_address_domain' if authority is not None and not old.actual_auxiliary_intersection(authority) else \
            'possible_city_auxiliary_alias' if authority is not None else 'unresolved_pointer_or_index_contract'
        item = dict(before)
        item.update(classification=classification, address_contract=authority,
            whole_pointer_values=sorted(old.complete_words(authority)) if authority else None,
            Y_values=authority['Y_values'] if authority else before['Y_values'],
            phase20_classification=before['classification'], phase20_address_contract=previous_contract,
            newly_proved_disjoint=classification == 'proved_disjoint_auxiliary_address_domain' and not previous_disjoint,
            candidate_address_contract=candidate if inherited else None,
            candidate_whole_pointer_values=sorted(old.complete_words(candidate)) if inherited and candidate else None,
            candidate_Y_values=candidate['Y_values'] if inherited and candidate else None,
            candidate_contract_is_authoritative=False,
            proof_basis='phase21_bounded_recruitment_loop' if key in {(11, x) for x in (0xC726, 0xC73F, 0xC767, 0xC76D)} else
                        'frozen_phase20_authoritative_contract' if inherited else 'phase21_net_register_return_context' if authority else 'unresolved_context',
            authoritative_contract_origin=dict(path='analysis/phase20/fields-static/all-indirect-accesses.json',
                sha256=base.digest(ROOT / 'analysis/phase20/fields-static/all-indirect-accesses.json'),
                physical_bank=key[0], cpu=key[1], contract_field='address_contract') if inherited and authority else None,
            authoritative_pointer_representation='complete_joint_address_set' if authority and 'whole_pointer_values' in authority else
                'inherited_conservative_independent_low_high_Cartesian_domain' if authority else None)
        if authority:
            intersection = old.actual_auxiliary_intersection(authority)
            assert intersection == authority['possible_auxiliary_effective_addresses']
            assert len(intersection) == authority['auxiliary_address_intersection_count']
        if inherited:
            selections.append(dict(**engine.raw(key), authoritative_origin=item['authoritative_contract_origin'],
                authoritative_intersection_count=authority['auxiliary_address_intersection_count'] if authority else None,
                candidate_intersection_count=candidate['auxiliary_address_intersection_count'] if candidate else None,
                candidate_is_authoritative=False))
        rows.append(item)
    return rows, selections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == base.ROM_SHA256
    engine = Analysis(rom)
    print('normal-RTS leaf passthrough contracts', len(engine.passthrough), flush=True)
    roots, fallback = [], []
    for round_index in range(3):
        engine.prove_returns()
        engine.steps, engine.copies, engine.copy_details = 0, set(), {}
        engine.states, engine.queue, engine.scheduled = {}, deque(), set()
        roots, fallback = engine.run()
        added = engine.refine_write_effects() if round_index < 2 else None
        engine.refinement_rounds.append(dict(round=round_index + 1, instruction_transfers=engine.steps,
            return_contract_count=len(engine.return_contracts), new_non_ZP_store_proofs=added,
            write_effect_update_applied=round_index < 2 and bool(added)))
        if not added:
            break
    rows, selections = output_contracts(engine)
    selected = [r for r in rows if r['phase17_remaining_candidate']]
    new = [r for r in rows if not r['phase17_instruction_access']]
    remaining = [r for r in rows if r['classification'] != 'proved_disjoint_auxiliary_address_domain']
    old380 = [r for r in rows if r['phase20_classification'] != 'proved_disjoint_auxiliary_address_domain']
    direct, raw = direct_inventory(engine)
    for name, data in (('all-indirect-accesses.json', rows), ('access-contracts.json', selected),
                       ('new-indirect-accesses.json', new), ('remaining-accesses.json', remaining),
                       ('phase20-remaining380-handling.json', old380)):
        save(name, dict(schema='phase21-city-auxiliary-access-contracts-v1', ROM_sha256=base.ROM_SHA256,
            access_count=len(data), classification_counts=dict(Counter(r['classification'] for r in data)),
            newly_proved_disjoint_count=sum(r['newly_proved_disjoint'] for r in data), accesses=data,
            source_CPU_cases=0))
    roots_before = {(r['physical_bank'], r['cpu']): r for r in base.read('analysis/phase20/fields-static/city-field-root-inventory.json')['accesses']}
    roots_after = []
    for row in old380:
        key = row['physical_bank'], row['cpu']
        proof = row['address_contract']
        role = 'proved_237_officer_recruitment_record_access' if row['newly_proved_disjoint'] else roots_before[key]['category']
        if key in ((11, 0xC778), (11, 0xC77F), (11, 0xC664), (11, 0xC66C)):
            role = 'first_FF_city_roster_scan_or_append_without_explicit_upper_bound'
        roots_after.append(dict(**engine.raw(key), category=role, classification=row['classification'],
            address_contract=proof, original_producer_origins=proof['origins'] if proof else [],
            frozen_phase20_root=roots_before[key],
            official_name_confirmed=False))
    save('city-field-root-inventory.json', dict(schema='phase21-city-auxiliary-contextual-role-inventory-v1',
        ROM_sha256=base.ROM_SHA256, access_count=len(roots_after), categories=dict(Counter(r['category'] for r in roots_after)),
        accesses=roots_after, limits='The380 previous candidates are all retained and assigned an evidence-scoped role. Original nearby sentinel diagnostics do not by themselves prove a bound. Bulk/roster/composite uses do not establish an official field name.'))
    save('normal-return-register-contracts.json', dict(schema='phase21-universal-leaf-register-passthrough-v1',
        ROM_sha256=base.ROM_SHA256, contract_count=len(engine.passthrough_catalog), contracts=engine.passthrough_catalog))
    save('bounded-recruitment-contract.json', engine.recruitment_contract)
    save('direct-indexed-accesses.json', direct)
    save('untrusted-PRG-opcode-windows.json', raw)
    save('authoritative-contract-selection.json', dict(schema='phase21-explicit-authoritative-contract-selection-v1',
        row_count=len(selections), rows=selections, candidate_contracts_are_authoritative=False))
    save('superseding-erratum.json', dict(schema='phase21-superseding-phase20-RNG-return-contract-v1',
        supersedes_path='analysis/phase20/fields-static/city-field-root-inventory.json',
        supersedes_sha256=base.digest(ROOT / 'analysis/phase20/fields-static/city-field-root-inventory.json'),
        corrected_claim='FixedE89A temporarily loads X0054 but first saves inputX→0053 and finally restores X←0053. Ordinary uninterrupted RTS therefore preserves X. A register may-write set is not a net postcondition.',
        original_instructions=[engine.raw(k) for k in sorted(engine.known) if k[0] == 31 and 0xE89A <= k[1] <= 0xE8A9],
        recruitment_correction='C71A..C794 is free-officer recruitment, not HP maintenance. Its initializer-rooted ordinary loop is bounded to237 officer records; the later first-FF city roster scan remains unbounded.',
        interrupt_boundary='This static contract does not say a nested NMI cannot overwrite0053. Such an external write between save and restore is explicitly outside the ordinary no-interrupt contract and must be established separately from native/core or interrupt analysis.',
        frozen_phase20_files_modified=False))
    summary = dict(schema='phase21-city-auxiliary-semantics-summary-v1', status='analyzed', ROM_sha256=base.ROM_SHA256,
        analyzer_path='scripts/analyze_city_auxiliary_semantics.py', analyzer_sha256=base.digest(__file__),
        artifact_sha256={p: base.digest(ROOT / p) for p in dict.fromkeys(INPUTS)},
        original_instruction_count=len(engine.known), original_instruction_byte_comparisons=engine.raw_checked,
        source_CPU_cases=0, normal_return_register_contract_count=len(engine.passthrough),
        saved_then_restored_register_contract_count=sum(bool(set(row['preserved_input_registers']) & set(engine.effects[row['physical_bank'], row['cpu']]['register_may_write'])) for row in engine.passthrough_catalog),
        global_instruction_transfers=engine.steps, finite_refinement_rounds=engine.refinement_rounds,
        complete_analysis_fixed_point_proven=False, initial_unknown_root_count=len(roots), fallback_unknown_position_count=len(fallback),
        baseline_candidate_count=len(selected), all_indirect_access_count=len(rows), new_indirect_access_count=len(new),
        classification_counts=dict(Counter(r['classification'] for r in selected)),
        all_indirect_classification_counts=dict(Counter(r['classification'] for r in rows)),
        new_indirect_classification_counts=dict(Counter(r['classification'] for r in new)),
        phase20_remaining_count=len(old380), remaining_access_count=len(remaining),
        newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint'] for r in rows),
        newly_proved_disjoint_old589_count=sum(r['newly_proved_disjoint'] for r in selected),
        trusted_direct_indexed_instruction_count=direct['instruction_count'], trusted_direct_indexed_auxiliary_access_count=direct['possible_auxiliary_access_count'],
        untrusted_raw_PRG_auxiliary_opcode_window_count=raw['possible_auxiliary_window_count'],
        official_target_field_names=dict(city_plus1=None, city_plus28=None, city_plus29=None, city_plus30=None, city_plus31=None),
        limitations=['Normal-return register relations are separate from may-write effects and from interrupt interleaving.',
            'The new237-record proof is initializer-rooted/no-interrupt; mid-loop arbitrary entry and external scratch mutation are excluded.',
            'Every1526/589/45 row retains an applicable authoritative domain; diagnostic candidates never establish disjointness.',
            'Direct/indexed trusted-CFG zero hits and untrusted raw opcode windows do not prove whole-ROM unused/reserved/padding semantics.',
            'No new official name is inferred for city+1 or+28..31. Bulk initialization and unbounded roster spill remain real contextual accesses.'])
    save('analysis-summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('normal_return_register_contract_count', 'saved_then_restored_register_contract_count', 'all_indirect_classification_counts', 'remaining_access_count', 'newly_proved_disjoint_all_count', 'trusted_direct_indexed_auxiliary_access_count', 'untrusted_raw_PRG_auxiliary_opcode_window_count')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
