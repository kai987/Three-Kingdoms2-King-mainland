#!/usr/bin/env python3
"""Two bounded original-input postbattle continuations, with a separate passive core.

The positive route inherits declared historical numerical preparation. No running
core or ROM writes are added here. This is not a CPU/IR execution fallback.
"""
from pathlib import Path
import argparse,collections,ctypes as C,hashlib,json,shutil,struct,subprocess,sys,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
from capture_native_deployment_pointer import serialized,sha,ROM_SHA,CORE_SHA,decode_event as decode_parent
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase27-observer/observed/nestopia_libretro.dylib'
OBSERVER_SHA='4e8df712fb9193474abcc089bc34b9d6c764f1f5ac96075bc9ef8b5da66fc6c2'
UPSTREAM=ROOT/'.toolchain/phase27-observer/upstream';RUN=ROOT/'analysis/phase27/runtime'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3';WORDS=48;RECORD_BYTES=192;SNAPSHOT_BYTES=10240
FIVE=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
CASES={
 'natural-postbattle-skip':dict(mother='analysis/phase22/runtime/original-control/observed-g04-n03-battle-015-002.state',mother_sha256='2f43339d3d1710b3bee503b68179e48269dd08e30e79fa57ea577ac9672bab12',parent_frame=7636,frames=64,outcome=1,natural=True),
 'controlled-ancestry-resource-loss':dict(mother='analysis/phase15/runtime/succession-heir/observed-g04-n03-battle-015-002.state',mother_sha256='f48bd9f42d10c5eba227b76371258307a33ed8071d4e1af8921eafc3d2f22ddc',parent_frame=8051,frames=32,outcome=0,natural=False)}
def write(p,j):Path(p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def pin(p):p=Path(p);return dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p))
def mother(case):return ROOT/CASES[case]['mother']
def fields(r,s):
 return dict(global_007A=r[0x7A],NMI_0078=r[0x78],city_0400_0403=list(r[0x400:0x404]),battle_0500_0501=list(r[0x500:0x502]),
  outcome_0514=r[0x514],turn_0506=r[0x506],battle_city_050E=r[0x50E],battle_0514_051F=list(r[0x514:0x520]),
  frame_end_ZP_0000_002F=list(r[:0x30]),frame_end_pointer_001A_001B=r[0x1A]|r[0x1B]<<8,raw_bank_selectors_DE_DF=list(r[0xDE:0xE0]),
  city_aux150=[s[32*i+j]for i in range(30)for j in(1,28,29,30,31)],all30_city_records_raw32=[list(s[32*i:32*i+32])for i in range(30)],
  active_city_raw32=list(s[r[0x50E]*32:r[0x50E]*32+32]),active_city_words={str(i):s[r[0x50E]*32+i]|s[r[0x50E]*32+i+1]<<8 for i in(2,4,6,8,12,14)},
  active_city_byte11=s[r[0x50E]*32+11],raw_supplies_052B_0533=list(r[0x52B:0x534]))
