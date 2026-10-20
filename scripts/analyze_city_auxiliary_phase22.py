#!/usr/bin/env python3
"""Phase22: original guard/unchanged-roster and scalar-index pointer relations.

Frozen phase1..21 inputs are read only. Index projections are never substituted
for the new explicit pointer/index disjunction, and raw opcode windows remain
unproved entries rather than silently decoded code.
"""
from collections import Counter, deque
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase22/fields-static'
SPEC = importlib.util.spec_from_file_location('frozen_phase21_field_model', ROOT / 'scripts/analyze_city_auxiliary_semantics.py')
old = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = old; SPEC.loader.exec_module(old)
base = old.base
OLD_AUDIT = '635554d4c3845b4459e929a1153d797f4ac913ea673ce6ea19c882f1d20aa389'
OLD_ZIP = '6a8923b2355fcfa58b0d6acc2da88e1224c2c40a8509f01f3dd4e811d445657f'
DISJOINT = 'proved_disjoint_auxiliary_address_domain'
INPUTS = list(dict.fromkeys(old.INPUTS + [
    'scripts/analyze_city_auxiliary_semantics.py', 'analysis/phase21/verification.json',
    'analysis/phase21/fields-static/all-indirect-accesses.json',
    'analysis/phase21/fields-static/analysis-summary.json', 'analysis/phase21/fields-static/verification.json',
    'analysis/phase21/fields-static/bounded-recruitment-contract.json',
    'analysis/phase21/fields-static/untrusted-PRG-opcode-windows.json',
    'analysis/phase21/recruitment/static-catalog.json',
    'analysis/phase21/runtime/core-provenance/upstream/source/core/NstCpu.cpp',
]))


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def cases(contract):
    return contract.get('address_cases', [contract])


def projection_words(contract):
    return frozenset(p for item in cases(contract) for p in old.old.complete_words(item))


def projection_Y(contract):
    return sorted({y for item in cases(contract) for y in item['Y_values']})


def auxiliary_intersection(contract):
    return sorted({a for item in cases(contract) for a in old.old.actual_auxiliary_intersection(item)})


def dummy_auxiliary_intersection(contract, operation):
    """Uncorrected-page bus reads are separate from effective data addresses."""
    found = set()
    for item in cases(contract):
        pointers = old.old.complete_words(item)
        for address in base.AUX:
            for index in item['Y_values']:
                pointer = (address & 0xFF00) | ((address - index) & 255)
                if pointer in pointers and (operation == 'STA' or (pointer & 255) + index >= 256):
                    found.add(address)
                    break
    return sorted(found)


def scalar_domain(rows):
    values = set(range(256))
    for row in rows:
        op, operand = row['op'], row['operand']
        if op in ('LDX', 'LDY', 'LDA'):
            assert row['mode'] == 'im'
            values = {operand}
        elif op == 'ASL': values = {(a * 2) & 255 for a in values}
        elif op == 'LSR': values = {a >> 1 for a in values}
        elif op == 'AND': values = {a & operand for a in values}
        elif op == 'ORA': values = {a | operand for a in values}
        elif op == 'EOR': values = {a ^ operand for a in values}
        else: assert op in ('TAX', 'TAY')
    return sorted(values)


