#!/usr/bin/env python3
"""Early postbattle controller continuation under original ordinary inputs and a separate passive core.

One route inherits declared historical numerical preparation. No running
core or ROM writes are added here. This is not a CPU/IR execution fallback.
"""
from pathlib import Path
import argparse,collections,ctypes as C,hashlib,json,shutil,struct,subprocess,sys,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
from capture_native_postbattle_pointer import serialized,sha,ROM_SHA,CORE_SHA
import capture_native_postbattle_completion as prior
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase30-observer/observed/nestopia_libretro.dylib'
OBSERVER_SHA='bb15dc22b1ee5cd1a0e449e9a979a86a26ae2d8762579921ed74a8052cd20996'
UPSTREAM=ROOT/'.toolchain/phase30-observer/upstream';RUN=ROOT/'analysis/phase30/runtime'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3';WORDS=68;RECORD_BYTES=272;SNAPSHOT_BYTES=10240
FIVE=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
CASES={'natural-stage0-human': {'mother': 'analysis/phase22/runtime/original-control/observed-g04-n03-battle-015-000.state', 'mother_sha256': '2b4517e763d15709fa324b4544526579fce8073000b594e2ecc3c7d8f5279f91', 'parent_frame': 6116, 'frames': 8, 'start_stage': 0, 'ancestry_case': 'natural-postbattle-skip', 'natural': True, 'outcome': 1, 'first_stage': [13, 0]}, 'natural-stage1-mode0': {'mother': 'analysis/phase22/runtime/original-control/observed-g04-n03-battle-015-001.state', 'mother_sha256': '6da2e90a4fa7dd0dd947c2653efc8a117534aa7bada44978ca706b66458bcb47', 'parent_frame': 7635, 'frames': 32, 'start_stage': 1, 'ancestry_case': 'natural-postbattle-skip', 'natural': True, 'outcome': 1, 'first_stage': [15, 2]}, 'controlled-stage0-human': {'mother': 'analysis/phase15/runtime/succession-heir/observed-g04-n03-battle-015-000.state', 'mother_sha256': '00d5f3afc0a0a6ee306357a265c2529d97cfb8abba2fce36be11df16349dedc3', 'parent_frame': 8048, 'frames': 8, 'start_stage': 0, 'ancestry_case': 'controlled-ancestry-resource-loss', 'natural': False, 'outcome': 0, 'first_stage': [14, 0]}}
def write(p,j):Path(p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def pin(p):p=Path(p);return dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p))
def mother(case):return ROOT/CASES[case]['mother']
def ancestry(case):
 c=CASES[case];a=prior.ancestry(c['ancestry_case']);m=ROOT/c['mother'];assert sha(m)==c['mother_sha256'];points=json.loads((m.parent/'checkpoints.json').read_text());point=next(x for x in points if x.get('state')==m.name);assert point['frame']==c['parent_frame'];a.update(mother=prior.pin(m),parent_checkpoint=point);return a

def fields(r,s):
 x=prior.fields(r,s);x.update(early_side_0504=r[0x504],early_mode_6F91=s[0xF91],early_050B=r[0x50B],early_working_officers_6FA1_6FB4=list(s[0xFA1:0xFB5]),early_CHR_cache_bytes={hex(a):r[a]for a in(0xB2,0xB3,0xC2,0xC3,0xCA,0xCB,0xD2,0xD3,0xDA,0xDB)},raw_ruler_records_6F07_6F3E=[s[0xF07+8*i:0xF0F+8*i].hex()for i in range(7)]);return x

def decode_event(raw_record,frame=None,sequence=None):
 e=prior.decode_event(raw_record,frame,sequence);pc=e['opcode_PC'];a=e['address'];physical=e['physical_bank'];p=a&0x7FF
 e['postbattle_mode_6F91']=e['strategy_side_6F91']
 e['early_controller_byte_read']=physical==8 and pc in(0xBAEF,0xBB47)and e['kind']=='read'and a==((e['pointer_0000_0001']+e['Y'])&65535)
 e['early_BC46_JSR_boundary']=physical==8 and e['kind']=='opcode_boundary'and pc in(0xBB36,0xBB8C)
 e['early_mode_dispatch_target']=physical==8 and e['kind']=='opcode_boundary'and pc in(0xBC52,0xBD59,0xBD67)
 e['early_SRAM_write']=physical==8 and 0xBC46<=pc<0xBF0A and e['kind']=='write_attempt'and 0x6000<=a<0x8000
 if e['kind']=='write_attempt'and a<0x2000 and p in(0xB2,0xB3,0xC2,0xC3,0xCA,0xCB,0xD2,0xD3,0xDA,0xDB,0x504,0x50B):
  e['target_type']='early_control_or_CHR_cache_RAM_write';e['captured_RAM_byte_after_write']=e['CHR_cache_00C2']if p==0xC2 else None
 return e

