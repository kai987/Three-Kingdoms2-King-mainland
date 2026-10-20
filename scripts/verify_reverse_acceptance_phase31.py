#!/usr/bin/env python3
"""Read-only evidence/acceptance checks; no gameplay or historical producer runs."""
from pathlib import Path
from collections import Counter
import ast
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase31/acceptance'
BASE_AUDIT = '6cabf530d87046ca0df8d13775b8180b793c92a4a51ed1ab2772533bfb00d4d5'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def literal(node):
    return node.value if isinstance(node, ast.Constant) else None


def main():
    req = read(OUT / 'requirements.json')
    provenance = read(OUT / 'request-provenance.json')
    assert req['status'] == 'documented_acceptance_gaps_not_whole_ROM_complete'
    assert req['scaffold_status'] == 'final_evidence_reviewed', 'New31 scaffold remains pending formal evidence'
    assert all('PENDING' not in json.dumps(row['phase31_change']) for row in req['dimensions'])
    assert req['overall_reverse_engineering_complete'] is False and req['completion_percentage'] is None
    assert 'Phase31 final' in req['assessment_limit'] and 'no automatic32' in req['assessment_limit']
    assert sha(ROOT / 'analysis/phase30/verification.json') == BASE_AUDIT
    oldreq = read(ROOT / 'analysis/phase30/acceptance/requirements.json')
    oldpro = read(ROOT / 'analysis/phase30/acceptance/request-provenance.json')
    assert req['user_request_register'] == oldreq['user_request_register']
    assert provenance['request_locators'] == oldpro['request_locators']
    assert provenance['source_messages'] == oldpro['source_messages']
    assert req['previous_parent_assessment'] == oldreq['parent_assessment']
    assert provenance['previous_frozen_provenance_parent'] == oldpro['frozen_provenance_parent']
    assert req['parent_assessment']['path'] == 'analysis/phase30/acceptance/requirements.json'
    assert provenance['frozen_provenance_parent']['path'] == 'analysis/phase30/acceptance/request-provenance.json'
    pins = {'analysis/phase30/verification.json': BASE_AUDIT}
    for path in (OUT / 'requirements.json', OUT / 'request-provenance.json'):
        pins[str(path.relative_to(ROOT))] = sha(path)
    for record in (req['parent_assessment'], req['previous_parent_assessment'],
                   provenance['frozen_provenance_parent'], provenance['previous_frozen_provenance_parent']):
        assert sha(ROOT / record['path']) == record['sha256']
        pins[record['path']] = record['sha256']
    paths = dict(source='analysis/phase31/player-disposition/validation.json',
                 native='analysis/phase31/runtime/validation.json',
                 fields='analysis/phase31/fields-static/verification.json')
    documents = {key: read(ROOT / path) for key, path in paths.items()}
    for key, document in documents.items():
        assert document['status'] == 'passed'
        pins[paths[key]] = sha(ROOT / paths[key])
    source, native, fields = (documents[key] for key in ('source', 'native', 'fields'))
    assert source['quick'] is False and source['new_production_source_modules'] == 0
    assert source['new_gameplay_algorithm_claim'] is False
    assert source['source_original_CPU_callbacks'] == 0 and source['production_IR_interpretation'] is False
    assert len(source['cases']) == source['original_CPU_parent_cases'] == sum(source['counts'].values())
    assert all(row['source_original_CPU_callbacks'] == 0 for row in source['cases'])
    assert fields['original_contract_CPU_cases'] == 13998 and fields['source_CPU_cases'] == fields['Native_runs'] == 0
    assert fields['actual_caller_RTS_CPU_cases'] == 13992 and fields['explicit_prefix_CPU_cases'] == 6
    assert fields['model_guard_check_count'] == 29 and fields['remaining_access_count'] == 325
    assert fields['newly_proved_disjoint_all_count'] == 1
    assert fields['all_indirect_classification_counts'] == dict(proved_disjoint_auxiliary_address_domain=1201,
        possible_city_auxiliary_alias=80, unresolved_pointer_or_index_contract=245)
    facts = req['phase31_current_counts']
    assert facts['source_cases'] == source['original_CPU_parent_cases']
    assert facts['source_comparison_counts'] == source['counts']
    assert facts['source_guards'] == source['source_guard_count']
    assert facts['source_origin_counts'] == dict(Counter(row['origin'] for row in source['cases']))
    assert source['original_CPU_parent_cases'] == 325 and source['counts'] == {'actual_caller_RTS': 317, 'strict_dependency_prefix': 8}
    assert source['source_guard_count'] == 0
    assert facts['source_case_groups'] == dict(new_controlled=192, reused30_BB36_controlled=2, reused30_passive=14, new31_passive=117)
    new_passive = [row for row in source['cases'] if row['case'].startswith('passive31/')]
    assert len(new_passive) == 117
    assert facts['new31_passive_ancestries'] == dict(Counter(row['metadata']['ancestry_origin'] for row in new_passive)) == {'natural_ancestry': 87, 'controlled_ancestry': 30}
    assert facts['new_production_source_modules'] == 0
    assert facts['independent_field_CPU_cases'] == 13998 and facts['field_model_checks'] == 29
    assert facts['new_conditional_exclusions'] == 1 and facts['remaining_candidates'] == 325
    assert facts['native_summary'] == {key: native[key] for key in facts['native_summary']}
    assert native['Source_CPU_cases'] == 0 and native['additional_core_memory_writes'] == 0
    for key, value in dict(routes=4, first_original_frames=2204, all_control_frames=8816,
        fresh_process_runs=16, nonempty_repeat_checks=18639, PNG_checks=4408, WAV_checks=8,
        observer_events=1376552, software_snapshots=297).items():
        assert native[key] == value
    for key in ('all_five_complete_buffers_equal_each_frame', 'initial_API_complete_buffers_equal',
                'all_artifacts_repeat_exact', 'full_serialized_buffers_not_normalized'):
        assert native[key] is True
    dimensions = {row['id']: row for row in req['dimensions']}
    terms = {
        'A01': ['身份', '语义'], 'A02': ['城市辅助', '待验'],
        'A03': ['本轮1处', '325候选'], 'A04': ['复用', '闭包待验'],
        'A05': ['未列为用户必需目标'], 'A06': ['交错待验'],
        'A07': [str(native['all_control_frames']) + '控制帧', '全场景待验'],
        'A08': ['自然', '受控', '待验'], 'A09': ['回执'], 'A10': ['尚未整体完成'],
    }
    assert set(dimensions) == {f'A{index:02}' for index in range(1, 11)}
    assert 'BB8C→BC46→BB8F' in dimensions['A06']['phase31_change']['result']
    for ident, expected in terms.items():
        row = dimensions[ident]
        assert row['summary_reviewed_phase'] == 31
        assert all(term in row['acceptance_status_zh'] for term in expected), (ident, row['acceptance_status_zh'])
    users = {row['id'] for row in req['user_request_register']}
    assert users == {f'U{index:02}' for index in range(1, 12)}
    locators = {row['request_id']: row for row in provenance['request_locators']}
    messages = {row['message_id']: row for row in provenance['source_messages']}
    assert set(locators) == users
    for row in req['user_request_register']:
        locator = locators[row['id']]
        message = messages[locator['message_id']]
        assert row['quote'] in message['text'] and message['source_kind'] == 'read_thread_userMessage'
        assert message['turn_id'] == locator['turn_id'] == row['source']['turn_id']
        assert row['source']['message_id'] == locator['message_id']
        assert row['source']['source_thread_id'] == message['source_thread_id'] == provenance['source_thread_id']
        assert row['source']['source_kind'] == 'direct_human_userMessage'
    report = req['coordination_and_continuation']
    assert report['source_kind'] == 'coordinator_delegation_report' and report['not_verbatim_user_quote'] is True
    assert report['execution_boundary'] == provenance['coordination_report']['execution_boundary']
    assert report['source_thread_id'] != provenance['source_thread_id']
    evidence = []
    for row in req['dimensions']:
        assert row['requirement_kind'] in ('user_explicit', 'engineering_suggestion', 'mixed')
        assert set(row['user_request_ids']) <= users
        assert row['acceptance_status'] in ('verified_within_declared_scope', 'partially_verified', 'not_requested_extension', 'not_complete')
        assert row['current_scope'] and row['gaps'] and row['pending_results'] and row['verified_results'] and row['acceptance_method']
        assert row['phase31_change']['result'] and row['phase31_change']['remaining_gap']
        for result in row['verified_results']:
            assert result['claim'] and result['receipt_kind'] and result['evidence'] in row['evidence']
        for name in row['evidence']:
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts and not any(part.startswith('exploratory') for part in path.parts)
            assert (ROOT / path).is_file(), name
            pins[name] = sha(ROOT / path)
            evidence.append(dict(dimension=row['id'], path=name, sha256=pins[name]))
    inventory, externals, boundaries = [], [], []
    for path in sorted((ROOT / 'source/recovered').glob('*.py')):
        text = path.read_text()
        tree = ast.parse(text)
        name = str(path.relative_to(ROOT))
        pins[name] = sha(path)
        local_external, local_boundary = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == '_external':
                    args = [literal(value) for value in node.args]
                    local_external.append(dict(path=name, line=node.lineno,
                        callsite_literal=args[0] if args else None, target_literal=args[1] if len(args) > 1 else None))
                if (isinstance(node.func, ast.Attribute) and node.func.attr == '_result' and node.args and literal(node.args[0]) == 'dependency'
                    or any(value.arg == 'status' and literal(value.value) == 'dependency' for value in node.keywords)):
                    local_boundary.append(dict(path=name, line=node.lineno, kind='declared_dependency_return'))
            elif isinstance(node, ast.Dict) and any(literal(key) == 'status' and literal(value) == 'dependency' for key, value in zip(node.keys, node.values)):
                local_boundary.append(dict(path=name, line=node.lineno, kind='declared_dependency_return'))
        externals.extend(local_external)
        boundaries.extend(local_boundary)
        inventory.append(dict(path=name, sha256=pins[name],
            function_definitions=sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree)),
            declared_external_call_sites=len(local_external), declared_dependency_markers=len(local_boundary)))
    save('source-dependency-inventory.json', dict(schema='phase31-source-syntax-not-service-total-v1', status='inventoried',
        source_file_count=len(inventory), inventory=inventory, external_sites=externals,
        dependency_markers=boundaries, unknown_unique_services=None, whole_game_service_closure_proven=False,
        original_CPU_cases=0, source_CPU_cases=0, Native_frames=0,
        limits=['Syntax markers are not entry reachability, resolved owner or a missing-service count.']))
    lines = ['# 阶段31十维验收与范围', '',
        '保留冻结30的11项直接人类原quote与逐turn/message定位。本轮继续范围由coordinator report单列，不编造新的直接人类逐字引用。', '',
        '本脚本只核引用、身份、摘要和Source AST，原CPU/Source/Native新增执行均0。Source复用和独立字段合同按各自正式回执计数，不以case或候选数计算整体完成率。阶段31结束待评估，不自动32。', '']
    for row in req['dimensions']:
        lines += ['## ' + row['id'] + ' · ' + row['title'], '', '**' + row['acceptance_status_zh'] + '**', '',
                  '本轮变化：' + row['phase31_change']['result'], '', '保留缺口：' + row['phase31_change']['remaining_gap'], '',
                  '现有范围：' + row['current_scope'], '', '已验结果及回执：', '']
        lines += ['- ' + value['claim'] + ' [' + value['receipt_kind'] + '](' + os.path.relpath(ROOT / value['evidence'], OUT) + ')' for value in row['verified_results']]
        lines += ['', '待验：', ''] + ['- ' + value for value in row['pending_results']] + ['', '验收方法：', '']
        lines += [f'{index}. {value}' for index, value in enumerate(row['acceptance_method'], 1)] + ['']
    lines += ['## 复现', '', '`python3 scripts/verify_reverse_acceptance_phase31.py` 只生成新31验收输出；不执行历史producer、CPU或核心。最终BQA/总审计/包状态另见本轮正式回执。', '']
    (OUT / 'README.md').write_text('\n'.join(lines))
    for name in ('README.md', 'source-dependency-inventory.json'):
        pins[str((OUT / name).relative_to(ROOT))] = sha(OUT / name)
    result = dict(schema='phase31-acceptance-inventory-validation-v1', status='passed',
        dimensions=10, request_excerpts=11, direct_user_message_locator_checks=11,
        current_summary_cross_receipt_checks=10, evidence_reference_checks=len(evidence),
        source_syntax_checks=len(inventory), phase31_current_counts=facts,
        original_CPU_cases=0, source_CPU_cases=0, Native_frames=0,
        overall_reverse_engineering_complete=False, completion_percentage=None,
        unknown_unique_services=None,
        source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)): sha(__file__)},
        artifact_and_dependency_sha256=pins,
        limits=['Passing checks document/reference/schema/syntax consistency; not new gameplay or whole-ROM completion.'])
    save('verification.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'dimensions', 'request_excerpts',
        'evidence_reference_checks', 'source_syntax_checks', 'overall_reverse_engineering_complete')}))


if __name__ == '__main__':
    main()
