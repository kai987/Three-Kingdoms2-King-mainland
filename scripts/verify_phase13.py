#!/usr/bin/env python3
"""Fail-closed static audit of phase13 source/oracle/native/browser evidence.

No6502 execution, controlIR execution or native-core replay occurs here.
Original CPU comparison receipts, source guards and native media stay separate.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit,parse_qs,unquote
import argparse,ast,hashlib,json,sys,wave
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_phase12 import source_AST,objects,path_for,relative,sha,read
OUT=ROOT/'analysis/phase13';SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={
 'city':'city_ui_controller','panels':'city_panel_services','global-ui':'global_ui_controller',
 'graphics':'ui_graphics_initialization','scenario':'scenario_initialization',
 'city-details':'city_officer_details_controller','title-intro':'title_intro_graphics',
 'action-bridges':'city_action_bridges','arithmetic':'ui_arithmetic_services',
 'menu-navigation':'city_menu_navigation',
}
FOLDERS={key:key for key in MODULES};INTEGRATION=OUT/'source-integration.json'

class Audit:
    def __init__(self,rom):self.rom=rom;self.pins={};self.raw_count=0;self.raw_bytes=0;self.archives=[]
    def pin(self,path,expected,size=None):
        p=path_for(path);assert p.is_file(),f'Missing pinned file {p}'
        assert isinstance(expected,str)and len(expected)==64,(path,expected)
        actual=sha(p);assert actual==expected,f'Stale pin {relative(p)}: {actual} != {expected}'
        if size is not None:assert p.stat().st_size==size,(p,size)
        key=relative(p)
        if key in self.pins:assert self.pins[key]==expected
        self.pins[key]=expected
    def common_pins(self,data,area):
        module=MODULES[area]
        dictionaries=('pins','source_sha256','dependencies','dependency_source_sha256','source_and_validator_sha256',
                      'source_and_analyzer_pins','REA_archive_pins','source_dependency_pins')
        for value in objects(data):
            if isinstance(value.get('path'),str)and isinstance(value.get('sha256'),str):self.pin(value['path'],value['sha256'],value.get('bytes'))
            for key in dictionaries:
                if isinstance(value.get(key),dict):
                    for path,digest in value[key].items():
                        if isinstance(digest,str):self.pin(path,digest)
        for key,path in [('source_sha256',data.get('source_path',data.get('source_file',f'source/recovered/{module}.py'))),
                         ('validator_sha256',data.get('validator_path',f'scripts/verify_{module}.py')),
                         ('analyzer_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py')),
                         ('analysis_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py'))]:
            if isinstance(data.get(key),str):self.pin(path,data[key])
        if isinstance(data.get('evidence_sha256'),str):self.pin(OUT/FOLDERS[area]/'evidence.json',data['evidence_sha256'])
    def raw(self,data,area):
        for v in objects(data):
            if 'raw_hex'not in v:continue
            offset=next((v[k]for k in('rom_offset','file_offset','file_start','file')if isinstance(v.get(k),(int,str))),None)
            if offset is None:continue
            if isinstance(offset,str):offset=int(offset,0)
            raw=bytes.fromhex(v['raw_hex']);assert raw and self.rom[offset:offset+len(raw)]==raw,(area,v.get('name'),offset)
            for key in('byte_count','bytes'):
                if isinstance(v.get(key),int):assert v[key]==len(raw),(area,key,v[key],len(raw))
            if isinstance(v.get('sha256'),str):assert hashlib.sha256(raw).hexdigest()==v['sha256']
            bank=v.get('physical_bank',v.get('bank'));cpu=next((v[k]for k in('cpu_start','cpu_address','cpu','pc')if k in v),None)
            if bank is not None and cpu is not None:
                if isinstance(bank,str):bank=int(bank,0)
                if isinstance(cpu,str):cpu=int(cpu,0)
                assert offset==16+bank*8192+(cpu&8191),(area,bank,cpu,offset,'iNES16 header')
                end=v.get('cpu_end_exclusive',v.get('end_exclusive'))
                if end is not None:
                    if isinstance(end,str):end=int(end,0)
                    assert end-cpu==len(raw),(area,cpu,end,len(raw))
            self.raw_count+=1;self.raw_bytes+=len(raw)
    def archive(self,value):
        if isinstance(value,str):
            p=path_for(value);assert p.exists(),p
            if p.is_dir():
                files=[p/'image.bin',p/'evidence-bundle.json',p/'mapping.json']
                for f in files:self.pin(f,sha(f))
                mapping=read(p/'mapping.json');banks=mapping['physical_banks'];offsets=mapping['file_offsets']
                assert offsets==[16+bank*8192 for bank in banks],(p,'iNES16 mapping')
                assert(p/'image.bin').read_bytes()==b''.join(self.rom[o:o+8192]for o in offsets),(p,'archived original banks')
                self.archives.append(dict(path=relative(p),files={f.name:sha(f)for f in files}))
            else:self.pin(p,sha(p));self.archives.append(dict(path=relative(p),sha256=sha(p)))
        elif isinstance(value,list):
            for item in value:self.pin(item['path'],item['sha256'],item.get('bytes'));self.archives.append(item)

def cpu_counts(receipt):
    total=receipt.get('rom_cpu_case_count',receipt.get('actual_ROM_CPU_comparison_count'));assert isinstance(total,int)and total>=0
    counts=receipt.get('counts',{});assert all(isinstance(v,int)and v>=0 for v in counts.values())
    assert sum(counts.values())==total,(counts,total)
    complete=next((receipt[k]for k in('complete_return_count','complete_CPU_count','original_complete_case_count')if k in receipt),None)
    prefix=next((receipt[k]for k in('strict_prefix_count','strict_prefix_CPU_count','original_prefix_case_count')if k in receipt),None)
    if prefix is None:prefix=sum(v for k,v in counts.items()if'prefix'in k.lower())
    if complete is None:complete=total-prefix
    assert complete+prefix==total,(complete,prefix,total)
    guards=receipt.get('source_guard_case_count',receipt.get('source_guard_count',0));assert isinstance(guards,int)and guards>=0
    return total,guards,complete,prefix

def audit_native(audit):
    from PIL import Image
    root=OUT/'runtime';e=read(root/'evidence.json');r=read(root/'validation.json')
    assert e['status']==r['status']=='passed'and e['rom_sha256']==r['rom_sha256']==SHA
    assert r['evidence_sha256']==sha(root/'evidence.json')
    for pin in e['dependency_pins']:audit.pin(pin['path'],pin['sha256'],pin.get('bytes'))
    assert not r['native_internal_CPU_trace']and r['source_CPU_comparisons_in_this_receipt']==0
    total=Counter();details=[]
    for case in e['native_cases']:
        p=root/case['case'];v=read(p/'validation.json');rep=read(p/'repeat-validation.json')
        assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']
        assert not v['rom_modified']and v['rom_sha256']==SHA and v['natural_inherited_start']
        assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
        assert not v['source_pipeline_installed']and not v['native_internal_CPU_trace']and v['source_CPU_comparisons_in_this_receipt']==0
        assert v['final_SRAM_equals_initial']and not v['SRAM_changed_addresses']
        assert v['UI_marker_FF_alone_is_not_completion']and v['labels_checked_against_state_and_queue']
        for field,key in [('scripts/capture_city_ui_flows.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),('scripts/nes_runtime.py','original_runtime_sha256')]:audit.pin(field,v[key])
        audit.pin('.toolchain/nestopia/nestopia_libretro.dylib',v['core']['core_sha256'])
        for field,key in [('initial_state','initial_state_sha256'),('provenance','provenance_sha256')]:audit.pin(v[field],v[key])
        for name,item in v['artifact_sha256'].items():
            f=p/name;assert f.stat().st_size==item['bytes']>0 and sha(f)==item['sha256'],f
        second=path_for(rep['second_run']);assert path_for(rep['first_run']).resolve()==p.resolve()
        assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
        for item in rep['artifacts']:
            one=p/item['artifact'];two=second/item['artifact'];assert item['equal']
            assert one.stat().st_size==two.stat().st_size==item['bytes']>0 and sha(one)==sha(two)==item['sha256'],one
        for name in rep['formal_JSON_exact_parity']:assert(p/name).read_bytes()==(second/name).read_bytes()and(p/name).stat().st_size>0
        for name in v['excluded_empty_VRAM']:assert(p/name).stat().st_size==0
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
            assert sha(p/point['SRAM'])==v['initial_SRAM_sha256']
            with Image.open(p/point['image'])as image:
                assert list(image.size)==row['native_dimensions']==[256,240]
                assert hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
        total.update(frames_first_run=v['frames'],checkpoint_count=v['checkpoint_count'],nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
            formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
            excluded_empty_VRAM=len(v['excluded_empty_VRAM']),excluded_snapshot_metadata_JSON=len(v['excluded_snapshot_metadata_JSON']))
        details.append(dict(case=case['case'],status='passed',natural_inherited_start=True,frames=v['frames'],checkpoint_count=v['checkpoint_count'],
            input_step_count=v['input_step_count'],termination=v['termination'],observed_states=v['observed_states'],final_SRAM_unchanged=True,
            receipt_path=relative(p/'validation.json'),repeat_receipt_path=relative(p/'repeat-validation.json')))
    for key,value in total.items():assert r[key]==value,(key,value,r[key])
    assert r['frames_both_runs']==2*r['frames_first_run']and r['native_case_count']==len(details)
    assert e['summary']=={key:r[key]for key in e['summary']}
    return dict(**r,cases=details,PCM_stereo_sample_frames_both_runs_derived=2*r['PCM_stereo_sample_frames_first_run'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-pending',action='store_true',help='Missing artifacts may produce a pending draft; existing stale/failed artifacts still fail closed');args=p.parse_args()
    rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    audit=Audit(rom);audit.pin(Path(__file__),sha(Path(__file__)));audit.pin('scripts/package_results.py',sha(ROOT/'scripts/package_results.py'))
    for script in('scripts/build_phase13_city_evidence.py','scripts/write_phase13_report.py'):
        audit.pin(script,sha(ROOT/script))
    missing=[]
    def require(path):
        if path.is_file():return read(path)
        assert args.allow_pending,f'Missing required final artifact {relative(path)}'
        missing.append(relative(path));return None
    regressions={}
    for phase in range(5,13):
        path=ROOT/f'analysis/phase{phase}/verification.json';old=read(path);assert old['status']=='passed'
        for field in('source_and_validator_sha256','artifact_and_dependency_sha256'):
            for name,digest in old.get(field,{}).items():
                # Historical reports are repinned by the root before final.
                audit.pin(name,digest)
        regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_pins=True)
    areas={};receipts={};evidence={};cpu=guards=complete=prefix=0
    for area,module in MODULES.items():
        folder=OUT/FOLDERS[area];r=require(folder/'validation.json');e=require(folder/'evidence.json')
        if r is None or e is None:continue
        assert r['status']=='passed'and r.get('failed_count',0)==0 and not r.get('failures')and not r.get('quick',False),area
        assert r['rom_sha256']==e['rom_sha256']==SHA
        for key in('production_source_original_CPU_callbacks','production_original_CPU_callbacks','source_original_CPU_callbacks'):
            if key in r:assert r[key]==0,(area,key)
        for key in('source_IR_interpretation','production_IR_interpretation'):
            if key in r:assert not r[key],(area,key)
        audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
        if 'REA_archive'in e:audit.archive(e['REA_archive'])
        executed=folder/'executed-instructions.json'
        if executed.is_file():
            for item in objects(read(executed)):
                if 'rom_offset'not in item:continue
                bank=item.get('physical_bank',item.get('bank'));pc=item.get('cpu_address',item.get('cpu',item.get('pc')))
                if bank is not None and pc is not None:assert item['rom_offset']==16+bank*8192+(pc&8191),(area,item)
        t,g,c,s=cpu_counts(r);cpu+=t;guards+=g;complete+=c;prefix+=s
        exclusions=r.get('unusable_input_fixtures_excluded',0)
        assert isinstance(exclusions,int)and exclusions>=0
        if exclusions:
            file=r['unusable_fixture_artifact'];path=folder/file if isinstance(file,str)and not file.startswith('analysis/')else path_for(file)
            assert path.is_file();audit.pin(path,sha(path))
        areas[area]=dict(status='passed',source_path=f'source/recovered/{module}.py',receipt_path=relative(folder/'validation.json'),evidence_path=relative(folder/'evidence.json'),
            rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=s,
            declared_scope=r.get('comparison',r.get('scope')),verification_only_original_CPU_callback_count=r.get('verification_only_original_CPU_callback_count',0),
            unusable_input_fixtures_excluded=exclusions,included_exclusions_in_CPU_count=False)
        receipts[area]=sha(folder/'validation.json');evidence[area]=sha(folder/'evidence.json')
    for pair in(8,10,23,25,27,29):audit.archive(f'analysis/rea/pairs/pair-{pair:02d}')
    ast_checks=source_AST([ROOT/f'source/recovered/{module}.py'for module in MODULES.values()]+[ROOT/'source/recovered/scene_coordinator.py'])
    integration=require(INTEGRATION);t=g=c=s=0
    if integration is not None:
        assert integration['status']=='passed'and integration['failed_count']==0 and not integration['failures']
        assert integration['rom_sha256']==SHA and integration['source_original_CPU_callbacks']==0 and not integration['source_IR_interpretation']
        assert integration.get('production_fallback')is False
        for name,digest in integration['source_sha256'].items():audit.pin(name,digest)
        for name,digest in integration.get('artifact_sha256',{}).items():audit.pin(name,digest if isinstance(digest,str)else digest['sha256'])
        t,g,c,s=cpu_counts(integration)
        assert len(integration['rows'])==t and Counter(row['comparison']for row in integration['rows'])==Counter({k:v for k,v in(('complete_return',c),('strict_prefix',s))if v})
        assert g==len(integration.get('guards',integration.get('source_guards',[])))
        for row in integration['rows']:
            if 'source_original_CPU_callbacks'in row:assert row['source_original_CPU_callbacks']==0
            if 'status'in row:assert row['status']=='passed'
        receipts['source-integration']=sha(INTEGRATION)
    discovery_path=OUT/'dependencies/inventory.json';discovery=require(discovery_path);discovery_summary=None
    if discovery is not None:
        assert discovery['rom_sha256']==SHA and discovery['status']=='passed'
        assert not discovery['original_ROM_modified']and not discovery['native_internal_CPU_trace']
        assert discovery['production_source_CPU_callbacks']==0 and not discovery['source_equivalence_claim']
        for name,digest in discovery['dependency_pins'].items():audit.pin(name,digest)
        for site in discovery['original_farcall_sites']:
            raw=bytes.fromhex(site['raw_call_hex']);offset=site['rom_offset']
            assert len(raw)==5 and rom[offset:offset+5]==raw
            assert hashlib.sha256(raw).hexdigest()==site['raw_call_sha256']
            assert offset==16+site['caller_physical_bank']*8192+(site['call_PC']&8191)
        audit.raw(discovery,'dependency-discovery');audit.pin(discovery_path,sha(discovery_path));evidence['dependency-discovery']=sha(discovery_path)
        discovery_summary=dict(catalog_path=relative(discovery_path),included_in_source_comparison_count=False,
            bounded_original_CPU_cases=discovery['bounded_original_CPU_cases'],
            complete_original_callback_cases=discovery['complete_original_callback_cases'],prefix_budget_cases=discovery['prefix_budget_cases'],
            observed_farcall_count=len(discovery['original_farcall_sites']),native_internal_CPU_trace=False)
    runtime=None
    ne=require(OUT/'runtime/evidence.json');nr=require(OUT/'runtime/validation.json')
    if ne is not None and nr is not None:
        runtime=audit_native(audit);receipts['native']=sha(OUT/'runtime/validation.json');evidence['native']=sha(OUT/'runtime/evidence.json')
    for doc in('README.md','source/README.md','analysis/index.html','analysis/phase13/README.md'):
        path=ROOT/doc
        if path.is_file():audit.pin(path,sha(path))
        else:assert args.allow_pending;missing.append(doc)
    static_path=OUT/'browser-static-validation.json';static=require(static_path)
    if static is not None:
        assert static['status']=='passed'and static['JS_syntax']=='passed'and not static['native_files_modified']
        assert static['HTML_sha256']==sha(OUT/'index.html')
        audit.pin('scripts/build_phase13_browser.py',static['generator_sha256']);audit.pin(OUT/'runtime/evidence.json',static['native_evidence_sha256'])
        for item in static['modules']:
            area=areas[item['key']];assert(item['CPU'],item['complete'],item['prefix'],item.get('guard_count',item.get('source_guards')))==(
                area['rom_cpu_case_count'],area['complete_return_CPU_cases'],area['strict_prefix_CPU_cases'],area['source_guard_case_count'])
        assert len(static['modules'])==len(MODULES)
        if runtime is not None:
            qa=static['native_static_QA'];assert qa['nonempty_double_run_artifacts']==runtime['nonempty_repeat_artifact_checks']
            assert qa['formal_JSON_exact_parity']==runtime['formal_JSON_repeat_checks']and qa['frame_PCM_segments']==runtime['frames_first_run']
            assert qa['PNG_native_RGB_RAM_SRAM_state_checkpoints']==runtime['checkpoint_count']
        audit.pin(static_path,sha(static_path))
    browser_path=OUT/'browser-validation.json';browser=require(browser_path)
    if browser is not None:
        assert browser['status']=='passed'
        assert browser.get('html_sha256',browser.get('HTML_sha256'))==sha(OUT/'index.html')
        if 'checks'in browser:assert all(browser['checks'].values())
        assert not browser.get('console_errors',[])
        image=OUT/'browser-proof.png';audit.pin(image,browser['screenshot_sha256'])
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
        integration_rom_cpu_case_count=t,integration_source_guard_case_count=g,
        all_CPU_cases_including_integration=cpu+t,all_source_guards_including_integration=guards+g,
        all_complete_return_CPU_cases_including_integration=complete+c,all_strict_prefix_CPU_cases_including_integration=prefix+s,
        source_and_validator_sha256={p:h for p,h in audit.pins.items()if p.startswith(('source/','scripts/'))},
        artifact_and_dependency_sha256={p:h for p,h in audit.pins.items()if not p.startswith(('source/','scripts/'))},
        receipt_sha256=receipts,evidence_sha256=evidence,raw_object_count=audit.raw_count,raw_bytes_checked=audit.raw_bytes,
        REA_archives=audit.archives,source_AST=ast_checks,rebuilt_byte_identical=True,regressions=regressions,dependency_discovery=discovery_summary,
        native_evidence_path=relative(OUT/'runtime/evidence.json'),native=runtime,browser_static_receipt_path=relative(static_path),
        browser_static_receipt_sha256=sha(static_path)if static is not None else None,
        browser_receipt_sha256=sha(browser_path)if browser is not None else None,browser_status=browser['status']if browser else'pending',
        limitations=['Per-module comparison scopes remain explicit; no uniform2KB claim.',
            'CPU complete returns, strictprefixes, source guards and invalid-fixture exclusions are separate.',
            'Original helper discovery and validator-only originalCPU callbacks are not production fallback.',
            'Native2flows use original RGB/48kPCM with ordinary controls, no extra memory writes; they do not prove complete monthly/war/campaign execution.',
            'Source production has no6502/controlIR executor; hardware synthesis remains the original core.',
            'Frozen native inputs, original ROM and versioned oldZIPs remain immutable; earlier current integration/audit receipts were rerun by the coordinator to refresh changed shared API pins. This static aggregate reads those receipts and does not rerun their CPU matrices.'])
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','all_CPU_cases_including_integration','browser_status','missing_required_artifacts')},ensure_ascii=False))
if __name__=='__main__':main()
