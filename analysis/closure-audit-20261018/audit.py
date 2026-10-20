#!/usr/bin/env python3
"""Read/hash existing evidence; write ONLY this closure-audit directory.

No project modules are imported; no producer, CPU, Source runner, emulator,
compiler, subprocess or archive extraction is invoked. A passed result is
an integrity/inventory result, never a new game-validation result.
"""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import re
import time

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parent.parent
ROM = '/Users/paulasmith/Downloads/三国志2超级版.nes'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BASE = 'analysis/phase31/verification.json'
ALL = 'analysis/phase31/fields-static/all-indirect-accesses.json'
REM = 'analysis/phase31/fields-static/remaining-accesses.json'
RAW = 'analysis/phase31/fields-static/raw345-executability-ledger.json'
GROUP = 'analysis/phase23/fields-static/shared-producer-caller-groups.json'
REQ = 'analysis/phase31/acceptance/requirements.json'
SRC31 = 'analysis/phase31/player-disposition/validation.json'
NAT31 = 'analysis/phase31/runtime/validation.json'
CPU31 = 'analysis/phase31/fields-static/verification.json'
S32 = 'analysis/phase32/source-continuity/validation.json'
F32 = 'analysis/phase32/fields-static/static-verification.json'
P32 = 'analysis/phase32/ancestry-prefix/day30/prefix.json'
H32 = 'analysis/phase32/ancestry-prefix/day30/historical-comparison.json'
ANCHORS = {
    BASE: '717bc872656ca43617e20888a921951fa086634672a7bbbad1ac148a445341ac',
    'analysis/phase31/package-receipt.json': '7e079e1de8239e36c4f56d5a37a6abec828e750a38041d0eb7705d74cf18e8b7',
    'build/三国志2超级版-逆向分析-v31增量.zip': 'f3d208962ac264508cac4a65992b1adbcf23a831868bf28f196444813bbc09e5',
    '.toolchain/nestopia/nestopia_libretro.dylib': '924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a',
    ROM: ROM_SHA,
}
HASH_CACHE = {}


def path(p):
    return pathlib.Path(p) if pathlib.Path(p).is_absolute() else ROOT / p


def read(p):
    return json.loads(path(p).read_text())


def fingerprint(p):
    p = path(p)
    a = p.stat()
    sig = (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns)
    if sig not in HASH_CACHE:
        h = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
                h.update(block)
        b = p.stat()
        assert sig == (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns), str(p)
        HASH_CACHE[sig] = h.hexdigest()
    return {'sha256': HASH_CACHE[sig], 'bytes': a.st_size}


def save(name, obj):
    p = OUT / name
    assert p.resolve().parent == OUT
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def textfile(name, text):
    p = OUT / name
    assert p.resolve().parent == OUT
    p.write_text(text.rstrip() + '\n')


def ev(p, phase=None, kind='receipt_read_current_hash_not_reexecuted', locator=None):
    return {'path': p, **fingerprint(p), 'phase': phase,
            'evidence_kind': kind, 'locator': locator}


def frozen_check(pins):
    errors, found = [], {}
    for p, expected in pins.items():
        try:
            actual = fingerprint(p)
            found[p] = actual
            if actual['sha256'] != expected:
                errors.append({'path': p, 'expected': expected, 'actual': actual['sha256']})
        except (OSError, AssertionError) as error:
            errors.append({'path': p, 'error': str(error)})
    return found, errors


def residue_paths():
    files = {str(p.relative_to(ROOT)) for p in (ROOT / 'analysis/phase32').rglob('*') if p.is_file()}
    files |= {str(p.relative_to(ROOT)) for p in (ROOT / 'scripts').glob('*phase32*.py')}
    files |= {'scripts/capture_native_postbattle_nonempty.py',
              'source/recovered/postbattle_continuity_phase32.py'}
    files |= {str(p.relative_to(ROOT)) for p in (ROOT / '.toolchain/phase32-observer').rglob('*') if p.is_file()}
    return sorted(files)


def source_id(row):
    return f"I:{ROM_SHA}:b{row['physical_bank']:02d}:cpu{row['cpu']:04X}:rom{row['rom_offset']:06X}"


def window_id(row):
    return f"W:{ROM_SHA}:b{row['physical_bank']:02d}:off{row['bank_offset']:04X}:rom{row['rom_offset']:06X}"


def pin_check(p):
    d, results = read(p), []
    for key in ('source_sha256', 'source_and_validator_sha256', 'artifact_sha256', 'input_sha256'):
        for name, expected in d.get(key, {}).items():
            if isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected):
                actual = fingerprint(name)['sha256'] if path(name).is_file() else None
                results.append({'map': key, 'path': name, 'expected': expected,
                                'actual': actual, 'matches': actual == expected})
    return {'receipt': ev(p, 32), 'checks': results,
            'mismatch_count': sum(not r['matches'] for r in results)}


