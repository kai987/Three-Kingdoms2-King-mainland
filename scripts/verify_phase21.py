#!/usr/bin/env python3
"""Read-only phase21 aggregate. No CPU, core, compiler or old producer runs.

The only output is analysis/phase21/verification.json. Frozen phase20 pins are
strict inherited inputs. Source differential cases, original-CPU contracts,
passive-core bus events and model guards retain distinct counting domains.
"""
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import struct
import sys
from urllib.parse import unquote, urlparse
import wave
from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase21'
sys.path.insert(0, str(ROOT))
from source.recovered.nestopia_context import NestopiaContext

ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OLD_AUDIT = 'e548b4cd1a3a1c0f1890236b982d20fa8e7c63f4f16ee9a11deb2d04d8916205'
OLD_ZIP = 'b7fcfa4882c0442d697cfe01ef2ab0df530d2d73efe0aa1ec43e1c201b697463'
CORE_SHA = '924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
AUX = frozenset(0x6000 + 32 * c + o for c in range(30) for o in (1, 28, 29, 30, 31))
DISJOINT = 'proved_disjoint_auxiliary_address_domain'
POSTZIP = {'package-receipt.json', 'archive-validation.json', 'package-validation.json'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def original(bank, pc):
    return 16 + bank * 8192 + (pc & 8191)


def words(contract):
    if 'whole_pointer_values' in contract:
        return frozenset(contract['whole_pointer_values'])
    return frozenset(lo | hi << 8 for lo in contract['low_byte_values'] for hi in contract['high_byte_values'])


def intersection(contract):
    values = words(contract)
    return sorted(a for a in AUX if any(((a - y) & 65535) in values for y in contract['Y_values']))


class Audit:
    def __init__(self, rom):
        self.rom, self.pins, self.sources, self.counts = rom, {}, {}, Counter()
        self.sha_cache = {}

    def pin(self, path, expected=None):
        path = Path(path)
        path = path if path.is_absolute() else ROOT / path
        relative = path.relative_to(ROOT).as_posix()
        assert not any(part.startswith('exploratory') or part == '__pycache__' for part in path.parts), relative
        assert path.is_file(), f'Missing required artifact: {relative}'
        actual = self.sha_cache.setdefault(relative, sha(path)) if relative not in self.sha_cache else self.sha_cache[relative]
        assert expected is None or actual == expected, (relative, 'stale pin', expected, actual)
        assert relative not in self.pins or self.pins[relative] == actual
        self.pins[relative] = actual
        return actual

    def record_pins(self, record, folder=None):
        for group in ('source_sha256', 'source_and_validator_sha256', 'artifact_sha256', 'artifact_and_dependency_sha256', 'input_sha256', 'dependency_pins'):
            values = record.get(group, {})
            if isinstance(values, dict):
                for name, value in values.items():
                    expected = value.get('sha256') if isinstance(value, dict) else value
                    if not isinstance(expected, str):
                        continue
                    path = Path(name)
                    if folder is not None and not path.is_absolute() and path.parts[0] not in ('analysis', 'source', 'scripts', 'build', '.toolchain'):
                        path = folder / path
                    self.pin(path, expected)
            elif isinstance(values, list):
                for dep in values:
                    self.pin(dep['path'], dep['sha256'])
        for key in ('analyzer', 'validator'):
            if key + '_path' in record and key + '_sha256' in record:
                self.pin(record[key + '_path'], record[key + '_sha256'])
        for key in ('validation', 'trace_receipt', 'formal_Native_provenance'):
            value = record.get(key)
            if isinstance(value, dict) and 'path' in value and 'sha256' in value:
                self.pin(value['path'], value['sha256'])

    def raw(self, row, bank=None):
        if 'raw_hex' not in row:
            return
        physical = row.get('physical_bank', bank)
        pc = row.get('cpu', row.get('cpu_address', row.get('cpu_start', row.get('call_pc'))))
        assert physical is not None and pc is not None, row
        raw = bytes.fromhex(row['raw_hex'])
        offset = original(physical, pc)
        assert row.get('rom_offset', offset) == offset, row
        assert self.rom[offset:offset + len(raw)] == raw, row
        self.counts['original_raw_byte_objects_verified'] += 1

    def nested_raw(self, value):
        if isinstance(value, dict):
            if all(k in value for k in ('physical_bank', 'rom_offset', 'raw_hex')) and any(k in value for k in ('cpu', 'cpu_address', 'cpu_start')):
                self.raw(value)
            for child in value.values():
                self.nested_raw(child)
        elif isinstance(value, list):
            for child in value:
                self.nested_raw(child)

    def frozen_history(self):
        prior_path = ROOT / 'analysis/phase20/verification.json'
        self.pin(prior_path, OLD_AUDIT)
        prior = read(prior_path)
        assert prior['status'] == 'passed' and prior['rebuilt_byte_identical'] and prior['ROM_sha256'] == ROM_SHA
        assert len(prior['source_and_validator_sha256']) == 447
        assert len(prior['artifact_and_dependency_sha256']) == 29859
        for name, digest in prior['source_and_validator_sha256'].items():
            self.pin(name, digest)
            self.sources[name] = digest
        for name, digest in prior['artifact_and_dependency_sha256'].items():
            self.pin(name, digest)
        self.counts['unchanged_phase20_source_script_pins'] = 447
        self.counts['unchanged_phase20_artifact_dependency_pins'] = 29859
        assert sha(ROOT / 'build/三国志2超级版-逆向分析-v20.zip') == OLD_ZIP
        assert (ROOT / 'build/三国志2超级版.rebuilt.nes').read_bytes() == self.rom
        self.pin('build/三国志2超级版.rebuilt.nes')

    def static_fields(self):
        folder = OUT / 'fields-static'
        summary, validation, evidence = (read(folder / n) for n in ('analysis-summary.json', 'verification.json', 'evidence.json'))
        assert summary['status'] == 'analyzed' and validation['status'] == evidence['status'] == 'passed'
        assert validation['failed_count'] == 0 and summary['source_CPU_cases'] == validation['source_CPU_cases'] == 0
        for record in (summary, validation, evidence):
            self.record_pins(record)
        all_rows = read(folder / 'all-indirect-accesses.json')['accesses']
        canonical = {(r['physical_bank'], r['cpu']): r for r in all_rows}
        assert len(canonical) == len(all_rows) == 1526
        origin_files = {}
        for row in all_rows:
            self.raw(row)
            contract = row['address_contract']
            if contract is not None:
                found = intersection(contract)
                assert found == contract['possible_auxiliary_effective_addresses']
                assert len(found) == contract['auxiliary_address_intersection_count']
                assert row['whole_pointer_values'] == sorted(words(contract)) and row['Y_values'] == contract['Y_values']
            if row['classification'] == DISJOINT:
                assert contract is not None and not intersection(contract)
            origin = row.get('authoritative_contract_origin')
            if origin:
                self.pin(origin['path'], origin['sha256'])
                if origin['path'] not in origin_files:
                    origin_files[origin['path']] = {(r['physical_bank'], r['cpu']): r for r in read(ROOT / origin['path'])['accesses']}
                assert origin_files[origin['path']][row['physical_bank'], row['cpu']][origin['contract_field']] == contract
            assert row['candidate_contract_is_authoritative'] is False
            candidate = row['candidate_address_contract']
            assert row['candidate_whole_pointer_values'] == (sorted(words(candidate)) if candidate else None)
            assert row['candidate_Y_values'] == (candidate['Y_values'] if candidate else None)
            if row['newly_proved_disjoint']:
                required = contract['required_execution_contract']
                assert (required['original_entry_physical_bank'], required['original_entry_cpu']) == (11, 0xC71A)
                assert required['intervening_interrupts_or_external_mutation'] is False
                self.pin(required['path'])
        expected = {DISJOINT: 1150, 'possible_city_auxiliary_alias': 106, 'unresolved_pointer_or_index_contract': 270}
        assert Counter(r['classification'] for r in all_rows) == summary['all_indirect_classification_counts'] == expected
        for name, count, key in (('access-contracts.json', 589, 'classification_counts'), ('new-indirect-accesses.json', 45, 'new_indirect_classification_counts'), ('phase20-remaining380-handling.json', 380, None)):
            rec = read(folder / name)
            assert rec['access_count'] == len(rec['accesses']) == count
            assert Counter(r['classification'] for r in rec['accesses']) == rec['classification_counts']
            if key:
                assert rec['classification_counts'] == summary[key]
            for row in rec['accesses']:
                assert row == canonical[row['physical_bank'], row['cpu']]
        remaining = read(folder / 'remaining-accesses.json')['accesses']
        assert len(remaining) == summary['remaining_access_count'] == validation['remaining_access_count'] == 376
        assert {tuple((r['physical_bank'], r['cpu'])) for r in remaining} == {k for k, r in canonical.items() if r['classification'] != DISJOINT}
        assert sum(r['newly_proved_disjoint'] for r in all_rows) == summary['newly_proved_disjoint_all_count'] == 4
        assert all(v is None for v in summary['official_target_field_names'].values())
        direct = read(folder / 'direct-indexed-accesses.json')
        assert direct['instruction_count'] == len(direct['instructions']) == 19174
        for row in direct['instructions']:
            self.raw(row)
            mode, operand = row['mode'], row['operand']
            indices = range(256) if mode in ('abx', 'aby', 'zpx', 'zpy') else (0,)
            mask = 255 if mode in ('zpx', 'zpy') else 65535
            hit = {((operand + n) & mask) for n in indices} & AUX
            assert sorted(hit) == row['possible_auxiliary_effective_addresses'] and not hit
        raw = read(folder / 'untrusted-PRG-opcode-windows.json')
        assert raw['possible_auxiliary_window_count'] == len(raw['windows']) == 345
        for row in raw['windows']:
            off = 16 + row['physical_bank'] * 8192 + row['bank_offset']
            assert row['rom_offset'] == off and self.rom[off:off + 3] == bytes.fromhex(row['raw_hex'])
            assert not row['matching_trusted_instructions']
        assert validation['original_RNG_normal_return_CPU_cases'] == 65536
        assert validation['original_recruitment_loop_CPU_cases'] == len(validation['original_recruitment_loop_checks']) == 15
        assert (validation['original_recruitment_normal_return_cases'], validation['original_recruitment_success_prefix_cases']) == (8, 7)
        assert validation['model_guard_check_count'] == len(validation['model_checks']) == 20
        assert all(c['passed'] for c in validation['model_checks'])
        assert validation['external_scratch_clobber_model_counterexample_count'] == 1
        assert validation['original_RNG_checks']['external_scratch_clobber_counterexample']['observed_original_NMI'] is False
        assert summary['complete_analysis_fixed_point_proven'] is False
        for path in folder.glob('*.json'):
            self.nested_raw(read(path))
        self.counts.update(static_original_RNG_normal_RTS_contracts=65536, static_original_recruitment_normal_RTS_contracts=8,
            static_original_recruitment_success_prefix_contracts=7, static_model_and_output_checks=20,
            external_scratch_clobber_model_counterexamples=1, new_static_disjoint_accesses=4,
            remaining_auxiliary_candidates=376, static_unknown_accesses=270,
            trusted_direct_indexed_positions=19174, untrusted_raw_PRG_absolute_opcode_windows=345)
        return canonical

    def source_cases(self):
        folder = OUT / 'recruitment'
        body, evidence, catalog = (read(folder / n) for n in ('validation.json', 'evidence.json', 'static-catalog.json'))
        assert body['status'] == 'passed' and not body['quick'] and not body['failures'] and body['failed_count'] == 0
        assert body['original_CPU_parent_cases'] == len(body['cases']) == 2448
        expect = dict(actual_caller_RTS=2415, actual_nonlocal_return=30, original_loop_wait=1, strict_missing_dependency_prefix=2)
        assert Counter(r['comparison'] for r in body['cases']) == body['counts'] == expect
        assert body['source_guard_count'] == len(body['guards']) == 3 and all(g['status'] == 'passed' for g in body['guards'])
        assert body['source_original_CPU_callbacks'] == evidence['production_original_CPU_callbacks'] == 0
        assert not body['production_IR_interpretation'] and not evidence['production_IR_interpretation'] and not evidence['production_runtime_codegen']
        for row in body['cases']:
            assert (row['RAM_bytes'], row['SRAM_bytes']) == (2048, 8192)
            assert row['all_registers_ordered_IO_banks_N163_equal'] and row['source_original_CPU_callbacks'] == 0
        coverage = evidence['coverage']
        assert coverage['static_new_manual_instruction_positions'] == coverage['dynamically_executed_new_manual_positions'] == len(catalog['instructions']) == 225
        assert coverage['new_manual_code_bytes'] == 476 and coverage['not_dynamically_executed'] == 0
        assert coverage['all_paths_or_all_inputs_proven'] is False
        executed = {(r['physical_bank'], r['cpu_address']) for r in body['executed_instruction_positions']}
        for row in catalog['instructions']:
            self.raw(row)
            assert (row['physical_bank'], row['cpu_address']) in executed
        for row in catalog['original_ranges']:
            self.raw(row)
            assert len(bytes.fromhex(row['raw_hex'])) == row['byte_count']
        for row in catalog['real_dependencies']:
            self.raw(row, bank=11)
            assert bytes.fromhex(row['raw_hex']) == bytes((0x20, row['target'] & 255, row['target'] >> 8))
        integration = read(OUT / 'source-integration.json')
        assert integration['status'] == 'passed' and integration['original_CPU_parent_cases'] == len(integration['rows']) == 5
        assert Counter(r['completion'] for r in integration['rows']) == integration['counts'] == dict(returned=4, nonlocal_return=1)
        assert integration['guard_count'] == len(integration['guards']) == 3
        assert integration['source_original_CPU_callbacks'] == 0 and not integration['production_IR_interpretation'] and not integration['Native_internal_CPU_trace']
        for row in integration['rows']:
            assert row['all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal'] and row['source_original_CPU_callbacks'] == 0
            assert row['prepared_new_bytes'] == (row['origin'] == 'controlled_terminal_fixture')
            if row['completion'] == 'nonlocal_return':
                assert row['terminal_repeat_unchanged'] is True
        assert sum(r['origin'] == 'actual_Native_snapshot_original_CPU_reached_caller' for r in integration['rows']) == 4
        for record in (body, evidence, integration):
            self.record_pins(record)
        # Only new production modules: old historical IR artifacts remain frozen
        # analysis artifacts and are not silently reclassified as new source.
        for filename in ('city_recruitment_services.py', 'city_recruitment_integration.py'):
            tree = ast.parse((ROOT / 'source/recovered' / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
                    assert not any(any(bad in name for bad in ('py65', 'state_machine', 'artifact_session', 'importlib')) for name in names), (filename, names)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in ('eval', 'exec', 'compile', '__import__'), (filename, node.lineno)
        self.counts.update(controlled_and_actual_source_matrix_cases=2448, source_matrix_actual_RTS=2415,
            source_matrix_nonlocal_returns=30, source_matrix_original_loop_wait=1, source_matrix_missing_dependency_prefixes=2,
            integration_source_CPU_parent_cases=5, integration_actual_RTS=4, integration_nonlocal_terminal=1,
            new_source_CPU_parent_cases=2453, new_source_actual_caller_RTS_parents=2419,
            new_source_nonlocal_return_parents=31, new_source_wait_parents=1, new_source_strict_dependency_prefixes=2,
            new_source_guards=6, named_original_static_positions=225, named_original_manual_bytes=476)

    def cpu_diagnostics(self):
        evidence, trace = (read(OUT / 'cpu' / n) for n in ('evidence.json', 'runtime-trace.json'))
        assert evidence['status'] == trace['status'] == 'bounded_original_CPU_observation'
        assert evidence['source_CPU_comparison_cases'] == trace['source_CPU_comparison_cases'] == 0
        assert evidence['contexts'] == len(trace['contexts']) == 3 and evidence['exported_actual_caller_entries'] == len(trace['captured_callers']) == 5
        assert evidence['prepared_bytes'] == trace['PC_RNG_request_ready_or_caller_injections'] == 0
        assert evidence['new_NMI_IRQ_arrivals'] == trace['new_NMI_IRQ_arrivals'] == 0
        assert not evidence['Native_internal_CPU_trace'] and not trace['Native_internal_CPU_trace']
        assert evidence['original_CPU_instructions'] == sum(c['original_instructions'] for c in trace['contexts']) == 101157
        assert evidence['total_city_accesses'] == trace['total_city_accesses'] == 7723
        assert evidence['target_auxiliary_accesses'] == trace['target_auxiliary_accesses'] == len(trace['target_auxiliary_observations']) == 5
        for row in trace['contexts']:
            self.pin(row['native_state'], row['native_sha256'])
            assert row['prepared_bytes'] == [] and row['new_NMI_IRQ_arrivals'] == 0 and not row['Native_internal_CPU_trace']
            captured = NestopiaContext.parse((ROOT / row['native_state']).read_bytes())
            assert captured.registers == row['captured_registers'] and list(captured.prg_banks) == row['actual_PRG_banks']
        for row in trace['target_auxiliary_observations']:
            assert row['ROM_offset'] == original(row['physical_bank'], row['pc'])
            assert self.rom[row['ROM_offset']] == row['opcode']
            assert row['target_auxiliary'] and row['effective_address'] in AUX
        for record in (evidence, trace):
            self.record_pins(record)
        self.counts.update(original_CPU_diagnostic_contexts_not_source_cases=3,
            original_CPU_diagnostic_instructions=101157, diagnostic_exported_caller_entries=5)

    def core_provenance(self):
        folder = OUT / 'runtime/core-provenance'
        provenance = read(folder / 'build.json')
        assert provenance['status'] == 'recorded' and provenance['commit'] == '135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
        assert provenance['original_git_tree'] == 'e5e257e800213b13b53008b5deb47f2da4f7f3b7'
        assert not provenance['modified_emulator_object_layout'] and not provenance['toolchain_in_release_archive']
        assert provenance['original_core']['sha256'] == CORE_SHA
        for key in ('original_core', 'pristine_rebuild', 'passive_observer'):
            self.pin(provenance[key]['path'], provenance[key]['sha256'])
        self.pin(folder / 'observer.patch', provenance['patch_sha256'])
        patched = apply_patch_in_memory((folder / 'observer.patch').read_bytes(), folder / 'upstream')
        assert len(provenance['source_files']) == 10
        for source in provenance['source_files']:
            path = folder / 'upstream' / source['path']
            if source['original_sha256'] is not None:
                self.pin(path, source['original_sha256'])
                original_raw = path.read_bytes()
            else:
                assert source['path'] in patched
                original_raw = b''
            result = patched.get(source['path'], original_raw)
            assert hashlib.sha256(result).hexdigest() == source['patched_sha256'], source['path']
        assert set(patched) == {'source/core/NstCpu.cpp', 'source/core/board/NstBoard.cpp', 'source/core/board/NstBoard.hpp', 'source/core/NstWatch.hpp', 'source/core/NstWatch.cpp.inc'}
        for filename in ('baseline-build.log', 'observer-build.log'):
            assert (folder / filename).stat().st_size > 0
            self.pin(folder / filename)
        self.counts.update(independent_core_variants=3, archived_upstream_original_files=8,
                           in_memory_patch_source_hash_checks=10)
        return provenance

    def runtime(self, provenance):
        folder = OUT / 'runtime'
        validation, evidence = (read(folder / n) for n in ('validation.json', 'evidence.json'))
        assert validation['status'] == evidence['status'] == 'passed' and validation['failed_count'] == 0
        self.pin(folder / 'evidence.json', validation['evidence_sha256'])
        self.pin('scripts/capture_city_auxiliary_watchpoints.py', validation['script_sha256'])
        assert all(validation[k] == value for k, value in evidence['summary'].items())
        assert (validation['natural_input_routes'], validation['core_variants'], validation['fresh_process_runs']) == (1, 3, 6)
        assert (validation['frames_per_complete_route'], validation['frames_first_run_controls'], validation['frames_both_runs_controls']) == (11589, 34767, 69534)
        assert validation['additional_core_memory_writes'] == validation['state_imports'] == 0
        for key in ('all_five_complete_buffer_hashes_match_original_each_frame', 'all_initial_full_API_buffers_equal', 'all_raw_artifacts_repeat_exact'):
            assert validation[key] is True
        reference_folder = ROOT / evidence['original_reference_case']
        reference = read(reference_folder / 'frame-services.json')
        assert len(reference) == 11589
        five = ('RAM_sha256', 'SRAM_sha256', 'RGB_sha256', 'PCM_sha256', 'whole_serialized_state_sha256')
        artifacts, points_count = 0, 0
        variants = {'original-control': 'original_core', 'pristine-rebuild': 'pristine_rebuild', 'observer-accept': 'passive_observer'}
        assert {r['variant'] for r in evidence['runs']} == set(variants)
        for run in evidence['runs']:
            first = folder / run['variant']
            record = read(folder / run['validation'])
            repeat = read(folder / run['repeat_validation'])
            other = ROOT / repeat['second_run']
            assert record['status'] == repeat['status'] == 'passed' and not record['failures']
            assert record['frames'] == run['frames'] == 11589 and record['complete_original_input_route']
            assert record['cold_boot'] and not record['state_imported'] and record['additional_core_memory_writes'] == 0
            assert not record['serialized_buffer_normalized'] and record['initial_full_serialized_bytes_equal']
            assert record['first_serialize_query_at_cold_boot'] and not record['additional_callback_into_emulated_CPU']
            assert not record['Native_internal_instruction_trace'] and not record['original_core_internal_trace_claim']
            assert record['current_core']['core_sha256'] == run['core_sha256'] == provenance[variants[run['variant']]]['sha256']
            assert record['observer_core_CPU_bus_log'] == (run['variant'] == 'observer-accept')
            assert repeat['all_artifact_bytes_exact'] and repeat['full_serialized_buffers_not_normalized']
            assert repeat['artifact_checks'] == len(repeat['artifacts']) == (43 if record['observer_core_CPU_bus_log'] else 39)
            assert {r['path'] for r in repeat['artifacts']} == set(record['artifact_sha256'])
            second_record = read(other / 'validation.json')
            assert second_record['artifact_sha256'] == record['artifact_sha256'] and second_record['frames'] == 11589
            for item in repeat['artifacts']:
                assert item['bytes'] > 0 and record['artifact_sha256'][item['path']] == {k: item[k] for k in ('bytes', 'sha256')}
                for target in (first, other):
                    path = target / item['path']
                    assert path.stat().st_size == item['bytes']
                    self.pin(path, item['sha256'])
            artifacts += len(repeat['artifacts'])
            self.pin(record['original_reference_validation'], record['original_reference_validation_sha256'])
            self.pin(record['original_reference_frames'], record['original_reference_frames_sha256'])
            assert (first / 'initial.state').read_bytes() == (other / 'initial.state').read_bytes() == (reference_folder / 'initial.state').read_bytes()
            for current in (first, other):
                frames = read(current / 'frame-parity.json')
                callbacks = read(current / 'audio-callbacks.json')
                assert len(frames) == len(callbacks) == 11589
                audio = record['full_audio']
                wav_path = current / audio['saved_path'] if audio['saved_path'] else ROOT / audio['original_reference_path']
                self.pin(wav_path, audio['WAV_sha256'])
                pcm_hash = hashlib.sha256()
                with wave.open(str(wav_path), 'rb') as wav:
                    assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (2, 2, 48000)
                    for i, row in enumerate(frames):
                        old = reference[i]
                        assert row['frame'] == old['frame'] == i + 1 and row['all_five_match_original']
                        assert all(row[k] == old[k] for k in five)
                        assert row['actual_saved_CPU_registers'] == old['actual_saved_CPU_registers']
                        assert row['actual_saved_PRG_banks'] == old['actual_saved_PRG_banks']
                        cb = callbacks[i]
                        assert cb['emulated_frame_start'] == i and cb['stereo_sample_frames'] == row['PCM_stereo_sample_frames'] and cb['pcm_sha256'] == row['PCM_sha256']
                        pcm = wav.readframes(row['PCM_stereo_sample_frames'])
                        assert len(pcm) == row['PCM_bytes'] == 4 * row['PCM_stereo_sample_frames']
                        assert hashlib.sha256(pcm).hexdigest() == row['PCM_sha256']
                        pcm_hash.update(pcm)
                        assert wav.tell() * 4 == row['PCM_stop_byte']
                    assert not wav.readframes(1) and wav.getnframes() == audio['stereo_sample_frames'] == 9255892
                assert pcm_hash.hexdigest() == audio['PCM_sha256']
                checkpoints = read(current / 'checkpoints.json')
                assert len(checkpoints) == record['checkpoint_count'] == 8
                for point in checkpoints:
                    row = frames[point['frame'] - 1]
                    with Image.open(current / point['image']) as image:
                        assert image.size == (256, 240) and hashlib.sha256(image.convert('RGB').tobytes()).hexdigest() == row['RGB_sha256']
                    for key, size in (('RAM', 2048), ('SRAM', 8192)):
                        path = current / point[key]
                        assert path.stat().st_size == size and sha(path) == row[key + '_sha256']
                    path = current / point['state']
                    assert sha(path) == row['whole_serialized_state_sha256']
                    capture = NestopiaContext.parse(path.read_bytes())
                    assert capture.ram == (current / point['RAM']).read_bytes() and capture.sram == (current / point['SRAM']).read_bytes()
                    assert capture.registers == row['actual_saved_CPU_registers'] and list(capture.prg_banks) == row['actual_saved_PRG_banks']
                points_count += len(checkpoints)
            for filename in record['excluded_empty_VRAM']:
                assert (first / filename).stat().st_size == (other / filename).stat().st_size == 0
        assert artifacts == 121 and points_count == 48
        self.counts.update(native_routes=1, native_core_variants=3, native_fresh_process_runs=6,
            native_first_run_control_frames=34767, native_all_control_frames=69534,
            native_nonempty_repeat_artifacts=121, native_checkpoints_all_six_runs=48,
            native_five_buffer_frame_comparisons=69534, original_PCM_sample_pairs_per_complete_route=9255892)
        return validation

    def correlation(self, canonical, runtime):
        folder = OUT / 'access-runtime'
        verification, evidence = (read(folder / n) for n in ('verification.json', 'evidence.json'))
        assert verification['status'] == evidence['status'] == 'passed' and verification['failed_count'] == 0
        self.record_pins(verification)
        raw = (OUT / 'runtime/observer-accept/bus-events.bin').read_bytes()
        events = [json.loads(line) for line in (OUT / 'runtime/observer-accept/events.jsonl').read_text().splitlines()]
        assert len(raw) == 72 * len(events) == 236088 and len(events) == 3279
        for i, event in enumerate(events):
            assert decode_event(raw[72 * i:72 * (i + 1)]) == event
            assert event['sequence'] == i + 1 and 1 <= event['frame'] <= 11589
            assert event['rom_offset'] == original(event['physical_bank'], event['opcode_PC'])
        city = [e for e in events if e['target_type'] == 'city_auxiliary']
        assert len(city) == evidence['city_bus_events'] == runtime['observer_city_auxiliary_events'] == 612
        dummy, semantic, writes = [], [], []
        by_pc, by_slot = defaultdict(list), defaultdict(list)
        for i, event in enumerate(events):
            if event['target_type'] != 'city_auxiliary':
                continue
            assert event['address'] in AUX
            key = event['physical_bank'], event['opcode_PC']
            assert key in canonical and canonical[key]['classification'] != DISJOINT
            by_pc[key].append(event)
            by_slot[event['city_index'], event['city_offset']].append(event)
            opcode = self.rom[event['rom_offset']]
            if event['kind'] == 'read' and opcode == 0x91:
                nxt = events[i + 1]
                assert nxt['kind'] == 'write_attempt' and all(nxt[k] == event[k] for k in ('frame', 'cycle', 'address', 'physical_bank', 'opcode_PC'))
                dummy.append(event)
            elif event['kind'] == 'read':
                assert (event['physical_bank'], event['opcode_PC'], opcode) == (10, 0xBD97, 0xB1)
                semantic.append(event)
            else:
                assert event['kind'] == 'write_attempt' and opcode == 0x91 and event['WRAM_writable'] and event['storage_byte_after_event'] == event['value']
                writes.append(event)
        assert (len(dummy), len(semantic), len(writes), len(by_pc), len(by_slot)) == (300, 12, 300, 3, 150)
        assert (evidence['STA_indirect_Y_dummy_reads'], evidence['dedicated_load_reads'], evidence['committed_bulk_writes']) == (300, 12, 300)
        all_rows = read(folder / 'all1526-association.json')
        assert len(all_rows) == 1526
        for row in all_rows:
            key = row['physical_bank'], row['cpu']
            assert row['classification'] == canonical[key]['classification'] and not row['negative_observation_excludes_access']
            hits = by_pc[key]
            assert row['sequences'] == [e['sequence'] for e in hits]
            assert row['observed_city_bus_events'] == len(hits) and row['observed_kinds'] == Counter(e['kind'] for e in hits)
        old380 = read(folder / 'previous380-association.json')
        assert len(old380) == 380 and sum(r['newly_proved_disjoint'] for r in old380) == 4
        assert {tuple((r['physical_bank'], r['cpu'])) for r in old380} == {tuple((r['physical_bank'], r['cpu'])) for r in read(OUT / 'fields-static/phase20-remaining380-handling.json')['accesses']}
        slots = read(folder / 'all150-field-slots.json')
        assert len(slots) == 150
        for row in slots:
            hit = by_slot[row['city_index'], row['city_offset']]
            assert row['counts'] == Counter(e['kind'] for e in hit)
            assert row['semantic_read_sequences'] == [e['sequence'] for e in semantic if (e['city_index'], e['city_offset']) == (row['city_index'], row['city_offset'])]
            assert row['dummy_read_sequences'] == [e['sequence'] for e in dummy if (e['city_index'], e['city_offset']) == (row['city_index'], row['city_offset'])]
            assert row['write_sequences'] == [e['sequence'] for e in writes if (e['city_index'], e['city_offset']) == (row['city_index'], row['city_offset'])]
        assert all(v is None for v in evidence['official_names'].values())
        assert evidence['source_CPU_cases'] == verification['checks']['source_CPU_cases'] == verification['checks']['negative_observations_promoted_to_exclusion'] == 0
        assert verification['checks']['raw_decode_exact'] == 3279 and verification['checks']['static_opcode_byte_matches'] == 1526
        assert evidence['bounded_recruitment_observation'] == runtime['bounded_recruitment_observation'] == dict(C71A_entry_count=3, C75F_loop_steps=711, C762_loop_checks=711, C732_recruitment_RNG_calls=0, C794_recruitment_success_exits=0)
        observed_rng = read(OUT / 'runtime/RNG-save-restore-observations.json')
        assert observed_rng['status'] == 'observed' and len(observed_rng['pairs']) == runtime['E89A_observed_entry_exit_pairs'] == 12
        for pair in observed_rng['pairs']:
            enter, leave = events[pair['entry_sequence'] - 1], events[pair['exit_sequence'] - 1]
            assert (enter['physical_bank'], enter['opcode_PC'], leave['physical_bank'], leave['opcode_PC']) == (31, 0xE89A, 31, 0xE8A9)
            assert enter['X'] == pair['X_entry'] == leave['X'] == pair['X_exit']
        assert sum(e['target_type'] == 'cpu_scratch_0053' for e in events) == runtime['observer_RAM53_write_events'] == 615
        self.counts.update(observer_raw_events=3279, observer_city_bus_events=612,
            STA_indirect_Y_dummy_reads_not_semantic_consumption=300, committed_bulk_city_writes=300,
            dedicated_city_plus1_reads=12, correlated_static_positions=1526, correlated_previous_candidates=380,
            field_slots_accounted=150, observed_RNG_entry_exit_pairs=12, observed_RAM53_write_events=615)

    def browser(self, allow_pending):
        required = (OUT / 'README.md', OUT / 'index.html', OUT / 'browser-validation.json')
        missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
        if missing:
            assert allow_pending, ('Missing final Root documents/browser QA', missing)
            return {'status': 'pending', 'expected_missing_final_artifacts': missing}
        qa = read(OUT / 'browser-validation.json')
        assert qa['status'] == 'passed' and qa['console_errors'] == []
        self.pin(OUT / 'index.html', qa['HTML_sha256'])
        assert qa['check_count'] == len(qa['checks']) and len(qa['checks']) >= 20
        assert all(row['status'] == 'passed' for row in qa['checks'])
        parser = Page()
        parser.feed((OUT / 'index.html').read_text())
        source_paths = ('source/recovered/city_recruitment_services.py', 'source/recovered/city_recruitment_integration.py')
        assert len(parser.sources) == 2
        for actual, path in zip(parser.sources, source_paths):
            assert actual.encode('utf8') == (ROOT / path).read_bytes()
            self.pin(path)
        data = json.loads(parser.evidence)
        assert data['rows'] == read(OUT / 'access-runtime/previous380-association.json')
        assert data['points'] == read(OUT / 'runtime/observer-accept/checkpoints.json')
        events = [json.loads(line) for line in (OUT / 'runtime/observer-accept/events.jsonl').read_text().splitlines()]
        assert data['events'] == events
        assert (len(data['rows']), len(data['points']), len(data['events'])) == (380, 8, 3279)
        for href in parser.links:
            url = urlparse(href)
            if url.scheme or not url.path:
                continue
            path = (OUT / unquote(url.path)).resolve()
            if path in (OUT / 'verification.json', ROOT / 'build/三国志2超级版-逆向分析-v21.zip'):
                continue
            assert path.is_file(), ('Broken portal link', href)
        screenshot = qa['screenshot']
        self.pin(screenshot['path'], screenshot['sha256'])
        with Image.open(ROOT / screenshot['path']) as image:
            assert image.format == screenshot['format']
            if 'dimensions' in screenshot:
                assert list(image.size) == screenshot['dimensions']
        self.record_pins(qa)
        self.counts.update(browser_full_source_modules=2, browser_raw_candidate_rows=380,
                           browser_actual_checkpoints=8, browser_checks=len(qa['checks']))
        return {'status': 'passed', 'receipt_path': 'analysis/phase21/browser-validation.json',
                'receipt_sha256': self.pin(OUT / 'browser-validation.json'), 'HTML_sha256': qa['HTML_sha256']}


def decode_event(raw):
    seq, frame, cycle, kind, pc, buspc, address, value, a, x, y, p, sp, banks, scratch, working, permission, storage = struct.unpack('<18I', raw)
    pages = [(banks >> shift) & 255 for shift in (0, 8, 16, 24)]
    bank = pages[(pc - 0x8000) // 8192] if 0x8000 <= pc < 0xFFFF else None
    target = 'sparse_opcode_boundary' if kind == 2 else 'city_auxiliary' if 0x6000 <= address < 0x63C0 else 'cpu_scratch_0053'
    return dict(sequence=seq, frame=frame, cycle=cycle, kind={0:'read', 1:'write_attempt', 2:'opcode_boundary', 3:'word_read_low', 4:'word_read_high'}[kind],
        opcode_PC=pc if pc != 0xFFFF else None, bus_PC=buspc, physical_bank=bank,
        rom_offset=None if bank is None else original(bank, pc), actual_PRG_banks=pages,
        address=address, value=value, A=a, X=x, Y=y, P=p, SP=sp,
        scratch_0053_0054=[scratch & 255, (scratch >> 8) & 255], pointer_0022_0023=scratch >> 16,
        working_0036_0039=[(working >> shift) & 255 for shift in (0, 8, 16, 24)],
        target_type=target, city_index=(address-0x6000)//32 if target == 'city_auxiliary' else None,
        city_offset=(address-0x6000)%32 if target == 'city_auxiliary' else None,
        WRAM_readable=bool(permission & 1), WRAM_writable=bool(permission & 2),
        storage_byte_after_event=None if storage == 0xFFFFFFFF else storage)


def apply_patch_in_memory(raw_patch, original_folder):
    """Apply exact ordinary unified hunks in memory, verifying every old line."""
    sections, current = {}, None
    for line in raw_patch.splitlines(keepends=True):
        if line.startswith(b'diff --git '):
            current = line.rstrip().split(b' b/', 1)[1].decode()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    result = {}
    for path, section in sections.items():
        original_path = original_folder / path
        before = original_path.read_bytes().splitlines(keepends=True) if original_path.exists() else []
        after, cursor, i = [], 0, 0
        while i < len(section):
            line = section[i]
            if not line.startswith(b'@@ '):
                i += 1
                continue
            match = re.match(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            assert match, (path, line)
            old_start = int(match[1]) - 1 if int(match[1]) else 0
            old_count, new_count = int(match[2] or b'1'), int(match[4] or b'1')
            assert old_start >= cursor
            after.extend(before[cursor:old_start]); cursor = old_start
            i += 1; removed = inserted = 0
            while i < len(section) and not section[i].startswith(b'@@ '):
                hunk = section[i]
                if hunk.startswith(b'\\ No newline'):
                    raise AssertionError('Unmodeled no-newline patch marker')
                if not hunk or hunk[:1] not in (b' ', b'-', b'+'):
                    break
                prefix, content = hunk[:1], hunk[1:]
                if prefix in (b' ', b'-'):
                    assert cursor < len(before) and before[cursor] == content, (path, cursor, hunk)
                    cursor += 1; removed += 1
                if prefix in (b' ', b'+'):
                    after.append(content); inserted += 1
                i += 1
            assert (removed, inserted) == (old_count, new_count), (path, removed, inserted, old_count, new_count)
        after.extend(before[cursor:])
        result[path] = b''.join(after)
    return result


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_source = False; self.in_pre = False; self.in_evidence = False
        self.current = ''; self.sources = []; self.evidence = ''; self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('class') == 'source':
            self.in_source = True
        if tag == 'pre' and self.in_source:
            self.in_pre = True; self.current = ''
        if tag == 'script' and attrs.get('id') == 'evidenceData':
            self.in_evidence = True
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])
    def handle_endtag(self, tag):
        if tag == 'pre' and self.in_pre:
            self.sources.append(self.current); self.in_pre = False
        if tag == 'details':
            self.in_source = False
        if tag == 'script':
            self.in_evidence = False
    def handle_data(self, text):
        if self.in_pre:
            self.current += text
        if self.in_evidence:
            self.evidence += text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--allow-pending-browser', action='store_true', help='Explicit provisional output; never sets passed without final Root QA')
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA
    audit = Audit(rom)
    audit.frozen_history()
    canonical = audit.static_fields()
    audit.source_cases()
    audit.cpu_diagnostics()
    provenance = audit.core_provenance()
    runtime = audit.runtime(provenance)
    audit.correlation(canonical, runtime)
    browser = audit.browser(args.allow_pending_browser)
    # Exact new-area traversal: retain empty raw VRAM as files, but it is never
    # counted as effective parity content. No excluded exploratory dependency.
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path != OUT / 'verification.json' and path.name not in POSTZIP and '__pycache__' not in path.parts and not any(p.startswith('exploratory') for p in path.parts):
            audit.pin(path)
    for folder in ('source', 'scripts'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and not any(p.startswith('exploratory') for p in path.parts):
                relative = path.relative_to(ROOT).as_posix()
                digest = audit.pin(path)
                assert relative not in audit.sources or audit.sources[relative] == digest
                audit.sources[relative] = digest
    status = 'passed' if browser['status'] == 'passed' else 'pending_browser'
    result = dict(schema='phase21-frozen-history-city-field-recruitment-and-passive-core-audit-v1', status=status,
        ROM_sha256=ROM_SHA, rebuilt_byte_identical=True, old_v20_preserved_sha256=OLD_ZIP, old_phase20_audit_sha256=OLD_AUDIT,
        source_and_validator_sha256=audit.sources, artifact_and_dependency_sha256=audit.pins, checks=dict(audit.counts), browser=browser,
        limits=['2453 source comparisons are distinct from65551 original-CPU static-contract checks, model guards and three overlapping originalCPU diagnostic continuations.',
            'Four new disjoint recruitment contracts require the initializer-rooted ordinary no-interrupt execution; Native did not observe the successful recruitment branch.',
            'The observer core is separately rebuilt/instrumented; five-buffer parity holds only for the six recorded executions and is not universal binary equivalence.',
            '300 STA-indirect-Y dummy bus reads are not dedicated gameplay field consumption; only12 dedicated plus1 reads were observed on this route.',
            'No formal name, unused/reserved/padding status or whole-ROM reachability theorem is inferred for city+1/+28..31.',
            'Core binaries are provenance-pinned external runtimes; archived original source copies plus exact patch are independently hash-reconstructed in memory.'])
    (OUT / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(status=status, checks=dict(audit.counts), source_pins=len(audit.sources), artifact_pins=len(audit.pins)), ensure_ascii=False))


if __name__ == '__main__':
    main()
