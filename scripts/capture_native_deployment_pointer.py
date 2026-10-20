#!/usr/bin/env python3
"""Original ordinary-input deployment continuation and separate passive observer.

Frozen producers, source modules and original cores are imported read-only.
"""
from pathlib import Path
import argparse,collections,ctypes as C,hashlib,json,shutil,struct,subprocess,sys,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
from capture_native_appearance_pointer import serialized,sha,ROM_SHA,CORE_SHA,decode_event as decode_parent
MOTHER=ROOT/'analysis/phase11/runtime/cold-battle/battle-enter-confirm.state'
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase26-observer/observed/nestopia_libretro.dylib'
OBSERVER_SHA='ed7a9942c789f94595e8a8a842a9574245df5e97f8e57e062b2208e95a6814b1'
UPSTREAM=ROOT/'.toolchain/phase26-observer/upstream'
RUN=ROOT/'analysis/phase26/runtime';COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
WORDS=44;RECORD_BYTES=176;SNAPSHOT_BYTES=10240
PLAN=[(35,('a',),'original-invasion-confirmation'),(125,(),'deployment-and-original-battle-return')]
FIVE=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def rel(path):return str(Path(path).resolve().relative_to(ROOT))
def pin(path):return dict(path=rel(path),bytes=Path(path).stat().st_size,sha256=sha(path))
def fields(r,s):
 return dict(global_007A=r[0x7A],NMI_0078=r[0x78],city_0400_0403=list(r[0x400:0x404]),battle_0500_0501=list(r[0x500:0x502]),
  raw_6F44=s[0xF44],raw_packed_0507=r[0x507],battle_city_050E=r[0x50E],neighbor_city_052A=r[0x52A],
  strategy_side_6F91=s[0xF91],noncommander_count_6F94=s[0xF94],strategies_6FA1_6FB4=list(s[0xFA1:0xFB5]),
  unit_y_0614=list(r[0x614:0x628]),unit_x_0600=list(r[0x600:0x614]),officer_ids_0664=list(r[0x664:0x678]),
  frame_end_ZP_0000_002F=list(r[:0x30]),city_aux150=[s[32*i+j]for i in range(30)for j in(1,28,29,30,31)],
  all30_city_records_raw32=[list(s[32*i:32*i+32])for i in range(30)],battle_setup_0500_0533=list(r[0x500:0x534]),
  profile_counts_6F99_6FA0=list(s[0xF99:0xFA1]),unit_cache_6FC9_6FDC=list(s[0xFC9:0xFDD]),frame_end_raw_bank_selectors_DE_DF=list(r[0xDE:0xE0]))

def ancestry():
 folder=ROOT/'analysis/phase11/runtime/cold-battle';v=json.loads((folder/'validation.json').read_text())
 assert v['status']=='passed'and v['natural_gameplay']and not v['controlled_fixture']and v['initial_state']is None
 assert v['preparation_reference']is None and v['inherited_preparation']=={}and v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
 assert v['core']['core_sha256']==CORE_SHA and v['artifact_sha256'][MOTHER.name]['sha256']==sha(MOTHER)
 assert sha(ROOT/'scripts/capture_scene_controller_flows.py')==v['script_sha256']
 point=next(x for x in json.loads((folder/'checkpoints.json').read_text())if x['state']==MOTHER.name);assert point['frame']==5626
 return dict(parent_validation=pin(folder/'validation.json'),parent_checkpoints=pin(folder/'checkpoints.json'),parent_producer=pin(ROOT/'scripts/capture_scene_controller_flows.py'),
  parent_input_plan=pin(folder/'input-plan.json'),original_cold_plan=pin(ROOT/v['original_cold_plan']),parent_checkpoint=point,
  ancestor_cold_boot=True,ancestor_state_imported=False,ancestor_numeric_preparation_bytes=0,new_case_state_imported=True,new_case_cold_boot=False,
  scope='Pinned formal phase11 cold-battle case declares real cold boot, no imported state and no numeric/ready/result preparation. This new case imports its frame5626 checkpoint; the historical cold route is not rerun.')

