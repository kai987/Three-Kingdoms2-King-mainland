#!/usr/bin/env python3
"""Capture an explicitly selected original battle-finalizer entry in Nestopia.

Only battle main15/sub3 and outcome0 are prepared. A is ordinary controller
input; no readiness/ack byte is forced. This is a finalizer fixture, not a
naturally completed battle or proof of the whole preceding roster transaction.
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
    parser.add_argument('--out', type=Path, default=ROOT / 'analysis/phase6/runtime/ownership-commit')
    args = parser.parse_args()
    assert hashlib.sha256(args.rom.read_bytes()).hexdigest() == ROM_SHA256
    parent = ROOT / 'analysis/runtime/phase3/battle-tactics-true.state'
    runtime = Runtime(args.rom, args.out)
    checkpoints = []
    def capture(label):
        runtime.snapshot(label)
        m, s = runtime.memory(2), runtime.memory(0)
        city = m[0x50E]
        item = {'label': label, 'frame': runtime.frames, 'global_main': m[0x7A],
                'nmi_scene': m[0x78], 'battle_state': list(m[0x500:0x502]),
                'city': city, 'owner_raw': s[32*city], 'owner_low3': s[32*city]&7,
                'side_rulers': m[0x507], 'outcome': m[0x514],
                'ruler_turn': list(m[0x400:0x402]), 'button_87': m[0x87],
                'roster': list(s[32*city+17:32*city+27])}
        checkpoints.append(item)
        return item
    try:
        runtime.load_state(parent)
        runtime.run(1)
        before = capture('before')
        memory = (C.c_ubyte * 2048).from_address(runtime.core.retro_get_memory_data(2))
        prepared = {0x500: 15, 0x501: 3, 0x514: 0}
        patches = [{'address': address, 'old': memory[address], 'new': value}
                   for address, value in prepared.items()]
        for address, value in prepared.items():
            memory[address] = value
        runtime.run(2, ['a'])
        runtime.run(60)
        after = capture('after')
        expected = (before['owner_raw']&240) | (before['side_rulers']>>4)
        assert after['owner_raw'] == expected, (before, after, expected)
        assert after['global_main'] in (1, 2)
        artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in args.out.glob('*') if p.is_file() and p.stat().st_size and p.suffix in ('.png', '.bin', '.state')}
        result = {'status': 'passed', 'rom_sha256': ROM_SHA256, 'rom_modified': False,
                  'natural_gameplay': False, 'parent_state': str(parent.relative_to(ROOT)),
                  'parent_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
                  'RAM_preparation': patches, 'SRAM_preparation': [],
                  'readiness_or_ack_injection': False, 'core': runtime.info,
                  'frames': runtime.frames, 'events': runtime.events, 'checkpoints': checkpoints,
                  'artifact_sha256': artifacts, 'expected_owner_raw': expected,
                  'limits': ['Main15/sub3/outcome0 is an explicitly chosen finalizer entry, not a completed battle.',
                             'Only the final ownership/global return is tested; preceding allocation/loss/supply stages are excluded.',
                             'The A press is real controller input. No busy/render acknowledgement is forced.']}
        (args.out / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': 'passed', 'before': before, 'after': after}, ensure_ascii=False))
    finally:
        runtime.close()

if __name__ == '__main__':
    main()
