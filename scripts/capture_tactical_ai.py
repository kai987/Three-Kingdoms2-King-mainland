#!/usr/bin/env python3
"""Replay one unpatched battle-side AI turn, or separately trace its CPU call.

The complete-core mode uses ordinary controller input from a saved original
battle menu. CPU mode is a synchronous, explicitly seeded call to bank8 A000;
it is not a native-core instruction trace or a second video/NMI experiment.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
PARENT = ROOT / 'analysis/runtime/phase3/attack-intro-7.state'
PLAN = [
    {'frames': 12, 'buttons': ['down']},
    {'frames': 35, 'buttons': []},
    {'frames': 12, 'buttons': ['right']},
    {'frames': 35, 'buttons': []},
    {'frames': 2, 'buttons': ['a']},
    {'frames': 300, 'buttons': []},
    {'frames': 2, 'buttons': ['a']},
    {'frames': 302, 'buttons': []},
]
CAPTURES = {
    94: 'menu-selected', 396: 'wait-confirmation',
    431: 'ai-request', 432: 'ai-proposal', 485: 'first-coordinate-commit',
    486: 'first-ap-charge', 489: 'first-action-return',
    491: 'next-request', 540: 'fourth-coordinate-commit',
    551: 'scan-exhausted', 563: 'next-side',
    665: 'player-turn-message', 700: 'final',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def fields(ram, sram, frame):
    units = []
    for slot in range(20):
        ident = ram[0x664 + slot]
        if ident == 255:
            continue
        record = sram[0x3C0 + 12 * ident:0x3C0 + 12 * ident + 12]
        units.append({'slot': slot, 'officer_id': ident,
                      'x': ram[0x600 + slot], 'y': ram[0x614 + slot],
                      'side_condition_raw': ram[0x628 + slot],
                      'hundred_troops_cache': ram[0x63C + slot],
                      'condition_raw': ram[0x650 + slot],
                      'strategy_raw': sram[0xFA1 + slot],
                      'officer_record_hex': record.hex(' ').upper()})
    return {
        'frame': frame, 'global_main_007A': ram[0x7A], 'nmi_scene_0078': ram[0x78],
        'battle_state_0500_0501': list(ram[0x500:0x502]),
        'side_0504': ram[0x504], 'active_action_points_0505': ram[0x505],
        'round_0506': ram[0x506], 'side_rulers_0507': ram[0x507],
        'target_0509': ram[0x509], 'battle_actor_or_scratch_050A': ram[0x50A],
        'reserves_050C_050D': list(ram[0x50C:0x50E]),
        'side_controller_050F': ram[0x50F],
        'ai_phase_6F8B': sram[0xF8B], 'ai_actor_6F8C': sram[0xF8C],
        'proposal_action_or_direction_6F8D': sram[0xF8D],
        'proposal_target_6F8E': sram[0xF8E], 'proposal_status_6F8F': sram[0xF8F],
        'rng_cursor_6F92': sram[0xF92], 'scan_cursor_6F94': sram[0xF94],
        'status3_count_6F95': sram[0xF95], 'eligible_attempts_6F96': sram[0xF96],
        'menu_cursor_0012': ram[0x12],
        'text_jobs_0300_0304': [ram[0x300], ram[0x304]], 'units': units,
    }


def state_chunks(blob, start, end):
    result = {}
    while start + 8 <= end:
        tag, size = blob[start:start+4], int.from_bytes(blob[start+4:start+8], 'little')
        if start + 8 + size > end:
            raise ValueError('Malformed native save-state chunk')
        result[tag] = blob[start+8:start+8+size]
        start += 8 + size
    return result


def saved_cpu_and_banks(path):
    blob = Path(path).read_bytes()
    assert blob[:4] == b'NST\x1a'
    top = state_chunks(blob, 8, 8 + int.from_bytes(blob[4:8], 'little'))
    cpu = state_chunks(top[b'CPU\0'], 0, len(top[b'CPU\0']))
    img = state_chunks(top[b'IMG\0'], 0, len(top[b'IMG\0']))
    mapper = state_chunks(img[b'MPR\0'], 0, len(img[b'MPR\0']))
    prg = state_chunks(mapper[b'PRG\0'], 0, len(mapper[b'PRG\0']))
    raw = prg[b'BNK\0']
    assert len(raw) == 12 and all(raw[3*i] == 0 for i in range(4))
    return cpu[b'REG\0'], [int.from_bytes(raw[3*i+1:3*i+3], 'little') for i in range(4)]


def core_capture(args):
    from nes_runtime import Runtime
    runtime = Runtime(args.rom, args.out)
    frame_log, checkpoints = [], []
    def observe(rt):
        item = fields(rt.memory(2), rt.memory(0), rt.frames)
        frame_log.append(item)
        if rt.frames in CAPTURES:
            label = CAPTURES[rt.frames]
            rt.snapshot(label)
            _, banks = saved_cpu_and_banks(args.out / (label + '.state'))
            checkpoints.append(dict(item, label=label, physical_prg_banks=banks))
    try:
        runtime.load_state(PARENT)
        initial = fields(runtime.memory(2), runtime.memory(0), 0)
        for step in PLAN:
            runtime.run(step['frames'], step['buttons'], observer=observe)
        assert runtime.frames == 700
        assert len(checkpoints) == len(CAPTURES)
        by_frame = {item['frame']: item for item in frame_log}
        request, proposal = by_frame[431], by_frame[432]
        assert request['ai_phase_6F8B'] == 0
        assert (proposal['ai_phase_6F8B'], proposal['ai_actor_6F8C'],
                proposal['proposal_action_or_direction_6F8D'], proposal['proposal_status_6F8F']) == (255, 1, 3, 0)
        movements = []
        for before, after in zip([initial]+frame_log, frame_log):
            prior = {unit['slot']: unit for unit in before['units']}
            for unit in after['units']:
                old = prior.get(unit['slot'])
                if old and (old['x'], old['y']) != (unit['x'], unit['y']):
                    movements.append({'frame': after['frame'], 'slot': unit['slot'],
                                      'from': [old['x'], old['y']], 'to': [unit['x'], unit['y']]})
        assert movements == [
            {'frame': 485, 'slot': 1, 'from': [17, 17], 'to': [18, 17]},
            {'frame': 507, 'slot': 1, 'from': [18, 17], 'to': [18, 16]},
            {'frame': 519, 'slot': 1, 'from': [18, 16], 'to': [19, 16]},
            {'frame': 540, 'slot': 1, 'from': [19, 16], 'to': [20, 16]},
        ], movements
        charges = [{'frame': after['frame'], 'before': before['active_action_points_0505'],
                    'after': after['active_action_points_0505']}
                   for before, after in zip(frame_log, frame_log[1:])
                   if before['side_0504'] == after['side_0504'] == 0 and
                   before['active_action_points_0505'] != after['active_action_points_0505']]
        assert charges == [{'frame': 486, 'before': 24, 'after': 21},
                           {'frame': 508, 'before': 21, 'after': 18},
                           {'frame': 520, 'before': 18, 'after': 15},
                           {'frame': 541, 'before': 15, 'after': 10}], charges
        assert by_frame[563]['side_0504'] == 128 and by_frame[563]['round_0506'] == 2
        assert all(item['global_main_007A'] == 4 and item['nmi_scene_0078'] == 3 for item in frame_log)
        write_json(args.out / 'input-plan.json', PLAN)
        write_json(args.out / 'frame-fields.json', frame_log)
        write_json(args.out / 'checkpoints.json', checkpoints)
        payloads = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                    for p in sorted(args.out.iterdir()) if p.is_file() and p.stat().st_size and
                    p.suffix in ('.png', '.bin', '.state')}
        assert len(payloads) == 13*4 and all(v['bytes'] > 0 for v in payloads.values())
        result = {'status': 'passed', 'rom_sha256': ROM_SHA256, 'rom_modified': False,
                  'natural_inputs_after_saved_original_snapshot': True,
                  'parent_state': str(PARENT.relative_to(ROOT)), 'parent_sha256': digest(PARENT),
                  'parent_menu_image': 'analysis/runtime/phase3/attack-intro-7.png',
                  'RAM_injections': [], 'SRAM_injections': [],
                  'readiness_or_ack_injection': False, 'core': runtime.info,
                  'script_sha256': digest(__file__), 'frames': runtime.frames,
                  'frame_samples': len(frame_log), 'checkpoint_count': len(checkpoints),
                  'input_plan': PLAN, 'initial': initial, 'checkpoints': checkpoints,
                  'coordinate_commits': movements, 'action_point_charges': charges,
                  'native_instruction_trace': False, 'artifact_sha256': payloads,
                  'empty_vram_exports_excluded': sorted(p.name for p in args.out.glob('*-vram.bin') if not p.stat().st_size),
                  'limits': [
                      'The imported parent is a saved original battle menu; this script does not replay reset-to-battle.',
                      'No RAM/SRAM/ROM or acknowledgement is patched; only ordinary controller input follows the parent.',
                      'Frame-end fields show requests/proposals/effects, not every CPU instruction or asynchronous intermediate write.',
                      'This actor produces movement-status0 proposals; no successful status2 tactic or phase1 secondary path is claimed.',
                      'The returning side still has an original message awaiting input; no completed natural battle is claimed.',
                      'Pixels do not independently identify AI phase, strategy, proposal target, RNG cursor, or AP arithmetic.',
                  ]}
        write_json(args.out / 'validation.json', result)
        if args.compare:
            previous = json.loads((args.compare / 'validation.json').read_text())
            pairs = []
            for name, current in payloads.items():
                expected = previous['artifact_sha256'][name]
                pairs.append({'artifact': name, 'bytes': current['bytes'],
                              'sha256': current['sha256'], 'equal': current == expected})
            assert all(item['equal'] for item in pairs)
            assert digest(args.out/'frame-fields.json') == digest(args.compare/'frame-fields.json')
            repeat = {'status': 'passed', 'nonempty_artifact_checks': len(pairs),
                      'all_hashes_equal': True, 'full_frame_fields_equal': True,
                      'first_run': str(args.compare.relative_to(ROOT)),
                      'second_run': str(args.out.relative_to(ROOT)), 'artifacts': pairs}
            write_json(args.compare / 'repeat-validation.json', repeat)
        print(json.dumps({'status': 'passed', 'frames': runtime.frames,
                          'checkpoints': len(checkpoints), 'movements': movements,
                          'action_point_charges': charges, 'payloads': len(payloads)}))
    finally:
        runtime.close()


def cpu_capture(args):
    from py65.devices.mpu6502 import MPU
    from py65.disassembler import Disassembler
    from trace_startup import Bus
    parent = args.parent_capture or ROOT/'analysis/phase7/runtime/natural-turn'
    args.out.mkdir(parents=True, exist_ok=True)
    state_path = parent / 'ai-request.state'
    regs, banks = saved_cpu_and_banks(state_path)
    assert len(regs) == 7 and banks[1:] == [8, 9, 31]
    bus = Bus(args.rom.read_bytes(), 'zero')
    bus.ram[:] = (parent/'ai-request-ram.bin').read_bytes()
    bus.sram[:] = (parent/'ai-request-sram.bin').read_bytes()
    bus.banks = banks.copy(); bus.bank_initialized = [True]*4; bus.protect = 0x4C
    # Native REG payload: PC(lo,hi), SP, A, X, Y, P. The synchronous call
    # explicitly starts A000 with the captured register values and a real
    # E22C caller address; it does not claim to resume the saved native PC.
    cpu = MPU(memory=bus); cpu.pc=0xA000
    cpu.sp,cpu.a,cpu.x,cpu.y,cpu.p=regs[2:7]
    cpu.stPush(0xE2);cpu.stPush(0x2B)
    entry_regs = {name:getattr(cpu,name) for name in ('pc','sp','a','x','y','p')}
    bus.cpu=cpu; dis=Disassembler(cpu); rows=[]; counts=Counter(); writes_before=bytes(bus.sram)
    decision_entries=[]
    for step in range(500000):
        if cpu.pc == 0xE22C:
            break
        bus.step_no=step;bus.pc=cpu.pc
        if cpu.pc in (0xA099,0xA95C,0xAAF8,0xB933):
            actor=bus.sram[0xF8C]
            decision_entries.append({'step':step,'pc':cpu.pc,'file_offset':16+8*8192+(cpu.pc&8191),
                                     'actor':actor,'strategy_raw':bus.sram[0xFA1+actor] if actor<20 else None,
                                     'phase':bus.sram[0xF8B],'proposal_status':bus.sram[0xF8F]})
        physical, offset=bus.origin(cpu.pc)
        size,assembly=dis.instruction_at(cpu.pc)
        raw=bytes(bus.peek(cpu.pc+i)for i in range(size))
        rows.append({'step':step,'bank':physical,'pc':cpu.pc,
                     'file_offset':16+offset,'bytes':raw.hex(' ').upper(),
                     'assembly':assembly,'a':cpu.a,'x':cpu.x,'y':cpu.y,'p':cpu.p,'sp':cpu.sp})
        counts[(physical,cpu.pc)]+=1
        cpu.step()
    else:
        raise AssertionError(f'AI call did not return: {cpu.pc:04X}')
    after=fields(bus.ram,bus.sram,0)
    native=json.loads((parent/'checkpoints.json').read_text())
    native=next(item for item in native if item['label']=='ai-proposal')
    keys=['ai_phase_6F8B','ai_actor_6F8C','proposal_action_or_direction_6F8D',
          'proposal_target_6F8E','proposal_status_6F8F','scan_cursor_6F94',
          'status3_count_6F95','eligible_attempts_6F96']
    comparisons={key:{'actual_cpu':after[key],'native_next_frame':native[key],
                      'equal':after[key]==native[key]}for key in keys}
    assert all(value['equal']for value in comparisons.values()),comparisons
    write_json(args.out/'actual-cpu-instructions.json',rows)
    (args.out/'after-ram.bin').write_bytes(bytes(bus.ram))
    (args.out/'after-sram.bin').write_bytes(bytes(bus.sram))
    result={'status':'passed','case_count':1,'instruction_count':len(rows),'script_sha256':digest(__file__),
            'unique_instruction_starts':len(counts),'rom_sha256':ROM_SHA256,
            'source_kind':'separate synchronous actual-ROM CPU call using native-captured RAM/SRAM',
            'native_instruction_trace':False,'source_reconstruction_executed':False,
            'captured_state_sha256':digest(state_path),'captured_reg_payload_hex':regs.hex(' ').upper(),
            'captured_native_pc':int.from_bytes(regs[:2],'little'),'entry_registers':entry_regs,
            'seeded_call':{'entry':0xA000,'return_pc':0xE22C,'physical_banks':banks,
                           'stack_preparation':'Push E22B high then low at captured SP; no readiness/ack preparation.',
                           'sram_access_contract':'N163 protect=4C; captured first 4KiB SRAM writable.'},
            'return_registers':{name:getattr(cpu,name)for name in ('pc','sp','a','x','y','p')},
            'native_field_comparisons':comparisons,'mapper_events':bus.mapper_events,
            'decision_entry_events':decision_entries,
            'io_event_count':len(bus.io_events),'blocked_sram_writes':bus.blocked_sram_writes,
            'changed_sram_addresses':[0x6000+i for i,(a,b)in enumerate(zip(writes_before,bus.sram))if a!=b],
            'limits':['One seeded CPU call is not an exact instruction recording of Nestopia.',
                      'Only declared proposal/scan fields are compared with the next complete-core frame.',
                      'No NMI/video/APU/IRQ is generated during this synchronous CPU call.']}
    assert result['io_event_count']==0 and result['blocked_sram_writes']==0
    write_json(args.out/'validation.json',result)
    if args.compare:
        names=['actual-cpu-instructions.json','after-ram.bin','after-sram.bin']
        checks=[{'artifact':name,'bytes':(args.out/name).stat().st_size,
                 'sha256':digest(args.out/name),
                 'equal':digest(args.out/name)==digest(args.compare/name)}for name in names]
        assert all(item['equal']and item['bytes']for item in checks)
        write_json(args.compare/'repeat-validation.json',
                   {'status':'passed','nonempty_artifact_checks':len(checks),
                    'all_hashes_equal':True,'artifacts':checks,
                    'first_run':str(args.compare.relative_to(ROOT)),
                    'second_run':str(args.out.relative_to(ROOT)),
                    'case_count_domain':1,'repeat_run_not_an_additional_CPU_case':True})
    print(json.dumps({'status':'passed','cpu_cases':1,'instructions':len(rows),'comparisons':comparisons}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom',type=Path)
    parser.add_argument('--mode',choices=('core','cpu'),default='core')
    parser.add_argument('--out',type=Path,default=ROOT/'analysis/phase7/runtime/natural-turn')
    parser.add_argument('--compare',type=Path)
    parser.add_argument('--parent-capture',type=Path)
    args=parser.parse_args()
    args.out=args.out.resolve()
    if args.compare:args.compare=args.compare.resolve()
    if args.parent_capture:args.parent_capture=args.parent_capture.resolve()
    assert digest(args.rom)==ROM_SHA256
    if args.mode=='core':core_capture(args)
    else:cpu_capture(args)


if __name__=='__main__':
    main()
