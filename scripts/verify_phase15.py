#!/usr/bin/env python3
"""Read-only, fail-closed phase15 source/CPU/native/browser aggregate.

No CPU, control IR or original core executes here. Two primary areas are
counted once: fields and audio (body matrix plus distinct genuine caller
inputs). CampaignSession is a child of source-integration, not a third primary
matrix. Nested main/NMI/IRQ stages remain within their parent comparisons.
Missing final artifacts may produce an explicit pending draft; stale or failed
existing artifacts never become passed by refreshing their hashes.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit, parse_qs, unquote
import argparse, hashlib, json, sys, wave
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from verify_phase12 import source_AST, objects, path_for, relative, sha, read
from verify_phase13 import Audit as PreviousAudit
OUT=ROOT/'analysis/phase15'
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={'fields':'record_fields','audio-domain':'audio_scene_services'}
INTEGRATION=OUT/'source-integration.json'
GENUINE_AUDIO=OUT/'audio-domain/writer-provenance.json'
NATIVE_CASES={'cold-yearwrap','consecutive-invasions-attack-return','succession-heir','succession-no-heir'}


class Audit(PreviousAudit):
    def common_pins(self,data,area=None,relative_base=None):
        def resolve(path):
            p=Path(path)
            if relative_base is not None and not p.is_absolute()and not str(p).startswith(('analysis/','source/','scripts/','.toolchain/','build/')):
                return relative_base/p
            return path
        maps=('pins','source_sha256','dependencies','dependency_source_sha256','source_and_validator_sha256',
              'source_and_analyzer_pins','REA_archive_pins','source_dependency_pins','dependency_pins',
              'native_input_sha256','artifact_sha256','source_and_analyzer_sha256',
              'artifact_and_dependency_sha256','parent_snapshot_sha256')
        for item in objects(data):
            if isinstance(item.get('path'),str)and isinstance(item.get('sha256'),str):
                self.pin(resolve(item['path']),item['sha256'],item.get('bytes'))
            for key in maps:
                if isinstance(item.get(key),dict):
                    for path,digest in item[key].items():
                        if isinstance(digest,str):self.pin(resolve(path),digest)
                        elif isinstance(digest,dict)and isinstance(digest.get('sha256'),str):self.pin(resolve(path),digest['sha256'],digest.get('bytes'))
        if not isinstance(data,dict):return
        module=MODULES.get(area,'campaign_session')
        for key,path in [('source_sha256',data.get('source_path',f'source/recovered/{module}.py')),
                         ('validator_sha256',data.get('validator_path',f'scripts/verify_{module}.py')),
                         ('analyzer_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py'))]:
            if isinstance(data.get(key),str):self.pin(path,data[key])

    def raw(self,data,area):
        # Original writer provenance uses uppercaseCPU/ROM keys. Normalize
        # only this metadata copy; never rewrite the frozen original receipt.
        rows=[]
        for item in objects(data):
            row=dict(item)
            if 'ROM_offset'in row and 'rom_offset'not in row:row['rom_offset']=row['ROM_offset']
            if 'CPU_PC'in row and 'cpu'not in row:row['cpu']=row['CPU_PC']
            if 'CPU_address'in row and 'cpu'not in row:row['cpu']=row['CPU_address']
            if 'raw_hex'in row:rows.append(row)
        super().raw(rows,area)


def counts(receipt):
    total=receipt.get('rom_cpu_case_count',receipt.get('actual_ROM_CPU_comparison_count'))
    assert isinstance(total,int)and total>=0
    groups=receipt.get('counts',receipt.get('group_case_counts'))
    if groups is not None:
        assert all(isinstance(v,int)and v>=0 for v in groups.values())and sum(groups.values())==total
    rows=receipt.get('rows',receipt.get('cases',[]));assert len(rows)==total
    actual=Counter(x['comparison']for x in rows);assert set(actual)<={'complete_return','strict_prefix'}
    complete=receipt.get('complete_return_count',receipt.get('total_complete_return_CPU_cases',actual['complete_return']))
    prefix=receipt.get('strict_prefix_count',receipt.get('total_strict_prefix_CPU_cases',actual['strict_prefix']))
    assert actual==Counter({k:v for k,v in [('complete_return',complete),('strict_prefix',prefix)]if v})and complete+prefix==total
    guards=receipt.get('source_guard_case_count',0)
    assert isinstance(guards,int)and guards>=0
    if 'guards'in receipt:assert len(receipt['guards'])==guards
    return total,guards,complete,prefix


def passed(receipt,production_contract=True):
    assert receipt['status']=='passed'and not receipt.get('quick',False)
    assert receipt.get('failed_count',0)==0 and not receipt.get('failures')
    assert receipt.get('rom_sha256',receipt.get('ROM_sha256'))==SHA
    if not production_contract:return
    for item in objects(receipt):
        for key in('source_original_CPU_callbacks','production_original_CPU_callbacks','original_CPU_helper_callbacks','source_control_IR_callbacks'):
            if key in item:assert item[key]==0
        for key in('source_IR_interpretation','production_IR_interpretation','runtime_IR_interpretation'):
            if key in item:assert not item[key]


def fields_semantics(receipt):
    rows=receipt['rows'];kinds=Counter(x['completion_kind']for x in rows)
    prefixes=[x for x in rows if x['comparison']=='strict_prefix']
    body=[x for x in rows if x['comparison']=='complete_return']
    assert all(x['source_status']=='returned'and x['completion_kind']=='actual_caller_RTS'for x in body)
    for row in prefixes:
        pc=row['final_registers']['pc']
        if row['entry']==0xBD95:assert pc in(0xBDA3,0xBDEE)
        elif row['entry']==0xA041:assert pc in(0xA068,0xA06B)
        elif row['entry']==0xACF0:assert pc==0xAD03
        else:assert row['entry']==0xAB25 and row['source_status']=='dependency'and pc==0xF2AF
    assert all(row['all_RAM_byte_count']==2048 and row['all_SRAM_byte_count']==8192 for row in rows)
    return dict(actual_caller_RTS_cases=len(body),explicit_bounded_field_prefix_cases=kinds['bounded_field_prefix'],
        deliberate_missing_fixed_service_prefix_cases=kinds['missing_fixed_service'],fixture_domains=receipt['fixture_domains'],
        prefixes_are_not_complete_parent_functions=True,normal_cooldown_and_full_roster_alias_are_distinct=True)


def audio_semantics(body,genuine,audit):
    assert genuine['schema']=='phase15-controlled-original-NMI-audio-writer-v1'
    passed(genuine);t,g,c,p=counts(genuine);assert(t,g,c,p)==(20,0,20,0)
    assert genuine['core_frames_generated']==0 and not genuine['native_internal_CPU_trace']
    audit.common_pins(genuine,'audio-domain');audit.raw(genuine,'audio-genuine-call-inputs')
    inputs=[]
    for row in genuine['rows']:
        assert row['completion_kind']=='actual_caller_RTS'and row['comparison']=='complete_return'
        assert not row['new_source_RAM_differences']and not row['new_source_SRAM_differences']and not row['new_source_register_differences']
        assert row['new_source_ordered_ports_equal']and row['new_source_banks_equal']
        prefix=path_for(row['actual_callee_input']);meta_path=Path(str(prefix)+'.json');meta=read(meta_path)
        ram_path=Path(str(prefix)+'-ram.bin');sram_path=Path(str(prefix)+'-sram.bin')
        ram=ram_path.read_bytes();assert len(ram)==2048 and sram_path.stat().st_size==8192
        assert meta['ROM_sha256']==SHA and meta['registers']==row['initial_registers']and meta['NMI']==row['NMI']and meta['heir']==row['heir']
        registers=meta['registers'];sp=registers['sp']
        word=ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8
        assert((word+1)&65535)==meta['actual_return_PC']==row['return_PC']==row['final_registers']['pc']
        assert((sp+2)&255)==meta['actual_return_SP']==row['return_SP']==row['final_registers']['sp']
        assert registers['pc']==0xA003 and meta['banks'][1:3]==[14,15]
        for path in(meta_path,ram_path,sram_path):audit.pin(path,sha(path))
        inputs.append(dict(path=relative(meta_path),heir=row['heir'],NMI=row['NMI'],caller_PC=row['return_PC'],caller_SP=row['return_SP']))
    assert len({x['path']for x in inputs})==20 and Counter(x['heir']for x in inputs)==Counter({False:10,True:10})
    groups=body['counts'];assert body['source_original_CPU_callbacks']==0 and not body['source_IR_interpretation']
    assert body['comparison']['RAM_bytes']==2048 and body['comparison']['SRAM_bytes']==8192
    assert body['comparison']['free_stack_residue']=='included'
    assert groups['missing_F25F_actual_call_boundary:strict_prefix']==1 and groups['actual_B0_data_loop_budget:strict_prefix']==1
    return dict(body_ROM_CPU_cases=body['rom_cpu_case_count'],genuine_caller_ROM_CPU_cases=t,
        body_complete_return_CPU_cases=body['complete_return_count'],genuine_complete_return_CPU_cases=c,
        deliberate_missing_F25F_prefix_cases=1,declared_music_data_loop_budget_prefix_cases=1,
        genuine_receipt_path=relative(GENUINE_AUDIO),genuine_callee_inputs=inputs,
        original_context_producer_sequences=len(genuine['sequences']),
        original_context_preparation_steps_are_not_extra_source_comparison_cases=True,
        original_context_NMI_arrivals_are_not_extra_CPU_cases=True,
        legacy_semantic_idle_stack_differences_are_contract_diagnostics=True)


def audit_integration(audit,receipt):
    passed(receipt);t,g,c,p=counts(receipt);audit.common_pins(receipt)
    children=receipt['children'];assert{child['component']for child in children}=={'session','succession'}
    assert sum(child['CPU_cases']for child in children)==t and sum(child['guards']for child in children)==g
    child_details=[]
    for child in children:
        path=path_for(child['path']);audit.pin(path,child['sha256']);raw=read(path);passed(raw);child_counts=counts(raw)
        assert child_counts[:2]==(child['CPU_cases'],child['guards']);audit.common_pins(raw)
        combined=[row for row in receipt['rows']if row['component']==child['component']]
        assert len(combined)==len(raw['rows'])
        for original,normalized in zip(raw['rows'],combined):
            # The assembler may change only comparison/completion bookkeeping.
            for key,value in original.items():
                if key not in('comparison','completion_kind'):assert normalized[key]==value,(child['component'],key)
            assert normalized['component_comparison']==original['comparison']
            assert normalized['comparison']==('strict_prefix'if original['comparison']=='strict_prefix'else'complete_return')
        child_details.append(dict(component=child['component'],receipt_path=relative(path),rom_cpu_case_count=child_counts[0],source_guard_case_count=child_counts[1]))
        if child['component']=='session':
            assert raw['comparison']['RAM_bytes']==2048 and raw['comparison']['SRAM_bytes']==8192
            assert raw['comparison']['AXYP_SP_PC']and raw['comparison']['ordered_IO_reads_writes_and_banks']
            nested=[row for row in raw['rows']if row['group']=='NMI_IRQ_chain_then_same_owner_resume']
            assert len(nested)==30
            for row in nested:
                stages=row['stages'];irqs=stages[2:-2]
                assert[x['kind']for x in stages[:2]]==['NMI_wait','accepted_nested_busy_NMI_wait']
                assert[x['kind']for x in stages[-2:]]==['same_nested_NMI_resume_RTI','same_NMI_resume_RTI']
                assert 1<=len(irqs)<=5 and all(x['kind']=='actual_IRQ_RTI'for x in irqs)
                assert[x['pending_depth']for x in row['session_events']]==[1,2]+[2]*len(irqs)+[1,0]
                assert row['completion_kind']=='actual_interrupt_RTI'and irqs[-1]['flag62']==0
                assert all(x['flag62']==128 for x in irqs[:-1])
                assert row['stages'][1]['SP']==row['stages'][0]['SP']-8
                assert row['stages'][-1]['SP']==row['caller_SP']
    kinds=Counter(row['completion_kind']for row in receipt['rows'])
    assert dict(kinds)=={key:value for key,value in receipt['completion_kinds'].items()if value}
    succession=[row for row in receipt['rows']if row['component']=='succession']
    assert len(succession)==2
    nmis=[]
    for row in succession:
        count=row.get('RAM_bytes',row.get('comparison_scope',{}).get('RAM_bytes'))
        sram=row.get('SRAM_bytes',row.get('comparison_scope',{}).get('SRAM_bytes'))
        assert count==2048 and sram==8192,'Phase15 succession must close original inactive-stack residues, not retain the old1976B scope'
        assert row['manual_ack_writes']==0 and row['same_register_object']and row['same_pending_phase']and row['same_ServiceCall_and_generator']
        assert row['idle_stack_exclusion']is None and row['all_declared_comparisons_equal']and row['active_caller_preserved']
        assert row['ack_origin']=='Actual26CBBD..CBBF'
        arrivals=row['NMI_software_arrivals'];assert arrivals in(241,481);nmis.append(arrivals)
        assert row['NMI_parent_case_count']==1 and row['nested_NMI_comparisons_not_added_to_case_count']
        assert len(row['all_NMI_comparisons'])==arrivals and row['pure_source_owner_counts']['audio_scene_exact']==arrivals
        for observed in row['all_NMI_comparisons']:
            assert observed['RAM_bytes']==2048 and observed['RAM_difference_count']==observed['SRAM_difference_count']==observed['register_difference_count']==0
            assert observed['ordered_ports_equal']and observed['bank_equal']and observed['N163_image_equal']
        if 'RAM_scope_addresses'in row:assert set(row['RAM_scope_addresses'])==set(range(2048))
    assert sorted(nmis)==[241,481]
    return dict(status='passed',receipt_path=relative(INTEGRATION),rom_cpu_case_count=t,source_guard_case_count=g,
        complete_return_CPU_cases=c,strict_prefix_CPU_cases=p,completion_kinds=dict(kinds),children=child_details,
        parent_sequences_are_counted_once=True,nested_succession_NMI_arrivals=sum(nmis),nested_NMI_arrivals_not_added_as_CPU_cases=True,
        succession_RAM_bytes=2048,succession_SRAM_bytes=8192,actual_ack_source=True,
        declared_scope=receipt.get('comparison_scope',receipt.get('comparison')))


def audit_preparation(audit,folder,validation):
    """Never convert imported/controlled starts to a global zero-write claim."""
    preparation=validation.get('preparation',[]);assert isinstance(preparation,list)
    forbidden={0x62,0x78,0x7A,0x7B,0x7E,0x4C8,0x500,0x501,0x540,0x541,0x543,0x544,0x6F8B}
    for item in preparation:
        assert all(key in item for key in('frame','kind','address','before','after','reason'))
        address=item['address'];assert isinstance(address,int)and address not in forbidden,(folder.name,item,'Unrequested result/phase/readiness injection')
        assert isinstance(item['before'],int)and isinstance(item['after'],int)and 0<=item['before']<256 and 0<=item['after']<256
    groups=validation.get('preparation_groups',[])
    preparation_path=folder/'preparation.json'
    if not groups and preparation_path.is_file():
        data=read(preparation_path);assert data['writes']==preparation;groups=data['groups'];audit.pin(preparation_path,sha(preparation_path))
    flattened=[]
    for group in groups:
        if 'before'in group:
            def snapshot(item):
                if isinstance(item,dict):
                    location=item['path'];path=path_for(location)if str(location).startswith(('analysis/','/'))else folder/location
                    audit.pin(path,item['sha256'],item['bytes']);return path
                return folder/item
            old_ram=snapshot(group['before']['RAM']);old_sram=snapshot(group['before']['SRAM'])
            new_ram=snapshot(group['after']['RAM']);new_sram=snapshot(group['after']['SRAM'])
        else:
            old_ram=path_for(group['before_RAM']);old_sram=path_for(group['before_SRAM'])
            new_ram=path_for(group['after_RAM']);new_sram=path_for(group['after_SRAM'])
        old=[bytearray(old_ram.read_bytes()),bytearray(old_sram.read_bytes())]
        assert len(old[0])==2048 and len(old[1])==8192
        group_items=group.get('writes',[item for item in preparation if item['frame']==group['frame']])
        flattened.extend(group_items)
        for item in group_items:
            address=item['address'];data,index=(old[0],address)if address<2048 else(old[1],address-0x6000)
            assert 0<=index<len(data)and data[index]==item['before'],item
            data[index]=item['after']
        assert bytes(old[0])==new_ram.read_bytes()and bytes(old[1])==new_sram.read_bytes()
        for path in(old_ram,old_sram,new_ram,new_sram):audit.pin(path,sha(path))
    if preparation:assert groups,'Controlled preparations need exact before/after RAM/SRAM groups to audit all changed bytes'
    assert flattened==preparation
    return dict(prepared_byte_writes=len(preparation),preparation_frames=sorted({x['frame']for x in preparation}),
        exact_preparation_groups=len(groups),natural_zero_extra_writes=not preparation)


def audit_native(audit):
    from PIL import Image
    folder=OUT/'runtime';e=read(folder/'evidence.json');v=read(folder/'validation.json');passed(e);passed(v)
    assert v['evidence_sha256']==sha(folder/'evidence.json')
    audit.common_pins(e);audit.common_pins(v);audit.raw(e,'native')
    assert not v['native_internal_CPU_trace']and v['source_CPU_comparisons_in_this_receipt']==0
    assert{item['case']for item in e['native_cases']}==NATIVE_CASES
    static_path=folder/'static-validation.json';static=read(static_path)
    assert static['status']=='passed'and static['failed_count']==0
    audit.pin(static_path,sha(static_path));audit.pin(folder/'README.md',sha(folder/'README.md'))
    total=Counter();details=[]
    for manifest in e['native_cases']:
        p=folder/manifest['case'];r=read(p/'validation.json');rep=read(p/'repeat-validation.json');passed(r)
        audit.pin(p/'validation.json',sha(p/'validation.json'));audit.pin(p/'repeat-validation.json',sha(p/'repeat-validation.json'))
        assert rep['status']=='passed'and rep['all_hashes_equal']and r['rom_modified']is False
        assert not r['source_pipeline_installed']and not r['native_internal_CPU_trace']and r['source_CPU_comparisons_in_this_receipt']==0
        audit.common_pins(r,relative_base=p);audit.pin('.toolchain/nestopia/nestopia_libretro.dylib',r['core']['core_sha256'])
        for script,key in [('scripts/capture_campaign_flows.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),
                           ('scripts/nes_runtime.py','original_runtime_sha256'),('scripts/capture_boot_cooperation_flows.py','capture_base_sha256')]:audit.pin(script,r[key])
        assert r['fresh_process_per_run']and not r['battery_file_imported']
        assert r['additional_core_memory_writes_after_declared_preparation']==0 and not r['selected_tactic_result_request_cache_animation_ack_injection']
        prep=audit_preparation(audit,p,r)
        if manifest['case']=='cold-yearwrap':
            assert r['cold_boot']and not r['state_imported']and not r.get('battery_file_imported',False)
            assert not r['preparation']and r['additional_core_memory_writes']==0
        else:
            mother=r.get('initial_state',r.get('mother_state'));mother_sha=r.get('initial_state_sha256',r.get('mother_sha256'))
            assert r['state_imported']and mother and mother_sha
            audit.pin(mother,mother_sha)
            assert(p/'initial.state').read_bytes()==path_for(mother).read_bytes()
            assert r['additional_core_memory_writes']==len(r['preparation'])
        assert r['additional_ready_or_result_injections']==0
        for name,item in r['artifact_sha256'].items():audit.pin(p/name,item['sha256'],item['bytes']);assert item['bytes']>0
        second=path_for(rep['second_run']);assert path_for(rep['first_run']).resolve()==p.resolve()
        assert rep['whole_serialized_buffers_exact']
        assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
        for item in rep['artifacts']:
            one=p/item['artifact'];two=second/item['artifact'];assert item['equal']and item['bytes']>0
            audit.pin(one,item['sha256'],item['bytes']);audit.pin(two,item['sha256'],item['bytes'])
        for name in rep['formal_JSON_exact_parity']:
            assert(p/name).read_bytes()==(second/name).read_bytes()and(p/name).stat().st_size>0
        for name in r['excluded_empty_VRAM']:assert(p/name).stat().st_size==0
        frames=read(p/'frame-services.json');points=read(p/'checkpoints.json');callbacks=read(p/'audio-callbacks.json')
        assert len(frames)==r['frames']and len(points)==r['checkpoint_count']and callbacks
        audio=r['full_audio']
        with wave.open(str(p/'full-flow.wav'),'rb')as stream:
            assert(stream.getnchannels(),stream.getsampwidth(),stream.getframerate(),stream.getnframes())==(2,2,48000,audio['stereo_sample_frames'])
            pcm=stream.readframes(stream.getnframes())
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
            assert 0<=row['emulated_frame_start']<r['frames']
        assert cursor==len(pcm)
        assert sha(p/'initial-ram.bin')==r['initial_RAM_sha256']and sha(p/'initial-sram.bin')==r['initial_SRAM_sha256']
        for point in points:
            row=frames[point['frame']-1]
            assert sha(p/point['RAM'])==row['RAM_sha256']and sha(p/point['SRAM'])==row['SRAM_sha256']
            assert(p/point['RAM']).stat().st_size==2048 and(p/point['SRAM']).stat().st_size==8192 and(p/point['state']).stat().st_size>0
            with Image.open(p/point['image'])as image:
                assert list(image.size)==row['native_dimensions']==[256,240]
                assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
        # Case-specific proof contracts are read from the frozen producer;
        # source/CPU loops above never stand in for a native campaign outcome.
        events=r['campaign_events'];final=r['final_fields']
        assert events==read(p/'campaign-events.json')
        assert(final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase'])==(2,2,0,1)
        if manifest['case']=='cold-yearwrap':
            monthly=[item for item in events if item['kind']=='monthly-return']
            commands=[item for item in events if item['kind']=='accepted-original-recruitment-command']
            assert len(monthly)==12 and len(commands)==36 and[item['ordinal']for item in commands]==list(range(1,37))
            assert final['calendar_and_turn_6F00_6F06'][:2]==[90,0]
            assert[item['calendar'][:2]for item in monthly]==[[89,i]for i in range(1,12)]+[[90,0]]
            assert final['ruler_6F03']==2 and final['remaining_budget_raw_6F05']==3
            assert(p/'initial-sram.bin').read_bytes()==bytes(8192)
            effects=dict(monthly_returns=12,accepted_original_command_cards=36,final_calendar_raw=[90,0],player_budget_replenished=3,
                         some_zero_quantity_commands_are_original_cap_guard_acceptances=True)
        elif manifest['case']=='consecutive-invasions-attack-return':
            retreats=[item for item in events if item['kind']=='original-invasion-retreat-battle-completed']
            damages=[item for item in events if item['kind']=='original-ordinary-attack-object-loss-observed']
            returned=[item for item in events if item['kind']=='original-ordinary-attack-scene-returned']
            assert len(retreats)==2 and[item['battle']for item in retreats]==[1,2]and all(not item['actual_victory_claimed']for item in retreats)
            assert damages and returned and len(r['preparation'])==2
            assert{item['address']for item in r['preparation']}=={0x600,0x614}and all(item['kind']=='RAM'for item in r['preparation'])
            for damage in damages:
                assert damage['active_global']==6 and damage['active_nmi']==4
                assert len(damage['before_object_values'])==len(damage['after_object_values'])==22
                assert any(a<b for a,b in zip(damage['after_object_values'],damage['before_object_values']))
            effects=dict(invasions_ended_by_original_retreat=2,ordinary_attack_object_loss_observations=damages,
                         ordinary_attack_return_observations=returned,two_battles_are_not_two_victories=True)
        else:
            casts=[item for item in events if item['kind']=='original-trap-cast']
            deaths=[item for item in events if item['kind']=='original-record-status3-observed']
            settlement=[item for item in events if item['kind']=='original-inheritance-settlement-observed']
            assert len(casts)==4 and[item['ordinal']for item in casts]==[1,2,3,4]
            assert all(item['result']==0 and item['target_slot_now']==255 for item in casts)
            assert{item['officer_id']for item in deaths}=={8,51,167,191}
            assert all(item['record']['health']==0 and item['record']['status']==3 for item in deaths)
            assert len(settlement)==1;settle=settlement[0];expected_leader=9 if manifest['case']=='succession-heir'else 255
            assert settle['leader_before']==8 and settle['leader_after']==expected_leader and settle['city4_owner']==2
            assert final['rulers'][1]['ID']==expected_leader and final['city_owners'][4]==2
            assert final['campaign_officers']['8']['health']==0 and final['campaign_officers']['8']['status']==3
            for base in(0x600,0x614,0x628,0x63C,0x650,0x664):assert final['unit_arrays'][hex(base)][:4]==[255]*4
            assert r['observed_cooperation_status_values']==[255]
            effects=dict(actual_trap_casts=4,removed_officers=[8,51,167,191],ruler1_leader_after=expected_leader,city4_owner_after=2,
                         original_postbattle_settlement_observed=True,domestic_CA19_or_FB_FC_ack_path_not_proven_by_native=True)
        total.update(frames_first_run=r['frames'],checkpoint_count=r['checkpoint_count'],nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
            formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
            excluded_empty_VRAM=len(r['excluded_empty_VRAM']),excluded_snapshot_metadata_JSON=len(r['excluded_snapshot_metadata_JSON']),
            additional_core_memory_writes=r['additional_core_memory_writes'],state_import_count=int(r['state_imported']),
            cold_boot_case_count=int(r['cold_boot']),controlled_fixture_count=int(r['controlled_fixture']))
        details.append(dict(case=manifest['case'],status='passed',frames=r['frames'],checkpoint_count=r['checkpoint_count'],
            cold_boot=r['cold_boot'],state_imported=r['state_imported'],controlled_fixture=r['controlled_fixture'],preparation=prep,
            verified_effects=effects,effects_derived_from_frozen_campaign_events_and_final_fields=True,
            receipt_path=relative(p/'validation.json'),repeat_receipt_path=relative(p/'repeat-validation.json')))
    for key,value in total.items():assert v[key]==value,(key,value,v[key])
    assert v['frames_both_runs']==2*v['frames_first_run']and v['native_case_count']==len(details)
    assert e['summary']=={key:v[key]for key in e['summary']}
    assert static['decoded_nonempty_RGB_images']==v['checkpoint_count']and static['decoded_WAV_files']==v['native_case_count']
    assert static['artifact_rehash_checks']==sum(len(read(folder/case['case']/'validation.json')['artifact_sha256'])for case in e['native_cases'])
    return dict(**v,cases=details,natural_and_controlled_cases_are_separate=True,
        no_global_zero_write_claim=True,PCM_stereo_sample_frames_both_runs_derived=2*v['PCM_stereo_sample_frames_first_run'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path)
    parser.add_argument('--allow-pending',action='store_true',help='Only missing artifacts may yield pending; stale or failed existing files still fail closed')
    args=parser.parse_args();rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    audit=Audit(rom);missing=[]
    for path in(Path(__file__),ROOT/'scripts/verify_phase13.py',ROOT/'scripts/verify_phase12.py',ROOT/'scripts/package_results.py'):audit.pin(path,sha(path))
    def require(path):
        if path.is_file():return read(path)
        assert args.allow_pending,f'Missing final artifact {relative(path)}'
        missing.append(relative(path));return None
    regressions={}
    for phase in range(5,15):
        path=ROOT/f'analysis/phase{phase}/verification.json';old=read(path);passed(old,production_contract=False)
        for key in('source_and_validator_sha256','artifact_and_dependency_sha256'):
            for name,digest in old.get(key,{}).items():audit.pin(name,digest)
        regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_pins=True)
    areas={};receipts={};evidences={};cpu=guards=complete=prefix=0
    for area,module in MODULES.items():
        folder=OUT/area;r=require(folder/'validation.json');e=require(folder/'evidence.json')
        if r is None or e is None:continue
        passed(r);assert e.get('rom_sha256',e.get('ROM_sha256'))==SHA
        audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
        for name in('static-catalog.json','source-catalog.json','executed-instructions.json','schema.json','initial-records.json','field-accesses.json'):
            path=folder/name
            if path.is_file():data=read(path);audit.common_pins(data,area);audit.raw(data,area);audit.pin(path,sha(path))
        for path in folder.glob('*.asm'):audit.pin(path,sha(path))
        doc=folder/'README.md';assert doc.is_file();audit.pin(doc,sha(doc))
        t,g,c,p=counts(r);body_counts=dict(rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=p)
        semantics=fields_semantics(r)if area=='fields'else None
        if area=='audio-domain':
            genuine=require(GENUINE_AUDIO)
            if genuine is None:continue
            semantics=audio_semantics(r,genuine,audit);gt,gg,gc,gp=counts(genuine)
            t+=gt;g+=gg;c+=gc;p+=gp
            receipts['audio-genuine-call-inputs']=sha(GENUINE_AUDIO)
        cpu+=t;guards+=g;complete+=c;prefix+=p
        areas[area]=dict(status='passed',source_path=f'source/recovered/{module}.py',receipt_path=relative(folder/'validation.json'),evidence_path=relative(folder/'evidence.json'),
            rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=p,
            primary_receipt_counts=body_counts,declared_scope=r.get('scope',r.get('comparison')),completion_and_prefix_semantics=semantics,
            declared_limits=r.get('limits',e.get('limitations',[])))
        receipts[area]=sha(folder/'validation.json');evidences[area]=sha(folder/'evidence.json')
    for pair in(10,14,25,27):audit.archive(f'analysis/rea/pairs/pair-{pair:02d}')
    ast_paths=[ROOT/'source/recovered/record_fields.py',ROOT/'source/recovered/audio_scene_services.py',ROOT/'source/recovered/campaign_session.py',ROOT/'source/recovered/scene_coordinator.py']
    ast_checks=source_AST(ast_paths)
    for path in ast_paths:audit.pin(path,sha(path))
    integration=require(INTEGRATION);integration_info=None;t=g=c=p=0
    if integration is not None:
        integration_info=audit_integration(audit,integration);t,g,c,p=counts(integration)
        receipts['source-integration']=sha(INTEGRATION)
    runtime=None;ne=require(OUT/'runtime/evidence.json');nr=require(OUT/'runtime/validation.json')
    if ne is not None and nr is not None:
        runtime=audit_native(audit);receipts['native']=sha(OUT/'runtime/validation.json');evidences['native']=sha(OUT/'runtime/evidence.json')
    for doc in('README.md','source/README.md','analysis/index.html','analysis/phase15/README.md'):
        path=ROOT/doc
        if path.is_file():audit.pin(path,sha(path))
        else:assert args.allow_pending;missing.append(doc)
    for script in('scripts/write_phase15_report.py',):
        path=ROOT/script
        if path.is_file():audit.pin(path,sha(path))
        else:assert args.allow_pending;missing.append(script)
    static_path=OUT/'browser-static-validation.json';static=require(static_path)
    if static is not None:
        assert static['status']=='passed'and static['JS_syntax']=='passed'and not static['native_files_modified']
        assert static['HTML_sha256']==sha(OUT/'index.html')
        builder=static.get('generator_path','scripts/build_phase15_browser.py');audit.pin(builder,static['generator_sha256'])
        if 'template_generator_sha256'in static:audit.pin('scripts/build_phase14_browser.py',static['template_generator_sha256'])
        audit.pin(OUT/'runtime/evidence.json',static['native_evidence_sha256'])
        assert static['final_required']and static['integration']['status']=='passed'and static['integration']['current_pins_match']
        assert{item['key']for item in static['modules']}=={'fields','audio-domain','session'}
        for item in static['modules']:
            if item['key']=='session':
                expected=counts(read(OUT/'session/validation.json'))
            else:
                row=areas[item['key']]['primary_receipt_counts']
                expected=(row['rom_cpu_case_count'],row['source_guard_case_count'],row['complete_return_CPU_cases'],row['strict_prefix_CPU_cases'])
            assert(item['CPU'],item['guards'],item['complete'],item['prefix'])==expected
            assert item['verification_CPU_callbacks']==item['production_CPU_callbacks']==0
        if runtime is not None:
            qa=static['native_static_QA']
            assert qa['nonempty_double_run_artifacts']==runtime['nonempty_repeat_artifact_checks']
            assert qa['formal_JSON_exact_parity']==runtime['formal_JSON_repeat_checks']
            assert qa['same_frame_PNG_RAM_SRAM_state']==runtime['checkpoint_count']
            assert qa['frame_PCM_segments']==runtime['frames_first_run']and qa['WAV_header_PCM_hash']==runtime['native_case_count']
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
            if isinstance(item.get('src'),str)and'?'in item['src']:
                url=urlsplit(item['src']);expected=parse_qs(url.query).get('sha')
                if expected:
                    file=ROOT/unquote(url.path.lstrip('/'))if url.path.startswith('/analysis/')else OUT/unquote(url.path)
                    audit.pin(file,expected[0])
        audit.pin(browser_path,sha(browser_path))
    if(OUT/'index.html').exists():audit.pin(OUT/'index.html',sha(OUT/'index.html'))
    result=dict(schema='phase15-read-only-source-native-aggregate-v1',status='passed'if not missing else'pending_dependencies',rom_sha256=SHA,missing_required_artifacts=missing,
        rom_cpu_case_count=cpu,source_guard_case_count=guards,total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=prefix,areas=areas,
        source_integration_receipt_path=relative(INTEGRATION),source_integration_ROM_CPU_cases=t,source_integration_guard_cases=g,
        source_integration_complete_return_CPU_cases=c,source_integration_strict_prefix_CPU_cases=p,source_integration=integration_info,
        source_integration_completion_kinds=integration_info['completion_kinds']if integration_info else None,
        source_integration_main_boundary_CPU_cases=integration_info['completion_kinds'].get('main_E066_boundary',0)if integration_info else 0,
        source_integration_actual_interrupt_RTI_CPU_cases=integration_info['completion_kinds'].get('actual_interrupt_RTI',0)if integration_info else 0,
        source_integration_actual_caller_RTS_CPU_cases=integration_info['completion_kinds'].get('actual_caller_RTS',0)if integration_info else 0,
        integration_rom_cpu_case_count=t,integration_source_guard_case_count=g,all_CPU_cases_including_integration=cpu+t,
        all_source_guards_including_integration=guards+g,all_complete_return_CPU_cases_including_integration=complete+c,all_strict_prefix_CPU_cases_including_integration=prefix+p,
        source_and_validator_sha256={path:h for path,h in audit.pins.items()if path.startswith(('source/','scripts/'))},
        artifact_and_dependency_sha256={path:h for path,h in audit.pins.items()if not path.startswith(('source/','scripts/'))},
        receipt_sha256=receipts,evidence_sha256=evidences,raw_object_count=audit.raw_count,raw_bytes_checked=audit.raw_bytes,REA_archives=audit.archives,
        source_AST=ast_checks,rebuilt_byte_identical=True,regressions=regressions,native_evidence_path=relative(OUT/'runtime/evidence.json'),native=runtime,
        browser_static_receipt_path=relative(static_path),browser_static_receipt_sha256=sha(static_path)if static is not None else None,
        browser_receipt_sha256=sha(browser_path)if browser is not None else None,browser_status=browser['status']if browser else'pending',
        limitations=['Field2449 prefixes stop at explicit field/parent-work or missing-service boundaries; they are not complete parent functions.',
            'Audio1631 body and20 distinct genuine callee comparisons are counted once; original context preparation steps/NMI arrivals are not extra cases.',
            'CampaignSession is only a source-integration child; its nested software stages and succession241/481NMIarrivals are not added again.',
            'Declared complete comparison categories may be main-E066/RTI boundaries rather than RTS; per-row completion kinds are retained.',
            'Natural cold12-month and imported/controlled battle/succession native preparations are distinguished percase; no globalzero-write claim.',
            'Source services issue software/port effects, not native hardware timing, RGB or PCM synthesis. Originalcore media are separate evidence.',
            'The original ROM, frozenNative and older versionedZIPs remain immutable; root legitimately reruns current old5..14 audits/integration for changed source pins. This auditor never executes CPU/core/IR.'])
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','rom_cpu_case_count','source_guard_case_count','all_CPU_cases_including_integration','browser_status','missing_required_artifacts')},ensure_ascii=False))

if __name__=='__main__':main()