def start_observer(rt,out):
 if not hasattr(rt.core,'nestopia_early_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  f=getattr(core,'nestopia_early_'+name);f.argtypes=[C.c_uint];f.restype=None
 for name in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_early_'+name).restype=C.c_uint
 core.nestopia_early_data.restype=C.POINTER(C.c_uint32);core.nestopia_early_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_early_words()==WORDS
 original=core.retro_run
 def run():core.nestopia_early_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_early_enable(7)
 parent=json.loads((ROOT/'analysis/phase27/runtime/natural-postbattle-skip/observer/event-schema.json').read_text())
 added=['RAM0087_008A_fade_packed4','RAM007D_0080_jobs_packed4']+[f'RAM{0x100+4*i:04X}_{0x103+4*i:04X}_palette_packed4'for i in range(16)]+['RAM00DE_00E1_bank_shadow_packed4','RAM00E2_00E5_bank_shadow_packed4']
 write(out/'event-schema.json',dict(schema='phase30-passive-postbattle-parent-ABI-v1',words=WORDS,bytes_per_record=RECORD_BYTES,raw_layout=parent['raw_layout']+added,
  sequence='One-based globally contiguous per fresh process; begin_frame doesnot resetsequence.',cycle='Original cycles.count, including unchangedframe rebasing.',
  opcode_PC='Actual ExecuteOp PC before FetchPc8; bus_PC actual Cpu.pc. last_CPU_opcode_field is previousopcode at preFetch boundaries.',
  before_after='Word44 const physicalbacking before originalwrite; word17 WRAM backingafter. NewRAM domains capturepostvalue frompackedbacking; controller82..86 and addedearlyCHR/side RAM postvalues not independentlycaptured exceptC2; fullsoftware snapshots retain them.',
  snapshot=dict(bytes=10240,layout='physical2048RAM then8192WRAM',scope='Selected actual opcode boundaries, not allare publicJSR entries. D4F0/CC29 are actual software entries; D4F5 is a later middle-entry.',method='Const physicalbacking copy, no map.Peek/device API',instantaneous_N163_PPU_APU_captured=False),
  watch=dict(city='AllSRAM6000..7FFF write attempts and150 cityauxiliarybus accesses',RAM='00..03,06/07,0A..0C,1A/B,7D..8A,78/7A,DE..E5,0100..013F,400/401,500/501/504/50B,B2/B3,C2/C3,CA/CB,D2/D3,DA/DB originalwrites',
   opcodes='8A006/BAB3/BAC1..BF09, trueBB36/BB8C callsites andBC46/localhelpers; inheritedD4F0/CC29,phase2/3/fade/farprotocol;fixedF368/F2AF/F2D7/F266/F25F/E856. Allscopes filtered byactualPRG.'),
  original_reference='original-control',overflow='Hardfailure on eventor snapshot overflow; no silentdrops',
  limits=['ECEE immediateRTS startsasynchronous palettework; itis not a blockingwait. LaterBBA0 calls are fresh perNMI invocations.',
   'Onlyindependent observer has internal selectedevents. No instantaneous N163/PPU/APU capture.',
   'Observed21frame completion depends on actualold8A=4; ECEE itselfdoesnot initialise8A. LaterECBFfade is a separateepoch.']))
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter(),targets=collections.Counter())
def drain(rt,obs,out,case):
 if obs is None:return
 c=rt.core;assert c.nestopia_early_overflow()==c.nestopia_early_snapshot_overflow()==0
 n=c.nestopia_early_count();raw=C.string_at(c.nestopia_early_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=c.nestopia_early_snapshot_count();snap=C.string_at(c.nestopia_early_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<68I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1;obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count'];payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:];assert list(r[:0x30])==e['ZP_0000_002F']
   prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,
    RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],stack_top_word_raw=e['stack_top_word_raw'],
    actual_battle_state=list(r[0x500:0x502]),actual_side_0504=r[0x504],actual_mode_6F91=s[0xF91],actual_working_officers=list(s[0xFA1:0xFB5]),actual_outcome=r[0x514],actual_fade_0087_008A=list(r[0x87:0x8B]),actual_shadow_DE_E5=list(r[0xDE:0xE6]),capture_core_sha256=rt.info['core_sha256'],mother=pin(mother(case)),additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if CASES[case]['natural']else 19,
    instantaneous_N163_PPU_APU_captured=False,origin='Independent30 passive observer actual pre-opcode software context, retaining actual existing stack; not fixed-core internal trace.',exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin')
   write(out/(prefix+'.json'),row);obs['index'].write(json.dumps(row,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out,case,probe=False):
 assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA and(sha(core)in(CORE_SHA,OBSERVER_SHA));c=CASES[case];m=mother(case);assert sha(m)==c['mother_sha256']
 out=Path(out);out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Refuse overwrite'
 rt=ServiceRuntime(rom,out,core);obs=start_observer(rt,out);rows=[];points=[]
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(m);(out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0));initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial)
  assert initial['battle_0500_0501']==[15,c['start_stage']]and initial['outcome_0514']==c['outcome']
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);state=serialized(rt);ctx=NestopiaContext.parse(state);pcm=rt.pcm_frame();drain(rt,obs,out,case);label='frame-%03d'%rt.frames
   row=dict(frame=rt.frames,parent_route_frame=c['parent_frame']+rt.frames,RAM_sha256=digest(r),SRAM_sha256=digest(s),RGB_sha256=digest(rt.frame.tobytes()),PCM_sha256=digest(pcm),whole_serialized_state_sha256=digest(state),whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),actual_saved_CPU_registers=ctx.registers,actual_saved_PRG_banks=list(ctx.prg_banks),**fields(r,s));rows.append(row)
   (out/(label+'.state')).write_bytes(state);(out/(label+'-ram.bin')).write_bytes(r);(out/(label+'-sram.bin')).write_bytes(s);rt.frame.save(out/(label+'.png'));points.append(dict(label=label,frame=rt.frames,image=label+'.png',state=label+'.state',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  plan=[dict(start_frame=0,frames=c['frames'],buttons=[],label='ordinary-release-through-postbattle-settlement')];rt.run(c['frames'],(),observe);final=fields(rt.memory(2),rt.memory(0));assert rows[0]['battle_0500_0501']==c['first_stage']
  wav=rt.save_wav(out/'full-audio.wav');wav['path']='full-audio.wav';write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',plan);write(out/'audio-callbacks.json',rt.audio_calls)
  anc=ancestry(case);write(out/'preparation.json',anc);events=None
  if obs:
   for name in('raw','decoded','snap','index'):obs[name].close()
   events=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshot_count'],kinds=dict(obs['kinds']),targets=dict(obs['targets']),overflow=0,**{key:dict(path=name,bytes=(out/name).stat().st_size,sha256=sha(out/name))for key,name in [('raw','bus-events.bin'),('decoded','events.jsonl'),('snapshots','snapshots.bin'),('snapshot_index','snapshot-index.jsonl')]})
  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.stat().st_size and p.name not in('validation.json','repeat-validation.json')}
  deps=[Path(__file__),ROOT/'scripts/capture_native_postbattle_completion.py',ROOT/'scripts/capture_native_postbattle_parent.py',ROOT/'scripts/capture_native_postbattle_pointer.py',ROOT/'scripts/capture_native_deployment_pointer.py',ROOT/'scripts/capture_native_appearance_pointer.py',ROOT/'scripts/capture_native_pointer_lifecycle.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',m,m.with_name(m.stem+'-ram.bin'),m.with_name(m.stem+'-sram.bin'),ROOT/'analysis/phase27/runtime/natural-postbattle-skip/observer/event-schema.json']
  deps += [ROOT/x['path']for x in anc.values()if isinstance(x,dict)and 'path'in x and 'sha256'in x]
  receipt=dict(schema='phase30-native-postbattle-parent-stream-v1',status='passed',case=case,variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,core=rt.info,core_path=rel(core),AV=rt.av_info,mother=pin(m),ancestry=anc,state_imported=True,cold_boot=False,additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if c['natural']else 19,natural_ordinary_input_route=c['natural'],controlled_ancestry=not c['natural'],frames=c['frames'],checkpoint_count=len(points),input_step_count=1,initial_fields=initial,final_fields=final,full_audio=wav,observer_events=events,artifact_sha256=artifacts,dependency_pins=[pin(p)for p in deps],full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,
   verified_effects=dict(first_observed_next_battle_state=c['first_stage'],initial_early_stage=c['start_stage'],initial_outcome=c['outcome'],new_numeric_or_status_ready_result_RNG_PC_writes=0),
   limits=['Separate imported window: frame-end pointer/resource values do not replace opcode-time lifecycle evidence. Following C027 is separately attributed.','Only controlled-stage0-human inherits19 declared phase15 numerical preparation writes and incompletely established earlier legacy preparation. Two natural windows have different imported starting frames and are not a continuous stage0-to1 replay.','Internal events from independent observer only; no instantaneous N163/PPU/APU capture.'])
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
 for name in('clean','build','dependency-rebuild'):shutil.copyfile('/tmp/phase30-observer-'+name+'.log',base/('observer-'+name+'.log'))
 old=[('.toolchain/phase21-observer/observed/nestopia_libretro.dylib','45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d'),
  ('.toolchain/phase24-observer/observed/nestopia_libretro.dylib','16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'),
  ('.toolchain/phase25-observer/observed/nestopia_libretro.dylib','7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0'),
  ('.toolchain/phase26-observer/observed/nestopia_libretro.dylib','ed7a9942c789f94595e8a8a842a9574245df5e97f8e57e062b2208e95a6814b1'),
  ('.toolchain/phase27-observer/observed/nestopia_libretro.dylib','4e8df712fb9193474abcc089bc34b9d6c764f1f5ac96075bc9ef8b5da66fc6c2'),('.toolchain/phase28-observer/observed/nestopia_libretro.dylib','818969eae3c71133a9cebb5ef213a735ff4906768d7b3b055d1a1e71a76644b6'),('.toolchain/phase29-observer/observed/nestopia_libretro.dylib','532d6a9113eaef571f56cc1717f97e0d2b39cbb94cb48b01b9886116c54c70cb')]
 for name,value in old:assert sha(ROOT/name)==value
 assert sha(OBSERVER)==sha(UPSTREAM/'libretro/nestopia_libretro.dylib')==OBSERVER_SHA
 write(base/'build.json',dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,parent_frozen_patch=pin(ROOT/'analysis/phase29/runtime/core-provenance/observer.patch'),
  original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),unchanged_old_observers=[pin(ROOT/n)for n,_ in old],
  clean_command=['make','clean'],build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],first_build_clean_new_tree=True,final_source_clean_build=True,
  include_dependency_declared='../source/core/NstCpu.o: ../source/core/NstWatch.cpp.inc ../source/core/NstWatch.hpp',dependency_rebuild_byte_identical=True,
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=n,sha256=sha(UPSTREAM/n))for n in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],
  modified_emulator_object_layout=False,extra_emulated_bus_reads=0,extra_emulated_bus_writes=0,
  snapshot_method='Const RAM/WRAM backing copies only, no map.Peek/map.Poke/device API.',toolchain_in_archive=False,
  ABI_change='68u32 byte layout unchanged from frozen29; new read-only opcode/pointer hooks and independent early exports only. No emulated reads/writes or objectlayout change.'))

