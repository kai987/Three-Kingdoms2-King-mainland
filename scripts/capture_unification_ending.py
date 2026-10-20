#!/usr/bin/env python3
"""Replay the ROM's thirty-city victory -> global13 -> NMI8 ending route.

Only the thirty city-owner bytes are prepared in SRAM. The original B and A
buttons leave the city command and accept the victory summary; RAM, ROM,
rendering readiness and acknowledgement flags are never patched. This is a
controlled ownership scenario, not natural campaign reachability evidence.
"""
import argparse
import ctypes as C
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from nes_runtime import Runtime
from source.recovered.officers import ROM_SHA256

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'analysis/phase6/runtime/unification-ending')
    args = parser.parse_args()
    assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == ROM_SHA256
    parent = ROOT / 'analysis/runtime/city-commands.state'
    runtime = Runtime(args.rom, args.out)
    transitions, checkpoints = [], []
    def observe(rt):
        m, s = rt.memory(2), rt.memory(0)
        state = [m[k] for k in (0x7A, 0x78, 0x400, 0x401, 0x541, 0x542)]
        if not transitions or transitions[-1]['state'] != state:
            transitions.append({'frame': rt.frames, 'state': state,
                                'ruler': s[0xF03], 'event_6f8b': s[0xF8B]})
    def capture(label):
        runtime.snapshot(label)
        runtime.frame.resize((768, 720), resample=0).save(args.out / (label + '-zoom.png'))
        m, s = runtime.memory(2), runtime.memory(0)
        row = {'label': label, 'frame': runtime.frames,
               'global_main': m[0x7A], 'nmi_scene': m[0x78],
               'ruler_turn': list(m[0x400:0x402]), 'ending_mode': m[0x541],
               'ruler': s[0xF03], 'owned_cities': sum((s[32*i]&7)==s[0xF03] for i in range(30)),
               'score_u24': int.from_bytes(m[0x435:0x438], 'little'),
               'summary_parameters_042c_0450': list(m[0x42C:0x450]),
               'image': label + '.png', 'zoom': label + '-zoom.png'}
        checkpoints.append(row)
        return row
    try:
        runtime.load_state(parent)
        sram = (C.c_ubyte*8192).from_address(runtime.core.retro_get_memory_data(0))
        ruler = sram[0xF03]
        assert 0 <= ruler < 7
        patches = [{'address': 0x6000 + city*32, 'old': sram[city*32],
                    'new': (sram[city*32]&248)|ruler} for city in range(30)]
        for item in patches:
            sram[item['address']-0x6000] = item['new']
        runtime.run(2, ['b'], observe)
        runtime.run(600, observer=observe)
        summary = capture('victory-summary')
        assert summary['owned_cities'] == 30 and summary['ruler_turn'] == [15, 2]
        runtime.run(2, ['a'], observe)
        runtime.run(600, observer=observe)
        ending = capture('ending')
        assert ending['global_main'] == 14 and ending['nmi_scene'] == 8
        assert ending['ending_mode'] in (1, 2, 3)
        assert any(t['state'][0] == 13 for t in transitions)
        artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in args.out.iterdir() if p.is_file() and p.stat().st_size and p.suffix in ('.png', '.bin', '.state')}
        result = {'status': 'passed', 'rom_sha256': ROM_SHA256, 'rom_modified': False,
                  'natural_gameplay': False, 'parent_state': str(parent.relative_to(ROOT)),
                  'parent_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
                  'SRAM_preparation': patches, 'RAM_preparation': [],
                  'readiness_or_ack_injection': False, 'core': runtime.info,
                  'frames': runtime.frames, 'events': runtime.events,
                  'transitions': transitions, 'checkpoints': checkpoints,
                  'artifact_sha256': artifacts,
                  'clear_new_text': {'summary': ['ソウソウさま ゼンコクトウイツ', 'おめでとうございます'],
                                     'reading_status': 'Manual native-pixel transcription from original controlled Cao Cao fixture.'},
                  'limits': ['All30 ownership is explicitly prepared; preceding conquests and faction retirements are not simulated.',
                             'This captures an ending scene, not its complete animation/credits or physical console validation.',
                             'Only ordinary B/A input advances the route after preparation; no RAM readiness bit is set.']}
        (args.out / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': 'passed', 'frames': runtime.frames, 'summary': summary,
                          'ending': ending, 'transitions': transitions}, ensure_ascii=False))
    finally:
        runtime.close()

if __name__ == '__main__':
    main()
