#!/usr/bin/env python3
"""Offline family audit, unchanged ledger copies and final hash seal."""
from pathlib import Path
import argparse,ast,collections,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-shared-entry-family'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)
def save(n,x):
    p=OUT/n;assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def audit():
    scope=read(OUT/'family-scope-v2.json');run=OUT/'run-01';v=read(run/'validation.json');plan=read(OUT/'case-matrix.json');inputs=read(run/'execution-inputs.json')
    assert v['status']=='passed_full_declared_family_matrix'and v['cases_sha256']==sha(run/'cases.jsonl')
    assert v['scope_sha256']==sha(OUT/'family-scope.json')==scope['original_execution_scope_sha256']
    assert inputs['matrix_sha256']==sha(OUT/'case-matrix.json')and (run/'executed-scope.json').read_bytes()==(OUT/'family-scope.json').read_bytes()
    for name,value in inputs['Source_and_scripts_sha256'].items():assert sha(ROOT/name)==value,name
    groups=collections.Counter();counts=collections.Counter();slots=set();callers=set();keys=[];examples=[];generations=[];raw_consumers={};natural=None
    cross=read(OUT/'cross-ledger-relations-v2.json')
    with(run/'cases.jsonl').open()as f:
        for spec,line in zip(plan['cases'],f,strict=True):
            row=json.loads(line);assert row['case']==spec['key']and row['spec']==spec and row['status']=='passed';keys.append(row['case']);groups[row['group']]+=1
            ci=spec['caller_index'];caller=None if ci is None else scope['dynamic_callers'][ci]
            if caller:callers.add((caller['bank'],caller['pc']))
            for p in row['segments']:
                counts['segments']+=1;counts['instructions']+=p['instructions'];counts['actual_JSR']+=p['actual_JSR']is not None
                counts['valid_current_frame']+=p['current_frame_premise_valid'];counts['Source_prefix']+=p['Source_prefix_paired'];counts['selected_reads']+=len(p['selected_reads'])
                assert p['full_RAM_nonwrite_domain_checked']and p['whole_SRAM_unchanged']and not p['actual_caller_RTS']
                assert len(p['executed_positions'])==p['instructions']
                assert p['executed_positions'][-1]==[31,spec['entry']if p['boundary']=='selected_LDA_only'else 0xEAF4]
                if p['current_frame_premise_valid']:
                    call=p['actual_JSR'];word=caller['pc']+2;sp=call['registers']['sp'];generation=p['generation']
                    assert[(w['address'],w['value'])for w in call['pushes']]==[(0x100+sp,word>>8),(0x100+((sp-1)&255),word&255)]
                    assert[x['stack_address']for x in p['actual_PLA_reads']]==[0x100+((sp-1)&255),0x100+sp]
                    assert all(x['last_writer']==dict(kind='primary_JSR',generation=generation,PC=caller['pc'])for x in p['actual_PLA_reads'])
                    assert all(x['live01_02']==word and not x['auxiliary_alias']for x in p['selected_reads'])
                    if p['legal_inline_target']:slots.add((caller['bank'],caller['pc'],p['input_registers']['a']))
                if p['Source_prefix_paired']:assert p['current_frame_premise_valid']and p['legal_inline_target']
                if row['group']=='raw_A_address_axis'and spec['index']==0:
                    raw_consumers[caller['bank'],caller['pc']]=dict(case=row['case'],selected_read=p['selected_reads'][0],initial_banks=p['initial_banks'],Source_prefix_paired=p['Source_prefix_paired'])
            if row['group']in('bare_EADE_aux_counterexample','middle_aux_counterexample','current_frame_fault'):
                examples.append(row)
            if row['controlled_generation_reentry']:
                re=row['controlled_generation_reentry'];assert re['before']['sp']==re['after']['sp'];assert all(re['before'][k]==re['after'][k]for k in('x','p'))
                generations.append(row)
            if spec.get('actual_initial_context'):natural=row
    assert keys==[x['key']for x in plan['cases']]and dict(groups)==plan['groups']
    assert counts==dict(segments=16273,instructions=260289,actual_JSR=16264,valid_current_frame=16256,Source_prefix=4035,selected_reads=32541)
    assert len(callers)==49 and len(slots)==331 and len(generations)==4 and natural is not None
    assert natural['segments'][0]['Source_prefix_paired']
    directory=ROOT/'analysis/wp05-natural-nonempty/runtime/natural-day31-nonempty/observer'
    target=scope['natural_reference']['target'];initial=scope['natural_reference']['initial']
    assert (run/'WP05-replayed-target-ram.bin').read_bytes()==(directory/target['exported_RAM']).read_bytes()
    assert (run/'WP05-replayed-target-sram.bin').read_bytes()==(directory/target['exported_SRAM']).read_bytes()
    wp05=read(ROOT/'analysis/wp05-natural-nonempty/evidence.json');frame=next(x for x in wp05['actual_call_frames']if x['actual_call']['opcode_PC']==0xBC49)
    save('natural-anchor-evidence.json',dict(schema='wp03-existing-natural-anchor-and-new-prefix-replay-v1',initial=initial,target=target,
        initial_metadata=rec(directory/'callee-0022-BC49.json'),initial_RAM=rec(directory/initial['exported_RAM']),initial_SRAM=rec(directory/initial['exported_SRAM']),
        target_RAM=rec(directory/target['exported_RAM']),target_SRAM=rec(directory/target['exported_SRAM']),
        old_actual_current_JSR_frame=frame,new_CPU_Source_prefix_case=natural,
        Native_selected_LDA_or_Pull8_reads_captured=False,new_CPU_replay_records_selected_LDA_and_PLA_reads=True,
        initial_REG_PRG_RAM_SRAM_not_modified=True,new_Native_runs=0,all_other_matrix_inputs_controlled=True))
    save('counterexamples-and-generations.json',dict(counterexamples=examples,two_generation_cases=generations,
        caveat='Same-value external writes invalidate provenance without numeric error; low-level prefixes never execute target body. Two-generation host PC/A/Y reentry is disclosed, not natural target-return continuity.'))
    relations=[]
    for row in cross['operand_byte_relations']:
        case=raw_consumers[row['caller_bank'],row['caller_pc']];assert case['selected_read']['logical_effective_address']==row['caller_pc']+3
        relations.append(dict(**row,actual_controlled_index0_CPU_consumer=case,relation='Two operand bytes plus first inline low byte. Data-consumer provenance, not raw-opcode execution or semantic-root merge.'))
    save('operand-byte-consumer-evidence.json',dict(relations=relations,count=3,raw345_categories_unchanged=True,raw228_to_selected_semantic_relation=None))
    ledger=ROOT/'analysis/wp02-current-jsr-contract'
    for name in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json'):
        assert not(OUT/name).exists();shutil.copyfile(ledger/name,OUT/name);assert(OUT/name).read_bytes()==(ledger/name).read_bytes()
    save('ledger-preservation.json',dict(schema='wp03-no-global-migration-v1',files=[dict(before=rec(ledger/n),after=rec(OUT/n),byte_identical=True)for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json')],
        instruction_objects_unchanged=1526,remaining_objects_unchanged=323,raw_window_objects_unchanged=345,
        selected_scope_only=scope['selected_typed_ids'],excluded_E04D_unchanged=True,classification_changes=0,
        reason='Bounded current-JSR49-caller interface only. Other49 known callers and computed/bare/middle/mapping/interrupt entries not closed; no global row promotion.'))
    save('shared-interface-contract.json',dict(schema='wp03-bounded-shared-EADE-interface-v1',canonical_scope=rec(OUT/'family-scope-v2.json'),
        execution_scope_v1=rec(OUT/'family-scope.json'),ID_normalization=rec(OUT/'typed-ID-normalization.json'),
        shared_dependency='DEP-EADE-CURRENT-JSR-49CALLERS',typed_instruction_ids=scope['selected_typed_ids'],
        resolved_bounded_caller_interfaces=49,resolved_bounded_legal_inline_slots=331,
        known_direct_callers_static_only=49,known_direct_callers_total=98,known_inline_words_total=745,
        premises=['Current original JSR at one locked caller and its original mapped table; both frame bytes retain this generation.',
                  'No external write or interrupts in positive window; raw-byte index addresses separate from legal table slots.',
                  'Boundary is after EAF4 JMP before target first opcode, never RTS or target behavior.'],
        raw_A_address_rule='01/02=current callerPC+2; firstY=(2*A+1)&255, secondY=(2*A+2)&255; each addition uses the whole pointer. Only the locked callers/maps are covered.',
        Source_scope='2845 existing synchronous battle/attack dispatch prefixes (includes inherited postbattle method) plus1190 ControlHelpers-only duel prefixes; no duel handler/whole scene.',
        production_Source_changes=0,new_gameplay_or_service_algorithms=0,unknown_real_dependencies_encountered_in_this_window=0,
        global_reachable_service_closure_proven=False,global_field_classification_changes=0,raw228_semantic_mapping=None))
    save('semantic-validation.json',dict(status='passed_bounded_shared_interface_audit',CPU_parent_cases=16269,**dict(counts),
        dynamic_callers=49,legal_slots=331,static_known_callers=98,static_inline_words=745,
        Source_synchronous_dispatch_prefixes=2845,Source_ControlHelpers_only_prefixes=1190,
        Native_new_runs=0,new_original_CPU_replay_from_WP05_context=1,actual_caller_RTS_cases=0,
        strict_unknown_service_prefixes=0,field_classification_changes=0,raw_classification_changes=0,remaining=323,
        whole_game_closure_proven=False,unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
        original_CPU_or_Source_executions_in_this_audit=0))
    print(json.dumps(dict(status='passed_offline_family_audit',CPU=16269,Source_prefix=4035,ledger_changes=0,remaining=323)))
def seal():
    before=read(OUT/'frozen-before.json');after=read(OUT/'frozen-after.json');assert before['status']==after['status']=='passed'
    assert before['old_work_paths']==after['old_work_paths']==239404 and before['full_work_manifest_sha256']==after['full_work_manifest_sha256']
    run=OUT/'run-01';inputs=read(run/'execution-inputs.json')
    for name,value in inputs['Source_and_scripts_sha256'].items():assert sha(ROOT/name)==value
    for p in(ROOT/'scripts').glob('*wp03*.py'):ast.parse(p.read_text())
    assert read(OUT/'semantic-validation.json')['status']=='passed_bounded_shared_interface_audit'
    save('input-manifest.json',dict(schema='wp03-input-manifest-v1',current_producers=[rec(p)for p in sorted((ROOT/'scripts').glob('*wp03*.py'))],
        actual_execution_inputs=rec(run/'execution-inputs.json'),canonical_scope=rec(OUT/'family-scope-v2.json'),original_execution_scope=rec(OUT/'family-scope.json'),
        ID_version_mapping=rec(OUT/'typed-ID-normalization.json'),frozen_work=rec(OUT/'frozen-work-inputs.json'),frozen_before=rec(OUT/'frozen-before.json'),frozen_after=rec(OUT/'frozen-after.json'),
        previous_authority=rec(ROOT/'analysis/wp02-current-jsr-contract/verification.json'),Native_new_runs=0,ROM_distributed=False,
        production_CPU_IR_fallback_added=False,ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'))
    files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))if p.is_file()}
    save('artifact-manifest.json',dict(files=files,excludes=['artifact-manifest.json','verification.json']))
    save('verification.json',dict(schema='wp03-EADE-family-final-verification-v1',status='passed_bounded_shared_entry_family',
        CPU_parent_cases=16269,CPU_prefix_segments=16273,CPU_primary_JSRs=16264,CPU_instructions=260289,
        Source_prefix_comparisons=4035,Source_synchronous_dispatch_prefixes=2845,Source_ControlHelpers_only_prefixes=1190,
        Source_whole_scene_cases=0,Native_new_runs=0,actual_caller_RTS_cases=0,
        static_known_direct_callers=98,dynamically_checked_callers=49,legal_slots=331,
        WP05_actual_initial_snapshot_replay='exactly matched original target snapshot23; existing natural evidence only',
        old_work_paths_preserved=239404,field_ledger=dict(total=1526,conditional_disjoint=1203,possible=80,unknown=243,remaining=323),
        raw345_independent=dict(total=345,operand=104,data=13,unproved_entry=228),field_classification_changes=0,raw_classification_changes=0,
        official_city_names={str(i):None for i in(1,28,29,30,31)},unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
        whole_game_closure_proven=False,new_Source_services_or_algorithms=0,
        CPU_receipt=rec(run/'validation.json'),semantic_validation=rec(OUT/'semantic-validation.json'),input_manifest=rec(OUT/'input-manifest.json'),artifact_manifest=rec(OUT/'artifact-manifest.json'),
        shared_interface=rec(OUT/'shared-interface-contract.json'),artifact_pins=len(files),
        next_family_readiness='EE07 inline far-entry pair27:A06F/A077 has original call/data byte provenance, but needs a separately locked input/caller matrix and downstream strict boundaries.',
        stop_after_this_family=True,published_or_pushed=False))
    print(json.dumps(dict(status='passed_bounded_shared_entry_family',artifact_pins=len(files),verification_sha256=sha(OUT/'verification.json'),remaining=323)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
