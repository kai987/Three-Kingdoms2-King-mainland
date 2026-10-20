#!/usr/bin/env python3
"""Verify retained ROM provenance and aggregate explicitly bounded phase5 receipts."""
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

def read(name):
    return json.loads((ROOT / name).read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    assert (ROOT / 'build/三国志2超级版.rebuilt.nes').read_bytes() == rom
    programs = {}
    for label, filename in [('domestic_ai', 'program.json'), ('ruler_turn', 'turn-program.json')]:
        path = ROOT / 'analysis/phase5/domestic-ai' / filename
        program = json.loads(path.read_text())
        assert program['rom_sha256'] == ROM_SHA256
        for item in program['instructions']:
            pc, offset = item['pc'], item['file']
            base = 0xA000 if item['bank'] in (10, 25) else 0xC000
            assert offset == 16 + item['bank'] * 8192 + pc - base
            op, mode = OPS[rom[offset]]
            size = SIZES[mode]
            assert op == ('JSR' if item['op'] in ('DISPATCH', 'FARCALL') else item['op'])
            value = int.from_bytes(rom[offset + 1:offset + size], 'little')
            if op in BRANCHES:
                value = (pc + size + (value if value < 128 else value - 256)) & 65535
            assert value == item['operand'], (label, hex(pc), value, item['operand'])
            assert bytes.fromhex(item['raw_hex']) == rom[offset:offset + size]
            if item['op'] == 'DISPATCH':
                assert value == 0xEADE
                for i, target in enumerate(item['targets']):
                    assert int.from_bytes(rom[offset + 3 + 2*i:offset + 5 + 2*i], 'little') == target
            if item['op'] == 'FARCALL':
                assert value == 0xEE07
                assert int.from_bytes(rom[offset + 3:offset + 5], 'little') == item['inline_target']
        programs[label] = {'instruction_count': len(program['instructions']), 'sha256': digest(path), 'bytes_verified': True}
    domestic = read('analysis/phase5/domestic-ai/evidence.json')
    turn = read('analysis/phase5/domestic-ai/turn-controllers.json')
    for table in domestic['dispatches']:
        offset = table['file']
        assert bytes.fromhex(table['raw_hex']) == rom[offset:offset + table['count']*2]
        for i, target in enumerate(table['targets']):
            assert int.from_bytes(rom[offset + i*2:offset + i*2 + 2], 'little') == target
    assert sum(c['count'] for c in turn['controllers']) == 37
    for table in turn['controllers'] + turn['all_tables']:
        offset = table['table_file']
        assert bytes.fromhex(table['raw_hex']) == rom[offset:offset + table['count']*2]
        for i, target in enumerate(table['targets']):
            assert int.from_bytes(rom[offset + i*2:offset + i*2 + 2], 'little') == target
    transfer_evidence = read('analysis/phase5/transfer/evidence.json')
    for entry in transfer_evidence['code_ranges']:
        offset = entry['rom_offset']
        raw = bytes.fromhex(entry['bytes_hex'])
        assert raw == rom[offset:offset + len(raw)]
        assert hashlib.sha256(raw).hexdigest() == entry['byte_sha256']
    troops_evidence = read('analysis/phase5/troops/evidence.json')
    troop_instruction_count = 0
    for entry in troops_evidence['entries']:
        offset = entry['file']
        raw = rom[offset:offset + entry['cpu_end_exclusive'] - entry['cpu_start']]
        assert hashlib.sha256(raw).hexdigest() == entry['raw_sha256']
        for item in entry['instructions']:
            raw = bytes.fromhex(item['raw_hex'])
            assert raw == rom[item['file']:item['file'] + len(raw)]
            assert OPS[raw[0]][0] == item['op']
            troop_instruction_count += 1
    receipts = {a: read(f'analysis/phase5/{a}/validation.json') for a in ('transfer', 'domestic-ai', 'terrain', 'troops')}
    for area, receipt in receipts.items():
        assert receipt.get('rom_sha256', receipt.get('original_rom_sha256')) == ROM_SHA256
        assert not receipt.get('failures') and not receipt.get('turn_failures'), area
        if area != 'transfer':
            assert receipt['status'] == 'passed'
    assert receipts['transfer']['source_sha256'] == digest(ROOT / 'source/recovered/officer_transfer.py')
    terrain = receipts['terrain']
    assert terrain['formal_name_confirmed'] is False and terrain['formal_name'] is None
    counts = {'transfer': receipts['transfer']['total'], 'domestic_ai': receipts['domestic-ai']['case_count'],
              'terrain': terrain['rom_oracle_case_count'], 'troops': receipts['troops']['case_count']}
    assert sum(counts.values()) == 83702
    assert receipts['domestic-ai']['turn_controller_terminations'] == {'returned': 209, 'validated_to_explicit_boundary': 13}
    core = read('analysis/phase5/troops/core-fixture/validation.json')
    replay = read('analysis/phase5/troops/core-fixture/replay-validation.json')
    assert core['status'] == replay['status'] == 'passed'
    assert not core['rom_modified'] and not core['ram_patches']
    assert len(core['sram_patches']) == 4
    for name, expected in core['artifact_sha256'].items():
        assert digest(ROOT / 'analysis/phase5/troops/core-fixture' / name) == expected
    checkpoint = next(c for c in core['checkpoints'] if c['label'] == 'committed-overflow')
    assert checkpoint['raw_troops'] == 1098 and checkpoint['low10'] == 74 and checkpoint['upper6'] == 1
    integration = read('analysis/phase5/source-integration.json')
    assert integration['status'] == 'passed'
    assert not integration['failures'] and integration['case_count'] == 989
    assert integration['actual_ROM_comparison_count'] == 982
    for name, expected in integration['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    old_integration = read('analysis/phase4/source-integration.json')
    assert old_integration['status'] == 'passed' and old_integration['case_count'] == 8
    rea = {}
    for pair in (10, 27):
        path = ROOT / f'analysis/rea/pairs/pair-{pair:02d}/inspect_native_load_image.json'
        receipt = json.loads(path.read_text())
        assert receipt['structuredContent']['normalized_result']['status'] == 'verified'
        rea[str(pair)] = {'load_image': 'verified', 'sha256': digest(path)}
    names = ['game_engine', 'officer_transfer', 'domestic_ai', 'troop_fields', 'terrain_semantics', 'officers', 'game_enums']
    files = [f'source/recovered/{n}.py' for n in names]
    files += [f'scripts/{prefix}_{n}.py' for n in ('officer_transfer', 'domestic_ai', 'troop_fields', 'terrain_semantics') for prefix in ('analyze', 'verify')]
    files += ['scripts/verify_phase5_integration.py', 'scripts/capture_troop_overflow.py']
    result = {'status': 'passed', 'rom_sha256': ROM_SHA256, 'original_and_rebuilt_identical': True,
              'rom_differential_case_count': sum(counts.values()), 'rom_differential_counts': counts,
              'terrain_artifact_checks': terrain['artifact_case_count'],
              'turn_cases_stopped_at_explicit_boundary': 13,
              'integration_case_count': integration.get('case_count'), 'phase4_integration_cases': 8,
              'integration_rom_comparisons': integration['actual_ROM_comparison_count'],
              'integration_source_contract_checks': integration['source_contract_check_count'],
              'integration_receipt_sha256': digest(ROOT / 'analysis/phase5/source-integration.json'),
              'programs': programs, 'troop_prefix_instruction_count': troop_instruction_count,
              'transfer_code_range_count': len(transfer_evidence['code_ranges']), 'transfer_services': 16,
              'turn_primary_subentries': 37, 'turn_unique_entry_count': len({t for c in turn['controllers'] for t in c['targets']}), 'rea_new_pairs': rea,
              'troop_overflow_core_frames': core['frames'], 'core_replay_status': replay['status'],
              'troop_numeric_overflow_confirmed': True, 'terrain1_formal_name_confirmed': False,
              'source_and_validator_sha256': {n: digest(ROOT / n) for n in files},
              'receipt_sha256': {a: digest(ROOT / f'analysis/phase5/{a}/validation.json') for a in receipts},
              'limits': ['83702 counts bounded ROM comparisons; 13 turn cases stop at declared reset (1), PPU (6) and NMI (6) boundaries.',
                         '892 terrain artifact checks are separate from CPU differential cases.',
                         'Control IR validators explicitly use original-ROM adapters for unresolved external helpers; high-level APIs do not.',
                         '1098 is an unmodified-core result after two explicit SRAM word preparations, not proof of natural campaign reachability.',
                         'Direct flag1 AI entry requires valid postbattle city/roster scratch. Logical SRAM does not model upper-region write protection for invalid pointers.',
                         'Upper6 may contain numeric overflow; independent flag semantics remain unproved. Terrain1 formal name remains unknown.',
                         'This is reconstructed logic/control source, not original development source or a complete independently playable NES game.']}
    (ROOT / 'analysis/phase5/verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'rom_differential_case_count', 'terrain_artifact_checks', 'integration_case_count', 'programs')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