def probe(rom,out):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA
 out=Path(out);out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir())
 rt=ServiceRuntime(rom,out,ORIGINAL);rows=[];last=None
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(MOTHER)
  (out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0))
  def observe(runtime):
   nonlocal last
   r,s=rt.memory(2),rt.memory(0);state=serialized(rt);ctx=NestopiaContext.parse(state);f=fields(r,s)
   row=dict(frame=rt.frames,registers=ctx.registers,actual_PRG_banks=list(ctx.prg_banks),RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rt.frame.tobytes()),PCM_sha256=digest(rt.pcm_frame()),state_sha256=digest(state),**f);rows.append(row)
   key=(r[0x7A],r[0x78],r[0x400],r[0x401],r[0x500],r[0x501])
   if key!=last or rt.frames<=4:
    label='frame-%03d'%rt.frames;(out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s);rt.frame.save(out/(label+'.png'))
    print(json.dumps(dict(frame=rt.frames,key=key,PC=ctx.registers['pc'],banks=list(ctx.prg_banks))),flush=True);last=key
  plan=[(35,('a',)),(180,())]
  for count,buttons in plan:rt.run(count,buttons,observe)
  state=serialized(rt);(out/'final.state').write_bytes(state);(out/'final-ram.bin').write_bytes(rt.memory(2));(out/'final-sram.bin').write_bytes(rt.memory(0));rt.frame.save(out/'final.png')
  write(out/'frames.json',rows);write(out/'input-plan.json',[dict(frames=n,buttons=list(b))for n,b in plan])
  write(out/'provenance.json',dict(mother=rel(MOTHER),mother_sha256=sha(MOTHER),state_imported=True,cold_boot=False,additional_core_memory_writes=0,inherited_preparation_byte_writes=0,core_sha256=CORE_SHA,ROM_sha256=ROM_SHA,frames=rt.frames,internal_instruction_trace=False))
 finally:rt.close()