def build():
    started = time.monotonic()
    baseline = read(BASE)
    maps = {k: baseline[k] for k in ('source_and_validator_sha256', 'artifact_and_dependency_sha256',
                                    'included_dependency_sha256', 'external_dependency_sha256')}
    assert {k: len(v) for k, v in maps.items()} == {
        'source_and_validator_sha256': 596, 'artifact_and_dependency_sha256': 91929,
        'included_dependency_sha256': 38442, 'external_dependency_sha256': 53487}
    pins, conflicts = {}, []
    for name, values in maps.items():
        for p, digest in values.items():
            if p in pins and pins[p] != digest:
                conflicts.append([name, p])
            pins[p] = digest
    assert not conflicts
    assert set(maps['source_and_validator_sha256']) <= set(maps['artifact_and_dependency_sha256'])
    assert not set(maps['included_dependency_sha256']) & set(maps['external_dependency_sha256'])
    assert set(maps['included_dependency_sha256']) | set(maps['external_dependency_sha256']) == set(pins)
    pins.update(ANCHORS)
    before, freeze_errors = frozen_check(pins)
    assert not freeze_errors, freeze_errors[:10]
    residues = {p: fingerprint(p) for p in residue_paths()}
    print(f'Frozen phase31 paths checked: {len(before)}; phase32 residue paths: {len(residues)}', flush=True)

    all31, rem31, raw31 = read(ALL), read(REM), read(RAW)
    all32 = read('analysis/phase32/fields-static/all-indirect-accesses.json')
    rem32 = read('analysis/phase32/fields-static/remaining-accesses.json')
    raw32 = read('analysis/phase32/fields-static/raw345-executability-ledger.json')
    counts = dict(collections.Counter(r['classification'] for r in all31['accesses']))
    assert len(all31['accesses']) == 1526 and len(rem31['accesses']) == 325
    assert counts == all31['classification_counts'] == all32['classification_counts']
    identity_fields = ('physical_bank', 'cpu', 'rom_offset', 'raw_hex', 'op', 'mode', 'operand',
                       'classification', 'address_contract', 'whole_pointer_values', 'Y_values')
    def by_identity(rows):
        return {(r['physical_bank'], r['cpu']): r for r in rows}
    b31, b32 = by_identity(all31['accesses']), by_identity(all32['accesses'])
    assert b31.keys() == b32.keys()
    assert all(all(a.get(k) == b32[key].get(k) for k in identity_fields) for key, a in b31.items())
    rb31, rb32 = by_identity(rem31['accesses']), by_identity(rem32['accesses'])
    assert rb31.keys() == rb32.keys()
    assert all(all(a.get(k) == rb32[key].get(k) for k in identity_fields) for key, a in rb31.items())
    metadata_deltas = []
    for key, old in b31.items():
        new = b32[key]
        changes = {k: {'phase31_present': k in old, 'phase32_present': k in new,
                       'phase31': old.get(k), 'phase32': new.get(k)}
                   for k in old.keys() | new.keys() if old.get(k) != new.get(k) or (k in old) != (k in new)}
        if changes:
            metadata_deltas.append({'physical_bank': key[0], 'cpu': key[1], 'changes': changes})
    assert len(metadata_deltas) == 3
    assert {(d['physical_bank'], d['cpu']) for d in metadata_deltas} == {(8, 0xB525), (8, 0xB52B), (8, 0xBDB8)}
    assert all(not set(d['changes']) & set(identity_fields) for d in metadata_deltas)
    assert raw31['windows'] == raw32['windows'] and len(raw31['windows']) == 345
    rawcounts = dict(collections.Counter(r['phase22_executability_category'] for r in raw31['windows']))
    assert rawcounts == raw31['categories']
    remaining_keys = {(r['physical_bank'], r['cpu']) for r in rem31['accesses']}
    assert len(remaining_keys) == 325
    assert remaining_keys == {(r['physical_bank'], r['cpu']) for r in all31['accesses']
                              if r['classification'] != 'proved_disjoint_auxiliary_address_domain'}
    assert len({r['rom_offset'] for r in all31['accesses']}) == 1526
    rom_bytes = path(ROM).read_bytes()
    for row in all31['accesses']:
        assert row['rom_offset'] == 16 + row['physical_bank'] * 8192 + (row['cpu'] & 8191)
        raw = bytes.fromhex(row['raw_hex'])
        assert rom_bytes[row['rom_offset']:row['rom_offset'] + len(raw)] == raw
    for row in raw31['windows']:
        assert row['rom_offset'] == 16 + row['physical_bank'] * 8192 + row['bank_offset']
        raw = bytes.fromhex(row['raw_hex'])
        assert rom_bytes[row['rom_offset']:row['rom_offset'] + len(raw)] == raw
    history = read(GROUP)
    group_members, membership = [], {}
    for g in history['groups']:
        members = [r for r in g['accesses'] if (r['physical_bank'], r['cpu']) in remaining_keys]
        if not members:
            continue
        entry = {'historical_group_id': g['group_id'], 'physical_bank': g['physical_bank'],
                 'pointer_zero_page': g['pointer_zero_page'], 'unknown_producer': g['unknown_producer'],
                 'remaining_member_count': len(members), 'current_instruction_row_ids': [],
                 'shared_pointer_producers': g['shared_pointer_producers'],
                 'known_enclosing_procedures': g['known_enclosing_procedures'],
                 'actual_semantic_root_id': None,
                 'scope': 'Historical work container, not a proof of a shared current generation, owner or semantic root.'}
        for member in members:
            key = (member['physical_bank'], member['cpu'])
            assert key not in membership
            membership[key] = g['group_id']
            real = next(r for r in rem31['accesses'] if (r['physical_bank'], r['cpu']) == key)
            entry['current_instruction_row_ids'].append(source_id(real))
        group_members.append(entry)
    assert set(membership) == remaining_keys and len(group_members) == 96
    instruction_map = []
    remaining_indices = {(r['physical_bank'], r['cpu']): i for i, r in enumerate(rem31['accesses'])}
    phase32_indices = {(r['physical_bank'], r['cpu']): i for i, r in enumerate(all32['accesses'])}
    for i, row in enumerate(all31['accesses']):
        key = (row['physical_bank'], row['cpu'])
        remaining = key in remaining_keys
        b517 = key in {(8, 0xB525), (8, 0xB52B)}
        gap = 'G-B517' if b517 else ('G-ACCESS-CONTRACTS' if remaining else None)
        instruction_map.append({'source_row_id': source_id(row), 'source_path': ALL,
            'source_locator': f'/accesses/{i}', 'remaining_source_path': REM if remaining else None,
            'remaining_source_locator': f'/accesses/{remaining_indices[key]}' if remaining else None,
            'phase32_source_path': 'analysis/phase32/fields-static/all-indirect-accesses.json',
            'phase32_source_locator': f'/accesses/{phase32_indices[key]}',
            'physical_bank': row['physical_bank'], 'cpu': row['cpu'], 'rom_offset': row['rom_offset'],
            'classification': row['classification'], 'gap_id': gap,
            'historical_group_id': membership.get(key),
            'actual_root_dependency_id': 'current-JSR-to-B517-live21-22' if b517 else None,
            'cross_ledger_semantic_mapping': None})
    window_map = []
    for i, row in enumerate(raw31['windows']):
        category = row['phase22_executability_category']
        unresolved = category == 'unresolved_raw_window_no_proved_control_entry'
        window_map.append({'source_row_id': window_id(row), 'source_path': RAW,
            'source_locator': f'/windows/{i}', 'physical_bank': row['physical_bank'],
            'phase32_source_path': 'analysis/phase32/fields-static/raw345-executability-ledger.json',
            'phase32_source_locator': f'/windows/{i}',
            'bank_offset': row['bank_offset'], 'rom_offset': row['rom_offset'],
            'category': category, 'gap_id': 'G-RAW-ENTRY' if unresolved else None,
            'bounded_classification': 'entry_unproved' if unresolved else 'known_operand_or_declared_data_overlap',
            'actual_root_dependency_id': None, 'cross_ledger_semantic_mapping': None,
            'alternate_entry_globally_impossible': False})
    # Compare actual byte intervals only. Zero intersection is not semantic independence.
    instruction_bytes = {r['rom_offset'] + i for r in all31['accesses'] for i in range(2)}
    raw_bytes = {r['rom_offset'] + i for r in raw31['windows'] for i in range(3)}
    overlap = sorted(instruction_bytes & raw_bytes)
    assert not overlap
    coverage = {
        'schema': 'nes-closure-coverage-comparison-v1',
        'basis': [ev(ALL, 31), ev(REM, 31), ev(RAW, 31), ev(GROUP, 23),
                  ev('analysis/phase32/fields-static/analysis-summary.json', 32), ev(F32, 32)],
        'fixed_denominator': 1526,
        'formal_phase31': {'conditional_disjoint': 1201, 'possible_alias': 80, 'unknown_contract': 245, 'remaining': 325},
        'actual_phase32_frozen_draft': {'conditional_disjoint': 1201, 'possible_alias': 80, 'unknown_contract': 245, 'remaining': 325,
            'changed_classification_rows': 0, 'changed_authoritative_contract_rows': 0,
            'metadata_changed_rows': len(metadata_deltas), 'metadata_deltas': metadata_deltas,
            'note': 'B525/B52B add unaccepted proposal metadata; BDB8 clears the per-round newly_proved flag. These are not classification changes.'},
        'phase32_unexecuted_proposal': {'conditional_disjoint': 1203, 'possible_alias': 80, 'unknown_contract': 243, 'remaining': 323,
            'status': 'not_adopted', 'candidate_rows': ['8:B525', '8:B52B'],
            'missing_acceptance': 'Current full original-CPU receipt, current pins and generation/caller premises; static draft is not enough.'},
        'raw_window_ledger': {'denominator': 345, 'operand_overlap': 104, 'declared_data_overlap': 13, 'entry_unproved': 228,
            'all_starts_unproved': all(not r['trusted_instruction_entry_at_start'] for r in raw31['windows']),
            'trusted_matching_instruction_rows': sum(len(r['matching_trusted_instructions']) for r in raw31['windows'])},
        'cross_ledger': {'instruction_raw_byte_interval_overlap_count': len(overlap),
            'semantic_relation': None, 'semantic_root_count': None,
            'addition_of_325_and_345_or_228_permitted': False,
            'limit': 'Different syntactic ledgers. No byte overlap does not prove distinct semantic dependencies.'},
        'historical_group_projection': {'group_count': len(group_members),
            'known_producer_containers': sum(not g['unknown_producer'] for g in group_members),
            'unknown_producer_containers': sum(g['unknown_producer'] for g in group_members),
            'current_member_count': sum(g['remaining_member_count'] for g in group_members),
            'unique_semantic_roots': None},
        'official_city_field_names': {'1': None, '28': None, '29': None, '30': None, '31': None},
        'overall_reverse_engineering_complete': False, 'completion_percentage': None,
        'unknown_unique_services': None,
        'limits': ['Conditional exclusion is not unused/padding/reserved proof.',
                   'Source325 cases and remaining325 instruction rows have different denominators.',
                   'Dummy bus accesses, same-value stores, pointer fetches and logical consumers must be distinguished.']}
    save('coverage-comparison.json', coverage)

    gaps = []

    def gap(identifier, title, object_key, rows, evidence, impact, dependencies, acceptance, work, dims, kind='proof_obligation'):
        gaps.append({'gap_id': identifier, 'title': title, 'object_key': object_key,
            'object_kind': kind, 'status': 'open', 'source_row_ids': rows,
            'assessment_kind': 'derived_by_readonly_audit_from_the_listed_evidence',
            'evidence': evidence, 'impact': impact, 'dependencies': dependencies,
            'acceptance_criteria': acceptance, 'concrete_next_work': work, 'acceptance_dimensions': dims,
            'semantic_root_count': None})

    gap('G-ACCESS-CONTRACTS', '剩余间接访问的指针、入口和索引合同', 'phase31-fixed1526-contract-closure',
        [r['source_row_id'] for r in instruction_map if r['gap_id'] == 'G-ACCESS-CONTRACTS'],
        [ev(REM, 31), ev(GROUP, 23)],
        '323行未决访问挂在此批次验收义务；另2行挂G-B517。这里不是一个已证实的共同语义根因。', [],
        ['每行保留身份与前提，追踪实际current producer/caller、完整联合指针及索引。',
         '能合并依赖时记录证明；不能合并时root=null。保留裸入口、同值写、未来alias和FF空洞反例。',
         '只在原字节、实际调用及当前回执均成立后改变分类；不得用局部观察证明全局unused。'],
        ['按96个历史分工容器排查，首先选择具有完整producer/caller证据的合同；未知容器不推断为共同owner。'], ['A02', 'A03'])
    gap('G-B517', 'B517真实当前JSR帧及inline dispatch合同', 'current-JSR-to-B517-live21-22',
        [r['source_row_id'] for r in instruction_map if r['gap_id'] == 'G-B517'],
        [ev('analysis/phase32/fields-static/current-frame-dispatch-contract.json', 32, 'unaccepted_static_candidate'),
         ev(F32, 32, 'stale_pin_static_model_receipt'), ev('scripts/verify_inline_dispatch_contracts_phase32.py', 32, 'unexecuted_current_script')],
        '已有生产dispatch owner；这不是缺失服务或首次实现。两条读访问不能仅凭代码存在迁移为排除，A09E/ACAB两个caller子合同及返回栈代际仍需正式验收。', [],
        ['从真实A09E/ACAB JSR开始记录实际栈写、live21/22和两个logical读取，停在真实JMP目标边界，不伪造RTS。',
         '合法8/16项索引与更宽rawA地址lemma分列；AC7B→B6E5两次调用后的2C、寄存器和当前JSR栈必须取实际现场。',
         '检验当前代际/部分覆盖/裸栈反例；更早栈同值不替代真实current JSR。保持city alias反例。',
         '当前脚本和输入pins一致的full CPU回执通过后，才考虑1203/80/243候选。'],
        ['审阅当前脚本的实际代际覆盖和合同域，再另行授权运行；本次不修、不运行静态草稿。'], ['A02', 'A03', 'A06'])
    gaps[-1]['existing_production_owner'] = {
        'path': 'source/recovered/tactical_cooperation_controller.py',
        'class': 'TacticalCooperationController', 'method': '_dispatch', 'line': 117,
        'new_implementation_required': False,
        'evidence': ev('source/recovered/tactical_cooperation_controller.py', 31, 'frozen_existing_production_owner', 'TacticalCooperationController._dispatch')}
    gap('G-RAW-ENTRY', '228个原字节窗口的可信执行入口', 'raw345-control-entry-closure',
        [r['source_row_id'] for r in window_map if r['gap_id']], [ev(RAW, 31)],
        '窗口看似opcode不能证明是可执行访问；104 operand与13数据重叠也不证明任意替代入口不可能。', [],
        ['对228窗补足可信CFG/动态实际入口或明确有界数据来源证据；保留mapper页及computed target前提。',
         '与间接访问账本的语义同根关系仅在有真实依赖证据时建立；没有证据保持null。'],
        ['从可达分派目标和声明ROM数据来源追踪入口；不进行无边界随机扫测。'], ['A03'])
    for offset in [1, 28, 29, 30, 31]:
        gap(f'G-CITY-{offset:02d}', f'城市+{offset}正式字段含义', f'city-record-offset-{offset}', [],
            [ev('analysis/phase31/fields-static/analysis-summary.json', 31), ev(CPU31, 31),
             ev('analysis/phase31/runtime/evidence.json', 31)],
            '正式名称仍null；当前排除合同不能证明padding、reserved或unused，也不能从FF/0或dummy命中命名。',
            ['G-ACCESS-CONTRACTS', 'G-B517', 'G-RAW-ENTRY'],
            ['找到有来源的logical consumer/producer，完整追踪写入、读取、UI或玩法效果并用原模拟器实际触发。',
             '若查明多字段共同编码，记录联合结构和逐offset关系；证据不足时继续null。',
             '区分实际逻辑访问、总线dummy、pointer fetch和同值store；不足以证明时不得强行命名。'],
            ['利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。'], ['A02'])
        gaps[-1]['dependency_relation'] = 'Discovery aids and exclusion-proof dependencies; positive field semantics may be accepted from independently proven logical consumer and UI/gameplay evidence without first closing every candidate.'
    gap('G-NONEMPTY-MODE2', '自然非空mode2完整战后分配与返回', 'natural-BB36-mode2-nonempty-allocation', [],
        [ev('analysis/phase31/runtime/natural-AI-mode2/observations.json', 31),
         ev('analysis/phase31/ancestry/natural-AI-mode2/ancestry.json', 31),
         ev(P32, 32, 'single_original_run_prefix'), ev(H32, 32, 'historical_prefix_comparison')],
        '31的自然mode2临时名单为空；32停day30。旧7966→7967帧末差异只能提供下一次捕获候选，不能证明完整动态callee链。', [],
        ['合法祖先及真实输入下临时名单非空，记录实际outcome writer（含1→1同值）和BB36→BC46→BD67→BD96/BDB8→BB39。',
         '记录真实入栈/返回PC与SP、目标城市/武将和名单写；不写PC、ready、RNG、结果或名册制造命中。',
         '新窗口原核/被动核initial及逐帧五完整buffer等价，独立fresh复跑；母链单跑范围另列。'],
        ['先审定32 producer与observer版本配套；从7610前缀前的合法母档建立有界结算窗口。'], ['A04', 'A08'])
    gap('G-HUMAN14', '自然human14 phase1..6完整多人交互', 'human14-active-plus-captives-at-least11', [],
        [ev('analysis/phase31/runtime/controlled14-direct/observations.json', 31),
         ev('analysis/phase32/source-continuity/design.json', 32, 'authored_design')],
        '31只有14/0直接结束；城市名册>=11不等D0E1选择名单>=11。', [],
        ['以同侧active20与captives20构成真实>=11候选前置，明确合法祖先与普通输入；不得注入名册/结果，受控数值准备另列且不能替代自然成功。',
         '原模拟器实际覆盖14/1..6、确认/取消/返回和结算，观察真实列表及返回状态。',
         '完整回城及fresh复跑，不把逐callee夹具或phase0命中替代交互。'],
        ['先建立合法战斗编组和俘虏来源，再固定有限按钮计划；自然前提不存在时停止并保留缺口。'], ['A04', 'A08'])
    gap('G-SOURCE-CONTINUITY', '单Source实例跨主循环与中断的完整连续流程', 'single-GameEngine-E066-main-NMI-IRQ-resume', [],
        [ev(SRC31, 31), ev(S32, 32, 'bounded_source_CPU_smoke'),
         ev('source/recovered/postbattle_continuity_phase32.py', 32, 'authored_adapter')],
        '31每case新Engine；32前三案仅2周期且E066寄存器为夹具，不能证明完整1551路线或真实起点。',
        ['G-NONEMPTY-MODE2', 'G-HUMAN14'],
        ['实际E066初始RAM/SRAM/REG/PRG一次导入，同Engine/Coordinator/session/pending跨完整UI计划，不从下一Native帧回填。',
         '每事件对照原CPU的2K/8K、AXYP/SP/PC、四PRG、combined logical IO及声明N163输入；跨main/NMI/IRQ/resume保持身份。',
         'pending只完成一次，缺服务、重复resume、正常返回和非局部边界分别验收。32 ECEE局部恰一次通过不能泛化。',
         '完整natural13计划与未来非空mode2、human14实际路线分列，Source周期不叫Native视频帧。'],
        ['先取得真实E066现场，跑最短完整路线再扩展；复用既有玩法owner，不新增臆造算法。'], ['A04', 'A06', 'A08'])
    gap('G-SERVICE-CLOSURE', '全局可达服务依赖闭包', 'reachable-global-game-service-graph', [],
        [ev('analysis/phase31/acceptance/source-dependency-inventory.json', 31), ev(SRC31, 31)],
        '未知唯一服务数null；8个故意缺服务prefix不是8个真实未知服务，AST标记数也不是服务总数。', [],
        ['从全局入口与实际可达分派形成有界服务图，逐owner记录callee合同、动态/静态证据及缺失依赖。',
         '同地址、同scratch或多API层不能自动去重；实际owner/caller等价须有证据。',
         '可达逻辑均有可读实现或明确设备输入合同，未知仍列prefix；冻结已恢复owner不重新列为未知。'],
        ['按当前依赖库存定位真实未闭合前门，优先阻塞连续UI的服务；不把整个IR或原CPU当生产fallback。'], ['A04'])
    gap('G-INTERRUPT-BOUNDARIES', '关键等待、NMI/IRQ、reset与非局部返回边界', 'finite-reachable-interrupt-and-owner-lifetimes', [],
        [ev(S32, 32, 'bounded_source_CPU_smoke'), ev('source/recovered/campaign_session.py', 31, 'frozen_source')],
        '32 special已对照21NMI/85IRQ/22resume，但仅限该受控序列；nonlocal_count=0不能宣称正常非局部完结支持，reset未验。B517无中断合同前提不构成中断时序验证。',
        ['G-SOURCE-CONTINUITY', 'G-SERVICE-CLOSURE'],
        ['列出可达关键边界的有限矩阵：等待前后、同NMI恢复、IRQ嵌套/RTI、reset、非局部退出及owner/pending生命周期。',
         '分别给真实正常路线、受控故障拒绝和恢复证据；同值写、SP/PC和副作用都比较。',
         '保留ECEE同步立即RTS；EE07使用实际栈，恢复code pair同时保留E1数据页副作用。',
         '后续fresh NMI/callback必须在BBA0重新读取87直到原palette完成，不能用同generator伪等待或人工ack。',
         '不要求任意硬件交错穷尽；遇不支持路径保留明确合同和prefix。'],
        ['从现有ECEE/EE07副作用回归扩展有判别力边界；不做无限随机测试。'], ['A06'])
    gap('G-DEVICE-BOUNDARY', '显式设备输入与完整画面/音频合成的验收边界', 'declared-host-inputs-versus-original-core-frame-buffers', [],
        [ev(NAT31, 31), ev(S32, 32, 'bounded_software_device_fixture')],
        '共同N163/2002/4015/5800夹具、逻辑IO与原核RGB/PCM不是同一证据。软件snapshot不含即时PPU/APU/N163全状态。', [],
        ['可读逻辑明确端口、N163和IRQ输入合同，未知设备输入拒绝/前缀，不隐式写ready或结果。',
         '对选定原模拟器流程分别验收五buffer与输入/观察核身份；全帧合成仍由原核负责。',
         '独立PPU/APU/N163周期模拟器、独立可玩重制不自动加入原逆向任务；若另需独立合成，应单独定范围。'],
        ['将每条Source计划的显式设备夹具和Native五buffer回执并列引用，保持证据边界。'], ['A07'], 'scope_and_input_contract')

    register = {'schema': 'nes-closure-unique-gap-register-v1',
        'deduplication_rule': 'Named entries are actual proof/acceptance objects, not a count of unique code defects. Merge only a demonstrated object/dependency; unresolved semantic roots and cross-ledger relations remain null.',
        'named_acceptance_object_count': len(gaps), 'unknown_unique_semantic_roots': None,
        'unknown_unique_services': None, 'whole_game_service_closure_proven': False,
        'gaps': gaps, 'instruction_row_mapping': instruction_map,
        'raw_window_row_mapping': window_map, 'historical_work_containers': group_members,
        'cross_ledger_relations': {'physical_interval_overlap_count': len(overlap),
            'semantic_same_root_pairs': None, 'semantic_disjoint_pairs': None,
            'limits': 'All original row identities preserved. No 1:1 semantic mapping was inferred.'},
        'counts': {'all_instruction_rows': 1526, 'remaining_instruction_rows': 325,
            'resolved_within_contract_rows': 1201, 'B517_shared_object_rows': 2,
            'remaining_other_instruction_rows': 323, 'all_raw_rows': 345,
            'raw_entry_unproved_rows': 228, 'raw_overlap_classified_rows': 117,
            'historical_container_count': 96, 'unique_semantic_defect_count': None},
        'row_evidence': [ev(ALL, 31), ev(REM, 31), ev(RAW, 31), ev(GROUP, 23)]}
    save('unique-gap-register.json', register)

    def package(identifier, title, deps, ids, artifacts, stops):
        return {'work_package_id': identifier, 'title': title, 'dependencies': deps,
            'dependency_kind': 'proposed_planning_order_not_a_claim_of_logical_necessity',
            'gap_ids': ids, 'status': 'planned_not_executed_in_this_audit',
            'acceptance_artifacts': artifacts, 'stop_conditions': stops,
            'remaining_rounds_estimate': None}

    packages = [
        package('WP01', '固定本次审计边界与32草稿输入', [], [],
            ['本目录verification及完整输入hash清单；31正式与32草稿分列'],
            ['31任一pin改变、32残留输入漂移或scope不明时停止；不修旧文件。']),
        package('WP02', '闭合B517两个current-JSR合同', ['WP01'], ['G-B517'],
            ['当前full原CPU合同回执、代际/反例/索引域、审阅后的逐行候选迁移表'],
            ['当前栈或中断前提未证、脚本pin不一致则不迁移；285/14093计划不能当执行数。']),
        package('WP03', '按producer/entry补足访问与raw窗口合同', ['WP01'], ['G-ACCESS-CONTRACTS', 'G-RAW-ENTRY'],
            ['每个原行ID→当前依赖/合同/证据映射；确认或明确null的跨账本关系'],
            ['没有真实entry/producer证据就保留unknown；不把96容器当96真实服务。']),
        package('WP04', '证明城市辅助字段语义', ['WP01'], [f'G-CITY-{x:02d}' for x in (1, 28, 29, 30, 31)],
            ['logical消费者/写者链、原机判别流程、逐offset字段表及可读源码命名'],
            ['只有dummy、字节默认值或有界未命中时保留null，不命名reserved。']),
        package('WP05', '配套观察核并验证自然非空mode2', ['WP01'], ['G-NONEMPTY-MODE2'],
            ['原核/被动核构建来源一致性、合法母链、实际callee/栈/写日志及fresh五buffer回执'],
            ['32 producer仍绑定旧31核或观察核不一致时不运行；禁止制造结果命中。']),
        package('WP06', '建立自然多人human14路线', ['WP01'], ['G-HUMAN14'],
            ['实际>=11 active+captives前置、phase1..6输入/列表/回城与fresh回执'],
            ['只有城市名册人数或phase0完成时不得通过；没有合法前置保留缺口。']),
        package('WP07', '梳理可达服务闭包与设备输入合同', ['WP01'], ['G-SERVICE-CLOSURE', 'G-DEVICE-BOUNDARY'],
            ['真实owner/caller依赖图、strict prefix清单、明确端口/N163/IRQ输入合同'],
            ['未知服务保持prefix；不扩成独立硬件模拟器或重制项目。']),
        package('WP08', '单实例连续Source和关键中断验收', ['WP05', 'WP06', 'WP07'],
            ['G-SOURCE-CONTINUITY', 'G-INTERRUPT-BOUNDARIES'],
            ['真实E066一次初态、完整natural13/非空mode2/human14计划、逐事件原CPU对照和有限边界矩阵'],
            ['不得中途回填下一Native RAM；无实际REG就标夹具；未支持nonlocal/reset不得称通过。']),
        package('WP09', '最终十维对照和交付评估', ['WP02', 'WP03', 'WP04', 'WP05', 'WP06', 'WP07', 'WP08'],
            [g['gap_id'] for g in gaps],
            ['冻结十维逐项结论、仍未知范围、输入hash及按需小增量归档'],
            ['证据不足明确部分完成；不自动追加随机轮次或新硬件广度。'])]
    packages[0]['status'] = 'completed_by_this_audit'
    packages[0]['completion_receipt'] = 'analysis/closure-audit-20261018/verification.json'
    wp = {'schema': 'nes-closure-work-packages-v1', 'packages': packages,
        'ordered_topological_plan': [p['work_package_id'] for p in packages],
        'parallel_after_freeze': [['WP02', 'WP03', 'WP05', 'WP07']],
        'dependency_limits': 'Edges describe a workable plan, not new universal prerequisites. Human14 acquisition may proceed independently of mode2; field-specific semantics need only the relevant proven consumer. Minimal Source routes may run once their own blockers and actual initial context are ready, while full global-service closure continues in parallel.',
        'total_remaining_rounds_estimate': None,
        'estimate_reason': 'No measured per-obligation workload or legal-route acquisition rate supports an interval. Case counts are not remaining rounds.',
        'current_audit_execution': 'WP01 inventory only; no future package execution authorized by this report.',
        'final_stop': 'Stop after delivering this audit and work-package plan; parent assessment decides continuation.'}
    save('work-packages.json', wp)

    req = read(REQ)
    matrix = []
    for dim in req['dimensions']:
        identifier = dim['id']
        related = [g['gap_id'] for g in gaps if identifier in g['acceptance_dimensions']]
        extra = ''
        status = 'partially_verified'
        if identifier == 'A01':
            status, extra = 'verified_within_declared_scope', '本次全量只读hash核验；字节身份不证明语义。'
        elif identifier == 'A05':
            status, extra = 'optional_extension_not_required', '独立可玩重制、原作者工程和同NES源码编译不是自动新增义务。'
        elif identifier == 'A09':
            status, extra = 'verified_within_phase31_delivery_scope', '31最终audit、BQA、ZIP receipt已存在并被当前hash复核；历史清单中“随后完成”是旧时点，不再作为新增缺口。32仍无总验收/归档。'
        elif identifier == 'A10':
            status, extra = 'not_complete', '本次是收尾清点通过，不是整款逆向完成；城市名/未知服务/完成比例/轮数保持null。'
        elif identifier == 'A04':
            extra = '32只补局部2周期与ECEE回归；不覆盖1551完整连续Source计划。已恢复owner不重列为未知。'
        elif identifier == 'A06':
            extra = '有限关键边界验收；不要求任意交错穷尽，不将合同拒绝当动态IRQ成功。'
        elif identifier == 'A07':
            extra = '明确设备输入与原核音画验证边界；不要求另建周期硬件模拟器。'
        elif identifier == 'A08':
            extra = '31 natural13全7阶段已有原机连续证据；未闭合的是非空mode2及真实>=11的14/1..6。'
        elif identifier == 'A02':
            extra = '城市+1/+28..31正式名称null；禁止从无命中、默认值或dummy命名。'
        elif identifier == 'A03':
            extra = '正式1201/80/245不变；32 static陈旧pin不被采纳。raw345独立。'
        references = [ev(p, None, 'frozen_dimension_reference') for p in dim['evidence']]
        if identifier == 'A09':
            references += [ev(BASE, 31), ev('analysis/phase31/package-receipt.json', 31),
                           ev('analysis/phase31/browser-validation.json', 31)]
        matrix.append({'dimension_id': identifier, 'title': dim['title'],
            'original_requirement_kind': dim['requirement_kind'], 'original_user_request_ids': dim['user_request_ids'],
            'formal_phase31_result': dim['phase31_change']['result'],
            'formal_phase31_remaining_bound': dim['phase31_change']['remaining_gap'],
            'current_audit_status': status, 'current_interpretation': extra,
            'gap_ids': related, 'evidence': references,
            'acceptance_method': dim['acceptance_method'],
            'stop_condition': 'Respect listed evidence scope; unresolved dependencies remain open. No automatic next phase.'})
    save('frozen-acceptance-matrix.json', {'schema': 'nes-closure-frozen-ten-dimension-matrix-v1',
        'basis': [ev(REQ, 31), ev('analysis/phase31/acceptance/request-provenance.json', 31),
                  ev('analysis/phase31/acceptance/verification.json', 31)],
        'dimensions': matrix, 'dimension_count': 10,
        'original_reverse_engineering_scope_preserved': True,
        'new_independent_hardware_emulator_required': False,
        'remake_is_optional': True, 'random_testing_without_stop_bound_required': False,
        'overall_reverse_engineering_complete': False, 'completion_percentage': None,
        'remaining_rounds_estimate': None})

    # Freeze the partial tree as found. Receipt pins may be stale; do not repair them.
    pin_receipts = [pin_check(p) for p in [S32, 'analysis/phase32/source-continuity/design.json', F32,
        'analysis/phase32/fields-static/analysis-summary.json', 'analysis/phase32/fields-static/evidence.json']]
    producer = 'scripts/capture_native_postbattle_nonempty.py'
    match = re.search(r"OBSERVER_SHA\s*=\s*['\"]([0-9a-f]{64})", path(producer).read_text())
    assert match
    observed = '.toolchain/phase32-observer/observed/nestopia_libretro.dylib'
    builds = [p for p in residues if p.endswith('nestopia_libretro.dylib')]
    absent = ['analysis/phase32/verification.json', 'analysis/phase32/package-receipt.json',
              'analysis/phase32/runtime', 'analysis/phase32/runtime-repeat',
              'analysis/phase32/source-continuity/actual-spec.json',
              'analysis/phase32/source-continuity/evidence.json',
              'analysis/phase32/fields-static/cpu-contract-validation.json',
              'analysis/phase32/fields-static/quick-validation.json',
              'analysis/phase32/acceptance', 'analysis/phase32/index.html']
    assert all(not path(p).exists() for p in absent), absent
    p32, h32, s32 = read(P32), read(H32), read(S32)
    same_copy = fingerprint(S32)['sha256'] == fingerprint('analysis/phase32/exploratory/source-regression-smoke-validation.json')['sha256']
    phases = {'schema': 'nes-closure-phase32-residue-inventory-v1',
        'status': 'unaccepted_partial_experiments_preserved',
        'analysis_and_source_script_files': {p: v for p, v in residues.items() if not p.startswith('.toolchain/')},
        'observer_toolchain_files': {p: v for p, v in residues.items() if p.startswith('.toolchain/')},
        'file_count': len(residues), 'total_bytes': sum(v['bytes'] for v in residues.values()),
        'file_count_kind': 'residue paths including build objects and git metadata; not cases or accepted deliverables',
        'groups': {'analysis': sum(p.startswith('analysis/') for p in residues),
            'scripts': sum(p.startswith('scripts/') for p in residues),
            'Source': sum(p.startswith('source/') for p in residues),
            'toolchain': sum(p.startswith('.toolchain/') for p in residues)},
        'zero_byte_files': [p for p, v in residues.items() if v['bytes'] == 0],
        'receipt_pin_checks': pin_receipts, 'missing_formal_outputs': absent,
        'source_smoke': {'receipt': ev(S32, 32, 'bounded_source_CPU_smoke'),
            'status_as_written': s32['status'],
            'parent_cases': s32['original_CPU_parent_case_count'],
            'complete_short_declared_plans': s32['complete_event_plan_count'],
            'guards': s32['source_guard_case_count'], 'failed': s32['failed_count'],
            'Native_video_frames_claimed': s32['Native_video_frames_claimed'],
            'source_original_CPU_callbacks': s32['source_original_CPU_callbacks'],
            'production_IR_interpretation': s32['source_IR_interpretation'],
            'rows': s32['rows'], 'exploratory_regression_copy_byte_identical': same_copy,
            'count_duplicate_as_new_run': False,
            'limits': 'Three default plans are only 2 cycles, partial_plan=true, controlled E066 REG fixtures; the fourth is the ECEE controlled continuation regression. No full 1551 UI or actual E066 context.'},
        'historical_text_inconsistency': {'design_status': read('analysis/phase32/source-continuity/design.json')['status'],
            'validation_limits_still_say_authored_without_execution': any('without execution' in x for x in s32['limits']),
            'interpretation': 'Author-time design/README/limits were not updated after Root smoke. Preserve both time layers; receipt rows support only bounded smoke, not a formal phase32 release.'},
        'fields_draft': {'receipt': ev(F32, 32), 'status_as_written': read(F32)['status'],
            'metadata_deltas_from_phase31': metadata_deltas,
            'CPU_cases_executed_as_reported': read(F32)['original_CPU_contract_cases'],
            'model_checks_as_reported': read(F32)['model_guard_check_count'],
            'planned_full_CPU_cases_not_executed': read(F32)['planned_full_original_CPU_cases'],
            'planned_quick_CPU_cases_not_executed': read(F32)['planned_quick_original_CPU_cases'],
            'acceptance': 'No adoption: static validator pin is stale and no current CPU receipt exists.'},
        'original_prefix': {'receipt': ev(P32, 32, 'single_original_run_prefix'),
            'frames': p32['frames'], 'state_imports': p32['state_imports'],
            'cold_boot': p32['cold_boot'], 'fresh_repeat_proven': p32['fresh_repeat_proven'],
            'internal_CPU_trace': p32['internal_CPU_trace'],
            'same_complete_buffer_hash_counts': h32['same_complete_buffer_hash_counts'],
            'claim_limit': 'One original-only import/run, no fresh observer-equivalence receipt. Ends day30/main7/7/mode10; no new nonempty settlement.'},
        'observer_pairing': {'producer': ev(producer, 32, 'unexecuted_incomplete_producer'),
            'declared_OBSERVER_SHA': match.group(1),
            'observer_dylibs': {p: fingerprint(p) for p in builds},
            'declared_matches_observed32': match.group(1) == fingerprint(observed)['sha256'],
            'acceptance': 'Compiled residuals are not a run. Producer, observed copy and last build are not an accepted matching release.'}}
    save('phase32-residue-inventory.json', phases)

    phase31_summary = {'schema': 'nes-closure-formal-phase31-inventory-v1',
        'status': 'formal_frozen_baseline_receipts_current_hash_verified',
        'audit': ev(BASE, 31), 'package_receipt': ev('analysis/phase31/package-receipt.json', 31),
        'archive': ev('build/三国志2超级版-逆向分析-v31增量.zip', 31),
        'CPU_contracts': {'receipt': ev(CPU31, 31), 'original_CPU_cases': 13998, 'actual_RTS': 13992, 'explicit_prefixes': 6, 'models': 29},
        'Source': {'receipt': ev(SRC31, 31), 'parent_cases': 325, 'RTS': 317, 'strict_prefixes': 8,
            'guards': 0, 'per_case_new_Engine': True, 'continuous_single_instance_UI': False},
        'Native': {'receipt': ev(NAT31, 31),
            'counts': {k: v for k, v in read(NAT31).items() if k in ['routes', 'fresh_process_runs', 'first_original_frames', 'all_control_frames',
                    'nonempty_repeat_checks', 'PNG_checks', 'WAV_checks', 'observer_events', 'software_snapshots', 'cold_boots', 'state_imports']},
            'natural13_all_seven_phases_continuous': True, 'human14_phase1_to6': False,
            'natural_mode2_temporary_list_nonempty': False},
        'statement': 'Historical CPU/Source/Native receipt results are preserved and hash-checked, not reexecuted by this audit.'}
    save('formal-phase31-inventory.json', phase31_summary)

    # Human-readable tables use the same objects as the JSON registers.
    textfile('coverage-table.md', '''# 覆盖对照（固定分母）

| 账本/状态 | 分母 | 条件排除 | possible | unknown | 剩余 |
|---|---:|---:|---:|---:|---:|
| 31正式账本 | 1526 | 1201 | 80 | 245 | 325 |
| 32现存草稿（与31相同） | 1526 | 1201 | 80 | 245 | 325 |
| 32尚未执行的两行提案（未采纳） | 1526 | 1203 | 80 | 243 | 323 |

| raw窗口账本 | 总数 | operand重叠 | 声明数据重叠 | 尚无可信入口 |
|---|---:|---:|---:|---:|
| 冻结31/现存32 | 345 | 104 | 13 | 228 |

325与345/228不能相加为唯一问题数。实际字节区间无重叠，只是物理关系，不证明语义依赖互斥。
325条剩余访问完整投影到96个历史分工容器（45 known/51 unknown producer）；这些容器不是96个已证明的真实服务或根因。
城市+1、+28、+29、+30、+31的正式名称均为null。条件排除不是unused/padding/reserved证明。

完整原行身份、来源数组位置和映射见 [unique-gap-register.json](unique-gap-register.json)。''')
    table = ['# 唯一验收对象和待证依赖', '',
        '这些对象用于去重和安排验收，不代表已知的唯一语义缺陷总数；该总数仍为null。每条原始访问/窗口都保留独立ID。', '',
        '| ID | 对象 | 原行数 | 依赖 | 下一步 |', '|---|---|---:|---|---|']
    for g in gaps:
        table.append(f"| {g['gap_id']} | {g['title']} | {len(g['source_row_ids'])} | {', '.join(g['dependencies']) or '无前置包'} | {g['concrete_next_work'][0]} |")
    table += ['', 'B517两行共享已识别的current-JSR验证依赖；其他行真实语义根因未证时保留null。raw104/13按现有有界重叠分类映射gap=null，不推断全局不可能存在替代入口。',
        '', '每对象的来源路径、hash、阶段、观察/推导类型、影响、验收条件和下一步详见 [JSON清单](unique-gap-register.json)。']
    textfile('gap-table.md', '\n'.join(table))
    table = ['# 固定十维验收', '', '| 维度 | 当前结论 | 说明 |', '|---|---|---|']
    for d in matrix:
        table.append(f"| {d['dimension_id']} {d['title']} | {d['current_audit_status']} | {d['current_interpretation']} |")
    table += ['', '只采用31最终分项和当前字节证据；历史滚动remaining_gap不自动成为新的任务。原始11条请求及其定位仍由冻结request register保留。',
        '', '独立可玩重制为可选扩展；未新增独立周期硬件模拟器、任意中断交错穷尽或无限随机测试义务。']
    textfile('acceptance-table.md', '\n'.join(table))
    table = ['# 收尾工作包（WP01本次完成，其余本次不执行）', '', '| 顺序 | 工作包 | 状态 | 依赖 | 验收产物 |', '|---|---|---|---|---|']
    for p in packages:
        table.append(f"| {p['work_package_id']} | {p['title']} | {p['status']} | {', '.join(p['dependencies']) or '无'} | {'；'.join(p['acceptance_artifacts'])} |")
    table += ['', 'WP01之后可并行进行合同、入口、原机路线与服务图工作。WP04使用相关真实消费者合同，不必等待全部账本关闭；WP06可独立建立合法自然路线；WP08按选定路线等待真实现场及实际阻塞服务。',
        '', '以上依赖表示当前建议安排，不是新增的逻辑硬前提。human14合法路线可独立取得；字段语义只需其真实消费者合同。最短Source路线在本路线阻塞服务和真实初态就绪后可先验，全局闭包可继续并行。',
        '', '剩余轮数估计=null：没有逐义务工时或合法路线获取率数据支持区间。案例数量不能换算轮数。',
        '', '本次完成清点与计划即停止，等待父级评估；不会自动开始32补丁或33。']
    textfile('work-packages.md', '\n'.join(table))
    textfile('README.md', f'''# NES逆向收尾清点审计 · 2026-10-18

**本次审计通过只表示清单、引用和冻结输入一致；整款逆向尚未完成。** 第31阶段是正式基线，第32阶段保留为未验收实验附件，本次没有新运行CPU、Source验证器或原模拟器。

正式字段账本仍为1526条中的1201条条件排除、80条possible、245条unknown，剩325条。城市+1及+28..31正式名称均为null。32两行提案1203/80/243未执行、未采纳；raw345=104/13/228是另一账本，不能相加成唯一缺口数。

本次按协调方报告的恢复指令改做全项目审计，停止32实现/搜索；该报告与原始人类请求分开标注。当前恢复turn `01a14d7e-26f3-70c2-bcd2-01087fadf653` 实际读取为inProgress/error=null；已产生本目录清点产物。前一次32 turn `01a14284-3ae8-7051-bfc2-204061f57ded` 状态failed，原错误全文：

> You’ve hit your usage limit. Visit https://chatgpt.com/settings/usage to purchase more credits or try again at Oct 22nd, 2026 4:07 PM.

这是历史错误，不表示当前账户限制。完整来源类型及读取元数据见 [scope-provenance.json](scope-provenance.json)。

## 正式成果与32残留

| 类别 | 已有证据 | 限制 |
|---|---|---|
| 31字段原CPU合同 | 13998案=13992 RTS+6裸后缀前缀，29模型检查 | 有界合同，不是Source或Native |
| 31可读Source | 325案=317 RTS+8故意缺服务前缀，0guard | 每case新Engine，不是1551连续UI |
| 31原模拟器 | 4路线、16fresh、2204首跑/8816控制帧，五完整buffer逐帧等价 | natural13全7阶段已覆盖；14仅phase0；自然mode2名单空 |
| 32 Source实验 | 3×2软件周期+1 ECEE回归，4短计划/1guard | E066寄存器夹具，无实际E066初态；duplicate smoke不重复计数 |
| 32字段草稿 | 报告28静态模型检查、CPU0；full14093/quick285只是计划 | validator pin陈旧，无当前full CPU回执，正式分类未变 |
| 32原核前缀 | 一次7610帧、一次导入、0新增准备，五hash与历史各7610/7610相同 | 非fresh observer验收；末态day30/main7/7/mode10，未新触发非空结算 |

32前缀导入31自然AI祖先segment06母档；本段0新增准备不取代上游导入和继承历史，完整范围仍见31 ancestry。32 design/README仍写作者未执行，与后来Root短smoke处于不同时点，旧文件保持原样。32 producer仍绑定旧31观察核，32 observed副本和最后编译核也未形成一致的验收版本；编译产物不是运行证据。32无正式runtime、总verification、acceptance、HTML或封包。详情和逐文件hash见 [phase32-residue-inventory.json](phase32-residue-inventory.json)。其中0B VRAM占位不作有效缓冲证据。

## 可审阅材料

- [覆盖对照表](coverage-table.md) / [机器可读对照](coverage-comparison.json)
- [缺口和依赖表](gap-table.md) / [全部原行ID映射](unique-gap-register.json)
- [固定十维验收表](acceptance-table.md) / [机器可读矩阵](frozen-acceptance-matrix.json)
- [后续工作包](work-packages.md) / [依赖与停止条件](work-packages.json)
- [正式31清点](formal-phase31-inventory.json)
- [本次只读核验回执](verification.json) / [输入hash清单](input-hash-manifest.json)

剩余关键流程是自然**非空**mode2的实际分配/callee/返回、真实>=11名单的human14 phase1..6、一次真实E066初态的单Source实例完整UI和关键中断边界，以及可达服务闭包。共同设备夹具与原核五buffer分开验收；本次没有新增独立硬件模拟器或重制义务。

32之前的正式91929 artifact/dependency pins及596 source/script pins在本次开始和结束分别只读核对；32全体残留（含观察核工具链）按发现状态冻结。不修旧草稿、不重跑producer、不重打旧大包。审计器仅使用标准库读文件和hash，写入范围限本目录。新增输出hash清单排除它自身和最终verification，避免自引用；verification记录输出hash清单的hash。

本次不计新增游戏CPU/Source/Native成功，未给完成百分比或剩余轮数（均null）。完成此材料整理后停止，等待父级评估。
''')

    # All evidence references must exist and point to the current frozen bytes.
    references = []
    def collect(obj):
        if isinstance(obj, dict):
            if 'path' in obj and 'sha256' in obj and isinstance(obj['path'], str):
                references.append((obj['path'], obj['sha256']))
            for v in obj.values():
                collect(v)
        elif isinstance(obj, list):
            for v in obj:
                collect(v)
    for obj in [coverage, register, phases, phase31_summary, matrix]:
        collect(obj)
    assert all(fingerprint(p)['sha256'] == h for p, h in references)
    input_manifest = {'schema': 'nes-closure-input-hash-manifest-v1',
        'formal_phase31_audit': ev(BASE, 31),
        'phase31_expected_maps': maps,
        'additional_anchors': ANCHORS,
        'phase32_residue_sha256_and_size': residues,
        'evidence_reference_sha256': {p: h for p, h in references},
        'limits': 'Read-only hashes prove identity/integrity, not reexecution. Historic receipt claims are not new CPU/Native successes.'}
    save('input-hash-manifest.json', input_manifest)
    HASH_CACHE.clear()  # A genuinely new end-of-audit content pass, inode dedup only within this pass.
    after, final_errors = frozen_check(pins)
    residue_after = {p: fingerprint(p) for p in residue_paths()}
    assert after == before and not final_errors
    assert residues == residue_after
    gap_ids = {g['gap_id'] for g in gaps}
    assert len(gap_ids) == len(gaps)
    assert all(r['gap_id'] is None or r['gap_id'] in gap_ids for r in instruction_map + window_map)
    assert len({r['source_row_id'] for r in instruction_map}) == 1526
    assert len({r['source_row_id'] for r in window_map}) == 345
    assert sum(r['gap_id'] is not None for r in instruction_map) == 325
    assert sum(r['gap_id'] is not None for r in window_map) == 228
    known_packages = set()
    for p in packages:
        assert set(p['dependencies']) <= known_packages
        assert set(p['gap_ids']) <= gap_ids
        known_packages.add(p['work_package_id'])
    outputs = {str(p.relative_to(ROOT)): fingerprint(p) for p in sorted(OUT.iterdir())
               if p.is_file() and p.name not in ('verification.json', 'output-hash-manifest.json')}
    save('output-hash-manifest.json', {'schema': 'nes-closure-output-hashes-v1', 'files': outputs,
        'excluded': ['output-hash-manifest.json', 'verification.json'],
        'reason': 'Avoid self-referential digest cycle; verification pins this manifest.'})
    verification = {'schema': 'nes-closure-readonly-verification-v1', 'status': 'passed',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Input integrity, inventory/counts/dedup/reference consistency only.',
        'checks': {'formal_map_counts': {k: len(v) for k, v in maps.items()},
            'unique_formal_pin_paths': 91929, 'unique_paths_with_anchors': len(pins),
            'source_pins_subset_artifact_pins': True,
            'included_external_partition_disjoint_and_complete': True,
            'pin_map_conflicts': conflicts,
            'full_start_and_end_content_hash_passes': 2,
            'formal_pin_mismatches': final_errors, 'formal_bytes_unchanged': after == before,
            'phase32_residue_files': len(residues), 'phase32_residue_bytes': sum(x['bytes'] for x in residues.values()),
            'phase32_residue_unchanged': residues == residue_after,
            'all_instruction_id_count': len(instruction_map), 'remaining_instruction_mapping_count': 325,
            'original_ROM_instruction_byte_and_offset_checks': 1526,
            'original_ROM_raw_window_byte_and_offset_checks': 345,
            'raw_window_id_count': len(window_map), 'raw_entry_unproved_mapping_count': 228,
            'historical_container_count': 96, 'semantic_root_count': None,
            'matrix_dimensions': len(matrix), 'gap_reference_integrity': True,
            'work_package_DAG_and_references_valid': True,
            'evidence_reference_checks': len(references), 'all_evidence_hashes_current': True,
            'phase31_phase32_actual_instruction_identity_classifications_authoritative_contracts_identical': True,
            'phase32_metadata_changed_rows': len(metadata_deltas),
            'phase31_phase32_raw_window_rows_identical': True,
            'raw_instruction_byte_overlap_count': len(overlap),
            'all_formal32_outputs_absent': True,
            'phase32_receipt_stale_pin_count': sum(x['mismatch_count'] for x in pin_receipts)},
        'input_hash_manifest': ev(str((OUT / 'input-hash-manifest.json').relative_to(ROOT)), None, 'this_audit_manifest'),
        'output_hash_manifest': ev(str((OUT / 'output-hash-manifest.json').relative_to(ROOT)), None, 'this_audit_manifest'),
        'this_audit_new_execution': {'original_CPU_cases': 0, 'Source_cases': 0, 'Native_frames': 0,
            'emulator_processes': 0, 'compilations': 0, 'old_producers_executed': 0},
        'overall_reverse_engineering_complete': False, 'completion_percentage': None,
        'unknown_unique_services': None, 'remaining_rounds_estimate': None,
        'self_hash_included': False, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'stop': 'Audit finished; no automatic phase32 implementation or phase33.',
        'limitations': ['Stale/unaccepted phase32 receipts are preserved as findings, not repaired or promoted.',
                       'Old package CRC/extraction results are inherited by current byte-identical receipt/archive; this audit did not reextract.',
                       'No claim of new whole-game closure, natural-route success or independent hardware synthesis.']}
    save('verification.json', verification)
    print(json.dumps({'status': verification['status'], 'checks': verification['checks'],
                      'elapsed_seconds': verification['elapsed_seconds']}, ensure_ascii=False), flush=True)


def verify_only():
    v = read(str((OUT / 'verification.json').relative_to(ROOT)))
    for name in ('input_hash_manifest', 'output_hash_manifest'):
        assert fingerprint(v[name]['path'])['sha256'] == v[name]['sha256']
    m = read(str((OUT / 'input-hash-manifest.json').relative_to(ROOT)))
    pins = dict(m['phase31_expected_maps']['artifact_and_dependency_sha256'])
    pins.update(m['additional_anchors'])
    _, errors = frozen_check(pins)
    assert not errors, errors[:5]
    assert {p: fingerprint(p) for p in residue_paths()} == m['phase32_residue_sha256_and_size']
    outputs = read(str((OUT / 'output-hash-manifest.json').relative_to(ROOT)))
    assert all(fingerprint(p) == expected for p, expected in outputs['files'].items())
    for p, digest in m['evidence_reference_sha256'].items():
        assert fingerprint(p)['sha256'] == digest
    print(json.dumps({'read_only_verify': 'passed', 'formal_unique_pins_plus_anchors': len(pins),
                      'phase32_files': len(m['phase32_residue_sha256_and_size']),
                      'output_files': len(outputs['files']), 'CPU_Source_Native_executed': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    verify_only() if args.verify_only else build()
