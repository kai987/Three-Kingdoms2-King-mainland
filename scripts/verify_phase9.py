#!/usr/bin/env python3
"""Check phase9 original bytes, source receipts, native replays and delivery pins."""
import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source.recovered.game_engine import ROM_SHA256

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def pin_file(item):
    assert sha(ROOT/item['path'])==item['sha256'],item['path']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    modules={'individual':'tactic_individual_effects','area-conversion':'tactic_area_conversion','targeting':'player_tactic_targeting'}
    receipts={area:read(f'analysis/phase9/{area}/validation.json')for area in modules}
    evidence={area:read(f'analysis/phase9/{area}/evidence.json')for area in (*modules,'settlement')}
    code_count=code_bytes=data_bytes=0
    for area,e in evidence.items():
        assert e['rom_sha256']==ROM_SHA256
        for item in e['ranges']:
            raw=bytes.fromhex(item['raw_hex']);offset=item.get('rom_offset',item.get('file_start'))
            assert raw==rom[offset:offset+len(raw)],(area,item['name'])
            assert hashlib.sha256(raw).hexdigest()==item['sha256'];code_count+=1;code_bytes+=len(raw)
        for item in e.get('dependency_pins',[])+e.get('REA_archive',[]):pin_file(item)
        for item in e.get('tables',[]):
            raw=bytes.fromhex(item['raw_hex']);offset=item['rom_offset']
            assert raw==rom[offset:offset+len(raw)] and hashlib.sha256(raw).hexdigest()==item['sha256'];data_bytes+=len(raw)
        for item in e.get('map_chunks',[]):
            raw=rom[item['rom_offset']:item['rom_offset']+item['byte_count']]
            assert hashlib.sha256(raw).hexdigest()==item['sha256'];data_bytes+=len(raw)
    for area,module in modules.items():
        r=receipts[area];assert r['status']=='passed' and r['failed_count']==0 and not r['failures']
        assert r['rom_sha256']==ROM_SHA256
        assert sha(ROOT/f'source/recovered/{module}.py')==r['source_sha256']
        assert sha(ROOT/f'scripts/verify_{module}.py')==r['validator_sha256']
        for name,expected in r.get('dependency_source_sha256',{}).items():assert sha(ROOT/'source/recovered'/name)==expected
        if 'evidence_sha256'in r:assert sha(ROOT/f'analysis/phase9/{area}/evidence.json')==r['evidence_sha256']
    for row in evidence['targeting']['native_snapshot_inputs']:
        for kind in ('header','RAM','SRAM'):assert sha(ROOT/row[kind+'_path'])==row[kind+'_sha256']
    assert len(evidence['targeting']['native_snapshot_inputs'])==20
    legacy=read('analysis/phase8/effects/evidence.json')['fully_recovered_effect_ids']
    remaining=[1,5,7,8,9,10,12,14]
    assert sorted(legacy+remaining)==list(range(16)) and not set(legacy)&set(remaining)
    assert evidence['area-conversion']['supported_tactic_ids']==[7,8,10,12,14]
    assert sorted(int(k)for k in evidence['individual']['entries'])==[1,5,9]
    independent=[f'source/recovered/{m}.py'for m in modules.values()]+['source/recovered/tactical_effects_complete.py']
    for name in independent:
        imports=[]
        for node in ast.walk(ast.parse((ROOT/name).read_text())):
            if isinstance(node,ast.Import):imports.extend(v.name for v in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
        assert not any(v in item for item in imports for v in ('tactical_ai_control','runtime_services','py65','trace_startup','state_machine')),(name,imports)
    integration=read('analysis/phase9/source-integration.json')
    assert integration['status']=='passed' and not integration['failures']
    assert integration['actual_ROM_CPU_comparison_count']==sum(integration['counts'].values())==1421
    assert integration['native_core_field_comparison_count']==len(integration['native_core_field_cases'])==12
    assert integration['source_guard_count']==len(integration['source_guards'])==3
    assert all(v['all_memory_unchanged'] and v['rejected']for v in integration['source_guards'])
    for name,expected in integration['source_sha256'].items():assert sha(ROOT/name)==expected,name
    for case in integration['native_core_field_cases']:assert all(v['equal']for v in case['comparisons'])
    manifest=read('analysis/phase9/runtime/evidence.json');summary=manifest['summary']
    assert manifest['status']=='passed' and manifest['rom_modified'] is False
    assert manifest['native_instruction_trace'] is False and manifest['CPU_oracle_cases_in_this_receipt']==0
    assert sha(ROOT/manifest['script'])==manifest['script_sha256']
    assert sha(ROOT/'scripts/nes_runtime.py')==manifest['runtime_helper_sha256']
    assert sha(ROOT/manifest['parent_state'])==manifest['parent_sha256']
    assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')==manifest['core']['core_sha256']
    frames=checkpoints=artifacts=empty_vram=full_logs=0;runtime_pins={};rng_cases=[]
    prohibited=set(range(0x4D8,0x4E0))|{0x500,0x501,0x543,0x544,0x4C8,0x7E,0x81,0x87,0x300,0x304,0x310,0x6F8B,0x6F8C,0x6F8D,0x6F8E,0x6F8F,0x6F92}
    for row in manifest['native_cases']:
        base=Path('analysis/phase9/runtime');r=read(base/row['validation']);repeat=read(base/row['repeat_validation'])
        path=ROOT/base/row['case'];second=ROOT/repeat['second_run']
        assert r['status']==repeat['status']=='passed' and repeat['all_hashes_equal'] and repeat['full_frame_fields_equal']
        assert r['rom_sha256']==ROM_SHA256 and r['rom_modified'] is False and r['controlled_fixture'] and not r['natural_gameplay']
        assert not r['selected_tactic_result_request_cache_animation_ack_injection'] and not r['readiness_or_ack_injection']
        assert r['script_sha256']==manifest['script_sha256'] and r['core']==manifest['core']
        assert sha(ROOT/r['parent_state'])==r['parent_sha256'] and r['native_instruction_trace'] is False
        parent=ROOT/r['parent_state'];prefix=parent.with_suffix('')
        for kind,size,suffix,start in [('RAM',2048,'-ram.bin',0),('SRAM',8192,'-sram.bin',0x6000)]:
            current=bytearray(Path(str(prefix)+suffix).read_bytes());assert len(current)==size
            for item in r[kind+'_preparation']:
                address=item['address'];assert address not in prohibited
                assert current[address-start]==item['old'];current[address-start]=item['new']
            assert bytes(current)==(path/f'initial-{kind.lower()}.bin').read_bytes()
        assert r['rng_preparation']==[v for v in r['RAM_preparation']if v['address']==0x50]
        if r['rng_preparation']:rng_cases.append(row['case'])
        assert len(read(base/row['frame_fields']))==r['frames']==r['frame_samples']==row['frames']
        assert sha(path/'frame-fields.json')==sha(second/'frame-fields.json');full_logs+=1
        assert len(read(base/row['checkpoints']))==r['checkpoint_count']==row['checkpoint_count']
        assert r['available_memory_exports']['VRAM']=={'available':False,'bytes':0,'excluded':True}
        empty_vram+=len(r['empty_vram_exports_excluded']);frames+=r['frames'];checkpoints+=r['checkpoint_count']
        assert len(repeat['artifacts'])==repeat['nonempty_artifact_checks']==row['nonempty_artifact_checks']
        for item in repeat['artifacts']:
            first=path/item['artifact'];other=second/item['artifact']
            assert item['equal'] and first.stat().st_size==other.stat().st_size==item['bytes']>0
            assert sha(first)==sha(other)==item['sha256'];artifacts+=1
        for name,expected in r['artifact_sha256'].items():
            assert (path/name).stat().st_size==expected['bytes']>0 and sha(path/name)==expected['sha256']
        runtime_pins[row['case']]=sha(path/'validation.json')
    assert rng_cases==['tactic-08','tactic-09','tactic-09-levelup']
    assert len(manifest['native_cases'])==summary['native_case_count']==10
    assert frames==summary['frames_first_run']==18809 and checkpoints==summary['checkpoint_count']==83
    assert artifacts==summary['nonempty_artifact_hash_checks']==362 and full_logs==10 and empty_vram==83
    assert read('analysis/phase9/runtime/validation.json')['summary']==summary
    browser=read('analysis/phase9/browser-validation.json');assert browser['status']=='passed' and all(browser['checks'].values())
    assert sha(ROOT/'analysis/phase9/index.html')==browser['html_sha256']
    assert sha(ROOT/'analysis/phase9/browser-proof.png')==browser['screenshot_sha256']
    regressions={}
    for phase in (5,6,7,8):
        previous=read(f'analysis/phase{phase}/verification.json');assert previous['status']=='passed'
        assert previous['source_and_validator_sha256']['source/recovered/game_engine.py']==sha(ROOT/'source/recovered/game_engine.py')
        regressions[str(phase)]=sha(ROOT/f'analysis/phase{phase}/verification.json')
    files=independent+['source/recovered/game_engine.py','source/recovered/tactical_effects.py',
          'source/recovered/tactical_decisions.py','source/recovered/officer_transfer.py',
          'source/recovered/battle.py','source/recovered/game_algorithms.py','source/recovered/game_enums.py',
          'scripts/verify_phase9.py','scripts/verify_phase9_integration.py',
          'scripts/analyze_phase9_settlement.py','scripts/capture_remaining_tactics.py',
          'scripts/build_phase9_browser.py','scripts/nes_runtime.py','scripts/package_results.py']
    for module in modules.values():files.extend([f'scripts/analyze_{module}.py',f'scripts/verify_{module}.py'])
    result=dict(status='passed',rom_sha256=ROM_SHA256,rebuilt_byte_identical=True,
                rom_cpu_case_count=sum(r['rom_cpu_case_count']for r in receipts.values()),
                source_guard_case_count=sum(r['source_guard_case_count']for r in receipts.values()),
                integration_rom_cpu_case_count=1421,integration_source_guard_case_count=3,
                native_core_field_comparison_count=12,native_core_case_count=10,native_core_frame_count=frames,
                native_core_frames_both_runs=frames*2,native_core_checkpoint_count=checkpoints,
                repeat_artifact_checks=artifacts,full_frame_log_repeat_checks=full_logs,excluded_empty_vram_exports=empty_vram,
                rng_prepared_cases=rng_cases,native_internal_CPU_trace=False,source_original_code_calls=0,
                semantic_source_IR_interpretation=False,fully_recovered_effect_ids=list(range(16)),external_effect_ids=[],
                verified_code_ranges=code_count,verified_code_range_bytes=code_bytes,verified_table_and_map_bytes=data_bytes,
                source_and_validator_sha256={f:sha(ROOT/f)for f in files},
                receipt_sha256={area:sha(ROOT/f'analysis/phase9/{area}/validation.json')for area in modules},
                evidence_sha256={area:sha(ROOT/f'analysis/phase9/{area}/evidence.json')for area in evidence},
                runtime_validation_sha256=runtime_pins,integration_sha256=sha(ROOT/'analysis/phase9/source-integration.json'),
                runtime_evidence_sha256=sha(ROOT/'analysis/phase9/runtime/evidence.json'),
                browser_sha256=sha(ROOT/'analysis/phase9/browser-validation.json'),regressions=regressions,
                limits=['Declared gameRAM/all8KiBSRAM semantic comparison excludes CPU registers/stack/mapper and video timing.',
                        '10 native cases use explicit numerical/position/RNG preparations; no natural campaign reachability claim.',
                        'Native frame fields are not an internal core CPU instruction trace.',
                        'Death refresh, graphics/audio/input services remain real prerequisites; no automatic acknowledgement.'])
    assert result['rom_cpu_case_count']==4267 and result['source_guard_case_count']==31
    (ROOT/'analysis/phase9/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','rom_cpu_case_count','source_guard_case_count',
          'integration_rom_cpu_case_count','integration_source_guard_case_count','native_core_field_comparison_count',
          'native_core_case_count','native_core_frame_count','repeat_artifact_checks','verified_code_ranges')},ensure_ascii=False))
if __name__=='__main__':main()
