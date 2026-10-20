#!/usr/bin/env python3
"""Render original faction/termination dialogue IDs in explicit core RAM fixtures.

This proves the original text/pixels, not natural game-event reachability or a
completed faction cleanup. The ROM stays unchanged; every RAM preparation is
recorded against an imported original-core menu snapshot.
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

# Manually read from the retained original-core pixels for this exact fixture.
# D8/D9 parent-menu residue and waiting pages are deliberately not transcribed.
TRANSCRIPTIONS = {
    'D5': {'clear_new_lines': ['もはや このニンズウでは', 'ゼンコクトウイツは フカノウです'],
           'reading_status': 'manual from original native pixels; only clear newly rendered lines, not parent menu residue'},
    'C3': {'clear_new_lines': ['ソウソウが シボウして', 'ソウソウいちぞくは めつぼうしました'],
           'reading_status': 'manual native-pixel transcription; explicit Cao Cao display fixture, not actual death'},
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'analysis/phase6/runtime/messages')
    args = parser.parse_args()
    assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == ROM_SHA256
    parent = ROOT / 'analysis/phase5/runtime/city-info/menu-2.state'
    captures = []
    for message in (0xD5, 0xC3, 0xD8, 0xD9):
        runtime = Runtime(args.rom, args.out)
        try:
            runtime.load_state(parent)
            memory = (C.c_ubyte * 2048).from_address(runtime.core.retro_get_memory_data(2))
            sram = runtime.memory(0)
            current_ruler = sram[0xF03]
            assert 0 <= current_ruler < 7
            leader = sram[0xF07 + current_ruler*8]
            initial_leader = runtime.blob[16 + 26*8192 + 0xC3BB - 0xC000 + current_ruler]
            other_ruler = (current_ruler + 1) % 7
            defeating_leader = 255 if message == 0xD9 else sram[0xF07 + other_ruler*8]
            year = sram[0xF00] + 100
            month = sram[0xF01] + 1
            # Parameters are explicit display inputs, not outcomes of death.
            preparation = {0x310: 1, 0x311: message, 0x312: 255, 0x313: 255,
                           0x300: 0, 0x304: 255, 0x308: 0, 0x303: 0, 0x7E: 0,
                           0x42C: leader, 0x42D: initial_leader, 0x42E: defeating_leader,
                           0x42F: year & 255, 0x430: year >> 8, 0x431: 0,
                           0x432: month, 0x433: 0, 0x434: 0}
            changes = [{'address': address, 'old': memory[address], 'new': value}
                       for address, value in preparation.items()]
            for address, value in preparation.items():
                memory[address] = value
            runtime.run(240)
            label = f'message-{message:02X}'
            runtime.snapshot(label)
            runtime.frame.resize((768, 720), resample=0).save(args.out / (label + '-zoom.png'))
            frame = runtime.memory(2)
            entry = {'message_id': message, 'message_hex': f'{message:02X}',
                     'parent_state': str(parent.relative_to(ROOT)),
                     'parent_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
                     'RAM_preparation': changes, 'SRAM_preparation': [],
                     'rom_modified': False, 'natural_gameplay': False,
                     'display_ruler': current_ruler, 'display_leader': leader,
                     'initial_leader': initial_leader, 'defeating_leader': defeating_leader,
                     'source_parameter_layout': 'pair25/26 C386,C3DB; dates+100/+1; initial C3BB ruler table',
                     'frames': runtime.frames, 'core': runtime.info,
                     'jobs': list(frame[0x300:0x30A]), 'image': label + '.png',
                     'zoom': label + '-zoom.png', 'state': label + '.state',
                     'artifact_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in args.out.glob(label + '*') if p.stat().st_size},
                     'scope': 'Original message rendering after explicit queue/parameter setup; no political event reachability claim.'}
            (args.out / (label + '-fixture.json')).write_text(json.dumps(entry, ensure_ascii=False, indent=2) + '\n')
            captures.append(entry)
        finally:
            runtime.close()
    result = {'rom_sha256': ROM_SHA256, 'captures': captures,
              'text_transcriptions': TRANSCRIPTIONS,
              'limits': ['Messages are explicitly queued RAM fixtures, not natural campaign events.',
                         'Numeric/identity display arguments are controlled; they do not prove an actual ruler death.',
                         'libretro memory3 is unavailable; original rendered pixels and serialized core state are retained.']}
    (args.out / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'captures': len(captures), 'jobs': {c['message_hex']: c['jobs'] for c in captures}}, ensure_ascii=False))

if __name__ == '__main__':
    main()
