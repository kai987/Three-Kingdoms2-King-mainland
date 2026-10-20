#!/usr/bin/env python3
"""Two short, zero-preparation original-core continuations and passive traces.

G033 appearance-table pointer creation is separate from the known B431 city
reserve submission. Frozen earlier producers, cores and outputs are never edited.
"""
from pathlib import Path
import argparse, collections, ctypes as C, hashlib, json, shutil, struct, subprocess, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
from capture_native_pointer_lifecycle import decode_event as decode_previous,fields as previous_fields

ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
OBSERVER_SHA='7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0'
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase25-observer/observed/nestopia_libretro.dylib'
UPSTREAM=ROOT/'.toolchain/phase25-observer/upstream';COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
RUN=ROOT/'analysis/phase25/runtime';WORDS=40;RECORD_BYTES=160;SNAPSHOT_BYTES=10240
CASES={
 'natural-appearance-pointer':dict(mother='analysis/phase22/runtime/original-control/AI-ruler1-status00-frame14569.state',
  plans=[(22,(),'request-FF-settled')],frames=22),
 'natural-nonzero-reserve-submit':dict(mother='analysis/phase24/runtime/original-control/frame-076.state',
  plans=[(2,('down',),'end-row-input'),(20,(),'end-row-settled'),(2,('a',),'submit-input'),(60,(),'city-world-returned')],frames=84)}
FIVE=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def rel(path):return str(Path(path).resolve().relative_to(ROOT))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def pin(path):return dict(path=rel(path),bytes=Path(path).stat().st_size,sha256=sha(path))
def serialized(rt):
 n=rt.core.retro_serialize_size();buf=C.create_string_buffer(n);assert rt.core.retro_serialize(buf,n);return buf.raw
def fields(r,s):
 f=previous_fields(r,s);records=[list(s[0x3C0+12*i:0x3CC+12*i])for i in range(237)]
 f.update(all237_officer_records_raw12=records,all237_officer_status_bytes=[x[11]for x in records],
  officer152_status_code=records[152][11]&3,officer152_raw12=records[152],
  domestic_city_0036=r[0x36],year_raw_6F00=s[0xF00],ruler_6F03=s[0xF03],domestic_phase_6F5B=s[0xF5B],request_6F8B=s[0xF8B],
  frame_end_ZP_0000_002F=list(r[:0x30]),frame_end_pointer22_23=int.from_bytes(r[0x22:0x24],'little'))
 return f