def early_observations(folder,case):
 events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));ops=[e for e in events if e['kind']=='opcode_boundary'];early=[e for e in ops if e['physical_bank']==8 and e['opcode_PC']in(0xBAC1,0xBB3D,0xBC46,0xBC52,0xBD59,0xBD67,0xBB36,0xBB8C,0xBB39,0xBB8F)]
 calls=[]
 for e in early:
  if e['opcode_PC']!=0xBC46:continue
  previous=next(p for p in reversed(ops)if p['sequence']<e['sequence']);assert previous['physical_bank']==8 and previous['opcode_PC']==0xBB8C and previous['SP']==e['SP']+2 and e['stack_top_word_raw']&65535==0xBB8E
  calls.append(dict(entry=e,actual_JSR_boundary=previous,return_PC=0xBB8F,not_inferred_from_return_word_minus3=True))
 writes=[e for e in events if e['early_SRAM_write']];city=[e for e in writes if e['address']<0x63C0];controller=[e for e in events if e['early_controller_byte_read']]
 modes=[e for e in early if e['early_mode_dispatch_target']];assert not any(e['opcode_PC']in(0xBB36,0xBD67)for e in early)
 if case=='natural-stage0-human':assert not calls and not city and[e['opcode_PC']for e in early]==[0xBAC1]and[e['value']for e in controller]==[0]
 elif case=='natural-stage1-mode0':
  assert len(calls)==1 and modes[0]['opcode_PC']==0xBC52 and modes[0]['postbattle_mode_6F91']==0 and[e['value']for e in controller]==[3]
  assert[(e['address'],e['storage_byte_before_write'],e['physical_storage_byte_after_event'])for e in city]==[(0x6091+i,255,ID)for i,ID in enumerate((8,191,51,167))]
 else:assert len(calls)==1 and modes[0]['opcode_PC']==0xBD59 and modes[0]['postbattle_mode_6F91']==1 and not city and[e['value']for e in controller]==[0,3]
 entries=[e for e in events if e['full_snapshot_sequence']];pub=[e for e in entries if e['physical_bank']==8 and e['opcode_PC']in(0xA006,0xBAB3,0xBAC1,0xBB3D,0xBC46)and e['RAM0500_0503'][1]<2]
 ecee=[e for e in ops if e['physical_bank']==31 and e['opcode_PC']==0xECEE];returns=[]
 for e in ecee:
  ret=next(p for p in ops if p['sequence']>e['sequence']and p['physical_bank']==31 and p['opcode_PC']==0xED18);resume=next(p for p in ops if p['sequence']>ret['sequence']and p['physical_bank']==8 and p['opcode_PC']==0xBB96);assert e['frame']==ret['frame']==resume['frame']and e['SP']==ret['SP']and resume['SP']==ret['SP']+2;returns.append(dict(entry=e,before_RTS=ret,resumed_parent=resume))
 gates=[e for e in ops if e['physical_bank']==8 and e['opcode_PC']==0xBBA0];holds=[e for e in gates if not e['fade_0087_008A'][0]&128];release=[e for e in gates if e['fade_0087_008A'][0]&128]
 modewrites=[e for e in events if e['kind']=='write_attempt'and e['address']==0x6F91 and e['physical_bank']==8 and e['opcode_PC']in(0xBB2B,0xBB33,0xBB81,0xBB89)]
 return dict(case=case,observer_events=len(events),full_software_snapshots=len(entries),early_original_entries=early,public_early_software_inputs=pub,actual_BC46_calls=calls,mode_targets=modes,controller_byte_reads=controller,original_mode_writes=modewrites,early_SRAM_writes=writes,early_city_roster_writes=city,changed_early_city_bytes=sum(e['storage_byte_before_write']!=e['physical_storage_byte_after_event']for e in city),phase2_ECEE_immediate_returns=returns,phase3_fresh_hold_callbacks=holds,phase3_completion_callbacks=release,city_auxiliary_bus_events=[e for e in events if e['target_type']=='city_auxiliary_bus'],unobserved_in_this_Native_scope=['AI stage0 BB36','BC46 mode2 targetBD67'],limits=['Three separate imported ordinary-input windows; the two natural windows are not a continuous new stage0-to1 playthrough.','Only independent30 observer supplies selected internal software events; instantaneous N163/PPU/APU are not captured.','Controlled route inherits19 known bytes and incompletely established earlier legacy preparation.','Roster assignment here is not recruitment; packed officer status and location are not inferred from a roster write.'])

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
     pcm=wav.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']and wav.tell()*4==row['PCM_stop_byte'];label='frame-%03d'%row['frame'];r=(first/(label+'-ram.bin')).read_bytes();s=(first/(label+'-sram.bin')).read_bytes();state=(first/(label+'.state')).read_bytes();ctx=NestopiaContext.parse(state)
     assert(ctx.ram,ctx.sram,ctx.registers,list(ctx.prg_banks))==(r,s,row['actual_saved_CPU_registers'],row['actual_saved_PRG_banks'])and digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']and fields(r,s)=={k:row[k]for k in fields(r,s)}
     for name in(label+'.state',label+'-ram.bin',label+'-sram.bin',label+'.png'):assert(first/name).read_bytes()==(out/case/'original-control'/name).read_bytes()
     with Image.open(first/(label+'.png'))as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
    assert not wav.readframes(1)and whole.hexdigest()==a['full_audio']['PCM_sha256']and wav.tell()*4==a['full_audio']['PCM_bytes']
   write(first/'repeat-validation.json',dict(status='passed',first=rel(first),second=rel(second),artifact_checks=len(a['artifact_sha256']),all_bytes_exact=True,script_sha256=sha(__file__)))
   streams.append(dict(case=case,variant=variant,validation=case+'/'+variant+'/validation.json',repeat_validation=case+'/'+variant+'/repeat-validation.json',checkpoints=case+'/'+variant+'/checkpoints.json',frame_services=case+'/'+variant+'/frame-services.json',full_audio=case+'/'+variant+'/full-audio.wav',frames=c['frames'],events=a['observer_events']))
  results.append(early_observations(out/case/'observer',case));raw=(out/case/'observer/bus-events.bin').read_bytes();events=[json.loads(x)for x in(out/case/'observer/events.jsonl').read_text().splitlines()];assert len(raw)==len(events)*RECORD_BYTES
  for i,e in enumerate(events):
   assert decode_event(raw[i*RECORD_BYTES:(i+1)*RECORD_BYTES],sequence=i+1)==e
   if e['data_ROM_offset']is not None:assert rom[e['data_ROM_offset']]==e['value']
 write(out/'early-lifecycle-observations.json',dict(schema='phase30-actual-early-postbattle-observations-v1',routes=results,Source_CPU_cases=0,Native_BB36_mode2_observed=False))
 write(out/'repeat-artifact-checks.json',dict(status='passed',checks=checks,nonempty_artifact_checks=len(checks),full_serialized_buffers_not_normalized=True))
 summary=dict(routes=3,natural_routes=2,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=12,original_first_frames=sum(c['frames']for c in CASES.values()),all_control_frames=4*sum(c['frames']for c in CASES.values()),original_checkpoints=sum(c['frames']for c in CASES.values()),nonempty_artifact_repeat_checks=len(checks),PNG_checks=PNG,WAV_checks=WAV,observer_events=sum(x['observer_events']for x in results),full_software_snapshots=sum(x['full_software_snapshots']for x in results),early_public_software_inputs=sum(len(x['public_early_software_inputs'])for x in results),actual_BC46_calls=sum(len(x['actual_BC46_calls'])for x in results),actual_BB8C_calls=2,actual_BB36_calls=0,actual_BC46_mode0_calls=1,actual_BC46_mode1_calls=1,actual_BC46_mode2_calls=0,early_city_roster_writes=sum(len(x['early_city_roster_writes'])for x in results),changed_early_city_roster_bytes=sum(x['changed_early_city_bytes']for x in results),ECEE_immediate_returns=sum(len(x['phase2_ECEE_immediate_returns'])for x in results),phase3_fresh_hold_callbacks=sum(len(x['phase3_fresh_hold_callbacks'])for x in results),phase3_completion_callbacks=sum(len(x['phase3_completion_callbacks'])for x in results),city_auxiliary_bus_events=sum(len(x['city_auxiliary_bus_events'])for x in results),additional_core_memory_writes=0,cold_boots=0,state_imports=12,all_five_complete_buffers_equal_each_frame=True,all_complete_initial_API_buffers_equal=True,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,Source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase30-early-postbattle-native-v1',status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),summary=summary,streams=streams,case_ancestry={case:ancestry(case)for case in CASES},core_provenance=pin(out/'core-provenance/build.json'),observations='early-lifecycle-observations.json',Source_CPU_cases=0,original_core_internal_CPU_trace=False,limits=['Separate imported windows, not a new continuous battle or cold boot. Natural2 and controlled1 ancestries are distinct.','Fixed original vs distinct observer full initial/frame buffers exact. No instantaneous N163/PPU/APU capture.','BB36/mode2 not observed; absence is bounded to these windows, not an unreachability claim.'])
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
