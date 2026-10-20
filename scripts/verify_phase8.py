#!/usr/bin/env python3
"""Verify immutable ROM evidence, semantic source receipts and native replays."""
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

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    receipts={area:read(f'analysis/phase8/{area}/validation.json')for area in ('strategies','effects')}
    evidence={area:read(f'analysis/phase8/{area}/evidence.json')for area in receipts}
    range_bytes=0;range_count=0;data_bytes=0
    for area,r in receipts.items():
        assert r['status']=='passed' and not r['failures'] and r['failed_count']==0
        assert r['rom_sha256']==ROM_SHA256
        assert sha(ROOT/f'source/recovered/tactical_{"strategy_ai" if area=="strategies" else "effects"}.py')==r['source_sha256']
        assert sha(ROOT/f'scripts/verify_tactical_{"strategy_ai" if area=="strategies" else "effects"}.py')==r['validator_sha256']
        for item in evidence[area]['ranges']:
            raw=bytes.fromhex(item['raw_hex']);offset=item.get('rom_offset',item.get('file_start'))
            assert raw==rom[offset:offset+len(raw)] and hashlib.sha256(raw).hexdigest()==item['sha256']
            range_count+=1;range_bytes+=len(raw)
    strategies=evidence['strategies'];effects=evidence['effects']
    for item in strategies['tables']+strategies['city_base_records']:
        raw=bytes.fromhex(item['raw_hex'])if 'raw_hex'in item else bytes(item['raw_y_x'])
        offset=item['rom_offset'];assert raw==rom[offset:offset+len(raw)]
        assert hashlib.sha256(raw).hexdigest()==item['sha256'];data_bytes+=len(raw)
    for item in strategies['dependency_pins']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
    for table in ('player_AP_cost_table','AI_AP_cost_table'):
        item=effects[table];raw=bytes(item['bytes']);assert raw==rom[item['file']:item['file']+len(raw)]
    assert effects['fully_recovered_effect_ids']==[0,2,3,4,6,11,13,15]
    assert effects['external_effect_ids']==[1,5,7,8,9,10,12,14]
    assert effects['deployment']['AI_AP_cost']==0 and effects['deployment']['player_AP_cost']==10
    assert receipts['strategies']['original_complete_case_count']==2215
    assert receipts['strategies']['original_prefix_case_count']==2
    for name,expected in receipts['effects']['dependency_source_sha256'].items():assert sha(ROOT/'source/recovered'/name)==expected
    assert sha(ROOT/'analysis/phase8/effects/evidence.json')==receipts['effects']['evidence_sha256']
    integration=read('analysis/phase8/source-integration.json')
    assert integration['status']=='passed' and not integration['failures']
    assert integration['actual_ROM_CPU_comparison_count']==46
    assert integration['native_core_field_comparison_count']==5
    for name,expected in integration['source_sha256'].items():assert sha(ROOT/name)==expected,name
    for case in integration['native_core_field_cases']:assert all(v['equal']for v in case['comparisons'])

    # Inspect actual imports as an additional source contract; the CPU oracle
    # exists in validation scripts, never these independent gameplay modules.
    for name in ('tactical_strategy_ai.py','tactical_effects.py'):
        tree=ast.parse((ROOT/'source/recovered'/name).read_text());imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(v.name for v in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
        assert not any(v in item for v in ('tactical_ai_control','runtime_services','py65','trace_startup')for item in imports)

    runtime={};replay_checks=0;native_replay_checks=0
    for area in ('ambush-chain','ordinary-cast','cpu-call','cpu-expiry'):
        base=f'analysis/phase8/runtime/{area}';r=read(base+'/validation.json');repeat=read(base+'/repeat-validation.json')
        assert r['status']==repeat['status']=='passed' and r['rom_sha256']==ROM_SHA256
        assert repeat['all_hashes_equal'] and sha(ROOT/'scripts/capture_tactical_effects.py')==r['script_sha256']
        for artifact in repeat['artifacts']:
            first=ROOT/base/artifact['artifact'];second=ROOT/repeat['second_run']/artifact['artifact']
            assert artifact['equal'] and first.stat().st_size==artifact['bytes']>0
            assert sha(first)==sha(second)==artifact['sha256'];replay_checks+=1
        assert len(repeat['artifacts'])==repeat['nonempty_artifact_checks']
        if area in ('ambush-chain','ordinary-cast'):
            native_replay_checks+=len(repeat['artifacts'])
            assert r['rom_modified'] is False and r['controlled_fixture'] and not r['natural_gameplay']
            assert not r['readiness_or_ack_injection'] and not r['success_or_completed_cache_injection']
            assert r['rng_preparation']==[] and repeat['full_frame_fields_equal']
            assert sha(ROOT/r['parent_state'])==r['parent_sha256']
            assert sha(ROOT/'scripts/nes_runtime.py')==r['runtime_helper_sha256']
            assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')==r['core']['core_sha256']
            fields=read(base+'/frame-fields.json');assert len(fields)==r['frame_samples']==r['frames']
            checkpoints=read(base+'/checkpoints.json');assert len(checkpoints)==r['checkpoint_count']
            assert not r['available_memory_exports']['VRAM']['available']
            assert r['available_memory_exports']['VRAM']['bytes']==0
            prohibited=set(range(0x4D8,0x4E0))|{0x500,0x501,0x543,0x544,0x4C8,0x300,0x310,0x6F8B,0x6F8F,0x6F92}
            for item in r['RAM_preparation']+r['SRAM_preparation']:assert item['address']not in prohibited
            for name,expected in r['artifact_sha256'].items():
                assert (ROOT/base/name).stat().st_size==expected['bytes']>0
                assert sha(ROOT/base/name)==expected['sha256']
        else:
            trace=read(base+'/actual-cpu-instructions.json');assert len(trace)==r['instruction_count']
            for item in trace:
                raw=bytes.fromhex(item['bytes']);offset=item['file_offset']
                assert raw==rom[offset:offset+len(raw)]
            assert r['native_instruction_trace'] is False
        runtime[area]=r
    ambush=runtime['ambush-chain']['verified_effects'];ordinary=runtime['ordinary-cast']['verified_effects']
    assert ambush['deploy_cache']==[3,20,17,5] and ambush['deployment_raw_troops']==[700,600]
    assert ambush['deployment_AP']==[10,10] and ambush['trigger_troops_low10']==[1000,468]
    assert ambush['reported_loss']==532 and ambush['NMI_consume_XP_caster']==[3500,3766]
    assert ambush['damage_only_XP_caster']==[3500,3500] and ambush['cache_after_confirmation']==[255,20,17,4]
    assert ambush['request1_visible_at_frame_boundary']is False and not ambush['full_expiry_observed_in_core']
    assert ordinary['AP']==[16,12] and ordinary['target_condition_0651']==[0,3] and ordinary['result_0544']==[255,0]
    assert runtime['cpu-call']['protocol_request_values']==[255,1,255]
    assert all(v['equal']for v in runtime['cpu-call']['native_field_comparisons'].values())
    assert runtime['cpu-call']['blocked_sram_writes']==0 and runtime['cpu-call']['io_event_count']==0
    assert runtime['cpu-expiry']['actual_ROM_CPU_prefix_call_count']==5
    assert runtime['cpu-expiry']['source_CPU_differential_case_count']==0

    for phase in (5,6,7):assert read(f'analysis/phase{phase}/verification.json')['status']=='passed'
    browser=read('analysis/phase8/browser-validation.json');assert browser['status']=='passed'
    assert sha(ROOT/'analysis/phase8/index.html')==browser['html_sha256']
    assert sha(ROOT/'analysis/phase8/browser-proof.png')==browser['screenshot_sha256']
    assert all(browser['checks'].values())
    files=['source/recovered/game_engine.py','source/recovered/tactical_strategy_ai.py',
           'source/recovered/tactical_effects.py','source/recovered/tactical_decisions.py',
           'source/recovered/tactical_exchange.py','source/recovered/ai.py','source/recovered/battle.py',
           'source/recovered/city_ownership.py','source/recovered/game_algorithms.py',
           'scripts/analyze_tactical_strategy_ai.py','scripts/verify_tactical_strategy_ai.py',
           'scripts/analyze_tactical_effects.py','scripts/verify_tactical_effects.py',
           'scripts/capture_tactical_effects.py','scripts/verify_phase8_integration.py','scripts/verify_phase8.py',
           'scripts/build_phase8_browser.py','scripts/nes_runtime.py']
    result=dict(status='passed',rom_sha256=ROM_SHA256,rebuilt_byte_identical=True,
                rom_cpu_case_count=sum(v['rom_cpu_case_count']for v in receipts.values()),
                source_guard_case_count=sum(v['source_guard_case_count']for v in receipts.values()),
                integration_rom_cpu_case_count=integration['actual_ROM_CPU_comparison_count'],
                integration_source_guard_case_count=integration['source_guard_count'],
                native_core_field_comparison_count=integration['native_core_field_comparison_count'],
                native_core_case_count=2,native_core_frame_count=runtime['ambush-chain']['frames']+runtime['ordinary-cast']['frames'],
                native_core_checkpoint_count=24,native_core_repeat_artifact_checks=native_replay_checks,
                repeat_artifact_checks=replay_checks,independent_actual_CPU_protocol_cases=1,independent_actual_CPU_expiry_prefix_calls=5,
                native_internal_CPU_trace=False,source_original_code_calls=0,semantic_source_IR_interpretation=False,
                verified_code_ranges=range_count,verified_code_range_bytes=range_bytes,verified_strategy_data_bytes=data_bytes,
                fully_recovered_effect_ids=effects['fully_recovered_effect_ids'],external_effect_ids=effects['external_effect_ids'],
                source_and_validator_sha256={f:sha(ROOT/f)for f in files},
                receipt_sha256={area:sha(ROOT/f'analysis/phase8/{area}/validation.json')for area in receipts},
                evidence_sha256={area:sha(ROOT/f'analysis/phase8/{area}/evidence.json')for area in receipts},
                runtime_validation_sha256={area:sha(ROOT/f'analysis/phase8/runtime/{area}/validation.json')for area in runtime},
                integration_sha256=sha(ROOT/'analysis/phase8/source-integration.json'),
                browser_sha256=sha(ROOT/'analysis/phase8/browser-validation.json'),
                regressions={str(phase):sha(ROOT/f'analysis/phase{phase}/verification.json')for phase in (5,6,7)},
                limits=['Semantic source comparison covers declared RAM/allSRAM, not CPU registers/stack/mapper or NES timing.',
                        'CPU protocol/expiry captures are independent original-code evidence, not more source differential or native frames.',
                        'Two native cases have explicit legal preparation fields; no natural campaign reachability claim.',
                        '8 effect bodies remain external, as do real graphics/audio/input prerequisites.'])
    (ROOT/'analysis/phase8/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','rom_cpu_case_count','source_guard_case_count','integration_rom_cpu_case_count',
          'native_core_field_comparison_count','native_core_frame_count','repeat_artifact_checks','verified_code_ranges')},ensure_ascii=False))

if __name__=='__main__':main()
