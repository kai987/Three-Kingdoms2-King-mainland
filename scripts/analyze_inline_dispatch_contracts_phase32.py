#!/usr/bin/env python3
"""Phase32 current-frame inline-dispatch address contracts; no CPU execution.

Only NEW phase32 artifacts are written. A Root-produced original-CPU receipt is
required before either inherited access classification can be promoted.
"""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase32/fields-static'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BASE_AUDIT_SHA = '717bc872656ca43617e20888a921951fa086634672a7bbbad1ac148a445341ac'
BASE_LEDGER = 'analysis/phase31/fields-static/all-indirect-accesses.json'
ATLAS = 'analysis/phase18/control/instruction-atlas.json'
SELECTED = ((8, 0xB525), (8, 0xB52B))
AUX = frozenset(0x6000 + city * 32 + offset for city in range(30)
                for offset in (1, 28, 29, 30, 31))
HELPER_HEX = '8C20000AA8C8688D2100688D2200B1218D2300C8B1218D2400AC20006C2300'
CALLS = {
    0xA09E: dict(name='actor_strategy', prologue=0xA099, raw_return=0xA0A0,
                 table_start=0xA0A1, table_end_exclusive=0xA0B1,
                 legal_indices=list(range(8))),
    0xACAB: dict(name='tactic_predicate', prologue=0xACAB, raw_return=0xACAD,
                 table_start=0xACAE, table_end_exclusive=0xACCE,
                 legal_indices=list(range(16))),
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def off(bank, pc):
    return 16 + bank * 8192 + (pc & 8191)


def normal(address):
    address &= 65535
    return address & 2047 if address < 8192 else address


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def model_transfer(rom, call_pc, index, original_y, caller_sp):
    """Closed-form arithmetic theorem, not an opcode interpreter or CPU run.

    `caller_sp` is the SP before the *actual* immutable JSR, not a synthetic
    B517 stack word. The corresponding Root test must execute that JSR.
    """
    info = CALLS[call_pc]
    raw_return = info['raw_return']
    first_y = ((index << 1) + 1) & 255
    second_y = (first_y + 1) & 255
    first_address = (raw_return + first_y) & 65535
    second_address = (raw_return + second_y) & 65535
    low = rom[off(8, first_address)]
    high = rom[off(8, second_address)]
    return dict(call_PC=call_pc, index=index, incoming_Y=original_y,
                caller_SP=caller_sp, after_JSR_SP=(caller_sp - 2) & 255,
                final_SP=caller_sp, pointer=raw_return,
                first_Y=first_y, second_Y=second_y,
                first_logical_address=first_address,
                second_logical_address=second_address,
                table_low=low, table_high=high, transfer_PC=low | high << 8,
                final_Y=original_y, legal_inline_index=index in info['legal_indices'],
                raw_outside_table_is_not_legal_strategy_or_predicate=index not in info['legal_indices'])


def admissible_context(context):
    """The conditional current-frame capability is deliberately not a PC tag."""
    call_pc = context.get('call_PC')
    return (call_pc in CALLS and context.get('code_pair') == [8, 9]
            and context.get('entry') == call_pc
            and context.get('actual_JSR_executed') is True
            and context.get('current_frame_unmodified') is True
            and context.get('stack_word_from_this_dynamic_JSR') is True
            and context.get('no_external_or_interrupt_mutation') is True
            and context.get('bare_or_middle_entry') is False
            and context.get('original_code_and_inline_data') is True)


def address_contract(cpu):
    ys = list(range(1, 256, 2)) if cpu == 0xB525 else list(range(0, 256, 2))
    cases = []
    for call_pc, info in CALLS.items():
        pointer = info['raw_return']
        addresses = sorted({normal(pointer + y) for y in ys})
        overlap = sorted(set(addresses) & AUX)
        cases.append(dict(call_PC=call_pc, whole_pointer_values=[pointer], Y_values=ys,
                          logical_effective_addresses=addresses,
                          auxiliary_addresses=overlap,
                          auxiliary_address_intersection_count=len(overlap),
                          premise='This dynamic original JSR establishes the still-intact current frame; no interruption or middle entry.'))
    pointers = sorted(info['raw_return'] for info in CALLS.values())
    flat = sorted({normal(pointer + y) for pointer in pointers for y in ys} & AUX)
    assert not flat
    return dict(whole_pointer_values=pointers, whole_pointer_count=len(pointers),
                Y_values=ys, address_cases=cases,
                auxiliary_address_intersection_count=0,
                possible_auxiliary_effective_addresses=[],
                top_level_projection_auxiliary_intersection_count=len(flat),
                authority='Complete current dynamic JSR A09E or ACAB through B517, not bare B517/B525/B52B.',
                raw_index_domain=list(range(256)),
                valid_inline_target_domain_separate=True,
                logical_effective_address_only=True,
                no_full_game_or_interrupt_closure_claim=True)


def original_inventory(rom):
    atlas = read(ATLAS)
    instructions = atlas['instructions']
    predicate_callers = []
    by = {(row['physical_bank'], row['cpu']): row for row in instructions}
    for row in instructions:
        if row['physical_bank'] == 8 and row['op'] == 'JSR' and row.get('operand') == 0xAC7B:
            prefix = by[8, row['cpu'] - 2]
            assert prefix['op'] == 'LDX' and prefix['mode'] == 'im' and prefix['operand'] in range(16)
            predicate_callers.append(dict(prefix_entry=prefix['cpu'], input_X=prefix['operand'],
                call_PC=row['cpu'], target_PC=0xAC7B,
                prefix_raw_hex=prefix['raw_hex'] + ' ' + row['raw_hex'],
                rom_offset=off(8, prefix['cpu']), bytes=5,
                scope='Only complete adjacent immediate-LDX/JSR prefix; not a middle-call or whole-game closure assertion.'))
    assert len(predicate_callers) == 14
    extra = {item['prefix_entry'] for item in predicate_callers} | {item['call_PC'] for item in predicate_callers}
    selected = []
    for row in instructions:
        include = (row['physical_bank'] == 8 and (0xB517 <= row['cpu'] < 0xB536
                or 0xA099 <= row['cpu'] <= 0xA09E or 0xAC7B <= row['cpu'] <= 0xACAB
                or 0xB6E5 <= row['cpu'] <= 0xB74A or row['cpu'] in extra))
        include |= row['physical_bank'] == 31 and 0xF266 <= row['cpu'] < 0xF26D
        if include:
            item = {key: row[key] for key in ('physical_bank', 'cpu', 'rom_offset', 'op', 'mode', 'size', 'operand', 'raw_hex')}
            assert item['rom_offset'] == off(item['physical_bank'], item['cpu'])
            assert rom[item['rom_offset']:item['rom_offset'] + item['size']] == bytes.fromhex(item['raw_hex'])
            selected.append(item)
    helper = sorted((row for row in selected if row['physical_bank'] == 8 and 0xB517 <= row['cpu'] < 0xB536), key=lambda row: row['cpu'])
    assert helper[0]['cpu'] == 0xB517 and helper[-1]['cpu'] == 0xB533
    assert all(left['cpu'] + left['size'] == right['cpu'] for left, right in zip(helper, helper[1:]))
    assert b''.join(bytes.fromhex(row['raw_hex']) for row in helper) == bytes.fromhex(HELPER_HEX)
    callers = [row for row in instructions if row['physical_bank'] in (8, 9)
               and row['op'] in ('JSR', 'JMP') and row.get('operand') == 0xB517]
    assert {(row['physical_bank'], row['cpu'], row['op']) for row in callers} == {(8, pc, 'JSR') for pc in CALLS}
    for call_pc in CALLS:
        assert rom[off(8, call_pc):off(8, call_pc) + 3] == bytes.fromhex('20 17 B5')
    tables = []
    for call_pc, info in CALLS.items():
        start, end = info['table_start'], info['table_end_exclusive']
        raw = rom[off(8, start):off(8, end)]
        words = [int.from_bytes(raw[index:index + 2], 'little') for index in range(0, len(raw), 2)]
        assert len(words) == len(info['legal_indices'])
        assert all(0xA000 <= target < 0xC000 for target in words)
        for index, target in enumerate(words):
            assert model_transfer(rom, call_pc, index, 17, 253)['transfer_PC'] == target
        tables.append(dict(physical_bank=8, call_PC=call_pc, cpu=start, end_exclusive=end,
                           rom_offset=off(8, start), bytes=len(raw), raw_hex=raw.hex(' ').upper(),
                           targets=words, legal_indices=info['legal_indices']))
    terrain = [row for row in selected if row['physical_bank'] == 8 and 0xB6E5 <= row['cpu'] <= 0xB74A]
    assert {row['operand'] for row in terrain if row['op'] == 'JSR'} == {0xB6EF, 0xF266}
    assert all(row['mode'] == 'ab' and row['operand'] in (0x22, 0x23, 0x24, 0x25, 0x26)
               for row in terrain if row['op'] in ('STA', 'STX', 'STY'))
    assert all(row['op'] not in ('INC', 'DEC', 'ROL', 'ROR') for row in terrain)
    assert not any(row['op'] in ('ASL', 'LSR') and row['mode'] != 'a' for row in terrain)
    for row in terrain:
        if row['mode'] == 'rel':
            raw_delta = bytes.fromhex(row['raw_hex'])[1]
            target = row['cpu'] + 2 + (raw_delta if raw_delta < 128 else raw_delta - 256)
            assert target > row['cpu'] and 0xB6E5 <= target <= 0xB74A
    return sorted(selected, key=lambda row: (row['physical_bank'], row['cpu'])), tables, predicate_callers


def prepared_contract(rom):
    instructions, tables, predicate_callers = original_inventory(rom)
    return dict(schema='phase32-current-dynamic-JSR-inline-dispatch-contract-v1',
        ROM_sha256=ROM_SHA, selected_targets=[dict(physical_bank=bank, cpu=pc) for bank, pc in SELECTED],
        original_instructions=instructions, immutable_inline_tables=tables,
        trusted_atlas_callers=[dict(physical_bank=8, call_PC=pc, **info) for pc, info in CALLS.items()],
        exact_helper_range=dict(physical_bank=8, cpu=0xB517, end_exclusive=0xB536,
                                rom_offset=off(8, 0xB517), bytes=31, raw_hex=HELPER_HEX),
        write_domain=[0x20, 0x21, 0x22, 0x23, 0x24],
        AC7B_live_2C_lifecycle=dict(input_X_legal_inline_domain=list(range(16)),
            actual_adjacent_LDX_JSR_prefixes=predicate_callers,
            observed_static_prefix_X_values=sorted({row['input_X'] for row in predicate_callers}),
            original_sequence='AC7B STX002C; AC8D andACA2 actualJSR B6E5; ACA8 LDA002C; ACAB actualJSR B517.',
            complete_B6E5_descendants=[dict(physical_bank=8, entry=0xB6EF), dict(physical_bank=31, entry=0xF266)],
            direct_write_domain=[0x22, 0x23, 0x24, 0x25, 0x26, 0xDE, 0xE000],
            stack_write_domain='Only page0100 for actualJSR/PHA; no alias with002C for anySP.',
            return_postcondition='002C unchanged on every normal return, but X is set0 by B731; caller reloads A from live002C.',
            premise='Original acyclic helper+fixedF266, original mapping behavior, normal return, no IRQ/external mutation; not arbitrary unknown callee.',
            no_global_X_or_raw_X_legality_claim=True),
        call_and_stack_lifecycle=[
            'Execute current original JSR, which writes raw call_PC+2 high then low in page0100; JSR decreases SP by2 modulo256.',
            'B517 saves incomingY to20, shifts rawA modulo256, sets firstY=(2*A+1)&FF.',
            'PLA atB51D andB521 consume precisely this uninterrupted current-frame low/high word into21/22.',
            'No call, indexed/indirect store or loop occurs before B525/B52B; fixed stores20..24 cannot alias page0100 even at wrapped SP.',
            'Between the two reads only STA0023 and INY execute, so live21/22 remains the complete current word, not independent byte sets.',
            'Final LDY0020 restores incomingY; JMP($0023) transfers to inline target and does not RTS. Current JSR frame is consumed, outer caller frame remains.',
            'Two generations at the same call PC obtain their own actual stack writes; equality of static call PC alone never creates a capability.',
        ],
        address_contracts={f'{pc:04X}': address_contract(pc) for _, pc in SELECTED},
        strategy_index_limit=dict(AND_0F_proves=list(range(16)), strategy_table_indices=list(range(8)),
                                  assertion='AND0F alone does not establish <8; raw8..15 remains an out-of-table-target counterexample.'),
        stop_boundary=dict(original_CPU='Immediately after original B533 indirect JMP, before the first target opcode.',
                           comparison='dispatch_transfer_prefix', actual_caller_RTS=False,
                           invalid_target_never_executed=True),
        model_scope=dict(raw_A=list(range(256)), incoming_Y=list(range(256)), caller_SP=list(range(256)),
                         code_pair=[8, 9], data_window_bank=list(range(32)),
                         flags='B517 has no ADC/SBC/branches; D does not alter its address arithmetic.',
                         interrupt='No NMI/IRQ/external mutation during JSR-to-JMP window; a rejected premise, not a tested interrupt schedule.'),
        bare_counterexample_specifications=[
            dict(entry=0xB517, synthetic_raw_stack_word=0x6000, raw_A=index,
                 note='No current original JSR; arbitrary real stack bytes can construct city6000 pointer.')
            for index in (0, 13, 14, 15)
        ] + [dict(entry=pc, pointer_21_22=0x6000, Y=y,
                  note='Bare middle access bypasses both original PLA producers.')
             for pc, y in ((0xB525, 1), (0xB52B, 28), (0xB525, 29), (0xB52B, 30), (0xB525, 31))],
        semantic_credit='B517 dispatch gameplay and source already named in frozen phases7/14; new conditional address/lifetime proof only.',
        source_CPU_cases=0, Native_runs=0,
        official_city_auxiliary_names={str(offset): None for offset in (1, 28, 29, 30, 31)},
        limits=[
            'Only current complete JSR premises confer the address contract; bare/middle entry, partial stack overwrite, interrupted generations and changed code/banks are rejected.',
            'RawA may be any byte for the ROM-address lemma; only the declared 8/16 indices select legitimate inline words.',
            'Root CPU tests stop at transfer, not at a fake RTS; target behavior, whole-game termination and full interrupted closure are outside this contract.',
            'Logical effective addresses exclude instruction fetch, pointer-byte fetch and page-cross/store dummy bus accesses.',
            'A conditional exclusion does not assign official names or prove unused/reserved city fields.',
        ])


def receipt_usable(receipt):
    if not receipt or receipt.get('status') != 'passed':
        return False
    assert receipt['ROM_sha256'] == ROM_SHA and receipt['source_CPU_cases'] == 0 and receipt['Native_runs'] == 0
    assert receipt['quick'] is False
    assert receipt['actual_caller_RTS_CPU_cases'] == 0 and receipt['original_CPU_contract_cases'] > 0
    assert receipt['all_contract_cases_stop_at_inline_transfer_or_selected_access_prefix'] is True
    assert receipt['failed_count'] == 0
    for path, digest in receipt['source_and_validator_sha256'].items():
        assert sha(ROOT / path) == digest, ('stale Root CPU producer', path)
    return True


def generate(rom, cpu_receipt=None):
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA
    assert sha(ROOT / 'analysis/phase31/verification.json') == BASE_AUDIT_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    proof = prepared_contract(rom)
    save('current-frame-dispatch-contract.json', proof)
    if cpu_receipt:
        assert cpu_receipt['contract_sha256'] == sha(OUT / 'current-frame-dispatch-contract.json')
    promote = receipt_usable(cpu_receipt)
    prior = read(BASE_LEDGER)
    assert prior['classification_counts'] == dict(proved_disjoint_auxiliary_address_domain=1201,
        possible_city_auxiliary_alias=80, unresolved_pointer_or_index_contract=245)
    rows = copy.deepcopy(prior['accesses'])
    for row in rows:
        selected = (row['physical_bank'], row['cpu']) in SELECTED
        row['newly_proved_disjoint'] = bool(promote and selected)
        if not selected:
            continue
        assert row['classification'] == 'unresolved_pointer_or_index_contract'
        proposal = address_contract(row['cpu'])
        row['phase32_prior_classification'] = row['classification']
        row['phase32_conditional_contract_proposal'] = proposal
        row['phase32_current_frame_CPU_receipt_required'] = not promote
        if not promote:
            continue
        row['phase32_prior_authority'] = dict(path=BASE_LEDGER, sha256=sha(ROOT / BASE_LEDGER),
                                             physical_bank=row['physical_bank'], cpu=row['cpu'])
        row['phase32_bare_entry_candidate_not_authority'] = copy.deepcopy(row.get('address_contract'))
        row['classification'] = 'proved_disjoint_auxiliary_address_domain'
        row['address_contract'] = proposal
        row['whole_pointer_values'] = proposal['whole_pointer_values']
        row['Y_values'] = proposal['Y_values']
        row['proof_basis'] = 'phase32_current_dynamic_JSR_stack_and_live_pointer_conditional_contract'
        row['limits'] = proof['limits']
    counts = dict(Counter(row['classification'] for row in rows))
    selected_rows = [row for row in rows if (row['physical_bank'], row['cpu']) in SELECTED]
    remaining = [row for row in rows if row['classification'] != 'proved_disjoint_auxiliary_address_domain']
    save('all-indirect-accesses.json', dict(schema='phase32-inline-dispatch-all-indirect-ledger-v1',
        ROM_sha256=ROM_SHA, access_count=len(rows), classification_counts=counts,
        newly_proved_disjoint_count=2 if promote else 0, accesses=rows))
    save('selected-accesses.json', dict(schema='phase32-inline-dispatch-selected-accesses-v1',
                                      accesses=selected_rows))
    save('remaining-accesses.json', dict(schema='phase32-remaining-city-auxiliary-candidates-v1',
                                       count=len(remaining), accesses=remaining))
    save('raw345-executability-ledger.json', read('analysis/phase31/fields-static/raw345-executability-ledger.json'))
    lines = []
    for row in proof['original_instructions']:
        lines.append(f"{row['physical_bank']:02d}:{row['cpu']:04X} file={row['rom_offset']:06X} {row['raw_hex']:<10} {row['op']} {row['mode']}")
    for row in proof['immutable_inline_tables']:
        lines.append(f"{row['physical_bank']:02d}:{row['cpu']:04X} file={row['rom_offset']:06X} {row['raw_hex']} ; inline word data, not decoded code")
    (OUT / 'original-ranges.asm').write_text('\n'.join(lines) + '\n')
    dependencies = ['analysis/phase31/verification.json', BASE_LEDGER, ATLAS,
        'analysis/phase31/fields-static/raw345-executability-ledger.json',
        'source/recovered/tactical_cooperation_controller.py',
        'source/recovered/tactical_ai_control.py']
    artifact = {path: sha(ROOT / path) for path in dependencies}
    artifact.update({str(path.relative_to(ROOT)): sha(path) for path in OUT.iterdir()
                     if path.is_file() and path.name in ('current-frame-dispatch-contract.json',
                         'all-indirect-accesses.json', 'selected-accesses.json', 'remaining-accesses.json',
                         'raw345-executability-ledger.json', 'original-ranges.asm', 'cpu-contract-validation.json')})
    scripts = ['scripts/analyze_inline_dispatch_contracts_phase32.py',
               'scripts/verify_inline_dispatch_contracts_phase32.py']
    source_pins = {path: sha(ROOT / path) for path in scripts if (ROOT / path).exists()}
    summary = dict(schema='phase32-inline-dispatch-field-summary-v1',
        status='original_CPU_contracts_verified' if promote else 'analyzed_pending_Root_original_CPU_contracts',
        ROM_sha256=ROM_SHA, old_phase31_audit_sha256=BASE_AUDIT_SHA,
        original_CPU_contract_receipt_required=not promote, source_CPU_cases=0, Native_runs=0,
        original_CPU_contract_cases=cpu_receipt['original_CPU_contract_cases'] if promote else 0,
        actual_caller_RTS_CPU_cases=0,
        explicit_transfer_or_access_prefix_CPU_cases=cpu_receipt['original_CPU_contract_cases'] if promote else 0,
        all_indirect_access_count=1526, previous_candidate_count=325,
        all_indirect_classification_counts=counts, remaining_access_count=len(remaining),
        newly_proved_disjoint_all_count=2 if promote else 0,
        raw345=dict(total=345, operand=104, known_data=13, no_proved_control_entry=228),
        official_city_auxiliary_names=proof['official_city_auxiliary_names'],
        whole_game_closure_proven=False, complete_analysis_fixed_point_proven=False,
        source_and_validator_sha256=source_pins, artifact_sha256=artifact,
        limits=proof['limits'])
    save('analysis-summary.json', summary)
    evidence = dict(schema='phase32-inline-dispatch-field-evidence-v1',
        status='bounded_original_CPU_contracts_verified' if promote else 'pending_Root_original_CPU_contracts',
        ROM_sha256=ROM_SHA, source_CPU_cases=0, Native_runs=0,
        analyzer_path=scripts[0], analyzer_sha256=source_pins[scripts[0]],
        validator_path=scripts[1], validator_sha256=source_pins.get(scripts[1]),
        contract_path=str((OUT / 'current-frame-dispatch-contract.json').relative_to(ROOT)),
        contract_sha256=sha(OUT / 'current-frame-dispatch-contract.json'),
        source_and_validator_sha256=source_pins, artifact_sha256=artifact,
        new_source_module_count=0, semantic_first_recovery_claim=False,
        original_CPU_contract_cases=summary['original_CPU_contract_cases'],
        actual_caller_RTS_CPU_cases=0,
        raw_byte_original_instructions=proof['original_instructions'],
        immutable_tables=proof['immutable_inline_tables'], limits=proof['limits'])
    save('evidence.json', evidence)
    state = '已由Root独立原CPU合同验证' if promote else '等待Root执行独立原CPU合同；目前不迁移分类'
    (OUT / 'README.md').write_text(f'''# 阶段32：本次JSR栈帧与B517的两个ROM读取\n\n{state}。分析器本身不执行CPU、Source、Native或旧生成器。\n\n原8:A09E与8:ACAB都是真实`JSR B517`，分别把本次raw返回word A0A0／ACAD压入栈。B517把本次两字节PLA到21／22，B525与B52B读inline word，最后`JMP($23)`。验证停止于原JMP完成、目标第一条指令之前；这些是transfer前缀，不是RTS。\n\n完整当次JSR、pair8/9、原代码/表、期间无中断或外部写的前提下，固定ZP写20..24不碰0100栈，SP环绕也不改变两次PLA的当代来源。两读之间只有STA23与INY，live21/22不变。全部rawA0..255只生成byteY；逻辑EA仍在代码ROM窗口。任意裸B517栈、B525/B52B中段入口不能借此合同。\n\n`AND0F`只证明0..15。strategy表只有8项，predicate表16项；strategy8..15及更大rawA的越表目标保留，绝不伪称合法策略或继续执行目标。裸stackword6000及中段21/22=6000保留城市+1和+28..31反例。\n\n全部1526项：{counts.get('proved_disjoint_auxiliary_address_domain', 0)}条件不交／{counts.get('possible_city_auxiliary_alias', 0)}可能／{counts.get('unresolved_pointer_or_index_contract', 0)}未知，余{len(remaining)}；本轮正式迁移{2 if promote else 0}。其余1524项权威合同与raw345=104操作数／13数据／228未证入口不变。条件地址证明不等城市字段未用，正式名称仍null。\n\n- [当代栈与原字节合同](current-frame-dispatch-contract.json)\n- [原指令和inline数据](original-ranges.asm)\n- [全部1526项](all-indirect-accesses.json)\n- [两处被选访问](selected-accesses.json)\n- [保留候选](remaining-accesses.json)\n- [CPU合同回执](cpu-contract-validation.json)\n- [分项终审](verification.json)\n\nSource／Native病例均0。本轮不重记阶段7／14已知dispatch语义，不声称中断闭合、完整目标行为、全ROM未用或官方字段名。阶段32完成后等待评估，不自动33。\n''')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--promote-verified', action='store_true', help='Require existing Root-produced current CPU receipt.')
    args = parser.parse_args()
    receipt = read('analysis/phase32/fields-static/cpu-contract-validation.json') if args.promote_verified else None
    result = generate(args.rom.read_bytes(), receipt)
    print(json.dumps({key: result[key] for key in ('status', 'all_indirect_classification_counts',
        'remaining_access_count', 'newly_proved_disjoint_all_count', 'original_CPU_contract_cases')}))


if __name__ == '__main__':
    main()
