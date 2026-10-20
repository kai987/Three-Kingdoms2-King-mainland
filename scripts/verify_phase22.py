#!/usr/bin/env python3
"""Read-only phase22 aggregate; writes only analysis/phase22/verification.json.

No CPU/core/producer is run. Frozen phase21 pins remain exact inputs. Source
comparisons, original-CPU contracts, bus observations and model guards are
counted separately. Effective-address and dummy bus-address domains differ.
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import sys
from urllib.parse import unquote, urlparse
import wave
from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase22'
SPEC = importlib.util.spec_from_file_location('frozen_phase21_readonly_audit', ROOT / 'scripts/verify_phase21.py')
prior = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = prior; SPEC.loader.exec_module(prior)
ROM_SHA = prior.ROM_SHA
OLD_AUDIT = '635554d4c3845b4459e929a1153d797f4ac913ea673ce6ea19c882f1d20aa389'
OLD_ZIP = '6a8923b2355fcfa58b0d6acc2da88e1224c2c40a8509f01f3dd4e811d445657f'
AUX, DISJOINT = prior.AUX, prior.DISJOINT
POSTZIP = prior.POSTZIP
sha, read, original = prior.sha, prior.read, prior.original


def cases(proof):
    return proof.get('address_cases', [proof])


def words(proof):
    return frozenset(p for item in cases(proof) for p in prior.words(item))


def indices(proof):
    return sorted({y for item in cases(proof) for y in item['Y_values']})


def intersection(proof):
    return sorted({a for item in cases(proof) for a in prior.intersection(item)})


def dummy_intersection(proof, operation):
    result = set()
    for item in cases(proof):
        pointers = prior.words(item)
        for address in AUX:
            for index in item['Y_values']:
                pointer = (address & 0xFF00) | ((address - index) & 255)
                if pointer in pointers and (operation == 'STA' or (pointer & 255) + index >= 256):
                    result.add(address); break
    return sorted(result)


class Audit(prior.Audit):
    def frozen_history(self):
        path = ROOT / 'analysis/phase21/verification.json'
        self.pin(path, OLD_AUDIT)
        old = read(path)
        assert old['status'] == 'passed' and old['ROM_sha256'] == ROM_SHA and old['rebuilt_byte_identical']
        assert len(old['source_and_validator_sha256']) == 460
        assert len(old['artifact_and_dependency_sha256']) == 30303
        for name, digest in old['source_and_validator_sha256'].items():
            self.pin(name, digest); self.sources[name] = digest
        for name, digest in old['artifact_and_dependency_sha256'].items():
            self.pin(name, digest)
        assert sha(ROOT / 'build/三国志2超级版-逆向分析-v21.zip') == OLD_ZIP
        assert (ROOT / 'build/三国志2超级版.rebuilt.nes').read_bytes() == self.rom
        self.pin('build/三国志2超级版.rebuilt.nes')
        self.counts.update(unchanged_phase21_source_script_pins=460, unchanged_phase21_artifact_dependency_pins=30303)

    def records(self, *records):
        for record in records:
            self.record_pins(record)
            self.nested_raw(record)

    def static_fields(self):
        folder = OUT / 'fields-static'
        summary, validation, evidence = (read(folder / name) for name in ('analysis-summary.json', 'verification.json', 'evidence.json'))
        assert summary['status'] == 'analyzed' and validation['status'] == evidence['status'] == 'passed'
        assert validation['failed_count'] == 0 and summary['source_CPU_cases'] == validation['source_CPU_cases'] == evidence['source_CPU_cases'] == 0
        self.records(summary, validation, evidence)
        old = {(r['physical_bank'], r['cpu']): r for r in read(ROOT / 'analysis/phase21/fields-static/all-indirect-accesses.json')['accesses']}
        all_rows = read(folder / 'all-indirect-accesses.json')
        canonical = {(r['physical_bank'], r['cpu']): r for r in all_rows['accesses']}
        assert len(canonical) == len(all_rows['accesses']) == 1526 and set(canonical) == set(old)
        relational = 0
        for key, row in canonical.items():
            self.raw(row)
            proof = row['address_contract']
            assert row['phase21_classification'] == old[key]['classification']
            if proof:
                hit = intersection(proof)
                assert hit == proof['possible_auxiliary_effective_addresses'] and len(hit) == proof['auxiliary_address_intersection_count']
                assert row['whole_pointer_values'] == sorted(words(proof)) and row['Y_values'] == indices(proof)
                if 'address_cases' in proof:
                    relational += 1
                    assert len(proof['address_cases']) == 2
                    assert proof['whole_pointer_values'] == row['whole_pointer_values'] and proof['Y_values'] == row['Y_values']
                    for case in proof['address_cases']:
                        assert prior.intersection(case) == case['possible_auxiliary_effective_addresses'] == []
                        assert case['auxiliary_address_intersection_count'] == 0
                    flat = dict(whole_pointer_values=row['whole_pointer_values'], Y_values=row['Y_values'])
                    assert len(prior.intersection(flat)) == proof['independent_projection_auxiliary_intersection_count'] == 150
                    assert not hit and not proof['required_execution_contract']['bare_suffix_entry_covered']
                if row['classification'] == DISJOINT:
                    assert hit == []
                origin = row['authoritative_contract_origin']
                if origin:
                    self.pin(origin['path'], origin['sha256'])
                    assert proof == old[key][origin['contract_field']]
            else:
                assert row['classification'] == 'unresolved_pointer_or_index_contract'
            candidate = row['candidate_address_contract']
            assert row['candidate_contract_is_authoritative'] is False
            assert row['candidate_whole_pointer_values'] == (sorted(words(candidate)) if candidate else None)
            assert row['candidate_Y_values'] == (indices(candidate) if candidate else None)
            assert row['newly_proved_disjoint'] == (row['classification'] == DISJOINT and old[key]['classification'] != DISJOINT)
            assert 'excludes' in row['address_scope'] and 'dummy' in row['address_scope']
        assert relational == 4
        for filename, size, counts in (
            ('all-indirect-accesses.json', 1526, {DISJOINT:1158, 'possible_city_auxiliary_alias':98, 'unresolved_pointer_or_index_contract':270}),
            ('access-contracts.json', 589, {DISJOINT:251, 'possible_city_auxiliary_alias':84, 'unresolved_pointer_or_index_contract':254}),
            ('new-indirect-accesses.json', 45, {DISJOINT:37, 'possible_city_auxiliary_alias':1, 'unresolved_pointer_or_index_contract':7}),
            ('phase21-remaining376-handling.json', 376, None), ('remaining-accesses.json', 368, None)):
            data = read(folder / filename)
            assert data['access_count'] == len(data['accesses']) == size
            assert Counter(r['classification'] for r in data['accesses']) == data['classification_counts']
            if counts is not None:
                assert data['classification_counts'] == counts
            assert all(row == canonical[row['physical_bank'], row['cpu']] for row in data['accesses'])
        assert {k for k,r in canonical.items() if r['newly_proved_disjoint']} == {(11,0xC664),(11,0xC66C),(11,0xC778),(11,0xC77F),(24,0xDF34),(26,0xD2D2),(26,0xD2D8),(29,0xAD01)}
        assert summary['newly_proved_disjoint_all_count'] == 8 and summary['remaining_access_count'] == validation['remaining_access_count'] == 368
        assert summary['complete_analysis_fixed_point_proven'] is False
        assert all(value is None for value in summary['official_target_field_names'].values())
        dummy = read(folder / 'logical-vs-dummy-bus-contracts.json')
        self.pin(dummy['original_emulator_source_path'], dummy['original_emulator_source_sha256'])
        source_lines = (ROOT / dummy['original_emulator_source_path']).read_text().splitlines()
        assert '\n'.join(source_lines[dummy['first_source_line']-1:dummy['last_source_line']])+'\n' == dummy['original_source_excerpt']
        assert dummy['access_count'] == len(dummy['accesses']) == 1526
        for row in dummy['accesses']:
            authority = canonical[row['physical_bank'], row['cpu']]
            proof = authority['address_contract']
            predicted = dummy_intersection(proof, authority['op']) if proof else None
            assert predicted == row['dummy_auxiliary_bus_addresses'] and row['dummy_auxiliary_intersection_count'] == (len(predicted) if predicted is not None else None)
            assert row['logical_classification'] == authority['classification']
            assert row['operation'] == authority['op'] and row['instruction_result_uses_dummy_value'] is False and row['logical_contract_changed'] is False
        assert Counter(r['classification'] for r in dummy['accesses']) == dummy['classification_counts'] == summary['dummy_bus_domain_classification_counts']
        assert summary['logical_disjoint_sites_with_possible_dummy_auxiliary_read'] == sum(r['logical_classification'] == DISJOINT and bool(r['dummy_auxiliary_bus_addresses']) for r in dummy['accesses']) == 13
        for filename in ('guarded-roster-contracts.json','scalar-index-constructor-contracts.json','declared-immutable-data-inventory.json','raw345-executability-ledger.json','logical-vs-dummy-bus-contracts.json'):
            self.nested_raw(read(folder / filename))
        raw = read(folder / 'raw345-executability-ledger.json')
        assert raw['window_count'] == len(raw['windows']) == 345
        assert Counter(r['phase22_executability_category'] for r in raw['windows']) == raw['categories'] == summary['raw_window_categories']
        assert all(not r['promoted_to_executable_code'] and not r['trusted_instruction_entry_at_start'] for r in raw['windows'])
        assert validation['original_scalar_constructor_prefix_CPU_cases'] == 11264
        assert validation['original_count_prefix_caller_RTS_CPU_cases'] == 2816
        assert validation['original_guarded_recruitment_caller_CPU_cases'] == 660
        assert validation['original_raw_suffix_prefix_counterexample_CPU_cases'] == 14
        assert validation['original_contract_CPU_cases'] == evidence['original_contract_CPU_cases'] == 14754
        assert validation['model_guard_check_count'] == len(validation['model_checks']) == 17 and all(r['passed'] for r in validation['model_checks'])
        assert len(validation['count_prefix_checks']) == 2816 and len(validation['guarded_recruitment_checks']) == 660 and len(validation['raw_suffix_counterexamples']) == 14
        assert sum(r['raw_input_A_cases'] for r in validation['scalar_constructor_checks']) == 11264
        self.counts.update(static_all_indirect_accesses=1526, static_previous_candidates=376, static_remaining_candidates=368, static_newly_disjoint=8,
            static_logically_disjoint=1158, static_possible_alias=98, static_unknown_contract=270, guarded_relational_accesses=4,
            guarded_flat_projection_intersection_per_access=150, guarded_actual_relation_intersection=0,
            static_original_CPU_contract_cases_not_Source_cases=14754, static_model_guard_checks_not_Source_cases=17,
            logical_disjoint_sites_with_possible_dummy_bus_read=13, original_raw_hypotheses_retained=345)
        return canonical

    def source_cases(self):
        folder = OUT / 'release'
        body, evidence, catalog = (read(folder / name) for name in ('validation.json','evidence.json','static-catalog.json'))
        assert body['status'] == 'passed' and body['failed_count'] == 0 and body['failures'] == [] and not body['quick']
        assert body['original_CPU_parent_cases'] == len(body['cases']) == 1370
        assert Counter(row['comparison'] for row in body['cases']) == body['counts'] == dict(actual_caller_RTS=1365, actual_nonlocal_return=3, strict_missing_dependency_prefix=2)
        assert body['source_guard_count'] == len(body['guards']) == 5 and all(g['status'] == 'passed' for g in body['guards'])
        assert body['source_original_CPU_callbacks'] == evidence['production_original_CPU_callbacks'] == 0
        assert not body['production_IR_interpretation'] and not body['Native_internal_CPU_trace'] and not evidence['production_runtime_codegen']
        for row in body['cases']:
            assert (row['RAM_bytes'],row['SRAM_bytes']) == (2048,8192)
            assert row['AXYP_SP_PC_ordered_IO_banks_N163_equal'] and row['source_original_CPU_callbacks'] == 0
            if row['comparison'] == 'actual_nonlocal_return':
                assert (row['final_registers']['pc'],row['final_registers']['sp']) == (0xA027,0xFD)
        assert Counter(r['domain'] for r in body['cases']) == dict(controlled_numeric_and_caller_CPU_fixture=1360, actual_Native_snapshot_originalCPU_reached_caller=5, Native_snapshot_plus_declared_hardware_NMI_CPU_fixture=3, strict_missing_dependency_fixture=2)
        coverage = evidence['coverage']
        assert coverage['new_manual_positions'] == coverage['dynamically_executed_new_manual_positions'] == len(catalog['instructions']) == 106
        assert coverage['new_manual_code_bytes'] == catalog['new_manual_code_bytes'] == 212 and coverage['not_dynamic'] == 0 and coverage['all_inputs_or_paths_proven'] is False
        executed = {(row['physical_bank'], row['cpu_address']) for row in body['executed_instruction_positions']}
        for row in catalog['instructions']:
            self.raw(row); assert (row['physical_bank'],row['cpu_address']) in executed
        for row in catalog['original_ranges']:
            self.raw(row); assert row['byte_count'] == len(bytes.fromhex(row['raw_hex']))
        for row in catalog['real_dependencies']:
            self.raw(row,bank=13)
        integration = read(OUT / 'source-integration.json')
        assert integration['status'] == 'passed' and integration['original_CPU_parent_cases'] == len(integration['rows']) == 14
        assert Counter(r['completion'] for r in integration['rows']) == integration['counts'] == dict(returned=13,nonlocal_return=1)
        assert integration['guard_count'] == len(integration['guards']) == 3 and integration['source_original_CPU_callbacks'] == 0
        assert not integration['production_IR_interpretation'] and not integration['Native_internal_CPU_trace']
        for row in integration['rows']:
            assert row['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal'] and row['source_original_CPU_callbacks'] == 0
            assert row['prepared_new_bytes'] == (row['origin'] == 'controlled_numeric_and_caller_CPU_fixture')
            if row['completion'] == 'nonlocal_return':
                assert row['final_registers']['pc'] == 0xA027 and row['final_registers']['sp'] == 0xFD
        self.records(body,evidence,catalog,integration)
        for name in ('postbattle_release_services.py','wild_recruitment_integration.py'):
            tree = ast.parse((ROOT/'source/recovered'/name).read_text())
            for node in ast.walk(tree):
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    names = [item.name for item in node.names] if isinstance(node,ast.Import) else [node.module or '']
                    assert not any(any(bad in value for bad in ('py65','state_machine','artifact_session','importlib')) for value in names),(name,names)
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    assert node.func.id not in ('eval','exec','compile','__import__'),(name,node.lineno)
        producers,e = (read(OUT/'producers'/name) for name in ('catalog.json','evidence.json'))
        assert e['status'] == 'bounded_catalog' and e['source_CPU_cases'] == 0
        assert producers['verified_direct_clear_motif_count'] == producers['all_PRG_exact_AND_FC_indirect_store_motif_matches'] == len(producers['producers']) == 7
        self.records(producers,e)
        self.counts.update(source_release_CPU_cases=1370,source_release_actual_RTS=1365,source_release_nonlocal_return=3,source_release_dependency_prefix=2,
            source_integration_CPU_cases=14,source_integration_actual_RTS=13,source_integration_nonlocal_return=1,
            new_source_CPU_cases=1384,new_source_actual_RTS=1378,new_source_nonlocal_return=4,new_source_dependency_prefix=2,new_source_guards=8,
            new_named_original_instruction_positions=106,new_named_original_manual_bytes=212,status0_producer_motif_catalog_positions=7)

    def cpu_diagnostics(self):
        e,t = (read(OUT/'cpu'/name) for name in ('evidence.json','trace.json'))
        assert e['status'] == t['status'] == 'bounded_original_CPU_observation'
        assert e['source_CPU_cases'] == t['source_CPU_cases'] == 0 and not e['Native_internal_CPU_trace'] and not t['Native_internal_CPU_trace']
        assert e['contexts'] == len(t['rows']) == 2 and e['exported_caller_inputs'] == 8
        assert sum(r['original_instructions'] for r in t['rows']) == e['original_CPU_prefix_instructions'] == 26383
        contexts = []
        for row in t['rows']:
            self.pin(row['native_state'],row['native_sha256'])
            state = prior.NestopiaContext.parse((ROOT/row['native_state']).read_bytes())
            assert state.registers == row['saved_registers'] and list(state.prg_banks) == row['actual_banks']
            assert not row['Native_internal_CPU_trace'] and row['source_CPU_cases'] == 0
            contexts += row['captured']
        assert len(set(contexts)) == 8
        caller_domains = Counter()
        for entry in contexts:
            d = read(OUT/'cpu/actual-callers'/entry/'context.json')
            caller_domains[d['origin']] += 1
            self.pin(d['original_Native_state'],d['original_Native_state_sha256'])
            assert d['prepared_numeric_bytes'] == [] and not d['synthetic_caller_or_PC_or_RNG_or_request_preparation'] and not d['Native_internal_CPU_trace']
            assert d['injected_new_NMI'] == int(d['origin']=='Native_snapshot_plus_declared_hardware_NMI_CPU_fixture')
            ram = (OUT/'cpu/actual-callers'/entry/'input-ram.bin').read_bytes()
            sram = (OUT/'cpu/actual-callers'/entry/'input-sram.bin').read_bytes()
            assert len(ram)==2048 and len(sram)==8192
            sp = d['registers']['sp']
            assert d['existing_return_PC'] == (((ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8)+1)&65535)
        assert caller_domains == dict(actual_Native_snapshot_originalCPU_reached_caller=5,Native_snapshot_plus_declared_hardware_NMI_CPU_fixture=3)
        self.records(e,t)
        self.counts.update(original_CPU_diagnostic_contexts_not_source_cases=2,original_CPU_diagnostic_instructions=26383,
            actual_saved_PC_exported_caller_inputs=5,declared_new_hardware_NMI_exported_inputs=3)

    def runtime(self,provenance):
        folder = OUT/'runtime'
        e,v = (read(folder/name) for name in ('evidence.json','validation.json'))
        assert e['status'] == v['status'] == 'passed' and v['failed_count'] == 0
        assert e['summary'] == {key:v[key] for key in e['summary']}
        self.pin(folder/'evidence.json',v['evidence_sha256'])
        self.pin('scripts/capture_native_wild_recruitment.py',v['script_sha256'])
        assert (v['native_input_routes'],v['original_core_cases'],v['core_variants'],v['fresh_process_runs']) == (1,1,2,4)
        assert (v['frames_per_route'],v['total_control_frames_both_variants_both_runs'],v['nonempty_artifact_checks'],v['decoded_PNG_checks']) == (15200,60800,1669,408)
        assert v['additional_core_memory_writes'] == v['inherited_preparation_byte_writes'] == 0 and v['state_imports_per_run'] == 1
        assert v['all_five_full_buffers_match_each_frame'] and v['initial_full_serialized_buffers_equal'] and v['all_nonempty_artifacts_repeat_exact']
        assert v['source_CPU_comparisons'] == 0
        assert len(e['native_cases']) == len(e['observer_runs']) == 1
        assert e['original_core_sha256'] == provenance['original_core']['sha256'] and e['observer_core_sha256'] == provenance['passive_observer']['sha256']
        self.pin(e['core_provenance'])
        reference_frames = None; initial_state = None; total_artifacts=0; png_checks=0
        for variant,core in (('original-control','original_core'),('observer','passive_observer')):
            first = folder/variant
            record = read(first/'validation.json'); repeat = read(first/'repeat-validation.json'); other = ROOT/repeat['second_run']
            second = read(other/'validation.json')
            assert record == second and record['status'] == repeat['status'] == 'passed'
            assert record['frames'] == 15200 and record['checkpoint_count'] == 204
            assert record['natural_gameplay'] and not record['controlled_fixture'] and record['state_imported'] and not record['cold_boot']
            assert record['additional_core_memory_writes'] == record['additional_core_memory_writes_after_declared_preparation'] == record['additional_ready_or_result_injections'] == 0
            assert record['preparation'] == record['preparation_groups'] == [] and not record['status_location_roster_RNG_PC_request_reply_ready_prepared']
            assert record['inherited_context']['inherited_preparation_byte_writes'] == 0
            assert not record['native_internal_CPU_trace'] and record['observer_core_sparse_CPU_events'] == (variant=='observer') and record['source_CPU_comparisons'] == 0
            assert record['core']['core_sha256'] == provenance[core]['sha256'] and record['full_serialized_buffers_not_normalized']
            assert repeat['artifacts_checked'] == len(record['artifact_sha256']) == (833 if variant=='original-control' else 836)
            assert repeat['all_nonempty_artifact_bytes_exact'] and repeat['validation_bytes_exact'] and repeat['full_serialized_buffers_not_normalized']
            self.record_pins(record,first)
            self.pin(record['mother_state'],record['mother_sha256'])
            for name,detail in record['artifact_sha256'].items():
                assert detail['bytes']>0
                for target in (first,other):
                    path=target/name
                    assert path.stat().st_size==detail['bytes'];self.pin(path,detail['sha256'])
            total_artifacts += len(record['artifact_sha256'])
            state=(first/'initial.state').read_bytes()
            assert state==(other/'initial.state').read_bytes()
            if initial_state is None:initial_state=state
            else:assert initial_state==state
            frames=read(first/'buffer-hashes.json')
            assert len(frames)==15200 and frames==read(other/'buffer-hashes.json')
            five=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
            if reference_frames is None:reference_frames=frames
            else:
                assert all(all(current[key]==reference[key] for key in five) and current['whole_serialized_state_bytes']==reference['whole_serialized_state_bytes'] for current,reference in zip(frames,reference_frames))
            callbacks=read(first/'audio-callbacks.json');assert len(callbacks)==15200
            audio=record['full_audio'];pcm_digest=hashlib.sha256();pcm_stops=[]
            wav_path=first/'full-audio.wav';self.pin(wav_path,audio['WAV_sha256'])
            with wave.open(str(wav_path),'rb') as wav:
                assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
                for i,(row,callback) in enumerate(zip(frames,callbacks)):
                    assert row['frame']==i+1 and callback['emulated_frame_start']==i
                    pcm=wav.readframes(callback['stereo_sample_frames'])
                    assert len(pcm)==4*callback['stereo_sample_frames'] and sha_bytes(pcm)==callback['pcm_sha256']==row['PCM_sha256']
                    pcm_digest.update(pcm);pcm_stops.append(wav.tell()*4)
                assert not wav.readframes(1) and wav.getnframes()==audio['stereo_sample_frames']==12140007
                assert wav.tell()*4==audio['PCM_bytes']==48560028
            assert pcm_digest.hexdigest()==audio['PCM_sha256']
            checkpoints=read(first/'checkpoints.json');assert len(checkpoints)==204 and checkpoints==read(other/'checkpoints.json')
            for point in checkpoints:
                row=frames[point['frame']-1]
                assert point['PCM_stop_byte']==pcm_stops[point['frame']-1]
                with Image.open(first/point['image']) as image:
                    assert image.size==(256,240) and sha_bytes(image.convert('RGB').tobytes())==row['RGB_sha256']
                for key,size in (('RAM',2048),('SRAM',8192)):
                    path=first/point[key];assert path.stat().st_size==size and self.pin(path)==row[key+'_sha256']
                path=first/point['state'];assert path.stat().st_size==row['whole_serialized_state_bytes'] and self.pin(path)==row['whole_serialized_state_sha256']
                context=prior.NestopiaContext.parse(path.read_bytes())
                assert context.ram==(first/point['RAM']).read_bytes() and context.sram==(first/point['SRAM']).read_bytes()
                png_checks+=1
            for filename in record['excluded_empty_VRAM']:
                assert (first/filename).stat().st_size==(other/filename).stat().st_size==0
            effect=record['verified_effects']
            assert effect['release_frame']==7635 and effect['original_selected_release_officers']==[5,30] and effect['released_statuses']==[0,0]
            assert effect['monthly_transitions']==2 and effect['wild_recruitment']==dict(frame=14837,officer=5,before_status=0,after_status=2,before_loyalty=86,after_loyalty=90,byte5_preserved=2,destination_city=2,roster_before=[222,38,153,109,255,255,255,255,255,255],roster_after=[222,38,153,109,5,255,255,255,255,255])
            assert effect['final_calendar']==[189,3] and effect['final_controller']==[2,2,0,1] and effect['actual_AI_continuation_returned_FF']
        assert total_artifacts==1669 and png_checks==408
        self.counts.update(native_input_routes=1,native_original_core_cases=1,native_core_variants=2,native_fresh_process_runs=4,
            native_frames_per_route=15200,native_all_control_frames=60800,native_additional_memory_writes=0,native_inherited_preparation_bytes=0,native_state_imports_per_run=1,
            native_nonempty_repeat_artifacts=1669,native_actual_PNG_checks=408,native_full_unique_WAV_checks=2,native_PCM_sample_pairs_per_route=12140007)
        return v

    def correlation(self,canonical,runtime):
        folder=OUT/'access-runtime';e,v=(read(folder/name) for name in ('evidence.json','verification.json'))
        assert e['status']==v['status']=='passed' and v['failed_count']==0
        self.records(e,v)
        raw=(OUT/'runtime/observer/bus-events.bin').read_bytes()
        events=[json.loads(line) for line in (OUT/'runtime/observer/events.jsonl').read_text().splitlines()]
        assert len(raw)==72*len(events)==372672 and len(events)==5176
        for i,event in enumerate(events):
            assert prior.decode_event(raw[72*i:72*(i+1)])==event and event['sequence']==i+1
            assert 1<=event['frame']<=15200 and event['rom_offset']==original(event['physical_bank'],event['opcode_PC'])
        city=[event for event in events if event['target_type']=='city_auxiliary']
        assert len(city)==e['city_bus_events']==25
        semantics=read(folder/'actual-city-bus-semantics.json');assert len(semantics)==25
        semantics_by_seq={r['sequence']:r for r in semantics}
        by_pc,by_slot=defaultdict(list),defaultdict(list);roles=Counter()
        for event in city:
            key=event['physical_bank'],event['opcode_PC'];authority=canonical[key];contract=authority['address_contract']
            assert event['address'] in AUX and self.rom[event['rom_offset']]==bytes.fromhex(authority['raw_hex'])[0]
            role=semantics_by_seq[event['sequence']];assert (role['physical_bank'],role['cpu'],role['address'],role['frame'])==(key[0],key[1],event['address'],event['frame'])
            assert event['kind']=='read'
            if role['role']=='dedicated_city_plus1_load':
                assert key==(10,0xBD97) and authority['classification']!=DISJOINT and event['address'] in intersection(contract)
            elif role['role']=='load_indirect_Y_page_cross_dummy_read':
                assert key==(11,0xC73F) and authority['classification']==DISJOINT
                pointer=event['pointer_0022_0023'];assert pointer==role['observed_pointer22']==0x63FC and event['Y']==5
                assert role['logical_effective_address']==pointer+event['Y']==0x6401
                assert event['address']==((pointer&0xFF00)|((pointer+event['Y'])&255))==0x6301
                assert event['address'] in dummy_intersection(contract,'LDA') and role['logical_effective_address'] not in AUX
            else:
                assert role['role']=='store_addressing_dummy_read' and key==(13,0xD243) and authority['classification']==DISJOINT
                assert event['address'] in dummy_intersection(contract,'STA')
                assert role['observed_pointer22'] is None and role['logical_effective_address'] is None
            roles[role['role']]+=1;by_pc[key].append(event);by_slot[event['city_index'],event['city_offset']].append(event)
        assert roles==dict(dedicated_city_plus1_load=22,load_indirect_Y_page_cross_dummy_read=2,store_addressing_dummy_read=1)
        assert (e['dedicated_or_logical_reads'],e['load_indirect_Y_page_cross_dummy_reads'],e['store_dummy_reads'],e['committed_writes'])==(22,2,1,0)
        associated=read(folder/'all1526-association.json');assert len(associated)==1526
        for row in associated:
            key=row['physical_bank'],row['cpu'];hit=by_pc[key]
            assert row['classification']==canonical[key]['classification'] and not row['negative_observation_excludes_access']
            assert row['sequences']==[event['sequence'] for event in hit] and row['observed_city_bus_events']==len(hit)
            assert row['observed_kinds']==Counter(event['kind'] for event in hit)
            assert row['observed_bus_roles']==Counter(semantics_by_seq[event['sequence']]['role'] for event in hit)
            assert row['observed_logical_effective_address_events']==sum(semantics_by_seq[event['sequence']]['role']=='dedicated_city_plus1_load' for event in hit)
        previous=read(folder/'previous376-association.json');assert len(previous)==376 and sum(r['newly_proved_disjoint'] for r in previous)==8
        slots=read(folder/'observed-field-slots.json');assert len(slots)==5
        for row in slots:
            hit=by_slot[row['city_index'],row['city_offset']]
            assert row['counts']==Counter(event['kind'] for event in hit) and row['sequences']==[event['sequence'] for event in hit]
        success=read(OUT/'runtime/observer-success.json');assert success['status']=='observed' and len(success['successful_scans'])==1
        scan=success['successful_scans'][0]
        begin,end=scan['scan_entry'],scan['success_RTS_boundary']
        assert events[begin['sequence']-1]==begin and events[end['sequence']-1]==end
        assert (begin['opcode_PC'],begin['SP'],end['opcode_PC'],end['SP'],end['frame'])==(0xC71A,0xF9,0xC794,0xFB,14837)
        assert scan['original_ROM_bytes_C792_C794']=='686860' and self.rom[original(11,0xC792):original(11,0xC795)]==b'\x68\x68\x60'
        assert success['E89A_observed_pairs']==62 and success['all_observed_E89A_X_preserved']
        assert v['checks']['source_CPU_cases']==e['source_CPU_cases']==v['checks']['negative_observations_promoted_to_exclusion']==0
        assert v['checks']['raw_decode_exact']==5176
        assert all(value is None for value in e['official_city_names'].values())
        self.counts.update(observer_raw_events=5176,observer_city_bus_events=25,observed_dedicated_city_plus1_reads=22,
            observed_STA_indirect_Y_dummy_reads_not_consumption=1,observed_LDA_pagecross_dummy_reads_not_consumption=2,
            observed_field_slots=5,actual_native_C794_success_exits=1,correlated_static_positions=1526,correlated_previous_candidates=376)

    def browser(self,allow_pending):
        required=[OUT/'README.md',OUT/'index.html',OUT/'browser-validation.json']
        missing=[str(p.relative_to(ROOT)) for p in required if not p.is_file()]
        if missing:
            assert allow_pending,('Missing final Root report/browser QA',missing)
            return dict(status='pending',expected_missing_final_artifacts=missing)
        qa=read(OUT/'browser-validation.json')
        assert qa['status']=='passed' and qa['console_errors']==[] and qa['check_count']==len(qa['checks'])>=20
        assert all(row['status']=='passed' for row in qa['checks'])
        self.pin(OUT/'index.html',qa['HTML_sha256'])
        page=prior.Page();page.feed((OUT/'index.html').read_text())
        source_paths=['postbattle_release_services.py','wild_recruitment_integration.py','city_recruitment_services.py']
        assert len(page.sources)==len(source_paths)==3
        for actual,path in zip(page.sources,source_paths):
            assert actual.encode('utf8')==(ROOT/'source/recovered'/path).read_bytes()
        data=json.loads(page.evidence)
        assert data['rows']==read(OUT/'access-runtime/previous376-association.json')
        for link in page.links:
            url=urlparse(link)
            if url.scheme or not url.path:continue
            path=(OUT/unquote(url.path)).resolve()
            if path in (OUT/'verification.json',ROOT/'build/三国志2超级版-逆向分析-v22.zip'):continue
            assert path.is_file(),('Broken portal link',link)
        screenshot=qa['screenshot'];self.pin(screenshot['path'],screenshot['sha256'])
        with Image.open(ROOT/screenshot['path']) as image:
            assert image.format==screenshot['format']
            if 'dimensions' in screenshot:assert list(image.size)==screenshot['dimensions']
        self.record_pins(qa)
        self.counts.update(browser_full_source_modules=3,browser_checks=len(qa['checks']))
        return dict(status='passed',receipt_path='analysis/phase22/browser-validation.json',receipt_sha256=self.pin(OUT/'browser-validation.json'),HTML_sha256=qa['HTML_sha256'])


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path)
    parser.add_argument('--allow-pending-browser',action='store_true')
    args=parser.parse_args();rom=args.rom.read_bytes();assert sha_bytes(rom)==ROM_SHA
    audit=Audit(rom);audit.frozen_history();canonical=audit.static_fields();audit.source_cases();audit.cpu_diagnostics()
    provenance=audit.core_provenance();runtime=audit.runtime(provenance);audit.correlation(canonical,runtime)
    browser=audit.browser(args.allow_pending_browser)
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path!=OUT/'verification.json' and path.name not in POSTZIP and '__pycache__' not in path.parts and not any(part.startswith('exploratory') for part in path.parts):
            audit.pin(path)
    for directory in ('source','scripts'):
        for path in sorted((ROOT/directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and not any(part.startswith('exploratory') for part in path.parts):
                relative=path.relative_to(ROOT).as_posix();digest=audit.pin(path)
                assert relative not in audit.sources or audit.sources[relative]==digest
                audit.sources[relative]=digest
    result=dict(schema='phase22-frozen-history-recruitment-guard-relations-and-natural-success-audit-v1',status='passed' if browser['status']=='passed' else 'pending_browser',
        ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v21_preserved_sha256=OLD_ZIP,old_phase21_audit_sha256=OLD_AUDIT,
        source_and_validator_sha256=audit.sources,artifact_and_dependency_sha256=audit.pins,checks=dict(audit.counts),browser=browser,
        source_CPU_cases=1384,source_actual_caller_RTS_cases=1378,source_nonlocal_return_cases=4,source_strict_dependency_prefix_cases=2,source_guard_cases=8,
        original_static_contract_CPU_cases=14754,static_model_guard_checks=17,
        limits=['Source1384 comparisons are distinct from14754 originalCPU static-contract checks,17 model guards,2 overlapping diagnostic continuations and5176 observer bus events.',
            'Four guarded pointer/index relations are conditional no-interrupt contracts. Their independent projection has150 auxiliary intersections while their actual disjunctive relation has0.',
            'Logical effective-address disjointness can coexist with dummy bus hits. The route has22 logical plus1 reads,1 STA dummy and2 LDA page-cross dummy reads; no field value is consumed by the dummy reads.',
            'One natural ordinary-input route is imported from an unchanged natural motherstate; separately pinned original and observer cores each run twice with full five-buffer equality. This is not universal emulator equivalence.',
            'Three originalCPU callee inputs explicitly add a hardware NMI/controller-port fixture; five are reached from the actual saved PC without new NMI. Neither is an original-core full instruction trace.',
            'No official city+1/+28..31 name, unused/reserved/padding theorem or complete whole-ROM reachability result is asserted.'])
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks=dict(audit.counts),source_pins=len(audit.sources),artifact_pins=len(audit.pins)),ensure_ascii=False))


if __name__=='__main__':main()