class Analysis(old.Analysis):
    def __init__(self, rom):
        self.scalar_prefixes = []
        super().__init__(rom)
        self.guards, self.guarded_sites = self.guard_contracts()

    def install_templates(self):
        super().install_templates()
        previous = {}
        for key, row in self.known.items():
            previous.setdefault((key[0], key[1] + row['size']), []).append(key)
        for catalog in self.template_catalog:
            if catalog['kind'] != 'immutable_ROM_indexed_word': continue
            load_key = catalog['loads_start']['physical_bank'], catalog['loads_start']['cpu']
            predecessor = previous.get(load_key, [])
            if len(predecessor) != 1: continue
            register = self.known[load_key]['mode'][-1].upper()
            last = predecessor[0]; row = self.known[last]
            if row['op'] == 'LD' + register and row['mode'] == 'im':
                prefix = [last]
            elif row['op'] == 'TA' + register:
                prefix, cursor = [last], last
                for _ in range(8):
                    preceding = previous.get(cursor, [])
                    if len(preceding) != 1: break
                    key = preceding[0]; value = self.known[key]
                    supported = value['op'] in ('ASL', 'LSR') and value['mode'] == 'a' or value['op'] in ('AND', 'ORA', 'EOR', 'LDA') and value['mode'] == 'im'
                    if not supported: break
                    prefix.insert(0, key); cursor = key
                if len(prefix) == 1: continue
            else: continue
            domain = scalar_domain([self.known[k] for k in prefix])
            if len(domain) == 256: continue
            marker = catalog['complete_after']['physical_bank'], catalog['complete_after']['cpu']
            descriptor = self.markers[marker]
            first_keys = self.straight(load_key, 5)
            increment = len(first_keys) == 5 and self.known[first_keys[2]]['op'] in ('INX', 'INY')
            load_keys = first_keys if increment else self.straight(load_key, 4)
            loads = [self.known[k] for k in load_keys if self.known[k]['op'] == 'LDA']
            assert len(loads) == 2
            increment = len(load_keys) == 5
            values = []
            for index in domain:
                first = self.rom_value(load_key, loads[0]['operand'] + index, catalog['explicit_data_window_bank'])
                second = self.rom_value(load_key, loads[1]['operand'] + ((index + int(increment)) & 255), catalog['explicit_data_window_bank'])
                assert first is not None and second is not None
                values.append(first | second << 8 if descriptor['marker_half'] == 1 else second | first << 8)
            prior_entry = descriptor['entry']
            if not set(prefix) <= descriptor['prologue']:
                assert prior_entry == load_key
                self.templates[prior_entry].remove(descriptor)
                if not self.templates[prior_entry]: del self.templates[prior_entry]
                descriptor['entry'] = prefix[0]
                self.templates.setdefault(prefix[0], []).append(descriptor)
            descriptor['prologue'] |= frozenset(prefix)
            descriptor['addresses'] = frozenset(values)
            catalog.update(**self.raw(descriptor['entry']), index_domain=domain,
                whole_pointer_values=sorted(descriptor['addresses']),
                instructions=[self.raw(k) for k in sorted(descriptor['prologue'])],
                scalar_prefix_contract=dict(entry=self.raw(prefix[0]), instructions=[self.raw(k) for k in prefix],
                    raw_input_domain=list(range(256)), output_index_values=domain,
                    statement='Exact contiguous pure bit operations/immediates and register transfer. Every raw input byte is included; no legal-city/ruler selector range is assumed. The original constructor builder must traverse this prefix, and any alternate middle entry/merge loses the capability.'),
                limits='Full original must-builder prefix, including any explicit mapper setup; narrowed index comes only from actual preceding instructions. No same-PC identity or unstated7-ruler assumption.')
            self.scalar_prefixes.append(catalog)

    def local_region(self, start, end):
        nodes = {k for k in self.known if k[0] == 11 and start <= k[1] <= end}
        successors = {}
        for key in nodes:
            row = self.known[key]
            if row['op'] == 'RTS': targets = []
            elif row['op'] == 'JSR': targets = [(11, row['cpu'] + row['size'])]
            else: targets = self.edges.get(key, [])
            successors[key] = [target for target in targets if target in nodes]
        incoming = [(source, target) for target in nodes for source in self.predecessors.get(target, ()) if source not in nodes]
        assert all(target == (11, start) for _, target in incoming), incoming
        reachable, queue = set(), [(11, start)]
        while queue:
            key = queue.pop()
            if key not in reachable:
                reachable.add(key); queue.extend(successors[key])
        pred = {key: {p for p in reachable if key in successors[p]} for key in reachable}
        dom = {key: ({key} if key == (11, start) else set(reachable)) for key in reachable}
        changed = True
        while changed:
            changed = False
            for key in sorted(reachable):
                if key == (11, start): continue
                value = {key} | set.intersection(*(dom[p] for p in pred[key]))
                if value != dom[key]: dom[key] = value; changed = True
        return nodes, successors, dom, incoming

    def guard_contracts(self):
        specs = [dict(name='appearance_recruitment_capacity', start=0xC5D2, end=0xC66E,
                      count_call=0xC5F1, compare=0xC5F4, branch=0xC5F6, passed=0xC5F8,
                      pointer_refresh=0xC65E, sites=(0xC664, 0xC66C), pointer_y_store=0xC659),
                 dict(name='unaffiliated_recruitment_capacity', start=0xC6CC, end=0xC77F,
                      count_call=0xC6EA, compare=0xC6ED, branch=0xC6EF, passed=0xC6F1,
                      pointer_refresh=0xC772, sites=(0xC778, 0xC77F), pointer_y_store=0xC76D)]
        helper_ranges = [(11, 0xD105, 0xD12C), (11, 0xD69D, 0xD6CF), (11, 0xD283, 0xD2AA),
                         (11, 0xD471, 0xD493), (11, 0xC66F, 0xC6C9), (31, 0xE89A, 0xE8A9), (31, 0xF266, 0xF26C)]
        helpers = []
        for bank, start, end in helper_ranges:
            original_rows = [self.raw(k) for k in sorted(self.known) if k[0] == bank and start <= k[1] <= end]
            helpers.append(dict(physical_bank=bank, entry_cpu=start, end_cpu=end, original_instructions=original_rows,
                SRAM_write_contract='Only selected city offsets2,3,4,5 for D69D; all remaining writes in these helpers are RAM/stack/mapper, never a real-city roster.'))
        guarded, catalog = {}, []
        for spec in specs:
            nodes, successors, dom, incoming = self.local_region(spec['start'], spec['end'])
            for pc in spec['sites']:
                assert {(11, spec[k]) for k in ('count_call', 'compare', 'branch', 'passed', 'pointer_refresh')} <= dom[11, pc]
            assert self.known[11, spec['count_call']]['operand'] == 0xD304
            assert bytes.fromhex(self.known[11, spec['compare']]['raw_hex']) == b'\xC9\x0A'
            assert self.known[11, spec['branch']]['op'] == 'BCS'
            # Slice every path after the accepted edge that can reach the sites.
            forward, queue = set(), [(11, spec['passed'])]
            while queue:
                key = queue.pop()
                if key not in forward:
                    forward.add(key); queue.extend(successors[key])
            backwards, queue = set(), [(11, pc) for pc in spec['sites']]
            while queue:
                key = queue.pop()
                if key not in backwards:
                    backwards.add(key); queue.extend(p for p in nodes if key in successors[p])
            middle = forward & backwards
            stores, callees = [], set()
            for key in sorted(middle):
                row = self.known[key]
                if row['op'] == 'JSR': callees.add(base.mapped(key, row['operand']))
                if row['op'] not in base.WRITES or row['mode'] == 'a': continue
                if row['mode'] in ('iy', 'ix'):
                    assert key[1] in (spec['pointer_y_store'], spec['sites'][1])
                    reason = 'Officers begin63C0; actual status-offset11 write is outside all real30city rosters.' if key[1] == spec['pointer_y_store'] else 'Final firstFF append; happens only after the bound has selected the vacancy.'
                else:
                    addresses = old.direct_addresses(row)
                    assert addresses is not None and not any(0x6000 <= a < 0x63C0 for a in addresses)
                    assert 0x36 not in {base.normalized_ram(a) for a in addresses}
                    reason = 'Full raw-index/16-bit-wrap direct destination domain is disjoint from real30cities and does not change currentcity0036.'
                stores.append(dict(**self.raw(key), role=reason))
            permitted = {(31, 0xF266), (31, 0xE89A), (11, 0xD471), (11, 0xD283), (11, 0xC66F), (11, 0xD105)}
            assert callees <= permitted, callees
            proof = dict(schema='phase22-original-capacity-unchanged-firstFF-v1', name=spec['name'],
                physical_bank=11, original_entry_cpu=spec['start'], count_call=self.raw((11, spec['count_call'])),
                compare=self.raw((11, spec['compare'])), reject_branch=self.raw((11, spec['branch'])),
                passed_edge_cpu=spec['passed'], guarded_access_cpus=list(spec['sites']),
                incoming_trusted_edges=[dict(source=self.raw(a), target_cpu=b[1]) for a, b in incoming],
                required_dominator_cpus=[spec[k] for k in ('count_call', 'compare', 'branch', 'passed', 'pointer_refresh')],
                original_middle_instructions=[self.raw(k) for k in sorted(middle)],
                original_stores_and_roles=stores, actual_local_callees=[dict(physical_bank=b, cpu=p) for b, p in sorted(callees)],
                helper_write_contracts=helpers,
                count_prefix_instructions=[self.raw(k) for k in sorted(self.known) if k[0] == 11 and 0xD304 <= k[1] <= 0xD318],
                argument='D304 inspects offsets17..26 untilFF or ten entries. A<10 proves a currentFF within17..26. Every trusted path to the four sites passes that accepting edge. Between it and the final read/append, city0036 is unchanged and no real30city roster byte is written. The subsequent D105 reloads that same city pointer. Hence the same vacancy is still in17..26. Rawcity IDs30..255 have base>=63C0, so even unknownY0..255 cannot intersect the target city area.',
                scope='Ordinary no-interrupt/no-external-mutation execution through the original guarded entry, within the frozen trusted-CFG/helper contracts. Bare suffix entry is not covered; the original raw suffix can still read/write tail/nextcity bytes. Not a guarantee of termination or arbitrary raw control entry.')
            catalog.append(proof)
            for pc in spec['sites']:
                alternatives = [dict(case='real30city_guarded_vacancy', raw_city_ID_values=list(range(30)),
                        whole_pointer_values=list(range(0x6000, 0x63C0, 32)), Y_values=list(range(17, 27))),
                    dict(case='raw_noncity_ID_no_city_address', raw_city_ID_values=list(range(30, 256)),
                        whole_pointer_values=list(range(0x63C0, 0x8000, 32)), Y_values=list(range(256)))]
                for item in alternatives:
                    item['possible_auxiliary_effective_addresses'] = old.old.actual_auxiliary_intersection(item)
                    item['auxiliary_address_intersection_count'] = len(item['possible_auxiliary_effective_addresses'])
                    assert not item['possible_auxiliary_effective_addresses']
                flat = dict(whole_pointer_values=list(range(0x6000, 0x8000, 32)), Y_values=list(range(256)))
                guarded[11, pc] = dict(whole_pointer_values=flat['whole_pointer_values'], whole_pointer_count=256,
                    Y_values=flat['Y_values'], Y_was_unknown=True,
                    pointer_index_relation='explicit_original_guarded_disjunction', address_cases=alternatives,
                    independent_projection_auxiliary_intersection_count=len(old.old.actual_auxiliary_intersection(flat)),
                    possible_auxiliary_effective_addresses=[], auxiliary_address_intersection_count=0,
                    may_write_zero_page=False, may_write_stack_RAM_mirror=False,
                    origins=[dict(**self.raw((11, spec['count_call'])), origin_kind='original_capacity_guard_and_preserved_vacancy')],
                    required_execution_contract=dict(path='analysis/phase22/fields-static/guarded-roster-contracts.json', name=spec['name'],
                        original_entry_cpu=spec['start'], intervening_interrupts_or_external_mutation=False,
                        bare_suffix_entry_covered=False))
        return catalog, guarded

    def contract(self, key):
        if hasattr(self, 'guarded_sites') and key in self.guarded_sites: return self.guarded_sites[key]
        return super().contract(key)


