#!/usr/bin/env python3
"""Audit phase10 immutable bytes, declared source contracts and native media."""
import argparse
import ast
import hashlib
import json
import sys
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source.recovered.officers import ROM_SHA256

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def pins(values,prefix=Path()):
    for name,expected in values.items():assert sha(ROOT/prefix/name)==expected,name
def objects(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from objects(child)
    elif isinstance(value,list):
        for child in value:yield from objects(child)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    modules={'graphics':'battle_graphics_services','audio':'audio_services','nmi':'battle_nmi_services','text':'text_services','scroll':'scroll_graphics_services'}
    receipts={};evidence={};raw_objects=raw_bytes=0
    for area,module in modules.items():
        base=Path('analysis/phase10')/area;r=read(base/'validation.json');e=read(base/'evidence.json')
        assert r['status']=='passed' and r['failed_count']==0 and not r['failures'],area
        assert r['rom_sha256']==e['rom_sha256']==ROM_SHA256
        assert r['source_sha256']==sha(ROOT/f'source/recovered/{module}.py')
        assert r['validator_sha256']==sha(ROOT/f'scripts/verify_{module}.py')
        for key,prefix in [('dependencies',Path()),('dependency_source_sha256',Path('source/recovered'))]:pins(r.get(key,{}),prefix)
        if 'evidence_sha256'in r:assert r['evidence_sha256']==sha(ROOT/base/'evidence.json')
        if 'analysis_sha256'in e:assert e['analysis_sha256']==sha(ROOT/f'scripts/analyze_{module}.py')
        for item in e.get('dependency_pins',[])+e.get('REA_archive',[]):assert sha(ROOT/item['path'])==item['sha256'],item['path']
        for item in r.get('dependency_pins',[]):assert sha(ROOT/item['path'])==item['sha256'],item['path']
        for item in objects(e):
            if 'raw_hex' in item and 'rom_offset'in item:
                raw=bytes.fromhex(item['raw_hex']);offset=item['rom_offset']
                assert raw==rom[offset:offset+len(raw)],(area,item.get('name'))
                if 'sha256'in item:assert hashlib.sha256(raw).hexdigest()==item['sha256']
                raw_objects+=1;raw_bytes+=len(raw)
        # New offsets include the16-byte iNES header (phase9 historical erratum).
        executed=ROOT/base/'executed-instructions.json'
        if executed.exists():
            for item in json.loads(executed.read_text()):
                bank=item.get('physical_bank',item.get('bank'));cpu=item.get('cpu_address',item.get('cpu'))
                assert item['rom_offset']==16+bank*8192+(cpu&8191),area
        receipts[area]=r;evidence[area]=e
    independent=[f'source/recovered/{v}.py'for v in modules.values()]+[
        'source/recovered/service_memory.py','source/recovered/battle_presentation_services.py','source/recovered/tactic_presentation_effects.py']
    for name in independent:
        imports=[]
        for node in ast.walk(ast.parse((ROOT/name).read_text())):
            if isinstance(node,ast.Import):imports.extend(v.name for v in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
        assert not any(v in item for item in imports for v in ('py65','trace_startup','runtime_services','tactical_ai_control','state_machine')),(name,imports)
    integration=read('analysis/phase10/source-integration.json');assert integration['status']=='passed' and not integration['failures']
    assert integration['actual_ROM_CPU_comparison_count']==sum(integration['counts'].values())
    assert integration['NMI_original_CPU_callbacks']==0 and integration['complete_NMI_return_registers_compared']
    assert integration['native_core_field_comparison_count']==0
    assert integration['source_guard_count']==len(integration['source_guards']);pins(integration['source_sha256'])
    terrain=read('analysis/phase10/terrain-validation.json');assert terrain['status']=='passed' and not terrain['failures']
    assert terrain['rom_sha256']==ROM_SHA256
    for item in objects(terrain):
        if 'raw_hex'in item and 'rom_offset'in item:
            raw=bytes.fromhex(item['raw_hex']);assert raw==rom[item['rom_offset']:item['rom_offset']+len(raw)]
            if 'sha256'in item:assert hashlib.sha256(raw).hexdigest()==item['sha256']
    pins(terrain['source_sha256'])
    manifest=read('analysis/phase10/runtime/evidence.json');native=read('analysis/phase10/runtime/validation.json')
    assert manifest['status']==native['status']=='passed' and manifest['summary']==native['summary']
    assert manifest['rom_sha256']==ROM_SHA256 and manifest['rom_modified'] is False
    assert manifest['native_internal_CPU_trace'] is False and manifest['source_CPU_comparisons_in_this_receipt']==0
    for key,name in [('capture_script_sha256','capture_service_flow'),('runtime_extension_sha256','nes_service_runtime'),('original_runtime_sha256','nes_runtime'),('generator_sha256','build_phase10_browser')]:
        assert manifest[key]==sha(ROOT/f'scripts/{name}.py')
    assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')==manifest['core']['core_sha256']
    assert native['evidence_sha256']==sha(ROOT/'analysis/phase10/runtime/evidence.json')
    frames=checkpoints=artifacts=parity=sample_frames=pcm_bytes=wav_checks=0;runtime_pins={}
    for row in manifest['native_cases']:
        base=Path('analysis/phase10/runtime')/row['case'];r=read(base/'validation.json');repeat=read(base/'repeat-validation.json')
        assert r['status']==repeat['status']=='passed' and repeat['all_hashes_equal']
        assert r['rom_modified'] is False and r['additional_core_memory_writes']==r['additional_input_events']==0
        assert row['controlled_fixture'] and not r['natural_campaign']
        assert r['core']==manifest['core'] and r['AV']['native_dimensions']==[256,240] and r['AV']['sample_rate']==48000
        assert sha(ROOT/r['initial_state'])==r['initial_state_sha256']==row['initial_state_sha256']
        assert sha(ROOT/r['preparation_reference'])==r['preparation_sha256']==row['preparation_sha256']
        old=read(r['preparation_reference']);assert read(base/'input-plan.json')==old['input_plan']
        assert r['script_sha256']==manifest['capture_script_sha256'] and r['runtime_extension_sha256']==manifest['runtime_extension_sha256'] and r['original_runtime_sha256']==manifest['original_runtime_sha256']
        second=ROOT/repeat['second_run']
        for item in repeat['artifacts']:
            first=ROOT/base/item['artifact'];other=second/item['artifact']
            assert item['equal'] and first.stat().st_size==other.stat().st_size==item['bytes']>0
            assert sha(first)==sha(other)==item['sha256'];artifacts+=1
        assert len(repeat['artifacts'])==repeat['nonempty_artifact_checks']==row['nonempty_artifact_checks']
        for name,item in r['artifact_sha256'].items():assert sha(ROOT/base/name)==item['sha256'] and (ROOT/base/name).stat().st_size==item['bytes']>0
        logs=read(base/'frame-services.json');callbacks=read(base/'audio-callbacks.json');points=read(base/'checkpoints.json')
        assert len(logs)==len(callbacks)==r['frames']==row['frames'] and len(points)==row['checkpoint_count']
        for point in points:
            for suffix in ('.png','-ram.bin','-sram.bin','.state'):
                filename=point['label']+suffix
                assert (ROOT/base/filename).read_bytes()==(ROOT/'analysis/phase9/runtime'/row['case']/filename).read_bytes();parity+=1
        assert r['prior_byte_parity_checks']==len(points)*4 and r['empty_VRAM_exports_excluded']==len(points)
        for name,key in [('full-flow.wav','full_audio'),('cast-and-result.wav','cast_excerpt')]:
            with wave.open(str(ROOT/base/name),'rb')as wav:
                assert wav.getnchannels()==2 and wav.getsampwidth()==2 and wav.getframerate()==48000 and wav.getcomptype()=='NONE'
                pcm=wav.readframes(wav.getnframes());assert wav.getnframes()==r[key]['stereo_sample_frames']
            assert len(pcm)==r[key]['PCM_bytes']>0 and hashlib.sha256(pcm).hexdigest()==r[key]['PCM_sha256'] and sha(ROOT/base/name)==r[key]['WAV_sha256'];wav_checks+=1
            if key=='full_audio':
                sample_frames+=r[key]['stereo_sample_frames'];pcm_bytes+=len(pcm);cursor=0
                for index,(log,callback)in enumerate(zip(logs,callbacks),1):
                    stop=log['PCM_stop_byte'];part=pcm[cursor:stop]
                    assert stop>cursor and len(part)==4*log['PCM_stereo_samples']==4*callback['stereo_sample_frames']
                    assert hashlib.sha256(part).hexdigest()==log['PCM_sha256']==callback['pcm_sha256']
                    assert index==log['frame']==callback['emulated_frame_start']+1;assert log['PCM_nonzero']==any(part);cursor=stop
                assert cursor==len(pcm)
        frames+=len(logs);checkpoints+=len(points);runtime_pins[row['case']]=sha(ROOT/base/'validation.json')
    summary=native['summary'];assert len(manifest['native_cases'])==summary['native_case_count']==10
    assert frames==summary['frames_first_run']==18809 and checkpoints==summary['checkpoint_count']==83
    assert artifacts==summary['nonempty_repeat_artifact_checks']==392 and parity==summary['phase9_native_artifact_parity_checks']==332
    assert sample_frames==summary['PCM_stereo_sample_frames_full']==15022464 and pcm_bytes==summary['PCM_bytes_full']==60089856
    assert wav_checks==summary['WAV_file_checks']==20 and all(native['checks'].values())
    browser=read('analysis/phase10/browser-validation.json');assert browser['status']=='passed' and all(browser['checks'].values())
    assert sha(ROOT/'analysis/phase10/index.html')==browser['html_sha256'] and sha(ROOT/'analysis/phase10/browser-proof.png')==browser['screenshot_sha256']
    regressions={}
    for phase in (5,6,7,8,9):
        previous=read(f'analysis/phase{phase}/verification.json');assert previous['status']=='passed'
        assert previous['source_and_validator_sha256']['source/recovered/game_engine.py']==sha(ROOT/'source/recovered/game_engine.py')
        regressions[str(phase)]=sha(ROOT/f'analysis/phase{phase}/verification.json')
    files=independent+['source/recovered/game_engine.py','scripts/verify_phase10.py','scripts/verify_phase10_integration.py','scripts/verify_phase10_terrain.py','scripts/capture_service_flow.py','scripts/nes_service_runtime.py','scripts/nes_runtime.py','scripts/build_phase10_browser.py','scripts/package_results.py']
    for module in modules.values():files.extend([f'scripts/analyze_{module}.py',f'scripts/verify_{module}.py'])
    result=dict(status='passed',rom_sha256=ROM_SHA256,rebuilt_byte_identical=True,
        rom_cpu_case_count=sum(r['rom_cpu_case_count']for r in receipts.values()),source_guard_case_count=sum(r['source_guard_case_count']for r in receipts.values()),
        original_audio_complete_case_count=receipts['audio']['original_complete_case_count'],original_audio_prefix_case_count=receipts['audio']['original_prefix_case_count'],
        integration_rom_cpu_case_count=integration['actual_ROM_CPU_comparison_count'],integration_source_guard_case_count=integration['source_guard_count'],
        terrain_rom_cpu_case_count=terrain['rom_cpu_case_count'],terrain_source_guard_case_count=terrain['source_guard_case_count'],NMI_validator_external_ROM_callbacks=receipts['nmi']['actual_external_ROM_callback_count'],integration_original_CPU_callbacks=0,
        source_original_code_calls=0,new_service_IR_interpretation=False,native_core_field_comparison_count=0,native_internal_CPU_trace=False,
        native_core_case_count=10,native_core_frame_count=frames,native_core_frames_both_runs=frames*2,native_core_checkpoint_count=checkpoints,
        repeat_artifact_checks=artifacts,phase9_native_artifact_parity_checks=parity,PCM_stereo_sample_frames_full=sample_frames,PCM_bytes_full=pcm_bytes,WAV_file_checks=wav_checks,
        verified_original_byte_objects=raw_objects,verified_original_bytes_with_overlap=raw_bytes,
        source_and_validator_sha256={f:sha(ROOT/f)for f in files},receipt_sha256={area:sha(ROOT/f'analysis/phase10/{area}/validation.json')for area in modules},evidence_sha256={area:sha(ROOT/f'analysis/phase10/{area}/evidence.json')for area in modules},
        runtime_validation_sha256=runtime_pins,integration_sha256=sha(ROOT/'analysis/phase10/source-integration.json'),terrain_sha256=sha(ROOT/'analysis/phase10/terrain-validation.json'),runtime_evidence_sha256=sha(ROOT/'analysis/phase10/runtime/evidence.json'),browser_sha256=sha(ROOT/'analysis/phase10/browser-validation.json'),regressions=regressions,
        limits=['Native full flows inherit explicit numerical/position/RNG preparations; no natural campaign reachability claim.',
                'New source emits game software register requests, not CPU-cycle NES pixels or PCM synthesis.',
                '61 original CPU helper callbacks belong only to isolated NMI validation; pure integration callbacks do not use them.',
                '12 exact integrated NMI cases cover fixed scene0/1 and busy reentry0/1/3/4, not full active scene3/4 controllers.',
                'Text/animation semantic contracts exclude transient CPU registers; original tactic bodies exclude CPU scratch/stack and field-write interleaving.',
                'Unknown scene/controller callbacks and unavailable hardware inputs remain dependencies.',
                'Historical phase9 individual/targeting executed-instructions rom_offset is PRG-relative; add16 for file offsets. Original-ranges and phase10 offsets already include header.'])
    (ROOT/'analysis/phase10/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','rom_cpu_case_count','source_guard_case_count','integration_rom_cpu_case_count','terrain_rom_cpu_case_count','native_core_frame_count','repeat_artifact_checks','PCM_stereo_sample_frames_full')},ensure_ascii=False))
if __name__=='__main__':main()