def ancestry(case):
 c=CASES[case];m=mother(case);folder=m.parent;v=json.loads((folder/'validation.json').read_text());points=json.loads((folder/'checkpoints.json').read_text())
 assert sha(m)==c['mother_sha256']and v['status']=='passed';point=next(x for x in points if x.get('state')==m.name);assert point['frame']==c['parent_frame']
 base=dict(parent_validation=pin(folder/'validation.json'),parent_checkpoints=pin(folder/'checkpoints.json'),parent_checkpoint=point,
  mother=pin(m),new_case_state_imported=True,new_case_cold_boot=False,additional_core_memory_writes=0,additional_preparation=[],
  earlier_ancestry_scope='Imports retain all historical preparation. No state is substituted with a similarly named later cold replay.')
 if c['natural']:
  assert v['additional_core_memory_writes']==0 and not v['preparation'];par=ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/validation.json';pv=json.loads(par.read_text())
  assert pv['cold_boot']and not pv['state_imported']and pv['additional_core_memory_writes']==0
  base.update(natural_ordinary_input_route=True,controlled_ancestry=False,known_inherited_preparation=[],known_inherited_preparation_byte_writes=0,
   earlier_parent=pin(par),earlier_parent_state=pin(ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/city-commands.state'),earlier_ancestor_cold_boot=True)
 else:
  prep=v['preparation'];assert len(prep)==v['additional_core_memory_writes']==19
  meta=ROOT/'analysis/runtime/phase3/attack-intro-7.json';rawmeta=json.loads(meta.read_text());assert sha(ROOT/'analysis/runtime/phase3/attack-intro-7.state')=='82a7e08a2d85b724f495ed6899390ad8c9afa4d9753ee4ac7b713d296233c089'
  history=[];seen=set();p=meta
  while p.exists()and p not in seen:
   seen.add(p);j=json.loads(p.read_text());history.append(pin(p));imp=next((e['imported_state']for e in j.get('events',[])if 'imported_state'in e),None)
   if not imp:break
   pp=ROOT/imp;history.append(pin(pp));p=pp.with_suffix('.json')
  group_pins=[]
  for group in v['preparation_groups']:
   before={};after={}
   for domain,size in(('RAM',2048),('SRAM',8192)):
    pp=folder/group['before'][domain]['path'];ap=folder/group['after'][domain]['path'];before[domain]=bytearray(pp.read_bytes());after[domain]=ap.read_bytes();assert len(before[domain])==len(after[domain])==size
    group_pins.extend([pin(pp),pin(ap)])
   for row in group['writes']:
    index=row['address']-(0x6000 if row['kind']=='SRAM'else 0);assert before[row['kind']][index]==row['before'];before[row['kind']][index]=row['after']
   assert all(bytes(before[k])==after[k]for k in before)
  base.update(natural_ordinary_input_route=False,controlled_ancestry=True,known_inherited_preparation=prep,known_inherited_preparation_byte_writes=19,
   historical_preparation_base=rel(folder),historical_preparation_buffer_pins=group_pins,
   historical_preparation_groups=v.get('preparation_groups',v.get('groups',[])),earlier_parent=pin(ROOT/'analysis/runtime/phase3/attack-intro-7.state'),earlier_import_metadata_chain=history,
   earlier_than_phase15_numeric_preparation_status='not fully established by the legacy import/button metadata; not assumed zero',
   additional_scope='The nineteen explicitly recorded phase15 numerical preparations precede real original-core combat. No new numerical/status/location/roster/ready/result/RNG/PC preparation is performed here.')
 return base

def decode_event(raw_record,frame=None,sequence=None):
 w=struct.unpack('<48I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record);assert len(w)==48
 e=decode_parent(w[:44],frame,sequence);a=e['address'];pc=e['opcode_PC'];bank=e['physical_bank'];kind=e['kind'];zp=e['ZP_0000_002F'];ptr=zp[0x1A]|zp[0x1B]<<8
 read=kind in('read','word_read_low','word_read_high');data_bank=e['actual_PRG_banks'][(a-0x8000)//8192]if read and 0x8000<=a<0x10000 else None
 target='opcode_boundary'if kind=='opcode_boundary'else('city_auxiliary_bus'if 0x6000<=a<0x63C0 and(a&31)in(1,28,29,30,31)else('city_record_write_attempt'if 0x6000<=a<0x63C0 and kind=='write_attempt'else('city_record_read_bus'if 0x6000<=a<0x63C0 else('pointer_001A_001B_RAM_write'if a<0x2000 and(a&0x7FF)in(0x1A,0x1B)else('PRG_mapper_port_write'if a in(0xE000,0xE800,0xF000)else 'selected_postbattle_ROM_bus')))))
 e.update(target_type=target,pointer_001A_001B=ptr,battle_0506_0507_050E_0514=[w[40]>>b&255 for b in(0,8,16,24)],
  RAM0500_0503=[w[45]>>b&255 for b in(0,8,16,24)],RAM0514_0517=[w[46]>>b&255 for b in(0,8,16,24)],RAM0518_051B=[w[47]>>b&255 for b in(0,8,16,24)],
  storage_byte_before_write=w[44]if w[44]!=0xFFFFFFFF else None,
  data_physical_bank=data_bank,data_ROM_offset=16+data_bank*8192+(a&8191)if data_bank is not None else None,
  logical_G106_city_read=read and bank==8 and pc in(0xBF74,0xBFA0,0xBFA6,0xBFEC,0xBFF2)and a==((ptr+e['Y'])&65535),
  G106_STA_dummy_read=read and bank==8 and pc in(0xBFDF,0xBFE9)and a==((ptr&0xFF00)|((ptr+e['Y'])&255)),
  logical_G106_city_store=kind=='write_attempt'and bank==8 and pc in(0xBFDF,0xBFE9)and a==((ptr+e['Y'])&65535))
 for key in('pointer_0020_0021','logical_coordinate_read','battle_setup_0506_0507_050E_052A'):e.pop(key,None)
 return e

def start_observer(rt,out):
 if not hasattr(rt.core,'nestopia_postbattle_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  f=getattr(core,'nestopia_postbattle_'+name);f.argtypes=[C.c_uint];f.restype=None
 for name in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_postbattle_'+name).restype=C.c_uint
 core.nestopia_postbattle_data.restype=C.POINTER(C.c_uint32);core.nestopia_postbattle_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_postbattle_words()==WORDS
 original=core.retro_run
 def run():core.nestopia_postbattle_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_postbattle_enable(7)
 parent=json.loads((ROOT/'analysis/phase26/runtime/observer/event-schema.json').read_text())
 layout=parent['raw_layout'].copy();layout[40]='RAM0506_0507_050E_0514_packed4';layout+=['physical_backing_byte_before_write_or_FFFFFFFF','RAM0500_0503_packed4','RAM0514_0517_packed4','RAM0518_051B_packed4']
 write(out/'event-schema.json',dict(schema='phase27-passive-postbattle-pointer-ABI-v1',words=WORDS,bytes_per_record=RECORD_BYTES,raw_layout=layout,
  sequence='One-based globally contiguous per fresh process; begin_frame does not reset sequence.',cycle='Original cycles.count, including unchanged frame rebasing.',
  opcode_PC='ExecuteOp actual PC before FetchPc8; bus_PC actual Cpu.pc at the bus hook. last_CPU_opcode_field is previous opcode at pre-Fetch boundaries.',
  before_after='Only write events: word44 is const backing before the original store, word17 is WRAM backing after the original store. RAM after is fullZP; no added emulated reads/writes.',
  snapshot=dict(bytes=10240,layout='physical2048 RAM followed by physical8192 WRAM',entries=['8:BAB3 only sub2','8:BF0A','8:BF9E','8:BFB3','8:BFEC','9:C027'],method='const backing copy; no map.Peek/device API',instantaneous_N163_PPU_APU_captured=False),
  watch=dict(city_auxiliary='All original bus accesses to150 city+1/+28..31 bytes',city_writes='All original city6000..63BF write attempts, including following C027 supply return',pointer_writes='1A/1B mirrored RAM writes via PokeRam and PokeBus',selected_ROM='Actual code/operand/data original ROM bus reads and opcode boundaries in BF0A..C026 plus declared parent/fixed entry boundaries'),
  original_reference='original-control',overflow='Explicit hard failure on event or snapshot overflow; no silent drop',limits=['Separate observer only provides internal events. Fixed original core has independent five-buffer controls.','Bus reads include fetch/dummy accesses and are not automatically field consumers.','No instantaneous N163, PPU or APU state.']))
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter(),targets=collections.Counter())
def drain(rt,obs,out,case):
 if obs is None:return
 c=rt.core;assert c.nestopia_postbattle_overflow()==c.nestopia_postbattle_snapshot_overflow()==0
 n=c.nestopia_postbattle_count();raw=C.string_at(c.nestopia_postbattle_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=c.nestopia_postbattle_snapshot_count();snap=C.string_at(c.nestopia_postbattle_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<48I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1;obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count'];payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:];assert list(r[:0x30])==e['ZP_0000_002F']
   prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,
    RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],stack_top_word_raw=e['stack_top_word_raw'],
    capture_core_sha256=rt.info['core_sha256'],mother=pin(mother(case)),additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if CASES[case]['natural']else 19,
    instantaneous_N163_PPU_APU_captured=False,origin='Independent27 passive observer actual pre-opcode software context, retaining actual existing stack; not fixed-core internal trace.',exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin')
   write(out/(prefix+'.json'),row);obs['index'].write(json.dumps(row,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out,case,probe=False):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA and(sha(core)in(CORE_SHA,OBSERVER_SHA));c=CASES[case];m=mother(case);assert sha(m)==c['mother_sha256']
 out=Path(out);out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Refuse overwrite'
 rt=ServiceRuntime(rom,out,core);obs=start_observer(rt,out);rows=[];points=[]
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(m);(out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0));initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial)
  assert initial['battle_0500_0501']==[15,2]and initial['outcome_0514']==c['outcome']
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);state=serialized(rt);ctx=NestopiaContext.parse(state);pcm=rt.pcm_frame();drain(rt,obs,out,case);label='frame-%03d'%rt.frames
   row=dict(frame=rt.frames,parent_route_frame=c['parent_frame']+rt.frames,RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rt.frame.tobytes()),PCM_sha256=digest(pcm),whole_serialized_state_sha256=digest(state),whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),actual_saved_CPU_registers=ctx.registers,actual_saved_PRG_banks=list(ctx.prg_banks),**fields(r,s));rows.append(row)
   (out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s);rt.frame.save(out/(label+'.png'));points.append(dict(label=label,frame=rt.frames,image=label+'.png',state=label+'.state',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  plan=[dict(start_frame=0,frames=c['frames'],buttons=[],label='ordinary-release-through-postbattle-settlement')];rt.run(c['frames'],(),observe);final=fields(rt.memory(2),rt.memory(0));assert rows[0]['battle_0500_0501']==[15,3]
  wav=rt.save_wav(out/'full-audio.wav');wav['path']='full-audio.wav';write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  anc=ancestry(case);write(out/'preparation.json',anc);events=None
  if obs:
   for name in('raw','decoded','snap','index'):obs[name].close()
   events=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshot_count'],kinds=dict(obs['kinds']),targets=dict(obs['targets']),overflow=0,**{key:dict(path=name,bytes=(out/name).stat().st_size,sha256=sha(out/name))for key,name in [('raw','bus-events.bin'),('decoded','events.jsonl'),('snapshots','snapshots.bin'),('snapshot_index','snapshot-index.jsonl')]})
  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.stat().st_size and p.name not in('validation.json','repeat-validation.json')}
  deps=[Path(__file__),ROOT/'scripts/capture_native_deployment_pointer.py',ROOT/'scripts/capture_native_appearance_pointer.py',ROOT/'scripts/capture_native_pointer_lifecycle.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',m,m.with_name(m.stem+'-ram.bin'),m.with_name(m.stem+'-sram.bin'),ROOT/'analysis/phase26/runtime/observer/event-schema.json']
  deps += [ROOT/x['path']for x in anc.values()if isinstance(x,dict)and 'path'in x and 'sha256'in x]
  receipt=dict(schema='phase27-native-postbattle-pointer-stream-v1',status='passed',case=case,variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,core=rt.info,core_path=rel(core),AV=rt.av_info,mother=pin(m),ancestry=anc,state_imported=True,cold_boot=False,additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if c['natural']else 19,natural_ordinary_input_route=c['natural'],controlled_ancestry=not c['natural'],frames=c['frames'],checkpoint_count=len(points),input_step_count=1,initial_fields=initial,final_fields=final,full_audio=wav,observer_events=events,artifact_sha256=artifacts,dependency_pins=[pin(p)for p in deps],full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,
   verified_effects=dict(original_battle15_sub2_to_sub3=True,initial_outcome=c['outcome'],new_numeric_or_status_ready_result_RNG_PC_writes=0),
   limits=['Frame-end pointer and resources are not opcode-time G106 effects. Following C027 supply return is separately attributed.','Positive route inherits19 declared phase15 numerical preparation writes and incompletely established earlier legacy preparation.','Internal events from independent observer only; no instantaneous N163/PPU/APU capture.'])
  write(out/'validation.json',receipt);print(json.dumps(dict(case=case,variant=receipt['variant'],frames=rt.frames,initial=initial['active_city_words'],final=final['active_city_words'],endpoint=[final['global_007A'],final['NMI_0078'],final['city_0400_0403'],final['battle_0500_0501']],events=events and events['count'],snapshots=events and events['full_RAM_SRAM_snapshots'])),flush=True)
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
 for name in('clean','build','dependency-rebuild'):shutil.copyfile('/tmp/phase27-observer-'+name+'.log',base/('observer-'+name+'.log'))
 old=[('.toolchain/phase21-observer/observed/nestopia_libretro.dylib','45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d'),
  ('.toolchain/phase24-observer/observed/nestopia_libretro.dylib','16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'),
  ('.toolchain/phase25-observer/observed/nestopia_libretro.dylib','7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0'),
  ('.toolchain/phase26-observer/observed/nestopia_libretro.dylib','ed7a9942c789f94595e8a8a842a9574245df5e97f8e57e062b2208e95a6814b1')]
 for name,value in old:assert sha(ROOT/name)==value
 assert sha(OBSERVER)==sha(UPSTREAM/'libretro/nestopia_libretro.dylib')==OBSERVER_SHA
 write(base/'build.json',dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,parent_frozen_patch=pin(ROOT/'analysis/phase26/runtime/core-provenance/observer.patch'),
  original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),unchanged_old_observers=[pin(ROOT/n)for n,_ in old],
  clean_command=['make','clean'],build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],first_build_clean_new_tree=True,final_source_clean_build=True,
  include_dependency_declared='../source/core/NstCpu.o: ../source/core/NstWatch.cpp.inc ../source/core/NstWatch.hpp',dependency_rebuild_byte_identical=True,
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=n,sha256=sha(UPSTREAM/n))for n in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],
  modified_emulator_object_layout=False,extra_emulated_bus_reads=0,extra_emulated_bus_writes=0,
  snapshot_method='Const RAM/WRAM backing copies only, no map.Peek/map.Poke/device API.',toolchain_in_archive=False,
  ABI_change='48u32: first44 frozen26 layout exceptword40 outcome0514 replaces052A, append const backing byte before original write plus0500/0514/0518 four-byte groups. Existingword17 WRAM backing after store, not arbitraryRAM. No emulated reads/writes added.'))