def table_inventory(rom):
    tables, inputs = [], []
    def normalize(row, path, location):
        bank = row.get('physical_bank', row.get('bank'))
        pc = row.get('cpu_start', row.get('cpu_address', row.get('cpu')))
        raw = row.get('raw_hex')
        if bank is None or pc is None or not isinstance(raw, str): return
        bank = int(bank, 0) if isinstance(bank, str) else bank
        pc = int(pc, 0) if isinstance(pc, str) else pc
        data = bytes.fromhex(raw); offset = base.original(bank, pc)
        assert rom[offset:offset + len(data)] == data, (path, location)
        if not data: return
        tables.append(dict(path=path, source_sha256=base.digest(ROOT / path), JSON_location=location,
            name=row.get('name', row.get('domain', location)), physical_bank=bank, cpu_start=pc,
            rom_offset=offset, byte_count=len(data), raw_hex=data.hex(' ').upper(),
            scope='An explicit immutable-table/data contract in this archived evidence, not a prohibition of every hypothetical alternate CPU entry.'))
    for path in sorted((ROOT / 'analysis').glob('phase*/**/evidence.json')):
        if any(p.startswith('exploratory') or p in ('runtime', 'runtime-repeat', 'cpu', 'fields-static', 'access-runtime', 'provenance') for p in path.parts): continue
        stage = path.relative_to(ROOT / 'analysis').parts[0]
        if not stage[5:].isdigit() or int(stage[5:]) > 21: continue
        record = json.loads(path.read_text()); found = False
        for key in ('tables', 'immutable_tables', 'dispatch_tables'):
            values = record.get(key)
            if isinstance(values, list):
                for i, row in enumerate(values):
                    if isinstance(row, dict):
                        old_len = len(tables); normalize(row, str(path.relative_to(ROOT)), f'{key}[{i}]'); found |= len(tables) != old_len
        if found: inputs.append(str(path.relative_to(ROOT)))
    controls_path = 'analysis/phase18/control/control-contracts.json'
    controls = base.read(controls_path)
    for family in ('bounded_dispatch_tables', 'global_tables'):
        for i, row in enumerate(controls[family]): normalize(row['table'], controls_path, f'{family}[{i}].table')
    source = 'analysis/phase21/recruitment/static-catalog.json'
    for i, row in enumerate(base.read(source)['original_ranges']):
        if i not in (0, 2): normalize(row, source, f'original_ranges[{i}]')
    return tables, sorted(set(inputs + [controls_path, source]))


