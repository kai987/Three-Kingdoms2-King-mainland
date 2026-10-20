#!/usr/bin/env python3
"""Fail-closed phase14 audit: reset boundaries, two cooperating AI domains.

Reads frozen originalCPU/source/native/browser receipts and current pins only.
No CPU execution, controlIR execution, core replay or production change occurs.
Three primarydomains plus one independently validated cooperationUI auxiliary
area are counted once; its standalone cases are not duplicated in integration.
Completion kinds, terminal/poll/service/budget prefixes and source guards remain
separate. Old Native/versioned ZIPs remain immutable; old current audits may be
rerun by the root for new coordinator/API pins before this final audit.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit,parse_qs,unquote
import argparse,hashlib,json,sys,wave
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from verify_phase12 import source_AST,objects,path_for,relative,sha,read
from verify_phase13 import Audit as PreviousAudit,cpu_counts
OUT=ROOT/'analysis/phase14';SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={'boot':'boot_initialization','domestic':'domestic_cooperation_controller','tactical':'tactical_cooperation_controller',
         'city-cooperation-ui':'city_cooperation_ui_services'}
INTEGRATION=OUT/'source-integration.json'
NATIVE_CASES={'cold-city-domestic-cycle','core-reset-battery-retention','title-intro-software-restart'}

class Audit(PreviousAudit):
    def common_pins(self,data,area):
        module=MODULES[area]
        maps=('pins','source_sha256','dependencies','dependency_source_sha256','source_and_validator_sha256',
              'source_and_analyzer_pins','REA_archive_pins','source_dependency_pins','dependency_pins',
              'native_input_sha256','artifact_sha256','source_and_analyzer_sha256')
        for value in objects(data):
            if isinstance(value.get('path'),str)and isinstance(value.get('sha256'),str):self.pin(value['path'],value['sha256'],value.get('bytes'))
            for key in maps:
                if isinstance(value.get(key),dict):
                    for path,digest in value[key].items():
                        if isinstance(digest,str):self.pin(path,digest)
                        elif isinstance(digest,dict)and isinstance(digest.get('sha256'),str):self.pin(path,digest['sha256'],digest.get('bytes'))
        if not isinstance(data,dict):return
        for key,path in [('source_sha256',data.get('source_path',f'source/recovered/{module}.py')),
                         ('validator_sha256',data.get('validator_path',f'scripts/verify_{module}.py')),
                         ('analyzer_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py'))]:
            if isinstance(data.get(key),str):self.pin(path,data[key])
        if isinstance(data.get('evidence_sha256'),str):self.pin(OUT/area/'evidence.json',data['evidence_sha256'])

def classification(area,r):
    """Receipt-specific categories: never classify every completion as RTS."""
    if area=='boot':
        rows=r['rows'];halts=[x for x in rows if x['comparison']=='strict_prefix']
        kinds=r['completion_kinds'];assert sum(kinds.values())==r['rom_cpu_case_count']
        assert kinds['reset_E066_boundary']+kinds['actual_caller_RTS']==r['complete_return_count']
        assert kinds['permanent_F41E_diagnostic']==r['strict_prefix_count']
        assert sum(r['group_case_counts'].values())==r['rom_cpu_case_count']
        assert len(halts)==r['strict_prefix_count']==3
        assert all(x['boundary']==0xF41E for x in halts)
        reset=[x for x in rows if x['boundary']==0xE066]
        assert reset and all(x['final_registers']['sp']==255 for x in reset)
        return dict(complete_count_includes_non_RTS_reset_boundaries=True,
            reset_boundary=0xE066,reset_completion_meaning=r['complete_reset_meaning'],
            representative_reset_rows=len(reset),representative_rows=len(rows),rows_are_not_exhaustive_CPU_cases=True,
            terminal_diagnostic_prefix_cases=3,terminal_diagnostic_pc=0xF41E,
            terminal_diagnostic_is_original_permanent_loop=True,unknown_helper_prefix_cases=0,
            diagnostic_palette_colors=[x['diagnostic_palette_color']for x in halts],
            precise_completion_counts=dict(r['completion_kinds']))
    if area=='domestic':
        rows=r['cases'];assert len(rows)==r['rom_cpu_case_count']
        actual=Counter((x['mode'],x['comparison'])for x in rows)
        assert actual==Counter({tuple(k.split('/')):v for k,v in r['counts'].items()})
        waits=[x for x in rows if x['source_status']=='waiting']
        missing=[x for x in rows if x['mode']=='missing_service']
        assert len(waits)==22 and len(missing)==21 and len(waits)+len(missing)==r['strict_prefix_count']
        assert all(x['comparison']=='strict_prefix'and x['waiting_field']==0x6F8B and x['waiting_value']==1 and
            x['final_registers']['pc']in(0xCA7F,0xCB79)for x in waits)
        assert all(x['comparison']=='strict_prefix'and x['source_status']=='dependency'for x in missing)
        return dict(actual_ack_wait_prefix_cases=len(waits),missing_fixed_service_fixture_prefix_cases=len(missing),
            waiting_field=0x6F8B,waiting_required_value=1,waits_do_not_generate_acknowledgement=True,
            pure_source_counts={k:v for k,v in r['counts'].items()if k.startswith('pure_source/')},
            validator_only_original_CPU_helper_cases=sum(v for k,v in r['counts'].items()if k.startswith('original_fixed_helpers/')),
            validator_only_original_CPU_helper_calls=r['original_fixed_helper_calls'],
            helper_calls_not_added_to_CPU_case_count=True)
    if area=='city-cooperation-ui':
        rows=r['rows'];assert len(rows)==r['rom_cpu_case_count']
        assert r['strict_prefix_count']==0 and all(row['completion_kind']=='actual_caller_RTS'and row['comparison']=='complete_return'for row in rows)
        assert Counter(row['group']for row in rows)==Counter(r['counts'])
        return dict(actual_caller_RTS_cases=r['complete_return_count'],independent_auxiliary_area=True,
            included_in_source_integration_count=False,raw_badge_237_255_is_addressing_test_not_valid_game_identity=True)
    rows=r['rows'];counts=r['counts']
    protocol=counts.get('B517_protocol_boundary:strict_prefix',0);budget=counts.get('explicit_block_budget:strict_prefix',0)
    missing=counts.get('missing_F266_real_call_prefix:strict_prefix',0)
    assert protocol+budget+missing==r['strict_prefix_count']
    return dict(inline_B517_protocol_prefix_cases=protocol,explicit_source_block_budget_prefix_cases=budget,
        missing_fixed_service_fixture_prefix_cases=missing,
        explicit_budget_zero_instruction_prefix_rows=sum(x['group']=='explicit_block_budget'and x['original_instructions']==0 for x in rows),
        source_budget_counts_are_not_original_instruction_counts=r['source_block_count_is_not_original_instruction_count'],
        protocol_prefixes_are_not_complete_actor_decisions=True,
        independent_source_F266_calls=r['independent_source_F266_calls'])

def audit_native(audit):
    from PIL import Image
    root=OUT/'runtime';e=read(root/'evidence.json');r=read(root/'validation.json')
    assert e['schema']=='phase14-native-boot-cooperation-flows-v1'
    assert e['status']==r['status']=='passed'and e['rom_sha256']==r['rom_sha256']==SHA
    assert r['evidence_sha256']==sha(root/'evidence.json')
    assert r['fresh_process_per_run']and r['state_import_count']==r['battery_file_import_count']==0
    audit.raw(e,'native')
    pins=e['dependency_pins']
    if isinstance(pins,dict):
        for path,digest in pins.items():audit.pin(path,digest if isinstance(digest,str)else digest['sha256'])
    else:
        for p in pins:audit.pin(p['path'],p['sha256'],p.get('bytes'))
    assert not r['native_internal_CPU_trace']and r['source_CPU_comparisons_in_this_receipt']==0
    assert {x['case']for x in e['native_cases']}==NATIVE_CASES
    total=Counter();details=[]
    for case in e['native_cases']:
        p=root/case['case'];v=read(p/'validation.json');rep=read(p/'repeat-validation.json')
        assert v['schema']=='phase14-native-boot-cooperation-flow-v1'
        assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']
        assert not v['rom_modified']and v['rom_sha256']==SHA
        assert v['cold_boot']and v['fresh_process_per_run']and not v['state_imported']and not v['battery_file_imported']
        assert v['all_frames_native_RGB_PCM_RAM_SRAM_hashed']and v['initial_SRAM_all_zero']
        audit.pin(v['cold_button_plan_path'],v['cold_button_plan_sha256'])
        assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
        assert not v['source_pipeline_installed']and not v['native_internal_CPU_trace']and v['source_CPU_comparisons_in_this_receipt']==0
        for field,key in [('scripts/capture_boot_cooperation_flows.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),('scripts/nes_runtime.py','original_runtime_sha256')]:audit.pin(field,v[key])
        audit.pin('.toolchain/nestopia/nestopia_libretro.dylib',v['core']['core_sha256'])
        for name,item in v['artifact_sha256'].items():
            f=p/name;assert f.stat().st_size==item['bytes']>0 and sha(f)==item['sha256'],f
        second=path_for(rep['second_run']);assert path_for(rep['first_run']).resolve()==p.resolve()
        assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
        for item in rep['artifacts']:
            one=p/item['artifact'];two=second/item['artifact'];assert item['equal']
            assert one.stat().st_size==two.stat().st_size==item['bytes']>0 and sha(one)==sha(two)==item['sha256'],one
        for name in rep['formal_JSON_exact_parity']:
            assert(p/name).read_bytes()==(second/name).read_bytes()and(p/name).stat().st_size>0
        assert len(rep['formal_JSON_exact_parity'])==7
        for name in v['excluded_empty_VRAM']:assert(p/name).stat().st_size==0
        assert(p/'initial-sram.bin').read_bytes()==bytes(8192),'Native cold start must not import battery/state'
        frames=read(p/'frame-services.json');points=read(p/'checkpoints.json');callbacks=read(p/'audio-callbacks.json')
        assert len(frames)==v['frames']and len(points)==v['checkpoint_count']and callbacks
        audio=v['full_audio']
        with wave.open(str(p/'full-flow.wav'),'rb')as w:
            assert(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,audio['stereo_sample_frames'])
            pcm=w.readframes(w.getnframes())
        assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and any(pcm)
        assert sha(p/'full-flow.wav')==audio['WAV_sha256']
        cursor=0
        for index,row in enumerate(frames,1):
            assert row['frame']==index
            count=row['PCM_stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
            assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['PCM_sha256']
            assert cursor==row['PCM_stop_byte']and any(chunk)==row['PCM_nonzero']
        assert cursor==len(pcm);cursor=0
        for row in callbacks:
            count=row['stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
            assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['pcm_sha256']
            assert 0<=row['emulated_frame_start']<v['frames']
        assert cursor==len(pcm)
        for point in points:
            row=frames[point['frame']-1]
            assert sha(p/point['RAM'])==row['RAM_sha256']and sha(p/point['SRAM'])==row['SRAM_sha256']
            assert(p/point['RAM']).stat().st_size==2048 and(p/point['SRAM']).stat().st_size==8192 and(p/point['state']).stat().st_size>0
            with Image.open(p/point['image'])as image:
                assert list(image.size)==row['native_dimensions']==[256,240]
                assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
        native_kind={}
        if case['case']=='core-reset-battery-retention':
            events=v['core_reset_events'];assert len(events)==1;event=events[0]
            assert event['operation']=='retro_reset'and event['SRAM_byteidentical']and not event['SRAM_diff']
            before=p/'before-core-reset-sram.bin';immediate=p/'immediate-reset-sram.bin'
            assert sha(before)==event['before_SRAM_sha256']==event['after_SRAM_sha256']==sha(immediate)
            final=sha(p/'final-sram.bin');assert final==sha(before)
            assert not any('immediate-reset'in point['image']for point in points),'No newRGB frame at instantaneous retro_reset boundary'
            native_kind=dict(reset_operation='original_libretro_retro_reset',immediate_battery_byteidentical=True,final_battery_byteidentical=True)
        elif case['case']=='title-intro-software-restart':
            restart=v['software_restart_observed_frames'];assert restart
            for number in restart:
                previous=frames[number-2];now=frames[number-1]
                assert previous['global_state']==10 and previous['active_main']==4 and now['global_state']==0
            assert any(row['active_controller']=='title'and row['active_main']==4 and row['title_intro_counter_0471_0470']==0xB58 for row in frames)
            assert sha(p/'final-sram.bin')==sha(p/'initial-sram.bin')
            native_kind=dict(software_restart_observed_frames=restart,original_E000_link='Raw originalTitle jump plus observed fields; not native internalPC trace',
                             timer_full_word=0xB58,final_battery_unchanged=True)
        else:
            events=read(p/'flow-events.json')
            exhausted=[row for row in events if row['kind']=='turn-budget-change'and row['before']==1 and row['after']==0 and row['ruler']==2]
            assert exhausted;last_exhausted=exhausted[-1]['frame']
            ai_events=[row for row in events if row['kind']=='observed-domestic-cooperation-status-change'and row['frame']>last_exhausted]
            starts={row['ruler']:row for row in ai_events if row['after']==0};finishes={row['ruler']:row for row in ai_events if row['after']==255}
            assert set(starts)==set(finishes)=={0,1,3,4,5,6}
            assert all(starts[j]['frame']<finishes[j]['frame']and finishes[j]['phase']==2 for j in starts)
            changes=[row for row in events if row['kind']=='calendar-month-change'and row['before']==0 and row['after']==1 and row['frame']>last_exhausted]
            assert changes
            final=frames[-1]
            assert (final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase'])==(2,2,0,1)
            assert (final['ruler_6F03'],final['remaining_budget_raw_6F05'],final['calendar_year_6F00'],final['calendar_month_zero_based_6F01'])==(2,3,89,1)
            assert sha(p/'final-sram.bin')!=sha(p/'initial-sram.bin')
            native_kind=dict(player_command_budget_observed=[3,0],player_last_exhaustion_frame=last_exhausted,
                AI_rulers_with_request_and_return=sorted(starts),AI_request_return_frames={str(j):[starts[j]['frame'],finishes[j]['frame']]for j in starts},
                February_observed=True,calendar_change_frames=[row['frame']for row in changes],player_budget_replenished=3,
                persistent_SRAM_changes_are_original_code_generated=True,observed_cooperation_statuses=sorted({row['after']for row in ai_events}))
        total.update(frames_first_run=v['frames'],checkpoint_count=v['checkpoint_count'],nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
            formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
            excluded_empty_VRAM=len(v['excluded_empty_VRAM']),excluded_snapshot_metadata_JSON=len(v['excluded_snapshot_metadata_JSON']))
        details.append(dict(case=case['case'],status='passed',cold_boot=True,state_imported=False,battery_file_imported=False,
            frames=v['frames'],checkpoint_count=v['checkpoint_count'],input_step_count=v['input_step_count'],termination=v['termination'],
            semantics=native_kind,receipt_path=relative(p/'validation.json'),repeat_receipt_path=relative(p/'repeat-validation.json')))
    for key,value in total.items():assert r[key]==value,(key,value,r[key])
    assert r['frames_both_runs']==2*r['frames_first_run']and r['native_case_count']==3
    assert e['summary']=={key:r[key]for key in e['summary']}
    return dict(**r,cases=details,PCM_stereo_sample_frames_both_runs_derived=2*r['PCM_stereo_sample_frames_first_run'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true',help='Write pending draft only for missing artifacts; stale/failed existing receipts still fail closed');args=p.parse_args()
    rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    audit=Audit(rom)
    for path in(Path(__file__),ROOT/'scripts/verify_phase13.py',ROOT/'scripts/verify_phase12.py',ROOT/'scripts/package_results.py'):audit.pin(path,sha(path))
    missing=[]
    def require(path):
        if path.is_file():return read(path)
        assert args.allow_pending,f'Missing final artifact {relative(path)}'
        missing.append(relative(path));return None
    regressions={}
    for phase in range(5,14):
        path=ROOT/f'analysis/phase{phase}/verification.json';old=read(path);assert old['status']=='passed'and old['rom_sha256']==SHA
        for field in('source_and_validator_sha256','artifact_and_dependency_sha256'):
            for name,digest in old.get(field,{}).items():audit.pin(name,digest)
        regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_pins=True)
    areas={};receipts={};evidences={};cpu=guards=complete=prefix=0
    for area,module in MODULES.items():
        folder=OUT/area;r=require(folder/'validation.json');e=require(folder/'evidence.json')
        if r is None or e is None:continue
        assert r['status']=='passed'and not r.get('quick',False)and r.get('failed_count',0)==0 and not r.get('failures')
        assert r['rom_sha256']==e['rom_sha256']==SHA
        for key in('source_original_CPU_callbacks','production_original_CPU_callbacks','production_source_original_CPU_callbacks'):
            if key in r:assert r[key]==0
        for key in('source_IR_interpretation','production_IR_interpretation'):
            if key in r:assert not r[key]
        audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
        if 'REA_archive'in e:audit.archive(e['REA_archive'])
        for name in('static-catalog.json','source-catalog.json','offline-control-graph.json','executed-instructions.json'):
            path=folder/name
            if path.is_file():
                data=read(path);audit.common_pins(data,area);audit.raw(data,area);audit.pin(path,sha(path))
                if name=='executed-instructions.json':
                    for row in objects(data):
                        if 'rom_offset'in row:
                            bank=row.get('physical_bank',row.get('bank'));pc=row.get('cpu_address',row.get('cpu',row.get('pc')))
                            if bank is not None and pc is not None:assert row['rom_offset']==16+bank*8192+(pc&8191)
        for path in folder.glob('*.asm'):audit.pin(path,sha(path))
        analyzer=ROOT/f'scripts/analyze_{module}.py'
        if analyzer.is_file():audit.pin(analyzer,sha(analyzer))
        readme=folder/'README.md'
        assert readme.is_file(),f'Missing module scope documentation {readme}'
        audit.pin(readme,sha(readme))
        t,g,c,s=cpu_counts(r);cpu+=t;guards+=g;complete+=c;prefix+=s
        assert g==len(r.get('guards',[]))
        areas[area]=dict(status='passed',source_path=f'source/recovered/{module}.py',receipt_path=relative(folder/'validation.json'),evidence_path=relative(folder/'evidence.json'),
            rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=s,
            declared_scope=r.get('comparison_scope',r.get('comparison',r.get('scope'))),declared_limits=r.get('limits',[]),completion_and_prefix_semantics=classification(area,r))
        receipts[area]=sha(folder/'validation.json');evidences[area]=sha(folder/'evidence.json')
    for pair in(8,10,27,29):audit.archive(f'analysis/rea/pairs/pair-{pair:02d}')
    ast_checks=source_AST([ROOT/f'source/recovered/{module}.py'for module in MODULES.values()]+[ROOT/'source/recovered/scene_coordinator.py'])
    integration=require(INTEGRATION);t=g=c=s=0;integration_reset=integration_actual=integration_main=0;integration_scope_summary={}
    if integration is not None:
        assert integration['status']=='passed'and not integration.get('failures')and integration.get('failed_count',0)==0
        assert integration['rom_sha256']==SHA and integration['source_original_CPU_callbacks']==0 and not integration['source_IR_interpretation']
        for key in('source_sha256','source_and_validator_sha256','artifact_sha256'):
            for path,digest in integration.get(key,{}).items():audit.pin(path,digest if isinstance(digest,str)else digest['sha256'])
        t,g,c,s=cpu_counts(integration)
        assert len(integration['rows'])==t
        actual=Counter(row['comparison']for row in integration['rows']);assert actual==Counter({k:v for k,v in(('complete_return',c),('strict_prefix',s))if v})
        assert len(integration.get('guards',integration.get('source_guards',[])))==g
        for row in integration['rows']:
            if 'source_original_CPU_callbacks'in row:assert row['source_original_CPU_callbacks']==0
            if 'status'in row:assert row['status']=='passed'
        integration_reset=sum(row.get('completion_kind')=='reset_E066_boundary'for row in integration['rows'])
        assert integration.get('reset_boundary_count',integration_reset)==integration_reset
        for row in integration['rows']:
            if row.get('completion_kind')=='reset_E066_boundary':
                assert row['comparison']=='complete_return'
                regs=row.get('registers',row.get('final_registers'))
                assert regs['pc']==0xE066 and regs['sp']==255
                if 'old_UI_RTI_or_RTS'in row:assert not row['old_UI_RTI_or_RTS']
        integration_main=sum(row.get('completion_kind')in('global_main_E066_boundary','main_E066_boundary')for row in integration['rows'])
        integration_actual=sum(row.get('completion_kind')=='actual_caller_RTS'for row in integration['rows'])
        assert integration_reset+integration_main+integration_actual==c
        if 'completion_kinds'in integration:
            assert sum(integration['completion_kinds'].values())==t
            assert integration['completion_kinds'].get('reset_E066_boundary',0)==integration_reset
            assert integration['completion_kinds'].get('actual_caller_RTS',0)==integration_actual
        assert integration.get('main_boundary_count',integration_main)==integration_main
        assert integration.get('actual_caller_return_count',integration_actual)==integration_actual
        scope_counts=Counter();nmi_sequences=[]
        for row in integration['rows']:
            scope=row.get('comparison_scope',{});ram_count=row.get('RAM_bytes',scope.get('RAM_bytes'));sram_count=row.get('SRAM_bytes',scope.get('SRAM_bytes'))
            assert ram_count in(2048,1976)and sram_count==8192
            scope_counts[ram_count]+=1
            if ram_count==1976:
                assert row['group']=='main2_succession_actual_NMI2_resume'and not row['ack_injected']and row['main_generator_and_ServiceCall_retained']
                addresses=row['RAM_scope_addresses'];assert len(addresses)==len(set(addresses))==1976
                assert set(addresses)==set([*range(0x1B4),*range(0x200,0x800),*range(0x1FC,0x200)])
                assert row['active_main_caller_stack']==list(range(0x1FC,0x200))
                assert row['NMI_hardware_arrivals']in(241,481)
                for observation in row['NMI_fixed_scope_residue_observations']:
                    for address,original,recovered in observation['excluded_RAM_differences']:assert address not in addresses
                nmi_sequences.append(dict(group=row['group'],input=row['input'],RAM_bytes=ram_count,
                    active_main_caller_stack=row['active_main_caller_stack'],NMI_software_arrivals=row['NMI_hardware_arrivals'],
                    ack_injected=False,boundary_scope=row['boundary_scope']))
        assert scope_counts[1976]==2
        integration_scope_summary=dict(per_row_RAM_byte_counts={str(k):v for k,v in scope_counts.items()},
            complete_SRAM_byte_count=8192,interleaved_NMI_sequences=nmi_sequences,
            nested_NMI_arrivals=sum(row['NMI_hardware_arrivals']for row in integration['rows']if row.get('NMI_hardware_arrivals')),
            nested_NMI_arrivals_are_within_parent_CPU_cases_not_added=True,
            comparison_scope=integration['comparison_scope'])
        children=integration['children'];assert len(children)==2
        assert sum(child['CPU_cases']for child in children)==t and sum(child['guards']for child in children)==g
        for child in children:
            audit.pin(child['path'],child['sha256']);original=read(path_for(child['path']))
            assert original['rom_cpu_case_count']==child['CPU_cases']and original['source_guard_case_count']==child['guards']
            raw_rows=[dict(row)for row in original['rows']]
            combined_rows=[row for row in integration['rows']if row['component']==child['component']]
            assert len(raw_rows)==len(combined_rows)
            for raw,combined in zip(raw_rows,combined_rows):
                normalized=dict(raw);old=raw['comparison'];kind=raw.get('completion_kind')
                if kind is None:kind='reset_E066_boundary'if old=='reset_E066_boundary'else'main_E066_boundary'if old=='complete_main_boundary'else old
                normalized.update(comparison='strict_prefix'if old=='strict_prefix'else'complete_return',
                    completion_kind='strict_prefix'if old=='strict_prefix'else kind,component=child['component'],component_comparison=old,source_original_CPU_callbacks=0)
                assert normalized==combined
        for extra in('boot-integration.json','cooperation-integration.json'):

            path=OUT/extra
            if path.is_file():
                original=read(path);assert original['status']=='passed'and original['rom_sha256']==SHA
                assert original['source_original_CPU_callbacks']==0 and not original['source_IR_interpretation']
                for key in('source_sha256','source_and_validator_sha256','artifact_sha256'):
                    for name,digest in original.get(key,{}).items():audit.pin(name,digest if isinstance(digest,str)else digest['sha256'])
                audit.pin(path,sha(path))
                for location in original.get('executed_original_locations',[]):
                    bank=location.get('physical_bank',location.get('bank'));pc=location.get('CPU_address',location.get('cpu_address',location.get('cpu')))
                    offset=location.get('ROM_offset',location.get('rom_offset'));assert offset==16+bank*8192+(pc&8191)
        receipts['source-integration']=sha(INTEGRATION)
    runtime=None;ne=require(OUT/'runtime/evidence.json');nr=require(OUT/'runtime/validation.json')
    if ne is not None and nr is not None:
        runtime=audit_native(audit);receipts['native']=sha(OUT/'runtime/validation.json');evidences['native']=sha(OUT/'runtime/evidence.json')
    for doc in('README.md','source/README.md','analysis/index.html','analysis/phase14/README.md'):
        path=ROOT/doc
        if path.is_file():audit.pin(path,sha(path))
        else:assert args.allow_pending;missing.append(doc)
    for script in('scripts/write_phase14_report.py',):
        path=ROOT/script
        if path.is_file():audit.pin(path,sha(path))
        else:assert args.allow_pending;missing.append(script)
    static_path=OUT/'browser-static-validation.json';static=require(static_path)
    if static is not None:
        assert static['status']=='passed'and static['JS_syntax']=='passed'and not static['native_files_modified']
        assert static['HTML_sha256']==sha(OUT/'index.html')
        audit.pin('scripts/build_phase14_browser.py',static['generator_sha256']);audit.pin(OUT/'runtime/evidence.json',static['native_evidence_sha256'])
        for item in static['modules']:
            area=areas[item['key']]
            assert(item['CPU'],item['complete'],item['prefix'],item.get('guards',item.get('guard_count',item.get('source_guards'))))==(
                area['rom_cpu_case_count'],area['complete_return_CPU_cases'],area['strict_prefix_CPU_cases'],area['source_guard_case_count'])
        assert len(static['modules'])==len(MODULES)
        if runtime is not None:
            qa=static['native_static_QA'];assert qa['nonempty_double_run_artifacts']==runtime['nonempty_repeat_artifact_checks']
            assert qa['formal_JSON_exact_parity']==runtime['formal_JSON_repeat_checks']and qa['frame_PCM_segments']==runtime['frames_first_run']
            assert qa.get('same_frame_PNG_RAM_SRAM_state',qa.get('PNG_native_RGB_RAM_SRAM_state_checkpoints'))==runtime['checkpoint_count']
        audit.pin(static_path,sha(static_path))
    browser_path=OUT/'browser-validation.json';browser=require(browser_path)
    if browser is not None:
        assert browser['status']=='passed'and browser.get('html_sha256',browser.get('HTML_sha256'))==sha(OUT/'index.html')
        if 'checks'in browser:assert all(browser['checks'].values())
        assert not browser.get('console_errors',[])
        audit.pin(OUT/'browser-proof.png',browser['screenshot_sha256'])
        for item in browser.get('source_modules',[]):
            assert item['full_source_equal'];audit.pin('source/recovered/'+item['file'],item['sha256'],item['bytes'])
        for item in objects(browser):
            if isinstance(item.get('src'),str)and '?'in item['src']:
                url=urlsplit(item['src']);expected=parse_qs(url.query).get('sha')
                if expected:
                    file=ROOT/unquote(url.path.lstrip('/'))if url.path.startswith('/analysis/')else OUT/unquote(url.path)
                    audit.pin(file,expected[0])
        audit.pin(browser_path,sha(browser_path))
    if(OUT/'index.html').exists():audit.pin(OUT/'index.html',sha(OUT/'index.html'))
    result=dict(status='passed'if not missing else'pending_dependencies',rom_sha256=SHA,missing_required_artifacts=missing,
        rom_cpu_case_count=cpu,source_guard_case_count=guards,total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=prefix,areas=areas,
        source_integration_receipt_path=relative(INTEGRATION),source_integration_ROM_CPU_cases=t,source_integration_guard_cases=g,
        source_integration_complete_return_CPU_cases=c,source_integration_strict_prefix_CPU_cases=s,
        source_integration_reset_boundary_CPU_cases=integration_reset,source_integration_actual_return_CPU_cases=integration_actual,
        source_integration_main_boundary_CPU_cases=integration_main,source_integration_completion_kinds=integration.get('completion_kinds')if integration else None,
        source_integration_scope=integration_scope_summary,
        integration_rom_cpu_case_count=t,integration_source_guard_case_count=g,
        all_CPU_cases_including_integration=cpu+t,all_source_guards_including_integration=guards+g,
        all_complete_return_CPU_cases_including_integration=complete+c,all_strict_prefix_CPU_cases_including_integration=prefix+s,
        source_and_validator_sha256={p:h for p,h in audit.pins.items()if p.startswith(('source/','scripts/'))},
        artifact_and_dependency_sha256={p:h for p,h in audit.pins.items()if not p.startswith(('source/','scripts/'))},
        receipt_sha256=receipts,evidence_sha256=evidences,raw_object_count=audit.raw_count,raw_bytes_checked=audit.raw_bytes,
        REA_archives=audit.archives,source_AST=ast_checks,rebuilt_byte_identical=True,regressions=regressions,
        native_evidence_path=relative(OUT/'runtime/evidence.json'),native=runtime,
        browser_static_receipt_path=relative(static_path),browser_static_receipt_sha256=sha(static_path)if static is not None else None,
        browser_receipt_sha256=sha(browser_path)if browser is not None else None,browser_status=browser['status']if browser else'pending',
        limitations=['Boot successfulE066 reset boundaries are notRTS or completehardwareframes.',
            'F41E diagnostic prefixes preserve the original permanenthalt; they are notunknownhelper waits.',
            'Domestic ack22/missing21 and tactical protocol/budget/missing prefixes remain separate.',
            'Per-domain and per-integration-row scopes are retained; aggregate does not substitute a uniformframe scope.',
            'Validator-only originalCPUhelper calls and discovery are notadded to sourcecomparison counts or productioncallbacks.',
            'Native3cases use ordinaryinputs/originalretro_reset withoutstateimport, batteryimport or extraRAM/SRAM/result/readywrites; frames are notinternal6502 traces.',
            'Recovered production uses directPython, neveroriginalCPU/controlIR; originalNES hardware synthesis remains the nativecore.',
            'OriginalROM, Nativefrozen artifacts and oldversionedZIPs remainimmutable. Currentold5..13 integration/auditreceipts are legitimatelyrerun byroot forchangedAPIpins. This auditor reads them; it does not execute theirmatrices.'])
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','all_CPU_cases_including_integration','browser_status','missing_required_artifacts')},ensure_ascii=False))
if __name__=='__main__':main()
