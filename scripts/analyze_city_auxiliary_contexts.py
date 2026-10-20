#!/usr/bin/env python3
"""Phase20 offline constant/table constructors and universal return-pair contracts.

All stage19 inputs stay frozen.  New facts are proofs about complete words,
never correlation of independently joined byte domains or same-PC tags.
"""
from collections import Counter, deque
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from dataclasses import dataclass
from functools import lru_cache

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase20/fields-static'
SPEC = importlib.util.spec_from_file_location('frozen_phase19_pair_model', ROOT / 'scripts/analyze_city_pointer_provenance.py')
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)
ORIGINAL_STATE, ORIGINAL_JOIN = base.State, base.join
NUMERIC_LIMIT = 32


def finite(values):
    return values if values is None or len(values) <= NUMERIC_LIMIT else None


@dataclass
class ContextState(ORIGINAL_STATE):
    numbers: tuple = (None, None, None)
    number_stack: tuple = ()

    def copy(self):
        return ContextState(dict(self.pairs), self.registers, dict(self.pending), self.stack, self.builders,
                            self.numbers, self.number_stack)


def join(left, right):
    state = ORIGINAL_JOIN(left, right)
    state.numbers = tuple(None if a is None or b is None else finite(a | b) for a, b in zip(left.numbers, right.numbers))
    state.number_stack = tuple(None if a is None or b is None else finite(a | b) for a, b in zip(left.number_stack, right.number_stack)) \
        if len(left.number_stack) == len(right.number_stack) else ()
    return state


base.State, base.join = ContextState, join
INPUTS = base.INPUTS + [
    'scripts/analyze_city_pointer_provenance.py',
    'analysis/phase19/fields-static/all-indirect-accesses.json',
    'analysis/phase19/fields-static/analysis-summary.json',
    'analysis/phase19/fields-static/verification.json',
]


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def complete_words(contract):
    """Expand the *declared* domain, preserving its actual representation."""
    if 'whole_pointer_values' in contract:
        return frozenset(contract['whole_pointer_values'])
    return frozenset(low | (high << 8) for low in contract['low_byte_values'] for high in contract['high_byte_values'])


def actual_auxiliary_intersection(contract):
    words = complete_words(contract)
    return sorted(address for address in base.AUX
                  if any(((address - index) & 65535) in words for index in contract['Y_values']))


@lru_cache(maxsize=None)
def frozen_sha(path):
    return base.digest(ROOT / path)


def inherited_disjoint_authority(previous, phase18):
    """Resolve an actual zero-intersection object; a classification is not proof.

    Some frozen19 rows intentionally used a narrower18 independent proof while
    retaining a broader/unknown current pair diagnostic. Do not relabel that
    diagnostic as the inherited authoritative disjoint contract.
    """
    key = previous['physical_bank'], previous['cpu']
    current = previous['address_contract']
    candidates = []
    if current is not None:
        candidates.append((current, 'analysis/phase19/fields-static/all-indirect-accesses.json', 'address_contract'))
    older = previous.get('phase18_address_contract')
    if older is not None:
        assert older == phase18[key]['address_contract'], key
        candidates.append((older, 'analysis/phase18/fields-static/all-indirect-accesses.json', 'address_contract'))
    for contract, path, field_name in candidates:
        matched = actual_auxiliary_intersection(contract)
        assert matched == contract['possible_auxiliary_effective_addresses'], (key, path)
        assert len(matched) == contract['auxiliary_address_intersection_count'], (key, path)
        if not matched:
            return contract, dict(path=path, sha256=frozen_sha(path),
                                  physical_bank=key[0], cpu=key[1], contract_field=field_name,
                                  scope='Exact frozen original pointer/index domain and its original bounded-CFG preconditions; not merely an inherited classification label.')
    return None, None