def observations(folder,case):
 raw=(folder/'bus-events.bin').read_bytes();events=[json.loads(x)for x in(folder/'events.jsonl').read_text().splitlines()];assert len(raw)==len(events)*RECORD_BYTES
 for i,e in enumerate(events):assert decode_event(raw[i*RECORD_BYTES:(i+1)*RECORD_BYTES],sequence=i+1)==e
 stores=[e for e in events if e['logical_G106_city_store']];dummy=[e for e in events if e['G106_STA_dummy_read']];reads=[e for e in events if e['logical_G106_city_read']];entries=[e for e in events if e['full_snapshot_sequence']]
 bf=next(e for e in entries if e['physical_bank']==8 and e['opcode_PC']==0xBF0A);assert bf['RAM0514_0517'][0]==CASES[case]['outcome']and bf['stack_top_word_raw']&65535==0xBB98
 if CASES[case]['natural']:assert not stores and not reads and not any(e['opcode_PC']==0xBF9E for e in entries)
 else:
  assert len(stores)==len(dummy)==11 and len(reads)==15 and len([e for e in entries if e['opcode_PC']==0xBF9E])==5
  assert all(e['pointer_001A_001B']==0x6080 and e['address']==0x6080+e['Y']and e['value']==e['physical_storage_byte_after_event']for e in stores)
  assert sum(e['storage_byte_before_write']!=e['physical_storage_byte_after_event']for e in stores)==7
  assert all(e['actual_PRG_banks']==[16,8,9,31]for e in stores)
 supply=[e for e in events if e['kind']=='write_attempt'and 0x6000<=e['address']<0x63C0 and(e['address']&31)in(2,3,4,5)and not e['logical_G106_city_store']]
 aux=[e for e in events if e['target_type']=='city_auxiliary_bus']
 return dict(case=case,observer_events=len(events),software_entries=entries,logical_G106_reads=reads,logical_G106_stores=stores,STA_indirect_Y_dummy_bus_reads=dummy,STA_dummy_read_count=len(dummy),logical_read_count=len(reads),store_count=len(stores),
  changed_byte_count=sum(e['storage_byte_before_write']!=e['physical_storage_byte_after_event']for e in stores),unchanged_write_count=sum(e['storage_byte_before_write']==e['physical_storage_byte_after_event']for e in stores),
  following_other_city_gold_grain_writes=supply,city_auxiliary_events=aux,
  scope='Selected observer opcode-time logical accesses and original attempted stores, actual backing before/after. Other reads include instruction/operand/dummy bus reads. Subsequent supply return is not G106 reduction.')

