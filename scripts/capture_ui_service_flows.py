#!/usr/bin/env python3
"""Observe original-core portrait/name/details flows without new memory writes.

Native RGB/PCM and frame fields come only from the pinned Nestopia core.
The independent source CPU comparison is a separate phase12 receipt.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
from nes_service_runtime import ServiceRuntime
from capture_scene_controller_flows import fields as scene_fields,active,ROM_SHA,CORE_SHA
CASES=('battle-officer-info','ordinary-attack-return')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','handoffs.json')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(path.read_bytes())
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def relative(path):return str(path.resolve().relative_to(ROOT))

def fields(ram,sram):
    row=scene_fields(ram,sram)
    row.update(UI_control_040C_0417=list(ram[0x40C:0x418]),UI_main_040C=ram[0x40C],UI_row_040D=ram[0x40D],UI_officer_0410=ram[0x410],
               scratch_0000_0012=ram[0:0x13].hex(),packet_0380_03BF=ram[0x380:0x3C0].hex(),
               queue_0310_0373=ram[0x310:0x374].hex(),portrait_CHR_B8_B9=list(ram[0xB8:0xBA]),
               OAM_0200_02FF=ram[0x200:0x300].hex(),portrait_frame_A4=ram[0xA4],portrait_x_override_04BC=ram[0x4BC])
    ident=ram[0x410]
    if ident<237:
        raw=sram[0x3C0+12*ident:0x3C0+12*(ident+1)]
        row['selected_UI_officer_record']=dict(officer_id=ident,raw=raw.hex(),health=raw[0],martial=raw[1],intelligence=raw[2],
             loyalty=raw[3],virtue=raw[4],experience_raw16=raw[6]|raw[7]<<8,troops_raw16=raw[8]|raw[9]<<8,
             troops_display_low10=raw[8]|((raw[9]&3)<<8),equipment_raw=raw[10],state_and_level_raw=raw[11])
    return row

def capture(rom,out,case):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Use a new owned output directory'
    prior=ROOT/'analysis/phase11/runtime';rt=ServiceRuntime(rom,out)
    assert rt.info['core_sha256']==CORE_SHA and rt.av_info['sample_rate']==48000.0
    rows=[];points=[];plan=[];handoffs=[];labels=set();seen_main=set();seen_ui_rows=set();seen_edges=set();last=None
    if case=='battle-officer-info':
        initial_state=prior/'cold-battle/battle-control-return.state';provenance=prior/'cold-battle/validation.json';inherited_plan=None
    else:
        initial_state=prior/'ordinary-attack-return/initial.state';provenance=prior/'ordinary-attack-return/validation.json'
        inherited_plan=prior/'ordinary-attack-return/input-plan.json'
    previous=json.loads(provenance.read_text());assert previous['status']=='passed'and previous['additional_core_memory_writes']==0
    try:
        rt.load_state(initial_state);shutil.copyfile(initial_state,out/'initial.state')
        prefix=initial_state.with_suffix('')
        if case=='battle-officer-info':
            assert rt.memory(2)==Path(str(prefix)+'-ram.bin').read_bytes()and rt.memory(0)==Path(str(prefix)+'-sram.bin').read_bytes()
        else:
            # The phase11 copied state keeps its original phase3 mother.
            old_prefix=(ROOT/previous['initial_state']).with_suffix('')
            assert rt.memory(2)==Path(str(old_prefix)+'-ram.bin').read_bytes()and rt.memory(0)==Path(str(old_prefix)+'-sram.bin').read_bytes()
        first=fields(rt.memory(2),rt.memory(0));first.update(RAM_sha256=digest(rt.memory(2)),SRAM_sha256=digest(rt.memory(0)))
        assert first['global_state']==4 and first['nmi_scene']==3
        write(out/'initial-fields.json',first)
        def snap(label,reason,row=None):
            if label in labels:return
            labels.add(label);rt.snapshot(label);row=fields(rt.memory(2),rt.memory(0))if row is None else row
            points.append(dict(label=label,frame=rt.frames,reason=reason,image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',
                 global_state=row['global_state'],nmi_scene=row['nmi_scene'],battle_state=row['battle_state'],attack_state=row['attack_state'],
                 active_controller=row['active_controller'],active_main=row['active_main'],active_phase=row['active_phase'],
                 UI_control_040C_0417=row['UI_control_040C_0417'],UI_main_040C=row['UI_main_040C'],UI_row_040D=row['UI_row_040D'],UI_officer_0410=row['UI_officer_0410'],
                 scratch_0000_0012=row['scratch_0000_0012'],packet_0380_03BF=row['packet_0380_03BF'],queue_0310_0373=row['queue_0310_0373'],
                 portrait_CHR_B8_B9=row['portrait_CHR_B8_B9'],OAM_byte_count=row['OAM_byte_count'],PCM_stop_byte=len(rt.pcm)))
        def observe(runtime):
            nonlocal last
            ram,sram=runtime.memory(2),runtime.memory(0);pcm=runtime.pcm_frame()
            assert len(ram)==2048 and len(sram)==8192 and runtime.frame is not None
            row=fields(ram,sram);row.update(frame=runtime.frames,RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RGB_sha256=digest(runtime.frame.tobytes()),
                native_dimensions=list(runtime.frame.size),PCM_stereo_sample_frames=len(pcm)//4,PCM_sha256=digest(pcm),PCM_nonzero=any(pcm),PCM_stop_byte=len(runtime.pcm))
            rows.append(row)
            controller=row['active_controller'];main=row['active_main']
            if controller is not None and(controller,main)not in seen_main:
                seen_main.add((controller,main));snap(f'first-{controller}-main-{main:02d}','first active controller main observed at a completed native frame',row)
            if controller=='battle'and main==1:
                marker=row['UI_row_040D']
                if marker not in seen_ui_rows and(marker<10 or marker==255):
                    seen_ui_rows.add(marker);snap('info-rows-complete'if marker==255 else f'info-row-{marker:02d}',
                        'native end-of-frame UI row byte; skipped internal updates are not claimed observed',row)
            now=(row['global_state'],row['nmi_scene'])
            if last is not None and now!=last:
                handoffs.append(dict(frame=runtime.frames,from_global=last[0],from_nmi=last[1],to_global=now[0],to_nmi=now[1]))
                if(last,now)not in seen_edges:
                    seen_edges.add((last,now));snap(f'handoff-{len(seen_edges):02d}-g{now[0]:02d}-n{now[1]:02d}','observed native global/NMI transition',row)
            last=now
        def step(frames,buttons=(),purpose='',capture_label=None):
            plan.append(dict(start_frame=rt.frames,frames=frames,buttons=list(buttons),purpose=purpose,**({'capture':capture_label}if capture_label else{})))
            rt.run(frames,buttons,observer=observe)
            if capture_label:snap(capture_label,'explicit ordinary-input plan checkpoint')
        if case=='battle-officer-info':
            step(30,(),'settle inherited natural battle state','before-open')
            step(2,('b',),'open original officer-information command');step(240,(),'observe actual portrait/details production and consumption','info-open')
            opened=fields(rt.memory(2),rt.memory(0));assert opened['battle_state']==[1,1]and opened['UI_row_040D']==255,opened
            step(2,('a',),'close the original information page');step(240,(),'observe original battle control return','info-closed')
            final=fields(rt.memory(2),rt.memory(0));assert final['battle_state']==[0,2]and final['nmi_scene']==3,final
            verified=dict(actual_open_battle_state=opened['battle_state'],actual_details_final_row_byte=opened['UI_row_040D'],
                          actual_selected_officer=opened['UI_officer_0410'],actual_close_battle_state=final['battle_state'],
                          row_values_observed_after_frames=sorted(seen_ui_rows),ordinary_buttons_only=True)
            termination='original officer-information page opened and fully drawn; original A input returned to battle0/sub2'
        else:
            old_plan=json.loads(inherited_plan.read_text())
            old_points=json.loads((prior/'ordinary-attack-return/checkpoints.json').read_text());at={}
            for point in old_points:at.setdefault(point['frame'],[]).append(point['label'])
            previous_observe=observe
            def observe_with_prior(runtime):
                previous_observe(runtime)
                for label in at.get(runtime.frames,[]):snap(label,'inherited phase11 original-input checkpoint')
            observe=observe_with_prior
            for old_step in old_plan:
                assert rt.frames==old_step['start_frame']
                step(old_step['frames'],old_step['buttons'],'unchanged phase11 ordinary attack return input',old_step.get('capture'))
            assert rt.frames==previous['frames']
            final=fields(rt.memory(2),rt.memory(0));assert final['global_state']in(3,4)and final['battle_state']==[0,2]
            assert any(controller=='attack'for controller,_ in seen_main)
            parity={}
            for point in old_points:
                label=point['label'];parity[label]={suffix:(out/(label+suffix)).read_bytes()==(prior/'ordinary-attack-return'/(label+suffix)).read_bytes()
                    for suffix in('.png','-ram.bin','-sram.bin','.state')}
                assert all(parity[label].values()),(label,parity[label])
            verified=dict(inherited_input_plan_exact_buttons_and_durations=True,prior_checkpoint_artifacts_equal=parity,
                          prior_checkpoint_byte_parity_checks=4*len(old_points),actual_final_battle_state=final['battle_state'],
                          active_attack_mains_observed=sorted(main for controller,main in seen_main if controller=='attack'))
            termination='unchanged original retreat/confirmation inputs returned from ordinary attack to battle0/sub2'
        assert len(rows)==rt.frames and all(row['PCM_stereo_sample_frames']>0 for row in rows)and any(row['PCM_nonzero']for row in rows)
        wav=rt.save_wav(out/'full-flow.wav');write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan)
        write(out/'audio-callbacks.json',rt.audio_calls);write(out/'handoffs.json',handoffs)
        artifacts={};empty=[]
        for path in sorted(out.iterdir()):
            if not path.is_file():continue
            if path.stat().st_size==0:empty.append(path.name);continue
            if path.suffix in('.png','.bin','.state','.wav')or path.name in FORMAL:artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
        result=dict(schema='phase12-original-core-ui-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,
             additional_core_memory_writes=0,additional_ready_or_result_injections=0,source_pipeline_installed=False,
             initial_state=relative(initial_state),initial_state_sha256=sha(initial_state),provenance=relative(provenance),provenance_sha256=sha(provenance),
             inherited_start_natural=(case=='battle-officer-info'),inherited_controlled_fixture=(case!='battle-officer-info'),
             inherited_preparation_reference=previous['preparation_reference'],inherited_preparation=previous.get('inherited_preparation',{}),
             inherited_input_plan=relative(inherited_plan)if inherited_plan else None,inherited_input_plan_sha256=sha(inherited_plan)if inherited_plan else None,
             script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),
             reused_field_helpers_sha256=sha(ROOT/'scripts/capture_scene_controller_flows.py'),core=rt.info,AV=rt.av_info,
             frames=rt.frames,checkpoint_count=len(points),input_step_count=len(plan),verified_effects=verified,termination=termination,
             full_audio=wav,all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
             observed_active_main_states={controller:sorted(main for name,main in seen_main if name==controller)for controller,_ in sorted(seen_main)},
             final_fields=final,artifact_sha256=artifacts,excluded_empty_VRAM=empty,
             excluded_snapshot_metadata_JSON=sorted(p.name for p in out.glob('*.json')if p.name not in FORMAL),
             limits=['Native end-of-frame fields may miss same-frame packet producer/consumer steps; these are not internalCPU traces.',
                     'The natural battle state was inherited from the earlier zero-injection coldboot; the attack state inherits its explicit earlier adjacent-coordinate fixture.',
                     'No restored source controller is installed in Nestopia; nativepixels/PCM and independent sourceCPU comparison are separate evidence.'])
        write(out/'validation.json',result);return result
    finally:rt.close()

def aggregate(out,receipts):
    native=[]
    for row in receipts:
        name=row['case'];repeat=json.loads((out/name/'repeat-validation.json').read_text());points=json.loads((out/name/'checkpoints.json').read_text())
        native.append(dict(case=name,title='原战场武将资料：自然旧起点、B打开/A关闭'if name=='battle-officer-info'else'普通攻击：旧明示起点、原後退输入返回',
          validation=name+'/validation.json',checkpoints=name+'/checkpoints.json',frame_services=name+'/frame-services.json',input_plan=name+'/input-plan.json',
          repeat_validation=name+'/repeat-validation.json',full_WAV=name+'/full-flow.wav',images={p['label']:name+'/'+p['image']for p in points},
          frames=row['frames'],checkpoint_count=row['checkpoint_count'],verified_effects=row['verified_effects'],
          initial_state=row['initial_state'],initial_state_sha256=row['initial_state_sha256'],provenance=row['provenance'],
          inherited_start_natural=row['inherited_start_natural'],inherited_controlled_fixture=row['inherited_controlled_fixture'],
          nonempty_repeat_artifact_checks=repeat['nonempty_artifact_checks'],PCM_stereo_sample_frames=row['full_audio']['stereo_sample_frames']))
    summary=dict(native_case_count=len(receipts),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),
      checkpoint_count=sum(r['checkpoint_count']for r in receipts),nonempty_repeat_artifact_checks=sum(r['nonempty_repeat_artifact_checks']for r in native),
      formal_JSON_repeat_checks=len(FORMAL)*len(receipts),excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),
      excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),sample_rate=48000,
      PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),
      additional_core_memory_writes=0,source_CPU_comparisons_in_this_receipt=0,native_internal_CPU_trace=False,failed_count=0)
    evidence=dict(schema='phase12-native-ui-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=native,
      dependency_pins=[dict(path=relative(path),sha256=sha(path))for path in(Path(__file__),ROOT/'scripts/nes_service_runtime.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/capture_scene_controller_flows.py')])
    write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json')))
    lines=['# 第十二轮原核心UI流程','',
      '原RGB和48000Hz双声道16bit PCM由只读原ROM与锁定Nestopia libretro核心直接输出。恢复源码未安装到原核心；本回执没有源码CPU对照、内部CPU/NMItrace或源码独立波形合成的含义。两案只加载明确继承state再运行普通按钮，没有新增core RAM/SRAM、结果或ready写入。','',
      f'首跑{summary["frames_first_run"]}帧、两跑{summary["frames_both_runs"]}帧，{summary["checkpoint_count"]}检查点；{summary["nonempty_repeat_artifact_checks"]}份非空canonical产物逐项hash重复一致，另{summary["formal_JSON_repeat_checks"]}份正式JSON计入其中。排除{summary["excluded_empty_VRAM"]}份0B VRAM与目录路径metadata JSON。每帧完整RAM/SRAM/RGB/PCM哈希及完整WAV保留。','']
    for row in native:
        lines.extend([f'## {row["title"]}','',f'{row["frames"]}帧，{row["checkpoint_count"]}检查点。起点：`{row["initial_state"]}`；准确继承来源：`{row["provenance"]}`。',''])
        if row['case']=='battle-officer-info':lines.extend(['起点来自第十一轮无注入冷启动后的battle-control-return。none30、B2/none240打开原武将信息，真实battle1/sub1、040D=FF；A2/none240关闭，返回battle0/sub2。肖像和数字/姓名字段由原程序生成并消费，不注入packet或完成标志。逐帧040D仅是帧结束观测，未声称每个内部row都被观察到。',''])
        else:lines.extend(['起点继承第三轮唯一敌坐标准备的原state：0600敌X20→3、0614敌Y14→16；第十一轮只复制并公开来源。此轮使用完全相同普通输入/时长，所有旧检查点PNG/RAM/SRAM/state再次逐字节核对。命令设後退、原确认/结果后返回战场；不能称从自然战役无准备进入普通攻击。',''])
        lines.extend([f'- [真实输入]({row["input_plan"]})',f'- [逐帧UI/队列/字形/OAM与hash]({row["frame_services"]})',f'- [图片检查点]({row["checkpoints"]})',f'- [完整实际WAV]({row["full_WAV"]})',f'- [首跑范围/原state来源]({row["validation"]})',f'- [独立第二跑逐产物核对]({row["repeat_validation"]})',''])
    lines.extend(['每帧额外记录040C..0417控制字节、0000..0012 scratch、0380..03BF packet、0310..0373队列、B8/B9肖像CHR页与完整0200..02FF OAM。packet可能在一帧内生产/消费，本目录不据帧结束字段推断不存在这些原步骤。母档载入与独立core内存poke明确区分，新增poke数量为0。','',
      '```sh',"python3 scripts/capture_ui_service_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat",'```','', '[原核心汇总](validation.json) · [证据manifest](evidence.json)'])
    (out/'README.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(status='passed',summary=summary),ensure_ascii=False),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/runtime')
    p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--repeat',action='store_true');a=p.parse_args();out=a.out.resolve()
    assert sha(a.rom)==ROM_SHA;cases=CASES if a.case=='all'else(a.case,);receipts=[]
    for case in cases:
        first=out/case;one=capture(a.rom,first,case)
        if a.repeat:
            second=out.parent/'runtime-repeat'/case;two=capture(a.rom,second,case);checks=[]
            for name,expected in one['artifact_sha256'].items():checks.append(dict(artifact=name,equal=expected==two['artifact_sha256'].get(name),**expected))
            assert all(row['equal']for row in checks),[r for r in checks if not r['equal']]
            assert one['frames']==two['frames']and one['final_fields']==two['final_fields']
            write(first/'repeat-validation.json',dict(status='passed',first_run=relative(first),second_run=relative(second),all_hashes_equal=True,
                  nonempty_artifact_checks=len(checks),artifacts=checks,formal_JSON_exact_parity=list(FORMAL),
                  excluded_empty_VRAM=one['excluded_empty_VRAM'],excluded_directory_metadata_JSON=one['excluded_snapshot_metadata_JSON']))
        receipts.append(one);print(json.dumps(dict(case=case,status='passed',frames=one['frames'],checkpoints=one['checkpoint_count'],verified=one['verified_effects']),ensure_ascii=False),flush=True)
    if a.repeat:aggregate(out,receipts)
if __name__=='__main__':main()