def decode_event(raw_record,frame=None,sequence=None):
 w=struct.unpack('<44I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record);assert len(w)==44
 e=decode_parent(w[:40],frame,sequence);a=e['address'];p=a&0x7FF;kind=e['kind'];pc=e['opcode_PC'];zp=e['ZP_0000_002F'];pointer=zp[0x20]|zp[0x21]<<8
 if kind=='opcode_boundary':target='opcode_boundary'
 elif 0x6000<=a<0x63C0 and(a&31)in(1,28,29,30,31):target='city_auxiliary_bus'
 elif a<0x2000 and 0x20<=p<=0x25:target='pointer_scratch_RAM_write'
 elif a<0x2000 and 0x600<=p<0x628:target='unit_coordinate_RAM_write'
 elif 0x6F90<=a<0x6FB5:target='strategy_cache_SRAM_write'
 elif a in(0xE000,0xE800,0xF000)and kind=='write_attempt':target='PRG_mapper_port_write'
 else:target='selected_deployment_ROM_bus'
 read=kind in('read','word_read_low','word_read_high');bank=e['actual_PRG_banks'][(a-0x8000)//8192]if read and 0x8000<=a<0x10000 else None
 e.update(target_type=target,pointer_0020_0021=pointer,battle_setup_0506_0507_050E_052A=[w[40]>>b&255 for b in(0,8,16,24)],
  strategy_side_6F91=w[41]&255,noncommander_count_6F94=w[41]>>8&255,raw_bank_selector_DE=w[41]>>16&255,raw_bank_selector_DF=w[41]>>24&255,
  profile_counts_6F99_6FA0=[v>>b&255 for v in w[42:44]for b in(0,8,16,24)],
  data_physical_bank=bank,data_ROM_offset=16+bank*8192+(a&8191)if bank is not None else None,
  logical_coordinate_read=read and e['physical_bank']==8 and pc in(0xB272,0xB278,0xB290,0xB296)and a==((pointer+e['Y'])&65535))
 return e

def start_observer(rt,out):
 if not hasattr(rt.core,'nestopia_deployment_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  fn=getattr(core,'nestopia_deployment_'+name);fn.argtypes=[C.c_uint];fn.restype=None
 for name in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_deployment_'+name).restype=C.c_uint
 core.nestopia_deployment_data.restype=C.POINTER(C.c_uint32);core.nestopia_deployment_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_deployment_words()==WORDS and sys.byteorder=='little'
 original=core.retro_run
 def run():core.nestopia_deployment_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_deployment_enable(7)
 parent=json.loads((ROOT/'analysis/phase25/runtime/natural-appearance-pointer/observer/event-schema.json').read_text())
 added=['RAM0506_0507_050E_052A_packed4','SRAM6F91_side_6F94_count_RAMDE_DF_packed4','SRAM6F99_6F9C_profile_counts_packed4','SRAM6F9D_6FA0_profile_counts_packed4']
 write(out/'event-schema.json',dict(schema='phase26-passive-deployment-pointer-ABI-v1',words=WORDS,bytes_per_record=RECORD_BYTES,
  raw_layout=parent['raw_layout']+added,first40_words='Exact frozen phase25 raw layout; the pure parent decoder is reused, target types are reclassified for this core.',
  sequence='One-based globally contiguous per fresh process, not reset by begin_frame.',cycle='Original cycles.count with unchanged frame rebasing.',
  opcode_PC='ExecuteOp PC before FetchPc8. bus_PC is actual Cpu.pc at the hook. last_CPU_opcode_field is the previous opcode at the pre-Fetch boundary.',
  frame_identity='Local frame after one pinned natural state import, not a cold-boot frame number.',
  snapshot=dict(bytes=10240,layout='2048 physical RAM then8192 physical WRAM backing',before_entries=[0xB130,0xB1B0,0xB2AE,0xB312],physical_bank=8,
   method='Const direct physical backing copies, no map.Peek/device API.',N163_PPU_APU_instant_state_captured=False),
  watch=dict(ROM_reads='All original ROM bus reads while opcode physical8 B130..B3FC, including original instruction/operand fetches. Four logical coordinate reads require pointer+Y equality.',
   pointer_writes='Physical mirrored RAM20..25 through both original PokeRam/PokeBus fast paths; fullZP00..2F snapshot.',
   unit_writes='Physical RAM0600..0627 original writes, SRAM6F90..6FB4 writes, actual PRG portsE000/E800/F000 writes.',
   city_auxiliary='All original bus reads/write attempts to150 city+1/+28..31 addresses.'),
  original_reference='original-control',overflow='Hard failure on either event or snapshot overflow; no silent dropping.',
  limits=['Only this independent observer provides internal bus/opcode events; the fixed original core provides separate complete five-buffer controls.',
   'Read bus events include instruction fetches and hardware dummy reads, not automatically logical data consumers.',
   'Sparse software contexts contain no instantaneous N163, PPU or APU state.']))
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),
  index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter(),targets=collections.Counter())

def drain(rt,obs,out):
 if obs is None:return
 core=rt.core;assert core.nestopia_deployment_overflow()==core.nestopia_deployment_snapshot_overflow()==0
 n=core.nestopia_deployment_count();raw=C.string_at(core.nestopia_deployment_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=core.nestopia_deployment_snapshot_count();snap=C.string_at(core.nestopia_deployment_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<44I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1
  obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count']
   payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:]
   assert list(r[:0x30])==e['ZP_0000_002F']and e['physical_bank']==8 and e['opcode_PC']in(0xB130,0xB1B0,0xB2AE,0xB312)
   prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=8,entry=e['opcode_PC'],
    byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),
    actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],
    stack_top_word_raw=e['stack_top_word_raw'],capture_core_sha256=rt.info['core_sha256'],mother=pin(MOTHER),
    inherited_preparation_byte_writes=0,additional_core_memory_writes=0,instantaneous_N163_PPU_APU_captured=False,
    origin='Separate phase26 observer actual opcode-boundary software capture. Entry may be reached by original JMP; existing stack is retained without invented caller.',
    exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin')
   write(out/(prefix+'.json'),row);obs['index'].write(json.dumps(row,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA and sha(core)in(CORE_SHA,OBSERVER_SHA)
 out=Path(out);out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Refuse to overwrite existing capture'
 rt=ServiceRuntime(rom,out,core);obs=start_observer(rt,out);rows=[];points=[];plan=[]
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(MOTHER)
  (out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0));initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial)
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);state=serialized(rt);ctx=NestopiaContext.parse(state);pcm=rt.pcm_frame();drain(rt,obs,out);label='frame-%03d'%rt.frames
   row=dict(frame=rt.frames,RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rt.frame.tobytes()),PCM_sha256=digest(pcm),whole_serialized_state_sha256=digest(state),
    whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),actual_saved_CPU_registers=ctx.registers,actual_saved_PRG_banks=list(ctx.prg_banks),**fields(r,s));rows.append(row)
   (out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s);rt.frame.save(out/(label+'.png'))
   points.append(dict(label=label,frame=rt.frames,image=label+'.png',state=label+'.state',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  for count,buttons,label in PLAN:
   plan.append(dict(start_frame=rt.frames,frames=count,buttons=list(buttons),label=label,purpose='Original ordinary input, no game/RNG/request/PC/ready preparation.'));rt.run(count,buttons,observe)
  assert rt.frames==160;final=fields(rt.memory(2),rt.memory(0));assert initial['global_007A']==2 and final['global_007A']==4 and final['NMI_0078']==3 and final['battle_0500_0501']==[10,4]
  assert initial['city_aux150']==final['city_aux150'];wav=rt.save_wav(out/'full-audio.wav');wav['path']='full-audio.wav'
  write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  ancestor=ancestry();write(out/'preparation.json',dict(mother=pin(MOTHER),state_imported=True,cold_boot=False,preparation=[],additional_core_memory_writes=0,inherited_preparation_byte_writes=0,ancestry=ancestor))
  events=None
  if obs:
   for name in('raw','decoded','snap','index'):obs[name].close()
   events=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshot_count'],kinds=dict(obs['kinds']),targets=dict(obs['targets']),overflow=0,
    **{key:dict(path=name,bytes=(out/name).stat().st_size,sha256=sha(out/name))for key,name in [('raw','bus-events.bin'),('decoded','events.jsonl'),('snapshots','snapshots.bin'),('snapshot_index','snapshot-index.jsonl')]})
  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.stat().st_size and p.name not in('validation.json','repeat-validation.json')}
  deps=[Path(__file__),ROOT/'scripts/capture_native_appearance_pointer.py',ROOT/'scripts/capture_native_pointer_lifecycle.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',
   MOTHER,MOTHER.with_name(MOTHER.stem+'-ram.bin'),MOTHER.with_name(MOTHER.stem+'-sram.bin'),ROOT/'analysis/phase11/runtime/validation.json',ROOT/'analysis/phase25/runtime/natural-appearance-pointer/observer/event-schema.json']
  deps += [ROOT/x['path']for x in ancestor.values()if isinstance(x,dict)and 'path'in x and 'sha256'in x]
  receipt=dict(schema='phase26-native-deployment-pointer-v1',status='passed',variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,core=rt.info,core_path=rel(core),AV=rt.av_info,
   mother=pin(MOTHER),ancestry=ancestor,state_imported=True,cold_boot=False,additional_core_memory_writes=0,inherited_preparation_byte_writes=0,natural_ordinary_input_route=True,
   frames=160,checkpoint_count=len(points),input_step_count=len(plan),initial_fields=initial,final_fields=final,full_audio=wav,observer_events=events,
   verified_effects=dict(original_global2_to3_to4=True,endpoint_battle=[10,4],city_aux150_unchanged=True,ordinary_A35_then_release125=True),
   artifact_sha256=artifacts,dependency_pins=[pin(p)for p in deps],full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,
   limits=['Only the new independent core provides internal events. Actual saved frame-end fields are not substituted for opcode-time pointers or mapper banks.',
    'Entry software captures preserve actual registers and caller stack; instantaneous N163/PPU/APU is not captured.',
    'One original natural continuation. Untaken formation/helper branches remain distinct CPU fixture scope; zero auxiliary hits do not prove unused fields.'])
  write(out/'validation.json',receipt);print(json.dumps(dict(variant=receipt['variant'],frames=160,endpoint=final['battle_0500_0501'],events=events and events['count'],snapshots=events and events['full_RAM_SRAM_snapshots'])),flush=True)
 finally:rt.close()