def decode_event(raw_record,frame=None,sequence=None):
 w=struct.unpack('<40I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record);assert len(w)==40
 e=decode_previous(w[:36],frame,sequence);zp=e['ZP_0000_0023']+[v>>b&255 for v in w[36:39]for b in(0,8,16,24)]
 e.update(ZP_0000_002F=zp,product_002A_002B=zp[0x2A]|zp[0x2B]<<8,raw_officer_ID_0024=zp[0x24],
  current_city_0036=e['working_0036_0039'][0],appearance_pair_index_0037=e['working_0036_0039'][1],
  year_raw_6F00=w[39]&255,ruler_6F03=w[39]>>8&255,domestic_phase_6F5B=w[39]>>16&255,request_6F8B=w[39]>>24&255)
 a=e['address'];kind=e['kind']
 if kind=='opcode_boundary':target='opcode_boundary'
 elif a<0x2000 and(a&0x7FF)in(0,1,0x22,0x23):target='pointer_RAM_write'
 elif 0x6000<=a<0x63C0 and(a&31)in(1,28,29,30,31):target='city_auxiliary_bus'
 elif 0x6000<=a<0x63C0 and(a&31)in(12,13):target='city_reserve_submission_bus'
 elif 0x6000<=a<0x63C0 and 17<=a&31<=26:target='city_roster_write'
 elif 0x63C0<=a<0x6EDC and(a-0x63C0)%12==11:target='officer_status_write'
 else:target='appearance_ROM_bus'
 e.update(target_type=target,city_index=(a-0x6000)//32 if 0x6000<=a<0x63C0 else None,
  city_offset=(a-0x6000)%32 if 0x6000<=a<0x63C0 else None,
  officer_index=(a-0x63C0)//12 if target=='officer_status_write'else None)
 return e

def start_observer(rt,out,case):
 if not hasattr(rt.core,'nestopia_appearance_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  fn=getattr(core,'nestopia_appearance_'+name);fn.argtypes=[C.c_uint];fn.restype=None
 for name in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_appearance_'+name).restype=C.c_uint
 core.nestopia_appearance_data.restype=C.POINTER(C.c_uint32);core.nestopia_appearance_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_appearance_words()==WORDS and sys.byteorder=='little'
 original=core.retro_run
 def run():core.nestopia_appearance_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_appearance_enable(7)
 schema=dict(schema='phase25-passive-appearance-pointer-ABI-v1',words=40,bytes_per_record=160,
  first36_words='Same raw fields as frozen phase24 ABI; reuse its pure decoder for the first36 words.',
  appended_words=['ZP24_27_packed4','ZP28_2B_packed4','ZP2C_2F_packed4','SRAM_year6F00_ruler6F03_phase6F5B_request6F8B_packed4'],
  sequence='One-based globally contiguous per fresh process, frame buffer reset does not reset sequence.',
  opcode_PC='Exact ExecuteOp entry PC before FetchPc8; bus_PC is Cpu.pc at the actual bus hook.',
  last_CPU_opcode_field='Raw previous opcode at before-Fetch boundary; not claimed current opcode.',
  frame_identity='Local frame N after this case pinned mother import, no preparation. Not a claimed historical cold-boot frame N.',
  cycle='Original master-clock cycles.count with unchanged EndFrame rebasing; no frontend clock injection.',
  snapshot=dict(bytes_per_snapshot=10240,layout='2048B physical RAM then8192B physical WRAM backing',
   trigger='Before physical11 C5D2/D471 or physical27 B431, direct const backing copy, no emulated reads.',
   N163_PPU_APU_instant_state_captured=False),
  storage='e17 is WRAM backing only; physical RAM post-write bytes come from full ZP payload. FFFFFFFF decodes as None.',
  watch=dict(pointer_writes='Physical mirrored RAM00/01/22/23 through both PokeRam/PokeBus',
   ROM_reads='Physical11 C61F/C624 data bus8000..9FFF, actual bank at data page separately recorded',
   writes='All city roster17..26, officer status+11, all cityaux1/28..31, selected physical27 B449/B44F reserve writes',
   reads='Cityaux bus and selected reserve-store dummy bus reads remain explicit bus observations'),
  original_reference=case+'/original-control',overflow='Event/snapshot overflow is a hard failure; no silent dropping.',
  limits=['Separate observer-core internal events, never an internal trace attributed to fixed original core.',
   'Bus reads can be dummy. Logical-ROM-read attribution additionally checks opcode, pointer+Y and actual data bank.',
   'Sparse callee software state is exact. Device N163/PPU/APU state is not captured or fabricated.'])
 schema['raw_layout']=json.loads((ROOT/'analysis/phase24/runtime/observer/event-schema.json').read_text())['raw_layout']+schema['appended_words']
 write(out/'event-schema.json',schema)
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),
  index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter(),targets=collections.Counter())

def drain(rt,obs,out,mother):
 if obs is None:return
 core=rt.core;assert core.nestopia_appearance_overflow()==core.nestopia_appearance_snapshot_overflow()==0
 n=core.nestopia_appearance_count();raw=C.string_at(core.nestopia_appearance_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=core.nestopia_appearance_snapshot_count();snap=C.string_at(core.nestopia_appearance_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<40I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1
  obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count']
   raw=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=raw[:2048],raw[2048:]
   assert list(r[:0x30])==e['ZP_0000_002F']and r[0x36]==e['current_city_0036']
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],
    byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(raw),
    actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],
    stack_top_word_raw=e['stack_top_word_raw'],current_city_0036=e['current_city_0036'],capture_core_sha256=rt.info['core_sha256'],mother=pin(mother),
    inherited_preparation_byte_writes=0,additional_core_memory_writes=0,instantaneous_N163_PPU_APU_captured=False,
    origin='New phase25 passive core, exact opcode-boundary software snapshot; original control compared separately across complete five buffers.')
   if e['opcode_PC']in(0xC5D2,0xD471)or(e['opcode_PC']==0xB431 and e['new_buttons_0081']&1):
    prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
    row.update(exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin');write(out/(prefix+'.json'),row)
   obs['index'].write(json.dumps(row,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out,case):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA
 assert sha(core)in(CORE_SHA,OBSERVER_SHA)
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Refuse to overwrite an existing capture'
 config=CASES[case];mother=ROOT/config['mother'];rt=ServiceRuntime(rom,out,core);obs=start_observer(rt,out,case);rows=[];points=[];plan=[]
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(mother)
  (out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0))
  initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial)
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();state=serialized(rt);n=NestopiaContext.parse(state);assert n.ram==r and n.sram==s
   drain(rt,obs,out,mother);label='frame-%03d'%rt.frames
   row=dict(frame=rt.frames,RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rt.frame.tobytes()),PCM_sha256=digest(pcm),
    whole_serialized_state_sha256=digest(state),whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),
    actual_saved_CPU_registers=n.registers,actual_saved_PRG_banks=list(n.prg_banks),**fields(r,s));rows.append(row)
   (out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s)
   # Both routes are short; retain every actual newly rendered image.
   rt.frame.save(out/(label+'.png'));points.append(dict(label=label,frame=rt.frames,image=label+'.png',state=label+'.state',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  for n,buttons,label in config['plans']:
   plan.append(dict(start_frame=rt.frames,frames=n,buttons=list(buttons),label=label,purpose='Ordinary original controller input; no memory, RNG, request or PC injection.'))
   rt.run(n,buttons,observe)
  assert rt.frames==config['frames'];final=fields(rt.memory(2),rt.memory(0))
  if case=='natural-appearance-pointer':
   assert initial['officer152_status_code']==1 and final['officer152_status_code']==2 and final['request_6F8B']==255
   first=next(x['frame']for x in rows if x['officer152_status_code']==2)
   effects=dict(officer_ID=152,status_before=1,status_after=2,first_status2_frame=first,request_FF=True,
    frame_end_pointer_is_not_opcode_pointer=True,city_at_instant_read_not_presupposed=True)
  else:
   assert initial['officers']['30']['troops_raw16']==900 and initial['working_reserve_042C_042D']==9899 and initial['city_reserve_raw16']==9999
   assert final['city_state_0400_0403'][:2]==[0,1]and final['city_reserve_raw16']==9899 and final['officers']['30']['troops_raw16']==900
   effects=dict(officer_ID=30,troops_before=900,troops_after=900,city_reserve_before=9999,city_reserve_after=9899,original_submit_and_world_return=True,
    writer_physical_bank=27,actual_store_CPU=[0xB449,0xB44F],B441_is_JSR_not_store=True)
  wav=rt.save_wav(out/'full-audio.wav');wav['path']='full-audio.wav'
  write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  write(out/'preparation.json',dict(additional_core_memory_writes=0,preparation=[],inherited_preparation_byte_writes=0,mother=pin(mother),state_imported=True,cold_boot=False,
   scope='Zero-preparation ancestor continued by ordinary buttons; no historical route is copied or rerun.'))
  events=None
  if obs:
   for name in('raw','decoded','snap','index'):obs[name].close()
   events=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshot_count'],kinds=dict(obs['kinds']),targets=dict(obs['targets']),overflow=0,
    **{key:dict(path=name,bytes=(out/name).stat().st_size,sha256=sha(out/name))for key,name in [('raw','bus-events.bin'),('decoded','events.jsonl'),('snapshots','snapshots.bin'),('snapshot_index','snapshot-index.jsonl')]})
  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.stat().st_size and p.name not in('validation.json','repeat-validation.json')}
  deps=[Path(__file__),ROOT/'scripts/capture_native_pointer_lifecycle.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',mother,
   mother.with_name(mother.stem+'-ram.bin'),mother.with_name(mother.stem+'-sram.bin'),ROOT/'analysis/phase24/runtime/observer/event-schema.json',
   ROOT/('analysis/phase22/runtime/validation.json'if case=='natural-appearance-pointer'else'analysis/phase24/runtime/validation.json')]
  receipt=dict(schema='phase25-native-appearance-and-known-reserve-submit-v1',status='passed',case=case,variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,
   core=rt.info,core_path=rel(core),AV=rt.av_info,mother=pin(mother),cold_boot=False,state_imported=True,inherited_preparation_byte_writes=0,additional_core_memory_writes=0,
   natural_ordinary_input_route=True,frames=rt.frames,checkpoint_count=len(points),input_step_count=len(plan),initial_fields=initial,final_fields=final,
   full_audio=wav,verified_effects=effects,observer_events=events,artifact_sha256=artifacts,dependency_pins=[pin(p)for p in deps],
   full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,
   limits=['Original-core frame/saved-context observation and separate passive-core opcode events are different evidence.',
    'Sparse software snapshots do not contain instantaneous N163/PPU/APU; no hardware state is invented.',
    'Known reserve+12/+13 submission does not name city+1 or tail bytes; absence of auxiliary hits proves no unused field.'])
  write(out/'validation.json',receipt);print(json.dumps(dict(case=case,variant=receipt['variant'],frames=rt.frames,effects=effects,events=events and obs['count'],snapshots=events and obs['snapshot_count'])),flush=True)
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
 shutil.copyfile('/tmp/phase25-observer-build.log',base/'observer-build.log')
 write(base/'build.json',dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,
  parent_corrected_patch=pin(ROOT/'analysis/phase24/runtime/core-provenance/observer.patch'),original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),
  unchanged_old_observer=pin(ROOT/'.toolchain/phase24-observer/observed/nestopia_libretro.dylib'),
  build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],first_build_clean_new_tree=True,
  include_dependency_declared='../source/core/NstCpu.o: ../source/core/NstWatch.cpp.inc ../source/core/NstWatch.hpp',
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=n,sha256=sha(UPSTREAM/n))for n in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],
  modified_emulator_object_layout=False,extra_emulated_bus_reads=0,snapshot_method='Const physical backing copy; no map.Peek/map.Poke/device API.',toolchain_in_archive=False))

