#!/usr/bin/env python3
"""Original Nestopia scene-control replays with native RGB/48kPCM evidence.

Only ordinary controller inputs and explicitly inherited frozen states are used.
No corememory write, ROMpatch, readiness injection, result injection or source
controller is installed. Per-frame field observations are not internalCPU traces.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
from nes_service_runtime import ServiceRuntime
ROOT=Path(__file__).resolve().parents[1]
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
CASES=('cold-battle','ordinary-attack-return','duel-return')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','handoffs.json','initial-fields.json')

def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def relative(p):return str(p.relative_to(ROOT))
def active(ram):
 g,n=ram[0x7A],ram[0x78]
 if n==3 and g in(3,4):return 'battle',ram[0x500],ram[0x501]
 if n==4 and g in(5,6):return 'attack',ram[0x540],ram[0x541]
 if n==5 and g in(7,8):return 'duel',ram[0x4A8],ram[0x4A9]
 return None,None,None

def fields(ram,sram):
 name,main,phase=active(ram)
 officers={}
 for ident in set(ram[0x4AD:0x4AF]+ram[0x560:0x562]):
  if ident<237:
   a=0x3C0+12*ident;raw=sram[a:a+12]
   officers[str(ident)]=dict(raw=raw.hex(),health=raw[0],troops_low10=raw[8]|((raw[9]&3)<<8),status=raw[11]&3)
 return dict(global_state=ram[0x7A],nmi_scene=ram[0x78],active_controller=name,active_main=main,active_phase=phase,
             battle_state=list(ram[0x500:0x502]),attack_state=list(ram[0x540:0x542]),duel_state=list(ram[0x4A8:0x4AB]),
             attack_ids=list(ram[0x560:0x562]),duel_ids=list(ram[0x4AD:0x4AF]),duel_HP=list(ram[0x4B1:0x4B3]),
             battle_results=list(ram[0x514:0x518]),NMI_busy=ram[0x7B],OAM_byte_count=ram[0x7C],PPU_lock=ram[0x7D],PPU_jobs=ram[0x7E],
             IRQ_pending=ram[0x62],IRQ_split_state=list(ram[0x68:0x75]),PPUCTRL_cache=ram[0x8B],
             palette_fade=list(ram[0x87:0x8A]),palette_0100_013F=ram[0x100:0x140].hex(),
             text_progress_0300=ram[0x300],text_cursor_0304=ram[0x304],text_queue_0310_0313=ram[0x310:0x314].hex(),
             camera_008E_009D=ram[0x8E:0x9E].hex(),mapper_cache_00E1_00ED=ram[0xE1:0xEE].hex(),
             audio_RAM_0700_07FF=ram[0x700:0x800].hex(),RNG_cursor_0050=ram[0x50],officer_records=officers)

def capture(rom,out,case):
 out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Use a fresh owned output directory'
 runtime=ServiceRuntime(rom,out);assert runtime.info['core_sha256']==CORE_SHA;assert runtime.av_info['sample_rate']==48000.0
 rows=[];points=[];plan=[];handoffs=[];seen_main=set();seen_edges=set();seen_controllers=set();labels=set();last=None
 preparation=None;initial_state=None;pulses=0
 try:
  if case=='ordinary-attack-return':
   initial_state=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-enter.state'
   preparation=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/fixture.json'
  elif case=='duel-return':
   initial_state=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-entry.state'
   preparation=ROOT/'analysis/duel_fsm/runtime/injected-core/validation.json'
  if initial_state:
   runtime.load_state(initial_state);shutil.copyfile(initial_state,out/'initial.state')
   prefix=initial_state.with_suffix('');assert runtime.memory(2)==Path(str(prefix)+'-ram.bin').read_bytes();assert runtime.memory(0)==Path(str(prefix)+'-sram.bin').read_bytes()
  ram,sram=runtime.memory(2),runtime.memory(0);initial=fields(ram,sram)
  initial.update(RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RAM_bytes=len(ram),SRAM_bytes=len(sram))
  if case=='ordinary-attack-return':assert initial['global_state']==4 and initial['battle_state']==[3,2],initial
  if case=='duel-return':assert initial['global_state']==7,initial
  write(out/'initial-fields.json',initial)
  def snap(label,reason,row=None):
   if label in labels:return
   labels.add(label);runtime.snapshot(label)
   state=fields(runtime.memory(2),runtime.memory(0))if row is None else row
   points.append(dict(label=label,frame=runtime.frames,reason=reason,image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',
                      global_state=state['global_state'],nmi_scene=state['nmi_scene'],active_controller=state['active_controller'],active_main=state['active_main'],active_phase=state['active_phase'],
                      battle_state=state['battle_state'],attack_state=state['attack_state'],duel_state=state['duel_state'],duel_HP=state['duel_HP'],
                      PPU_jobs=state['PPU_jobs'],palette_fade=state['palette_fade'],PCM_stop_byte=len(runtime.pcm)))
  def observe(rt):
   nonlocal last
   ram,sram=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();assert len(ram)==2048 and len(sram)==8192 and rt.frame is not None
   row=fields(ram,sram);row.update(frame=rt.frames,RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RGB_sha256=digest(rt.frame.tobytes()),
        native_dimensions=list(rt.frame.size),PCM_stereo_sample_frames=len(pcm)//4,PCM_sha256=digest(pcm),PCM_nonzero=any(pcm),PCM_stop_byte=len(rt.pcm))
   rows.append(row)
   if row['active_controller']:
    seen_controllers.add(row['active_controller']);key=(row['active_controller'],row['active_main'])
    if key not in seen_main:
     seen_main.add(key);snap(f'first-{key[0]}-main-{key[1]:02d}', 'first observed active controller main field; not internalCPU trace',row)
   now=(row['global_state'],row['nmi_scene'])
   if last is not None and last!=now:
    edge=(last,now);handoffs.append(dict(frame=rt.frames,from_global=last[0],from_nmi=last[1],to_global=now[0],to_nmi=now[1],active_controller=row['active_controller']))
    if edge not in seen_edges:
     seen_edges.add(edge);snap(f'handoff-{len(seen_edges):03d}-g{now[0]:02d}-n{now[1]:02d}','first instance of observed global/NMI transition',row)
   last=now
  def step(frames,buttons=(),purpose='',capture_label=None):
   plan.append(dict(start_frame=runtime.frames,frames=frames,buttons=list(buttons),purpose=purpose,**({'capture':capture_label}if capture_label else{})))
   runtime.run(frames,buttons,observer=observe)
   if capture_label:snap(capture_label,'explicit input-plan checkpoint')
  if case=='cold-battle':
   original=ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json';original_plan=json.loads(original.read_text())
   assert len(original_plan)==78 and sum(x['frames']for x in original_plan)==7738
   for original_step in original_plan:
    step(original_step['frames'],original_step.get('buttons',()),'inherited cold-boot ordinary input plan',original_step.get('capture'))
   step(2,('b',),'exit the original tactic menu');step(180,(),'observe original battle control return','battle-control-return')
   assert active(runtime.memory(2))[0]=='battle';termination='cold boot reached battlefield and returned from tactic-selection control'
  elif case=='ordinary-attack-return':
   step(180,(),'original entry/initialization','initialization-observed');step(2,('a',),'original confirmation');step(240,(),'original presentation')
   for i in range(2):step(2,('a',),'advance original attack dialogue');step(180,(),'observe original stage',f'attack-prelude-{i+1}')
   step(12,('left',),'select 後退 for first command column');step(35,(),'release')
   for i in range(3):
    step(12,('down',),'select next original command row');step(35,(),'release');step(12,('left',),'select 後退 for this row');step(35,(),'release',f'retreat-row-{i+2}')
   for pulses in range(1,101):
    step(2,('a',),'confirm/continue original retreat action');step(90,(),'observe original control/result','return-detected'if False else None)
    if pulses>=3 and runtime.memory(2)[0x7A]in(3,4)and 'attack'in seen_controllers:break
   else:raise RuntimeError('Attack controller did not return under bounded ordinary inputs')
   snap('return-detected','original global returned to battle after ordinary attack retreat inputs');step(90,(),'confirm stable battle return','final')
   assert runtime.memory(2)[0x7A]in(3,4);termination='ordinary attack scene completed retreat/result return to battlefield'
  else:
   for pulses in range(1,301):
    step(2,('a',),'original duel confirm/continue input');step(30,(),'observe original initialization/action/result')
    if pulses>=6 and runtime.memory(2)[0x7A]in(3,4,5,6)and 'duel'in seen_controllers:break
   else:raise RuntimeError('Duel controller did not return under bounded ordinary inputs')
   snap('return-detected','original duel returned to battle or ordinary attack scene');step(90,(),'confirm stable non-duel return','final')
   assert runtime.memory(2)[0x7A]in(3,4,5,6);termination='duel scene traversed initialization/action/result and original return'
  assert all(r['PCM_stereo_sample_frames']>0 for r in rows)and any(r['PCM_nonzero']for r in rows)
  wav=runtime.save_wav(out/'full-flow.wav');write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan)
  write(out/'handoffs.json',handoffs);write(out/'audio-callbacks.json',runtime.audio_calls)
  artifacts={};excluded=[]
  for p in sorted(out.iterdir()):
   if not p.is_file():continue
   if p.stat().st_size==0:excluded.append(p.name);continue
   if p.suffix in('.png','.bin','.state','.wav')or p.name in FORMAL:artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
  result=dict(schema='phase11-native-scene-flow-v1',status='passed',case=case,rom_sha256=ROM_SHA,rom_modified=False,
      additional_core_memory_writes=0,additional_ready_or_result_injections=0,natural_gameplay=(case=='cold-battle'),
      controlled_fixture=(case!='cold-battle'),initial_state=relative(initial_state)if initial_state else None,
      initial_state_sha256=sha(initial_state)if initial_state else None,preparation_reference=relative(preparation)if preparation else None,
      preparation_sha256=sha(preparation)if preparation else None,inherited_preparation=json.loads(preparation.read_text())if preparation else{},
      original_cold_plan='analysis/runtime/phase3/replay-cold-to-battle.json'if case=='cold-battle'else None,
      script_sha256=sha(Path(__file__)),runtime_extension_sha256=sha(ROOT/'scripts/nes_service_runtime.py'),original_runtime_sha256=sha(ROOT/'scripts/nes_runtime.py'),
      core=runtime.info,AV=runtime.av_info,frames=runtime.frames,checkpoint_count=len(points),input_step_count=len(plan),A_confirmation_pulses=pulses,
      observed_active_main_states={name:sorted(main for n,main in seen_main if n==name)for name in sorted(seen_controllers)},
      global_NMI_handoffs=handoffs,final_fields=fields(runtime.memory(2),runtime.memory(0)),termination=termination,
      full_audio=wav,audio_callback_count=len(runtime.audio_calls),all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,
      native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0,
      artifact_sha256=artifacts,excluded_empty_VRAM=excluded,excluded_snapshot_metadata_JSON=sorted(p.name for p in out.glob('*.json')if p.name not in FORMAL),
      run_directory=relative(out),limits=['Native core RGB/PCM/frame fields do not establish internalCPU/NMIinstruction traces or sourcePCM synthesis.',
       'Active mainstate observations require matching NMI mode and global scene; stale inactive arrays are not counted.',
       'Coldcase is cold boot into battle plus a control interaction cycle, not a complete war victory.',
       'Attack/duel cases inherit explicitly disclosed earlier preparation and add only ordinary controller inputs.'])
  write(out/'validation.json',result);return result
 finally:runtime.close()

def aggregate(out,receipts):
 cases=[]
 for r in receipts:
  name=r['case'];first=out/name;repeat=json.loads((first/'repeat-validation.json').read_text())
  cases.append(dict(case=name,title={'cold-battle':'冷启动进入战场及控制交互周期','ordinary-attack-return':'普通攻击：原输入後退并返回战场','duel-return':'单挑：含初始化、动作与结果返回'}[name],
   status=r['status'],controlled_fixture=r['controlled_fixture'],natural_gameplay=r['natural_gameplay'],frames=r['frames'],checkpoint_count=r['checkpoint_count'],A_confirmation_pulses=r['A_confirmation_pulses'],
   observed_active_main_states=r['observed_active_main_states'],final_fields=r['final_fields'],initial_state=r['initial_state'],preparation_reference=r['preparation_reference'],
   validation=name+'/validation.json',repeat_validation=name+'/repeat-validation.json',checkpoints=name+'/checkpoints.json',frame_services=name+'/frame-services.json',input_plan=name+'/input-plan.json',
   audio_callbacks=name+'/audio-callbacks.json',full_WAV=name+'/full-flow.wav',images={p['label']:name+'/'+p['image']for p in json.loads((first/'checkpoints.json').read_text())},
   nonempty_repeat_artifact_checks=repeat['nonempty_artifact_checks'],PCM_stereo_sample_frames=r['full_audio']['stereo_sample_frames']))
 summary=dict(native_case_count=len(receipts),frames_first_run=sum(r['frames']for r in receipts),frames_both_runs=2*sum(r['frames']for r in receipts),checkpoint_count=sum(r['checkpoint_count']for r in receipts),
   nonempty_repeat_artifact_checks=sum(c['nonempty_repeat_artifact_checks']for c in cases),formal_JSON_repeat_checks=len(FORMAL)*len(receipts),
   excluded_empty_VRAM=sum(len(r['excluded_empty_VRAM'])for r in receipts),excluded_snapshot_metadata_JSON=sum(len(r['excluded_snapshot_metadata_JSON'])for r in receipts),
   PCM_stereo_sample_frames_first_run=sum(r['full_audio']['stereo_sample_frames']for r in receipts),PCM_stereo_sample_frames_both_runs=2*sum(r['full_audio']['stereo_sample_frames']for r in receipts),
   sample_rate=48000,additional_core_memory_writes=0,failed_count=0,native_internal_CPU_trace=False,source_CPU_comparisons_in_this_receipt=0)
 evidence=dict(schema='phase11-native-scene-flows-v1',status='passed',rom_sha256=ROM_SHA,core=receipts[0]['core'],summary=summary,native_cases=cases,
    dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in (Path(__file__),ROOT/'scripts/nes_service_runtime.py',ROOT/'scripts/nes_runtime.py')])
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',rom_sha256=ROM_SHA,**summary,evidence_sha256=sha(out/'evidence.json')))
 lines=['# Phase11 原Nestopia三类控制回放','', '完整原ROM/冻结Nestopia运行，原RGB与48000Hz双声道16bit PCM直接来自libretro callbacks。脚本不修改ROM、不新增core RAM/SRAM、ready或result写入。每帧完整RAM/SRAM/RGB/PCM哈希、活跃三controller字段、palette、NMI/PPU/IRQ、音频RAM与全部PCM保留。原字段观察不是内部CPU/NMItrace，也不能证明恢复源码自身合成PCM。','',
        f'双次独立回放：首跑{summary["frames_first_run"]}帧，两跑{summary["frames_both_runs"]}帧；{summary["checkpoint_count"]}checkpoint；{summary["nonempty_repeat_artifact_checks"]}非空artifact逐项hash相同，另明确排除{summary["excluded_empty_VRAM"]}个0B VRAM导出与目录metadata JSON。正式6类JSON逐字节一致，PNG/RAM/SRAM/state/WAV均非空。','']
 for c in cases:
  lines +=[f'## {c["title"]}','',f'{c["frames"]}帧，{c["checkpoint_count"]}checkpoint，A确认脉冲{c["A_confirmation_pulses"]}。最终global={c["final_fields"]["global_state"]}、NMI={c["final_fields"]["nmi_scene"]}，active={c["final_fields"]["active_controller"]}/{c["final_fields"]["active_main"]}/{c["final_fields"]["active_phase"]}。','']
  if c['case']=='cold-battle':lines +=['从原冷启动，用已有78步7738帧普通输入计划，保留原capture标记，追加B2+release180。说明是进入战场与控制交互周期，没有声称一场战争胜利。','']
  elif c['case']=='ordinary-attack-return':lines +=['起点继承phase3唯一敌坐标准备：0600从20→3、0614从14→16。起点原global4/battle3/sub2，由原程序自行产生普通攻击参数；本轮仅原按钮将四列命令设後退、确认结果并返回，无新增参数或ready写入。','']
  else:lines +=['起点继承旧明示单挑fixture-entry：global7、两ID/HP80与5、C991参数及旧RNG起点，原E2E8初始化尚未运行。本轮加载该只读state后只用A2/release30和最终release90，实际原初始化/动画/体力写回/结果/返回均由core执行；不能称自然战役进入单挑。精确旧准备在preparation_reference和该case validation中保留。','']
  lines +=[f'- [逐帧证据]({c["frame_services"]})',f'- [实际输入计划]({c["input_plan"]})',f'- [检查点图片与字段]({c["checkpoints"]})',f'- [完整原PCM WAV]({c["full_WAV"]})',f'- [首跑验证]({c["validation"]})',f'- [第二跑逐artifact复验]({c["repeat_validation"]})','']
 lines +=['主态首次观察仅在匹配global/NMI活跃scene时计入；inactive原数组仍可在原RAM查看，但不会当成覆盖证据。每种scene/main首次观测和global/NMI变化已保存；PNG取实际core帧，无图形模拟。两次snapshot目录metadata JSON不计重复证据；0B VRAM单列排除。','',
   '```sh',"python3 scripts/capture_scene_controller_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat",'```','', '[机核总证据](evidence.json) · [总回执](validation.json)']
 (out/'README.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='passed',summary=summary),ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase11/runtime');p.add_argument('--case',choices=('all',)+CASES,default='all');p.add_argument('--repeat',action='store_true');a=p.parse_args()
 assert sha(a.rom)==ROM_SHA;cases=CASES if a.case=='all'else(a.case,);receipts=[]
 for name in cases:
  first=a.out/name;one=capture(a.rom,first,name)
  if a.repeat:
   second=a.out.parent/'runtime-repeat'/name;two=capture(a.rom,second,name);checks=[]
   for f,expected in one['artifact_sha256'].items():checks.append(dict(artifact=f,equal=expected==two['artifact_sha256'].get(f),**expected))
   assert all(c['equal']for c in checks),[c for c in checks if not c['equal']]
   assert one['frames']==two['frames']and one['final_fields']==two['final_fields']
   repeat=dict(status='passed',first_run=relative(first),second_run=relative(second),all_hashes_equal=True,nonempty_artifact_checks=len(checks),artifacts=checks,
      formal_JSON_exact_parity=list(FORMAL),excluded_directory_metadata_JSON=one['excluded_snapshot_metadata_JSON'],excluded_empty_VRAM=one['excluded_empty_VRAM'])
   write(first/'repeat-validation.json',repeat)
  receipts.append(one)
  print(json.dumps(dict(case=name,status=one['status'],frames=one['frames'],pulses=one['A_confirmation_pulses'],final=one['final_fields']['global_state'],active=one['final_fields']['active_controller'],checkpoints=one['checkpoint_count']),ensure_ascii=False),flush=True)
 if a.repeat:aggregate(a.out,receipts)
if __name__=='__main__':main()
