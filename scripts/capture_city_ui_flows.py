#!/usr/bin/env python3
"""Natural original-core city menus/details, with no new RAM/result writes."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from nes_service_runtime import ServiceRuntime
from capture_scene_controller_flows import ROM_SHA,CORE_SHA
CASES=('city-menu-cancel-cycle','world-officer-browse-cycle')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','state-transitions.json')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(path.read_bytes())
def relative(path):return str(path.resolve().relative_to(ROOT))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def fields(ram,sram):
    index=ram[0x40C];ids=list(ram[0x410:0x418]);candidate=ids[index]if index<8 else None
    result=dict(global_state=ram[0x7A],nmi_scene=ram[0x78],city_main=ram[0x400],city_phase=ram[0x401],city_state_0400_040B=list(ram[0x400:0x40C]),
       menu_cursor_0012=ram[0x12],menu_cursor_0013=ram[0x13],controller_buttons_0081=ram[0x81],city_control_0470_047F=list(ram[0x470:0x480]),
       city_candidate_0471=ram[0x471],UI_index_040C=index,UI_row_040D=ram[0x40D],UI_ids_0410_0417=ids,UI_candidate_at_index=candidate,
       text_progress_0300=ram[0x300],text_cursor_0304=ram[0x304],PPU_jobs_007E=ram[0x7E],NMI_busy_007B=ram[0x7B],OAM_byte_count_007C=ram[0x7C],
       scratch_0000_001F=ram[:0x20].hex(),packet_0380_03BF=ram[0x380:0x3C0].hex(),queue_0310_037F=ram[0x310:0x380].hex(),
       OAM_0200_02FF=ram[0x200:0x300].hex(),CHR_cache_00B0_00DD=ram[0xB0:0xDE].hex(),portrait_CHR_B8_B9=list(ram[0xB8:0xBA]),
       camera_008E_00A9=ram[0x8E:0xAA].hex(),map_and_game_6F80_6FFF=sram[0xF80:0x1000].hex(),
       main_mapper_cache_DE_DF_E0=list(ram[0xDE:0xE1]),NMI_mapper_cache_E1_E2_E3=list(ram[0xE1:0xE4]),
       palette_0100_013F=ram[0x100:0x140].hex(),IRQ_pending_0062=ram[0x62],IRQ_fields_0068_0075=ram[0x68:0x76].hex(),
       RNG_cursor_0050=ram[0x50],calendar_and_request_6F00_6F06=list(sram[0xF00:0xF07]),audio_RAM_0700_07FF=ram[0x700:0x800].hex())
    if candidate is not None and candidate<237:
        record=sram[0x3C0+12*candidate:0x3C0+12*(candidate+1)]
        result['UI_candidate_record']=dict(ID=candidate,raw=record.hex(),health=record[0],martial=record[1],intelligence=record[2],
            loyalty=record[3],virtue=record[4],experience_raw16=record[6]|record[7]<<8,troops_raw16=record[8]|record[9]<<8,
            troops_display_low10=record[8]|((record[9]&3)<<8),equipment_raw=record[10],status_level_raw=record[11])
    if ram[0x471]<30:result['city_record_at_0471']=sram[ram[0x471]*32:(ram[0x471]+1)*32].hex()
    return result

def capture(rom,out,case):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Use a fresh output directory'
    mother=ROOT/'analysis/phase11/runtime/cold-battle/city-commands.state';provenance=mother.parent/'validation.json'
    previous=json.loads(provenance.read_text());assert previous['status']=='passed'and previous['natural_gameplay']and previous['additional_core_memory_writes']==0
    rt=ServiceRuntime(rom,out);assert rt.info['core_sha256']==CORE_SHA and rt.av_info['sample_rate']==48000.0
    rows=[];points=[];plan=[];transitions=[];labels=set();seen_states=set();last=None
    try:
        rt.load_state(mother);shutil.copyfile(mother,out/'initial.state');prefix=mother.with_suffix('')
        initial_ram=rt.memory(2);initial_sram=rt.memory(0)
        assert initial_ram==Path(str(prefix)+'-ram.bin').read_bytes()and initial_sram==Path(str(prefix)+'-sram.bin').read_bytes()
        first=fields(initial_ram,initial_sram);assert(first['global_state'],first['nmi_scene'],first['city_main'],first['city_phase'])==(2,2,1,1)
        write(out/'initial-fields.json',dict(first,RAM_sha256=digest(initial_ram),SRAM_sha256=digest(initial_sram)))
        def snap(label,reason,row=None):
            if label in labels:return
            labels.add(label);rt.snapshot(label);row=fields(rt.memory(2),rt.memory(0))if row is None else row
            points.append(dict(label=label,frame=rt.frames,reason=reason,image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',
                 global_state=row['global_state'],nmi_scene=row['nmi_scene'],city_main=row['city_main'],city_phase=row['city_phase'],menu_cursor_0012=row['menu_cursor_0012'],
                 UI_index_040C=row['UI_index_040C'],UI_row_040D=row['UI_row_040D'],UI_ids_0410_0417=row['UI_ids_0410_0417'],UI_candidate_at_index=row['UI_candidate_at_index'],
                 text_progress_0300=row['text_progress_0300'],text_cursor_0304=row['text_cursor_0304'],PPU_jobs_007E=row['PPU_jobs_007E'],PCM_stop_byte=len(rt.pcm)))
        def observe(runtime):
            nonlocal last
            ram,sram=runtime.memory(2),runtime.memory(0);pcm=runtime.pcm_frame()
            assert len(ram)==2048 and len(sram)==8192 and runtime.frame is not None
            row=fields(ram,sram);row.update(frame=runtime.frames,RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RGB_sha256=digest(runtime.frame.tobytes()),
                native_dimensions=list(runtime.frame.size),PCM_stereo_sample_frames=len(pcm)//4,PCM_sha256=digest(pcm),PCM_nonzero=any(pcm),PCM_stop_byte=len(runtime.pcm))
            rows.append(row);now=(row['global_state'],row['nmi_scene'],row['city_main'],row['city_phase'])
            if now!=last:transitions.append(dict(frame=runtime.frames,from_state=last,to_state=now));last=now
            if now not in seen_states:
                seen_states.add(now);snap(f'observed-g{now[0]:02d}-n{now[1]:02d}-main{now[2]:02d}-phase{now[3]:02d}',
                    'first observed raw active state; no completion inference from inherited FF',row)
        def step(frames,buttons=(),purpose='',label=None,expected=None):
            plan.append(dict(start_frame=rt.frames,frames=frames,buttons=list(buttons),purpose=purpose,**({'capture':label}if label else{})))
            rt.run(frames,buttons,observer=observe)
            if expected is not None:
                ram=rt.memory(2);assert(ram[0x7A],ram[0x78],ram[0x400],ram[0x401])==(2,2,*expected),(label,list(ram[0x400:0x406]))
                assert(ram[0x300],ram[0x304],ram[0x7E])==(255,255,0),(label,ram[0x300],ram[0x304],ram[0x7E])
            if label:snap(label,'validated planned state after ordinary input/release; marker alone is not completion')
        def press(key,release,purpose,label=None,expected=None):
            step(2,(key,),purpose);step(release,(),purpose+' release/observe',label,expected)
        def icon(index,label,expected):
            assert(rt.memory(2)[0x400],rt.memory(2)[0x401],rt.memory(2)[0x12])==(1,1,0)
            for _ in range(index):press('right',18,'select original city icon')
            assert rt.memory(2)[0x12]==index
            press('a',120,'open selected original icon',label,expected)
        step(30,(),'settle inherited natural city-command state','icons-ready',(1,1))
        if case=='city-menu-cancel-cycle':
            icon(0,'domestic-menu',(2,1));press('a',180,'open land-operation officer selection','domestic-officer-choice',(2,3))
            press('b',120,'cancel officer choice','domestic-choice-cancelled',(2,1));press('b',120,'return to four city icons','domestic-menu-closed',(1,1))
            icon(1,'military-menu',(3,1));press('a',180,'open original invasion destination choice','military-target-choice',(3,2))
            press('b',120,'cancel invasion destination','military-choice-cancelled',(3,1));press('b',120,'close military menu','military-menu-closed',(1,1))
            icon(2,'resource-menu',(4,1));press('b',120,'close original resource commands','resource-menu-closed',(1,1))
            icon(3,'town-menu',(5,1));press('a',180,'enter original weapon-shop officer choice','town-weapon-officer-choice',(5,18))
            press('b',120,'cancel weapon buyer before any purchase','town-choice-cancelled',(5,1));press('b',120,'close town menu','town-menu-closed',(1,1))
            press('b',180,'return from city icons to world/city cursor','world-map-return',(0,1))
            termination='domestic/military/resource/town menus and cancellable choices returned to city/world cursor0/sub1'
        else:
            press('b',180,'return from city icons to world/city cursor','world-map-ready',(0,1))
            press('b',240,'open original officer information from the world/city cursor','officer-info-first',(12,2))
            current=fields(rt.memory(2),rt.memory(0));assert current['UI_index_040C']==0 and current['UI_row_040D']==255 and current['UI_candidate_at_index']==131
            press('down',120,'browse the next original officer','officer-info-next',(12,2))
            current=fields(rt.memory(2),rt.memory(0));assert current['UI_index_040C']==1 and current['UI_row_040D']==255 and current['UI_candidate_at_index']==5
            press('up',120,'return to the first original officer','officer-info-first-again',(12,2))
            assert fields(rt.memory(2),rt.memory(0))['UI_candidate_at_index']==131
            press('a',180,'close officer information through its original confirmation','officer-info-closed',(0,1))
            termination='true25A021/AFE5 officer browser showed first/second/first officer and returned to city/world cursor0/sub1'
        final=fields(rt.memory(2),rt.memory(0));assert(final['global_state'],final['nmi_scene'],final['city_main'],final['city_phase'])==(2,2,0,1)
        sram_diff=[dict(address=0x6000+index,before=a,after=b)for index,(a,b)in enumerate(zip(initial_sram,rt.memory(0)))if a!=b]
        assert not sram_diff,sram_diff[:16]
        assert len(rows)==rt.frames and all(row['PCM_stereo_sample_frames']>0 for row in rows)and any(row['PCM_nonzero']for row in rows)
        wav=rt.save_wav(out/'full-flow.wav');write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan)
        write(out/'audio-callbacks.json',rt.audio_calls);write(out/'state-transitions.json',transitions)
        artifacts={};empty=[]
        for path in sorted(out.iterdir()):
            if not path.is_file():continue
            if path.stat().st_size==0:empty.append(path.name);continue
            if path.suffix in('.png','.bin','.state','.wav')or path.name in FORMAL:artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
        result=dict(schema='phase13-native-city-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,
             natural_inherited_start=True,additional_core_memory_writes=0,additional_ready_or_result_injections=0,source_pipeline_installed=False,
             initial_state=relative(mother),initial_state_sha256=sha(mother),provenance=relative(provenance),provenance_sha256=sha(provenance),
             initial_RAM_sha256=digest(initial_ram),initial_SRAM_sha256=digest(initial_sram),final_SRAM_equals_initial=True,SRAM_changed_addresses=sram_diff,
             script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),
             core=rt.info,AV=rt.av_info,frames=rt.frames,checkpoint_count=len(points),input_step_count=len(plan),termination=termination,
             observed_states=[list(state)for state in sorted(seen_states)],final_fields=final,full_audio=wav,
             all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
             artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(p.name for p in out.glob('*.json')if p.name not in FORMAL),
             labels_checked_against_state_and_queue=True,UI_marker_FF_alone_is_not_completion=True,
             limits=['Frame fields/RGB/PCM are original-core observations, not internalCPU traces or restored-source synthesis.',
                     'The camera/mapper fields are raw caches and actualpixels; no cycleaccurate/source hardware claim.',
                     'Info410 is the first list element; raw040C and candidate410[index] are recorded separately.',
                     'Finalworld cursor0/1 is a UI return, not a monthend/war/campaign completion.'])
        write(out/'validation.json',result);return result
    finally:rt.close()

def aggregate(out,receipts):
    cases=[]
    for row in receipts:
        name=row['case'];repeat=json.loads((out/name/'repeat-validation.json').read_text());points=json.loads((out/name/'checkpoints.json').read_text())
        cases.append(dict(case=name,title='城市四菜单、武将/目标选择与取消返回'if name=='city-menu-cancel-cycle'else'世界/城市界面武将资料：上下浏览与关闭',
            validation=name+'/validation.json',checkpoints=name+'/checkpoints.json',frame_services=name+'/frame-services.json',input_plan=name+'/input-plan.json',
            repeat_validation=name+'/repeat-validation.json',full_WAV=name+'/full-flow.wav',images={p['label']:name+'/'+p['image']for p in points},
            frames=row['frames'],checkpoint_count=row['checkpoint_count'],observed_states=row['observed_states'],final_fields=row['final_fields'],
            nonempty_repeat_artifact_checks=repeat['nonempty_artifact_checks'],PCM_stereo_sample_frames=row['full_audio']['stereo_sample_frames']))
    summary=dict(native_case_count=len(receipts),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),
       checkpoint_count=sum(r['checkpoint_count']for r in receipts),nonempty_repeat_artifact_checks=sum(c['nonempty_repeat_artifact_checks']for c in cases),
       formal_JSON_repeat_checks=len(FORMAL)*len(receipts),excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),
       excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),sample_rate=48000,
       PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),additional_core_memory_writes=0,
       final_SRAM_unchanged_in_all_cases=True,source_CPU_comparisons_in_this_receipt=0,native_internal_CPU_trace=False,failed_count=0)
    evidence=dict(schema='phase13-native-city-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=cases,
        dependency_pins=[dict(path=relative(path),sha256=sha(path))for path in(Path(__file__),ROOT/'scripts/nes_service_runtime.py',ROOT/'scripts/nes_runtime.py')])
    write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json')))
    lines=['# 第十三轮原核心城市UI回放','',
      '两案从第十一轮无注入冷启动的city-commands自然母档开始，仅普通按键；不新增core RAM/SRAM、ready、结果或packet写入。原只读ROM及锁定Nestopia直接产生RGB和48000Hz双声道PCM，恢复源码未安装到原核心。每案最终全部8192B SRAM与母档逐字节一致。','',
      f'首跑{summary["frames_first_run"]}帧，两跑{summary["frames_both_runs"]}帧，{summary["checkpoint_count"]}检查点；{summary["nonempty_repeat_artifact_checks"]}份非空产物hash重复一致（包含{summary["formal_JSON_repeat_checks"]}份正式JSON），排除{summary["excluded_empty_VRAM"]}份0B VRAM和目录路径metadata JSON。完整逐帧RGB/RAM/SRAM/PCM哈希与WAV公开。','',
      '## 原入口及命名核对','',
      '这些自然界面保持global2/NMI2；城市callback由fixedF8EC selector3B进入physical27A000→A00C/A01F，主/phase为0400/0401。全局2的main10A000内政AI不是这个城市NMIcontroller。NMI2此前的29A009/A00F/A03F是另外的呈现worker。','',
      '图标0→main2/1内政，图标1→3/1军队；图标2→4/1原文字「ブッシをはこぶ」「あたえる」，保持物资操作名称，不称战斗计略。图标3→5/1原提示「ここはマチです」街菜单，首地点5/18明确「ブキヤ」武器店武将选择，不叫外交。所有选择在资源/目标最终确认之前取消。','',
      '地图/城市0/1按B打开12/2武将资料，实际far25A021 bytes4CE5AF→AFE5；25A01B→B964是另一个候选扫描，25A012→B2D7是已有绘制worker，三者不能混淆。资料里040C是原索引、0410..417是列表，down后0410仍131但0411=5、索引变1，图中于禁；不是410字段直接改变为当前显示ID。','']
    for c in cases:lines.extend([f'## {c["title"]}','',f'{c["frames"]}帧、{c["checkpoint_count"]}检查点；最终global2/NMI2/city0/sub1，是UI周期结束，不称月轮或战役完成。','',
       f'- [实际按钮计划]({c["input_plan"]})',f'- [逐帧字段、相机、银行缓存、OAM及hash]({c["frame_services"]})',f'- [检查点原图]({c["checkpoints"]})',
       f'- [完整实际WAV]({c["full_WAV"]})',f'- [母档来源和最终SRAM对照]({c["validation"]})',f'- [独立第二跑核对]({c["repeat_validation"]})',''])
    lines.extend(['计划检查点先核对真实主/phase和300=FF、304=FF、7E=0，再保存图像；旧040D=FF单独不作为完成判断。自动状态截图只叫observed-state，不给其猜完成标签。原每帧数据不是内部CPU/NMItrace；相机/mapper缓存不会替代真实端口序或硬件时序证明。','',
      '```sh',"python3 scripts/capture_city_ui_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat",'```','', '[原核心manifest](evidence.json) · [汇总回执](validation.json)'])
    (out/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(status='passed',summary=summary),ensure_ascii=False),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/runtime');p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--repeat',action='store_true');a=p.parse_args();out=a.out.resolve()
    assert sha(a.rom)==ROM_SHA;receipts=[]
    for case in CASES if a.case=='all'else(a.case,):
        first=out/case;one=capture(a.rom,first,case)
        if a.repeat:
            second=out.parent/(out.name+'-repeat')/case;two=capture(a.rom,second,case)
            checks=[dict(artifact=name,equal=expected==two['artifact_sha256'].get(name),**expected)for name,expected in one['artifact_sha256'].items()]
            assert all(r['equal']for r in checks),[r for r in checks if not r['equal']]
            assert one['frames']==two['frames']and one['final_fields']==two['final_fields']
            write(first/'repeat-validation.json',dict(status='passed',first_run=relative(first),second_run=relative(second),all_hashes_equal=True,nonempty_artifact_checks=len(checks),
               artifacts=checks,formal_JSON_exact_parity=list(FORMAL),excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_directory_metadata_JSON=one['excluded_snapshot_metadata_JSON']))
        receipts.append(one);print(json.dumps(dict(case=case,status='passed',frames=one['frames'],checkpoints=one['checkpoint_count'],SRAM_unchanged=one['final_SRAM_equals_initial']),ensure_ascii=False),flush=True)
    if a.repeat:aggregate(out,receipts)
if __name__=='__main__':main()