class Analysis(base.Analysis):
    def __init__(self, rom):
        super().__init__(rom)
        self.templates = {}
        self.template_catalog = []
        self.return_contracts = {}
        self.return_catalog = {}
        self.return_evaluations = 0
        self.return_local_transfers = 0
        self.return_structures = {}
        self.proof_footprints = {}
        self.refinement_rounds = []
        self.collecting_returns = False
        self.predecessors = {}
        for source, targets in self.edges.items():
            for target in targets:
                self.predecessors.setdefault(target, set()).add(source)
        self.install_templates()
        self.install_structured_copy_loops()

    def install_structured_copy_loops(self):
        self.structured_loops, self.structured_sites = [], {}
        specs = [
            dict(name='scenario_SRAM_clear', start=0xDD8F, end=0xDDA7, stop=0xDDA9, count=4096,
                 sites={0xDD9A: (0, range(0x6000, 0x7000, 256), range(256))},
                 meaning='Bulk clear of6000..6FFF; includes all thirty city records but assigns no dedicated field meaning.'),
            dict(name='whole_city_template_copy', start=0xDDCD, end=0xDE10, stop=0xDE12, count=960,
                 sites={0xDDED: (0, range(0x8C00, 0x8FC0), (0,)), 0xDDEF: (2, range(0x6000, 0x63C0), (0,))},
                 meaning='960-byte city template copy: physicalbank16 ROM8C00..8FBF→6000..63BF, covering all30×32 bytes including+1 and+28..31.'),
            dict(name='whole_officer_template_copy', start=0xDE12, end=0xDE55, stop=0xDE57, count=2880,
                 sites={0xDE32: (0, range(0x8000, 0x8B40), (0,)), 0xDE34: (2, range(0x63C0, 0x6F00), (0,))},
                 meaning='2880-byte officer/adjacent template copy: physicalbank17 ROM8000..8B3F→63C0..6EFF; disjoint from the city area.'),
        ]
        for spec in specs:
            nodes = {key for key in self.known if key[0] == 30 and spec['start'] <= key[1] <= spec['end']}
            incoming = [(source, target) for target in nodes for source in self.predecessors.get(target, ()) if source not in nodes]
            assert all(target == (30, spec['start']) for source, target in incoming), (spec, incoming)
            assert not any(entry in nodes and entry != (30, spec['start']) for entry in self.effects), spec
            original_rows = [self.raw(key) for key in sorted(nodes)]
            for key in nodes:
                row = self.known[key]
                assert row['op'] != 'JSR' or row['operand'] == 0xF25F
            contract = dict(schema='phase20-bounded-original-template-loop-v1', name=spec['name'], physical_bank=30,
                entry_cpu=spec['start'], stop_cpu=spec['stop'], exact_iterations=spec['count'], meaning=spec['meaning'],
                all_external_CFG_edges_enter_initializer=True,
                incoming_original_edges=[dict(source=self.raw(source), target_cpu=target[1]) for source, target in incoming],
                original_instructions=original_rows,
                limits='Original constant-initialized loop and declared trusted CFG only; no arbitrary mid-loop external entry or interrupt corruption is claimed.')
            self.structured_loops.append(contract)
            for pc, (pointer, addresses, indices) in spec['sites'].items():
                key = 30, pc
                self.structured_sites[key] = dict(pointer=pointer, addresses=frozenset(addresses), indices=frozenset(indices),
                                                  name=spec['name'], entry=(30, spec['start']))

    def next_key(self, key):
        return base.mapped(key, key[1] + self.known[key]['size'])

    def straight(self, key, length):
        result = []
        for _ in range(length):
            if key not in self.known:
                return []
            result.append(key)
            key = self.next_key(key)
        return result

    @staticmethod
    def destination(row):
        if row['op'] != 'STA' or row['mode'] not in ('zp', 'ab'):
            return None
        address = base.normalized_ram(row['operand'])
        return address if address is not None and address < 256 else None

    def rom_value(self, key, address, data_bank=None):
        address &= 65535
        if 0x8000 <= address < 0xA000 and data_bank is not None:
            return self.rom[base.original(data_bank, address)]
        target = base.mapped(key, address)
        if target is None:
            return None
        return self.rom[base.original(*target)]

    def mapper_prefix(self, key):
        """Find an exact earlier LDY# / F25F or F266 contiguous prefix.

        The builder traverses the *entire* prefix at runtime of this abstract
        analysis; an alternate entry after the setter lacks that capability.
        No indirect store/call/control transfer or possible E000-window write
        may intervene. There is no assumed saved DE/E1 initial bank.
        """
        candidates = []
        for start in self.known:
            if start[0] != key[0] or not key[1] - 64 <= start[1] < key[1]:
                continue
            row = self.known[start]
            if row['op'] != 'LDY' or row['mode'] != 'im':
                continue
            call = self.next_key(start)
            if call not in self.known or self.known[call]['op'] != 'JSR' or self.known[call]['operand'] not in (0xF25F, 0xF266):
                continue
            cursor, keys, valid = self.next_key(call), [start, call], True
            while cursor != key:
                if cursor not in self.known or cursor[1] >= key[1] or len(keys) > 24:
                    valid = False
                    break
                here = self.known[cursor]
                if here['op'] in ('JSR', 'JMP', 'RTS', 'RTI', 'BRK') or here['mode'] == 'rel':
                    valid = False
                    break
                if here['op'] in base.WRITES and here['mode'] != 'a':
                    if here['mode'] in ('iy', 'ix'):
                        valid = False
                        break
                    indices = range(256) if here['mode'] in ('abx', 'aby', 'zpx', 'zpy') else (0,)
                    mask = 255 if here['mode'] in ('zpx', 'zpy') else 65535
                    if any(0xE000 <= (here['operand'] + index) & mask for index in indices):
                        valid = False
                        break
                keys.append(cursor)
                cursor = self.next_key(cursor)
            if valid:
                candidates.append((start, keys, row['operand'] & 31))
        return max(candidates, key=lambda value: value[0][1]) if candidates else None

    def install_templates(self):
        """Exact contiguous prefixes, with entry/merge builder protection.

        Same indexed register is not a same-PC identity: the prefix has no
        control/call/register modification between the actual two loads.
        A branch entering mid-prefix lacks its builder and destroys the fact.
        """
        for key in sorted(self.known):
            for length in (4, 5):
                keys = self.straight(key, length)
                if not keys:
                    continue
                rows = [self.known[k] for k in keys]
                first, store1 = rows[:2]
                if first['op'] != 'LDA':
                    continue
                destination = self.destination(store1)
                if destination is None:
                    continue
                increment = length == 5
                if increment:
                    step, second, store2 = rows[2:]
                    if step['op'] not in ('INX', 'INY'):
                        continue
                else:
                    second, store2 = rows[2:]
                other = self.destination(store2)
                if other not in ((destination + 1) & 255, (destination - 1) & 255):
                    continue
                if second['op'] != 'LDA':
                    continue
                if first['mode'] == second['mode'] == 'im' and not increment:
                    loaded = [(first['operand'], second['operand'])]
                    kind = 'literal_word'
                elif first['mode'] == second['mode'] and first['mode'] in ('abx', 'aby'):
                    if increment and step['op'] != ('INX' if first['mode'] == 'abx' else 'INY'):
                        continue
                    mapper = self.mapper_prefix(key) if any(0x8000 <= row['operand'] < 0xA000 for row in (first, second)) else None
                    data_bank = mapper[2] if mapper else None
                    loaded = []
                    for index in range(256):
                        low = self.rom_value(key, first['operand'] + index, data_bank)
                        high = self.rom_value(key, second['operand'] + ((index + int(increment)) & 255), data_bank)
                        if low is None or high is None:
                            break
                        loaded.append((low, high))
                    if len(loaded) != 256:
                        continue  # no implicit $8000 mapping assumption
                    kind = 'immutable_ROM_indexed_word'
                else:
                    continue
                marker = keys[-1]
                if marker in self.markers:
                    continue  # existing stronger raw-A constructor retained
                lo_first = other == (destination + 1) & 255
                pair_base = destination if lo_first else other
                addresses = frozenset(lo | (hi << 8) if lo_first else hi | (lo << 8) for lo, hi in loaded)
                load_start = key
                if kind == 'immutable_ROM_indexed_word' and mapper:
                    keys = mapper[1] + keys
                constructor_entry = keys[0]
                identifier = max(self.factory_ids, default=-1) + 1
                descriptor = dict(id=identifier, entry=constructor_entry, marker=marker, end=marker[1], base=pair_base,
                                  kind=kind, addresses=addresses, prologue=frozenset(keys), marker_half=1 if lo_first else 0)
                self.templates.setdefault(constructor_entry, []).append(descriptor)
                self.factory_ids[identifier] = descriptor
                self.markers[marker] = descriptor
                self.template_catalog.append(dict(
                    **self.raw(constructor_entry), loads_start=self.raw(load_start), complete_after=self.raw(marker), kind=kind, pointer_base=pair_base,
                    whole_pointer_values=sorted(addresses), index_domain=list(range(256)) if 'ROM' in kind else None,
                    explicit_data_window_bank=data_bank if kind == 'immutable_ROM_indexed_word' else None,
                    instructions=[self.raw(k) for k in keys],
                    limits='Exact contiguous original prefix, no calls/branches or unlisted index modifications. Raw index0..255 and 8-bit INX/INY wrap retained. Entry/merge must-builder required.'))

    def transfer(self, key, state):
        value = state.copy()
        if key in self.templates:
            value.builders |= frozenset(d['id'] for d in self.templates[key])
        marker = self.markers.get(key)
        active = marker and 'marker_half' in marker and marker['id'] in value.builders
        result = super().transfer(key, value)
        if active:
            result.registers = (frozenset(((marker['base'], marker['marker_half']),)),) + result.registers[1:]
        row = self.known[key]
        op, mode, operand = row['op'], row['mode'], row['operand']
        numbers, stack = list(state.numbers), state.number_stack
        def mapped_values(values, action):
            return None if values is None else frozenset(action(v) & 255 for v in values)
        if op in ('LDA', 'LDX', 'LDY'):
            number = frozenset((operand,)) if mode == 'im' else None
            address = base.normalized_ram(operand) if mode in ('zp', 'ab') else None
            if address is not None and address < 256:
                for pointer, fact in state.pairs.items():
                    if address == pointer:
                        number = frozenset(value & 255 for value in fact.addresses)
                        break
                    if address == (pointer + 1) & 255:
                        number = frozenset(value >> 8 for value in fact.addresses)
                        break
            if mode in ('ab', 'abx', 'aby') and operand >= 0xA000:
                index = numbers[1 if mode == 'abx' else 2] if mode != 'ab' else frozenset((0,))
                index = range(256) if index is None else index
                values = [self.rom_value(key, operand + n) for n in index]
                number = frozenset(values) if None not in values else None
            numbers[('LDA', 'LDX', 'LDY').index(op)] = number
        elif op in ('TAX', 'TAY', 'TXA', 'TYA'):
            source, destination = {'TAX': (0, 1), 'TAY': (0, 2), 'TXA': (1, 0), 'TYA': (2, 0)}[op]
            numbers[destination] = numbers[source]
        elif op in ('INX', 'DEX', 'INY', 'DEY'):
            index = 1 if op[-1] == 'X' else 2
            numbers[index] = mapped_values(numbers[index], lambda n: n + (1 if op.startswith('IN') else -1))
        elif op == 'TSX':
            numbers[1] = None
        elif op in ('AND', 'ORA', 'EOR'):
            source = range(256) if numbers[0] is None else numbers[0]
            numbers[0] = frozenset(n & operand if op == 'AND' else n | operand if op == 'ORA' else n ^ operand for n in source) if mode == 'im' else None
        elif op in ('ADC', 'SBC'):
            numbers[0] = frozenset((n + operand + carry if op == 'ADC' else n - operand - (1 - carry)) & 255
                                   for n in numbers[0] for carry in (0, 1)) if mode == 'im' and numbers[0] is not None else None
        elif op in ('ASL', 'LSR', 'ROL', 'ROR') and mode == 'a':
            source = numbers[0]
            numbers[0] = None if source is None else frozenset(
                ((n << 1) | carry) & 255 if op == 'ROL' else ((n >> 1) | (carry << 7)) if op == 'ROR' else
                ((n << 1) & 255) if op == 'ASL' else n >> 1 for n in source for carry in ((0, 1) if op in ('ROL', 'ROR') else (0,)))
        elif op in ('PHA', 'PHP'):
            stack = (stack + (numbers[0] if op == 'PHA' else None,))[-16:]
        elif op in ('PLA', 'PLP'):
            if op == 'PLA':
                numbers[0] = stack[-1] if stack else None
            stack = stack[:-1]
        elif op == 'TXS':
            stack = ()
        result.numbers = tuple(finite(number) for number in numbers)
        result.number_stack = stack if len(result.stack) == len(stack) else ()
        return result

    def index_values_at_access(self, key, state):
        old = self.access_index[key]['Y_values']
        old = frozenset(range(256) if old is None else old)
        return old if state.numbers[2] is None else old & state.numbers[2]

    def indirect_addresses(self, key, state):
        row = self.known[key]
        if key in self.structured_sites:
            site = self.structured_sites[key]
            return frozenset((pointer + index) & 65535 for pointer in site['addresses'] for index in site['indices'])
        if row['mode'] != 'iy' or row['operand'] not in state.pairs:
            return None
        indices = self.index_values_at_access(key, state)
        return frozenset((pointer + index) & 65535 for pointer in state.pairs[row['operand']].addresses for index in indices)

    def contract(self, key):
        if key in self.structured_sites:
            site = self.structured_sites[key]
            addresses = self.indirect_addresses(key, self.states.get(key))
            matched = sorted(addresses & base.AUX)
            return dict(whole_pointer_values=sorted(site['addresses']), whole_pointer_count=len(site['addresses']),
                low_high_relationship='Exact original constant-initialized bounded byte-loop address contract.',
                Y_values=sorted(site['indices']), Y_was_unknown=False,
                possible_auxiliary_effective_addresses=matched, auxiliary_address_intersection_count=len(matched),
                origins=[dict(**self.raw(site['entry']), origin_kind=site['name'])],
                may_write_zero_page=False, may_write_stack_RAM_mirror=False,
                structured_loop_contract=site['name'])
        proof = super().contract(key)
        if proof is not None:
            proof['Y_values'] = sorted(self.index_values_at_access(key, self.states[key]))
            proof['Y_was_unknown'] = self.access_index[key]['Y_values'] is None and self.states[key].numbers[2] is None
            proof['Y_contract_source'] = 'Intersection of frozen original index domain and current literal/transfer/universal-return scalar contract.'
        return proof

    def leaf_contract(self, entry, state):
        # The leaf evaluator receives CALLER-entry state, not each store's
        # actual local Y. Retain frozen all-path indices for this proof.
        masked = state.copy()
        masked.numbers = (None, None, None)
        return super().leaf_contract(entry, masked)

    def function_structure(self, entry):
        if entry in self.return_structures:
            return self.return_structures[entry]
        queue, seen, exits, barriers, calls = [entry], set(), [], [], set()
        while queue:
            key = queue.pop()
            if key in seen:
                continue
            seen.add(key)
            if key not in self.known:
                barriers.append(['missing_original_instruction', key])
                continue
            row = self.known[key]
            if row['op'] == 'RTS':
                exits.append(key)
                continue
            if row['op'] in ('RTI', 'BRK', '?'):
                barriers.append(['non_RTS_exit', key])
                continue
            targets = self.edges.get(key, [])
            if row['op'] == 'JSR' and key not in self.dispatch:
                following = base.mapped(key, row['cpu'] + row['size'] + (2 if row['operand'] == 0xEE07 else 0))
                calls.update(target for target in targets if target != following)
                targets = [target for target in targets if target == following]
            if not targets:
                barriers.append(['unresolved_control_exit', key])
            queue.extend(targets)
        result = dict(nodes=seen, exits=sorted(exits), barriers=barriers, calls=calls)
        self.return_structures[entry] = result
        return result

    def dispatch_successors(self, key, state):
        row = self.known[key]
        scratch = 0 if row['operand'] == 0xEADE else 0x20
        results = []
        for target in self.dispatch[key]['mapped_targets']:
            value = state.copy()
            base.kill(value, range(scratch, scratch + 5))
            value.pairs[scratch + 1] = base.Pair(frozenset((row['cpu'] + 2,)), self.add_origin(key, 'dispatcher_ROM_table'))
            value.pairs[scratch + 3] = base.Pair(frozenset((target[1],)), self.add_origin(key, 'dispatcher_CPU_target'))
            value.registers = (frozenset(((scratch + 3, 1),)), value.registers[1], value.registers[2])
            value.numbers = (frozenset((target[1] >> 8,)), state.numbers[1], state.numbers[2])
            value.builders = frozenset()
            results.append((target, value))
        return results

    def branch_successors(self, key, state):
        row = self.known[key]
        targets = self.edges.get(key, ())
        following = base.mapped(key, row['cpu'] + 2)
        relative = row['operand'] if row['operand'] < 128 else row['operand'] - 256
        taken_target = base.mapped(key, (row['cpu'] + 2 + relative) & 65535)
        # Zero-displacement taken/fallthrough are the SAME edge. No truth
        # restriction is valid at the common target (stage18 counterexample).
        predecessors = self.predecessors.get(key, set())
        if taken_target == following or len(predecessors) != 1:
            return [(target, state) for target in targets]
        previous = self.known[next(iter(predecessors))]
        if previous['op'] not in ('CMP', 'CPX', 'CPY') or previous['mode'] != 'im' or previous['cpu'] + previous['size'] != row['cpu']:
            return [(target, state) for target in targets]
        register = ('CMP', 'CPX', 'CPY').index(previous['op'])
        limit = previous['operand']
        domain = state.numbers[register]
        domain = range(256) if domain is None else domain
        def predicate(value):
            return {'BCC': value < limit, 'BCS': value >= limit,
                    'BEQ': value == limit, 'BNE': value != limit,
                    'BMI': bool((value - limit) & 128),
                    'BPL': not bool((value - limit) & 128)}.get(row['op'])
        if row['op'] not in ('BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL'):
            return [(target, state) for target in targets]
        result = []
        for target in targets:
            numbers = frozenset(value for value in domain if predicate(value) == (target == taken_target))
            if not numbers:
                continue
            value = state.copy()
            registers = list(value.numbers)
            registers[register] = finite(numbers)
            value.numbers = tuple(registers)
            result.append((target, value))
        return result

    def run_queue(self):
        # Same scoped control protocol as stage19, with explicit numeric
        # effects at dispatcher/far-callee entry (A is NOT the old selector).
        while self.queue:
            key = self.queue.popleft()
            self.scheduled.discard(key)
            state = self.transfer(key, self.states[key])
            row = self.known[key]
            if row['op'] != 'JSR':
                successors = self.branch_successors(key, state) if row['mode'] == 'rel' else [(target, state) for target in self.edges.get(key, ())]
                for target, value in successors:
                    self.emit(target, value)
            elif key in self.dispatch:
                for target, value in self.dispatch_successors(key, state):
                    self.emit(target, value)
            else:
                following, result = self.call_result(key, state)
                targets = [target for target in self.edges.get(key, ()) if target != following]
                for target in targets:
                    callee = state.copy()
                    if row['operand'] == 0xEE07:
                        base.kill(callee, set(range(0x58, 0x5E)) | {0xE2, 0xE3})
                        callee.pairs[0x5B] = base.Pair(frozenset((target[1],)), self.add_origin(key, 'farcall_CPU_target'))
                        callee.registers = (frozenset(), callee.registers[1], callee.registers[2])
                        callee.numbers = (frozenset((0x4C,)), callee.numbers[1], callee.numbers[2])
                    callee.stack, callee.number_stack, callee.builders = (), (), frozenset()
                    self.emit(target, callee)
                self.emit(following, result)
            self.steps += 1
            if self.steps % 50000 == 0:
                print(f'context worklist: {self.steps} transfers, {len(self.states)} positions, {len(self.queue)} queued', flush=True)

    def call_result(self, key, state):
        row = self.known[key]
        following = base.mapped(key, row['cpu'] + row['size'] + (2 if row['operand'] == 0xEE07 else 0))
        if row['operand'] == 0xEE07:
            targets = [target for target in self.edges.get(key, ()) if target != following]
            result = None
            for target in targets:
                value = self.apply_call(state, target, key, far=True)
                result = value if result is None else base.join(result, value)
            return following, result if result is not None else self.apply_call(state, None, key, far=True)
        return following, self.apply_call(state, base.mapped(key, row['operand']), key)

    def apply_call(self, state, target, key, far=False):
        result = super().apply_call(state, target, key, far)
        descriptor = self.factories.get(target)
        effect = self.effects.get(target)
        changed = descriptor['regs'] if descriptor else effect['register_may_write'] if effect else ('A', 'X', 'Y')
        numbers = [None if name in changed else number for name, number in zip(('A', 'X', 'Y'), state.numbers)]
        if target in ((31, 0xF25F), (31, 0xF266)):
            numbers = list(state.numbers)
        if descriptor:
            if target in ((31, 0xF368), (8, 0xB4C2), (11, 0xD319)):
                numbers[2] = frozenset(range(0, 32, 2))
            elif target == (11, 0xD304):
                numbers[2] = frozenset(range(17, 28))
            elif target not in ((11, 0xD283), (11, 0xD2AB), (31, 0xF308)):
                numbers[2] = frozenset((0,))
            if descriptor['returns_high']:
                numbers[0] = frozenset(pointer >> 8 for pointer in descriptor['addresses'])
            if target in ((11, 0xD283), (11, 0xD2AB)):
                numbers[1] = frozenset((0,))
        proof = self.return_contracts.get(target)
        if proof is not None and not descriptor:
            written = {byte for pointer in proof.pairs for byte in (pointer, (pointer + 1) & 255)}
            base.kill(result, written)
            for pointer, fact in proof.pairs.items():
                result.pairs[pointer] = base.Pair(fact.addresses,
                    fact.origins | self.add_origin(key, 'callee_whole_pair_return'))
            if not far:
                result.registers = tuple(base.valid_refs(refs, result.pairs) for refs in proof.registers)
            else:
                # EE07's mapper restoration changes A/Y after the callee RTS.
                result.registers = (frozenset(), result.registers[1], frozenset())
            numbers = [proven if proven is not None else old for old, proven in zip(numbers, proof.numbers)]
        if far:
            numbers[0], numbers[2] = None, None
        result.numbers = tuple(finite(number) for number in numbers)
        result.number_stack = state.number_stack if len(result.stack) == len(state.number_stack) else ()
        return result

    def evaluate_return(self, entry):
        structure = self.function_structure(entry)
        if structure['barriers'] or not structure['exits']:
            return None
        states, queue = {entry: base.State()}, deque((entry,))
        scheduled = {entry}
        while queue:
            key = queue.popleft()
            scheduled.discard(key)
            row = self.known[key]
            state = self.transfer(key, states[key])
            if row['op'] == 'RTS':
                continue
            if row['op'] == 'JSR':
                successors = self.dispatch_successors(key, state) if key in self.dispatch else [self.call_result(key, state)]
            else:
                successors = self.branch_successors(key, state) if row['mode'] == 'rel' else [(target, state) for target in self.edges.get(key, ())]
            for target, value in successors:
                if target not in structure['nodes']:
                    continue
                old = states.get(target)
                new = value if old is None else base.join(old, value)
                if old != new:
                    states[target] = new
                    if target not in scheduled:
                        queue.append(target)
                        scheduled.add(target)
            self.return_local_transfers += 1
        # Include every declared reachable local RTS exit; missing state is
        # not silently dropped as though an unanalysed path were impossible.
        if any(key not in states for key in structure['exits']):
            return None
        result = states[structure['exits'][0]]
        for key in structure['exits'][1:]:
            result = base.join(result, states[key])
        self.return_evaluations += 1
        return result

    def prove_returns(self):
        # Universal unknown entry state, not just the currently observed
        # callers. Facts can only be introduced by independently proved
        # constructors or already proved return contracts. No recursive seed.
        entries = set(self.effects)
        dependents = {}
        for entry in entries:
            for callee in self.function_structure(entry)['calls']:
                dependents.setdefault(callee, set()).add(entry)
        queue, scheduled = deque(sorted(entries)), set(entries)
        while queue:
            entry = queue.popleft()
            scheduled.discard(entry)
            result = self.evaluate_return(entry)
            if result is None or (not result.pairs and all(number is None for number in result.numbers)):
                continue
            previous = self.return_contracts.get(entry)
            if previous is None:
                proof = result
            else:
                # Earlier invariants are already sound universal contracts;
                # retain them even when a later independent proof is weaker.
                proof = previous.copy()
                for pointer, fact in result.pairs.items():
                    if pointer not in proof.pairs:
                        proof.pairs[pointer] = fact
                proof.numbers = tuple(new if old is None else old for old, new in zip(previous.numbers, result.numbers))
            if previous is not None and previous.pairs == proof.pairs and previous.numbers == proof.numbers:
                continue
            self.return_contracts[entry] = proof
            structure = self.function_structure(entry)
            self.return_catalog[entry] = dict(**self.raw(entry),
                input_contract='Unknown input data registers/ZP/pointers, conditioned on the frozen bounded-dispatch and normal-RTS CFG domains; no corrupted-selector or external-jump coverage claim. Only independently established complete output pairs are claimed.',
                whole_return_pairs={str(pointer): sorted(fact.addresses) for pointer, fact in proof.pairs.items()},
                return_numeric_registers={name: sorted(number) if number is not None else None for name, number in zip(('A', 'X', 'Y'), proof.numbers)},
                RTS_exits=[self.raw(k) for k in structure['exits']],
                original_local_positions=len(structure['nodes']), local_control_barriers=[],
                limits='Conditional on normal original local RTS paths in the trusted bounded CFG, not a termination/universal control-flow theorem. No recursive or same-PC identity seed.')
            for caller in sorted(dependents.get(entry, ())):
                if caller not in scheduled:
                    queue.append(caller)
                    scheduled.add(caller)

    def refine_write_effects(self):
        """Use only stabilized all-path complete-pair non-ZP store proofs.

        The may-write closure is a union, so a missing/computed dependency
        remains a full barrier. This never infers a return or termination.
        """
        added = 0
        for key, row in self.access_index.items():
            if row['op'] != 'STA' or key not in self.states:
                continue
            proof = self.contract(key)
            if proof is not None and not proof['may_write_zero_page'] and key not in self.old_safe:
                self.old_safe[key] = proof
                self.proof_footprints[key] = dict(**self.raw(key), address_contract=proof)
                added += 1
        if not added:
            return 0
        local = {}
        for entry in self.effects:
            structure = self.function_structure(entry)
            writes, regs, dependencies = set(), set(), set()
            barriers = list(structure['barriers'])
            if barriers:
                writes.update(base.ZP)
                regs.update(('A', 'X', 'Y'))
            for key in structure['nodes']:
                if key not in self.known:
                    continue
                row = self.known[key]
                op, mode, operand = row['op'], row['mode'], row['operand']
                if op in ('LDA', 'PLA', 'TXA', 'TYA', 'ADC', 'SBC', 'AND', 'ORA', 'EOR') or (op in ('ASL', 'LSR', 'ROL', 'ROR') and mode == 'a'):
                    regs.add('A')
                if op in ('LDX', 'TAX', 'TSX', 'INX', 'DEX'):
                    regs.add('X')
                if op in ('LDY', 'TAY', 'INY', 'DEY'):
                    regs.add('Y')
                if op in base.WRITES and mode != 'a':
                    if mode in ('ix', 'iy'):
                        if key not in self.old_safe:
                            writes.update(base.ZP)
                            barriers.append(['unproved_indirect_store', list(key)])
                    else:
                        here, _ = self.direct_targets(key)
                        writes.update(here)
                if op != 'JSR':
                    continue
                if key in self.dispatch:
                    scratch = 0 if operand == 0xEADE else 0x20
                    writes.update(range(scratch, scratch + 5))
                    regs.update(('A', 'Y'))
                elif operand == 0xEE07:
                    following = base.mapped(key, row['cpu'] + 5)
                    targets = [target for target in self.edges.get(key, ()) if target != following]
                    writes.update(range(0x58, 0x5E))
                    writes.update((0xE2, 0xE3))
                    regs.update(('A', 'Y'))
                    if targets:
                        dependencies.update(targets)
                    else:
                        writes.update(base.ZP)
                        regs.update(('A', 'X', 'Y'))
                        barriers.append(['unknown_far_callee', list(key)])
                else:
                    target = base.mapped(key, operand)
                    if target not in self.effects:
                        writes.update(base.ZP)
                        regs.update(('A', 'X', 'Y'))
                        barriers.append(['unknown_direct_callee', list(key)])
                    else:
                        dependencies.add(target)
            local[entry] = (writes, regs, dependencies, barriers)
        memo = {entry: (set(value[0]), set(value[1])) for entry, value in local.items()}
        changed = True
        while changed:
            changed = False
            for entry, (writes, regs, dependencies, _) in local.items():
                ww, rr = set(writes), set(regs)
                for target in dependencies:
                    w, r = memo.get(target, (base.ZP, {'A', 'X', 'Y'}))
                    ww.update(w)
                    rr.update(r)
                if (ww, rr) != memo[entry]:
                    memo[entry] = ww, rr
                    changed = True
        self.effects = {entry: dict(physical_bank=entry[0], cpu=entry[1],
            zero_page_may_write=sorted(writes), register_may_write=sorted(regs),
            instruction_count=len(self.function_structure(entry)['nodes']),
            barriers=local[entry][3]) for entry, (writes, regs) in memo.items()}
        return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == base.ROM_SHA256
    analysis = Analysis(rom)
    print('new exact constructor templates', len(analysis.template_catalog), flush=True)
    for round_index in range(3):
        analysis.prove_returns()
        print('universal return-pair contracts', len(analysis.return_contracts), flush=True)
        analysis.steps, analysis.copies, analysis.copy_details = 0, set(), {}
        analysis.states, analysis.queue, analysis.scheduled = {}, deque(), set()
        roots, fallback = analysis.run()
        added = analysis.refine_write_effects() if round_index < 2 else None
        analysis.refinement_rounds.append(dict(round=round_index + 1, new_complete_pair_non_ZP_store_proofs=added,
                                              total_additional_non_ZP_store_proofs=len(analysis.proof_footprints),
                                              return_contract_count=len(analysis.return_contracts),
                                              return_pair_contract_count=sum(bool(proof.pairs) for proof in analysis.return_contracts.values()),
                                              instruction_transfers=analysis.steps,
                                              write_effect_update_applied=round_index < 2 and bool(added)))
        if not added:
            break
    prior = base.read('analysis/phase19/fields-static/all-indirect-accesses.json')['accesses']
    phase18 = {(row['physical_bank'], row['cpu']): row for row in base.read('analysis/phase18/fields-static/all-indirect-accesses.json')['accesses']}
    rows = []
    authoritative_repairs = []
    for previous in prior:
        key = previous['physical_bank'], previous['cpu']
        contract = analysis.contract(key)
        old_disjoint = previous['classification'] == 'proved_disjoint_auxiliary_address_domain'
        old_authority, old_origin = inherited_disjoint_authority(previous, phase18) if old_disjoint else (None, None)
        old_disjoint = old_disjoint and old_authority is not None
        new_disjoint = contract is not None and not contract['auxiliary_address_intersection_count']
        disjoint = old_disjoint or new_disjoint
        classification = 'proved_disjoint_auxiliary_address_domain' if disjoint else \
            'possible_city_auxiliary_alias' if contract is not None else 'unresolved_pointer_or_index_contract'
        authority = contract if new_disjoint or not old_disjoint else old_authority
        authority_origin = old_origin if old_disjoint and not new_disjoint else None
        row = dict(previous)
        row.update(classification=classification, address_contract=authority,
                   whole_pointer_values=sorted(complete_words(authority)) if authority else None,
                   Y_values=authority['Y_values'] if authority else previous['Y_values'],
                   authoritative_contract_origin=authority_origin,
                   authoritative_pointer_representation='complete_joint_address_set' if authority and 'whole_pointer_values' in authority else
                       'inherited_conservative_independent_low_high_Cartesian_domain' if authority else None,
                   phase19_classification=previous['classification'],
                   phase19_proof_basis=previous['proof_basis'],
                   phase19_disjoint_proof=old_authority if old_disjoint else None,
                   proof_basis='new_whole_pointer_relation' if new_disjoint else 'frozen_phase19_disjoint_contract' if old_disjoint else 'whole_pointer_relation' if contract else 'unknown_relation',
                   newly_proved_disjoint=disjoint and not old_disjoint)
        if old_disjoint and not new_disjoint:
            row.update(candidate_address_contract=contract,
                       candidate_whole_pointer_values=contract['whole_pointer_values'] if contract else None,
                       candidate_Y_values=contract['Y_values'] if contract else None,
                       candidate_contract_is_authoritative=False)
            authoritative_repairs.append(dict(**analysis.raw(key),
                candidate_auxiliary_intersection_count=contract['auxiliary_address_intersection_count'] if contract else None,
                authoritative_auxiliary_intersection_count=0, authoritative_contract_origin=authority_origin,
                reason='The newer whole-pair analysis is broader or unknown here; the separately applicable exact frozen disjoint domain remains the authority.'))
        rows.append(row)
    selected = [r for r in rows if r['phase17_remaining_candidate']]
    added = [r for r in rows if not r['phase17_instruction_access']]
    remaining = [r for r in rows if r['classification'] != 'proved_disjoint_auxiliary_address_domain']
    field_roots = []
    for row in remaining:
        key = row['physical_bank'], row['cpu']
        proof = row['address_contract']
        if proof is None:
            category = 'unresolved_pointer_or_index_contract'
        elif proof.get('structured_loop_contract') == 'scenario_SRAM_clear':
            category = 'bulk_SRAM_clear_including_city_records'
        elif proof.get('structured_loop_contract') == 'whole_city_template_copy':
            category = 'whole_30_city_template_destination'
        elif key == (10, 0xBD97):
            category = 'dedicated_overlapping_word_city_plus1_plus2'
        elif all(0x6000 <= word <= 0x7FE0 and word % 32 == 0 for word in proof['whole_pointer_values']):
            category = 'aligned_city_base_dynamic_index_still_possible'
        else:
            category = 'other_full_pointer_domain_may_intersect_city_area'
        nearby = [analysis.raw(k) for k in sorted(analysis.known) if k[0] == key[0] and key[1] - 16 <= k[1] <= key[1] + 18]
        field_roots.append(dict(**analysis.raw(key), category=category,
            possible_field_offsets=sorted({(address - 0x6000) % 32 for address in proof['possible_auxiliary_effective_addresses']}) if proof else None,
            pointer_zero_page=row['pointer_zero_page'], effective_Y_values=proof['Y_values'] if proof else None,
            original_producer_origins=proof['origins'] if proof else [],
            original_nearby_instructions=nearby,
            frozen_caller_definition_slices=row['frozen_caller_and_definition_slice_reference'],
            sentinel_FF_comparison_in_nearby_context=any(r['op'] == 'CMP' and r['mode'] == 'im' and r['operand'] == 255 for r in nearby),
            roster_bound_27_comparison_in_nearby_context=any(r['op'] == 'CPY' and r['mode'] == 'im' and r['operand'] == 27 for r in nearby),
            dedicated_official_name_confirmed=False,
            limits='Nearby sentinel/bound instructions are diagnostic, not proof that every caller or path obeys a roster bound. Unknown entries remain unresolved.'))
    dedicated = [analysis.raw(k) for k in sorted(analysis.known) if k[0] == 10 and 0xBD8D <= k[1] <= 0xBDA7]
    rng_loop = [analysis.raw(k) for k in sorted(analysis.known) if (k[0] == 11 and 0xC71A <= k[1] <= 0xC764) or (k[0] == 31 and 0xE89A <= k[1] <= 0xE8A5)]
    save('city-field-root-inventory.json', dict(schema='phase20-city-auxiliary-root-and-loop-inventory-v1',
        ROM_sha256=base.ROM_SHA256, remaining_access_count=len(field_roots),
        category_counts=dict(Counter(r['category'] for r in field_roots)), accesses=field_roots,
        dedicated_plus1_composite=dict(instructions=dedicated,
            mechanical_meaning='LE16(city+1,city+2)>=300 threshold in the AI resupply flow. This is not the formal gold word at+2/+3 and is not an official name for+1.'),
        bounded_full_record_producers=analysis.structured_loops,
        pointer_arithmetic_not_assumed_bounded=dict(instructions=rng_loop,
            mechanical_reason='11:C732 calls fixedE89A; E89A loads X from RNG cursor0054. Therefore C75F INX / C760 CPX#ED is not by itself a pure237-record counter proof. No unsupported63C0+12*X loop bound is installed.'),
        official_field_names=dict(city_plus1=None, city_plus28=None, city_plus29=None, city_plus30=None, city_plus31=None),
        limitation='Bulk clear/template copying is real read/write use of the bytes, but is not a dedicated gameplay field or unused/reserved proof. All unresolved and raw-table alias candidates are retained.'))
    for name, data, schema in (
        ('all-indirect-accesses.json', rows, 'phase20-all-CFG-contextual-pointer-accesses-v1'),
        ('access-contracts.json', selected, 'phase20-old589-contextual-pointer-accesses-v1'),
        ('new-indirect-accesses.json', added, 'phase20-new45-contextual-pointer-accesses-v1'),
        ('remaining-accesses.json', remaining, 'phase20-remaining-contextual-pointer-accesses-v1')):
        save(name, dict(schema=schema, ROM_sha256=base.ROM_SHA256, access_count=len(data),
                        classification_counts=dict(Counter(r['classification'] for r in data)),
                        newly_proved_disjoint_count=sum(r['newly_proved_disjoint'] for r in data), accesses=data,
                        source_CPU_cases=0))
    save('constructor-contracts.json', dict(schema='phase20-original-literal-and-ROM-pair-constructors-v1',
                                           ROM_sha256=base.ROM_SHA256, contracts=analysis.template_catalog))
    save('structured-loop-contracts.json', dict(schema='phase20-bounded-original-record-template-loops-v1',
        ROM_sha256=base.ROM_SHA256, contracts=analysis.structured_loops))
    save('return-pair-contracts.json', dict(schema='phase20-original-universal-return-pair-contracts-v1',
                                           ROM_sha256=base.ROM_SHA256, contracts=[analysis.return_catalog[k] for k in sorted(analysis.return_catalog)]))
    save('pointer-preserving-store-proofs.json', dict(schema='phase20-additional-complete-pair-non-ZP-store-proofs-v1',
        ROM_sha256=base.ROM_SHA256, stores=[analysis.proof_footprints[k] for k in sorted(analysis.proof_footprints)]))
    save('call-effect-summaries.json', dict(schema='phase20-conservative-callee-may-write-closure-v1',
        ROM_sha256=base.ROM_SHA256, summaries=[analysis.effects[k] for k in sorted(analysis.effects)]))
    save('authoritative-contract-selection.json', dict(schema='phase20-explicit-disjoint-authority-selection-v1',
        ROM_sha256=base.ROM_SHA256, row_count=len(authoritative_repairs),
        broader_candidate_count=sum(row['candidate_auxiliary_intersection_count'] is not None for row in authoritative_repairs),
        unknown_candidate_count=sum(row['candidate_auxiliary_intersection_count'] is None for row in authoritative_repairs),
        rows=authoritative_repairs,
        limits='Candidate diagnostics are not used to claim disjointness; every inherited authoritative object is linked and recomputed independently.'))
    summary = dict(schema='phase20-city-auxiliary-context-summary-v1', status='analyzed', ROM_sha256=base.ROM_SHA256,
                   analyzer_path='scripts/analyze_city_auxiliary_contexts.py', analyzer_sha256=base.digest(__file__),
                   artifact_sha256={path: base.digest(ROOT / path) for path in INPUTS},
                   instruction_count=len(analysis.known), original_instruction_bytes_verified=len(analysis.known),
                   original_instruction_byte_comparisons=analysis.raw_checked,
                   source_CPU_cases=0, constructor_template_count=len(analysis.template_catalog),
                   universal_return_contract_count=len(analysis.return_contracts),
                   universal_return_pair_contract_count=sum(bool(proof.pairs) for proof in analysis.return_contracts.values()),
                   universal_numeric_only_return_contract_count=sum(not proof.pairs for proof in analysis.return_contracts.values()),
                   finite_numeric_domain_limit=NUMERIC_LIMIT,
                   structured_original_copy_loop_count=len(analysis.structured_loops),
                   return_contract_evaluations=analysis.return_evaluations,
                   return_local_instruction_transfers=analysis.return_local_transfers,
                   global_instruction_transfers=analysis.steps,
                   finite_proof_refinement_rounds=analysis.refinement_rounds,
                   complete_analysis_fixed_point_proven=False,
                   initial_unknown_root_count=len(roots), fallback_unknown_position_count=len(fallback),
                   classification_counts=dict(Counter(r['classification'] for r in selected)),
                   all_indirect_classification_counts=dict(Counter(r['classification'] for r in rows)),
                   new_indirect_classification_counts=dict(Counter(r['classification'] for r in added)),
                   all_indirect_access_count=len(rows), baseline_candidate_count=len(selected), new_indirect_access_count=len(added),
                   newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint'] for r in rows),
                   newly_proved_disjoint_old589_count=sum(r['newly_proved_disjoint'] for r in selected),
                   phase19_remaining_count=401, remaining_access_count=len(remaining),
                   remaining_by_bank=dict(sorted(Counter(str(r['physical_bank']) for r in remaining).items(), key=lambda x: int(x[0]))),
                   official_target_field_names=dict(city_plus1=None, city_plus28=None, city_plus29=None, city_plus30=None, city_plus31=None),
                   explicit_inherited_authority_selection_count=len(authoritative_repairs),
                   inherited_authority_with_broader_candidate_count=sum(row['candidate_auxiliary_intersection_count'] is not None for row in authoritative_repairs),
                   limitations=['No source gameplay execution or whole-ROM reachability theorem.',
                                'Scalar registers use a finite32-value domain, widened to unknown above32; compare/branch refinement requires the unique actual preceding immediate compare and excludes zero-displacement common edges.',
                                'All same-index ROM constructor prefixes keep raw index0..255. Unresolved8000 mappings are not guessed.',
                                'Return facts start from universally unknown caller input and include every declared local RTS; unresolved computed exits reject a return contract.',
                                'The proof closure adds established output invariants; it is not iterative re-joining of independent low/high bytes.',
                                'No official unused/reserved/padding meaning is inferred from zeros or finite execution.'])
    save('analysis-summary.json', summary)
    print(json.dumps({key: summary[key] for key in ('constructor_template_count', 'universal_return_contract_count', 'universal_return_pair_contract_count', 'classification_counts', 'all_indirect_classification_counts', 'newly_proved_disjoint_all_count')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