def raw_window_ledger(engine, tables):
    windows = base.read('analysis/phase21/fields-static/untrusted-PRG-opcode-windows.json')['windows']
    interiors, starts = {}, {}
    for key, row in engine.known.items():
        starts.setdefault(row['rom_offset'], []).append(key)
        for n in range(1, row['size']): interiors.setdefault(row['rom_offset'] + n, []).append((key, n))
    rows = []
    for previous in windows:
        row = dict(previous); offset = row['rom_offset']
        cover = [dict(path=t['path'], source_sha256=t['source_sha256'], JSON_location=t['JSON_location'], name=t['name'], rom_offset=t['rom_offset'], byte_count=t['byte_count'])
                 for t in tables if t['rom_offset'] <= offset and offset + 3 <= t['rom_offset'] + t['byte_count']]
        operand = [dict(instruction=engine.raw(k), interior_byte_offset=n) for k, n in interiors.get(offset, ())]
        assert offset not in starts
        category = 'trusted_operand_and_declared_data' if operand and cover else 'trusted_instruction_operand_no_proved_alternate_entry' if operand else 'declared_ROM_data_no_proved_instruction_entry' if cover else 'unresolved_raw_window_no_proved_control_entry'
        row.update(phase22_executability_category=category, trusted_operand_coverings=operand,
            archived_data_contract_coverings=cover, trusted_instruction_entry_at_start=False,
            promoted_to_executable_code=False, dedicated_field_semantics_confirmed=False,
            limits='No original trusted CFG edge enters this raw start. Operand/table overlap accounts for its current provenance, but does not prove impossible execution under unparsed external/computed entries or arbitrary mapper states.')
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('rom'); args = parser.parse_args()
    rom = Path(args.rom).read_bytes(); assert hashlib.sha256(rom).hexdigest() == base.ROM_SHA256
    assert base.digest(ROOT / 'analysis/phase21/verification.json') == OLD_AUDIT
    assert base.digest(ROOT / 'build/三国志2超级版-逆向分析-v21.zip') == OLD_ZIP
    engine = Analysis(rom)
    print('new scalar-index prefix contracts', len(engine.scalar_prefixes), flush=True)
    for round_number in range(3):
        engine.prove_returns(); engine.steps, engine.copies, engine.copy_details = 0, set(), {}
        engine.states, engine.queue, engine.scheduled = {}, deque(), set()
        roots, fallback = engine.run()
        added = engine.refine_write_effects() if round_number < 2 else None
        engine.refinement_rounds.append(dict(round=round_number + 1, original_instruction_transfers=engine.steps,
            new_non_ZP_store_proofs=added, return_contract_count=len(engine.return_contracts)))
        if not added: break
    previous = base.read('analysis/phase21/fields-static/all-indirect-accesses.json')['accesses']
    rows = []
    for before in previous:
        key = before['physical_bank'], before['cpu']; candidate = engine.contract(key); prior = before['address_contract']
        new_disjoint = candidate is not None and not auxiliary_intersection(candidate)
        prior_disjoint = before['classification'] == DISJOINT
        if prior_disjoint: assert prior is not None and not auxiliary_intersection(prior)
        authority = candidate if new_disjoint or not prior_disjoint and candidate is not None else prior
        inherited = authority is prior
        disjoint = authority is not None and not auxiliary_intersection(authority)
        classification = DISJOINT if disjoint else 'possible_city_auxiliary_alias' if authority else 'unresolved_pointer_or_index_contract'
        row = dict(before); row.update(classification=classification, address_contract=authority,
            address_scope='Logical effective data address; excludes addressing-mode dummy bus reads and instruction/pointer fetches.',
            whole_pointer_values=sorted(projection_words(authority)) if authority else None,
            Y_values=projection_Y(authority) if authority else before['Y_values'],
            phase21_classification=before['classification'], phase21_newly_disjoint=before['newly_proved_disjoint'],
            newly_proved_disjoint=disjoint and not prior_disjoint,
            proof_basis='phase22_guarded_pointer_index_disjunction' if key in engine.guarded_sites else 'frozen_phase21_authoritative_contract' if inherited else 'phase22_scalar_index_prefix_context' if authority else 'unresolved_context',
            authoritative_contract_origin=dict(path='analysis/phase21/fields-static/all-indirect-accesses.json', sha256=base.digest(ROOT / 'analysis/phase21/fields-static/all-indirect-accesses.json'),
                physical_bank=key[0], cpu=key[1], contract_field='address_contract') if inherited and authority else None,
            candidate_address_contract=candidate if inherited else prior,
            candidate_whole_pointer_values=sorted(projection_words(candidate if inherited else prior)) if (candidate if inherited else prior) else None,
            candidate_Y_values=projection_Y(candidate if inherited else prior) if (candidate if inherited else prior) else None,
            candidate_contract_is_authoritative=False,
            authoritative_pointer_representation='explicit_guarded_pointer_index_cases' if authority and 'address_cases' in authority else
                'complete_joint_address_set' if authority and 'whole_pointer_values' in authority else 'inherited_independent_low_high_Cartesian_domain' if authority else None)
        if authority:
            hit = auxiliary_intersection(authority)
            assert hit == authority['possible_auxiliary_effective_addresses'] and len(hit) == authority['auxiliary_address_intersection_count']
        rows.append(row)
    selected = [r for r in rows if r['phase17_remaining_candidate']]
    new = [r for r in rows if not r['phase17_instruction_access']]
    prior376 = [r for r in rows if r['phase21_classification'] != DISJOINT]
    remaining = [r for r in rows if r['classification'] != DISJOINT]
    tables, table_inputs = table_inventory(rom); raw = raw_window_ledger(engine, tables)
    dummy_rows = []
    for row in rows:
        proof = row['address_contract']
        hits = dummy_auxiliary_intersection(proof, row['op']) if proof else None
        dummy_rows.append(dict(physical_bank=row['physical_bank'], cpu=row['cpu'], rom_offset=row['rom_offset'], raw_hex=row['raw_hex'],
            logical_classification=row['classification'], operation=row['op'],
            dummy_auxiliary_bus_addresses=hits, dummy_auxiliary_intersection_count=len(hits) if hits is not None else None,
            classification='possible_dummy_auxiliary_bus_read' if hits else 'proved_no_dummy_auxiliary_bus_address_in_contract' if hits is not None else 'unresolved_pointer_or_index_contract',
            instruction_result_uses_dummy_value=False, logical_contract_changed=False,
            scope='Original IndY_R takes an uncorrected-page read only on carry; IndY_W reads the uncorrected page before every store. This is a separate conservative bus-address domain, not a semantic field consumer or an observation.'))
    source_path = 'analysis/phase21/runtime/core-provenance/upstream/source/core/NstCpu.cpp'
    source_lines = (ROOT / source_path).read_text().splitlines()
    first_line = next(i for i, line in enumerate(source_lines) if 'uint Cpu::IndY_R()' in line)
    last_line = next(i for i in range(first_line + 1, len(source_lines)) if '// relative addressing' in source_lines[i])
    save('logical-vs-dummy-bus-contracts.json', dict(schema='phase22-effective-data-and-uncorrected-bus-address-contracts-v1',
        original_emulator_source_path=source_path, original_emulator_source_sha256=base.digest(ROOT / source_path),
        first_source_line=first_line + 1, last_source_line=last_line + 1, original_source_excerpt='\n'.join(source_lines[first_line:last_line+1]) + '\n',
        access_count=len(dummy_rows), classification_counts=dict(Counter(r['classification'] for r in dummy_rows)), accesses=dummy_rows,
        scope='CPU/emulator addressing contracts, not native observations or source differential cases. A logical-disjoint row can have a dummy bus hit; no value from that dummy read is consumed by the instruction result.'))
    for filename, data in (('all-indirect-accesses.json', rows), ('access-contracts.json', selected), ('new-indirect-accesses.json', new), ('phase21-remaining376-handling.json', prior376), ('remaining-accesses.json', remaining)):
        save(filename, dict(schema='phase22-city-auxiliary-access-contracts-v1', ROM_sha256=base.ROM_SHA256, source_CPU_cases=0,
            access_count=len(data), classification_counts=dict(Counter(r['classification'] for r in data)), newly_proved_disjoint_count=sum(r['newly_proved_disjoint'] for r in data), accesses=data))
    save('guarded-roster-contracts.json', dict(schema='phase22-original-capacity-and-preserved-firstFF-contracts-v1', contracts=engine.guards))
    save('scalar-index-constructor-contracts.json', dict(schema='phase22-original-scalar-index-ROM-constructor-contracts-v1', contracts=engine.scalar_prefixes))
    save('declared-immutable-data-inventory.json', dict(schema='phase22-archived-original-immutable-data-contract-inventory-v1', contract_count=len(tables), contracts=tables))
    save('raw345-executability-ledger.json', dict(schema='phase22-raw-opcode-window-provenance-ledger-v1', window_count=len(raw), categories=dict(Counter(r['phase22_executability_category'] for r in raw)), windows=raw,
        limits='All345 original hypotheses retained. No new executable entry is asserted; trusted operand/data provenance and unresolved control domains remain distinct.'))
    summary = dict(schema='phase22-city-auxiliary-context-and-provenance-summary-v1', status='analyzed', ROM_sha256=base.ROM_SHA256,
        analyzer_path='scripts/analyze_city_auxiliary_phase22.py', analyzer_sha256=base.digest(__file__),
        artifact_sha256={p: base.digest(ROOT / p) for p in dict.fromkeys(INPUTS + table_inputs)},
        old_phase21_audit_sha256=OLD_AUDIT, old_v21_preserved_sha256=OLD_ZIP,
        source_CPU_cases=0, trusted_original_instruction_count=len(engine.known), original_instruction_byte_comparisons=engine.raw_checked,
        scalar_index_constructor_count=len(engine.scalar_prefixes), guarded_roster_contract_count=len(engine.guards),
        finite_refinement_rounds=engine.refinement_rounds, complete_analysis_fixed_point_proven=False,
        all_indirect_access_count=len(rows), baseline_candidate_count=len(selected), new_indirect_access_count=len(new),
        all_indirect_classification_counts=dict(Counter(r['classification'] for r in rows)), classification_counts=dict(Counter(r['classification'] for r in selected)), new_indirect_classification_counts=dict(Counter(r['classification'] for r in new)),
        phase21_remaining_count=len(prior376), remaining_access_count=len(remaining), newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint'] for r in rows),
        newly_disjoint_guarded_access_count=sum(r['newly_proved_disjoint'] and (r['physical_bank'], r['cpu']) in engine.guarded_sites for r in rows),
        newly_disjoint_scalar_context_access_count=sum(r['newly_proved_disjoint'] and (r['physical_bank'], r['cpu']) not in engine.guarded_sites for r in rows),
        dummy_bus_domain_classification_counts=dict(Counter(r['classification'] for r in dummy_rows)),
        logical_disjoint_sites_with_possible_dummy_auxiliary_read=sum(r['logical_classification'] == DISJOINT and bool(r['dummy_auxiliary_bus_addresses']) for r in dummy_rows),
        raw_window_count=len(raw), raw_window_categories=dict(Counter(r['phase22_executability_category'] for r in raw)),
        declared_immutable_data_contract_count=len(tables), official_target_field_names=dict(city_plus1=None, city_plus28=None, city_plus29=None, city_plus30=None, city_plus31=None),
        limitations=['No official name/unused/reserved/padding assertion from zeros or bounded nonobservation.',
            'The firstFF relation is guarded and no-interrupt; naked suffix aliases remain real outside that entry contract.',
            'For guarded rows, the independent top-level projection intersects150 target bytes; the explicit original guard-conditioned address_cases have intersection0. Candidates are nonauthoritative.',
            'Effective data-address disjointness does not imply absence of dummy bus reads. The latter have a separate1526-site ledger tied to the unchanged original IndY_R/IndY_W implementation.',
            'Raw opcode operand/data overlap is current provenance, not a theorem forbidding all unknown external/computed CPU entries.',
            'Scalar prefix narrowing uses all raw byte inputs and exact operations; no raw selector is silently restricted to seven rulers or thirty cities.',
            'Finite three-round proof strengthening does not claim complete global fixed-point or whole-ROM reachability.'])
    save('analysis-summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('scalar_index_constructor_count','all_indirect_classification_counts','remaining_access_count','newly_proved_disjoint_all_count','raw_window_categories')}, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
