#!/usr/bin/env python3
"""Offline audit/migration/seal; never imports game code or executes a CPU."""
from pathlib import Path
import argparse,ast,collections,copy,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp02-current-jsr-contract'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SELECTED={(8,0xB525),(8,0xB52B)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rel(p):return str(p.relative_to(ROOT))
def record(p):return dict(path=rel(p),sha256=sha(p),bytes=p.stat().st_size)
def save(name,x):
    p=OUT/name;assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def typed(row):return f'I:{ROM_SHA}:b{row["physical_bank"]:02X}:cpu{row["cpu"]:04X}:rom{row["rom_offset"]:06X}'

def audit():
    plan=read(OUT/'case-matrix.json');accept=read(OUT/'acceptance.json');run=OUT/'run-01';receipt=read(run/'validation.json');inputs=read(run/'execution-inputs.json')
    assert receipt['status']=='passed_full_declared_matrix'and receipt['controlled_CPU_parent_cases']==17207
    assert receipt['cases']==record(run/'cases.jsonl')
    assert sha(OUT/'case-matrix.json')==receipt['matrix_sha256']==accept['matrix_sha256']==inputs['matrix_sha256']
    for name,value in receipt['scripts_sha256'].items():assert sha(ROOT/name)==value
    for p in (run/'executed-scripts').iterdir():
        name='scripts/'+p.name;assert sha(p)==receipt['scripts_sha256'][name]
    groups=collections.Counter();instructions=segments=primary=valid=fixed=0;examples=[];generations=[];keys=[]
    expected_keys=[x['key']for x in plan['cases']]
    with(run/'cases.jsonl').open()as stream:
        for spec,line in zip(plan['cases'],stream,strict=True):
            row=json.loads(line);assert row['case']==spec['key']and row['group']==spec['group']and row['spec']==spec and row['status']=='passed'
            keys.append(row['case']);groups[row['group']]+=1
            for part in row['segments']:
                segments+=1;instructions+=part['original_instructions'];fixed+=len(part['F266_entries'])
                primary+=part['actual_primary_JSR']is not None;valid+=part['derived_current_frame_authority']
                assert part['whole_SRAM_unchanged']and part['all_RAM_nonwrite_invariants_checked']
                assert not part['actual_caller_RTS']and not part['target_first_opcode_executed']
                if part['actual_primary_JSR']:
                    call=part['actual_primary_JSR'];sp=call['registers']['sp'];word=spec['call_pc']+2
                    assert[(x['address'],x['value'])for x in call['actual_pushes']]==[(0x100+sp,word>>8),(0x100+((sp-1)&255),word&255)]
                    assert call['raw_return']==word
                if part['derived_current_frame_authority']:
                    assert len(part['actual_PLA_reads'])==2
                    assert all(x['last_writer']==dict(kind='primary_JSR',generation=part['generation'],PC=spec['call_pc'])for x in part['actual_PLA_reads'])
                    assert all(x['live21_22']==word and not x['auxiliary_alias']for x in part['selected_reads'])
                assert len(part['executed_positions'])==part['original_instructions']
                if part['boundary'].startswith('after_B533'):
                    assert part['executed_positions'][-1]==[8,0xB533]
                else:assert part['executed_positions'][-1]==[8,spec['entry']]
            if row['group']=='same_bus_two_generations':
                first,last=row['segments'];before=first['final_registers'];after=last['input_registers']
                assert before['sp']==after['sp']and before['x']==after['x']and before['p']==after['p']
                delta={k:dict(before=before[k],after=after[k])for k in before if before[k]!=after[k]}
                assert set(delta)<= {'pc','a','y'}
                generations.append(dict(case=row['case'],host_reentry='Controlled PC/A/Y preparation between completed transfer prefixes; no target RTS or natural path claim.',
                    register_delta=delta,same_bus_CPU=True,actual_generations=[dict(generation=x['generation'],call=x['actual_primary_JSR'],
                    PLA=x['actual_PLA_reads'],reads=x['selected_reads'],premise_valid=x['derived_current_frame_authority'])for x in row['segments']],
                    RAM_preparations=[x for x in row['disclosed_mutations']if x['generation']==1]))
            if row['group']in ('one_byte_frame_fault','between_reads_pointer_fault','bare_B517_aux_counterexample','middle_access_aux_counterexample','stale_stack_6000_fully_overwritten'):
                for part in row['segments']:
                    expected_word=None if spec['call_pc']is None else spec['call_pc']+2
                    examples.append(dict(case=row['case'],group=row['group'],premise_valid=part['derived_current_frame_authority'],
                        expected_raw_word=expected_word,observed_words=[x['live21_22']for x in part['selected_reads']],
                        numeric_word_matches=all(x['live21_22']==expected_word for x in part['selected_reads'])if expected_word is not None else None,
                        auxiliary_hit=any(x['auxiliary_alias']for x in part['selected_reads']),actual_PLA_reads=part['actual_PLA_reads'],
                        actual_primary_JSR=part['actual_primary_JSR'],selected_reads=part['selected_reads'],mutations=row['disclosed_mutations']))
    assert keys==expected_keys and dict(groups)==plan['groups']==accept['required_groups']==receipt['groups']
    assert (segments,primary,valid,instructions,fixed)==(17215,17206,17190,752661,8220)
    assert len(generations)==8
    save('generation-reentry-preparation.json',dict(schema='wp02-offline-observed-generation-reentry-v1',cases=generations,
        count=8,original_CPU_or_Source_executions=0,derivation='Actual saved generation0 final REG versus generation1 input REG; CPU not rerun.'))
    save('counterexample-and-overwrite-evidence.json',dict(cases=examples,
        caveat='A violated premise need not change numeric word or hit auxiliary memory; these fields are separate. Same-value external overwrite is also excluded by current-write provenance.',
        static_only_same_value_fault_note='Not a new dynamic same-value-fault case; source last-writer rule excludes all external frame writes, including same-value writes.'))
    proof=read(OUT/'static-contract.json')
    save('current-jsr-contract.json',dict(schema='wp02-current-dynamic-JSR-authoritative-contract-v1',
        ROM_SHA256=ROM_SHA,physical_code_pair=[8,9],actual_capture_origin=None,
        immutable_helper=proof['exact_helper_range'],inline_tables=proof['immutable_inline_tables'],
        calls=proof['trusted_atlas_callers'],address_contracts=proof['address_contracts'],
        premises=['Actual current original A09E or ACAB JSR executed, with both pushes still its own dynamic generation.',
                  'Original ROM/helper/inline bytes, fixed code pair8/9; binary or decimal flag does not change this helper address arithmetic.',
                  'No interrupts/external mutation/middle entry during JSR-to-selected-read window; live21/22 preserved through both reads.',
                  'Known control-atlas entry/call domain only; no universal assertion about corrupted/arbitrary external code entry.'],
        conditional_CPU_evidence=record(run/'validation.json'),complete_case_matrix=record(OUT/'case-matrix.json'),
        current_frame_valid_segments=17190,invalid_or_bare_counterexample_segments=25,
        arbitrary_SP_zp_nonalias=dict(SP_domain=list(range(256)),stack_page=[0x100,0x1FF],fixed_zero_page_writes=list(range(0x20,0x25))),
        raw_A_address_lemma='All256 raw inputs select byte Y parity; current raw word A0A0/ACAD plus byteY stays immutable A000-BFFF ROM, independent of semantic target validity.',
        legal_targets=dict(strategy=list(range(8)),predicate=list(range(16)),AND0F_only=list(range(16))),
        AC7B=dict(raw_X256_all_quadrant_pairs=4096,adjacent_real_prefix_cases=14,F266_actual_returns=8220,
                  saved_value='Input X to live2C; normal helpers leave2C, clobberX=0; ACA8 reloads A from2C.',
                  actual_known_prefix_X=proof['AC7B_live_2C_lifecycle']['observed_static_prefix_X_values']),
        boundary='After original B533 indirect JMP, before target first opcode; never RTS or full target result.',
        official_city_auxiliary_names={str(i):None for i in (1,28,29,30,31)},Source_cases=0,Native_runs=0,
        whole_game_closure_proven=False,logical_effective_reads_only=True,hardware_dummy_bus_or_interrupt_closure=False))

    old_path=ROOT/'analysis/phase31/fields-static/all-indirect-accesses.json';old=read(old_path);rows=copy.deepcopy(old['accesses'])
    migrations=[];untouched_old=[];untouched_new=[]
    for index,(original,row)in enumerate(zip(old['accesses'],rows,strict=True)):
        identity=(row['physical_bank'],row['cpu'])
        if identity not in SELECTED:
            assert row==original;untouched_old.append(original);untouched_new.append(row);continue
        assert original['classification']=='unresolved_pointer_or_index_contract'and original['address_contract']is None
        contract=copy.deepcopy(proof['address_contracts'][f'{row["cpu"]:04X}'])
        contract['authority']='wp02 current dynamic-JSR contract, complete declared CPU matrix; explicitly conditional.'
        contract['evidence']=record(OUT/'current-jsr-contract.json')
        row.update(classification='proved_disjoint_auxiliary_address_domain',address_contract=contract,
            whole_pointer_values=contract['whole_pointer_values'],Y_values=contract['Y_values'],
            proof_basis='wp02_current_dynamic_JSR_stack_and_live_pointer_contract',
            authoritative_contract_origin=rel(OUT/'current-jsr-contract.json'),
            authoritative_pointer_representation='complete_current_dynamic_JSR_return_word',wp02_newly_proved_disjoint=True)
        migrations.append(dict(typed_id=typed(row),json_pointer=f'/accesses/{index}',before=original,after=row,
            old_premise='No authoritative complete pointer/index relation; remains unknown in frozen31.',
            new_premise=contract['authority'],evidence=[record(OUT/'current-jsr-contract.json'),record(run/'validation.json')],
            meaning='Conditional logical effective-address exclusion, not an unused field or universal bare-entry theorem.'))
    assert len(rows)==1526 and len(migrations)==2 and len(untouched_old)==1524 and untouched_old==untouched_new
    counts=dict(collections.Counter(x['classification']for x in rows))
    assert counts==dict(proved_disjoint_auxiliary_address_domain=1203,possible_city_auxiliary_alias=80,unresolved_pointer_or_index_contract=243)
    save('all-indirect-accesses.json',dict(schema='wp02-conditional-current-JSR-ledger-v1',ROM_sha256=ROM_SHA,access_count=1526,
        classification_counts=counts,current_package_newly_proved_disjoint_count=2,accesses=rows,
        marker_policy='Only wp02_newly_proved_disjoint counts this package. All inherited legacy newly_proved_disjoint markers, including BDB8 true, remain unchanged history.'))
    save('candidate-migrations.json',dict(base=record(old_path),selected_migrations=migrations,selected_count=2,
        unselected_full_objects_preserved=1524,unselected_before_sha256=digest(untouched_old),unselected_after_sha256=digest(untouched_new),
        inherited_legacy_newly_true_count=sum(bool(x.get('newly_proved_disjoint'))for x in old['accesses']),
        wp02_newly_count=2,prior_counts=old['classification_counts'],after_counts=counts,prior_remaining=325,after_remaining=323))
    save('remaining-accesses.json',dict(accesses=[x for x in rows if x['classification']!='proved_disjoint_auxiliary_address_domain'],count=323))
    raw=ROOT/'analysis/phase31/fields-static/raw345-executability-ledger.json';target=OUT/raw.name;assert not target.exists();shutil.copyfile(raw,target);assert raw.read_bytes()==target.read_bytes()
    historical=ROOT/'analysis/phase7/runtime/cpu-call/actual-cpu-instructions.json';trace=read(historical);slices=[]
    for index,row in enumerate(trace):
        if row['bank']==8 and row['pc']==0xA09E:
            end=next(i for i in range(index+1,len(trace))if trace[i]['bank']==8 and trace[i]['pc']==0xB533)
            slices.append(dict(start_step=row['step'],trace=trace[index:end+1],next_record_PC=trace[end+1]['pc']))
    assert len(slices)==4
    save('historical-controlled-support.json',dict(trace=record(historical),captured_Native_callee=False,new_CPU_executions=0,
        provenance='Historical separate synchronous CPU from Native frame-end memory, host changed PC to A000/pushed E22B; Native PC AE9D. Not a Native A09E instantaneous capture.',
        A09E_actual_historical_JSRs=slices,ACAB_historical_capture_found=False,current_tests_actual_capture_origin=None))
    save('semantic-validation.json',dict(status='passed_full_declared_contract_audit',CPU_parent_cases=17207,prefix_segments=17215,
        actual_primary_JSRs=17206,current_frame_valid_segments=17190,invalid_counterexample_segments=25,
        original_CPU_instructions=752661,groups=dict(groups),F266_actual_returns=8220,new_candidate_promotions=2,
        unselected_ledger_objects_unchanged=1524,remaining=323,raw345_independent=dict(operand=104,data=13,unproved_entry=228),
        Source_cases=0,Native_runs=0,actual_capture_origin=None,actual_caller_RTS_cases=0,whole_game_closure_proven=False,
        CPU_not_rerun_during_this_audit=True))
    print(json.dumps(dict(status='passed_offline_audit_and_conditional_migration',cases=17207,promoted=2,remaining=323)))

