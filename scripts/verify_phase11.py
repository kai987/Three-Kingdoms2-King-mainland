#!/usr/bin/env python3
"""Read-only audit of phase11 source, original bytes, receipts and core media.

Does not run6502, scene source, control IR or the native core. It fails closed
on stale/missing evidence and writes only its own verification.json receipt.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit,parse_qs,unquote
import argparse,ast,hashlib,json,sys,wave
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase11'
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MODULES={'battle':'battle_scene_controller','attack':'attack_scene_controller','duel':'duel_scene_controller',
 'shared':'scene_shared_services','initialization':'scene_initialization','setup-ai':'battle_setup_ai',
 'background':'battle_background_initialization'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def objects(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from objects(child)
    elif isinstance(value,list):
        for child in value:yield from objects(child)
def path_for(value):
    p=Path(value)
    if p.is_absolute():return p
    if not (ROOT/p).exists()and len(p.parts)==1 and p.suffix=='.py':p=Path('source/recovered')/p
    return ROOT/p
def relative(path):
    try:return str(Path(path).resolve().relative_to(ROOT.resolve()))
    except ValueError:return str(Path(path).resolve())

class Audit:
    def __init__(self,rom):self.rom=rom;self.pins={};self.raw_count=0;self.raw_bytes=0;self.archives=[]
    def pin(self,path,expected,size=None):
        p=path_for(path);assert p.is_file(),f'Missing pinned file {p}'
        actual=sha(p);assert actual==expected,f'Stale pin {relative(p)}: {actual} != {expected}'
        if size is not None:assert p.stat().st_size==size,(p,size)
        key=relative(p)
        if key in self.pins:assert self.pins[key]==expected
        self.pins[key]=expected
    def common_pins(self,data,area):
        module=MODULES[area]
        for value in objects(data):
            if 'path'in value and 'sha256'in value:self.pin(value['path'],value['sha256'],value.get('bytes'))
            for key in('source_sha256','dependencies','dependency_source_sha256','source_and_validator_sha256'):
                if isinstance(value.get(key),dict):
                    for path,digest in value[key].items():self.pin(path,digest)
        for key,path in [('source_sha256',data.get('source_path',data.get('source_file',f'source/recovered/{module}.py'))),
                         ('validator_sha256',data.get('validator_path',f'scripts/verify_{module}.py')),
                         ('analyzer_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py')),
                         ('analysis_sha256',data.get('analyzer_path',f'scripts/analyze_{module}.py')),
                         ('shared_service_sha256','source/recovered/scene_shared_services.py')]:
            if isinstance(data.get(key),str):self.pin(path,data[key])
        if isinstance(data.get('evidence_sha256'),str):self.pin(f'analysis/phase11/{area}/evidence.json',data['evidence_sha256'])
    def raw(self,data,area):
        for v in objects(data):
            if 'raw_hex'not in v:continue
            offset=v.get('rom_offset',v.get('file_offset',v.get('file_start')))
            if offset is None:continue
            if isinstance(offset,str):offset=int(offset,0)
            raw=bytes.fromhex(v['raw_hex']);assert raw and self.rom[offset:offset+len(raw)]==raw,(area,v.get('name'),offset)
            for key in('byte_count','bytes'):
                if isinstance(v.get(key),int):assert v[key]==len(raw),(area,key,v[key],len(raw))
            if 'sha256'in v:assert hashlib.sha256(raw).hexdigest()==v['sha256']
            bank=v.get('physical_bank',v.get('bank'));cpu=v.get('cpu_start',v.get('cpu_address',v.get('cpu',v.get('pc'))))
            if bank is not None and cpu is not None:
                if isinstance(bank,str):bank=int(bank,0)
                if isinstance(cpu,str):cpu=int(cpu,0)
                assert offset==16+bank*8192+(cpu&8191),(area,bank,cpu,offset,'iNES16 header')
                end=v.get('cpu_end_exclusive',v.get('end_exclusive'))
                if end is not None:
                    if isinstance(end,str):end=int(end,0)
                    assert end-cpu==len(raw),(area,'range length',cpu,end,len(raw))
            self.raw_count+=1;self.raw_bytes+=len(raw)
    def archived_REA(self,value):
        if isinstance(value,str):
            p=path_for(value);assert p.exists(),p
            if p.is_dir():
                files=[p/'image.bin',p/'evidence-bundle.json',p/'mapping.json']
                for f in files:assert f.is_file();self.pins[relative(f)]=sha(f)
                mapping=read(p/'mapping.json');banks=mapping['physical_banks'];offsets=mapping['file_offsets']
                assert offsets==[16+bank*8192 for bank in banks],(p,'iNES16 mapping')
                assert (p/'image.bin').read_bytes()==b''.join(self.rom[o:o+8192]for o in offsets),(p,'archived original banks')
                self.archives.append(dict(path=relative(p),files={f.name:sha(f)for f in files}))
            else:self.archives.append(dict(path=relative(p),sha256=sha(p)))
        elif isinstance(value,list):
            for item in value:self.pin(item['path'],item['sha256'],item.get('bytes'));self.archives.append(item)

def cpu_counts(receipt):
    total=receipt.get('rom_cpu_case_count',receipt.get('actual_ROM_CPU_comparison_count'))
    assert isinstance(total,int)and total>=0
    counts=receipt.get('counts',{});assert sum(counts.values())==total,(counts,total)
    complete=next((receipt[k]for k in('complete_return_count','complete_CPU_count','original_complete_case_count')if k in receipt),None)
    prefix=next((receipt[k]for k in('strict_prefix_count','strict_prefix_CPU_count','original_prefix_case_count')if k in receipt),None)
    if prefix is None:prefix=sum(v for k,v in counts.items()if 'prefix'in k.lower())
    if complete is None:complete=total-prefix
    assert complete+prefix==total,(complete,prefix,total)
    guards=receipt.get('source_guard_case_count',receipt.get('source_guard_count',0))
    return total,guards,complete,prefix

def source_AST(paths):
    result=[]
    forbidden=('py65','trace_startup','battle_state_machine','attack_state_machine','duel_state_machine',
               'runtime_services','tactical_ai_control','inspect_game_data','analyze_')
    for p in paths:
        tree=ast.parse(p.read_text());imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or'')
            if isinstance(node,ast.Attribute):assert node.attr not in('instructions','opcodes','instruction_map'),(p,node.attr)
            if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','MPU'),(p,node.func.id)
            if isinstance(node,ast.Dict):
                keys={k.value for k in node.keys if isinstance(k,ast.Constant)and isinstance(k.value,str)}
                assert not {'op','mode','operand','next_pc'}<=keys,(p,'PC operation record')
            if isinstance(node,ast.Subscript)and isinstance(node.slice,ast.Constant)and node.slice.value=='op':
                raise AssertionError((p,'generic runtime opcode dispatch'))
        assert not any(word in name for name in imports for word in forbidden),(p,imports)
        result.append(dict(path=relative(p),sha256=sha(p),imports=imports,
          functions=sum(isinstance(n,ast.FunctionDef)for n in ast.walk(tree)),
          if_statements=sum(isinstance(n,ast.If)for n in ast.walk(tree)),
          loops=sum(isinstance(n,(ast.While,ast.For))for n in ast.walk(tree))))
    return result

def native(audit):
    from PIL import Image
    root=OUT/'runtime';e=read(root/'evidence.json');r=read(root/'validation.json')
    assert e['status']==r['status']=='passed'and e['rom_sha256']==r['rom_sha256']==SHA
    assert r['evidence_sha256']==sha(root/'evidence.json')
    for item in e['dependency_pins']:audit.pin(item['path'],item['sha256'])
    assert not r['native_internal_CPU_trace']and r['source_CPU_comparisons_in_this_receipt']==0
    total=Counter();details=[]
    for case in e['native_cases']:
        p=root/case['case'];v=read(p/'validation.json');rep=read(p/'repeat-validation.json')
        assert v['status']==rep['status']==case['status']=='passed'and rep['all_hashes_equal']
        for key in('frames','checkpoint_count','natural_gameplay','controlled_fixture','final_fields'):
            assert case[key]==v[key],(case['case'],key,'manifest/receipt parity')
        assert not v['rom_modified']and v['rom_sha256']==SHA
        assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
        assert not v['native_internal_CPU_trace']and v['source_CPU_comparisons_in_this_receipt']==0
        for name,key in [('scripts/capture_scene_controller_flows.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),('scripts/nes_runtime.py','original_runtime_sha256')]:audit.pin(name,v[key])
        audit.pin('.toolchain/nestopia/nestopia_libretro.dylib',v['core']['core_sha256'])
        for field,key in [('initial_state','initial_state_sha256'),('preparation_reference','preparation_sha256')]:
            if v[field]is not None:audit.pin(v[field],v[key])
            else:assert v[key]is None
        for name,item in v['artifact_sha256'].items():
            f=p/name;assert f.stat().st_size==item['bytes']>0 and sha(f)==item['sha256'],f
        second=path_for(rep['second_run']);assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
        assert path_for(rep['first_run']).resolve()==p.resolve()
        for item in rep['artifacts']:
            one=p/item['artifact'];two=second/item['artifact'];assert item['equal']
            assert one.stat().st_size==two.stat().st_size==item['bytes']>0
            assert sha(one)==sha(two)==item['sha256'],one
        for name in rep['formal_JSON_exact_parity']:
            assert (p/name).read_bytes()==(second/name).read_bytes()and(p/name).stat().st_size>0,(p,name)
        for name in v['excluded_empty_VRAM']:assert (p/name).stat().st_size==0
        frames=read(p/'frame-services.json');points=read(p/'checkpoints.json');callbacks=read(p/'audio-callbacks.json')
        assert len(frames)==v['frames']and len(points)==v['checkpoint_count']and len(callbacks)==v['audio_callback_count']
        audio=v['full_audio']
        with wave.open(str(p/'full-flow.wav'),'rb')as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,audio['stereo_sample_frames'])
            pcm=w.readframes(w.getnframes())
        assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and any(pcm)
        assert sha(p/'full-flow.wav')==audio['WAV_sha256']
        cursor=0
        for index,row in enumerate(frames,1):
            assert row['frame']==index
            count=row['PCM_stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
            assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['PCM_sha256']
            assert cursor==row['PCM_stop_byte']and any(chunk)==row['PCM_nonzero']
        assert cursor==len(pcm)
        cursor=0
        for row in callbacks:
            count=row['stereo_sample_frames'];chunk=pcm[cursor:cursor+4*count];cursor+=len(chunk)
            assert len(chunk)==4*count and hashlib.sha256(chunk).hexdigest()==row['pcm_sha256']
            assert 0<=row['emulated_frame_start']<v['frames']
        assert cursor==len(pcm)
        for point in points:
            row=frames[point['frame']-1]
            assert sha(p/point['RAM'])==row['RAM_sha256']and sha(p/point['SRAM'])==row['SRAM_sha256']
            with Image.open(p/point['image'])as img:
                assert list(img.size)==row['native_dimensions']
                assert hashlib.sha256(img.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
        total.update(frames_first_run=v['frames'],checkpoint_count=v['checkpoint_count'],
          nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],
          formal_JSON_repeat_checks=len(rep['formal_JSON_exact_parity']),
          PCM_stereo_sample_frames_first_run=audio['stereo_sample_frames'],
          excluded_empty_VRAM=len(v['excluded_empty_VRAM']),
          excluded_snapshot_metadata_JSON=len(v['excluded_snapshot_metadata_JSON']))
        details.append(dict(case=case['case'],status='passed',natural_gameplay=v['natural_gameplay'],controlled_fixture=v['controlled_fixture'],frames=v['frames']))
    for key,value in total.items():assert value==r[key],(key,value,r[key])
    assert e['summary']=={key:r[key]for key in e['summary']}
    assert r['frames_both_runs']==2*r['frames_first_run']and len(details)==r['native_case_count']
    assert r['PCM_stereo_sample_frames_both_runs']==2*r['PCM_stereo_sample_frames_first_run']
    return dict(**r,cases=details)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--allow-missing-browser',action='store_true');args=p.parse_args()
    rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    audit=Audit(rom);audit.pins['scripts/verify_phase11.py']=sha(__file__)
    audit.pins['scripts/package_results.py']=sha(ROOT/'scripts/package_results.py')
    regressions={}
    for phase in range(5,11):
        path=ROOT/f'analysis/phase{phase}/verification.json';previous=read(path)
        assert previous['status']=='passed'
        assert previous['source_and_validator_sha256']['source/recovered/game_engine.py']==sha(ROOT/'source/recovered/game_engine.py')
        regressions[str(phase)]=dict(status='passed',verification_sha256=sha(path),current_GameEngine_pin=True)
    areas={};receipts={};evidence={};cpu=guards=complete=prefix=0
    for area,module in MODULES.items():
        folder=OUT/area;r=read(folder/'validation.json');e=read(folder/'evidence.json')
        assert r['status']=='passed'and r.get('failed_count',0)==0 and not r.get('failures'),area
        assert r['rom_sha256']==e['rom_sha256']==SHA
        audit.common_pins(r,area);audit.common_pins(e,area);audit.raw(e,area)
        if 'REA_archive'in e:audit.archived_REA(e['REA_archive'])
        executed=folder/'executed-instructions.json'
        if executed.exists():
            for v in objects(read(executed)):
                if 'rom_offset'not in v:continue
                bank=v.get('physical_bank',v.get('bank'));address=v.get('cpu_address',v.get('cpu',v.get('pc')))
                if bank is None or address is None:continue
                assert v['rom_offset']==16+bank*8192+(address&8191),(area,v)
        t,g,c,s=cpu_counts(r);cpu+=t;guards+=g;complete+=c;prefix+=s
        areas[area]=dict(status='passed',rom_cpu_case_count=t,source_guard_case_count=g,complete_return_CPU_cases=c,strict_prefix_CPU_cases=s)
        receipts[area]=sha(folder/'validation.json');evidence[area]=sha(folder/'evidence.json')
    for pair in(12,23):audit.archived_REA(f'analysis/rea/pairs/pair-{pair}')
    ast_checks=source_AST([ROOT/f'source/recovered/{m}.py'for m in MODULES.values()]+[ROOT/'source/recovered/scene_coordinator.py'])
    integration=read(OUT/'source-integration.json');assert integration['status']=='passed'and not integration['failures']
    assert integration['rom_sha256']==SHA
    assert integration['source_original_CPU_callbacks']==0 and not integration['source_IR_interpretation']
    for path,digest in integration['source_sha256'].items():audit.pin(path,digest)
    t,g,c,s=cpu_counts(integration);assert g==len(integration['source_guards'])
    assert len(integration['rows'])==t and Counter(row['kind']for row in integration['rows'])==integration['counts']
    assert Counter(row['comparison']for row in integration['rows'])==Counter({key:value for key,value in [('complete_return',c),('strict_prefix',s)] if value})
    assert all(row['source_original_CPU_callbacks']==0 for row in integration['rows'])
    runtime=native(audit);browser_path=OUT/'browser-validation.json';browser=None
    if browser_path.exists():
        browser=read(browser_path);assert browser['status']=='passed'
        assert browser['html_sha256']==sha(OUT/'index.html')
        if 'checks'in browser:assert all(browser['checks'].values())
        if 'screenshot_sha256'in browser:assert browser['screenshot_sha256']==sha(OUT/'browser-proof.png')
        for v in objects(browser):
            if isinstance(v.get('src'),str)and '?'in v['src']:
                u=urlsplit(v['src']);expected=parse_qs(u.query).get('sha')
                if not expected:continue
                file=ROOT/unquote(u.path.lstrip('/'))if u.path.startswith('/analysis/')else OUT/unquote(u.path)
                assert sha(file)==expected[0],file
    else:assert args.allow_missing_browser,'Required live browser-validation.json missing'
    if (OUT/'index.html').exists():audit.pins['analysis/phase11/index.html']=sha(OUT/'index.html')
    result=dict(status='passed'if browser is not None else'pending_browser',rom_sha256=SHA,
      rom_cpu_case_count=cpu,source_guard_case_count=guards,
      total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=prefix,
      areas=areas,source_integration_ROM_CPU_cases=t,source_integration_guard_cases=g,
      source_integration_complete_return_CPU_cases=c,source_integration_strict_prefix_CPU_cases=s,
      integration_rom_cpu_case_count=t,integration_source_guard_case_count=g,
      all_CPU_cases_including_integration=cpu+t,all_source_guards_including_integration=guards+g,
      all_complete_return_CPU_cases_including_integration=complete+c,
      all_strict_prefix_CPU_cases_including_integration=prefix+s,
      source_and_validator_sha256={p:h for p,h in audit.pins.items()if p.startswith(('source/','scripts/'))},
      artifact_and_dependency_sha256={p:h for p,h in audit.pins.items()if not p.startswith(('source/','scripts/'))},
      receipt_sha256={**receipts,'source-integration':sha(OUT/'source-integration.json'),'native':sha(OUT/'runtime/validation.json')},
      evidence_sha256={**evidence,'native':sha(OUT/'runtime/evidence.json')},
      raw_object_count=audit.raw_count,raw_bytes_checked=audit.raw_bytes,REA_archives=audit.archives,
      source_AST=ast_checks,rebuilt_byte_identical=True,native=runtime,regressions=regressions,
      browser_status=browser['status']if browser else'pending',browser_receipt_sha256=sha(browser_path)if browser else None,
      limitations=['Complete return, strict prefix and source-only guards are separate counts.',
        'Top-level ROM/source counts describe the seven areas; integration counts are additional and explicitly labeled.',
        'Validator-only original CPU callbacks do not constitute production source fallback.',
        'AST checks cover the seven new production modules and scene coordinator, not retained historical GameEngine APIs.',
        'Native RGB/PCM frames are original core observations, not source hardware synthesis or native CPU trace.',
        'Unknown presentation/controller bodies remain explicit dependencies.'])
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k in('status','rom_cpu_case_count','source_guard_case_count','total_complete_return_CPU_cases','total_strict_prefix_CPU_cases','source_integration_ROM_CPU_cases','browser_status')}))
if __name__=='__main__':main()
