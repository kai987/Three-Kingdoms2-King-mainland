#!/usr/bin/env python3
"""Phase19: must-paired, whole-address provenance over frozen original CFG.

This is an offline abstract analysis, not a CPU, gameplay service, or proof of
whole-ROM reachability.  In particular, equality of a producer PC is NEVER a
reason to correlate two bytes.  Capabilities refer to a currently intact
pair, and every possible write to that pair invalidates all saved half refs.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase19/fields-static'
ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
AUX = frozenset(0x6000 + city * 32 + offset for city in range(30)
                for offset in (1, 28, 29, 30, 31))
ZP = frozenset(range(256))
WRITES = frozenset(('STA', 'STX', 'STY', 'INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR'))
INPUTS = [
    'analysis/phase18/control/instruction-atlas.json',
    'analysis/phase18/control/control-contracts.json',
    'analysis/phase18/fields-static/all-indirect-accesses.json',
    'analysis/phase18/fields-static/call-effect-summaries.json',
    'analysis/phase18/fields-static/indexed-store-proofs.json',
    'analysis/phase18/fields-static/pointer-preserving-store-proofs.json',
    'analysis/phase17/fields/alias-refinement.json',
    'analysis/phase17/fields/pointer-accesses.json',
    'analysis/phase19/runtime/resource-transfer-baseline/transfer-gold-after-up.png',
    'analysis/phase19/runtime/resource-transfer-baseline/transfer-gold-after-up.json',
    'analysis/phase19/runtime/resource-transfer-baseline/transfer-gold-after-up-ram.bin',
    'analysis/phase19/runtime/resource-transfer-baseline/transfer-gold-after-up-sram.bin',
    'analysis/phase19/runtime/resource-transfer-baseline/validation.json',
    'analysis/phase18/fields-static/access-contracts.json',
    'analysis/phase18/fields-static/new-indirect-accesses.json',
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def original(bank, pc):
    return 16 + bank * 8192 + (pc & 8191)


def mapped(key, pc):
    if pc >= 0xE000:
        return (31, pc)
    if key[0] == 31:
        return None
    pair = key[0] - int(key[1] >= 0xC000)
    return (pair + int(pc >= 0xC000), pc) if 0xA000 <= pc < 0xE000 else None


def normalized_ram(address):
    address &= 65535
    return address & 0x7FF if address < 0x2000 else None


@dataclass(frozen=True)
class Pair:
    addresses: frozenset[int]
    origins: int = 0


@dataclass
class State:
    pairs: dict[int, Pair] = field(default_factory=dict)
    registers: tuple[frozenset, frozenset, frozenset] = (frozenset(),) * 3
    pending: dict[int, frozenset] = field(default_factory=dict)
    stack: tuple[frozenset, ...] = ()
    builders: frozenset = frozenset()

    def copy(self):
        return State(dict(self.pairs), self.registers, dict(self.pending), self.stack, self.builders)


def valid_refs(refs, pairs):
    return frozenset((source, half) for source, half in refs if source in pairs)


def join(left, right):
    """Must-pair intersection of keys; MAY union of WHOLE addresses, not bytes."""
    pairs = {}
    for base in left.pairs.keys() & right.pairs.keys():
        a, b = left.pairs[base], right.pairs[base]
        pairs[base] = a if a == b else Pair(a.addresses | b.addresses, a.origins | b.origins)
    regs = tuple(valid_refs(a & b, pairs) for a, b in zip(left.registers, right.registers))
    pending = {base: valid_refs(left.pending[base] & right.pending[base], pairs)
               for base in left.pending.keys() & right.pending.keys()}
    pending = {base: refs for base, refs in pending.items() if refs}
    stack = tuple(valid_refs(a & b, pairs) for a, b in zip(left.stack, right.stack)) \
        if len(left.stack) == len(right.stack) else ()
    return State(pairs, regs, pending, stack, left.builders & right.builders)


def kill(state, written):
    """Kill a pair AND every half capability anywhere when either byte may change.

    A complete previously copied destination is independent and remains valid.
    Thus reexecuting a factory at the SAME PC cannot revive an old half-copy.
    """
    written = set(written)
    dead = {base for base in state.pairs if base in written or ((base + 1) & 255) in written}
    if dead:
        state.pairs = {base: fact for base, fact in state.pairs.items() if base not in dead}
    def refs(values):
        return frozenset(ref for ref in values if ref[0] not in dead)
    state.registers = tuple(refs(v) for v in state.registers)
    state.stack = tuple(refs(v) for v in state.stack)
    state.pending = {base: refs(v) for base, v in state.pending.items()
                     if base not in written and refs(v)}


def atomic_pair(state, base, fact):
    kill(state, (base, (base + 1) & 255))
    state.pairs[base] = fact


def byte_refs(state, address):
    refs = set(state.pending.get(address, ()))
    for base in state.pairs:
        if address == base:
            refs.add((base, 0))
        if address == (base + 1) & 255:
            refs.add((base, 1))
    return frozenset(refs)


def copy_store(state, address, refs):
    # Snapshot refs before the actual store, then remove any refs invalidated
    # by that very store.  Source/destination overlap is deliberately coarse.
    kill(state, (address,))
    refs = valid_refs(refs, state.pairs)
    if refs:
        state.pending[address] = refs
    derived = []
    for destination in ((address - 1) & 255, address):
        low, high = state.pending.get(destination, ()), state.pending.get((destination + 1) & 255, ())
        sources = {source for source, half in low if half == 0 and (source, 1) in high}
        # Every candidate source is currently intact, and each is an equality
        # proof for both current destination bytes. Union is an overapprox.
        if sources:
            addresses = frozenset(a for source in sources for a in state.pairs[source].addresses)
            origins = 0
            for source in sources:
                origins |= state.pairs[source].origins
            state.pairs[destination] = Pair(addresses, origins)
            derived.append((destination, tuple(sorted(sources))))
    return derived


def factory_specs(rom):
    """Original constructor contracts; raw A=0..255, raw ruler nibble=0..15."""
    rows = [
        (31, 0xF2AF, 0xF2D3, 0xF2D6, 0, 'city', {0, 1}, {'A', 'Y'}, True),
        (31, 0xF2D7, 0xF304, 0xF307, 0, 'officer', {0, 1}, {'A', 'Y'}, True),
        (31, 0xF308, 0xF343, 0xF35E, 0, 'name_ROM', {0, 1, 2, 0xE1}, {'A', 'X', 'Y'}, False),
        (31, 0xF368, 0xF375, 0xF378, 0, 'ruler_raw16', {0, 1}, {'A', 'Y'}, True),
        (31, 0xF387, 0xF3B9, 0xF3BC, 0, 'initial_officer_ROM', {0, 1, 0xE1}, {'A', 'Y'}, True),
        (8, 0xB469, 0xB48D, 0xB490, 0x20, 'city', {0x20, 0x21}, {'A', 'Y'}, True),
        (8, 0xB491, 0xB4BE, 0xB4C1, 0x20, 'officer', {0x20, 0x21}, {'A', 'Y'}, True),
        (8, 0xB4C2, 0xB4CF, 0xB4D2, 0x20, 'ruler_raw16', {0x20, 0x21}, {'A', 'Y'}, True),
        (8, 0xB4E1, 0xB513, 0xB516, 0x20, 'initial_officer_ROM', {0x20, 0x21, 0xDE}, {'A', 'Y'}, True),
        (11, 0xD105, 0xD121, 0xD12C, 0x20, 'city', {0x20, 0x21}, {'A', 'Y'}, False),
        (11, 0xD283, 0xD2A6, 0xD2AA, 0x20, 'officer', {0x20, 0x21}, {'A', 'X'}, False),
        (11, 0xD2AB, 0xD2CE, 0xD2D2, 0x22, 'officer', {0x22, 0x23}, {'A', 'X'}, False),
        (11, 0xD319, 0xD325, 0xD327, 0x24, 'ruler_raw16', {0x24, 0x25}, {'A', 'Y'}, True),
    ]
    result = {}
    for i, (bank, pc, marker, end, base, kind, writes, regs, high) in enumerate(rows):
        if kind == 'city':
            addresses = frozenset(0x6000 + 32 * a for a in range(256))
        elif kind == 'officer':
            addresses = frozenset(0x63C0 + 12 * a for a in range(256))
        elif kind == 'name_ROM':
            addresses = frozenset(0x901A + 10 * a for a in range(256))
        elif kind == 'initial_officer_ROM':
            addresses = frozenset(0x8000 + 12 * a for a in range(256))
        else:
            table = 0xF379 if bank == 31 else 0xB4D3 if bank == 8 else 0xD328
            addresses = frozenset(rom[original(bank, table + 2 * a)] |
                                  (rom[original(bank, table + 2 * a + 1)] << 8) for a in range(16))
        result[bank, pc] = dict(id=i, entry=(bank, pc), marker=(bank, marker), end=end,
                               base=base, kind=kind, addresses=addresses, writes=frozenset(writes),
                               regs=frozenset(regs), returns_high=high,
                               prologue=frozenset((bank, p) for p in range(pc, marker + 1)))
    # D304 calls the audited D105 and preserves that complete pair through its
    # bounded roster scan. No inferred correlation of independent return bytes.
    d = dict(result[11, 0xD105])
    d.update(id=len(rows), entry=(11, 0xD304), marker=None, end=0xD318,
             regs=frozenset(('A', 'X', 'Y')), prologue=frozenset())
    result[11, 0xD304] = d
    return result


class Analysis:
    def __init__(self, rom):
        self.rom = rom
        self.atlas = read(INPUTS[0])
        self.known = {(r['physical_bank'], r['cpu']): r for r in self.atlas['instructions']}
        self.edges = {(r['physical_bank'], r['cpu']): [tuple(t) for t in r['targets']]
                      for r in self.atlas['edges']}
        self.old_accesses = read(INPUTS[2])['accesses']
        self.access_index = {(r['physical_bank'], r['cpu']): r for r in self.old_accesses}
        self.effects = {(r['physical_bank'], r['cpu']): r for r in read(INPUTS[3])['summaries']}
        self.indexed = {(r['physical_bank'], r['cpu']): r for r in read(INPUTS[4])['stores']}
        self.old_safe = {(r['physical_bank'], r['cpu']): r['address_proof']
                         for r in read(INPUTS[5])['stores']}
        self.factories = factory_specs(rom)
        self.factory_ids = {d['id']: d for d in self.factories.values()}
        self.markers = {d['marker']: d for d in self.factories.values() if d['marker']}
        self.dispatch = {}
        for d in read(INPUTS[1])['bounded_dispatch_tables']:
            key = d['call']['physical_bank'], d['call']['cpu']
            self.dispatch[key] = dict(d, mapped_targets=[mapped(key, pc) for pc in d['targets']])
        self.states = {}
        self.queue = deque()
        self.scheduled = set()
        self.steps = 0
        self.copies = set()
        self.copy_details = {}
        self.conditional_leaves = {}
        self.leaf_cache = {}
        self.origins = []
        self.origin_ids = {}
        self.raw_checked = 0

    def raw(self, key):
        r = self.known[key]
        return {name: r[name] for name in ('physical_bank', 'cpu', 'rom_offset', 'op', 'mode', 'operand', 'raw_hex')}

    def add_origin(self, key, kind):
        tag = key, kind
        if tag not in self.origin_ids:
            self.origin_ids[tag] = len(self.origins)
            self.origins.append(dict(**self.raw(key), origin_kind=kind))
        return 1 << self.origin_ids[tag]

    def fact(self, d, key):
        return Pair(d['addresses'], self.add_origin(key, 'atomic_' + d['kind']))

    def emit(self, key, state):
        if key not in self.known:
            return
        previous = self.states.get(key)
        value = state if previous is None else join(previous, state)
        if previous != value:
            self.states[key] = value
            if key not in self.scheduled:
                self.queue.append(key)
                self.scheduled.add(key)

    def indices(self, key):
        proof = self.indexed.get(key)
        return proof['index_values'] if proof and proof['index_values'] is not None else range(256)

    def direct_targets(self, key):
        r = self.known[key]
        mode, operand = r['mode'], r['operand']
        if mode in ('zp', 'ab'):
            addresses = (operand,)
        elif mode in ('zpx', 'zpy'):
            addresses = ((operand + index) & 255 for index in self.indices(key))
        elif mode in ('abx', 'aby'):
            addresses = ((operand + index) & 65535 for index in self.indices(key))
        else:
            return None, True
        normalized = {normalized_ram(a) for a in addresses}
        return {a for a in normalized if a is not None and a < 256}, \
            any(a is not None and 256 <= a < 512 for a in normalized)

    def indirect_addresses(self, key, state):
        r = self.known[key]
        if r['mode'] != 'iy' or r['operand'] not in state.pairs:
            return None
        fact = state.pairs[r['operand']]
        old = self.access_index.get(key)
        indices = old['Y_values'] if old and old['Y_values'] is not None else range(256)
        return frozenset((base + y) & 65535 for base in fact.addresses for y in indices)

    def store_effect(self, key, state):
        r = self.known[key]
        if r['mode'] not in ('iy', 'ix'):
            return self.direct_targets(key)
        addresses = self.indirect_addresses(key, state)
        if addresses is not None:
            values = {normalized_ram(a) for a in addresses}
            return {a for a in values if a is not None and a < 256}, \
                any(a is not None and 256 <= a < 512 for a in values)
        proof = self.old_safe.get(key)
        if proof and not proof['may_write_zero_page']:
            return set(), proof['may_write_stack_RAM_mirror']
        return ZP, True

    def leaf_contract(self, entry, state):
        """Conditional local leaf writes under intact input pointer contracts.

        No calls/computed exits; any possible write to an input pointer, or an
        indirect write that may hit zero-page, rejects refinement. Thus later
        indirect stores cannot change the address domain being used here.
        """
        if entry not in self.leaf_cache:
            todo, seen, stores, valid, returned, stack_ops = [entry], set(), [], True, False, False
            while todo:
                key = todo.pop()
                if key in seen:
                    continue
                seen.add(key)
                if key not in self.known:
                    valid = False
                    break
                row = self.known[key]
                stack_ops |= row['op'] in ('PHA', 'PHP', 'PLA', 'PLP', 'TXS')
                if row['op'] == 'RTS':
                    returned = True
                    continue
                if row['op'] in ('JSR', 'RTI', 'BRK', '?') or (row['op'] == 'JMP' and row['mode'] != 'ab'):
                    valid = False
                    break
                if row['op'] in WRITES and row['mode'] != 'a':
                    stores.append(key)
                targets = self.edges.get(key, ())
                if not targets:
                    valid = False
                todo.extend(targets)
            self.leaf_cache[entry] = (valid and returned, tuple(stores), tuple(sorted(seen)), stack_ops)
        valid, stores, nodes, stack_ops = self.leaf_cache[entry]
        if not valid:
            return None
        writes, stack = set(), stack_ops
        indirect = []
        for key in stores:
            row = self.known[key]
            if row['mode'] in ('iy', 'ix'):
                if row['mode'] != 'iy' or row['operand'] not in state.pairs:
                    return None
                indirect.append(key)
            else:
                here, hit_stack = self.direct_targets(key)
                writes.update(here)
                stack |= hit_stack
        pointer_bytes = {byte for key in indirect for byte in
                         (self.known[key]['operand'], (self.known[key]['operand'] + 1) & 255)}
        if writes & pointer_bytes:
            return None
        for key in indirect:
            here, hit_stack = self.store_effect(key, state)
            if here:
                return None
            stack |= hit_stack
        bases = sorted({self.known[k]['operand'] for k in indirect})
        signature = (entry, tuple((base, tuple(sorted(state.pairs[base].addresses))) for base in bases))
        self.conditional_leaves[signature] = dict(
            **self.raw(entry), instruction_count=len(nodes), instructions=[self.raw(k) for k in nodes],
            RTS_exits=[self.raw(k) for k in nodes if self.known[k]['op'] == 'RTS'],
            zero_page_may_write=sorted(writes), may_write_stack=stack,
            required_pair_bases=bases,
            required_whole_pointer_values={str(base): sorted(state.pairs[base].addresses) for base in bases},
            contract='All original local paths end/loop within this call-free CFG. No input pointer byte is written; every indirect store is proven non-ZP under the current complete input pairs. Not a termination proof.')
        return writes, stack

    def apply_call(self, state, target, key, far=False):
        result = state.copy()
        d = self.factories.get(target)
        if d:
            writes, regs = d['writes'], d['regs']
            stack_write = False
        elif target in ((31, 0xF25F), (31, 0xF266)):
            writes, regs = ({0xE1} if target[1] == 0xF25F else {0xDE}), set()
            stack_write = False
        else:
            effect = self.effects.get(target)
            writes = set(effect['zero_page_may_write']) if effect else ZP
            regs = set(effect['register_may_write']) if effect else {'A', 'X', 'Y'}
            conditional = self.leaf_contract(target, state) if target else None
            if conditional is not None:
                writes, stack_write = conditional
            else:
                stack_write = True  # no unproved preservation of saved PHA halves
        if far:
            writes = set(writes) | set(range(0x58, 0x5E)) | {0xE2, 0xE3}
            regs = set(regs) | {'A', 'Y'}
            stack_write = True
        kill(result, writes)
        result.registers = tuple(frozenset() if name in regs else refs
                                 for name, refs in zip(('A', 'X', 'Y'), result.registers))
        if stack_write:
            result.stack = ()
        if d:
            atomic_pair(result, d['base'], self.fact(d, key))
            if d['returns_high'] and not far:
                result.registers = (frozenset(((d['base'], 1),)),) + result.registers[1:]
        # Only exact approved mapper routines may occur inside a constructor
        # prologue and retain its current invocation's builder capability.
        if target not in ((31, 0xF25F), (31, 0xF266)):
            result.builders = frozenset()
        return result

    def transfer(self, key, input_state):
        state = input_state.copy()
        row = self.known[key]
        op, mode, operand = row['op'], row['mode'], row['operand']
        state.builders = frozenset(i for i in state.builders if key in self.factory_ids[i]['prologue'])
        if key in self.factories and self.factories[key]['marker']:
            state.builders |= frozenset((self.factories[key]['id'],))
        regs = list(state.registers)
        if op in ('LDA', 'LDX', 'LDY'):
            addr = normalized_ram(operand) if mode in ('zp', 'ab') else None
            regs[('LDA', 'LDX', 'LDY').index(op)] = byte_refs(state, addr) if addr is not None and addr < 256 else frozenset()
        elif op in ('TAX', 'TAY', 'TXA', 'TYA'):
            source, destination = {'TAX': (0, 1), 'TAY': (0, 2), 'TXA': (1, 0), 'TYA': (2, 0)}[op]
            regs[destination] = regs[source]
        elif op in ('ADC', 'SBC', 'AND', 'ORA', 'EOR') or (op in ('ASL', 'LSR', 'ROL', 'ROR') and mode == 'a'):
            regs[0] = frozenset()
        elif op in ('INX', 'DEX', 'TSX'):
            regs[1] = frozenset()
        elif op in ('INY', 'DEY'):
            regs[2] = frozenset()
        elif op in ('PHA', 'PHP'):
            state.stack = (state.stack + (regs[0] if op == 'PHA' else frozenset(),))[-16:]
        elif op in ('PLA', 'PLP'):
            if op == 'PLA':
                regs[0] = state.stack[-1] if state.stack else frozenset()
            state.stack = state.stack[:-1]
        elif op == 'TXS':
            state.stack = ()
        state.registers = tuple(regs)
        if op in WRITES and mode != 'a':
            writes, stack = self.store_effect(key, state)
            if op in ('STA', 'STX', 'STY') and mode in ('zp', 'ab') and len(writes) == 1:
                refs = state.registers[('STA', 'STX', 'STY').index(op)]
                before = set(state.pairs)
                derived = copy_store(state, next(iter(writes)), refs)
                for base in set(state.pairs) - before:
                    self.copies.add((key, base))
                for base, sources in derived:
                    self.copy_details[key, base, sources] = dict(**self.raw(key), destination_pair_base=base,
                        current_source_pair_bases=list(sources),
                        relationship='Both destination half copies refer to the same currently intact source pair; any possible source write invalidates every pending/register/stack reference.')
            else:
                kill(state, writes)
            if stack:
                state.stack = ()
        d = self.markers.get(key)
        if d and d['id'] in state.builders:
            atomic_pair(state, d['base'], self.fact(d, d['entry']))
            state.builders -= frozenset((d['id'],))
            state.registers = (frozenset(((d['base'], 1),)),) + state.registers[1:]
        return state

    def run_queue(self):
        while self.queue:
            key = self.queue.popleft()
            self.scheduled.discard(key)
            state = self.transfer(key, self.states[key])
            row = self.known[key]
            if row['op'] != 'JSR':
                for target in self.edges.get(key, ()):
                    self.emit(target, state)
            elif key in self.dispatch:
                base = 0 if row['operand'] == 0xEADE else 0x20
                for target in self.dispatch[key]['mapped_targets']:
                    value = state.copy()
                    kill(value, range(base, base + 5))
                    table_pointer = row['cpu'] + 2
                    value.pairs[base + 1] = Pair(frozenset((table_pointer,)), self.add_origin(key, 'dispatcher_ROM_table'))
                    value.pairs[base + 3] = Pair(frozenset((target[1],)), self.add_origin(key, 'dispatcher_CPU_target'))
                    value.registers = (frozenset(((base + 3, 1),)), value.registers[1], value.registers[2])
                    value.builders = frozenset()
                    self.emit(target, value)
            else:
                following = mapped(key, row['cpu'] + row['size'] + (2 if row['operand'] == 0xEE07 else 0))
                targets = [target for target in self.edges.get(key, ()) if target != following]
                if row['operand'] == 0xEE07:
                    joined = None
                    for target in targets:
                        callee = state.copy()
                        kill(callee, set(range(0x58, 0x5E)) | {0xE2, 0xE3})
                        callee.pairs[0x5B] = Pair(frozenset((target[1],)), self.add_origin(key, 'farcall_CPU_target'))
                        callee.registers = (frozenset(), callee.registers[1], callee.registers[2])
                        callee.stack, callee.builders = (), frozenset()
                        self.emit(target, callee)
                        result = self.apply_call(state, target, key, far=True)
                        joined = result if joined is None else join(joined, result)
                    self.emit(following, joined if joined is not None else self.apply_call(state, None, key, far=True))
                else:
                    target = mapped(key, row['operand'])
                    if target in self.known:
                        callee = state.copy()
                        callee.stack, callee.builders = (), frozenset()
                        self.emit(target, callee)
                    self.emit(following, self.apply_call(state, target, key))
            self.steps += 1
            if self.steps % 50000 == 0:
                print(f'paired worklist: {self.steps} transfers, {len(self.states)} positions, {len(self.queue)} queued', flush=True)

    def run(self):
        for key, row in self.known.items():
            assert row['rom_offset'] == original(*key)
            assert self.rom[row['rom_offset']:row['rom_offset'] + row['size']] == bytes.fromhex(row['raw_hex'])
            self.raw_checked += 1
        incoming = Counter(target for targets in self.edges.values() for target in targets)
        roots = [key for key in self.known if not incoming[key]]
        for key in roots:
            self.emit(key, State())
        self.run_queue()
        # Isolated cycles/unreached positions remain externally unknown. This
        # explicit fallback also prevents reachability from becoming a proof.
        fallback = [key for key in self.known if key not in self.states]
        for key in fallback:
            self.emit(key, State())
        self.run_queue()
        return roots, fallback

    def contract(self, key):
        row, state = self.access_index[key], self.states[key]
        base = row['operand']
        if row['mode'] != 'iy' or base not in state.pairs:
            return None
        fact = state.pairs[base]
        indices = row['Y_values'] if row['Y_values'] is not None else range(256)
        addresses = self.indirect_addresses(key, state)
        matches = sorted(addresses & AUX)
        return dict(whole_pointer_values=sorted(fact.addresses), whole_pointer_count=len(fact.addresses),
                    low_high_relationship='union of complete paired addresses; no Cartesian byte product',
                    Y_values=list(indices), Y_was_unknown=row['Y_values'] is None,
                    possible_auxiliary_effective_addresses=matches, auxiliary_address_intersection_count=len(matches),
                    origins=[self.origins[i] for i in range(len(self.origins)) if fact.origins & (1 << i)],
                    may_write_zero_page=any((a := normalized_ram(address)) is not None and a < 256 for address in addresses),
                    may_write_stack_RAM_mirror=any((a := normalized_ram(address)) is not None and 256 <= a < 512 for address in addresses))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    args = parser.parse_args()
    rom = Path(args.rom).read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    analysis = Analysis(rom)
    roots, fallback = analysis.run()
    baseline = read(INPUTS[7])
    old_keys = {(r['physical_bank'], r['cpu']) for r in baseline['accesses']}
    candidates = {(r['physical_bank'], r['cpu']) for r in read(INPUTS[6])['remaining_candidates']}
    rows = []
    for old in analysis.old_accesses:
        key = old['physical_bank'], old['cpu']
        proof = analysis.contract(key)
        # A frozen independent-domain disjoint proof remains independently
        # sufficient. A new unknown relation is not a refutation of it.
        inherited_disjoint = old['classification'] == 'proved_disjoint_auxiliary_address_domain'
        disjoint = inherited_disjoint or (proof is not None and not proof['auxiliary_address_intersection_count'])
        classification = 'proved_disjoint_auxiliary_address_domain' if disjoint else \
            'possible_city_auxiliary_alias' if proof is not None else 'unresolved_pointer_or_index_contract'
        basis = 'whole_pointer_relation' if proof is not None and not proof['auxiliary_address_intersection_count'] else \
            'frozen_phase18_independent_domain' if inherited_disjoint else 'whole_pointer_relation' if proof else 'unknown_relation'
        rows.append(dict(**{name: old[name] for name in ('physical_bank', 'cpu', 'rom_offset', 'op', 'mode', 'operand', 'raw_hex', 'pointer_zero_page', 'Y_values')},
                         classification=classification, address_contract=proof,
                         whole_pointer_values=proof['whole_pointer_values'] if proof else None,
                         proof_basis=basis, phase18_classification=old['classification'],
                         phase18_address_contract=old['address_contract'] if inherited_disjoint else None,
                         newly_proved_disjoint=disjoint and not inherited_disjoint,
                         phase17_instruction_access=key in old_keys, phase17_remaining_candidate=key in candidates,
                         pointer_producer_calls=old.get('pointer_producer_calls', []),
                         original_preceding_context=[dict(physical_bank=key[0], **r) for r in old.get('context_original_bytes', [])],
                         frozen_caller_and_definition_slice_reference=dict(
                             path=INPUTS[13] if key in candidates else INPUTS[14] if key not in old_keys else INPUTS[2],
                             physical_bank=key[0], cpu=key[1],
                             scope='Frozen predecessor diagnostics/call owners, not a new reachability or source-generation proof.'),
                         limits=['Trusted bounded CFG/call domains only; external interrupted or corrupted pointer/selector inputs are not ruled out.',
                                 'Y/index and preexisting disjoint-store contracts are conservatively inherited from frozen phase18.',
                                 'An unresolved relation is not evidence of actual auxiliary-field use.']))
    selected = [r for r in rows if r['phase17_remaining_candidate']]
    added = [r for r in rows if not r['phase17_instruction_access']]
    for name, data, schema in (
        ('all-indirect-accesses.json', rows, 'phase19-all-corrected-CFG-paired-pointer-accesses-v1'),
        ('access-contracts.json', selected, 'phase19-city-auxiliary-paired-pointer-contracts-v1'),
        ('new-indirect-accesses.json', added, 'phase19-new-corrected-CFG-paired-pointer-accesses-v1')):
        save(name, dict(schema=schema, ROM_sha256=ROM_SHA256, access_count=len(data),
                        classification_counts=dict(Counter(r['classification'] for r in data)),
                        newly_proved_disjoint_count=sum(r['newly_proved_disjoint'] for r in data),
                        accesses=data, source_CPU_cases=0))
    factories = []
    for key, d in analysis.factories.items():
        instructions = [analysis.raw(k) for k in sorted(analysis.known) if k[0] == key[0] and key[1] <= k[1] <= d['end']]
        table_contract = None
        if d['kind'] == 'ruler_raw16':
            table_cpu = 0xF379 if key[0] == 31 else 0xB4D3 if key[0] == 8 else 0xD328
            offset = original(key[0], table_cpu)
            table_contract = dict(physical_bank=key[0], cpu=table_cpu, rom_offset=offset,
                                  raw_hex=rom[offset:offset + 32].hex(' ').upper(),
                                  extent='16 original LE16 words, including adjacent instruction bytes beyond the usual seven ruler entries')
        factories.append(dict(**analysis.raw(key), pointer_base=d['base'], kind=d['kind'],
                              raw_A_domain=list(range(256)), whole_pointer_values=sorted(d['addresses']),
                              pointer_complete_after_cpu=d['marker'][1] if d['marker'] else None,
                              zero_page_may_write=sorted(d['writes']), register_may_write=sorted(d['regs']),
                              raw_ruler_nibble_domain=list(range(16)) if d['kind'] == 'ruler_raw16' else None,
                              original_raw16_table=table_contract,
                              original_instructions=instructions))
    save('atomic-factory-contracts.json', dict(schema='phase19-original-atomic-pointer-factories-v1',
                                               ROM_sha256=ROM_SHA256, factories=factories))
    save('conditional-callee-contracts.json', dict(schema='phase19-conditional-original-leaf-write-contracts-v1',
                                                  ROM_sha256=ROM_SHA256, contracts=list(analysis.conditional_leaves.values())))
    save('complete-copy-contracts.json', dict(schema='phase19-original-complete-pair-copy-contracts-v1',
                                              ROM_sha256=ROM_SHA256, copies=list(analysis.copy_details.values())))
    # Separate, directly readable original UI evidence. The pointer analysis
    # itself has NOT established an official name for +1 or +28..31.
    cache = [analysis.raw(k) for k in sorted(analysis.known) if k[0] == 25 and 0xB8D7 <= k[1] <= 0xB963]
    selectors = [analysis.raw(k) for k in sorted(analysis.known) if k[0] == 27 and
                 (0xB8B4 <= k[1] <= 0xB8C5 or 0xB902 <= k[1] <= 0xB913 or
                  0xB92F <= k[1] <= 0xB976 or 0xB9AC <= k[1] <= 0xB9B4 or 0xB9D8 <= k[1] <= 0xB9E0)]
    native_ram = (ROOT / INPUTS[10]).read_bytes()
    native_sram = (ROOT / INPUTS[11]).read_bytes()
    source_city, destination_city = native_ram[0x470], native_ram[0x471]
    assert (len(native_ram), len(native_sram)) == (2048, 8192)
    save('city16-original-UI-link.json', dict(schema='phase19-city-plus16-original-UI-label-link-v1',
        ROM_sha256=ROM_SHA256, field_offset=16, original_labels=['宝', 'タカラ'],
        label_transcription_method='Direct reading of the unaltered original-core 256x240 RGB image, independently observed by multiple agents; no generated OCR/glyph replacement.',
        image_path=INPUTS[8], image_sha256=digest(ROOT / INPUTS[8]),
        image_label_regions=dict(header_treasure=[24, 88, 40, 104], third_transfer_row=[76, 194, 224, 210]),
        native_validation_path=INPUTS[12], native_validation_sha256=digest(ROOT / INPUTS[12]),
        native_observed_bytes=dict(source_city_0470=source_city, destination_city_0471=destination_city,
            source_city_plus16=native_sram[source_city * 32 + 16],
            destination_city_plus16=native_sram[destination_city * 32 + 16],
            third_quantity_limit_049C=native_ram[0x49C]),
        source_cache_original_instructions=cache, quantity_selection_and_effect_original_instructions=selectors,
        mechanical_link=['25:B8F7 LDY#10 / B8F9 LDA($00),Y / B8FB STA$049C caches source city+16.',
                         '25:B937..B963 clips that third limit to min(source city+16, 99-destination city+16); the observed destination99 makes the input limit0.',
                         '27:B933..B93E selects $049C as the third quantity limit; B962..B96D stores the selected byte in $0432.',
                         '27:B9AC..B9B4 subtracts $0432 from source city+16; B9D8..B9E0 adds it to destination city+16.'],
        confidence='confirmed_original_UI_label_and_dedicated_transfer_read_write_chain',
        limits=['This names +16 only, not the overlapping word(city+1,city+2) or tail bytes.',
                'The original transfer fixture is controlled as disclosed in its frozen native receipt; this static link does not relabel it natural gameplay.',
                'Old frozen API names/receipts remain unchanged; raw-byte cost uses do not by themselves identify a different official field.']))
    summary = dict(schema='phase19-city-pointer-provenance-summary-v1', status='analyzed', ROM_sha256=ROM_SHA256,
                   analyzer_path='scripts/analyze_city_pointer_provenance.py', analyzer_sha256=digest(__file__),
                   artifact_sha256={path: digest(ROOT / path) for path in INPUTS},
                   instruction_count=len(analysis.known), original_instruction_bytes_verified=analysis.raw_checked,
                   source_CPU_cases=0, whole_ROM_reachability_proven=False, official_field_names_confirmed=False,
                   worklist_transfers=analysis.steps, initial_unknown_root_count=len(roots), fallback_unknown_position_count=len(fallback),
                   relational_domain_fixed_point=True, fixed_point_scope='This must-pair domain and frozen conservative call effects; not a complete relational analysis of all CPU state.',
                   complete_copy_sites_observed=len(analysis.copies), atomic_factory_count=len(factories),
                   conditional_leaf_contract_count=len(analysis.conditional_leaves),
                   baseline_candidate_count=len(selected), classification_counts=dict(Counter(r['classification'] for r in selected)),
                   newly_proved_disjoint_candidate_count=sum(r['newly_proved_disjoint'] for r in selected),
                   all_indirect_access_count=len(rows), all_indirect_classification_counts=dict(Counter(r['classification'] for r in rows)),
                   newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint'] for r in rows),
                   whole_relation_disjoint_count=sum(r['proof_basis'] == 'whole_pointer_relation' and r['classification'] == 'proved_disjoint_auxiliary_address_domain' for r in rows),
                   inherited_only_disjoint_count=sum(r['proof_basis'] == 'frozen_phase18_independent_domain' for r in rows),
                   new_indirect_access_count=len(added), new_indirect_classification_counts=dict(Counter(r['classification'] for r in added)),
                   limitations=['No new production service/ROMCPU/Native execution is claimed by this static receipt.',
                                'Pointer-pair keys are must properties; whole address sets are may unions. Unknown calls erase affected pairs.',
                                'No equality based on producer PC or generation tags; any half-write erases all saved references to that source pair.',
                                'Constructor input domains retain all256 A values and all16 raw ruler indexes; no implicit valid-ID restriction.',
                                'General nonfactory return-pair summaries and arithmetic pointer updates remain unknown. Do not infer unused/padding or official names.'])
    save('analysis-summary.json', summary)
    print(json.dumps({key: summary[key] for key in ('worklist_transfers', 'classification_counts', 'newly_proved_disjoint_candidate_count', 'all_indirect_classification_counts', 'newly_proved_disjoint_all_count')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
