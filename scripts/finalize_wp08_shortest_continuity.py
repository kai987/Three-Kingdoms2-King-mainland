#!/usr/bin/env python3
"""Offline WP08 receipt verification. Does not import or execute game code."""
from pathlib import Path
import ast,hashlib,json,sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/wp08-shortest-continuity'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(Path(p).relative_to(ROOT))
def save(name,data):
    p=OUT/name
    assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def record(p):return dict(path=relative(p),sha256=sha(p),bytes=p.stat().st_size)

def main():
    run=OUT/'run-05';validation=read(run/'validation.json');inputs=read(run/'execution-inputs.json')
    assert validation['status']=='passed' and validation['complete_continuous_suffixes']==2
    assert validation['strict_prefixes']==0 and validation['Native_new_frames']==0
    spec=ROOT/inputs['spec_path'];plan=ROOT/inputs['input_plan_path']
    assert sha(spec)==inputs['spec_sha256'] and sha(plan)==inputs['input_plan_sha256']
    assert spec.read_bytes()==(run/'executed-spec.json').read_bytes()
    assert plan.read_bytes()==(run/'executed-input-plan.json').read_bytes()
    assert inputs['actual_two_pad_input_cycles']==[[0,0]]*27
    for name,digest in inputs['Source_and_runner_sha256'].items():assert sha(ROOT/name)==digest,name
    for p in (run/'executed-source').iterdir():
        originals=[k for k in inputs['Source_and_runner_sha256'] if Path(k).name==p.name]
        assert len(originals)==1 and sha(p)==inputs['Source_and_runner_sha256'][originals[0]]
    facts=[];pair_count=0
    for parent in validation['parents']:
        folder=run/parent['case'];events=parent['events'];last=events[-1]
        assert read(folder/'validation.json')==parent
        assert parent['status']=='passed_complete_continuous_software_suffix'
        assert parent['executed_software_cycles']==24 and parent['declared_cycle_upper_bound']==27
        assert parent['original_CPU_instructions']==81364 and parent['exception'] is None
        assert len(events)==parent['compared_event_count']
        assert sum(x['original_CPU_instructions'] for x in events)==81364
        assert parent['same_game_coordinator_bus_register_session']
        assert parent['initial_import_count_per_bus']==1 and parent['subsequent_Native_snapshot_imports']==0
        assert last['status']=='returned' and last['global_state']==1
        assert last['registers']==dict(a=255,x=5,y=40,p=55,sp=255,pc=0xE066)
        assert not last['ownership']['phases'] and not last['ownership']['retained_inner_owners']
        assert all(x['global_state'] not in (1,2) for x in events[:-1]
                   if x['status']=='returned' and x['pending_depth']==0)
        identities={k:v for k,v in events[0]['ownership'].items() if k.endswith('_identity')}
        for event in events:
            assert all(event['ownership'][k]==v for k,v in identities.items())
            assert event['ownership']['reset_epoch']==0
            for suffix,size,expected in (('ram',2048,event['RAM_sha256']),('sram',8192,event['SRAM_sha256']),
                                        ('ppu-sink',16384,event['software_devices']['PPU_bytes_sha256'])):
                prefix=f"event-{event['sequence']:04d}"
                left=(folder/f'{prefix}-CPU-{suffix}.bin').read_bytes()
                right=(folder/f'{prefix}-Source-{suffix}.bin').read_bytes()
                assert len(left)==len(right)==size and left==right
                assert hashlib.sha256(right).hexdigest()==expected
                pair_count+=1
        assert read(folder/'Source-combined-IO.json')==read(folder/'CPU-combined-IO.json')
        assert last['combined_IO_count']==3728
        source_reads=read(folder/'Source-selected-reads.json');cpu_reads=read(folder/'CPU-selected-reads.json')
        a=[x['value'] for x in source_reads if x['PC']==0xBBA0]
        b=[x['value'] for x in cpu_reads if x['oracle_opcode_PC']==0xBBA0]
        assert a==b==[1]*19+[255]
        audit=read(folder/'source-call-audit.json')
        ecee=[x for x in audit if x['target']==0xECEE and x['controlled_ECEE_mode']=='actual']
        assert len(ecee)==1 and ecee[0]['status']=='returned' and ecee[0]['after']['registers']['pc']==0xBB96
        ee07=[x for x in audit if x['target']==0xEE07 and x['before']['E1']!=x['after']['E1']]
        assert ee07 and all(x['entry_banks']==[17,12,13,31] and x['after']['banks']==[16,12,13,31]
                            and (x['before']['E1'],x['after']['E1'])==(49,48) for x in ee07)
        writes=read(folder/'Source-logical-writes.json');cpu_writes=read(folder/'CPU-logical-writes.json')
        commits=[x for x in writes if x['address']==0x6214 and (x['before'],x['value'])==(255,67)]
        assert len(commits)==1 and (commits[0]['PC'],commits[0]['SP'])==(0xBDB8,236)
        stack_pairs={}
        for word in (0xBB38,0xBD90):
            def pairs(rows):
                return [(a['address'],b['address'],a['value'],b['value'])for a,b in zip(rows,rows[1:])
                        if 0x100<=a['address']<0x200 and b['address']==a['address']-1
                        and (a['value'],b['value'])==(word>>8,word&255)]
            assert pairs(writes)==pairs(cpu_writes) and pairs(writes)
            stack_pairs[f'{word:04X}']=pairs(writes)
        checkpoints=read(folder/'oracle-selected-checkpoints.json')
        bb39=[x for x in checkpoints if x['registers']['pc']==0xBB39 and x['banks'][1:3]==[8,9]]
        assert len(bb39)==1 and bb39[0]['registers']['sp']==240
        source_bb39=[x for x in writes if x['PC']==0xBB39 and x['address']==0x501]
        assert len(source_bb39)==1 and source_bb39[0]['SP']==240
        fake=read(folder/'fake-return-checks.json')
        withheld=parent['case'].startswith('withheld')
        assert len(fake)==(2 if withheld else 0)
        for item in fake:
            assert item['original_CPU_instructions']==0 and item['Source_program_advance'] is False
            assert item['RAM_SRAM_store_counts_before']==item['RAM_SRAM_store_counts_after']==dict(Source=3499,CPU=3499)
            assert item['outer_inner_generator_positions_before']==item['outer_inner_generator_positions_after']
            assert item['registers']['pc']==0xECEE and item['registers']['sp']==238
        assert parent['compared_boundary_battle_states']==[[14,0],[15,0],[15,1],[15,2],[15,3]]
        facts.append(dict(case=parent['case'],software_cycles=24,declared_cycle_upper_bound=27,
            planned_two_pad_inputs=27,consumed_two_pad_inputs=24,compared_events=len(events),
            original_CPU_instructions=81364,software_logical_IO_count=3728,fake_zero_progress_checks=len(fake),
            final_global_state=1,final_PC='E066',final_SP=255,terminal_pending_empty=True,
            stage3_fresh_NMI_reads=a,ECEE_actual_resolution_count=1,EE07_side_effects=ee07,
            Source_BDB8_commit=commits[0],Source_and_CPU_BB39_SP=240,
            complete_logical_RAM_SRAM_write_counts=dict(CPU=len(cpu_writes),Source=len(writes)),
            complete_RAM_write_trace_identical=cpu_writes==writes,
            matched_actual_current_JSR_push_pairs=stack_pairs))
    assert pair_count==579
    save('semantic-validation.json',dict(schema='wp08-offline-semantic-verification-v1',status='passed',
        final_run='run-05',complete_parent_cases=2,compared_execution_boundaries=193,
        fake_zero_progress_checks=2,total_checked_operations=195,full_output_buffer_pairs_compared=pair_count,
        final_run_original_CPU_instructions=162728,facts=facts,
        hardware_timing_or_native_frames_proven=False,all_microcycle_bus_equivalence_proven=False,
        human14_phases1_to6_proven=False,operable_city_UI_proven=False))

    ledger=[]
    for number in range(1,6):
        path=OUT/f'run-{number:02d}';entry=read(path/'execution-inputs.json')
        for p in (path/'executed-source').iterdir():
            matches=[k for k in entry['Source_and_runner_sha256'] if Path(k).name==p.name]
            assert len(matches)==1 and sha(p)==entry['Source_and_runner_sha256'][matches[0]]
        aggregate=path/'validation.json'
        cases=[]
        for tag in ('normal-same-actual-origin','withheld-ECEE-same-actual-origin'):
            parent=path/tag;receipt=parent/'validation.json'
            saved=len(list(parent.glob('event-*-Source-ram.bin')))
            row=read(receipt) if receipt.exists() else None
            cases.append(dict(case=tag,saved_compared_boundary_buffer_sets=saved,
                final_case_receipt_exists=receipt.exists(),status=None if row is None else row['status'],
                original_CPU_instruction_count=None if row is None else row['original_CPU_instructions']))
        reasons={1:'Exploratory pass before stronger device/read/fake checks; input plan not consumed.',
                 2:'Failed new checker: BBA0 full-route assertion was premature inside ECEE restoration.',
                 3:'Incomplete attempt: final checker compared resumed current banks to caller banks; withheld has no final receipt.',
                 4:'Passed two cases; fake same-value write trace coverage strengthened in run05.',
                 5:'Final accepted shortest-subpackage run; explicit input plan consumed and pinned.'}
        ledger.append(dict(run=path.name,final_accepted=number==5,aggregate_receipt_exists=aggregate.exists(),
            aggregate_status=read(aggregate)['status'] if aggregate.exists() else None,
            spec_sha256_at_run=entry['spec_sha256'],runner_sha256_at_run=entry['Source_and_runner_sha256']['scripts/verify_wp08_shortest_continuity.py'],
            reason=reasons[number],parents=cases))
    save('execution-ledger.json',dict(schema='wp08-execution-ledger-v1',attempts=ledger,
        Source_parent_executions=10,final_accepted_parent_cases=2,Native_new_executions=0,
        no_backfilled_historical_source_hashes=True))

    adapter=ROOT/'source/recovered/postbattle_continuity_wp08.py';tree=ast.parse(adapter.read_text())
    imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert imports==['postbattle_continuity_phase32']
    assert not any(isinstance(node,ast.Name) and node.id in ('MPU','CPU','IR','NestopiaCore')for node in ast.walk(tree))
    frozen=read(OUT/'frozen-after.json');before=read(OUT/'frozen-before.json')
    assert frozen['status']==before['status']=='passed'
    assert frozen['expected_map_sha256']==before['expected_map_sha256'] and not frozen['missing_or_changed']
    scripts=['scripts/verify_wp08_shortest_continuity.py','scripts/verify_wp08_frozen_inputs.py',relative(Path(__file__).resolve())]
    for name in scripts:ast.parse((ROOT/name).read_text())
    anchors=['analysis/phase31/verification.json','analysis/wp05-natural-nonempty/verification.json',
             'analysis/closure-audit-20261018/verification.json',relative(spec),relative(plan)]
    manifest=dict(schema='wp08-input-hash-manifest-v1',executed_identity=record(run/'execution-inputs.json'),
        executed_Source_and_runner_sha256=inputs['Source_and_runner_sha256'],
        created_code_files=[record(ROOT/x)for x in scripts+[relative(adapter)]],
        anchors=[record(ROOT/x)for x in anchors],frozen_before=record(OUT/'frozen-before.json'),
        frozen_after=record(OUT/'frozen-after.json'),ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82',
        ROM_distributed=False,production_CPU_callbacks=0,production_IR_interpretation=False,
        test_oracle='Independent py65 original-instruction execution, separate bus; no Native core execution',
        dependency_note='Frozen helper and Source dependencies additionally preserved by full frozen-before/after map. No old producer main invoked.')
    save('input-manifest.json',manifest)
    files={relative(p):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))if p.is_file()}
    save('artifact-manifest.json',dict(schema='wp08-artifact-hash-manifest-v1',files=files,
        excluded_self_and_final_verification=['artifact-manifest.json','verification.json']))
    save('verification.json',dict(schema='wp08-shortest-subpackage-final-verification-v1',status='passed_bounded_subpackage',
        accepted_run='run-05',accepted_Source_cases=2,compared_execution_boundaries=193,
        fake_zero_progress_checks=2,output_buffer_pairs=579,original_CPU_instructions=162728,
        new_Native_frames=0,production_original_CPU_callbacks=0,whole_WP08_complete=False,
        whole_game_closure_proven=False,human14_phases1_to6_proven=False,operable_city_UI_proven=False,
        field_ledger=dict(total=1526,conditional_disjoint=1201,possible=80,unknown=245,remaining=325,
                          raw_independent_total=345,city_offset1_official_name=None,city_offsets28_31_official_names=None),
        unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
        new_genuine_unknown_service_prefixes=0,WP02_fallback_executed=False,
        next_recommended_not_executed='WP02: current-JSR B517 contracts; requires separate next-package authorization',
        artifact_manifest=record(OUT/'artifact-manifest.json'),input_manifest=record(OUT/'input-manifest.json'),
        semantic_validation=record(OUT/'semantic-validation.json'),frozen_after=record(OUT/'frozen-after.json'),
        artifact_paths_before_self_and_final=len(files),old_pins_preserved=frozen['unique_expected_paths']))
    print(json.dumps(dict(status='passed_bounded_subpackage',final_run='run-05',parents=2,boundaries=193,
        fake_checks=2,buffer_pairs=579,old_paths_preserved=frozen['unique_expected_paths'],artifact_pins=len(files),
        verification_sha256=sha(OUT/'verification.json')),ensure_ascii=False))
if __name__=='__main__':main()