def aggregate(out,rom_path):
 repeat=out.parent/(out.name+'-repeat');checks=[];streams=[];results=[];PNG=WAV=0;rom=Path(rom_path).read_bytes();assert digest(rom)==ROM_SHA
 for case,c in CASES.items():
  original_rows=None
  for variant in('original-control','observer'):
   first,second=out/case/variant,repeat/case/variant;a=json.loads((first/'validation.json').read_text());b=json.loads((second/'validation.json').read_text());assert a==b and a['status']=='passed'
   for name,p in a['artifact_sha256'].items():
    assert(first/name).read_bytes()==(second/name).read_bytes()and sha(first/name)==p['sha256'];checks.append(dict(case=case,first=rel(first/name),repeat=rel(second/name),**p));PNG+=name.endswith('.png');WAV+=name.endswith('.wav')
   rows=json.loads((first/'frame-services.json').read_text());assert len(rows)==c['frames']
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav'):assert(first/name).read_bytes()==(out/case/'original-control'/name).read_bytes()
   callbacks=json.loads((first/'audio-callbacks.json').read_text());assert len(callbacks)==len(rows)
   with wave.open(str(first/'full-audio.wav'))as wav:
    assert(wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
    for row,cb in zip(rows,callbacks):
     pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256'];assert wav.tell()*4==row['PCM_stop_byte'];label='frame-%03d'%row['frame']
     r=(first/(label+'-ram.bin')).read_bytes();s=(first/(label+'-sram.bin')).read_bytes();state=(first/(label+'.state')).read_bytes();ctx=NestopiaContext.parse(state)
     assert ctx.ram==r and ctx.sram==s and ctx.registers==row['actual_saved_CPU_registers']and list(ctx.prg_banks)==row['actual_saved_PRG_banks'];assert digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']
     assert fields(r,s)=={k:row[k]for k in fields(r,s)}
     for name in(label+'.state',label+'-ram.bin',label+'-sram.bin',label+'.png'):assert(first/name).read_bytes()==(out/case/'original-control'/name).read_bytes()
     with Image.open(first/(label+'.png'))as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
    assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes']
   write(first/'repeat-validation.json',dict(status='passed',first=rel(first),second=rel(second),artifact_checks=len(a['artifact_sha256']),all_bytes_exact=True,script_sha256=sha(__file__)))
   streams.append(dict(case=case,variant=variant,validation=case+'/'+variant+'/validation.json',repeat_validation=case+'/'+variant+'/repeat-validation.json',checkpoints=case+'/'+variant+'/checkpoints.json',frame_services=case+'/'+variant+'/frame-services.json',full_audio=case+'/'+variant+'/full-audio.wav',frames=c['frames'],events=a['observer_events']))
  ob=observations(out/case/'observer',case);results.append(ob)
  for e in [json.loads(x)for x in(out/case/'observer/events.jsonl').read_text().splitlines()]:
   if e['data_ROM_offset']is not None:assert rom[e['data_ROM_offset']]==e['value']
   if e['target_type']=='pointer_001A_001B_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
 write(out/'postbattle-observations.json',dict(schema='phase27-actual-postbattle-observations-v1',routes=results,limits=['Positive controlled ancestry is not claimed naturally reachable.','Instantaneous effects, subsequent supply return, and frame-end resources are separate.','11 original resource stores are7 changed bytes plus4 unchanged stores, not11 independent changed fields.']))
 write(out/'repeat-artifact-checks.json',dict(status='passed',checks=checks,nonempty_artifact_checks=len(checks),full_serialized_buffers_not_normalized=True))
 summary=dict(routes=2,natural_routes=1,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=8,original_first_frames=sum(c['frames']for c in CASES.values()),all_control_frames=4*sum(c['frames']for c in CASES.values()),original_checkpoints=sum(c['frames']for c in CASES.values()),nonempty_artifact_repeat_checks=len(checks),PNG_checks=PNG,WAV_checks=WAV,
  observer_events=sum(r['observer_events']for r in results),full_software_snapshots=sum(len(r['software_entries'])for r in results),logical_G106_reads=sum(r['logical_read_count']for r in results),G106_STA_dummy_read_count=sum(r['STA_dummy_read_count']for r in results),G106_store_count=sum(r['store_count']for r in results),G106_changed_byte_count=sum(r['changed_byte_count']for r in results),G106_unchanged_store_count=sum(r['unchanged_write_count']for r in results),city_auxiliary_bus_events=sum(len(r['city_auxiliary_events'])for r in results),additional_core_memory_writes=0,cold_boots=0,state_imports=8,all_five_complete_buffers_equal_each_frame=True,all_complete_initial_API_buffers_equal=True,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,Source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase27-G106-native-v1',status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),summary=summary,streams=streams,case_ancestry={case:ancestry(case)for case in CASES},core_provenance=pin(out/'core-provenance/build.json'),observations='postbattle-observations.json',Source_CPU_cases=0,original_core_internal_CPU_trace=False,limits=['Imported state continuations, not new cold boots. Positive parent has19 declared numerical writes plus incompletely established earlier legacy preparation.','Fixed original vs distinct observer full initial/frame buffers exact; internal events exist only in independent observer.','No instantaneous N163, PPU or APU capture. Untaken paths remain separate CPU fixtures; no whole-ROM completion claim.'])
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),evidence_sha256=sha(out/'evidence.json'),**summary));print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--probe',type=Path);p.add_argument('--case',choices=CASES);p.add_argument('--child',type=Path);p.add_argument('--core',type=Path);p.add_argument('--out',type=Path,default=RUN);a=p.parse_args()
 if a.probe:assert a.case;capture(a.rom,ORIGINAL,a.probe,a.case,True);return
 if a.child:assert a.case and a.core;capture(a.rom,a.core,a.child,a.case);return
 out=a.out.resolve();repeat=out.parent/(out.name+'-repeat');assert not out.exists()and not repeat.exists(),'Refuse overwrite formal outputs';out.mkdir(parents=True);provenance(out)
 for target in(out,repeat):
  for case in CASES:
   for variant,core in(('original-control',ORIGINAL),('observer',OBSERVER)):
    subprocess.run([sys.executable,str(Path(__file__).resolve()),str(a.rom.resolve()),'--child',str(target/case/variant),'--case',case,'--core',str(core)],check=True)
 aggregate(out,a.rom)
if __name__=='__main__':main()
