#!/usr/bin/env python3
"""Independent original-CPU roster-address contracts; zero Source/Native cases."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_postbattle_roster_contracts_phase31 as model
from py65.devices.mpu6502 import MPU

OUT = model.OUT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ContractBus:
    """Original RAM/SRAM/PRG and mapper writes; no invented hardware inputs."""
    def __init__(self, rom, data_bank=5):
        self.rom = rom
        self.ram = bytearray(2048)
        self.sram = bytearray([255]) * 8192
        self.banks = [data_bank, 8, 9, 31]
        self.mapper_writes = []
        self.writes = []

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
            return self.rom[16 + bank * 8192 + (address & 8191)]
        raise RuntimeError(f'Explicit hardware input unavailable:{address:04X}')

    def __setitem__(self, address, value):
        address &= 65535
        value &= 255
        if address < 8192:
            before = self.ram[address & 2047]
            self.ram[address & 2047] = value
            self.writes.append(dict(address=address, normalized_address=address & 2047,
                                    before=before, value=value, after=self.ram[address & 2047]))
            return
        if 0x6000 <= address < 0x8000:
            before = self.sram[address - 0x6000]
            self.sram[address - 0x6000] = value
            self.writes.append(dict(address=address, normalized_address=address,
                                    before=before, value=value, after=self.sram[address - 0x6000]))
            return
        if address in (0xE000, 0xE800, 0xF000):
            window = {0xE000: 0, 0xE800: 1, 0xF000: 2}[address]
            self.banks[window] = value & 31
            self.mapper_writes.append(dict(address=address, value=value, physical_bank=value & 31))
            return
        raise RuntimeError(f'Unsupported original hardware write:{address:04X}')


def seed_return(memory, registers, return_pc=0x9000):
    memory[0x100 + ((registers['sp'] + 1) & 255)] = (return_pc - 1) & 255
    memory[0x100 + ((registers['sp'] + 2) & 255)] = (return_pc - 1) >> 8
    return return_pc


def base_registers(entry, sp=253):
    return dict(pc=entry, a=83, x=91, y=57, p=0x20, sp=sp)


def full_fixture(rom, city, ruler, mode, side, scenario):
    memory = ContractBus(rom, data_bank=(city * 3 + ruler) & 31)
    memory[0x504] = side
    memory[0x507] = (ruler << 4) | ruler
    memory[0x50E] = city
    memory[0x52A] = (city + 13) % 30
    memory[0x52B] = 52
    memory[0x52C] = 255
    memory[0x54] = (city * 7 + ruler) & 255
    memory[0x6F91] = mode
    for index in range(7):
        memory[0x6F07 + index * 8] = 10 + index
    for slot in range(20):
        memory[0x628 + slot] = 255
        memory[0x664 + slot] = 255
    for index in range(40):
        memory[0x6F47 + index] = 255
    occupied = {'empty': 0, 'partial': 1, 'almost_full': 9, 'full': 10, 'mixed': None}[scenario]
    for target in range(30):
        address = 0x6000 + 32 * target
        memory[address] = ruler if target & 1 else 7
        count = occupied if occupied is not None else (0, 1, 9, 10)[target & 3]
        for index in range(10):
            memory[address + 17 + index] = (140 + index + target) % 237 if index < count else 255
        for offset in (1, 28, 29, 30, 31):
            memory[address + offset] = (target * 13 + offset) & 255
    # The collector walks both halves in a side-dependent order. IDs are
    # legitimate record indices; no result, request or ready byte is prepared.
    first = 10 if side & 128 else 0
    other = 0 if first else 10
    for index in range(10):
        slot = first + index
        memory[0x628 + slot] = side
        memory[0x664 + slot] = 50 + index
    for index in range(6):
        slot = other + index
        memory[0x628 + slot] = side
        memory[0x664 + slot] = 70 + index
    cap_base = 0x6F5B if side & 128 else 0x6F47
    for index in range(4):
        memory[cap_base + index] = 90 + index
    registers = base_registers(0xBC46, sp=250 if city & 1 else 253)
    stop = seed_return(memory, registers)
    memory.writes.clear()
    return memory, registers, stop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == model.ROM_SHA
    assert sha(ROOT / 'analysis/phase30/verification.json') == model.BASE_AUDIT
    summary = model.read('analysis/phase31/fields-static/analysis-summary.json')
    proof = model.read('analysis/phase31/fields-static/roster-write-lifecycle-contract.json')
    for group in ('source_and_validator_sha256', 'artifact_sha256'):
        for path, digest in summary[group].items():
            assert sha(ROOT / path) == digest, ('stale analyzer/input', path)
    prior = model.read('analysis/phase30/fields-static/all-indirect-accesses.json')['accesses']
    rows = model.read('analysis/phase31/fields-static/all-indirect-accesses.json')['accesses']
    by = {(row['physical_bank'], row['cpu']): row for row in rows}
    counts, visits, call_witnesses, y_witnesses = Counter(), Counter(), Counter(), Counter()
    cases, checks, bare, swaps, raw_alias = [], [], [], [], []
    authority = model.address_contract()

    def check(name, condition):
        assert condition, name
        checks.append(dict(name=name, passed=True))

    def execute(memory, registers, stop, tag, kind, *, typed=True, parent=False):
        cpu = MPU(memory=memory)
        for key, value in registers.items():
            setattr(cpu, key, value)
        before = bytes(memory.sram)
        stores, calls, escape_pending, scans = [], [], [], []
        for steps in range(50000):
            if steps and cpu.pc == stop:
                break
            assert cpu.pc >= 0x8000, (tag, 'unexpected PC', cpu.pc)
            bank = memory.banks[(cpu.pc - 0x8000) // 8192]
            visits[bank, cpu.pc] += 1
            opcode_pc, sp_before, write_start = cpu.pc, cpu.sp, len(memory.writes)
            if bank == 8 and cpu.pc == 0xBE6B:
                scans.append(dict(Y=cpu.y, address=0x6FA1 + cpu.y, value=memory[0x6FA1 + cpu.y]))
            if bank == 8 and cpu.pc == 0xBEC2:
                assert memory.banks[0] == 16, (tag, 'BE90 adjacency bank', memory.banks)
            if bank == 8 and cpu.pc in dict(model.CALLS):
                call = dict(call_PC=cpu.pc, return_PC=cpu.pc + 3, SP=cpu.sp,
                            city02=memory[2], raw03=memory[3], raw04=memory[4])
                expected = {0xBC65: [17], 0xBD8E: list(range(17, 27)),
                            0xBC8E: list(range(18, 27)), 0xBCC9: [17]}[cpu.pc]
                assert memory[3] in expected, (tag, call)
                calls.append(call)
                call_witnesses[cpu.pc] += 1
            if bank == 8 and cpu.pc == 0xBDB8:
                pointer = memory[0] | (memory[1] << 8)
                address = (pointer + cpu.y) & 65535
                raw_return = memory[0x100 + ((cpu.sp + 1) & 255)] | (memory[0x100 + ((cpu.sp + 2) & 255)] << 8)
                store = dict(pointer00=pointer, Y=cpu.y, address=address, value=cpu.a,
                             city02=memory[2], raw03=memory[3], raw04=memory[4], X=cpu.x,
                             SP=cpu.sp, raw_stacked_return=raw_return)
                assert pointer == 0x6000 + 32 * memory[2], (tag, store)
                if typed:
                    assert cpu.y in authority['Y_values'] and address not in model.AUX, (tag, store)
                assert cpu.a == memory[0x6FA1 + cpu.x], (tag, 'not live list value', store)
                if parent:
                    assert raw_return in {call + 2 for call, _ in model.CALLS}, (tag, store)
                stores.append(store)
                y_witnesses[cpu.y] += 1
            cpu.step()
            if bank == 8 and opcode_pc in (0xBDB0, 0xBDB4, 0xBDB7, 0xBDB8):
                event = dict(instruction_index=steps, PC=opcode_pc, SP_before=sp_before,
                             SP_after=cpu.sp, writes=memory.writes[write_start:])
                if opcode_pc != 0xBDB8:
                    escape_pending.append(event)
                else:
                    store = stores[-1]
                    assert len(event['writes']) == 1
                    actual = event['writes'][0]
                    assert actual['address'] == store['address'] and actual['value'] == store['value']
                    store['observed_write'] = actual
                    if escape_pending:
                        assert [item['PC'] for item in escape_pending] == [0xBDB0, 0xBDB4, 0xBDB7]
                        assert escape_pending[0]['SP_after'] == (escape_pending[0]['SP_before'] - 1) & 255
                        assert escape_pending[2]['SP_after'] == escape_pending[0]['SP_before'] == event['SP_before']
                        assert len(escape_pending[1]['writes']) == 1
                        assert escape_pending[1]['writes'][0]['address'] == 0x52C
                        assert escape_pending[1]['writes'][0]['value'] == store['city02']
                        store['escape_protocol'] = escape_pending + [event]
                        escape_pending = []
                    else:
                        store['escape_protocol'] = None
        else:
            raise RuntimeError((tag, 'CPU budget', cpu.pc))
        assert cpu.sp == (registers['sp'] + 2) & 255, (tag, cpu.sp, registers['sp'])
        assert memory.banks[1:] == [8, 9, 31]
        # City auxiliaries are independently snapshotted for the complete
        # normal-city parent domain. General typedrawcity tests may alias
        # other SRAM workspaces; these are not declared unchanged globally.
        auxiliary_unchanged = all(memory[address] == before[address - 0x6000] for address in model.AUX)
        if parent:
            assert auxiliary_unchanged, (tag, 'auxiliary changed')
        counts[kind] += 1
        cases.append(dict(case=tag, comparison=kind, entry=registers['pc'], stop_PC=cpu.pc,
                          final_SP=cpu.sp, original_instructions=steps, selected_stores=stores,
                          actual_BD96_calls=calls, mapper_writes=memory.mapper_writes,
                          BE55_scan_reads=scans,
                          input_SRAM_sha256=hashlib.sha256(before).hexdigest(),
                          final_SRAM_sha256=hashlib.sha256(memory.sram).hexdigest(),
                          all150_auxiliary_bytes_unchanged=auxiliary_unchanged,
                          full_parent_auxiliary_assertion_required=parent, Source_compared=False))
        return stores

    # Structural theorem uses exact liveF2AF word; all256 rawcity values
    # are checked without declaring them all natural game city indices.
    for city in range(256):
        for start in range(17, 27):
            for pattern in ('empty', 'short', 'cap'):
                memory = ContractBus(rom)
                memory[2], memory[3], memory[4] = city, start, 0
                memory[0x52B] = 52
                count = {'empty': 0, 'short': 3, 'cap': 12}[pattern]
                for index in range(32):
                    memory[0x6FA1 + index] = 50 + index if index < count else 255
                registers = base_registers(0xBD96, sp=247 if city & 1 else 253)
                stop = seed_return(memory, registers)
                memory.writes.clear()
                execute(memory, registers, stop, f'typed-BD96/city{city}/start{start}/{pattern}',
                        'typed_BD96_actual_caller_RTS')

    # FullBC46 mode dispatch plus all original local/fixed helpers. This is
    # a prepared OriginalCPU caller matrix, not passiveNative evidence.
    for city in range(30):
        for ruler in range(7):
            for mode in range(3):
                for side in (0, 128):
                    for scenario in ('empty', 'partial', 'almost_full', 'full', 'mixed'):
                        memory, registers, stop = full_fixture(rom, city, ruler, mode, side, scenario)
                        execute(memory, registers, stop,
                                f'full-BC46/city{city}/ruler{ruler}/mode{mode}/side{side}/{scenario}',
                                'complete_BC46_actual_caller_RTS', parent=True)

    # Explicit precondition counterexamples: firstwrite is beforeCPY27.
    for start in (1, 27, 28, 29, 30, 31, 255):
        memory = ContractBus(rom)
        memory[2], memory[3], memory[4] = 0, start, 0
        memory[0x52B] = 255
        for index in range(40):
            memory[0x6FA1 + index] = 40 + index if index < 32 else 255
        registers = base_registers(0xBD96)
        stop = seed_return(memory, registers)
        memory.writes.clear()
        stores = execute(memory, registers, stop, f'bare-BD96/raw03-{start}',
                         'bare_BD96_counterexample_RTS', typed=False)
        assert stores and stores[0]['Y'] == start
        if start != 27:
            assert any(store['address'] in model.AUX for store in stores)
        else:
            assert stores[0]['address'] == 0x601B  # +27 is outside roster, not in targetaux150.
        bare.append(dict(raw03=start, stores=stores, complete_parent_contract_applies=False))

    # A nakedstore suffix can alias scratch, mirroredscratch or callerstack.
    # Each case ends after one realopcode, before a corruptedreturn is used.
    suffix = []
    for pointer, y, label in ((0, 3, 'scratch03'), (0, 4, 'cursor04'),
                              (0x0800, 3, 'RAM_mirror03'), (0x0100, 254, 'caller_stack'),
                              (0x6000, 1, 'city_aux1'), (0x6000, 28, 'city_aux28')):
        memory = ContractBus(rom)
        memory[0], memory[1] = pointer & 255, pointer >> 8
        cpu = MPU(memory=memory)
        cpu.pc, cpu.y, cpu.a = 0xBDB8, y, 73
        address = (pointer + y) & 65535
        visits[8, cpu.pc] += 1
        cpu.step()
        assert memory[address] == 73 and cpu.pc == 0xBDBA
        suffix.append(dict(label=label, entry=0xBDB8, pointer00=pointer, Y=y,
                           address=address, normalized_address=model.normal(address),
                           comparison='bare_BDB8_one_opcode_alias_prefix',
                           complete_parent_contract_applies=False))
        counts['bare_BDB8_one_opcode_alias_prefix'] += 1

    # Controlled nontrivial commanderprioritization: no Native claim.
    for index in (1, 9, 19):
        memory = ContractBus(rom)
        memory[0x504] = 0
        memory[0x664] = 97
        for position in range(20):
            memory[0x6FA1 + position] = 50 + position
        memory[0x6FA1 + index] = 97
        registers = base_registers(0xBE55)
        stop = seed_return(memory, registers)
        hole = 0 if index == 1 else 1
        memory[0x6FA1 + hole] = 255
        first, target = memory[0x6FA1], memory[0x6FA1 + index]
        execute(memory, registers, stop, f'controlled-BE55/swap{index}',
                'controlled_BE55_nontrivial_swap_RTS')
        assert memory[0x6FA1] == target and memory[0x6FA1 + index] == first and first != target
        reads = cases[-1]['BE55_scan_reads']
        assert any(row['Y'] == hole and row['value'] == 255 for row in reads)
        assert any(row['Y'] == index and row['value'] == target for row in reads)
        swaps.append(dict(index=index, earlier_FF_hole=hole, original_scan_reads=reads,
                          before=[first, target], after=[target, first], Native_observed=False))

    # Samevalue is still an actual STA. Escapehandler has real PHA/store/PLA
    # before the targetedstore, including an unchanged052C destination.
    memory = ContractBus(rom)
    memory[2], memory[3], memory[4] = 4, 17, 0
    memory[0x52B], memory[0x52C] = 52, 4
    memory[0x6FA1], memory[0x6FA2], memory[0x6FA3] = 52, 60, 255
    memory[0x6000 + 32 * 4 + 17] = 52
    registers = base_registers(0xBD96)
    stop = seed_return(memory, registers)
    memory.writes.clear()
    same = execute(memory, registers, stop, 'controlled-BD96/escape-samevalue',
                   'controlled_BD96_escape_same_value_RTS')
    assert same[0]['observed_write']['before'] == same[0]['observed_write']['after'] == 52
    assert [event['PC'] for event in same[0]['escape_protocol']] == [0xBDB0, 0xBDB4, 0xBDB7, 0xBDB8]
    escape_write = same[0]['escape_protocol'][1]['writes'][0]
    assert escape_write['before'] == escape_write['after'] == 4

    # Rawcity125 is not a validfullparent city. With03=18/04=16, the first
    # store replaces the NEXT listentryFF, which the following iteration
    # reallyreads. This demonstrates livealias, not merely overlappingranges.
    memory = ContractBus(rom)
    memory[2], memory[3], memory[4] = 125, 18, 16
    memory[0x52B] = 255
    memory[0x6FA1 + 16] = 70
    memory[0x6FA1 + 17] = 255
    registers = base_registers(0xBD96)
    stop = seed_return(memory, registers)
    memory.writes.clear()
    aliased = execute(memory, registers, stop, 'controlled-rawcity125/future-FF-overwrite',
                      'controlled_rawcity125_live_future_alias_RTS')
    assert len(aliased) == 9
    assert aliased[0]['address'] == 0x6FA1 + 17
    assert aliased[0]['observed_write']['before'] == 255 and aliased[0]['observed_write']['after'] == 70
    assert aliased[1]['X'] == 17 and aliased[1]['value'] == 70
    raw_alias.append(dict(raw_city=125, raw03=18, raw04=16, complete_parent_contract_applies=False,
                          future_entry_before=255, first_store=aliased[0], next_iteration=aliased[1],
                          actual_store_count=9, nonalias_snapshot_list_would_stop_after_stores=1))

    check('7680typedBD96_all256rawcity10starts3listpatterns', counts['typed_BD96_actual_caller_RTS'] == 7680)
    check('6300completeBC46_30city7ruler3mode2side5occupancies', counts['complete_BC46_actual_caller_RTS'] == 6300)
    check('all_four_real_BD96_JSR_calls_reached', set(call_witnesses) == {call for call, _ in model.CALLS})
    check('all_ten_roster_Y_values_reached', set(range(17, 27)) <= set(y_witnesses))
    check('bare_raw03_precheck_store_counterexamples_retained', len(bare) == 7)
    check('raw255_wrap_reaches_city1_before_termination', any(store['Y'] == 1 for store in bare[-1]['stores']))
    check('bare_suffix_ZP_mirror_stack_city_aliases_real_opcodes', len(suffix) == 6)
    check('three_nontrivial_swaps_scan_past_real_FF_holes_controlled_notNative', len(swaps) == 3)
    check('real_PHA_052C_PLA_roster_store_and_samevalue_preserved', bool(same[0]['escape_protocol']))
    check('rawcity125_overwrites_future_FF_and_changes_actual_followup_read', len(raw_alias) == 1)
    check('all30_adjacency_rows_finite_and_normal_city_only', all(row['negative_terminator_index'] < 8 and all(x < 30 for x in row['candidate_cities']) for row in proof['adjacency_ROM']['rows']))
    check('F2AF_complete_original_only00_01_writes', {int.from_bytes(bytes.fromhex(row['raw_hex'])[1:], 'little') for row in proof['F2AF_complete_instructions'] if bytes.fromhex(row['raw_hex'])[0] in (0x8D, 0x8C, 0x2E)} == {0, 1})
    check('all256_aligned_words_times_Y17to26_logically_disjoint', not({model.normal((pointer + y) & 65535) for pointer in authority['whole_pointer_values'] for y in authority['Y_values']} & model.AUX))
    valid = dict(root=0xBC46, code_pair=[8, 9], mode=0, current_city=4, source_city=11,
                 rulers=[1, 2], complete_entry=True, binary=True, interrupted=False,
                 middle_entry=False, immutable_adjacency_table=True)
    check('complete_parent_premises_accept', model.admissible_context(valid))
    for key, value in (('root', 0xBD96), ('code_pair', [12, 13]), ('mode', 3),
                       ('current_city', 30), ('source_city', 30), ('rulers', [0, 8]),
                       ('complete_entry', False), ('binary', False), ('interrupted', True),
                       ('middle_entry', True), ('immutable_adjacency_table', False)):
        context = dict(valid)
        context[key] = value
        check('reject_missing_premise:' + key, not model.admissible_context(context))
    for previous, current in zip(prior, rows):
        key = (current['physical_bank'], current['cpu'])
        assert key == (previous['physical_bank'], previous['cpu'])
        if key == model.TARGET:
            assert current['address_contract'] == authority
            assert current['whole_pointer_values'] == authority['whole_pointer_values']
            assert current['Y_values'] == authority['Y_values']
        else:
            assert current['classification'] == previous['classification']
            assert current['address_contract'] == previous['address_contract']
    check('only_one_authority_changed_other1525_classifications_contracts_exact', True)
    for row in proof['original_instructions'] + proof['F2AF_complete_instructions']:
        index = model.off(row['physical_bank'], row['cpu'])
        raw = bytes.fromhex(row['raw_hex'])
        assert row['rom_offset'] == index and rom[index:index + len(raw)] == raw
    table = proof['adjacency_ROM']
    assert rom[table['rom_offset']:table['rom_offset'] + table['bytes']] == bytes.fromhex(table['raw_hex'])
    dispatch = proof['inline_table']
    raw = bytes.fromhex(dispatch['raw_hex'])
    assert rom[dispatch['rom_offset']:dispatch['rom_offset'] + len(raw)] == raw
    assert [raw[index] | (raw[index + 1] << 8) for index in range(0, 6, 2)] == [0xBC52, 0xBD59, 0xBD67]
    check('all_original_instructions_tables_plus16_bytes', True)
    check('raw345_exact_inherited_notnewcoverage', model.read('analysis/phase31/fields-static/raw345-executability-ledger.json') == model.read('analysis/phase30/fields-static/raw345-executability-ledger.json'))
    check('official_city_auxiliary_names_still_null', all(value is None for value in summary['official_city_auxiliary_names'].values()))
    sourcepins = {str(Path(__file__).relative_to(ROOT)): sha(__file__),
                  str(Path(model.__file__).relative_to(ROOT)): sha(model.__file__)}
    artifacts = dict(summary['artifact_sha256'])
    artifacts.update({str(path.relative_to(ROOT)): sha(path) for path in OUT.iterdir()
                      if path.is_file() and path.name not in ('verification.json', 'evidence.json', 'README.md')})
    complete = sum(value for key, value in counts.items() if key.endswith('_RTS'))
    prefix = sum(counts.values()) - complete
    (OUT / 'README.md').write_text(f'''# 完整BC46至BDB8：一个条件名单写入合同

选中仅physical8:BDB8 `STA($00),Y`。冻结30分母1526=1200条件不交/81可能/245未知，经独立原CPU合同后变为1201/80/245、候选326→325。城市+1/+28..31正式名仍为null；条件地址排除不是reserved、padding或unused命名。

完整BC46正常mode0/1/2、当前及来源城市0..29、ruler0..6、binary且无NMI/IRQ/外部mutation的生命周期下，四个真实JSR为BC65→BD96→BC68、BD8E→BD96→BD91、BC8E→BD96→BC91、BCC9→BD96→BCCC。其输入03分别17、17..26、18..26、17。BE90以原F25F30切physical16，30行原邻接表均在8字节内遇负值，之前只含0..29；输出占用计数限定0..10，首轮跳0/10，第二轮仅0。没有由旧源码变量名推域。

F2AF全部原指令只写00/01，完整生成6000+32×rawcity；不改live03/04。BD96返回前不再调用未知callee，Y从03起，每次写后才INY/CPY27。父链Y17..26因此只写十个名册槽。权威ptr保守放宽到全部256个F2AF word，仍与150个城市辅助地址不交；不据此把rawcity30..255叫正常城市。optional PHA/PLA用0100..01FF，052C在RAM且不碰00..04，正常城市/全部F2AF目标都不别名ZP或stack。rawcity125可别名6FA1工作区并改变值或终止，这不是本合同未考虑的独立内存；地址界仍由完整ptr/Y决定。

裸BD96原03=1/27..31/255的反例保持：第一个非FF项总先写再CPY27，255会绕回0并继续写到26。更裸的BDB8中段可直接写scratch03/04、0800镜像、callerstack或6001/601C，均有真实单opcode前缀。它们不套完整父入口合同。mode2来源满城保留04=BD的原行为没有清零或Xclamp。三个受控BE55非平凡换位只证明原CPU行为，不冒充Native现场。

本矩阵{sum(counts.values())}案，{complete}实际callerRTS、{prefix}明确裸后缀前缀，另{len(checks)}模型/原字节/前提检查。包括7680typedBD96构造callee、6300完整BC46准备caller、7裸BD96异常offset、6裸BDB8前缀、3个经过早先FF洞才命中commander的换位callee、1个escape同值写及1个rawcity125真实后续别名案。每次selectedstore从prestate到真实opcode后write均导出；optional路径保留PHA→052C实际写→PLA→BDB8的SP/先后，两个同值STA也没有按diff过滤。rawcity125/03=18/04=16首store把下一工作项FF改70，下一轮实际读70，导致9次store而不是静态列表1次；它只属于raw store-addresslemma，不扩大正常父链域。Source病例0、Native帧0，不执行生产Source或控制IR、不用helperRTS替身。Bus保留全2048RAM/8192SRAM，所有原local/fixedhelper逐指令执行；没有声称另一Source全RAM/AXYP/ports差分。py65逻辑地址观察不等完整dummy微周期，原STA dummy在硬件仍可能出现。

其余1525项分类和权威address_contract不改；raw345逐项继承104操作数/13数据/228未证控制，未增加动态覆盖或声称固定点。完整父链终止不作普遍定理，输入列表或裸别名仍可产生更长/循环行为。矩阵自身有预算，实际各例正常返回或明确前缀结束；无中断是合同前提，不是动态IRQ测试。

复现：`python3 scripts/analyze_postbattle_roster_contracts_phase31.py ROM`；`.venv-trace/bin/python scripts/verify_postbattle_roster_contracts_phase31.py ROM`。仅写新31目录，旧30及更早文件不改。
''')
    artifacts['analysis/phase31/fields-static/README.md'] = sha(OUT / 'README.md')
    result = dict(schema='phase31-original-roster-address-contract-validation-v1', status='passed',
                  failed_count=0, ROM_sha256=model.ROM_SHA, source_CPU_cases=0, Native_runs=0,
                  original_contract_CPU_cases=sum(counts.values()), counts=dict(counts),
                  actual_caller_RTS_CPU_cases=complete, explicit_prefix_CPU_cases=prefix,
                  model_guard_check_count=len(checks), model_checks=checks, case_rows=cases,
                  bare_BD96_counterexamples=bare, bare_BDB8_alias_prefixes=suffix,
                  controlled_nontrivial_swaps=swaps,
                  controlled_same_value_escape_protocol=same,
                  controlled_raw_city_future_aliases=raw_alias,
                  original_call_witness_counts={str(key): value for key, value in call_witnesses.items()},
                  selected_Y_witness_counts={str(key): value for key, value in y_witnesses.items()},
                  source_original_CPU_callbacks=0, source_and_validator_sha256=sourcepins,
                  artifact_sha256=artifacts,
                  executed_instruction_positions=[dict(physical_bank=bank, cpu=pc, count=count)
                                                   for (bank, pc), count in sorted(visits.items())],
                  newly_proved_disjoint_all_count=1, remaining_access_count=325,
                  all_indirect_classification_counts=summary['all_indirect_classification_counts'],
                  comparison_scope='OriginalCPU logical-address/pointer/Y/caller/order contract only; no independent Source/Native or dummy-cycle comparison.',
                  limits=proof['limits'])
    model.save('verification.json', result)
    model.save('evidence.json', dict(schema='phase31-roster-address-contract-evidence-v1',
        **{key: result[key] for key in ('status', 'ROM_sha256', 'source_CPU_cases', 'Native_runs',
            'original_contract_CPU_cases', 'counts', 'actual_caller_RTS_CPU_cases',
            'explicit_prefix_CPU_cases', 'model_guard_check_count', 'source_and_validator_sha256',
            'newly_proved_disjoint_all_count', 'remaining_access_count',
            'all_indirect_classification_counts', 'limits')},
        artifact_sha256=artifacts | {'analysis/phase31/fields-static/verification.json': sha(OUT / 'verification.json')}))
    print(json.dumps({key: result[key] for key in ('status', 'original_contract_CPU_cases', 'counts',
                                                  'model_guard_check_count', 'remaining_access_count')}))


if __name__ == '__main__':
    main()
