#!/usr/bin/env python3
"""Text/AST-only phase32 driver contract; never execute CPU/core/source bodies."""
from pathlib import Path
import argparse
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis/phase32/source-continuity'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-only', action='store_true',
                   help='Require a Root-executed runtime receipt before writing evidence')
    args = p.parse_args()
    source = ROOT/'source/recovered/postbattle_continuity_phase32.py'
    validator = ROOT/'scripts/verify_postbattle_continuity_phase32.py'
    tree = ast.parse(source.read_text())
    ast.parse(validator.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom): imports.append(node.module)
        assert not isinstance(node, ast.Import), 'Driver should have no runtime engine/CPU imports'
    assert imports == ['campaign_session']
    writes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            expression = ast.unparse(node)
            if expression.startswith('self.memory.'):
                writes.append(dict(line=node.lineno, target=expression))
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            assert not ast.unparse(node).startswith('self.memory['), \
                'No gameplay/stack/port byte may be assigned by this driver'
    assert [x['target'] for x in writes] == ['self.memory.controller_buttons']
    report = dict(schema='phase32-continuity-design-and-evidence-v1',
        status='authored_static_only_runtime_not_executed',
        production_class='PostbattleContinuity',
        source_sha256={str(x.relative_to(ROOT)): sha(x) for x in (source, validator, Path(__file__))},
        new_gameplay_algorithm_count=0, new_scene_service_owner_count=0,
        source_original_CPU_callbacks=0, source_IR_interpretation=False,
        AST_checks=dict(imports=imports, hardware_input_attribute_assignments=writes,
                        gameplay_subscript_stores=0),
        retained_objects=['GameEngine','SceneCoordinator','ServiceMemory','registers','CampaignSession'],
        pending_lifetime='Same phase, ServiceCall, owner and generator until real caller completion or reset retirement',
        completed_callee_lifetime='A later distinct completed call may own a fresh controller, as in frozen SceneCoordinator',
        hardware_inputs=['physical controller bytes','explicit port read sequences','explicit NMI/IRQ arrivals'],
        scheduling='Driver schedules nothing; validator declares a software main/NMI/IRQ policy, not Native video timing',
        initial_contexts=['actual captured E066 software context plus explicit common device fixture',
                          'clearly labelled E066 register fixture with inherited Native memory'],
        missing_dependencies='Strict prefix; no service success, PC/SP restoration or ready/62/87/result/RNG patch is fabricated',
        author_execution=dict(CPU=False, Native_core=False, old_producer=False, source_body=False, text_AST_only=True),
        runtime_counts=None)
    receipt = OUT/'validation.json'
    if receipt.exists():
        x = json.loads(receipt.read_text())
        for rel, pin in x['source_sha256'].items():
            assert sha(ROOT/rel) == pin, ('Stale Root runtime pin', rel)
        assert x['source_original_CPU_callbacks'] == 0 and x['source_IR_interpretation'] is False
        report.update(status='root_runtime_receipt_available',
            runtime_receipt=dict(path=str(receipt.relative_to(ROOT)), sha256=sha(receipt)),
            runtime_counts={k:x[k] for k in ('status','original_CPU_parent_case_count',
                'complete_event_plan_count','strict_prefix_count','nonlocal_return_count',
                'reset_boundary_count','source_guard_case_count','failed_count')})
    elif args.evidence_only:
        raise SystemExit('No Root-executed phase32 validation.json; runtime status remains unexecuted')
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT/('evidence.json' if receipt.exists() else 'design.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], output=str(target.relative_to(ROOT))), ensure_ascii=False))


if __name__ == '__main__':
    main()
