#!/usr/bin/env python3
"""A short zero-preparation military-allocation route and passive pointer trace.

Only this new producer, a separate phase24 core and new phase24 outputs are
written. The original ROM/core and all ancestor captures remain immutable.
"""
from pathlib import Path
import argparse, collections, ctypes as C, hashlib, json, shutil, struct, subprocess, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext

ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
OBSERVER_SHA='16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase24-observer/observed/nestopia_libretro.dylib'
UPSTREAM=ROOT/'.toolchain/phase24-observer/upstream'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
MOTHER=ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/action1-allocation-ready.state'
RUN=ROOT/'analysis/phase24/runtime'
BUFFER_KEYS=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
WORDS=36
RECORD_BYTES=WORDS*4
SNAPSHOT_BYTES=10240
PLAN=[
 (10,(),'allocation-settled'),
 (2,('down',),'row1-input'),(20,(),'row1-settled'),
 (2,('down',),'row2-input'),(20,(),'row2-settled'),
 (2,('right',),'allocate-input'),(20,(),'allocated'),
 (2,('left',),'return-input'),(20,(),'returned'),
 (2,('down',),'end-row-input'),(20,(),'end-row-settled'),
 (2,('a',),'commit-input'),(60,(),'city-world-returned')]

def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def rel(path):return str(Path(path).resolve().relative_to(ROOT))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def pin(path):return dict(path=rel(path),bytes=Path(path).stat().st_size,sha256=sha(path))
def serialized(rt):
 n=rt.core.retro_serialize_size();buf=C.create_string_buffer(n)
 assert rt.core.retro_serialize(buf,n)
 return buf.raw

def fields(r,s):
 ids=list(s[32*r[0x402]+17:32*r[0x402]+27]) if r[0x402]<30 else []
 officers={}
 for i in (131,5,30):
  q=0x3C0+12*i;raw=s[q:q+12]
  officers[str(i)]=dict(address=0x6000+q,raw12=list(raw),troops_raw16=int.from_bytes(raw[8:10],'little'),troops_low10=int.from_bytes(raw[8:10],'little')&1023)
 return dict(global_main_007A=r[0x7A],NMI_scene_0078=r[0x78],city_state_0400_0403=list(r[0x400:0x404]),
  row_0012=r[0x12],row_047A=r[0x47A],end_row_047B=r[0x47B],mode_047C=r[0x47C],
  working_reserve_042C_042D=int.from_bytes(r[0x42C:0x42E],'little'),city_reserve_raw16=int.from_bytes(s[32*r[0x402]+12:32*r[0x402]+14],'little') if r[0x402]<30 else None,
  city_roster10=ids,UI_cache_0151_015A=list(r[0x151:0x15B]),officers=officers,
  frame_end_ZP_0000_0023=list(r[:0x24]),all30_city_auxiliary_bytes=[[s[c*32+o]for o in (1,28,29,30,31)]for c in range(30)],
  all30_city_records_raw32=[list(s[c*32:c*32+32])for c in range(30)])

