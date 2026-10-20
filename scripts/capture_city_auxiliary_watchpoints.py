#!/usr/bin/env python3
"""Separate passive-core observations, checked against the pinned original core.

No prior runtime, source, ROM or original dylib is edited. Observer events are
new-core evidence, never retroactively attributed to old original-core captures.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,sys,subprocess,struct,collections,shutil
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
from capture_f8_native_flows import fields

ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ORIGINAL_CORE=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
ORIGINAL_CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
TOOLS=ROOT/'.toolchain/phase21-observer'
UPSTREAM=TOOLS/'upstream';COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
RUN=ROOT/'analysis/phase21/runtime'
CASES=('natural-F8-accept','natural-F8-reject')
VARIANTS={'original-control':ORIGINAL_CORE,'pristine-rebuild':TOOLS/'baseline/nestopia_libretro.dylib','observer-accept':TOOLS/'observed/nestopia_libretro.dylib'}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def rel(path):return str(Path(path).resolve().relative_to(ROOT))
def serialized(rt):
 size=rt.core.retro_serialize_size();raw=C.create_string_buffer(size)
 assert rt.core.retro_serialize(raw,size)
 return raw.raw

def decode_event(raw_record,frame=None,sequence=None):
 """Decode one unchanged 72B ABI record; optional arguments assert identity."""
 w=struct.unpack('<18I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record)
 assert len(w)==18
 seq,event_frame,cycle,kind,pc,buspc,address,value,a,x,y,p,sp,banks,scratch,working,permission,storage=w
 if frame is not None:assert event_frame==frame
 if sequence is not None:assert seq==sequence
 pages=[banks>>shift&255 for shift in(0,8,16,24)];bank=pages[(pc-0x8000)//8192]if 0x8000<=pc<0xFFFF else None
 target='sparse_opcode_boundary'if kind==2 else'city_auxiliary'if 0x6000<=address<0x63C0 else'cpu_scratch_0053'
 return dict(sequence=seq,frame=event_frame,cycle=cycle,kind={0:'read',1:'write_attempt',2:'opcode_boundary',3:'word_read_low',4:'word_read_high'}[kind],opcode_PC=pc if pc!=0xFFFF else None,bus_PC=buspc,
  physical_bank=bank,rom_offset=None if bank is None else 16+bank*8192+(pc&8191),actual_PRG_banks=pages,address=address,value=value,
  A=a,X=x,Y=y,P=p,SP=sp,scratch_0053_0054=[scratch&255,scratch>>8&255],pointer_0022_0023=scratch>>16,
  working_0036_0039=[working>>shift&255 for shift in(0,8,16,24)],target_type=target,city_index=(address-0x6000)//32 if target=='city_auxiliary'else None,city_offset=(address-0x6000)%32 if target=='city_auxiliary'else None,
  WRAM_readable=bool(permission&1),WRAM_writable=bool(permission&2),storage_byte_after_event=None if storage==0xFFFFFFFF else storage)

def observer_start(rt,out,case):
 if not hasattr(rt.core,'nestopia_watch_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  fn=getattr(core,'nestopia_watch_'+name);fn.argtypes=[C.c_uint];fn.restype=None
 for name in('count','overflow','words'):getattr(core,'nestopia_watch_'+name).restype=C.c_uint
 core.nestopia_watch_data.restype=C.POINTER(C.c_uint32)
 assert core.nestopia_watch_words()==18 and sys.byteorder=='little'
 original_run=core.retro_run
 def observed_run():core.nestopia_watch_begin_frame(rt.frames+1);original_run()
 core.retro_run=observed_run;core.nestopia_watch_enable(7)
 schema=dict(schema='phase21-passive-city-bus-events-v1',ABI='18 unsigned32 words, host little-endian; no header or dropped-record normalization',bytes_per_record=72,
  raw_words=['sequence','frame','core_master_cycle_count','kind_code','opcode_PC_or_FFFF','bus_PC','address','value','A','X','Y','P','SP','actual_PRG_banks_packed4','scratch_53_54_22_23_packed4','working_36_37_38_39_packed4','WRAM_permission_bits','storage_byte_after_event_or_FFFFFFFF'],
  kinds={0:'read',1:'write_attempt',2:'opcode_boundary',3:'word_read_low',4:'word_read_high'},
  sequence='Starts at1 and is globally contiguous across recorded events for this fresh process; per-frame buffer reset does not reset sequence.',
  cycle='Unmodified Cpu.cycles.count master-clock units, rebased by original Cpu::EndFrame; carries residual cycles and is not a wall-clock time or a frontend-forced zero.',
  original_reference_case=case,original_reference_frames=rel(ROOT/'analysis/phase20/runtime'/case/'frame-services.json'),frame_identity='Full cold boot local frame N equals reference frame N; zero state import.',
  watch_targets=dict(city_range=[0x6000,0x63BF],city_offsets=[1,28,29,30,31],RAM_write_normalized_address=0x53,
   opcode_boundaries={'11':[0xC6CC,0xC71A,0xC71C,0xC732,0xC735,0xC75F,0xC762,0xC794],'31':[0xE89A,0xE8A9]}),
  overflow='Any nonzero core overflow counter aborts the observation; no silent drop is accepted.',
  limits=['These are events from the separately rebuilt observer core, not an internal trace retroactively attributed to the original dylib.',
   'CPU bus accesses may include dummy accesses. A bus hit is not by itself an official field-name or semantic-use proof.',
   'Word low/high events describe the logical components after the unchanged map.Peek16 expression; they do not claim subread temporal order.',
   'Writes are CPU bus attempts. WRAM writable/readable flags and physical backing byte after the event are separately observed without emulated reads.',
   'Opcode_PC FFFF denotes a bus observation outside an active ExecuteOp; no instruction provenance is invented.'])
 write(out/'event-schema.json',schema)
 return dict(binary=(out/'bus-events.bin').open('wb'),JSON=(out/'events.jsonl').open('w'),count=0,kinds=collections.Counter(),targets=collections.Counter(),last_sequence=0)

def observer_drain(rt,observer):
 if observer is None:return 0
 assert rt.core.nestopia_watch_overflow()==0,'Observer event buffer overflow; observation is incomplete'
 count=rt.core.nestopia_watch_count();raw=C.string_at(rt.core.nestopia_watch_data(),count*72);observer['binary'].write(raw)
 for w in struct.iter_unpack('<18I',raw):
  r=decode_event(w,rt.frames,observer['last_sequence']+1);observer['last_sequence']=r['sequence']
  observer['JSON'].write(json.dumps(r,separators=(',',':'))+'\n');observer['kinds'][r['kind']]+=1;observer['targets'][r['target_type']]+=1
 observer['count']+=count;return count

def capture(rom,core,out,case,limit=None):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL_CORE)==ORIGINAL_CORE_SHA
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'A fresh output directory is required'
 parent=ROOT/'analysis/phase20/runtime'/case;receipt=json.loads((parent/'validation.json').read_text());reference=json.loads((parent/'frame-services.json').read_text());plan=json.loads((parent/'input-plan.json').read_text())
 assert receipt['status']=='passed'and receipt['cold_boot']and not receipt['state_imported']and receipt['additional_core_memory_writes']==0
 rt=ServiceRuntime(rom,out,Path(core).resolve());rows=[];failures=[];points=[];observer=observer_start(rt,out,case)
 interesting={10479:'actual-ruler4-status00',10490:'actual-cold-frame10490',10491:'actual-cold-frame10491',10492:'actual-cold-frame10492',10500:'actual-F8-produced',10885:'actual-choice-menu',receipt['verified_effects']['first_observed_reply']['frame']:'actual-original-reply',receipt['frames']:'actual-next-human-world'}
 target=receipt['frames']if limit is None else min(limit,receipt['frames'])
 try:
  # The original capture queried retro_serialize_size before its first frame.
  # This API caches its first measured capacity. Reproduce the call sequence;
  # do not pad, trim or normalize either original or rebuilt buffers.
  initial=serialized(rt);(out/'initial.state').write_bytes(initial)
  (out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0))
  assert initial==(parent/'initial.state').read_bytes(),'Initial full serialized API buffer differs'
  def observe(runtime):
   ram,sram=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();raw=serialized(rt);rgb=rt.frame.tobytes();old=reference[rt.frames-1]
   events=observer_drain(rt,observer)
   hashes=dict(RAM_sha256=digest(ram),SRAM_sha256=digest(sram),RGB_sha256=digest(rgb),PCM_sha256=digest(pcm),whole_serialized_state_sha256=digest(raw))
   mismatches={k:dict(original=old[k],current=v)for k,v in hashes.items()if old[k]!=v}
   if mismatches:
    label='first-mismatch-frame%d'%rt.frames;rt.snapshot(label);failures.append(dict(frame=rt.frames,mismatches=mismatches));raise AssertionError(f'Original core parity failure at frame{rt.frames}: {list(mismatches)}')
   n=NestopiaContext.parse(raw);assert n.ram==ram and n.sram==sram
   rows.append(dict(frame=rt.frames,**hashes,PCM_bytes=len(pcm),PCM_stereo_sample_frames=len(pcm)//4,PCM_stop_byte=len(rt.pcm),all_five_match_original=True,actual_saved_CPU_registers=n.registers,actual_saved_PRG_banks=n.prg_banks,observer_event_count=events))
   if rt.frames in interesting:
    label=interesting[rt.frames];rt.snapshot(label);points.append(dict(frame=rt.frames,label=label,fields=fields(ram,sram),RAM=label+'-ram.bin',SRAM=label+'-sram.bin',image=label+'.png',state=label+'.state'))
  for p in plan:
   count=min(p['frames'],target-rt.frames)
   if count<=0:break
   rt.run(count,p.get('buttons',()),observer=observe)
  assert rt.frames==target and len(rows)==target
  wav=rt.save_wav(out/'full-audio.wav');assert wav['PCM_sha256']==receipt['full_audio']['PCM_sha256']if limit is None else True
  if limit is None:
   assert wav['WAV_sha256']==receipt['full_audio']['WAV_sha256']
   if observer is None:(out/'full-audio.wav').unlink()
  wav.update(saved_path='full-audio.wav'if(observer or limit is not None)else None,original_reference_path=rel(parent/'full-audio.wav'))
  write(out/'frame-parity.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  if observer:
   observer['binary'].close();observer['JSON'].close()
   event_summary=dict(event_count=observer['count'],kinds=dict(observer['kinds']),targets=dict(observer['targets']),raw_ABI_bytes=(out/'bus-events.bin').stat().st_size,raw_ABI_sha256=sha(out/'bus-events.bin'),events_JSONL_sha256=sha(out/'events.jsonl'),overflow=0)
  else:event_summary=None
  result=dict(schema='phase21-original-core-passive-comparison-v1',status='passed',case=case,frames=target,complete_original_input_route=limit is None,
   stream_role='passive_observer'if observer else'original_control'if rt.info['core_sha256']==ORIGINAL_CORE_SHA else'pristine_rebuild',
   current_core=rt.info,current_core_path=rel(core),original_core_path=rel(ORIGINAL_CORE),original_core_sha256=ORIGINAL_CORE_SHA,rom_sha256=ROM_SHA,
   all_frame_RAM_SRAM_RGB_PCM_whole_serialized_buffers_equal=True,serialized_buffer_normalized=False,additional_core_memory_writes=0,cold_boot=True,state_imported=False,
   original_reference_validation=rel(parent/'validation.json'),original_reference_validation_sha256=sha(parent/'validation.json'),original_reference_frames=rel(parent/'frame-services.json'),original_reference_frames_sha256=sha(parent/'frame-services.json'),
   full_audio=wav,checkpoint_count=len(points),failures=[],Native_internal_instruction_trace=False,observer_core_CPU_bus_log=observer is not None,observer_events=event_summary,original_core_internal_trace_claim=False,script_sha256=sha(__file__))
  artifacts={};empty=[];excluded=[]
  for p in sorted(out.iterdir()):
   if not p.stat().st_size:empty.append(p.name);continue
   if p.suffix in('.bin','.state','.png','.wav','.jsonl')or p.name in('frame-parity.json','checkpoints.json','input-plan.json','audio-callbacks.json','event-schema.json'):
    artifacts[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
   elif p.suffix=='.json':excluded.append(p.name)
  result.update(artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=excluded,initial_full_serialized_bytes_equal=True,
   first_serialize_query_at_cold_boot=True,additional_callback_into_emulated_CPU=False,scope='Bounded original input route and all five full frame-buffer hashes, not a universal equivalence or semantic field-name theorem.')
  write(out/'validation.json',result);print(json.dumps(dict(status='passed',case=case,frames=target,current_core_sha256=rt.info['core_sha256'])),flush=True);return result
 except BaseException:
  write(out/'failed-parity.json',dict(status='failed',frames_observed=rt.frames,core=rt.info,failures=failures,script_sha256=sha(__file__)));raise
 finally:
  if observer:
   observer['binary'].close();observer['JSON'].close()
  rt.close()

def provenance(out):
 p=out/'core-provenance';p.mkdir(parents=True,exist_ok=True)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=UPSTREAM,text=True).strip();assert commit==COMMIT
 tracked=('source/core/NstCpu.cpp','source/core/NstCpu.hpp','source/core/NstMemory.hpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp','libretro/Makefile','libretro/Makefile.common','COPYING')
 pins=[]
 for name in tracked:
  raw=subprocess.check_output(['git','show',COMMIT+':'+name],cwd=UPSTREAM);dst=p/'upstream'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
  pins.append(dict(path=name,original_sha256=digest(raw),patched_sha256=sha(UPSTREAM/name)))
 patch=subprocess.check_output(['git','diff','--','source/core/NstCpu.cpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp'],cwd=UPSTREAM)
 for name in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc'):
  cp=subprocess.run(['git','diff','--no-index','--','/dev/null',name],cwd=UPSTREAM,capture_output=True);assert cp.returncode==1;patch+=cp.stdout
  pins.append(dict(path=name,original_sha256=None,patched_sha256=sha(UPSTREAM/name)))
 (p/'observer.patch').write_bytes(patch)
 for name in('baseline-build.log','observer-build.log'):shutil.copy2(TOOLS/name,p/name)
 result=dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,original_git_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=UPSTREAM,text=True).strip(),
  original_core=dict(path=rel(ORIGINAL_CORE),sha256=sha(ORIGINAL_CORE)),pristine_rebuild=dict(path=rel(VARIANTS['pristine-rebuild']),sha256=sha(VARIANTS['pristine-rebuild'])),passive_observer=dict(path=rel(VARIANTS['observer-accept']),sha256=sha(VARIANTS['observer-accept'])),
  compiler=subprocess.check_output(['xcrun','clang++','--version'],text=True).strip(),build_working_directory='libretro',build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],
  modified_emulator_object_layout=False,observation_storage='Separate static trace array and scalar metadata, never added to CPU/board serialized objects',
  patch_sha256=digest(patch),source_files=pins,toolchain_in_release_archive=False)
 write(p/'build.json',result);return result

def aggregate(out):
 comparisons=[];runs=[]
 for variant,core in VARIANTS.items():
  one=out/variant;two=out.parent/(out.name+'-repeat')/variant;a=json.loads((one/'validation.json').read_text());b=json.loads((two/'validation.json').read_text())
  assert a['status']==b['status']=='passed'and a['frames']==b['frames']==11589
  assert a['artifact_sha256']==b['artifact_sha256']and a['observer_events']==b['observer_events']and a['full_audio']==b['full_audio']
  checks=[]
  for name,pin in a['artifact_sha256'].items():
   for folder in(one,two):assert(folder/name).stat().st_size==pin['bytes']>0 and sha(folder/name)==pin['sha256']
   checks.append(dict(path=name,**pin))
  repeat=dict(status='passed',variant=variant,first_run=rel(one),second_run=rel(two),all_artifact_bytes_exact=True,artifact_checks=len(checks),artifacts=checks,full_serialized_buffers_not_normalized=True,script_sha256=sha(__file__))
  write(one/'repeat-validation.json',repeat)
  runs.append(dict(variant=variant,case=a['case'],stream_role=a['stream_role'],core_sha256=a['current_core']['core_sha256'],frames=a['frames'],validation=variant+'/validation.json',repeat_validation=variant+'/repeat-validation.json',checkpoints=variant+'/checkpoints.json',frame_parity=variant+'/frame-parity.json',input_plan=variant+'/input-plan.json',events=variant+'/events.jsonl'if a['observer_events']else None,raw_ABI=variant+'/bus-events.bin'if a['observer_events']else None,event_schema=variant+'/event-schema.json'if a['observer_events']else None,observer_events=a['observer_events'],full_audio=a['full_audio'],additional_core_memory_writes=0,state_imported=False,cold_boot=True))
  comparisons.append(repeat)
 obs=out/'observer-accept';r=json.loads((obs/'validation.json').read_text());counts=collections.Counter();scan=[];saved=[];rng=[]
 with(obs/'bus-events.bin').open('rb')as raw,(obs/'events.jsonl').open()as decoded:
  index=0
  while record:=raw.read(72):
   index+=1;x=decode_event(record,sequence=index);assert x==json.loads(next(decoded));counts[(x['target_type'],x['kind'])]+=1
   if x['kind']=='opcode_boundary':
    if x['physical_bank']==11:scan.append(x)
    if x['opcode_PC']==0xE89A:saved.append(x)
    if x['opcode_PC']==0xE8A9:
     start=saved.pop();assert start['X']==x['X'];rng.append(dict(entry_sequence=start['sequence'],exit_sequence=x['sequence'],entry_frame=start['frame'],exit_frame=x['frame'],X_entry=start['X'],X_exit=x['X'],scratch53_at_entry=start['scratch_0053_0054'][0],scratch53_at_exit=x['scratch_0053_0054'][0]))
  assert not saved and next(decoded,None)is None and index==r['observer_events']['event_count']
 sparse=collections.Counter(hex(x['opcode_PC'])for x in scan);assert sparse['0xc71a']==3 and sparse['0xc75f']==sparse['0xc762']==711 and sparse['0xc732']==0
 for p in json.loads((obs/'checkpoints.json').read_text()):
  n=NestopiaContext.parse((obs/p['state']).read_bytes());assert n.ram==(obs/p['RAM']).read_bytes()and n.sram==(obs/p['SRAM']).read_bytes()
 summary=dict(status='passed',natural_input_routes=1,core_variants=3,fresh_process_runs=6,frames_per_complete_route=11589,frames_first_run_controls=34767,frames_both_runs_controls=69534,observer_frames=11589,
  all_five_complete_buffer_hashes_match_original_each_frame=True,all_initial_full_API_buffers_equal=True,all_raw_artifacts_repeat_exact=True,additional_core_memory_writes=0,state_imports=0,failed_count=0,
  observer_event_count=index,observer_city_auxiliary_events=sum(n for(k,_),n in counts.items()if k=='city_auxiliary'),observer_RAM53_write_events=counts['cpu_scratch_0053','write_attempt'],
  bounded_recruitment_observation=dict(C71A_entry_count=sparse['0xc71a'],C75F_loop_steps=sparse['0xc75f'],C762_loop_checks=sparse['0xc762'],C732_recruitment_RNG_calls=sparse['0xc732'],C794_recruitment_success_exits=sparse['0xc794']),E89A_observed_entry_exit_pairs=len(rng),E89A_all_observed_X_preserved=True,
  output_equivalence_scope='The six declared cold-boot executions and recorded boundaries only; not a universal binary-equivalence or unused-field proof.')
 write(out/'RNG-save-restore-observations.json',dict(status='observed',pairs=rng,scope='Sparse observer-core entry/exit X and intervening write events. No universal interrupt-atomic claim.'))
 evidence=dict(schema='phase21-passive-city-watch-flows-v1',status='passed',summary=summary,runs=runs,original_reference_case='analysis/phase20/runtime/natural-F8-accept',build='core-provenance/build.json',decode_function='scripts/capture_city_auxiliary_watchpoints.py:decode_event',script_sha256=sha(__file__))
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(__file__)))
 (out/'README.md').write_text('''# 阶段21：独立被动观测核心\n\n原ROM、原核心及阶段20文件未修改。官方135dfa6源码先作未修改重建，再新增独立被动记录核心；三种核心每种各fresh进程双跑同一自然冷启动F8接受路线。原始RGB、PCM、2048B RAM、8192B SRAM、完整serialized API buffer逐帧与冻结20数据比较，包含首帧前initial序列化时序，不补零、不截断或归一化。\n\n[总证据](evidence.json) · [回执](validation.json) · [构建来源](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_city_auxiliary_watchpoints.py)\n\n新内部总线日志只属于独立observer核心，不追认旧原核心有内部trace。每事件保留实际opcode PC、实际PRG页、寄存器、地址和总线值；写尝试与WRAM权限、后存储值分列。数组溢出即失败。word低/高事件是原Peek16表达式的逻辑分量，不宣称其内部子读顺序。\n\n观察612个城市辅助字节总线事件，其中312读含300次原STA IndY dummy读取及12次BD97门槛读取；300写尝试来自原初始化清零和整城市模板复制。dummy读取和bulk覆盖不能给单字节命名或证明独立玩法。未命中只说明本条实际路径未观察，不能证明unused。\n\n在野招募C71A扫描3次，每次237记录；C732计0，未实际随机招募或成功。E89A另有12组真实入口/RTS前边界，观察X保持；中断窗口语义须结合完整RAM53事件，不扩为普遍原子性。原10490/10491/10492关键检查点由完整cold路线保留，不使用较弱的13帧存档重入路径冒充同帧。\n\n全48kHz实际PCM保留：observer案保存新全WAV，原控制和未修改重建的完整WAV先逐字节核同阶段20，再仅保留冻结原WAV路径与SHA，避免冗余文件。路径metadata JSON与0B VRAM不计入非空复跑。构建工具链不进入最终ZIP，官方来源、原文件、补丁与精确构建命令可复核。\n''')
 print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--core',type=Path);p.add_argument('--out',type=Path,default=RUN);p.add_argument('--case',choices=CASES,default=CASES[0]);p.add_argument('--limit',type=int);p.add_argument('--verify-passivity',action='store_true');a=p.parse_args()
 if a.verify_passivity:
  assert a.core is None and a.limit is None and a.case=='natural-F8-accept';a.out.mkdir(parents=True,exist_ok=True);provenance(a.out)
  for variant,core in VARIANTS.items():
   for out in(a.out/variant,a.out.parent/(a.out.name+'-repeat')/variant):subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--core',str(core),'--out',str(out),'--case',a.case],check=True)
  aggregate(a.out)
 else:
  assert a.core is not None;capture(a.rom,a.core,a.out,a.case,a.limit)
if __name__=='__main__':main()
