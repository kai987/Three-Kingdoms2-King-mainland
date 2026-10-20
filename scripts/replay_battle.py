#!/usr/bin/env python3
"""Run unchanged ROM inputs in Nestopia and record frame-level state changes.

This is a complete NES core replay; CPU-only differential fixtures are separate.
No ROM or RAM injection is used. The supplied plan records every controller input.
"""
import argparse
import hashlib
import json
from pathlib import Path
from nes_runtime import Runtime

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom', type=Path)
    p.add_argument('--plan', type=Path, default=ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json')
    p.add_argument('--out', type=Path, default=ROOT/'analysis/runtime/phase3/cold-replay')
    p.add_argument('--state', type=Path)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    runtime = Runtime(a.rom, a.out)
    sequence = []
    last = None
    def observe(r):
        nonlocal last
        ram = r.memory(2)
        # Values outside their active scene are retained scratch, not states.
        key = (ram[0x7a], ram[0x78], ram[0x500], ram[0x501], ram[0x540], ram[0x541], ram[0x4a8], ram[0x4a9])
        if key != last:
            sequence.append({'frame':r.frames,'global_007a':key[0], 'nmi_scene_0078':key[1],
                             'battle_0500':key[2], 'battle_sub_0501':key[3],
                             'attack_0540':key[4], 'attack_sub_0541':key[5],
                             'duel_04a8':key[6], 'duel_sub_04a9':key[7],
                             'slot_050a':ram[0x50a], 'slot_0509':ram[0x509],
                             'result_bytes_0515_0517':[ram[0x515],ram[0x517]]})
            last = key
    try:
        if a.state:runtime.load_state(a.state)
        for step in plan:
            runtime.run(step['frames'], step.get('buttons',[]), observer=observe)
            if step.get('capture'):runtime.snapshot(step['capture'])
        runtime.snapshot('final')
        receipt = {'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),
                   'plan':str(a.plan.resolve()),'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),
                   'imported_state':str(a.state.resolve()) if a.state else None,
                   'frames':runtime.frames,'engine':runtime.info,'changes':sequence,
                   'rom_writes':0,'ram_injections_in_this_replay':0,
                   'cold_boot_replay':a.state is None,
                   'limitations':['Post-frame sampling can miss transitions within a frame.',
                                  'Inactive battle/duel bytes are scratch and not active states.',
                                  'PPU replay does not validate audio or a physical console.',
                                  'An imported synthetic parent state retains its injection provenance.']}
        (a.out/'state-sequence.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'frames':runtime.frames,'state_changes':len(sequence),'final':sequence[-1]},ensure_ascii=False))
    finally:runtime.close()

if __name__=='__main__':main()