def decode_event(raw_record,frame=None,sequence=None):
 """Decode phase24's exact 36-u32/144-byte observer ABI, without inference."""
 w=struct.unpack('<36I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record)
 assert len(w)==WORDS
 seq,f,cycle,kind,pc,buspc,address,value,a,x,y,p,sp,banks,scratch,working,permission,storage=w[:18]
 if frame is not None:assert f==frame
 if sequence is not None:assert seq==sequence
 pages=[banks>>shift&255 for shift in (0,8,16,24)]
 bank=pages[(pc-0x8000)//8192]if 0x8000<=pc<=0xFFFF else None
 zp=[v>>shift&255 for v in w[18:27]for shift in (0,8,16,24)]
 city=[w[27]>>shift&255 for shift in (0,8,16,24)]
 ui=[w[28]>>shift&255 for shift in (0,8,16,24)]
 stack=[w[30]>>shift&255 for shift in (0,8,16,24)]
 target='opcode_boundary'if kind==2 else'pointer_0000_0001_write'if address<0x2000 and(address&0x7FF)in(0,1)else'city_auxiliary'if 0x6000<=address<0x63C0 and(address&31)in(1,28,29,30,31)else'allocation_SRAM_bus'
 return dict(sequence=seq,frame=f,cycle=cycle,kind={0:'read',1:'write_attempt',2:'opcode_boundary',3:'word_read_low',4:'word_read_high'}[kind],
  opcode_PC=None if pc==0xFFFF else pc,bus_PC=buspc,physical_bank=bank,actual_PRG_banks=pages,
  rom_offset=None if bank is None else 16+bank*8192+(pc&8191),address=address,value=value,A=a,X=x,Y=y,P=p,SP=sp,
  ZP_0000_0023=zp,pointer_0000_0001=zp[0]|zp[1]<<8,saved_pointer_0010_0011=zp[16]|zp[17]<<8,
  scratch_0053_0054=[scratch&255,scratch>>8&255],pointer_0022_0023=scratch>>16,
  working_0036_0039=[working>>shift&255 for shift in (0,8,16,24)],city_state_0400_0403=city,
  row_0012=ui[0],row_047A=ui[1],end_row_047B=ui[2],mode_047C=ui[3],working_reserve_042C_042D=w[29]&65535,
  stack_above_SP_4bytes=stack,stack_top_word_raw=stack[0]|stack[1]<<8,
  full_snapshot_sequence=w[31]or None,last_CPU_opcode_field=w[32],bus_internal=w[33]&255,bus_external=w[33]>>8&255,
  raw_UI_cache_0151_plus_row=None if w[34]==0xFFFFFFFF else w[34],NMI_scene_0078=w[35]&255,global_main_007A=w[35]>>8&255,
  new_buttons_0081=w[35]>>16&255,CHR_cache_00C2=w[35]>>24&255,
  target_type=target,WRAM_readable=bool(permission&1),WRAM_writable=bool(permission&2),
  physical_storage_byte_after_event=None if storage==0xFFFFFFFF else storage,
  city_index=(address-0x6000)//32 if target=='city_auxiliary'else None,city_offset=(address-0x6000)%32 if target=='city_auxiliary'else None)

def observer_start(rt,out):
 if not hasattr(rt.core,'nestopia_lifecycle_enable'):return None
 core=rt.core
 for name in ('enable','begin_frame'):
  fn=getattr(core,'nestopia_lifecycle_'+name);fn.argtypes=[C.c_uint];fn.restype=None
 for name in ('count','overflow','words','snapshot_count','snapshot_overflow'):
  getattr(core,'nestopia_lifecycle_'+name).restype=C.c_uint
 core.nestopia_lifecycle_data.restype=C.POINTER(C.c_uint32)
 core.nestopia_lifecycle_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_lifecycle_words()==WORDS and sys.byteorder=='little'
 original_run=core.retro_run
 def observed_run():core.nestopia_lifecycle_begin_frame(rt.frames+1);original_run()
 core.retro_run=observed_run;core.nestopia_lifecycle_enable(7)
 schema=dict(schema='phase24-passive-pointer-lifecycle-ABI-v1',bytes_per_record=RECORD_BYTES,words=WORDS,
  raw_layout=['sequence','frame','core_master_cycle_count','kind','opcode_PC_or_FFFF','bus_PC','address','value','A','X','Y','P','SP','actual_PRG_banks_packed4',
   'scratch53_54_22_23_packed4','working36_37_38_39_packed4','WRAM_permissions','physical_storage_after_or_FFFFFFFF',
   *['ZP_%02X_%02X_packed4'%(i,i+3)for i in range(0,0x24,4)],'city400_403_packed4','row12_47A_47B_47C_packed4',
   'working42C_42F_packed4','stack_SPplus1_through4_packed4','full_snapshot_sequence_or_zero','last_CPU_opcode_field','bus_internal_external_packed2','UI_cache151_plus_row_or_FFFFFFFF','NMI78_main7A_buttons81_CHRC2_packed4'],
  sequence='One-based globally contiguous per fresh process; per-frame count reset does not reset sequence.',
  cycle='Original Cpu.cycles.count master-clock count, rebased by original EndFrame. Not wall time and not forcibly frame-zeroed.',
  opcode_PC='Cpu::ExecuteOp entry PC captured before FetchPc8; bus_PC is the actual Cpu.pc at the bus hook. No inferred caller.',
  last_CPU_opcode_field='Raw Cpu.opcode at the hook. At a before-Fetch opcode boundary it still describes the previous opcode; it is not labeled the current opcode.',
  ZP='Direct const copy of physical RAM00..23 after a write event or before a boundary opcode.',
  raw_UI_cache='Byte at RAM0151+RAM0012 only if row<10; not assumed to equal selected officer without raw roster evidence.',
  snapshots=dict(bytes_per_snapshot=SNAPSHOT_BYTES,layout='2048 physical RAM bytes then8192 physical WRAM backing bytes',
   snapshot_sequence='One-based globally contiguous; full_snapshot_sequence links an event to snapshots.bin at (sequence-1)*10240.',
   trigger='Before physical28 D64A or D987 opcode, copied directly into external debug storage, no emulated bus reads.',
   excludes='No instantaneous N163/PPU/APU or whole CPU object snapshot is claimed; event registers/actual PRG are exact.',
   complete_RAM_and_SRAM=True),
  kinds={0:'read',1:'write_attempt',2:'opcode_boundary',3:'word_read_low',4:'word_read_high'},
  watch=dict(pointer_writes='PokeRam and PokeBus writes to physical mirrored RAM00/01',city_aux='CPU bus6000..63BF offsets1/28/29/30/31',
   allocation_SRAM='CPU bus6000..7FFF while physical28 opcodeD817..DA01; includes dummy reads',
   boundaries='Exact physical28 selected D64A/D805..DA01 addresses plus fixed31 F2AF/F2D7/EA7C; see patched source.'),
  overflow='Any event or full-snapshot overflow aborts; never silently discard.',
  scope='New observer core only, paired with this route original-control. Original core has saved-context/frame evidence, not an internal instruction trace.',
  limits=['Bus reads include6502 dummy reads; physical hit is not alone a logical field consumer.',
   'Word-read components are logical components after unchanged map.Peek16, not invented subread timing.',
   'Pointer partial writes can make00/01 invalid temporarily. D987 changes01 before EA7C; EA7C does not write00.',
   'Writes are attempts, with actual backing byte after separately preserved. Debug provider uses no emulated map.Peek.'])
 write(out/'event-schema.json',schema)
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),
  index=(out/'snapshot-index.jsonl').open('w'),sequence=0,snapshots=0,count=0,kinds=collections.Counter(),targets=collections.Counter(),boundaries=collections.Counter())

def observer_drain(rt,obs,out):
 if obs is None:return
 core=rt.core
 assert core.nestopia_lifecycle_overflow()==0 and core.nestopia_lifecycle_snapshot_overflow()==0
 n=core.nestopia_lifecycle_count();raw=C.string_at(core.nestopia_lifecycle_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=core.nestopia_lifecycle_snapshot_count();snap=C.string_at(core.nestopia_lifecycle_snapshot_data(),count*SNAPSHOT_BYTES)
 obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<36I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1
  obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['kind']=='opcode_boundary':obs['boundaries']['%02d:%04X'%(e['physical_bank'],e['opcode_PC'])]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshots']+=1;assert e['full_snapshot_sequence']==obs['snapshots']
   payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:]
   assert list(r[:0x24])==e['ZP_0000_0023'] and r[0x12]==e['row_0012'] and list(r[0x400:0x404])==e['city_state_0400_0403']
   assert [r[0x100+((e['SP']+i)&255)]for i in range(1,5)]==e['stack_above_SP_4bytes']
   item=dict(snapshot_sequence=obs['snapshots'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],
    byte_offset=(obs['snapshots']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),
    actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],
    stack_top_word_raw=e['stack_top_word_raw'],raw_UI_cache_0151_plus_row=e['raw_UI_cache_0151_plus_row'])
   item.update(origin='Separate phase24 passive observer, before actual opcode, not an original-core internal trace.',
    capture_core_sha256=rt.info['core_sha256'],mother=pin(MOTHER),inherited_preparation_byte_writes=0,additional_core_memory_writes=0,
    instantaneous_PPU_APU_N163_state_captured=False,complete_same_route_parity_receipt='analysis/phase24/runtime/validation.json')
   # Exact input exports for the two action-bearing D64A calls and D987;
   # no caller/RTS frame is manufactured.
   if e['opcode_PC']==0xD987 or (e['opcode_PC']==0xD64A and e['new_buttons_0081']&0xC0 and e['mode_047C']==0x10):
    prefix='callee-%04d-%04X'%(obs['snapshots'],e['opcode_PC'])
    (out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
    item['exported_RAM']=prefix+'-ram.bin';item['exported_SRAM']=prefix+'-sram.bin';write(out/(prefix+'.json'),item)
   obs['index'].write(json.dumps(item,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA
 assert sha(core)in(CORE_SHA,OBSERVER_SHA)
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Use a fresh output directory'
 rt=ServiceRuntime(rom,out,core);rows=[];points=[];obs=observer_start(rt,out);plan=[];step_ends=[];total=0
 for n,buttons,label in PLAN:
  plan.append(dict(start_frame=total,frames=n,buttons=list(buttons),capture=label,purpose='Original ordinary controller input, no RAM/SRAM/RNG/readiness writes.'))
  total+=n;step_ends.append(total)
 try:
  # Same original serialize API schedule in both cores, before import and before
  # first frame. Never normalize, truncate or pad opaque serialized buffers.
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(MOTHER)
  (out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0))
  initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial)
  assert initial['city_state_0400_0403']==[3,13,11,0] and initial['working_reserve_042C_042D']==9999
  assert initial['officers']['30']['troops_raw16']==800 and initial['city_roster10'][:3]==[131,5,30]
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();state=serialized(rt);rgb=rt.frame.tobytes();n=NestopiaContext.parse(state)
   assert n.ram==r and n.sram==s
   observer_drain(rt,obs,out)
   f=fields(r,s)
   rows.append(dict(frame=rt.frames,RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rgb),PCM_sha256=digest(pcm),
    whole_serialized_state_sha256=digest(state),whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),
    actual_saved_CPU_registers=n.registers,actual_saved_PRG_banks=list(n.prg_banks),**f))
   # A short route: retain every actually rendered original frame's full state
   # and RAM/SRAM, but only thirteen named screenshots, not fake pre-import RGB.
   label='frame-%03d'%rt.frames
   (out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s)
  for n,buttons,label in PLAN:
   rt.run(n,buttons,observe);rt.frame.save(out/(label+'.png'))
   row=rows[-1];points.append(dict(label=label,frame=rt.frames,image=label+'.png',state='frame-%03d.state'%rt.frames,
    RAM='frame-%03d-ram.bin'%rt.frames,SRAM='frame-%03d-sram.bin'%rt.frames,fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  assert len(rows)==rt.frames==182
  assert rows[55]['officers']['30']['troops_raw16']==900 and rows[55]['working_reserve_042C_042D']==9899
  assert rows[77]['officers']['30']['troops_raw16']==800 and rows[77]['working_reserve_042C_042D']==9999
  final=fields(rt.memory(2),rt.memory(0));assert final['city_state_0400_0403'][:2]==[0,1]
  assert final['officers']==initial['officers'] and final['city_roster10']==initial['city_roster10']
  audio=rt.save_wav(out/'full-audio.wav');audio['path']='full-audio.wav'
  write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  write(out/'preparation.json',dict(additional_core_memory_writes=0,preparation=[],inherited_preparation_byte_writes=0,
   mother_state=rel(MOTHER),mother_sha256=sha(MOTHER),state_imported=True,cold_boot=False,
   ancestry='Frozen phase14 original-core cold-city-domestic-cycle, ordinary cold boot and original buttons, zero preparation. This phase imports its allocation-ready checkpoint; it does not replay or claim a new cold boot.'))
  event_summary=None
  if obs:
   for name in ('raw','decoded','snap','index'):obs[name].close()
   event_summary=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshots'],kinds=dict(obs['kinds']),targets=dict(obs['targets']),boundaries=dict(obs['boundaries']),
    **{key:dict(path=name,bytes=(out/name).stat().st_size,sha256=sha(out/name))for key,name in
       (('raw','bus-events.bin'),('decoded','events.jsonl'),('snapshots','snapshots.bin'),('snapshot_index','snapshot-index.jsonl'))},overflow=0)
  excluded=['validation.json','repeat-validation.json'];artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.name not in excluded and p.stat().st_size}
  dependencies=[Path(__file__),ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',MOTHER,
   MOTHER.with_name(MOTHER.stem+'-ram.bin'),MOTHER.with_name(MOTHER.stem+'-sram.bin'),ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/validation.json']
  result=dict(schema='phase24-native-allocation-pointer-lifecycle-v1',status='passed',variant='observer'if obs else'original-control',
   ROM_sha256=ROM_SHA,core=rt.info,core_path=rel(core),mother=pin(MOTHER),cold_boot=False,state_imported=True,
   inherited_preparation_byte_writes=0,additional_core_memory_writes=0,natural_ordinary_input_route=True,frames=rt.frames,checkpoint_count=len(points),
   input_step_count=len(plan),full_audio=audio,AV=rt.av_info,initial_fields=initial,final_fields=final,
   verified_effects=dict(selected_officer=30,selected_row=2,initial_troops=800,after_right_troops=900,after_left_troops=800,
    initial_working_reserve=9999,after_right_working_reserve=9899,after_left_working_reserve=9999,
    city_world_returned=True,final_city_state=final['city_state_0400_0403'],original_roster_and_all_three_officer_records_restored=True),
   observer_events=event_summary,all_five_complete_buffers_hashed_each_frame=True,full_serialized_buffers_not_normalized=True,
   original_core_internal_instruction_trace=False,observer_sparse_CPU_events=obs is not None,source_CPU_cases=0,
   dependency_pins=[pin(p)for p in dependencies],artifact_sha256=artifacts,
   limits=['This is one natural short ordinary-input continuation, not a fresh cold boot or a universal equivalence proof.',
    'Saved frame-end REG/PRG differ in meaning from observer opcode-instant REG/PRG. NMI maps physical27/28 transiently.',
    'No instantaneous PPU/APU/N163 snapshot is exported with the sparse callee RAM/SRAM; no fake hardware return is supplied.',
    'City auxiliary bus events may be dummy reads. Zero events do not prove unused or assign an official field name.'])
  write(out/'validation.json',result)
  print(json.dumps(dict(variant=result['variant'],frames=rt.frames,final_city=final['city_state_0400_0403'],events=event_summary and obs['count'],snapshots=event_summary and obs['snapshots'])),flush=True)
 finally:rt.close()

def provenance(out):
 folder=out/'core-provenance';folder.mkdir(parents=True,exist_ok=True)
 assert subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()==COMMIT
 files=['source/core/NstCpu.cpp','source/core/NstCpu.hpp','source/core/NstMemory.hpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp','libretro/Makefile','libretro/Makefile.common']
 sources=[]
 for name in files:
  original=subprocess.check_output(['git','-C',str(UPSTREAM),'show',COMMIT+':'+name]);target=folder/'upstream'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original)
  modified=(UPSTREAM/name).read_bytes();sources.append(dict(path=name,original_sha256=digest(original),patched_sha256=digest(modified)))
 # Include untracked debug files in an ordinary reproducible git diff patch.
 patch=subprocess.check_output(['git','-C',str(UPSTREAM),'diff','--binary',COMMIT,'--','source/core/NstCpu.cpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp'])
 for name in ('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc'):
  raw=(UPSTREAM/name).read_text();lines=raw.splitlines();patch+=('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n--- /dev/null\n+++ b/'+name+'\n@@ -0,0 +1,'+str(len(lines))+' @@\n'+''.join('+'+line+'\n'for line in lines)).encode()
 (folder/'observer.patch').write_bytes(patch)
 for name in ('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc','source/core/NstCpu.cpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp'):
  target=folder/'patched'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((UPSTREAM/name).read_bytes())
 shutil.copyfile('/tmp/phase24-observer-build.log',folder/'observer-build.log')
 result=dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,
  original_git_tree=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse',COMMIT+'^{tree}'],text=True).strip(),
  original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),unchanged_phase21_core=pin(ROOT/'.toolchain/phase21-observer/observed/nestopia_libretro.dylib'),
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),build_working_directory='libretro',
  build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],
  modified_emulator_object_layout=False,debug_storage='External static event/snapshot arrays only, no fields added to CPU/board or serialized objects.',
  snapshot_method='Direct const physical RAM/WRAM backing copy. No map.Peek, emulated bus reads or device callbacks.',
  patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=name,sha256=sha(UPSTREAM/name))for name in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],toolchain_in_archive=False)
 write(folder/'build.json',result)

