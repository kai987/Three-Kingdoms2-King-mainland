#!/usr/bin/env python3
"""Verify phase7 ROM provenance, source pins, scoped CPU receipts and replays."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from inspect_game_data import OPS, SIZES
from source.recovered.game_engine import ROM_SHA256

BRANCHES = {'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads((ROOT / path).read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('rom',type=Path)
    args = parser.parse_args(); rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes() == rom
    program_path = 'analysis/phase7/controller/program.json'
    catalog_path = 'analysis/phase7/controller/state-catalog.json'
    program, catalog = read(program_path), read(catalog_path)
    assert program['rom_sha256'] == catalog['rom_sha256'] == ROM_SHA256
    occupied = set()
    for item in program['instructions']:
        pc, offset = item['pc'], item['file']
        assert item['bank'] == 8 and offset == 16+8*8192+pc-0xA000
        op, mode = OPS[rom[offset]]; size = SIZES[mode]
        assert op == item['op'], (hex(pc), op, item['op'])
        raw = rom[offset:offset+size]; assert raw == bytes.fromhex(item['raw_hex'])
        operand = int.from_bytes(raw[1:],'little')
        if op in BRANCHES: operand = (pc+size+(operand if operand<128 else operand-256))&65535
        assert operand == item['operand']
        assert not occupied.intersection(range(pc,pc+size)); occupied.update(range(pc,pc+size))
    assert len(program['instructions']) == 2213
    assert program['inline_tables'] == catalog['inline_tables']
    assert [t['count'] for t in program['inline_tables']] == [8,16]
    for table in program['inline_tables']:
        offset, cpu, count = table['table_file'], table['table_cpu'], table['count']
        assert cpu+count*2 == min(table['targets'])
        assert not occupied.intersection(range(cpu,cpu+count*2))
        assert bytes.fromhex(table['raw_hex']) == rom[offset:offset+count*2]
        for i, target in enumerate(table['targets']):
            assert int.from_bytes(rom[offset+2*i:offset+2*i+2],'little') == target
    for item in catalog['inline_helper_evidence']:
        offset = item['file']; raw = bytes.fromhex(item['raw_hex'])
        assert raw == rom[offset:offset+len(raw)]
    assert set(catalog['shared_helpers']) == {'F266'}
    assert not catalog['inline_audit']['reachable_EADE_calls'] and not catalog['inline_audit']['reachable_EE07_calls']
    receipts = {area:read(f'analysis/phase7/{area}/validation.json') for area in ('controller','decisions','exchange')}
    for area, receipt in receipts.items():
        assert receipt['status'] == 'passed' and not receipt['failures'], area
        assert receipt['rom_sha256'] == ROM_SHA256
    controller = receipts['controller']
    for key, path in [('source_sha256','source/recovered/tactical_ai_control.py'),
                      ('validator_sha256','scripts/verify_tactical_ai_control.py'),
                      ('program_sha256',program_path),('catalog_sha256',catalog_path)]:
        assert controller[key] == digest(ROOT/path), path
    for name, expected in controller['dependency_source_sha256'].items():
        assert expected == digest(ROOT/'source/recovered'/name), name
    decisions = read('analysis/phase7/decisions/evidence.json')
    for entry in decisions['routines']:
        offset = entry['rom_offset']; raw = bytes.fromhex(entry['raw_hex'])
        assert raw == rom[offset:offset+len(raw)] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    for pin in decisions['dependency_pins']:
        assert digest(ROOT/pin['file']) == pin['sha256'], pin['file']
    for row in decisions['terrain_data']['chunks']:
        raw = rom[row['rom_offset']:row['rom_offset']+row['byte_count']]
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
    rng = decisions['rng_data']; raw = rom[rng['rom_offset']:rng['rom_offset']+rng['byte_count']]
    assert hashlib.sha256(raw).hexdigest() == rng['sha256'] and len(set(raw)) == 256
    classes = decisions['terrain_data']; offset = classes['class_table_rom_offset']
    assert hashlib.sha256(rom[offset:offset+128]).hexdigest() == classes['classes_sha256']
    for kind in ('first','second'):
        costs = decisions['cost_tables']; offset = costs[kind+'_rom_offset']
        expected = bytes(x for row in costs[kind+'_rows'] for x in row)
        assert expected == rom[offset:offset+len(expected)]
    for key,path in [('source_sha256','source/recovered/tactical_decisions.py'),
                     ('verifier_sha256','scripts/verify_tactical_decisions.py')]:
        assert receipts['decisions'][key] == digest(ROOT/path)
    exchange = receipts['exchange']
    for entry in exchange['code_ranges']:
        offset = entry['file']; raw = bytes.fromhex(entry['raw_hex'])
        assert raw == rom[offset:offset+len(raw)] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    origin = read('analysis/phase7/secondary-origin.json')
    assert origin['rom_sha256'] == ROM_SHA256 and origin['tactic_id'] == 11
    for entry in origin['code_ranges']:
        offset = entry['file']; raw = bytes.fromhex(entry['raw_hex'])
        assert raw == rom[offset:offset+len(raw)] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    offset = origin['dispatch_table_file'] + 2*origin['tactic_id']
    assert int.from_bytes(rom[offset:offset+2],'little') == origin['dispatch_index11_target'] == 0xB42A
    for key,path in [('source_sha256','source/recovered/tactical_exchange.py'),
                     ('validator_sha256','scripts/verify_tactical_exchange.py')]:
        assert exchange[key] == digest(ROOT/path)
    cpu_counts = {'controller':controller['rom_cpu_case_count'],
                  'decisions':receipts['decisions']['rom_oracle_case_count'],'exchange':exchange['case_count']}
    guards = {'controller':controller['source_guard_case_count'],
              'decisions':receipts['decisions']['source_guard_case_count'],'exchange':exchange['source_only_guard_count']}
    integration = read('analysis/phase7/source-integration.json')
    assert integration['status'] == 'passed' and not integration['failures']
    assert integration['source_original_code_calls'] == 0
    assert integration['case_count'] == 44 and integration['actual_ROM_CPU_comparison_count'] == 43
    assert integration['native_core_field_comparison_count'] == 1
    for path,expected in integration['source_sha256'].items(): assert digest(ROOT/path) == expected,path
    core = read('analysis/phase7/runtime/natural-turn/validation.json')
    assert core['status'] == 'passed' and not core['rom_modified']
    assert not core['RAM_injections'] and not core['SRAM_injections'] and not core['readiness_or_ack_injection']
    assert core['frames'] == 700 and core['checkpoint_count'] == 13
    assert digest(ROOT/core['parent_state']) == core['parent_sha256']
    assert core['script_sha256'] == digest(ROOT/'scripts/capture_tactical_ai.py')
    assert len(core['coordinate_commits']) == len(core['action_point_charges']) == 4
    repeat_counts = {}
    for name in ('natural-turn','cpu-call'):
        receipt = read(f'analysis/phase7/runtime/{name}/repeat-validation.json')
        assert receipt['status'] == 'passed' and receipt['all_hashes_equal']
        for artifact in receipt['artifacts']:
            first, second = ROOT/receipt['first_run']/artifact['artifact'], ROOT/receipt['second_run']/artifact['artifact']
            assert artifact['equal'] and artifact['bytes'] > 0
            assert first.read_bytes() == second.read_bytes() and digest(first) == artifact['sha256']
        assert len(receipt['artifacts']) == receipt['nonempty_artifact_checks']
        repeat_counts[name] = receipt['nonempty_artifact_checks']
    assert read('analysis/phase7/runtime/natural-turn/repeat-validation.json')['full_frame_fields_equal']
    cpu = read('analysis/phase7/runtime/cpu-call/validation.json')
    assert cpu['status'] == 'passed' and cpu['instruction_count'] == 8243
    assert all(v['equal'] for v in cpu['native_field_comparisons'].values())
    trace = read('analysis/phase7/runtime/cpu-call/actual-cpu-instructions.json')
    assert len(trace) == cpu['instruction_count']
    for item in trace:
        offset, raw = item['file_offset'], bytes.fromhex(item['bytes'])
        assert raw == rom[offset:offset+len(raw)]
    assert read('analysis/phase6/verification.json')['status'] == 'passed'
    assert read('analysis/phase6/source-integration.json')['status'] == 'passed'
    rea_path = 'analysis/rea/pairs/pair-08/inspect_native_load_image.json'
    assert read(rea_path)['structuredContent']['normalized_result']['status'] == 'verified'
    files = [f'source/recovered/{name}.py' for name in ('game_engine','tactical_ai_control','tactical_decisions','tactical_exchange')]
    files += [f'scripts/{prefix}_{name}.py' for name in ('tactical_ai_control','tactical_decisions') for prefix in ('analyze','verify')]
    files += ['scripts/verify_tactical_exchange.py','scripts/verify_phase7_integration.py','scripts/verify_phase7.py','scripts/capture_tactical_ai.py']
    if (ROOT/'scripts/make_phase7_portal.py').exists(): files.append('scripts/make_phase7_portal.py')
    result = {'status':'passed','rom_sha256':ROM_SHA256,'original_and_rebuilt_identical':True,
              'rom_cpu_case_count':sum(cpu_counts.values()),'rom_cpu_counts':cpu_counts,
              'source_guard_case_count':sum(guards.values()),'source_guard_counts':guards,
              'controller_instruction_count':2213,'controller_static_byte_matches':controller['static_instruction_matches'],
              'controller_dynamic_instruction_count':controller['instruction_ir_coverage'],
              'strategy_count':8,'tactic_predicate_count':16,'controller_external_source_helpers':['F266'],
              'integration_case_count':44,'integration_rom_cpu_comparisons':43,'integration_native_fields_comparisons':1,
              'natural_core_frames':700,'natural_core_checkpoints':13,'native_coordinate_commits':4,
              'native_RAM_SRAM_injections':0,'repeat_artifact_checks':sum(repeat_counts.values()),'repeat_artifact_counts':repeat_counts,
              'synchronous_original_call_instructions':8243,'synchronous_call_field_comparisons':8,
              'secondary_cache_named_producer':'tactic11 十面埋伏',
              'secondary_origin_sha256':digest(ROOT/'analysis/phase7/secondary-origin.json'),
              'rea_retained_pair8_verified':True,'rea_load_image_sha256':digest(ROOT/rea_path),
              'source_and_validator_sha256':{p:digest(ROOT/p) for p in files},
              'receipt_sha256':{area:digest(ROOT/f'analysis/phase7/{area}/validation.json') for area in receipts},
              'integration_sha256':digest(ROOT/'analysis/phase7/source-integration.json'),
              'limits':['CPU cases include explicitly bounded prefixes/suffixes as well as complete returned routines; source guards are separate.',
                        'Full control IR recovers eight strategies; independent high-level rules cover only their documented segments.',
                        '1315 of2213 control instructions dynamically exercised; static byte parity is not branch-complete execution.',
                        'Natural core capture proves four movement proposals, AP charges and side switch; no successful tactic or phase1 core path is claimed.',
                        'Recorded8243-instruction CPU call is a separate seeded synchronous execution, not a Nestopia instruction recording or another full frame.',
                        'PPU/IRQ/audio and full game reconstruction remain incomplete.']}
    (ROOT/'analysis/phase7/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','rom_cpu_case_count','source_guard_case_count','integration_case_count','repeat_artifact_checks','controller_dynamic_instruction_count')},ensure_ascii=False))

if __name__ == '__main__':main()