def aggregate(out):
 repeated=out.parent/(out.name+'-repeat');case_rows=[];checks=[];all_events=[];frames=points=images=wavs=0
 for case,config in CASES.items():
  original_rows=None;streams=[]
  for variant in('original-control','observer'):
   one,two=out/case/variant,repeated/case/variant;a=json.loads((one/'validation.json').read_text());b=json.loads((two/'validation.json').read_text());assert a==b and a['status']=='passed'
   for name,pin in a['artifact_sha256'].items():
    assert(one/name).read_bytes()==(two/name).read_bytes()and sha(one/name)==pin['sha256'];checks.append(dict(first=rel(one/name),repeat=rel(two/name),**pin))
    images+=name.endswith('.png');wavs+=name.endswith('.wav')
   rows=json.loads((one/'frame-services.json').read_text())
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):
    assert(one/name).read_bytes()==(out/case/'original-control'/name).read_bytes()
   write(one/'repeat-validation.json',dict(status='passed',first=rel(one),second=rel(two),artifact_checks=len(a['artifact_sha256']),all_bytes_exact=True,script_sha256=sha(__file__)))
   streams.append(dict(variant=variant,validation=case+'/'+variant+'/validation.json',repeat_validation=case+'/'+variant+'/repeat-validation.json',checkpoints=case+'/'+variant+'/checkpoints.json',
    frame_services=case+'/'+variant+'/frame-services.json',full_audio=case+'/'+variant+'/full-audio.wav',frames=a['frames'],events=a['observer_events']))
  folder=out/case/'observer';events=[json.loads(x)for x in(folder/'events.jsonl').read_text().splitlines()];raw=(folder/'bus-events.bin').read_bytes()
  assert len(raw)==len(events)*RECORD_BYTES
  for i,e in enumerate(events):assert decode_event(raw[i*RECORD_BYTES:(i+1)*RECORD_BYTES],sequence=i+1)==e
  aux=[x for x in events if x['target_type']=='city_auxiliary_bus'];assert not aux
  if case=='natural-appearance-pointer':
   data=[x for x in events if x['target_type']=='appearance_ROM_bus'];status=[x for x in events if x['target_type']=='officer_status_write'];roster=[x for x in events if x['target_type']=='city_roster_write']
   assert len(data)==6 and len(status)==len(roster)==1
   hit=next(x for x in data if x['value']==152);assert(hit['frame'],hit['physical_bank'],hit['opcode_PC'],hit['current_city_0036'],hit['address'],hit['pointer_0022_0023'],hit['Y'],hit['actual_PRG_banks'][0])==(4,11,0xC61F,3,0x8B58,0x8B58,0,17)
   assert(status[0]['frame'],status[0]['physical_bank'],status[0]['opcode_PC'],status[0]['officer_index'],status[0]['value'])==(4,11,0xC659,152,26)
   assert roster[0]['frame']==4 and roster[0]['city_index']==3 and roster[0]['value']==152
   observation=dict(case=case,source='Separate phase25 observer, matched to this original-control route across complete five buffers.',
    table_reads=data,status_writes=status,roster_writes=roster,
    producer_boundaries=[x for x in events if x['kind']=='opcode_boundary'and x['physical_bank']==11 and x['frame']==4 and x['current_city_0036']==3],
    actual_read_city=3,actual_table_pointer=0x8B58,actual_table_data_bank=17,
    distinction='Frame4 ends after pointer22 has already been reused to8B6C for city4. It is not the pointer used to read ID152.',city_auxiliary_bus_events=0)
  else:
   bus=[x for x in events if x['target_type']=='city_reserve_submission_bus'];assert len(bus)==4
   assert[(x['frame'],x['kind'],x['physical_bank'],x['opcode_PC'],x['address'],x['value'])for x in bus]==[
    (23,'read',27,0xB449,0x616C,15),(23,'write_attempt',27,0xB449,0x616C,171),
    (23,'read',27,0xB44F,0x616D,39),(23,'write_attempt',27,0xB44F,0x616D,38)]
   observation=dict(case=case,reserve_bus_events=bus,city_auxiliary_bus_events=0,
    caller_boundaries=[x for x in events if x['kind']=='opcode_boundary'and x['frame']==23 and x['physical_bank']==27],
    distinction='B441 is the actual JSR F2AF. Stores are B449/B44F; the read before each STA is the addressing-mode dummy bus cycle, not an independent logical reserve read.')
  write(out/case/'opcode-observations.json',observation)
  all_events.extend(events);frames+=config['frames'];points+=len(json.loads((out/case/'original-control/checkpoints.json').read_text()))
  case_rows.append(dict(case=case,streams=streams,frames=config['frames'],verified_effects=a['verified_effects'],state_imported=True,cold_boot=False,additional_core_memory_writes=0))
 summary=dict(status='passed',natural_routes=2,core_variants=2,fresh_process_runs=8,original_first_frames=frames,all_control_frames=frames*4,
  original_checkpoints=points,nonempty_artifact_repeat_checks=len(checks),PNG_checks=images,WAV_checks=wavs,observer_events=len(all_events),
  additional_core_memory_writes=0,ancestor_preparation_bytes=0,state_imports=8,cold_boots=0,all_five_complete_buffers_equal_each_frame=True,
  all_complete_initial_API_buffers_equal=True,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,Source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase25-native-appearance-pointer-and-submit-flows-v1',status='passed',summary=summary,native_cases=case_rows,
  ROM_sha256=ROM_SHA,original_core_sha256=CORE_SHA,observer_core_sha256=sha(OBSERVER),build='core-provenance/build.json',decode_function='scripts/capture_native_appearance_pointer.py:decode_event',script_sha256=sha(__file__))
 write(out/'repeat-artifact-checks.json',checks);write(out/'evidence.json',evidence);write(out/'validation.json',dict(**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(__file__)))
 (out/'README.md').write_text('''# 阶段25：出仕表指针与非零库存提交\n\n两条零新增准备的自然按键续程分别建原核心与新观察核心对照，每核心各fresh进程双跑。导入祖先存档而非本轮冷启动。没有改status、名册、金币、兵数、RNG、request/ready、PC或栈；原ROM与所有旧核心/旧阶段产物保持不变。\n\n[证据](evidence.json) · [回执](validation.json) · [来源/构建](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_native_appearance_pointer.py)\n\n## G033 出仕表链\n\n母档是阶段22原控制流14569，只有原无键输入22帧。ID152真实状态1→2发生在local4，原AI请求在local22回FF。新观察即时证实city3，D471乘积60后建22/23=8B58，C61F从实际8000页bank17读ID152，C624读对应年份；C659写该武将status byte26，随后原city3名单追加。该状态1→2是出仕链，不混称上一轮status0→2在野录用。六次真实表数据读、一处状态写、一处名册写保留在[opcode观察](natural-appearance-pointer/opcode-observations.json)。local4帧末22/23已复用为下一城4的8B6C，不能把这个帧末值倒推为ID152读取时地址。\n\n## 已知库存提交对照\n\n从阶段24原核frame076导入，祖先已经用普通Right将ID30兵800分至900，工作库存9899而城市库存尚9999。本轮仅Down至结束、A，再无键，84帧回原city0/1。local23原B441 JSR F2AF建立city11指针6160；真正B449/B44F两次STA把city+12/+13写为AB/26，真实库存9999→9899，兵数保持900。两次STA前的读是IndY dummy bus周期。它们是已知库存写回，不是未知city+1/tail写者。见[opcode观察](natural-nonzero-reserve-submit/opcode-observations.json)。\n\n## 观察和可复核边界\n\n新核心从官方135dfa6及阶段24已校正、可重建相同二进制的补丁起，另建新目录/新身份。外部静态数组记录40个u32字段，完整ZP00..2F、乘积2A/B、实际AXYP/SP/PC、4PRG页与year/ruler/phase/request；CPU对象布局和原总线调用没有改变。Make显式声明.inc/.hpp依赖，首次构建在新净树进行。源码/原文件/完整补丁/构建日志和不同coreSHA保留。\n\nC5D2、D471和B431真实入口稀疏const复制2K RAM/8K WRAM，序号关联snapshot-index与原始snapshots.bin；没有map.Peek或额外仿真读取。没有瞬时N163/PPU/APU副本，后续独立CPU若需设备环境必须另声明fixture。只有新观察核心有内部事件，不追认固定原核心拥有内部trace。\n\n每新帧保留原256×240PNG、RAM/SRAM及完整未归一化serialized API buffer，原48kHz立体声PCM/WAV完整保存。包括首次serialize API查询与导入时序，全部五域逐帧匹配，所有非空文件双跑exact；raw ABI逐条公开decode_event复核，溢出即失败。本短路线city辅助字节总线事件0，不证明unused，也不赋予正式字段名。Source/原CPU、静态合同、Native观察须独立统计。\n''')
 print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--case',choices=CASES);p.add_argument('--core',type=Path);p.add_argument('--out',type=Path,default=RUN)
 p.add_argument('--verify-passivity',action='store_true');p.add_argument('--aggregate-only',action='store_true');a=p.parse_args()
 if a.aggregate_only:aggregate(a.out.resolve());return
 if a.verify_passivity:
  assert not a.out.exists()or not any(a.out.iterdir()),'Refuse to overwrite a phase25 output root'
  assert not a.out.parent.joinpath(a.out.name+'-repeat').exists(),'Refuse existing repeat root'
  a.out.mkdir(parents=True,exist_ok=True);provenance(a.out)
  for case in CASES:
   for variant,core in(('original-control',ORIGINAL),('observer',OBSERVER)):
    for folder in(a.out/case/variant,a.out.parent/(a.out.name+'-repeat')/case/variant):
     subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--core',str(core),'--case',case,'--out',str(folder)],check=True)
  aggregate(a.out.resolve())
 else:
  assert a.core is not None and a.case is not None;capture(a.rom,a.core.resolve(),a.out,a.case)

if __name__=='__main__':main()
