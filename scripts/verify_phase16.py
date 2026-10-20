#!/usr/bin/env python3
"""Read-only, fail-closed phase16 source/CPU/native/browser aggregate.

Five primary modules, nineteen independent genuine audio callers, and twenty
four root integration parents are counted once. No originalCPU, control IR or
native core executes here. Missing browser artifacts alone can yield a pending
preview; stale/failed evidence and missing non-browser files always fail.
An explicit current-parent bridge retains immutable historical source hashes
using exact portable bytecopies; it never relabels history as a new CPU run.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit,parse_qs,unquote
import argparse,hashlib,json,sys,wave,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from verify_phase12 import source_AST,objects,path_for,relative,sha,read
from verify_phase15 import Audit as EarlierAudit,counts,passed
OUT=ROOT/'analysis/phase16'
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={'fields':'field_semantics','succession':'battle_succession','audio-requests':'exact_audio_requests','graphics':'postbattle_graphics','loyalty':'postbattle_loyalty_bridge'}
INTEGRATION=OUT/'source-integration.json'
GENUINE_AUDIO=OUT/'audio-requests/actual-callers.json'
NATIVE_CASES={'heir-city13-month','no-heir-city13-month','player-defeat-successor','affinity-pages'}

class Audit(EarlierAudit):
    def __init__(self,rom):
        super().__init__(rom);self.metadata_range_corrections=[]
    def raw(self,data,area):
        rows=[]
        for item in objects(data):
            if 'raw_hex'not in item:continue
            row=dict(item);offset=row.get('rom_offset');raw=bytes.fromhex(row['raw_hex'])
            if isinstance(offset,int)and self.rom[offset:offset+len(raw)]!=raw and isinstance(row.get('call_pc'),int):
                bank=row.get('physical_bank',row.get('bank'));call=row['call_pc']
                assert offset==16+bank*8192+(call&8191)
                assert len(raw)>=5 and raw[0]==0xA0 and raw[2]==0x20 and self.rom[offset]==0x20
                assert self.rom[offset-2:offset-2+len(raw)]==raw
                correction=dict(area=area,kind='frozen_call_metadata_with_LDY_context',call_pc=call,
                    declared_call_rom_offset=offset,context_start_cpu=call-2,context_start_rom_offset=offset-2,
                    raw_hex=row['raw_hex'],reason='call_pc/file describe the original JSR; raw_hex includes the preceding two-byte LDY selector context')
                self.metadata_range_corrections.append(correction)
                row['rom_offset']=offset-2;row['cpu']=call-2
            rows.append(row)
        super().raw(rows,area)
    def common_pins(self,data,area=None,relative_base=None):
        def resolve(path):
            p=Path(path)
            if relative_base is not None and not p.is_absolute()and not str(p).startswith(('analysis/','source/','scripts/','.toolchain/','build/')):return relative_base/p
            return path
        maps=('pins','source_sha256','dependencies','dependency_source_sha256','source_and_validator_sha256',
              'source_and_analyzer_pins','REA_archive_pins','source_dependency_pins','dependency_pins',
              'native_input_sha256','artifact_sha256','source_and_analyzer_sha256','artifact_and_dependency_sha256','parent_snapshot_sha256')
        for item in objects(data):
            if isinstance(item.get('path'),str)and isinstance(item.get('sha256'),str):self.pin(resolve(item['path']),item['sha256'],item.get('bytes'))
            for key in maps:
                if isinstance(item.get(key),dict):
                    for path,digest in item[key].items():
                        if isinstance(digest,str):self.pin(resolve(path),digest)
                        elif isinstance(digest,dict)and isinstance(digest.get('sha256'),str):self.pin(resolve(path),digest['sha256'],digest.get('bytes'))
        if not isinstance(data,dict):return
        module=MODULES.get(area,'game_engine')
        for key,path in [('source_sha256',data.get('source_path',f'source/recovered/{module}.py')),
                         ('validator_sha256',data.get('validator_path',f'scripts/verify_{module}.py')),
                         ('analyzer_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py'))]:
            if isinstance(data.get(key),str):self.pin(path,data[key])


def field_semantics(receipt,audit):
    rows=receipt['rows'];prefix=[r for r in rows if r['comparison']=='strict_prefix']
    assert counts(receipt)==(2537,10,2280,257)
    assert all(r['all_RAM_byte_count']==2048 and r['all_SRAM_byte_count']==8192 for r in rows)
    assert all(r['completion_kind']=='actual_caller_RTS'and r['source_status']=='returned'for r in rows if r['comparison']=='complete_return')
    for r in prefix:
        if r['entry']==0xB64D:assert r['final_registers']['pc']==0xB663 and r['final_registers']['sp']==r['input_registers']['sp']and r['source_status']=='bounded_prefix'
        else:assert r['entry']==0xA7E7 and r['final_registers']['pc']==0xF2D7 and r['source_status']=='dependency'
    review=read(OUT/'fields/city-tail-candidate-review.json');initial=read(OUT/'fields/initial-records.json');schema=read(OUT/'fields/schema.json')
    assert review['remaining_possible_dedicated_alias_count']==647
    assert len(review['remaining_known_city_pointer_unknown_Y'])==72 and len(review['remaining_pointer_or_shifted_index_unresolved'])==575
    assert len(initial['officers'])==237 and initial['initial_affinity_counts']=={'1':70,'0':111,'2':56}
    assert [r['id']for r in initial['copied_adjacent_pseudo_slots']]==[237,238,239]and all(r['affinity']==3 and not r['valid_officer']for r in initial['copied_adjacent_pseudo_slots'])
    assert schema['officer_affinity']['codes'][3]['official_glyph']is None
    portable_path=OUT/'fields/provenance/manifest.json';manifest=read(portable_path)
    assert manifest['schema']=='phase16-portable-field-provenance-v1'and manifest['copy_count']==4 and manifest['copied_bytes']==364407
    assert manifest['originals_are_provenance_locations_not_portable_dependencies']is True
    audit.pin(portable_path,sha(portable_path));portable=[]
    atlas_path=OUT/'fields/all-bank-instruction-atlas.json';atlas=read(atlas_path)
    audit.pin(atlas_path,sha(atlas_path))
    decoded={(r['physical_bank'],r['cpu']):r for r in atlas['instructions']}
    seed_count=0
    for item in manifest['copies']:
        original=path_for(item['original_path']);copy=path_for(item['portable_path'])
        assert any(part.startswith('exploratory')for part in Path(item['original_path']).parts)
        assert not any(part.startswith('exploratory')for part in Path(item['portable_path']).parts)
        audit.pin(copy,item['sha256'],item['bytes']);seeds=read(copy)
        assert isinstance(seeds,list)
        for seed in seeds:
            bank=seed['physical_bank'];pc=seed['cpu_address'];offset=seed['rom_offset']
            assert 0<=bank<32 and 0x8000<=pc<=0xFFFF and offset==16+bank*8192+(pc&8191)
            instruction=decoded[(bank,pc)]
            assert instruction['rom_offset']==offset and item['portable_path']in instruction['sources']
            audit.raw([instruction],'fields/portable-seed-original-bytes')
        seed_count+=len(seeds)
        # An extracted archive need not include the excluded source directory.
        # The exact retained bytecopy remains independently pinned and checked.
        if original.is_file():assert original.read_bytes()==copy.read_bytes()
        portable.append(dict(original_path=item['original_path'],portable_path=item['portable_path'],sha256=item['sha256'],bytes=item['bytes'],instruction_seed_rows=len(seeds)))
    assert len(portable)==4 and sum(p['bytes']for p in portable)==364407 and seed_count==4001
    return dict(actual_caller_RTS_cases=2280,explicit_lower_glyph_prefix_cases=256,missing_F2D7_prefix_cases=1,
        copied_adjacent_pseudo_slots_are_not_legal_officers=[237,238,239],unresolved_city_alias_candidates=647,
        portable_provenance_manifest_path=relative(portable_path),portable_original_seed_copies=portable,
        portable_seed_original_ROM_byte_comparisons=seed_count,
        city_byte1_and_tail_have_no_proven_official_names=True,fixture_domains=receipt['fixture_domains'])


def genuine_audio(audit,receipt):
    passed(receipt);assert counts(receipt)==(19,0,19,0)
    assert receipt['native_internal_CPU_trace']is False and receipt['parent_case_count_not_added']==1
    audit.common_pins(receipt,'audio-requests');inputs=[]
    for row in receipt['rows']:
        assert row['comparison']=='complete_return'and row['completion_kind']=='actual_caller_RTS'
        prefix=path_for(row['input']);meta_path=Path(str(prefix)+'.json');meta=read(meta_path)
        ram_path=Path(str(prefix)+'-ram.bin');sram_path=Path(str(prefix)+'-sram.bin');ram=ram_path.read_bytes()
        assert len(ram)==2048 and sram_path.stat().st_size==8192 and meta['registers']==row['initial_registers']
        sp=meta['registers']['sp'];word=ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8
        assert((word+1)&65535)==meta['return_PC']==row['final_registers']['pc']
        assert((sp+2)&255)==meta['return_SP']==row['final_registers']['sp']
        assert meta['call_pc']==row['caller_PC']and row['entry']in(0xE57F,0xE590,0xE5F3,0xE5FA,0xE609,0xE673,0xE683)
        for path in(meta_path,ram_path,sram_path):audit.pin(path,sha(path))
        parent=path_for(meta['source_parent']);audit.pin(parent,sha(parent))
        inputs.append(dict(path=relative(meta_path),entry=row['entry'],caller_PC=row['caller_PC'],actual_return_PC=meta['return_PC'],actual_return_SP=meta['return_SP']))
    assert len({r['path']for r in inputs})==19
    return dict(ROM_CPU_cases=19,actual_caller_RTS_cases=19,receipt_path=relative(GENUINE_AUDIO),genuine_callee_inputs=inputs,
        originalCPU_context_preparation_steps_not_extra_cases=True,native_internal_CPU_trace=False)


def integration_semantics(audit,r):
    passed(r);audit.common_pins(r);assert counts(r)==(24,3,24,0)
    assert r['source_original_CPU_callbacks']==0 and r['comparison']['RAM_bytes']==2048 and r['comparison']['SRAM_bytes']==8192
    kinds=Counter(row['completion_kind']for row in r['rows']);assert dict(kinds)==r['completion_kinds']
    assert kinds==Counter({'actual_caller_RTS':22,'main_E066_and_actual_interrupt_RTI_sequence':2})
    sequences=[]
    for row in r['rows']:
        assert row['RAM_bytes']==2048 and row['SRAM_bytes']==8192
        if row['completion_kind']=='actual_caller_RTS':
            p=path_for(row['input_path']);audit.pin(p,sha(p))
            assert row['source_call_API']=='SceneCoordinator(actual_ServiceCall)'
        else:
            assert row['idle_stack_exclusion']is None and row['same_register_context']and row['manual_ack_or_ready_writes']==0
            assert row['all_event_RAM_SRAM_register_port_bank_N163_comparisons_equal']and row['nested_events_not_extra_CPU_cases']
            assert row['final_leader']==(9 if row['case']=='succession-heir'else 255)
            sequences.append(dict(case=row['case'],main_updates=row['main_updates'],NMI_arrivals=row['explicit_NMI_arrivals'],IRQ_arrivals=row['explicit_IRQ_arrivals'],
                completion_kind=row['completion_kind'],counted_parent_CPU_cases=1))
    return dict(status='passed',receipt_path=relative(INTEGRATION),ROM_CPU_cases=24,guards=3,completion_kinds=dict(kinds),
        genuine_city13_caller_RTS_cases=22,same_campaign_source_sequences=sequences,nested_events_not_added_to_CPU_count=True,source_original_CPU_callbacks=0)

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
        for script,key in [('scripts/capture_succession_flows.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),
                           ('scripts/nes_runtime.py','original_runtime_sha256'),('scripts/capture_campaign_flows.py','capture_base_sha256')]:audit.pin(script,r[key])
        assert r['fresh_process_per_run']and not r['battery_file_imported']
        assert r['additional_core_memory_writes_after_declared_preparation']==0 and not r['selected_tactic_result_request_cache_animation_ack_injection']
        prep=audit_preparation(audit,p,r)
        assert not r['cold_boot']and r['state_imported']
        if r['state_imported']:
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
            assert row['all30_city_byte1']==[0]*30
            tail=row['all30_city_bytes28_31']
            assert len(tail)==30 and all(isinstance(value,str)and value=='00000000'for value in tail)
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
        inherited=r['inherited_context'];assert inherited['applied_in_this_run']is False
        assert inherited['inherited_preparation_byte_writes']==len(inherited['preparation'])
        audit.pin(inherited['validation'],inherited['validation_sha256'])
        prior=read(path_for(inherited['validation']))
        if inherited['preparation']:assert prior['preparation']==inherited['preparation']
        events=r['campaign_events'];final=r['final_fields'];effects=r['verified_effects']
        assert events==read(p/'campaign-events.json')
        assert effects==manifest['verified_effects']and inherited==manifest['inherited_context']
        if manifest['case']in('heir-city13-month','no-heir-city13-month'):
            assert not r['preparation']and r['additional_core_memory_writes']==0
            expected=9 if manifest['case']=='heir-city13-month'else 255
            assert inherited['controlled_fixture']and inherited['inherited_preparation_byte_writes']==(19 if expected==9 else 26)
            assert effects['actual_city13_consumer']and effects['actual_ruler1_before']==8 and effects['actual_ruler1_after']==expected
            assert effects['calendar_before']==[89,0]and effects['calendar_after']==[89,1]
            assert effects['AI_rulers_observed']==([0,1,3,4,5,6]if expected==9 else[0,3,4,5,6])
            assert effects['intermediate_FC_FB_ack1_observed']is False
            assert final['rulers'][1]['ID']==expected and final['calendar_and_turn_6F00_6F06'][:2]==[89,1]
            assert(final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase'])==(2,2,0,1)
            assert any(e['kind']=='original-city13-consumer-ruler-writeback'for e in events)
            assert any(e['kind']=='original-post-succession-month-return'for e in events)
        elif manifest['case']=='player-defeat-successor':
            assert len(r['preparation'])==5 and not inherited['controlled_fixture']and inherited['inherited_preparation_byte_writes']==0
            assert effects['actual_original_attack']and effects['health_FF_preserved_not_normalized']
            assert effects['player_ruler_before']==131 and effects['player_ruler_after']==5 and effects['chosen_owned_city']==11
            assert effects['player_record_131_after']['health']==255 and effects['player_record_131_after']['status']==3
            assert final['rulers'][2]['ID']==5 and final['campaign_officers']['131']['health']==255 and final['campaign_officers']['131']['status']==3
            assert(final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase'])==(2,2,0,1)
        else:
            assert len(r['preparation'])==4 and inherited['inherited_preparation_byte_writes']==0
            assert effects['actual_four_original_information_open_close_cycles']and effects['tier_and_status_preserved']
            assert effects['packed_values']==[0x12,0x16,0x1A,0x1E]and effects['code3_official_name']is None
            assert effects['code3_out_of_table_bytes_top']==[0xA0,0x0B]and effects['code3_out_of_table_bytes_bottom']==[0x4A,0x4A]
            hashes=[]
            for region in effects['affinity_glyph_regions']:
                point=next(x for x in points if x['label']==region['checkpoint']);code=region['code']
                with Image.open(p/region['PNG'])as image:
                    crop=image.convert('RGB').crop(region['box']);assert list(crop.size)==[16,16]
                    assert hashlib.sha256(crop.tobytes()).hexdigest()==region['RGB_sha256']
                assert sha(p/region['PNG'])==region['PNG_sha256'];hashes.append(region['RGB_sha256'])
                data=(p/point['SRAM']).read_bytes();assert((data[0x69EF-0x6000]>>2)&3)==code
                assert point['fields']['UI_row_040D']==255
                start=r['preparation'][code]['frame'];progress={row['UI_row_040D']for row in frames[start:point['frame']]}
                assert set(range(10))|{255}<=progress
            assert len(set(hashes))==4 and effects['actual_completed_pages_row040D']==255
            assert(final['global_state'],final['nmi_scene'],final['active_main'],final['active_phase'])==(4,3,0,2)
        total.update(frames_first_run=r['frames'],checkpoint_count=r['checkpoint_count'],nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
            formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
            excluded_empty_VRAM=len(r['excluded_empty_VRAM']),excluded_snapshot_metadata_JSON=len(r['excluded_snapshot_metadata_JSON']),
            additional_core_memory_writes=r['additional_core_memory_writes'],state_import_count=int(r['state_imported']),
            inherited_preparation_byte_writes=inherited['inherited_preparation_byte_writes'])
        details.append(dict(case=manifest['case'],status='passed',frames=r['frames'],checkpoint_count=r['checkpoint_count'],
            cold_boot=r['cold_boot'],state_imported=r['state_imported'],controlled_fixture=r['controlled_fixture'],preparation=prep,
            verified_effects=effects,inherited_context=inherited,
            receipt_path=relative(p/'validation.json'),repeat_receipt_path=relative(p/'repeat-validation.json')))
    for key,value in total.items():assert v[key]==value,(key,value,v[key])
    assert v['frames_both_runs']==2*v['frames_first_run']and v['native_case_count']==len(details)
    assert e['summary']=={key:v[key]for key in e['summary']}
    assert static['decoded_nonempty_RGB_images']==v['checkpoint_count']and static['decoded_WAV_files']==v['native_case_count']
    assert static['artifact_rehash_checks']==sum(len(read(folder/case['case']/'validation.json')['artifact_sha256'])for case in e['native_cases'])
    return dict(**v,cases=details,natural_and_controlled_cases_are_separate=True,
        city_auxiliary_observation=dict(frame_count=v['frames_first_run'],city_count=30,byte1_all_zero=True,
            tails28_31_all_raw_hex_zero=True,scope='These four frozen Native flows only; zero values do not prove absence of readers/writers, unused bytes or official reserved status'),
        no_global_zero_write_claim=True,PCM_stereo_sample_frames_both_runs_derived=2*v['PCM_stereo_sample_frames_first_run'])



def browser_checks(audit,areas,runtime,allow_pending):
    missing=[]
    def required(path):
        if path.is_file():return read(path)
        assert allow_pending,f'Missing required browser artifact {relative(path)}'
        missing.append(relative(path));return None
    static_path=OUT/'browser-static-validation.json';static=required(static_path)
    if static is not None:
        assert static['status']=='passed'and static['JS_syntax']=='passed'and not static['native_files_modified']
        assert static['HTML_sha256']==sha(OUT/'index.html')and static['native_evidence_sha256']==sha(OUT/'runtime/evidence.json')
        assert static['final_required']and static['integration']['status']=='passed'and static['integration']['current_pins_match']
        assert{r['key']for r in static['modules']}==set(MODULES)
        for r in static['modules']:
            expected=areas[r['key']]['primary_receipt_counts']
            assert(r['CPU'],r['guards'],r['complete'],r['prefix'])==(expected['rom_cpu_case_count'],expected['source_guard_case_count'],expected['complete_return_CPU_cases'],expected['strict_prefix_CPU_cases'])
            assert r['verification_CPU_callbacks']==r['production_CPU_callbacks']==0
        qa=static['native_static_QA']
        assert qa['nonempty_double_run_artifacts']==runtime['nonempty_repeat_artifact_checks']and qa['formal_JSON_exact_parity']==36
        assert qa['same_frame_PNG_RAM_SRAM_state']==251 and qa['frame_PCM_segments']==17581 and qa['audio_callback_segments']==17581
        assert qa['WAV_header_PCM_hash']==4 and qa['preparation_group_checks']==5 and qa['affinity_glyph_region_checks']==4
        audit.pin('scripts/build_phase16_browser.py',static['generator_sha256'])
        if'template_generator_sha256'in static:audit.pin('scripts/build_phase14_browser.py',static['template_generator_sha256'])
        audit.pin(static_path,sha(static_path))
    browser_path=OUT/'browser-validation.json';browser=required(browser_path)
    if browser is not None:
        assert browser['status']=='passed'and browser.get('html_sha256',browser.get('HTML_sha256'))==sha(OUT/'index.html')
        assert all(browser.get('checks',{}).values())and not browser.get('console_errors',[])
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
    return static_path,static,browser_path,browser,missing


def current_parent_regression(audit,current_path):
    """Bridge immutable phase16 history to the actually rerun phase17 batch.

    No originalCPU or source body executes. Missing portable historical
    bytes may be copied once from the independently hash-checked v16 ZIP;
    thereafter the archive is provenance, not a portable required dependency.
    """
    history_path=OUT/'parent-regression.json';history=read(history_path)
    current_path=path_for(current_path);current=read(current_path)
    assert current_path.resolve()!=history_path.resolve()
    assert history['schema']=='phase16-current-source-actual-parent-regression-v1'
    assert current['schema']=='phase17-current-source-real-CPU-parent-regression-v1'
    for record,total in((history,20),(current,32)):
        assert record['status']=='passed'and record['ROM_sha256']==SHA and record['ROM_unchanged']is True
        assert record['planned_commands']==record['completed_commands']==total
        assert record['failed_commands']==0 and record['failures']==[]and record['source_changes']==[]
        assert len(record['rows'])==total and record['quick_or_scope_bypass_flags_used']is False
        assert record['native_core_replays_run']==record['readonly_audits_run']==0
        assert len({row['label']for row in record['rows']})==total
        for row in record['rows']:
            assert row['status']=='passed'and row['exit_code']==0
            command=row['command'];assert isinstance(command,list)and len(command)>=2
            assert command[1].startswith('scripts/')and command[1].endswith('.py')
            assert not{'--quick','--base-only','--catalog-only','--allow-pending-browser'}&set(command)
            if'--register-contract'in command:assert command[command.index('--register-contract')+1]=='exact'
    assert history['source_count']==76 and len(history['source_sha256'])==76
    actual_sources={relative(path):sha(path)for path in sorted((ROOT/'source/recovered').glob('*.py'))}
    assert len(actual_sources)==79 and current['source_sha256']==actual_sources,'Current parent must pin the entire actual79-file source set'
    assert set(history['source_sha256'])<=set(actual_sources)
    correspondences=[]
    for index,(old,new)in enumerate(zip(history['rows'],current['rows'][:20])):
        for key in('label','command','CPU_parent_case_count','source_guard_count','counts','is_original_CPU_execution'):
            assert old[key]==new[key],(index,key,'Historical/current replay contract differs')
        correspondences.append(dict(label=old['label'],historical_command_index=index+1,current_command_index=index+1,
            CPU_parent_case_count=new['CPU_parent_case_count'],source_guard_count=new['source_guard_count'],
            identical_command_case_and_guard_contract=True))
    for row in current['rows']:
        path=path_for(row['receipt']);assert path.resolve().is_relative_to((ROOT/'analysis').resolve())
        audit.pin(path,row['receipt_sha256']);receipt=read(path)
        assert receipt['status']=='passed'and not receipt.get('quick',False)
        assert not receipt.get('failures')and receipt.get('failed_count',0)==0
        count=next((receipt[k]for k in('actual_ROM_CPU_comparison_count','actual_ROM_comparison_count','rom_cpu_case_count')if k in receipt),None)
        guards=next((receipt[k]for k in('source_guard_case_count','source_guard_count','source_contract_check_count')if k in receipt),None)
        assert count==row['CPU_parent_case_count']and guards==row['source_guard_count'],row['label']
        assert receipt.get('counts')==row['counts'],row['label']
    current_log=current_path.parent/'parent-regression.log'
    audit.pin(current_log,current['log_sha256'])
    audit.pin(current_path,sha(current_path));audit.common_pins(current)
    audit.pin(history_path,sha(history_path))
    portable_root=ROOT/'analysis/phase17/regression/phase16-historical-source'
    archive=ROOT/'build/三国志2超级版-逆向分析-v16.zip'
    archive_key=relative(archive)
    archive_hash=current['old_ZIP_sha256_before'][archive_key]
    assert current['old_ZIP_sha256_after'][archive_key]==archive_hash and current['old_ZIPs_unchanged']is True
    proofs=[];extracted=[]
    for name,digest in history['source_sha256'].items():
        source=Path(name)
        assert not source.is_absolute()and source.parts[:2]==('source','recovered')and'..'not in source.parts
        if actual_sources[name]==digest:
            audit.pin(source,digest)
            proofs.append(dict(historical_source_path=name,historical_digest=digest,
                               validated_byte_location=name,changed_since_historical_run=False))
            continue
        copy=portable_root/source
        if not copy.is_file():
            assert archive.is_file()and sha(archive)==archive_hash,'Historical source extraction requires the immutable originalv16 bytes'
            with zipfile.ZipFile(archive)as versioned:
                assert source.as_posix()in versioned.namelist()
                raw=versioned.read(source.as_posix())
            assert hashlib.sha256(raw).hexdigest()==digest,(name,'Archived source does not prove historical pin')
            copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(raw)
            extracted.append(relative(copy))
        audit.pin(copy,digest)
        proofs.append(dict(historical_source_path=name,historical_digest=digest,
                           validated_byte_location=relative(copy),changed_since_historical_run=True,
                           archive_provenance_path=archive_key,archive_provenance_digest=archive_hash,
                           archive_is_required_portable_dependency=False))
    assert len(proofs)==76
    return current_path,dict(mode='explicit_current_parent_replay_bridge',
        current_parent_regression_receipt_path=relative(current_path),current_parent_commands=32,
        current_production_source_file_count=79,current_log_path=relative(current_log),
        immutable_historical_parent_receipt_path=relative(history_path),immutable_historical_receipt_digest=sha(history_path),
        historical_parent_commands=20,historical_source_file_count=76,
        historical_first20_replay_correspondences=correspondences,historical_source_byte_proofs=proofs,
        portable_historical_sources_extracted_this_audit=extracted,
        current_all32_receipt_hashes_verified=True,history_is_not_relabelled_as_current_run=True,
        originalCPU_or_native_replays_executed_by_this_audit=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--allow-pending-browser',action='store_true',help='Only missing browser acceptance may produce pending; all other artifacts and existing hashes remain mandatory')
    p.add_argument('--current-parent-regression',type=Path,help='Explicitly bridge unchanged historical20-command record to actual current32-command replay, with portable exact historical source proof')
    args=p.parse_args();rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    audit=Audit(rom)
    for name in('scripts/verify_phase16.py','scripts/verify_phase15.py','scripts/verify_phase13.py','scripts/verify_phase12.py',
                 'scripts/package_results.py','scripts/write_phase16_report.py','scripts/validate_phase16_package.py'):
        path=ROOT/name;audit.pin(path,sha(path))
    regressions={}
    for phase in range(5,16):
        path=ROOT/f'analysis/phase{phase}/verification.json';old=read(path);passed(old,production_contract=False)
        for key in('source_and_validator_sha256','artifact_and_dependency_sha256'):
            for name,digest in old.get(key,{}).items():audit.pin(name,digest)
        audit.pin(path,sha(path));regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_pins=True)
    parent_bridge=None
    if args.current_parent_regression is None:
        parent_path=OUT/'parent-regression.json';parents=read(parent_path)
        audit.pin(parent_path,sha(parent_path));audit.common_pins(parents)
    else:
        parent_path,parent_bridge=current_parent_regression(audit,args.current_parent_regression)
    areas={};receipts={};evidences={};cpu=guards=complete=prefix=0
    for area,module in MODULES.items():
        folder=OUT/area;r=read(folder/'validation.json');e=read(folder/'evidence.json');passed(r)
        assert e.get('rom_sha256',e.get('ROM_sha256'))==SHA
        audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
        for path in folder.glob('*.json'):
            if path.name in('validation.json','evidence.json','actual-callers.json'):continue
            data=read(path);audit.common_pins(data,area);audit.raw(data,f'{area}/{path.name}');audit.pin(path,sha(path))
        for path in folder.glob('*.asm'):audit.pin(path,sha(path))
        doc=folder/'README.md';assert doc.is_file();audit.pin(doc,sha(doc))
        t,g,c,s=counts(r);base=dict(rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=s)
        semantics=field_semantics(r,audit)if area=='fields'else None
        if area!='fields':
            comparison=r['comparison'];assert comparison['RAM_bytes']==2048 and comparison['SRAM_bytes']==8192
        if area=='audio-requests':
            genuine=read(GENUINE_AUDIO);semantics=dict(body_counts=base,genuine_audio=genuine_audio(audit,genuine))
            gt,gg,gc,gp=counts(genuine);t+=gt;g+=gg;c+=gc;s+=gp
            receipts['audio-genuine-call-inputs']=sha(GENUINE_AUDIO)
        cpu+=t;guards+=g;complete+=c;prefix+=s
        areas[area]=dict(status='passed',source_path=f'source/recovered/{module}.py',receipt_path=relative(folder/'validation.json'),evidence_path=relative(folder/'evidence.json'),
            rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=s,primary_receipt_counts=base,
            declared_scope=r.get('scope',r.get('comparison')),completion_and_prefix_semantics=semantics,declared_limits=r.get('limits',e.get('limitations',[])))
        receipts[area]=sha(folder/'validation.json');evidences[area]=sha(folder/'evidence.json')
    assert(cpu,guards,complete,prefix)==(12679,51,12418,261)
    for pair in(8,10,12,14,23,25,27,29):audit.archive(f'analysis/rea/pairs/pair-{pair:02d}')
    paths=[ROOT/f'source/recovered/{module}.py'for module in MODULES.values()]+[ROOT/'source/recovered/scene_coordinator.py',ROOT/'source/recovered/campaign_session.py']
    ast_checks=source_AST(paths)
    for path in paths:audit.pin(path,sha(path))
    integration=read(INTEGRATION);integration_info=integration_semantics(audit,integration);t,g,c,s=counts(integration)
    receipts['source-integration']=sha(INTEGRATION)
    integrated_positions=OUT/'integration-executed-instructions.json'
    audit.pin(integrated_positions,sha(integrated_positions));audit.raw(read(integrated_positions),'source-integration')
    runtime=audit_native(audit)
    assert(runtime['frames_first_run'],runtime['frames_both_runs'],runtime['checkpoint_count'],runtime['nonempty_repeat_artifact_checks'])==(17581,35162,251,1076)
    assert runtime['additional_core_memory_writes']==9 and runtime['inherited_preparation_byte_writes']==45 and runtime['formal_JSON_repeat_checks']==36
    receipts['native']=sha(OUT/'runtime/validation.json');evidences['native']=sha(OUT/'runtime/evidence.json')
    # Root's report is frozen before browser/audit. Do not create a rootREADME
    # or analysis/index generationcycle by pinning intermediate document states.
    for path in(OUT/'README.md',ROOT/'source/README.md'):audit.pin(path,sha(path))
    static_path,static,browser_path,browser,missing=browser_checks(audit,areas,runtime,args.allow_pending_browser)
    assert not any(any(part.startswith('exploratory')for part in Path(name).parts)for name in audit.pins),'Excluded exploration directories cannot remain required portableartifact pins'
    result=dict(schema='phase16-read-only-source-native-aggregate-v1',status='passed'if not missing else'pending_browser',rom_sha256=SHA,
        missing_required_artifacts=missing,areas=areas,rom_cpu_case_count=cpu,source_guard_case_count=guards,
        total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=prefix,
        source_integration_receipt_path=relative(INTEGRATION),source_integration_ROM_CPU_cases=t,source_integration_guard_cases=g,
        source_integration_complete_return_CPU_cases=c,source_integration_strict_prefix_CPU_cases=s,source_integration=integration_info,
        source_integration_completion_kinds=integration['completion_kinds'],source_integration_actual_caller_RTS_CPU_cases=22,
        source_integration_main_and_interrupt_parent_CPU_cases=2,integration_rom_cpu_case_count=t,integration_source_guard_case_count=g,
        all_CPU_cases_including_integration=cpu+t,all_source_guards_including_integration=guards+g,
        all_complete_return_CPU_cases_including_integration=complete+c,all_strict_prefix_CPU_cases_including_integration=prefix+s,
        source_and_validator_sha256={path:h for path,h in audit.pins.items()if path.startswith(('source/','scripts/'))},
        artifact_and_dependency_sha256={path:h for path,h in audit.pins.items()if not path.startswith(('source/','scripts/'))},
        receipt_sha256=receipts,evidence_sha256=evidences,raw_object_count=audit.raw_count,raw_bytes_checked=audit.raw_bytes,REA_archives=audit.archives,
        metadata_range_corrections=audit.metadata_range_corrections,
        source_AST=ast_checks,rebuilt_byte_identical=True,regressions=regressions,parent_regression_receipt_path=relative(parent_path),
        parent_regression_history_bridge=parent_bridge,
        native_evidence_path=relative(OUT/'runtime/evidence.json'),native=runtime,
        browser_static_receipt_path=relative(static_path),browser_static_receipt_sha256=sha(static_path)if static is not None else None,
        browser_receipt_sha256=sha(browser_path)if browser is not None else None,browser_status=browser['status']if browser else'pending',
        limitations=['Fieldlowerglyph256 and deliberate1missingF2D7 are strictprefixes; allother moduleprefixes retain their declared missing-helper/budget boundaries.',
          'Originalvalid237officers excludeaffinity3; initializedextra3pointer/data pseudoslots contain3. No officialfourthability or allROMno-producer theorem.',
          '647 potentialcitytailaliases remain explicit, not647confirmedconsumers and notproofthat+28..31 are unused.',
          'Audio2767body and19independent genuinecallers countedonce; originalcontext preparation instructions/parent sequences are notadded.',
          'Integration22actualcallerRTS plus2main/NMI/IRQparentsequences countedonce; nestedarrivals do notinflateCPUcasecount.',
          'FourNative importedstarts,9newpreparations and45previouslyapplied inheritedpreparations are distinct; no globalzero-write/naturalcampaign claim.',
          'Native hasnointernal6502trace andno sourcepipeline; originalcore RGB/PCM hardwaretiming remain separate from software/port/sourceCPU comparisons.',
          'OriginalROM, frozenNative and oldversionZIPs stayimmutable; root legitimately reruns oldcurrent5..15 source receipts/audits. This aggregate executes noCPU/core/IR.'])
    assert(result['all_CPU_cases_including_integration'],result['all_source_guards_including_integration'],result['all_complete_return_CPU_cases_including_integration'],result['all_strict_prefix_CPU_cases_including_integration'])==(12703,54,12442,261)
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','all_CPU_cases_including_integration','browser_status','missing_required_artifacts')},ensure_ascii=False))

if __name__=='__main__':main()
