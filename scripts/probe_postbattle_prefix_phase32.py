#!/usr/bin/env python3
"""Root-only original-core ordinary-input prefix; never a fresh-repeat claim."""
from pathlib import Path
import argparse, hashlib, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from nes_service_runtime import ServiceRuntime
from capture_native_postbattle_early import serialized, ROM_SHA, CORE_SHA
from source.recovered.nestopia_context import NestopiaContext

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom', type=Path)
    p.add_argument('--mother', type=Path, required=True)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--end', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--root-execution-authorized', action='store_true')
    a = p.parse_args()
    assert a.root_execution_authorized and sha(a.rom) == ROM_SHA
    assert a.end > 0 and not a.out.exists()
    a.out.mkdir(parents=True)
    plan = []
    for i, step in enumerate(json.loads(a.plan.read_text())):
        lo, hi = max(0, step['start_frame']), min(a.end, step['start_frame'] + step['frames'])
        if hi > lo:
            plan.append(dict(start_frame=lo, frames=hi-lo, buttons=step['buttons'], parent_step=i))
    assert sum(x['frames'] for x in plan) == a.end
    cursor = 0
    for step in plan:
        assert step['start_frame'] == cursor
        assert set(step['buttons']) <= {'a','b','start','select','up','down','left','right'}
        cursor += step['frames']
    rt = ServiceRuntime(a.rom, a.out)
    rows, changes, previous = [], [], None
    try:
        assert rt.info['core_sha256'] == CORE_SHA
        rt.load_state(a.mother)
        mother = a.mother.read_bytes()
        initial = NestopiaContext.parse(mother)
        assert (rt.memory(2), rt.memory(0)) == (initial.ram, initial.sram)
        (a.out/'initial.state').write_bytes(mother)
        (a.out/'initial-ram.bin').write_bytes(initial.ram)
        (a.out/'initial-sram.bin').write_bytes(initial.sram)
        def observe(r):
            nonlocal previous
            ram, sram, state = r.memory(2), r.memory(0), serialized(r)
            ctx, pcm = NestopiaContext.parse(state), r.pcm_frame()
            signature = [ram[0x7A],ram[0x78],ram[0x500],ram[0x501],ram[0x506]]
            rows.append(dict(frame=r.frames, signature=signature,
                outcome_0514=ram[0x514], mode_6F91=sram[0xF91],
                registers=ctx.registers, PRG=list(ctx.prg_banks),
                units=[dict(slot=i, ID=ram[0x664+i], side=ram[0x628+i]) for i in (0,10)],
                **{k+'_sha256':hashlib.sha256(v).hexdigest() for k,v in
                   [('RAM',ram),('SRAM',sram),('RGB',r.frame.tobytes()),('PCM',pcm),('state',state)]}))
            if signature != previous:
                label='change-%05d-'%r.frames+'-'.join(map(str,signature))
                r.snapshot(label)
                changes.append(dict(frame=r.frames, signature=signature, state=label+'.state'))
                previous = signature
        for step in plan: rt.run(step['frames'], step['buttons'], observe)
        rt.snapshot('final')
        wav = rt.save_wav(a.out/'full-audio.wav')
        save(a.out/'input-plan.json',plan)
        save(a.out/'frame-buffer-hashes.json',rows)
        save(a.out/'transitions.json',changes)
        save(a.out/'prefix.json',dict(schema='phase32-original-single-run-input-prefix-v1',
            status='observed_single_run_ancestry_not_formal_repeat', ROM_sha256=ROM_SHA,
            original_core_sha256=CORE_SHA, frames=rt.frames,
            mother=dict(path=str(a.mother),sha256=sha(a.mother)),
            parent_input_plan=dict(path=str(a.plan),sha256=sha(a.plan)),
            producer=dict(path=str(Path(__file__).relative_to(ROOT)),sha256=sha(__file__)),
            additional_core_memory_writes=0, preparation=[], Source_CPU_cases=0,
            state_imports=1, cold_boot=False, fresh_repeat_proven=False,
            internal_CPU_trace=False, final_state_sha256=sha(a.out/'final.state'), full_audio=wav))
        print(json.dumps(dict(status='single_run_observed',frames=rt.frames,final=rows[-1]),ensure_ascii=False))
    finally: rt.close()

if __name__ == '__main__': main()
