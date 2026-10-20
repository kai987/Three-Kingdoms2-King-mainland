#!/usr/bin/env python3
"""Replay the phase9 legal fixtures unchanged, observing full video/PCM services."""
import argparse
import hashlib
import json
from pathlib import Path
from nes_service_runtime import ServiceRuntime
ROOT=Path(__file__).resolve().parents[1]
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def capture(rom,out,case):
    prior=ROOT/'analysis/phase9/runtime'/case
    validation=json.loads((prior/'validation.json').read_text())
    plan=json.loads((prior/'input-plan.json').read_text())
    points=json.loads((prior/'checkpoints.json').read_text())
    at={}
    for point in points:at.setdefault(point['frame'],[]).append(point['label'])
    runtime=ServiceRuntime(rom,out);rows=[];checkpoints=[];frame_pcm_ends=[0]
    try:
        runtime.load_state(prior/'initial.state')
        assert runtime.memory(2)==(prior/'initial-ram.bin').read_bytes()
        assert runtime.memory(0)==(prior/'initial-sram.bin').read_bytes()
        def observe(rt):
            ram=rt.memory(2);sram=rt.memory(0);pcm=rt.pcm_frame()
            row=dict(frame=rt.frames,global_state=ram[0x7A],nmi_scene=ram[0x78],
                     battle_state=list(ram[0x500:0x502]),AP=ram[0x505],tactic=ram[0x543],result=ram[0x544],
                     animation=ram[0x4C8],message_progress=ram[0x300],message_type=ram[0x310],
                     text_draw_cursor=ram[0x304],PPU_jobs=ram[0x7E],NMI_busy=ram[0x7B],IRQ_pending=ram[0x62],
                     audio_channels_0700_07FF=ram[0x700:0x800].hex(),palette_0100_011F=ram[0x100:0x120].hex(),
                     RAM_sha256=hashlib.sha256(ram).hexdigest(),SRAM_sha256=hashlib.sha256(sram).hexdigest(),
                     RGB_sha256=hashlib.sha256(rt.frame.tobytes()).hexdigest(),
                     PCM_stereo_samples=len(pcm)//4,PCM_sha256=hashlib.sha256(pcm).hexdigest(),
                     PCM_nonzero=any(pcm),PCM_stop_byte=len(rt.pcm))
            rows.append(row);frame_pcm_ends.append(len(rt.pcm))
            for label in at.get(rt.frames,[]):
                rt.snapshot(label)
                checks={kind:(out/(label+kind)).read_bytes()==(prior/(label+kind)).read_bytes()
                        for kind in ('.png','-ram.bin','-sram.bin','.state')}
                assert all(checks.values()),(case,label,checks)
                checkpoints.append(dict(label=label,frame=rt.frames,prior_artifact_equal=checks,
                                        PPU_jobs=row['PPU_jobs'],animation=row['animation'],
                                        message_progress=row['message_progress'],PCM_stop_byte=len(rt.pcm)))
        for step in plan:
            assert runtime.frames==step['start_frame']
            runtime.run(step['frames'],step['buttons'],observer=observe)
        assert runtime.frames==validation['frames'] and len(checkpoints)==len(points)
        assert all(r['PCM_stereo_samples']>0 for r in rows) and any(r['PCM_nonzero']for r in rows)
        full_audio=runtime.save_wav(out/'full-flow.wav')
        start=next(p['frame']for p in points if p['label']=='effect-before')
        stop=next(p['frame']for p in points if p['label']=='result-message')
        excerpt=runtime.save_wav(out/'cast-and-result.wav',frame_pcm_ends[max(0,start-30)],frame_pcm_ends[stop])
        write(out/'frame-services.json',rows);write(out/'checkpoints.json',checkpoints)
        write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',runtime.audio_calls)
        artifacts={}
        for p in sorted(out.iterdir()):
            if p.is_file()and p.stat().st_size>0 and p.name not in ('validation.json','repeat-validation.json'):
                artifacts[p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
        result=dict(status='passed',case=case,rom_sha256=SHA,rom_modified=False,
                    initial_state=str((prior/'initial.state').relative_to(ROOT)),initial_state_sha256=sha(prior/'initial.state'),
                    preparation_reference=str((prior/'validation.json').relative_to(ROOT)),preparation_sha256=sha(prior/'validation.json'),
                    additional_core_memory_writes=0,additional_input_events=0,natural_campaign=False,
                    script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),
                    original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),core=runtime.info,AV=runtime.av_info,
                    frames=runtime.frames,checkpoints=len(checkpoints),prior_byte_parity_checks=len(checkpoints)*4,
                    final_battle_state=list(runtime.memory(2)[0x500:0x502]),
                    all_frames_native_RGB_and_PCM_observed=True,full_audio=full_audio,cast_excerpt=excerpt,
                    native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
                    artifact_sha256=artifacts,empty_VRAM_exports_excluded=len(checkpoints),
                    limits=['Input, positions/numerical/RNG conditions are inherited from the fully disclosed phase9 controlled fixtures.',
                            'Native video and PCM prove the original core flow; the readable source driver emits registers, it does not synthesize PCM.',
                            'Per-frame RAM/RGB/PCM records are not internal NMI/CPU instruction traces.'])
        write(out/'validation.json',result)
        return result
    finally:runtime.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/runtime')
    p.add_argument('--case',default='all');p.add_argument('--repeat',action='store_true');a=p.parse_args()
    assert sha(a.rom)==SHA
    cases=[v['case']for v in json.loads((ROOT/'analysis/phase9/runtime/evidence.json').read_text())['native_cases']]
    if a.case!='all':assert a.case in cases;cases=[a.case]
    for case in cases:
        first=a.out/case;first.mkdir(parents=True,exist_ok=True);one=capture(a.rom,first,case)
        if a.repeat:
            second=a.out.parent/'runtime-repeat'/case;second.mkdir(parents=True,exist_ok=True);two=capture(a.rom,second,case)
            checks=[]
            for name,expected in one['artifact_sha256'].items():
                equal=expected==two['artifact_sha256'][name]
                checks.append(dict(artifact=name,equal=equal,**expected))
            # Output-directory/event paths legitimately differ in snapshotJSON;
            # every recorded frame, PCM sample and real core artifact must match.
            canonical=[v for v in checks if not v['artifact'].endswith('.json')or v['artifact']in ('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json')]
            assert all(v['equal']for v in canonical),[v for v in canonical if not v['equal']]
            repeat=dict(status='passed',first_run=str(first.relative_to(ROOT)),second_run=str(second.relative_to(ROOT)),
                        all_hashes_equal=True,nonempty_artifact_checks=len(canonical),artifacts=canonical,
                        excluded_directory_metadata=[v['artifact']for v in checks if v not in canonical])
            write(first/'repeat-validation.json',repeat)
        print(json.dumps({k:one[k]for k in ('status','case','frames','checkpoints','prior_byte_parity_checks','full_audio')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