def provenance(out):
 base=out/'core-provenance';base.mkdir(parents=True,exist_ok=True)
 assert subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()==COMMIT
 names=['source/core/NstCpu.cpp','source/core/NstCpu.hpp','source/core/NstMemory.hpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp','libretro/Makefile','libretro/Makefile.common'];sources=[]
 for name in names:
  raw=subprocess.check_output(['git','-C',str(UPSTREAM),'show',COMMIT+':'+name]);p=base/'upstream'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  sources.append(dict(path=name,original_sha256=digest(raw),patched_sha256=sha(UPSTREAM/name)))
 patch=subprocess.check_output(['git','-C',str(UPSTREAM),'diff','--binary',COMMIT,'--','source/core/NstCpu.cpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp','libretro/Makefile'])
 for name in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc'):
  lines=(UPSTREAM/name).read_text().splitlines();patch+=('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n--- /dev/null\n+++ b/'+name+'\n@@ -0,0 +1,'+str(len(lines))+' @@\n'+''.join('+'+line+'\n'for line in lines)).encode()
 (base/'observer.patch').write_bytes(patch)
 for name in names+['source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc']:
  p=base/'patched'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((UPSTREAM/name).read_bytes())
 for name in('clean','build','dependency-rebuild'):shutil.copyfile('/tmp/phase26-observer-'+name+'.log',base/('observer-'+name+'.log'))
 old=[('.toolchain/phase21-observer/observed/nestopia_libretro.dylib','45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d'),
  ('.toolchain/phase24-observer/observed/nestopia_libretro.dylib','16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'),
  ('.toolchain/phase25-observer/observed/nestopia_libretro.dylib','7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0')]
 for name,value in old:assert sha(ROOT/name)==value
 assert sha(OBSERVER)==sha(UPSTREAM/'libretro/nestopia_libretro.dylib')==OBSERVER_SHA
 write(base/'build.json',dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,parent_frozen_patch=pin(ROOT/'analysis/phase25/runtime/core-provenance/observer.patch'),
  original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),unchanged_old_observers=[pin(ROOT/n)for n,_ in old],
  clean_command=['make','clean'],build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],first_build_clean_new_tree=True,final_source_clean_build=True,
  include_dependency_declared='../source/core/NstCpu.o: ../source/core/NstWatch.cpp.inc ../source/core/NstWatch.hpp',dependency_rebuild_byte_identical=True,
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=n,sha256=sha(UPSTREAM/n))for n in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],
  modified_emulator_object_layout=False,extra_emulated_bus_reads=0,extra_emulated_bus_writes=0,
  snapshot_method='Const RAM/WRAM backing copies only, no map.Peek/map.Poke/device API.',toolchain_in_archive=False,
  ABI_change='44u32 rather than40: append0506/0507/050E/052A,6F91/6F94/DE/DF and8 profile count bytes; all are backing reads, no emulated side effects.'))

