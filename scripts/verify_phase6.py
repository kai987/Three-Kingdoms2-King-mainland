#!/usr/bin/env python3
"""Pin phase6 source, lifted control bytes, bounded CPU receipts and core replays."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from inspect_game_data import OPS, SIZES
from source.recovered.game_engine import ROM_SHA256

BRANCHES = {'BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads((ROOT / path).read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    assert (ROOT / 'build/三国志2超级版.rebuilt.nes').read_bytes() == rom
    programs = {}
    for name, path in [('global', 'analysis/phase6/global/program.json'),
                       ('ending', 'analysis/phase6/factions/ending-program.json')]:
        program = read(path)
        assert program['rom_sha256'] == ROM_SHA256
        for item in program['instructions']:
            pc, offset, bank = item['pc'], item['file'], item['bank']
            base = 0xE000 if bank == 31 else 0xC000
            assert offset == 16 + bank * 8192 + pc - base
            op, mode = OPS[rom[offset]]
            size = SIZES[mode]
            lifted_op = item['op']
            assert op == ('JMP' if lifted_op in ('GLOBAL_DISPATCH', 'NMI_DISPATCH')
                          else 'JSR' if lifted_op in ('DISPATCH', 'FARCALL') else lifted_op)
            raw = rom[offset:offset + size]
            assert bytes.fromhex(item['raw_hex']) == raw
            value = int.from_bytes(raw[1:], 'little')
            if op in BRANCHES:
                value = (pc + size + (value if value < 128 else value - 256)) & 65535
            assert value == item['operand'], (name, hex(pc))
            if lifted_op in ('GLOBAL_DISPATCH', 'NMI_DISPATCH'):
                assert mode == 'ind'
                assert value == (0x4E if lifted_op == 'GLOBAL_DISPATCH' else 0)
            if lifted_op == 'DISPATCH':
                assert value == 0xEADE
                for i, target in enumerate(item['targets']):
                    assert int.from_bytes(rom[offset + 3 + 2*i:offset + 5 + 2*i], 'little') == target
            if lifted_op == 'FARCALL':
                assert value == 0xEE07
                assert int.from_bytes(rom[offset + 3:offset + 5], 'little') == item['inline_target']
        programs[name] = {'instruction_count': len(program['instructions']),
                          'sha256': digest(ROOT / path), 'original_bytes_verified': True}
    catalog = read('analysis/phase6/global/state-catalog.json')
    for domain, count, end in [('main', 15, 0xE09A), ('nmi', 9, 0xF88D)]:
        offset, cpu = catalog[domain + '_table_file'], catalog[domain + '_table_cpu']
        assert cpu + count * 2 == end
        assert bytes.fromhex(catalog[domain + '_table_raw_hex']) == rom[offset:offset + count * 2]
        targets = read('analysis/phase6/global/program.json')[domain + '_targets']
        assert len(targets) == count
        for i, target in enumerate(targets):
            assert int.from_bytes(rom[offset + i*2:offset + i*2 + 2], 'little') == target
    ending = read('analysis/phase6/factions/ending-controller.json')
    assert ending['primary_count'] == 6 and ending['legal_mode_sub_combinations'] == 17
    for table in ending['dispatches']:
        offset, count = table['file'], table['count']
        assert bytes.fromhex(table['raw_hex']) == rom[offset:offset + count * 2]
    owner = read('analysis/phase6/ownership/evidence.json')
    for entry in owner['code_ranges']:
        offset = entry['rom_offset']; raw = bytes.fromhex(entry['bytes_hex'])
        assert raw == rom[offset:offset + len(raw)]
        assert hashlib.sha256(raw).hexdigest() == entry['byte_sha256']
    for writer in owner['owner_writers']:
        offset = writer['rom_store_offset']; raw = bytes.fromhex(writer['store_bytes_hex'])
        assert raw == rom[offset:offset + len(raw)]
    adjacency = owner['data']; offset = adjacency['ROM_offset']
    assert bytes.fromhex(adjacency['bytes_hex']) == rom[offset:offset + adjacency['byte_count']]
    faction = read('analysis/phase6/factions/evidence.json')
    for entry in faction['ranges']:
        offset = entry['file']; raw = bytes.fromhex(entry['raw_hex'])
        assert raw == rom[offset:offset + len(raw)]
        assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    for table in faction['data_tables']:
        offset = table['file']
        assert bytes.fromhex(table['raw_hex']) == rom[offset:offset + table['size']]
    receipts = {area: read(f'analysis/phase6/{area}/validation.json')
                for area in ('ownership', 'factions', 'global')}
    for area, receipt in receipts.items():
        assert receipt['status'] == 'passed' and not receipt['failures'], area
        assert receipt.get('rom_sha256', receipt.get('original_rom_sha256')) == ROM_SHA256
    for area, module in [('ownership', 'city_ownership'), ('factions', 'faction_lifecycle')]:
        assert receipts[area]['source_sha256'] == digest(ROOT / f'source/recovered/{module}.py')
    for key, path in [('source_sha256', 'source/recovered/global_main_loop.py'),
                      ('validator_sha256', 'scripts/verify_global_main_loop.py'),
                      ('program_sha256', 'analysis/phase6/global/program.json')]:
        assert receipts['global'][key] == digest(ROOT / path), path
    guards = sum(receipts['global']['counts'][k] for k in
                 ('unproven_nmi_indices_rejected', 'unproven_main_indices_rejected'))
    cpu_counts = {area: receipt['case_count'] - (guards if area == 'global' else 0)
                  for area, receipt in receipts.items()}
    integration_path = 'analysis/phase6/source-integration.json'
    integration = read(integration_path)
    assert integration['status'] == 'passed' and not integration['failures']
    assert integration['source_original_code_calls'] == 0
    assert integration['actual_ROM_CPU_comparison_count'] == 53
    assert integration['actual_core_score_comparison_count'] == 1
    assert integration['source_contract_guard_count'] == 1
    for name, expected in integration['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    replay_counts = {}
    for area in ('messages', 'ownership-commit', 'unification-ending'):
        receipt = read(f'analysis/phase6/runtime/{area}/repeat-validation.json')
        assert receipt['status'] == 'passed'
        for artifact in receipt['artifacts']:
            first = ROOT / f'analysis/phase6/runtime/{area}' / artifact['path']
            repeat = ROOT / f'analysis/phase6/runtime/{area}-repeat' / artifact['path']
            assert artifact['bytes'] > 0 and artifact['repeat_identical']
            assert first.read_bytes() == repeat.read_bytes()
            assert digest(first) == artifact['sha256']
        assert len(receipt['artifacts']) == receipt['artifact_check_count']
        replay_counts[area] = receipt['artifact_check_count']
    win = read('analysis/phase6/runtime/unification-ending/validation.json')
    assert win['status'] == 'passed' and not win['rom_modified']
    assert not win['RAM_preparation'] and not win['readiness_or_ack_injection']
    assert len(win['SRAM_preparation']) == 30 and win['frames'] == 1204
    assert digest(ROOT / win['parent_state']) == win['parent_sha256']
    for i, patch in enumerate(win['SRAM_preparation']):
        assert patch['address'] == 0x6000 + i * 32
        assert patch['new'] == (patch['old'] & 0xF8) | 2
    commit = read('analysis/phase6/runtime/ownership-commit/validation.json')
    assert commit['status'] == 'passed' and not commit['rom_modified']
    assert not commit['SRAM_preparation'] and not commit['readiness_or_ack_injection']
    assert {p['address']: p['new'] for p in commit['RAM_preparation']} == {0x500: 15, 0x501: 3, 0x514: 0}
    assert digest(ROOT / commit['parent_state']) == commit['parent_sha256']
    assert [c['owner_raw'] for c in commit['checkpoints']] == [1, 2]
    messages = read('analysis/phase6/runtime/messages/evidence.json')
    for capture in messages['captures']:
        assert not capture['rom_modified'] and not capture['SRAM_preparation']
        assert digest(ROOT / capture['parent_state']) == capture['parent_sha256']
    summary, final = win['checkpoints']
    assert summary['score_u24'] == 75 and summary['owned_cities'] == 30
    assert final['ending_mode'] == 1 and final['global_main'] == 14 and final['nmi_scene'] == 8
    previous = read('analysis/phase5/verification.json')
    assert previous['status'] == 'passed' and previous['integration_case_count'] == 989
    assert read('analysis/phase4/source-integration.json')['status'] == 'passed'
    rea = {}
    candidate_count = 0
    for pair in (8, 10, 12, 14, 23, 25, 27, 29):
        path = f'analysis/rea/pairs/pair-{pair:02d}/inspect_native_load_image.json'
        assert read(path)['structuredContent']['normalized_result']['status'] == 'verified'
        rea[str(pair)] = digest(ROOT / path)
        candidate_count += len(read(f'analysis/rea/pairs/pair-{pair:02d}/procedure-index.json'))
    assert candidate_count == 880
    paths = [f'source/recovered/{name}.py' for name in
             ('game_engine', 'battle_state_machine', 'city_ownership', 'faction_lifecycle', 'global_main_loop')]
    paths += [f'scripts/{prefix}_{name}.py' for prefix in ('analyze', 'verify')
              for name in ('city_ownership', 'faction_lifecycle', 'global_main_loop')]
    paths += ['scripts/verify_phase6_integration.py', 'scripts/verify_phase6.py',
              'scripts/capture_faction_messages.py', 'scripts/capture_ownership_commit.py',
              'scripts/capture_unification_ending.py']
    paths += ['scripts/make_phase6_portal.py', 'scripts/make_portal.py']
    result = {'status': 'passed', 'rom_sha256': ROM_SHA256,
              'original_and_rebuilt_identical': True,
              'rom_cpu_comparison_count': sum(cpu_counts.values()), 'rom_cpu_counts': cpu_counts,
              'source_only_guard_count': guards + receipts['ownership']['source_only_guard_count'],
              'source_only_guard_counts': {'global': guards, 'ownership': receipts['ownership']['source_only_guard_count']},
              'programs': programs, 'main_states': 15, 'nmi_scenes': 9,
              'ending_modes': 6, 'legal_ending_mode_sub_combinations': 17,
              'discovered_owner_writer_count': len(owner['owner_writers']),
              'ownership_code_ranges': len(owner['code_ranges']), 'faction_code_ranges': len(faction['ranges']),
              'ending_terminations': receipts['factions']['ending_terminations'],
              'global_status_counts': receipts['global']['status_counts'],
              'integration_case_count': integration['case_count'],
              'integration_rom_cpu_comparisons': integration['actual_ROM_CPU_comparison_count'],
              'integration_core_score_comparisons': integration['actual_core_score_comparison_count'],
              'integration_source_guard_count': integration['counts']['source_contract_guards'],
              'integration_receipt_sha256': digest(ROOT / integration_path),
              'original_core_repeat_artifact_checks': sum(replay_counts.values()),
              'original_core_repeat_counts': replay_counts, 'unification_core_frames': 1204,
              'original_core_score': 75, 'rea_verified_pairs': rea,
              'rea_pair_candidate_procedure_count': candidate_count,
              'previous_phase5_rom_cpu_cases': previous['rom_differential_case_count'],
              'previous_phase5_integration_cases': 989,
              'source_and_validator_sha256': {path: digest(ROOT / path) for path in paths},
              'receipt_sha256': {area: digest(ROOT / f'analysis/phase6/{area}/validation.json') for area in receipts},
              'limits': ['CPU counts include bounded prefixes and declared external boundaries, not only complete returned functions.',
                         'Global source guards are separate from original CPU comparisons; core artifact checks are also separate.',
                         'Only known physical-pair source bridges are integrated; scene rendering, hardware/NMI/IRQ timing and audio remain explicit dependencies.',
                         'Original-core victory is a controlled30-owner SRAM fixture with ordinary B/A input, not a naturally played campaign.',
                         'Extinction events clear the leader byte only at the recovered commit; no full faction/city cleanup is inferred.',
                         'These are reconstructed readable rules and lifted control, not original source or a standalone playable remake.']}
    (ROOT / 'analysis/phase6/verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'rom_cpu_comparison_count', 'source_only_guard_count',
                                          'integration_case_count', 'original_core_repeat_artifact_checks', 'programs')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
