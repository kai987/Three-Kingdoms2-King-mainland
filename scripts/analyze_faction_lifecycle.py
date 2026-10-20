#!/usr/bin/env python3
"""Extract bounded faction/end-condition evidence from the read-only original ROM."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from inspect_game_data import OPS, SIZES, instruction, disassemble
from source.recovered.faction_lifecycle import ROM_SHA256

BRANCHES = {'BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS'}
MODES = {'zp': 'zpg', 'ab': 'abs', 'im': 'imm', 'a': 'acc', 'ix': 'inx', 'iy': 'iny', 'i': 'imp'}
PRIMARY = {0xD69B: (0xD69E, 6), 0xD923: (0xD926, 6), 0xD9CD: (0xD9D0, 7)}
RANGES = [
    (25, 0xA041, 0xA0A5, 'calendar_leader_skip_and_pool_threshold'),
    (25, 0xA186, 0xA19F, 'pool_warning_reset_gate'),
    (25, 0xA240, 0xA296, 'surviving_officer_pool'),
    (26, 0xC386, 0xC435, 'retirement_and_human_extinction_end'),
    (26, 0xC441, 0xC626, 'victory_score_and_acceptance'),
    (26, 0xC626, 0xC67C, 'summary_intellect_selection'),
    (26, 0xC91B, 0xC93A, 'FB_prompt'),
    (26, 0xCB7F, 0xCBC3, 'FC_FB_real_ack_timers'),
    (27, 0xA089, 0xA0B0, 'all30_city_victory_prefix'),
    (28, 0xDDBF, 0xDDDC, 'owner_low3_city_count'),
    (11, 0xCA74, 0xCA87, 'AI_no_successor_only_leaderFF_and_FB'),
    (11, 0xCA52, 0xCA68, 'after_ack_city_chiefs_and_external_domestic_continuation'),
    (24, 0xD72A, 0xD755, 'loss_reset_or_restore_parent'),
    (24, 0xD9DE, 0xDA41, 'credits_officer_buffer_with_byte_index'),
    (31, 0xE46A, 0xE4DA, 'global13_ending_setup_external'),
    (31, 0xFA53, 0xFA97, 'NMI8_original_pair23_callback'),
]


def locate(bank, cpu):
    base = 0xE000 if bank == 31 else (0xA000 if bank in (23, 25, 27) else 0xC000)
    return 16 + bank*8192 + cpu-base


def graph(rom):
    pending = [0xD693]; found = {}; occupied = {}; tables = {}; hooks = {}
    while pending:
        pc = pending.pop()
        while 0xA000 <= pc < 0xE000 and pc not in found:
            bank = 23 if pc < 0xC000 else 24; off = locate(bank, pc)
            op, mode = OPS[rom[off]]; size = SIZES[mode]
            assert op != '?', ('unknown_ending_opcode', hex(pc))
            assert all(q not in occupied for q in range(pc, pc+size)), ('overlap', hex(pc))
            for q in range(pc, pc+size): occupied[q] = pc
            operand = int.from_bytes(rom[off+1:off+size], 'little'); nxt = pc+size
            if op in BRANCHES: operand = (nxt + (operand if operand < 128 else operand-256)) & 65535
            _, asm = instruction(rom, off, pc)
            node = {'pc': pc, 'bank': bank, 'file': off, 'op': op,
                    'mode': MODES.get(mode, mode), 'operand': operand, 'next_pc': nxt,
                    'raw_hex': rom[off:off+size].hex(' ').upper(), 'assembly': asm}
            if op == 'JSR' and operand == 0xEADE:
                assert pc in PRIMARY, ('unbounded_ending_dispatch', hex(pc))
                table, count = PRIMARY[pc]; toff = locate(bank, table)
                targets = [int.from_bytes(rom[toff+2*i:toff+2*i+2], 'little') for i in range(count)]
                assert table+2*count == min(targets), ('dispatch_boundary', hex(pc))
                tables[pc] = {'call_pc': pc, 'table_cpu': table, 'bank': bank, 'file': toff,
                              'count': count, 'targets': targets,
                              'raw_hex': rom[toff:toff+2*count].hex(' ').upper(),
                              'boundary': 'Lastword is followed immediately by the first handler.'}
                node.update(op='DISPATCH', targets=targets); pending.extend(targets)
            elif op == 'JSR' and operand == 0xEE07:
                node.update(op='FARCALL', inline_target=int.from_bytes(rom[off+3:off+5], 'little'),
                            next_pc=pc+5, hook='explicit external banked dependency')
            elif op in ('JSR', 'JMP'):
                if mode == 'ind': raise ValueError(f'Unresolved indirect jump{pc:04X}')
                if 0xA000 <= operand < 0xE000: pending.append(operand)
                else: node['hook'] = f'explicit_cpu_{operand:04X}'
            elif op in BRANCHES: pending.append(operand)
            if 'hook' in node: hooks.setdefault(f'{operand:04X}', []).append(pc)
            found[pc] = node
            if op in ('JMP', 'RTS', 'RTI', 'BRK') or node['op'] == 'DISPATCH': break
            pc = node['next_pc']
    return found, tables, hooks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT/'analysis/phase6/factions')
    args = parser.parse_args(); rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    args.out.mkdir(parents=True, exist_ok=True)
    ranges = []
    for bank, start, end, name in RANGES:
        off = locate(bank, start); raw = rom[off:off+end-start]
        ranges.append({'name': name, 'bank': bank, 'cpu_start': start, 'cpu_end_exclusive': end,
                       'file': off, 'raw_hex': raw.hex(' ').upper(),
                       'sha256': hashlib.sha256(raw).hexdigest()})
        (args.out/f'{name}.asm').write_text(disassemble(rom, bank, 0xE000 if bank == 31 else
            0xA000 if bank in (23, 25, 27) else 0xC000, start, end))
    found, tables, hooks = graph(rom)
    program = {'rom_sha256': ROM_SHA256, 'pair': [23, 24], 'entry': 0xD693,
               'instructions': [found[pc] for pc in sorted(found)], 'hooks': hooks,
               'scope': 'Ending controller/control+local renderer preparatory code; external fixed/far graphics/NMI/reset hooks remain required.'}
    (args.out/'ending-program.json').write_text(json.dumps(program, ensure_ascii=False, indent=2)+'\n')
    lines = ['; OriginalROM bounded ending graph; inline pointers are data.']
    for pc in sorted(found):
        item = found[pc]; lines.append(f"{item['file']:06X} b{item['bank']} ${pc:04X}  {item['raw_hex']:<8} {item['assembly']}")
        if item['op'] == 'FARCALL': lines.append(f"; inline .word ${item['inline_target']:04X}")
        if pc in tables: lines.append('; inline words '+', '.join(f'${v:04X}' for v in tables[pc]['targets']))
    (args.out/'ending-control.asm').write_text('\n'.join(lines)+'\n')
    labels = ['mode0_loss_or_faction_extinction', 'mode1_score_lowbyte_ge70',
              'mode2_score_lowbyte40_to69', 'mode3_score_lowbyte_lt40',
              'mode4_officer_credits', 'mode5_final_text']
    mains = tables[0xD69B]['targets']
    catalog = {'rom_sha256': ROM_SHA256, 'entry': 0xD693, 'mode_field': 0x541,
               'sub_field': 0x542, 'primary_count': 6, 'legal_mode_sub_combinations': 17,
               'main_modes': [{'id': i, 'entry': pc, 'name': labels[i],
                   'substates': tables[0xD9CD if i == 4 else 0xD923]['targets'] if i in (4, 5) else None}
                   for i, pc in enumerate(mains)], 'dispatches': list(tables.values()),
               'instruction_count': len(found), 'external_calls': hooks,
               'reset_PCs': [0xD752, 0xD9C7],
               'scope': 'Fourunnested modes plus7credits and6finaltext substates. No wholeglobalE46A/PPU/NMI completion claim.'}
    (args.out/'ending-controller.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
    data_tables = []
    for bank, cpu, size, label in [(25, 0xA104, 40, 'five_turn_orders_stride8_seven_slots'),
                                   (26, 0xC3BB, 7, 'original_leader_name_substitutions_retirement'),
                                   (26, 0xC93A, 7, 'original_leader_name_substitutions_FB'),
                                   (27, 0xA025, 32, 'city_main16_table_including_victory15_bridge')]:
        off = locate(bank, cpu)
        data_tables.append({'name': label, 'bank': bank, 'cpu': cpu, 'file': off,
                            'size': size, 'raw_hex': rom[off:off+size].hex(' ').upper()})
    evidence = {'rom_sha256': ROM_SHA256, 'ranges': ranges, 'data_tables': data_tables, 'ending': catalog,
                'faction_record': {'base': 0x6F07, 'stride': 8, 'count': 7,
                  'byte0': 'leaderID,FFabsent', 'byte1': 'residence', 'byte3': 'controller',
                  'bytes4to7': 'packed diplomacy nibbles'},
                'distinct_conditions': ['leaderFF does not itself rewrite cityowner/roster/diplomacy',
                   'cityowner7 does not itself clear leader', 'FB is no-successor event; not a universal cityneutralization transaction',
                   'A240availableofficerpool<30 warns nationwideunification impossible',
                   'A0A6currentrulerownerlow3citycount==30 starts victoryscore'],
                'entry_inputs': {'owner_count_DDBF': {'ruler': 'RAM0010'},
                  'victory_prefix_A089': {'ruler': 'RAM6F03', 'normal_parent': 'citymain0/sub0'},
                  'officer_pool_A240': {'ruler': 'RAM6F03'},
                  'commit_AI_no_successor_CA74': {'pointer': 'RAM24/25 fromD319(0040)', 'ruler': 'RAM0040'},
                  'FB_prompt_C91B': {'ruler': 'RAM0040', 'old_leader': 'RAM0038'},
                  'retire_faction_C386': {'ruler': 'RAM040A'},
                  'human_extinction_C3DB': {'other_ruler_or_FF': 'RAM040C', 'existing_oldleader_names': 'RAM042C/042D'},
                  'victory_score_C441': {'ruler_record_pointer': 'RAM00EE/00EF'},
                  'best_intellect_C626': {'ruler': 'RAM6F03'},
                  'loss_exit_D72A': {'parent_condition': 'mode0 animation04CB alreadyFE', 'input': 'RAM0081bit0'}},
                'external_after_AI_ack': {'bank': 11, 'wait_cpu': 0xCA7F,
                  'next': 'CA52 C98F fixescitychiefs; then7-rulerouterloop,D249,andBEC7 remain in their own controllers'},
                'rendered_message_evidence': {'path': 'analysis/phase6/runtime/messages',
                  'D5_transcription': ['もはや このニンズウでは', 'ゼンコクトウイツは フカノウです'],
                  'C3_transcription': ['ソウソウが シボウして', 'ソウソウいちぞくは めつぼうしました'],
                  'scope': 'Originalcore controlled messagefixtures, not naturalcampaign reachability.'}}
    (args.out/'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'ranges': len(ranges), 'ending_instructions': len(found),
                      'main_modes': 6, 'mode_sub_combinations': 17, 'tables': len(tables)}))


if __name__ == '__main__': main()