def aggregate(out,rom_path):
 repeat=out.parent/(out.name+'-repeat');checks=[];original_rows=None;streams=[];images=wavs=0
 rom=Path(rom_path).read_bytes();assert digest(rom)==ROM_SHA
 for variant in('original-control','observer'):
  first,second=out/variant,repeat/variant;a=json.loads((first/'validation.json').read_text());b=json.loads((second/'validation.json').read_text());assert a==b and a['status']=='passed'
  for name,p in a['artifact_sha256'].items():
   assert(first/name).read_bytes()==(second/name).read_bytes()and sha(first/name)==p['sha256'];checks.append(dict(first=rel(first/name),repeat=rel(second/name),**p));images+=name.endswith('.png');wavs+=name.endswith('.wav')
  rows=json.loads((first/'frame-services.json').read_text())
  if original_rows is None:original_rows=rows
  assert rows==original_rows
  for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):assert(first/name).read_bytes()==(out/'original-control'/name).read_bytes()
  write(first/'repeat-validation.json',dict(status='passed',first=rel(first),second=rel(second),artifact_checks=len(a['artifact_sha256']),all_bytes_exact=True,script_sha256=sha(__file__)))
  callbacks=json.loads((first/'audio-callbacks.json').read_text());assert len(callbacks)==len(rows)==160
  with wave.open(str(first/'full-audio.wav'))as wav:
   assert(wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
   for row,cb in zip(rows,callbacks):
    pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']
    assert wav.tell()*4==row['PCM_stop_byte'];label='frame-%03d'%row['frame']
    r=(first/(label+'-ram.bin')).read_bytes();s=(first/(label+'-sram.bin')).read_bytes();state=(first/(label+'.state')).read_bytes();ctx=NestopiaContext.parse(state)
    assert ctx.ram==r and ctx.sram==s and ctx.registers==row['actual_saved_CPU_registers']and list(ctx.prg_banks)==row['actual_saved_PRG_banks']
    assert digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
    for name in(label+'.state',label+'-ram.bin',label+'-sram.bin',label+'.png'):assert(first/name).read_bytes()==(out/'original-control'/name).read_bytes()
    with Image.open(first/(label+'.png'))as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
   assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes']
  streams.append(dict(variant=variant,validation=variant+'/validation.json',repeat_validation=variant+'/repeat-validation.json',checkpoints=variant+'/checkpoints.json',frame_services=variant+'/frame-services.json',full_audio=variant+'/full-audio.wav',frames=160,events=a['observer_events']))
 folder=out/'observer';events=[json.loads(x)for x in(folder/'events.jsonl').read_text().splitlines()];raw=(folder/'bus-events.bin').read_bytes();assert len(raw)==len(events)*RECORD_BYTES
 for i,e in enumerate(events):assert decode_event(raw[i*RECORD_BYTES:(i+1)*RECORD_BYTES],sequence=i+1)==e
 logical=[e for e in events if e['logical_coordinate_read']];entries=[e for e in events if e['full_snapshot_sequence']]
 assert logical and all(e['data_physical_bank']==6 for e in logical)and any(e['opcode_PC']==0xB1B0 for e in entries)
 for e in events:
  if e['data_ROM_offset']is not None:assert e['value']==rom[e['data_ROM_offset']]
  if e['target_type']=='pointer_scratch_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
 aux=[e for e in events if e['target_type']=='city_auxiliary_bus'];profile=[e for e in events if e['target_type']=='strategy_cache_SRAM_write']
 pairs=[]
 for e in logical:
  address=(0x614 if e['opcode_PC']in(0xB272,0xB290)else 0x600)+e['X']
  store=next(x for x in events if x['sequence']>e['sequence']and x['target_type']=='unit_coordinate_RAM_write'and x['address']==address and x['value']==e['value'])
  pairs.append(dict(logical_read=e,following_original_store=store))
 write(out/'deployment-observations.json',dict(schema='phase26-actual-deployment-observations-v1',logical_coordinate_reads=logical,full_software_entries=entries,city_auxiliary_bus_events=aux,
  logical_read_to_unit_store_pairs=pairs,actual_profile_strategy_writes=profile,logical_coordinate_read_count=len(logical),software_snapshot_count=len(entries),
  scope='Exact selected opcode/bus events from the independent26 observer. Other ROM reads include actual code/operand fetches; no frame-end pointer substitution.',
  untaken_formation_entries=[pc for pc in(0xB2AE,0xB312)if not any(e['opcode_PC']==pc for e in entries)]))
 write(out/'repeat-artifact-checks.json',dict(status='passed',checks=checks,nonempty_artifact_checks=len(checks),full_serialized_buffers_not_normalized=True))
 summary=dict(natural_routes=1,core_variants=2,fresh_process_runs=4,original_first_frames=160,all_control_frames=640,original_checkpoints=160,
  nonempty_artifact_repeat_checks=len(checks),PNG_checks=images,WAV_checks=wavs,observer_events=len(events),full_software_snapshots=len(entries),logical_coordinate_reads=len(logical),
  city_auxiliary_bus_events=len(aux),additional_core_memory_writes=0,ancestor_preparation_bytes=0,cold_boots=0,state_imports=4,
  all_five_complete_buffers_equal_each_frame=True,all_complete_initial_API_buffers_equal=True,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,Source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase26-natural-G107-native-v1',status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),mother=pin(MOTHER),ancestry=ancestry(),
  summary=summary,streams=streams,core_provenance=pin(out/'core-provenance/build.json'),observations='deployment-observations.json',
  Source_CPU_cases=0,original_core_internal_CPU_trace=False,limits=['Imported original natural cold-route checkpoint; no new cold boot or numeric preparation.',
   'Internal events only from separate passive core; no instantaneous N163/PPU/APU capture.',
   'Observed coordinate map is only this route. Untaken paths require separate CPU fixtures. Zero auxiliary hits are bounded negatives, not unused-field proof.'])
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),evidence_sha256=sha(out/'evidence.json'),**summary))
 (out/'README.md').write_text('''# 阶段26：自然部署坐标指针 G107

本轮从冻结的 `phase11/runtime/cold-battle/battle-enter-confirm.state` 继续。原案例回执记录为无导入、无数值/结果/ready准备的真实冷启动普通输入路线；该保存点是其第5626帧。新案例自身导入保存点，不能称新冷启动。祖先与本轮全部准备均为0，精确来源见每个stream的 `preparation.json` 和根 `evidence.json`。

普通输入只有 A35帧、松开125帧。固定原核心与独立26观察核心各用两个fresh Python进程重放。完整initial序列化调用顺序相同；每帧原始2K RAM、8K SRAM、256×240 RGB、实际48kHz stereo PCM和全部serialized state均一致，不截断、不补零、不归一化。每一帧PNG/2K/8K/state、完整WAV、callbacks与正式JSON还做同核心两跑精确对照。

观察核心独立文件、独立hash与来源补丁在 `core-provenance/`；未改原ROM、固定核心或21/24/25观察核心。首次编译使用干净新树，Makefile显式依赖watch include；强制更新include触发CPU重编，重建二进制逐字一致。新hooks只读CPU/PRG/物理RAM和WRAM backing，不调用map.Peek、不增加仿真总线读写、不改变可序列化对象布局。44u32 ABI与原始日志详见 `observer/event-schema.json`，溢出会失败。

实际local139命中 B130、B1B0、B2AE，side0、非统帅数量3。B312在本路线未经过，不能称自然覆盖。四个G107逻辑位点共8次读取，实际20/21=8D4E、数据物理bank6；逐读及后继单位坐标写见 `deployment-observations.json`。完整原始ROM总线日志也含指令/操作数字节取指，不能把所有read事件当作字段消费者。帧末指针和银行不能替代这些opcode时点。

三个实际entry保留全部2K/8K、AXYP/SP/PC、真实四PRG、原软件返回栈。B130可由原JMP进入，不假造JSR caller。瞬时N163/PPU/APU设备状态没有捕获；后续Source/CPU验证如需该设备环境，必须另列显式共同夹具。

最终global4/NMI3、battle10/sub4。原初始化和后续场景执行都由核心完成，没有伪ack、跳PC、RNG或结果写入。未观察到150个城市辅助字节的总线事件仅是本160帧路线的有界负结果，不能证明unused或官方字段名。不是战役胜利、Source循环模拟器或整个ROM完成声明。
''')
 print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--probe',type=Path);p.add_argument('--child',type=Path);p.add_argument('--core',type=Path);p.add_argument('--out',type=Path,default=RUN);a=p.parse_args()
 if a.probe:probe(a.rom,a.probe);return
 if a.child:assert a.core;capture(a.rom,a.core,a.child);return
 out=a.out.resolve();repeat=out.parent/(out.name+'-repeat');assert not out.exists()and not repeat.exists(),'Refuse to overwrite formal outputs'
 out.mkdir(parents=True);provenance(out)
 for target in(out,repeat):
  for variant,core in(('original-control',ORIGINAL),('observer',OBSERVER)):
   subprocess.run([sys.executable,str(Path(__file__).resolve()),str(a.rom.resolve()),'--child',str(target/variant),'--core',str(core)],check=True)
 aggregate(out,a.rom)
if __name__=='__main__':main()