def seal():
    before=read(OUT/'frozen-before.json');after=read(OUT/'frozen-after.json')
    assert before['status']==after['status']=='passed'and before['full_work_manifest_sha256']==after['full_work_manifest_sha256']
    assert before['old_work_paths']==after['old_work_paths']==239340
    assert read(OUT/'semantic-validation.json')['status']=='passed_full_declared_contract_audit'
    appendix=OUT/'samevalue-appendix';appendix_run=appendix/'run-01';ap=read(appendix/'plan.json');ar=read(appendix_run/'validation.json')
    assert ar['status']=='passed_all4'and ar['controlled_CPU_parent_cases']==4 and ar['original_CPU_instructions']==64
    assert ar['plan_sha256']==sha(appendix/'plan.json')
    assert sha(ROOT/'scripts/verify_wp02_samevalue_appendix.py')==ap['producer_sha256']
    assert sha(ROOT/'scripts/verify_wp02_current_jsr.py')==ap['dependency_runner_sha256']
    assert (appendix_run/'executed-plan.json').read_bytes()==(appendix/'plan.json').read_bytes()
    assert sha(appendix_run/'executed-producer.py')==ap['producer_sha256']
    assert {x['case']for x in ar['cases']}=={x['key']for x in ap['cases']}
    for row in ar['cases']:
        assert row['external_same_value_mutation']['before']==row['external_same_value_mutation']['value']
        assert row['numeric_raw_word_correct']and row['selected_ROM_reads_correct']
        assert row['current_frame_provenance_premise_valid']is False
    save('contract-samevalue-addendum.json',dict(schema='wp02-authoritative-contract-samevalue-addendum-v1',
        main_current_JSR_contract=record(OUT/'current-jsr-contract.json'),appendix_plan=record(appendix/'plan.json'),
        appendix_actual_CPU_receipt=record(appendix_run/'validation.json'),
        conclusion='Numeric stack-word equality is insufficient. A same-value external high-byte write invalidates current-generation provenance while all observed numeric ROM results can remain correct.',
        main_CPU_parent_cases=17207,appendix_CPU_parent_cases=4,combined_CPU_parent_cases=17211,
        main_instructions=752661,appendix_instructions=64,combined_instructions=752725,
        combined_prefix_segments=17219,current_frame_valid_segments=17190,invalid_or_bare_segments=29,
        original_main_receipt_unchanged=True,Source_cases=0,Native_runs=0,actual_capture_origin=None))
    run=OUT/'run-01';pins=read(run/'execution-inputs.json')['script_sha256']
    for name,value in pins.items():assert sha(ROOT/name)==value
    scripts=sorted((ROOT/'scripts').glob('*wp02*.py'))
    for p in scripts:ast.parse(p.read_text())
    current_source=ROOT/'source/recovered/tactical_cooperation_controller.py'
    save('input-manifest.json',dict(schema='wp02-input-hash-manifest-v1',scripts=[record(p)for p in scripts],
        at_run_inputs=record(run/'execution-inputs.json'),frozen_work_manifest=record(OUT/'frozen-work-inputs.json'),
        frozen_before=record(OUT/'frozen-before.json'),frozen_after=record(OUT/'frozen-after.json'),
        existing_readable_Source=record(current_source),existing_Source_changed=False,
        official_prior_ledger=record(ROOT/'analysis/phase31/fields-static/all-indirect-accesses.json'),
        historical_support_trace=record(ROOT/'analysis/phase7/runtime/cpu-call/actual-cpu-instructions.json'),
        same_value_appendix_execution=record(appendix_run/'execution-inputs.json'),
        ROM_SHA256=ROM_SHA,ROM_distributed=False,production_CPU_IR_fallback_added=False))
    files={rel(p):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))if p.is_file()}
    save('artifact-manifest.json',dict(schema='wp02-artifact-hash-manifest-v1',files=files,excludes=['artifact-manifest.json','verification.json']))
    save('verification.json',dict(schema='wp02-final-bounded-contract-verification-v1',status='passed_bounded_WP02',
        CPU_parent_cases=17211,main_matrix_CPU_parent_cases=17207,same_value_appendix_CPU_parent_cases=4,
        actual_primary_JSRs=17210,original_CPU_instructions=752725,Source_cases=0,Native_runs=0,
        actual_capture_origin=None,actual_caller_RTS_cases=0,conditional_candidate_promotions=2,
        field_ledger=dict(total=1526,conditional_disjoint=1203,possible=80,unknown=243,remaining=323),
        unchanged_other_rows=1524,raw345_independent=dict(total=345,operand=104,data=13,unproved_entry=228),
        city_official_names={str(i):None for i in (1,28,29,30,31)},whole_game_closure_proven=False,
        unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
        old_work_paths_preserved=239340,input_manifest=record(OUT/'input-manifest.json'),artifact_manifest=record(OUT/'artifact-manifest.json'),
        semantic_validation=record(OUT/'semantic-validation.json'),CPU_receipt=record(run/'validation.json'),
        same_value_appendix_receipt=record(appendix_run/'validation.json'),
        authoritative_contract_addendum=record(OUT/'contract-samevalue-addendum.json'),
        artifact_paths_before_self_and_final=len(files),next_recommended_not_executed='WP03 caller/entry proof for the independent raw345 unproved-entry domain',
        scope='Complete predeclared bounded current-JSR contract matrix, not full state Cartesian, natural Native path or complete target behavior.'))
    print(json.dumps(dict(status='passed_bounded_WP02',verification_sha256=sha(OUT/'verification.json'),artifact_pins=len(files),remaining=323)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
