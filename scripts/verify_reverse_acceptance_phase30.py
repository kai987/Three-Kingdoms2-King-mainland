#!/usr/bin/env python3
"""Check the evidence-backed acceptance inventory without running gameplay.

This validates request/evidence references and inventories source boundaries.
An external call marker is not a missing-service count or a reachable entry.
It neither executes old producers nor overwrites any frozen phase.
"""
from pathlib import Path
from collections import Counter
import ast, hashlib, json, os

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase30/acceptance'
BASE_AUDIT='177c7d2d27dc3f5fd9840f90802be752befa3dd7ae885e867e9c110432f68a15'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def literal(node):return node.value if isinstance(node,ast.Constant)else None

def main():
    requirement_path=OUT/'requirements.json'
    req=json.loads(requirement_path.read_text())
    provenance_path=OUT/'request-provenance.json'
    provenance=json.loads(provenance_path.read_text())
    assert req['status']=='documented_acceptance_gaps_not_whole_ROM_complete'
    assert req['scaffold_status']=='final_evidence_reviewed', 'Phase30 scaffold is not final'
    assert all('PENDING'not in json.dumps(r['phase30_change'])for r in req['dimensions']), 'Pending phase30 conclusions'
    for parent in (req['parent_assessment'],provenance['frozen_provenance_parent'],req['previous_parent_assessment'],provenance['previous_frozen_provenance_parent']):
        assert sha(ROOT/parent['path'])==parent['sha256']
    assert req['overall_reverse_engineering_complete'] is False and req['completion_percentage'] is None
    oldreq=json.loads((ROOT/'analysis/phase29/acceptance/requirements.json').read_text())
    oldpro=json.loads((ROOT/'analysis/phase29/acceptance/request-provenance.json').read_text())
    assert req['user_request_register']==oldreq['user_request_register']
    assert provenance['request_locators']==oldpro['request_locators']and provenance['source_messages']==oldpro['source_messages']
    assert req['previous_parent_assessment']==oldreq['parent_assessment']
    assert provenance['previous_frozen_provenance_parent']==oldpro['frozen_provenance_parent']
    assert req['parent_assessment']['path']=='analysis/phase29/acceptance/requirements.json'
    assert provenance['frozen_provenance_parent']['path']=='analysis/phase29/acceptance/request-provenance.json'
    assert sha(ROOT/'analysis/phase29/verification.json')==BASE_AUDIT
    users={r['id'] for r in req['user_request_register']}
    assert users=={f'U{i:02}' for i in range(1,12)}
    assert {r['id']for r in req['dimensions']}=={f'A{i:02}'for i in range(1,11)}
    assert len(req['not_implicitly_required'])==5
    pins={str(requirement_path.relative_to(ROOT)):sha(requirement_path),
          str(provenance_path.relative_to(ROOT)):sha(provenance_path),
          'analysis/phase29/verification.json':BASE_AUDIT}
    # Cross-check the current summary against independent current receipts.
    # Historical per-result claims remain explicitly frozen parent records.
    ledger_path=ROOT/'analysis/phase30/fields-static/verification.json'
    native_path=ROOT/'analysis/phase30/runtime/validation.json'
    ledger=json.loads(ledger_path.read_text());native=json.loads(native_path.read_text())
    assert ledger['status']==native['status']=='passed'
    for path in (ledger_path,native_path):pins[str(path.relative_to(ROOT))]=sha(path)
    parent_source_path=ROOT/'analysis/phase30/early-services/validation.json'
    integration_path=ROOT/'analysis/phase30/source-integration.json'
    parent_source=json.loads(parent_source_path.read_text());integration=json.loads(integration_path.read_text())
    assert parent_source['status']==integration['status']=='passed' and not parent_source['quick']
    assert parent_source['passive_software_caller_cases']==40
    assert parent_source['controlled_cases']==1506 and parent_source['source_guard_count']==11
    assert parent_source['original_CPU_parent_cases']==1546
    assert parent_source['counts']=={'actual_caller_RTS':1540,'strict_dependency_prefix':6}
    assert parent_source['original_CPU_parent_cases']==parent_source['controlled_cases']+parent_source['passive_software_caller_cases']
    assert sum(parent_source['counts'].values())==parent_source['original_CPU_parent_cases']
    assert integration['inherited_regression_cases']==115 and integration['new_controlled_AI_stage0_cases']==2
    assert integration['new_early_caller_cases']==14 and integration['guard_count']==4
    assert integration['comparison_counts']=={'actual_caller_RTS':130,'actual_nonlocal_return':1}
    assert integration['new_early_targets']=={'40966':4,'47795':4,'47809':2,'47933':2,'48198':2}
    assert integration['new_early_ancestries']=={'natural_ancestry':7,'controlled_ancestry':7}
    assert integration['original_CPU_parent_cases']==117+integration['new_early_caller_cases']
    assert sum(integration['comparison_counts'].values())==integration['original_CPU_parent_cases']
    assert parent_source['source_original_CPU_callbacks']==integration['source_original_CPU_callbacks']==0
    assert parent_source['production_IR_interpretation']is integration['production_IR_interpretation']is False
    assert ledger['original_contract_CPU_cases']==7188 and ledger['source_CPU_cases']==0 and ledger['model_guard_check_count']==21
    assert ledger['actual_caller_RTS_CPU_cases']==7172 and ledger['explicit_prefix_CPU_cases']==16
    assert ledger['newly_proved_disjoint_all_count']==2 and ledger['remaining_access_count']==326
    assert native['all_control_frames']==192 and native['original_first_frames']==48 and native['routes']==3
    assert native['fresh_process_runs']==12 and native['additional_core_memory_writes']==0
    assert native['nonempty_artifact_repeat_checks']==879 and native['PNG_checks']==96 and native['WAV_checks']==6
    assert native['actual_BB8C_calls']==2 and native['actual_BB36_calls']==0
    assert native['early_public_software_inputs']==14 and native['changed_early_city_roster_bytes']==4
    assert native['ECEE_immediate_returns']==2 and native['phase3_fresh_hold_callbacks']==23 and native['phase3_completion_callbacks']==1
    facts=req['phase30_current_counts']
    assert facts==dict(source_child_cases=1546,source_child_controlled=1506,
        source_child_reused29_inputs=26,source_child_new30_inputs=14,
        source_child_RTS=1540,source_child_prefix=6,source_child_guards=11,
        root_cases=131,root_RTS=130,root_nonlocal=1,root_prefix=0,root_guards=4,
        two_layer_Source_cases=1677,two_layer_RTS=1670,two_layer_nonlocal=1,two_layer_prefix=6,two_layer_guards=15,
        independent_contract_CPU_cases=7188,contract_RTS=7172,contract_prefix=16,contract_model_checks=21,
        new_conditional_exclusions=2,remaining_candidates=326,
        Native_routes=3,Native_original_frames=48,Native_control_frames=192,Native_fresh_runs=12,
        Native_public_fields_per_checkpoint=35,Native_repeat_artifacts=879)
    for path in (parent_source_path,integration_path):pins[str(path.relative_to(ROOT))]=sha(path)
    summaries={r['id']:r for r in req['dimensions']}
    current_terms={
        'A01':['身份','语义'], 'A02':['归属','城市辅助','待验'],
        'A03':['本轮2处',str(ledger['remaining_access_count'])+'候选'],
        'A04':['四态','闭包待验'], 'A05':['未列为用户必需目标'],
        'A06':['交错待验'], 'A07':[str(native['all_control_frames'])+'控制帧','全场景待验'],
        'A08':['自然','受控','待验'], 'A09':['回执'], 'A10':['尚未整体完成'],
    }
    for ident,terms in current_terms.items():
        row=summaries[ident]
        assert row['summary_reviewed_phase']==30,ident
        assert all(term in row['acceptance_status_zh']for term in terms),(ident,row['acceptance_status_zh'])
    assert '自然' in summaries['A08']['phase30_change']['remaining_gap']
    for parent in (req['parent_assessment'],provenance['frozen_provenance_parent'],req['previous_parent_assessment'],provenance['previous_frozen_provenance_parent']):
        pins[parent['path']]=parent['sha256']
    locators={r['request_id']:r for r in provenance['request_locators']}
    messages={r['message_id']:r for r in provenance['source_messages']}
    assert set(locators)==users
    for row in req['user_request_register']:
        loc=locators[row['id']]; message=messages[loc['message_id']]
        assert row['quote'] in message['text'],row['id']
        assert message['source_kind']=='read_thread_userMessage'
        assert message['turn_id']==loc['turn_id']==row['source']['turn_id']
        assert row['source']['message_id']==loc['message_id']
        assert row['source']['source_thread_id']==message['source_thread_id']==provenance['source_thread_id']
        assert row['source']['source_kind']=='direct_human_userMessage'
    report=req['coordination_and_continuation']
    assert report['source_kind']=='coordinator_delegation_report' and report['not_verbatim_user_quote'] is True
    assert report['execution_boundary']==provenance['coordination_report']['execution_boundary']
    assert report['source_thread_id']!=provenance['source_thread_id']
    evidence=[]
    for row in req['dimensions']:
        assert row['requirement_kind'] in ('user_explicit','engineering_suggestion','mixed')
        assert set(row['user_request_ids'])<=users and row['current_scope'] and row['gaps'] and row['acceptance_method']
        assert row['acceptance_status'] in ('verified_within_declared_scope','partially_verified','not_requested_extension','not_complete')
        assert row['acceptance_status_zh'] and row['verified_results'] and row['pending_results']
        assert row['phase30_change']['result'] and row['phase30_change']['remaining_gap']
        for result in row['verified_results']:
            assert result['claim'] and result['receipt_kind'] and result['evidence'] in row['evidence']
        for name in row['evidence']:
            path=Path(name)
            assert not path.is_absolute() and '..'not in path.parts and not any(p.startswith('exploratory')for p in path.parts)
            assert (ROOT/path).is_file(),name
            pins[name]=sha(ROOT/path);evidence.append(dict(dimension=row['id'],path=name,sha256=pins[name]))
    inventory=[];all_external=[];all_boundaries=[]
    for path in sorted((ROOT/'source/recovered').glob('*.py')):
        text=path.read_text();tree=ast.parse(text);relative=str(path.relative_to(ROOT));pins[relative]=sha(path)
        functions=[n for n in ast.walk(tree)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        external=[];boundaries=[];imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append('.'*node.level+(node.module or ''))
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Attribute)and node.func.attr=='_external':
                    args=[literal(v)for v in node.args]
                    external.append(dict(path=relative,line=node.lineno,callsite_literal=args[0]if args else None,target_literal=args[1]if len(args)>1 else None))
                if (isinstance(node.func,ast.Attribute)and node.func.attr=='_result'and node.args and literal(node.args[0])=='dependency'
                    or any(v.arg=='status'and literal(v.value)=='dependency'for v in node.keywords)):
                    boundaries.append(dict(path=relative,line=node.lineno,kind='declared_dependency_return'))
            elif isinstance(node,ast.Dict):
                if any(literal(k)=='status'and literal(v)=='dependency'for k,v in zip(node.keys,node.values)):
                    boundaries.append(dict(path=relative,line=node.lineno,kind='declared_dependency_return'))
        all_external.extend(external);all_boundaries.extend(boundaries)
        inventory.append(dict(path=relative,sha256=pins[relative],function_definitions=len(functions),
                              declared_external_call_sites=len(external),declared_dependency_markers=len(boundaries),
                              imports=imports,legacy_IR_documentation=any('IR'in(ast.get_docstring(n)or'')for n in functions)))
    data=dict(schema='phase30-source-syntax-and-declared-boundaries-v1',status='inventoried',
              source_file_count=len(inventory),function_definition_count=sum(x['function_definitions']for x in inventory),
              declared_external_call_sites=len(all_external),declared_dependency_markers=len(all_boundaries),
              unknown_unique_services=None,whole_game_service_closure_proven=False,
              inventory=inventory,external_sites=all_external,dependency_markers=all_boundaries,
              limits=['Syntax and declared source edges only, not reachability, owner resolution, dynamic coverage or missing-service counts.',
                      'Inherited generated control-shaped Python and legacy IR APIs remain historical surfaces; new named services have their own execution receipts.',
                      'This inventory performs zero CPU comparisons and zero Native frames.'])
    save('source-dependency-inventory.json',data)
    labels={'user_explicit':'用户明确要求','engineering_suggestion':'工程验收建议','mixed':'用户目标与工程验收方法分别标注'}
    lines=['# 整体逆向验收清单与现有缺口','',
           '本清单从本对话中的明确请求及冻结工程记录整理。当前不能宣称全ROM语义源码化；字节重建、多域源码对照和若干完整原流程已有证据。没有用候选减少或累计case数计算完成百分比。','',
           '“尽量整理成可读源码”是已有要求；独立可玩重制、原作者工程、源码编译成相同NES和新硬件模拟器列为建议扩展，没有自动算成用户已经提出的目标。字段确认需要有区分力的读写／实际行为依据，原作者的内部变量名不是要求。','',
           '## 来源与证据边界','',
           '需求摘录及逐维结果见 [requirements.json](requirements.json)。11项逐字摘录的原对话turn/message定位及相关用户原文见 [请求来源](request-provenance.json)，由阶段24通过应用read_thread核对，本轮只读复核其冻结来源及逐字映射；浏览器环境块没有当作请求。历史回执及正文作为归档证据读取，本脚本只核引用、哈希和源码语法，没有重跑历史游戏或覆盖旧输出。后期报告优先于冻结根README的旧阶段标题；新的更强对照不改写旧范围。','',
           '阶段30获准一次的战后前两态与真实BC46调用协议、独立CC29姓名指针合同范围由协调对话报告，来源单列为coordinator_delegation_report，不冒充本对话的直接用户逐字指令。本轮执行边界是完成阶段30后等待父级评估，不自动开始阶段31。','',
           '未知服务总数仍为null。源码中出现external/dependency仅代表声明边界，必须结合实际mapper、entry与owner才能认定某服务缺失。详见 [源码边界清单](source-dependency-inventory.json)。','']
    for row in req['dimensions']:
        lines.extend(['## '+row['id']+' · '+row['title'],'',
                      '来源：'+labels[row['requirement_kind']]+'；关联请求 '+', '.join(row['user_request_ids'])+'。','',
                      '**验收状态：'+row['acceptance_status_zh']+'。**','',
                      '本轮变化：'+row['phase30_change']['result'],'',
                      '本轮后仍缺：'+row['phase30_change']['remaining_gap'],'',
                      '现有范围：'+row['current_scope'],'','已验结果与具体回执：',''])
        lines.extend('- '+r['claim']+' ['+r['receipt_kind']+']('+os.path.relpath(ROOT/r['evidence'],OUT)+')' for r in row['verified_results'])
        lines.extend(['','待验／限制：',''])
        lines.extend('- '+s for s in row['pending_results'])
        lines.extend(['','可执行验收方法：',''])
        lines.extend(f'{i}. {s}'for i,s in enumerate(row['acceptance_method'],1))
        links=['['+name+']('+os.path.relpath(ROOT/name,OUT)+')'for name in row['evidence']]
        lines.extend(['','证据：'+' · '.join(links),''])
    lines.extend(['## 本清单的检查','',
                  '运行 `python3 scripts/verify_reverse_acceptance_phase30.py` 只生成本轮新目录的清单、语法边界及引用回执，不执行游戏。其他需要重放的验收项必须另写新输出driver或使用新空目录；不要直接重跑历史固定OUT生成器。','',
                  '整体状态：尚未全部完成；本清单本身不是新的游戏验证，也不授权推送、发布或扩展成重制工程。',''])
    (OUT/'README.md').write_text('\n'.join(lines))
    artifacts={str((OUT/name).relative_to(ROOT)):sha(OUT/name)for name in('source-dependency-inventory.json','README.md')}
    value=dict(schema='phase30-existing-goals-acceptance-inventory-validation-v1',status='passed',
               dimensions=len(req['dimensions']),request_excerpts=len(users),direct_user_message_locator_checks=len(users),
               dimension_status_and_receipt_checks=len(req['dimensions']),coordinator_report_separately_labelled=True,
               current_summary_cross_receipt_checks=len(current_terms),
               phase30_current_counts=facts,
               dimension_status_counts=dict(Counter(r['acceptance_status']for r in req['dimensions'])),basis_counts=dict(Counter(r['requirement_kind']for r in req['dimensions'])),
               evidence_reference_checks=len(evidence),source_syntax_checks=len(inventory),
               original_CPU_cases=0,source_CPU_cases=0,Native_frames=0,overall_reverse_engineering_complete=False,completion_percentage=None,
               unknown_unique_services=None,source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
               artifact_and_dependency_sha256={**pins,**artifacts},limits=['Passing this receipt means document/schema/reference/syntax consistency only. It is not a gameplay or whole-ROM completion result.'])
    save('verification.json',value)
    print(json.dumps({k:value[k]for k in('status','dimensions','request_excerpts','evidence_reference_checks','source_syntax_checks','overall_reverse_engineering_complete')},ensure_ascii=False))

if __name__=='__main__':main()