def aggregate(out):
 second=out.parent/(out.name+'-repeat');runs=[];all_checks=[];original_rows=None
 for variant in ('original-control','observer'):
  one,two=out/variant,second/variant;a=json.loads((one/'validation.json').read_text());b=json.loads((two/'validation.json').read_text())
  assert a==b and a['status']=='passed'
  for item in a['dependency_pins']:assert sha(ROOT/item['path'])==item['sha256']
  for name,item in a['artifact_sha256'].items():
   assert(one/name).read_bytes()==(two/name).read_bytes()and sha(one/name)==item['sha256'] and(one/name).stat().st_size==item['bytes']>0
   all_checks.append(dict(first=rel(one/name),repeat=rel(two/name),**item))
  current=json.loads((one/'frame-services.json').read_text())
  if original_rows is None:original_rows=current
  assert current==original_rows,'Frame payloads must be identical between original and observer, without metadata fields or normalization'
  assert(one/'initial.state').read_bytes()==(out/'original-control/initial.state').read_bytes()
  for index,row in enumerate(current):
   for key in BUFFER_KEYS:assert row[key]==original_rows[index][key]
  repeat=dict(status='passed',variant=variant,first=rel(one),repeat=rel(two),nonempty_artifact_checks=len(a['artifact_sha256']),
   all_bytes_exact=True,all_serialized_buffers_full=True,script_sha256=sha(__file__))
  write(one/'repeat-validation.json',repeat)
  runs.append(dict(variant=variant,frames=a['frames'],validation=variant+'/validation.json',repeat_validation=variant+'/repeat-validation.json',
   checkpoints=variant+'/checkpoints.json',frame_services=variant+'/frame-services.json',input_plan=variant+'/input-plan.json',
   full_audio=variant+'/full-audio.wav',observer_events=a['observer_events']))
 obs=out/'observer';events=[json.loads(line)for line in(obs/'events.jsonl').read_text().splitlines()]
 raw=(obs/'bus-events.bin').read_bytes();assert len(raw)==len(events)*RECORD_BYTES
 for i,e in enumerate(events):assert decode_event(raw[i*RECORD_BYTES:(i+1)*RECORD_BYTES],sequence=i+1)==e
 lifecycle=[]
 for e in events:
  if e['kind']=='opcode_boundary'and e['physical_bank']==28 and e['opcode_PC']==0xD987:
   suffix=[x for x in events if x['sequence']>=e['sequence']and x['frame']==e['frame']]
   after=next(x for x in suffix if x['kind']=='opcode_boundary'and x['opcode_PC']==0xD9F0 and x['physical_bank']==28)
   division=next(x for x in suffix if x['kind']=='opcode_boundary'and x['opcode_PC']==0xEA7C and x['physical_bank']==31)
   returned=next(x for x in suffix if x['kind']=='opcode_boundary'and x['opcode_PC']==0xD9AC and x['physical_bank']==28)
   exit_event=next(x for x in suffix if x['kind']=='opcode_boundary'and x['opcode_PC']==0xDA01 and x['physical_bank']==28)
   prefix=[x for x in events if x['sequence']<e['sequence']and x['frame']==e['frame']and x['kind']=='opcode_boundary']
   city_entry=next(x for x in prefix if x['opcode_PC']==0xF2AF and x['physical_bank']==31)
   city_return=next(x for x in prefix if x['opcode_PC']==0xD80B and x['physical_bank']==28)
   officer_entry=next(x for x in prefix if x['opcode_PC']==0xF2D7 and x['physical_bank']==31)
   officer_return=next(x for x in prefix if x['opcode_PC']==0xD817 and x['physical_bank']==28)
   assert city_entry['A']==11 and city_return['pointer_0000_0001']==0x6160
   assert officer_entry['A']==30 and officer_entry['Y']==19 and officer_entry['pointer_0000_0001']==0x6160
   assert officer_return['pointer_0000_0001']==0x6528
   assert city_entry['SP']+2==city_return['SP'] and officer_entry['SP']+2==officer_return['SP']
   assert e['pointer_0000_0001']==after['pointer_0000_0001']==exit_event['pointer_0000_0001']==0x6528
   assert after['saved_pointer_0010_0011']==0x6528 and division['saved_pointer_0010_0011']==0x6528
   assert division['pointer_0000_0001']!=0x6528
   lifecycle.append(dict(frame=e['frame'],entry_sequence=e['sequence'],division_entry_sequence=division['sequence'],division_return_sequence=returned['sequence'],
    city_pointer_entry_sequence=city_entry['sequence'],city_pointer_return_sequence=city_return['sequence'],
    city_pointer=0x6160,raw_city_id=city_entry['A'],raw_roster_offset=officer_entry['Y'],raw_officer_ID=officer_entry['A'],
    officer_pointer_entry_sequence=officer_entry['sequence'],officer_pointer_return_sequence=officer_return['sequence'],
    actual_NMI_PRG_banks=e['actual_PRG_banks'],
    restored_sequence=after['sequence'],RTS_before_sequence=exit_event['sequence'],officer_pointer=0x6528,division_temporary_whole_pair=division['pointer_0000_0001'],
    actual_entry_SP=e['SP'],actual_RTS_before_SP=exit_event['SP'],return_word_raw=e['stack_top_word_raw'],
    scope='D987 saves00/01 to10/11, reuses01/02 for division operands, calls EA7C, restores00/01 before officer+8/+9 accesses. EA7C does not write00.'))
 assert len(lifecycle)==2
 write(out/'pointer-lifetimes.json',dict(status='observed',instances=lifecycle,limits='Exact two observed calls only, not a universal pointer-liveness proof.'))
 summary=dict(status='passed',natural_routes=1,state_imports_per_run=1,cold_boot=False,ancestor_preparation_bytes=0,additional_core_memory_writes=0,
  core_variants=2,fresh_process_runs=4,frames_per_route=182,frames_first_run_controls=364,frames_both_runs_controls=728,
  all_five_complete_buffers_match_original_each_frame=True,all_initial_serialized_buffers_equal=True,all_nonempty_artifacts_repeat_exact=True,
  nonempty_artifact_repeat_checks=len(all_checks),original_checkpoint_count=len(json.loads((out/'original-control/checkpoints.json').read_text())),
  PNG_count=sum(1 for x in all_checks if x['first'].endswith('.png')),WAV_count=sum(1 for x in all_checks if x['first'].endswith('.wav')),
  event_count=len(events),full_RAM_SRAM_snapshot_count=runs[1]['observer_events']['full_RAM_SRAM_snapshots'],D987_lifecycles=len(lifecycle),
  original_core_internal_instruction_trace=False,source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase24-native-pointer-lifecycle-flows-v1',**summary,runs=runs,build='core-provenance/build.json',mother=pin(MOTHER),
  decode_function='scripts/capture_native_pointer_lifecycle.py:decode_event',script_sha256=sha(__file__),
  limits=['One zero-preparation ordinary-input continuation, not a new cold boot.',
   'Only the separate new core has sparse internal events. Full original-core frame/buffer parity is demonstrated for this route.',
   'Instantaneous callee RAM/SRAM/AXYP/SP/PRG are preserved. N163/device state is not supplied as an instantaneous callee snapshot.',
   'No new official city+1/tail meaning or unused-field proof follows from a missing event.'])
 write(out/'repeat-artifact-checks.json',all_checks);write(out/'evidence.json',evidence)
 write(out/'validation.json',dict(**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(__file__)))
 (out/'README.md').write_text('''# 阶段24：原配兵界面的指针生命周期\n\n本轮只选G086配兵链。导入阶段14自然冷启动案的`action1-allocation-ready.state`，祖先与本轮均零数值准备；这是存档续行，不冒称重新冷启动。普通无键等待、Down两次、Right、Left、Down至结束、A，182帧后原城市状态回到0/1。ID30兵800→900→800；工作预备兵9999→9899→9999。提交后工作缓冲另被复用，不能将其末值10115解释为城预备兵；完整城记录与原武将记录另存。\n\n[总证据](evidence.json) · [回执](validation.json) · [指针实例](pointer-lifetimes.json) · [构建](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_native_pointer_lifecycle.py)\n\n原ROM与固定原核心、阶段21核心未修改。独立阶段24核心只加被动hook与外部静态日志数组，没有改CPU/board对象布局；直接const复制物理RAM与WRAM，不触发额外仿真总线读取。两种核心各fresh进程双跑，逐帧完整RGB、48kHz PCM、2048B RAM、8192B SRAM和未归一化完整serialized API buffer相等。包括相同首次serialize查询时机与导入日程。`repeat-artifact-checks.json`保留全部非空复跑文件hash。只有新观察核心具内部事件，不能追认原核心有内部trace。\n\n原NMI短暂映射physical27/28；帧末主循环通常已恢复16/10/11/31。因此每事件使用真实opcode PC及实际PRG页，另存bus时CPU.pc，不能从帧末银行推断事件银行。36-u32原始ABI逐条由公开decode_event解码并复核连续序号；完整布局见observer/event-schema.json。PokeRam/PokeBus覆盖物理镜像RAM00/01写，城市辅助总线访问与配兵范围SRAM总线访问分列；虚读与真实指针语义必须分别解释。\n\n两次F2AF输入city11建立6160；Y=17+row2=19取原名册ID30，F2D7建立武将指针6528。D987先将00/01保存至10/11，再重用01/02作为除法参数，临时wholepair不是可用武将指针。EA7C本身不写00。D9F0前恢复6528，之后才访问武将+8/+9。两次实际D987入口/RTS前SP分别F1/F3，原返回word分别D839/D880，不注入哨兵栈。这里只证明两个实际实例。\n\nD64A/D987入口稀疏保存完整2K/8K，与AXYP/SP/PC、4实际PRG页和原栈字节关联。`snapshots.bin`每条10240B，`snapshot-index.jsonl`与事件sequence交叉引用；四份action-bearing callee导出同名JSON/RAM/SRAM便于独立源码对照。未捕获瞬时N163/PPU/APU内部状态，不能补造该硬件上下文。Source/CPU验证另列，不计入本轮Native病例。\n\n每个实际新帧保存state/RAM/SRAM；13张原256×240PNG与原48k立体声WAV可核，未生成替代图声。城市+1与尾4字段仍无正式命名；本短路线未观察到它们的专用写入，不能由零事件证明unused。本轮不重跑祖先长历史、不复制原ROM、不改任何旧阶段产物。\n''')
 print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=RUN);p.add_argument('--core',type=Path)
 p.add_argument('--verify-passivity',action='store_true');p.add_argument('--aggregate-only',action='store_true');a=p.parse_args()
 if a.aggregate_only:aggregate(a.out.resolve());return
 if a.verify_passivity:
  assert a.core is None;a.out.mkdir(parents=True,exist_ok=True);provenance(a.out)
  for variant,core in (('original-control',ORIGINAL),('observer',OBSERVER)):
   for folder in (a.out/variant,a.out.parent/(a.out.name+'-repeat')/variant):
    subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--core',str(core),'--out',str(folder)],check=True)
  aggregate(a.out.resolve())
 else:
  assert a.core is not None;capture(a.rom,a.core.resolve(),a.out)

if __name__=='__main__':main()
