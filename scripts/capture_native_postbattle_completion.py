#!/usr/bin/env python3
"""Stage3 ownership/roster continuation under original ordinary inputs and a separate passive core.

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
from capture_native_postbattle_pointer import serialized,sha,ROM_SHA,CORE_SHA,decode_event as decode_parent
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/phase29-observer/observed/nestopia_libretro.dylib'
OBSERVER_SHA='532d6a9113eaef571f56cc1717f97e0d2b39cbb94cb48b01b9886116c54c70cb'
UPSTREAM=ROOT/'.toolchain/phase29-observer/upstream';RUN=ROOT/'analysis/phase29/runtime'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3';WORDS=68;RECORD_BYTES=272;SNAPSHOT_BYTES=10240
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
  active_city_byte11=s[r[0x50E]*32+11],raw_supplies_052B_0533=list(r[0x52B:0x534]),fade_0087_008A=list(r[0x87:0x8B]),ppu_flags_007D_0080=list(r[0x7D:0x81]),palette_active_0100_011F=list(r[0x100:0x120]),palette_backup_0120_013F=list(r[0x120:0x140]),shadow_bank_bytes_00DE_00E5=list(r[0xDE:0xE6]))
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
 w=struct.unpack('<68I',raw_record)if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record);assert len(w)==68
 e=decode_parent(w[:48],frame,sequence);a=e['address'];p=a&0x7FF;write=e['kind']=='write_attempt'
 fade=[w[48]>>b&255 for b in(0,8,16,24)];jobs=[w[49]>>b&255 for b in(0,8,16,24)];pal=[v>>b&255 for v in w[50:66]for b in(0,8,16,24)];shadows=[v>>b&255 for v in w[66:68]for b in(0,8,16,24)]
 target=e['target_type'];after=None
 if write and a<0x2000:
  if 0x87<=p<=0x8A:target='fade_RAM_write';after=fade[p-0x87]
  elif 0x100<=p<0x140:target='palette_RAM_write';after=pal[p-0x100]
  elif 0xDE<=p<=0xE5:target='PRG_shadow_RAM_write';after=shadows[p-0xDE]
  elif 0x7D<=p<=0x80:target='NMI_job_RAM_write';after=jobs[p-0x7D]
  elif p in(0x78,0x7A,0x400,0x401,0x500,0x501):
   target='scene_state_RAM_write';after={0x78:e['NMI_scene_0078'],0x7A:e['global_main_007A'],0x400:e['city_state_0400_0403'][0],0x401:e['city_state_0400_0403'][1],0x500:e['RAM0500_0503'][0],0x501:e['RAM0500_0503'][1]}[p]
  elif 0x81<=p<=0x86:target='controller_RAM_write'
 e.update(target_type=target,fade_0087_008A=fade,ppu_flags_007D_0080=jobs,palette_active_0100_011F=pal[:32],palette_backup_0120_013F=pal[32:],shadow_bank_bytes_00DE_00E5=shadows,captured_RAM_byte_after_write=after)
 if write and a<0x2000 and p in(0,1,2,3,6,7,10,11,12):
  e.update(target_type='completion_pointer_RAM_write',captured_RAM_byte_after_write=e['ZP_0000_002F'][p])
 pc=e['opcode_PC'];physical=e['physical_bank'];read=e['kind']in('read','word_read_low','word_read_high');ea0=(e['pointer_0000_0001']+e['Y'])&65535;cityptr=e['ZP_0000_002F'][10]|e['ZP_0000_002F'][11]<<8;eaA=(cityptr+e['Y'])&65535
 e.update(saved_city_pointer_000A_000B=cityptr,logical_completion_city_read=physical==8 and e['kind']=='read' and((pc==0xBBD6 and a==ea0)or(pc in(0xBC0E,0xBC23,0xBC34)and a==eaA)),logical_completion_leader_read=physical==8 and pc==0xBC1C and e['kind']=='read'and a==ea0,logical_completion_adjacency_read=physical==8 and pc==0xBBEB and e['kind']=='read'and a==((0x9D72+e['Y'])&65535),logical_completion_city_store=physical==8 and write and((pc==0xBBDD and a==ea0)or(pc in(0xBC3C,0xBC43)and a==eaA)),completion_STA_dummy_bus_read=physical==8 and e['kind']=='read'and((pc==0xBBDD and a==ea0)or(pc in(0xBC3C,0xBC43)and a==eaA)),logical_CC29_profile_ROM_read=physical==13 and pc in(0xCC92,0xCCAC)and e['kind']=='read'and a==((e['ZP_0000_002F'][6]|e['ZP_0000_002F'][7]<<8)+e['Y'])&65535)
 return e

def start_observer(rt,out):
 if not hasattr(rt.core,'nestopia_completion_enable'):return None
 core=rt.core
 for name in('enable','begin_frame'):
  f=getattr(core,'nestopia_completion_'+name);f.argtypes=[C.c_uint];f.restype=None
 for name in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_completion_'+name).restype=C.c_uint
 core.nestopia_completion_data.restype=C.POINTER(C.c_uint32);core.nestopia_completion_snapshot_data.restype=C.POINTER(C.c_ubyte)
 assert core.nestopia_completion_words()==WORDS
 original=core.retro_run
 def run():core.nestopia_completion_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_completion_enable(7)
 parent=json.loads((ROOT/'analysis/phase27/runtime/natural-postbattle-skip/observer/event-schema.json').read_text())
 added=['RAM0087_008A_fade_packed4','RAM007D_0080_jobs_packed4']+[f'RAM{0x100+4*i:04X}_{0x103+4*i:04X}_palette_packed4'for i in range(16)]+['RAM00DE_00E1_bank_shadow_packed4','RAM00E2_00E5_bank_shadow_packed4']
 write(out/'event-schema.json',dict(schema='phase29-passive-postbattle-parent-ABI-v1',words=WORDS,bytes_per_record=RECORD_BYTES,raw_layout=parent['raw_layout']+added,
  sequence='One-based globally contiguous per fresh process; begin_frame doesnot resetsequence.',cycle='Original cycles.count, including unchangedframe rebasing.',
  opcode_PC='Actual ExecuteOp PC before FetchPc8; bus_PC actual Cpu.pc. last_CPU_opcode_field is previousopcode at preFetch boundaries.',
  before_after='Word44 const physicalbacking before originalwrite; word17 WRAM backingafter. NewRAM domains capturepostvalue frompackedbacking; controller82..86 postvalue not independentlycaptured.',
  snapshot=dict(bytes=10240,layout='physical2048RAM then8192WRAM',scope='Selected actual opcode boundaries, not allare publicJSR entries. D4F0/CC29 are actual software entries; D4F5 is a later middle-entry.',method='Const physicalbacking copy, no map.Peek/device API',instantaneous_N163_PPU_APU_captured=False),
  watch=dict(city='Allcity6000..63BF writes and150 auxiliarybus accesses',RAM='00..03,06/07,0A..0C,1A/B,7D..8A,78/7A,DE..E5,0100..013F,400/401,500/501 originalwrites',
   opcodes='13D4F0/D4F5/D4FA andCC29..CCE5 profile helper;8A006/BAB3/BB93..BC45/G106;9C027/C07A;31EC67..ED18/EE07..EE52/F237/F25F/F2AF/F368..F378. Allscopes filtered byactualPRG.'),
  original_reference='original-control',overflow='Hardfailure on eventor snapshot overflow; no silentdrops',
  limits=['ECEE immediateRTS startsasynchronous palettework; itis not a blockingwait. LaterBBA0 calls are fresh perNMI invocations.',
   'Onlyindependent observer has internal selectedevents. No instantaneous N163/PPU/APU capture.',
   'Observed21frame completion depends on actualold8A=4; ECEE itselfdoesnot initialise8A. LaterECBFfade is a separateepoch.']))
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter(),targets=collections.Counter())
def drain(rt,obs,out,case):
 if obs is None:return
 c=rt.core;assert c.nestopia_completion_overflow()==c.nestopia_completion_snapshot_overflow()==0
 n=c.nestopia_completion_count();raw=C.string_at(c.nestopia_completion_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=c.nestopia_completion_snapshot_count();snap=C.string_at(c.nestopia_completion_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<68I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1;obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n');obs['kinds'][e['kind']]+=1;obs['targets'][e['target_type']]+=1
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count'];payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:];assert list(r[:0x30])==e['ZP_0000_002F']
   prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,
    RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],stack_top_word_raw=e['stack_top_word_raw'],
    actual_battle_state=list(r[0x500:0x502]),actual_outcome=r[0x514],actual_fade_0087_008A=list(r[0x87:0x8B]),actual_shadow_DE_E5=list(r[0xDE:0xE6]),capture_core_sha256=rt.info['core_sha256'],mother=pin(mother(case)),additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if CASES[case]['natural']else 19,
    instantaneous_N163_PPU_APU_captured=False,origin='Independent29 passive observer actual pre-opcode software context, retaining actual existing stack; not fixed-core internal trace.',exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin')
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
  deps=[Path(__file__),ROOT/'scripts/capture_native_postbattle_pointer.py',ROOT/'scripts/capture_native_deployment_pointer.py',ROOT/'scripts/capture_native_appearance_pointer.py',ROOT/'scripts/capture_native_pointer_lifecycle.py',ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',m,m.with_name(m.stem+'-ram.bin'),m.with_name(m.stem+'-sram.bin'),ROOT/'analysis/phase27/runtime/natural-postbattle-skip/observer/event-schema.json']
  deps += [ROOT/x['path']for x in anc.values()if isinstance(x,dict)and 'path'in x and 'sha256'in x]
  receipt=dict(schema='phase29-native-postbattle-parent-stream-v1',status='passed',case=case,variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,core=rt.info,core_path=rel(core),AV=rt.av_info,mother=pin(m),ancestry=anc,state_imported=True,cold_boot=False,additional_core_memory_writes=0,known_inherited_preparation_byte_writes=0 if c['natural']else 19,natural_ordinary_input_route=c['natural'],controlled_ancestry=not c['natural'],frames=c['frames'],checkpoint_count=len(points),input_step_count=1,initial_fields=initial,final_fields=final,full_audio=wav,observer_events=events,artifact_sha256=artifacts,dependency_pins=[pin(p)for p in deps],full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,
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
 for name in('clean','build','dependency-rebuild'):shutil.copyfile('/tmp/phase29-observer-'+name+'.log',base/('observer-'+name+'.log'))
 old=[('.toolchain/phase21-observer/observed/nestopia_libretro.dylib','45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d'),
  ('.toolchain/phase24-observer/observed/nestopia_libretro.dylib','16563909e4254f3d0fc34c3ecef9399a4a43f686230b32e66fae6256b630ea31'),
  ('.toolchain/phase25-observer/observed/nestopia_libretro.dylib','7ce7eb671327d6bcf629a1b5a5e43fa6a4184781bb75a6db91b0c1ed5c2b82f0'),
  ('.toolchain/phase26-observer/observed/nestopia_libretro.dylib','ed7a9942c789f94595e8a8a842a9574245df5e97f8e57e062b2208e95a6814b1'),
  ('.toolchain/phase27-observer/observed/nestopia_libretro.dylib','4e8df712fb9193474abcc089bc34b9d6c764f1f5ac96075bc9ef8b5da66fc6c2'),('.toolchain/phase28-observer/observed/nestopia_libretro.dylib','818969eae3c71133a9cebb5ef213a735ff4906768d7b3b055d1a1e71a76644b6')]
 for name,value in old:assert sha(ROOT/name)==value
 assert sha(OBSERVER)==sha(UPSTREAM/'libretro/nestopia_libretro.dylib')==OBSERVER_SHA
 write(base/'build.json',dict(status='recorded',upstream='https://github.com/libretro/nestopia.git',commit=COMMIT,parent_frozen_patch=pin(ROOT/'analysis/phase28/runtime/core-provenance/observer.patch'),
  original_core=pin(ORIGINAL),passive_observer=pin(OBSERVER),unchanged_old_observers=[pin(ROOT/n)for n,_ in old],
  clean_command=['make','clean'],build_command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6'],first_build_clean_new_tree=True,final_source_clean_build=True,
  include_dependency_declared='../source/core/NstCpu.o: ../source/core/NstWatch.cpp.inc ../source/core/NstWatch.hpp',dependency_rebuild_byte_identical=True,
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),patch_sha256=digest(patch),source_files=sources,
  debug_files=[dict(path=n,sha256=sha(UPSTREAM/n))for n in('source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc')],
  modified_emulator_object_layout=False,extra_emulated_bus_reads=0,extra_emulated_bus_writes=0,
  snapshot_method='Const RAM/WRAM backing copies only, no map.Peek/map.Poke/device API.',toolchain_in_archive=False,
  ABI_change='68u32 byte layout unchanged from frozen28; new read-only opcode/pointer hooks and independent completion exports only. No emulated reads/writes or objectlayout change.'))
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

def palette_lifecycle(folder,case):
 events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));ops=[e for e in events if e['kind']=='opcode_boundary'];writes=[e for e in events if e['kind']=='write_attempt']
 def op(pc,frame=None,after=0):return next(e for e in ops if e['physical_bank']==(13 if pc in(0xD4F0,0xD4F5,0xD4FA)else 8 if pc in(0xA006,0xBAB3,0xBB93,0xBB96,0xBB99,0xBB9C,0xBB9F,0xBBA0,0xBBA3,0xBBA5,0xBBB7,0xBBB8)else 9 if pc in(0xC027,0xC07A)else 31)and e['opcode_PC']==pc and(frame is None or e['frame']==frame)and e['sequence']>after and(pc!=0xEE07 or e['stack_top_word_raw']&65535==0xD4F7)and(pc!=0xEE4D or(e['stack_above_SP_4bytes'][1]|e['stack_above_SP_4bytes'][2]<<8)==0xD4F9)and(pc!=0xEE52 or e['stack_top_word_raw']&65535==0xD4F9))
 initial=json.loads((folder/'initial-fields.json').read_text());start=op(0xECEE);ret=op(0xED18);resume=op(0xBB96);complete=next(e for e in writes if e['physical_bank']==31 and e['opcode_PC']==0xEC95 and e['address']==0x87 and e['sequence']>start['sequence'])
 request=next(e for e in writes if e['opcode_PC']==0xECF0 and e['address']==0x87 and e['sequence']>start['sequence'])
 assert(start['frame'],ret['frame'],resume['frame'],complete['frame'])==(1,1,1,21)
 assert initial['fade_0087_008A'][3]==4 and start['fade_0087_008A']==[255,0,4,4]and ret['fade_0087_008A']==[1,0,4,4]
 assert ret['palette_backup_0120_013F']==start['palette_active_0100_011F']and ret['palette_active_0100_011F']==start['palette_active_0100_011F']
 assert start['SP']==ret['SP']and(start['stack_top_word_raw']&65535)==(ret['stack_top_word_raw']&65535)==0xBB95 and resume['SP']==(ret['SP']+2)&255
 assert request['storage_byte_before_write']==255 and request['captured_RAM_byte_after_write']==1 and complete['storage_byte_before_write']==1 and complete['captured_RAM_byte_after_write']==255
 gates=[e for e in ops if e['physical_bank']==8 and e['opcode_PC']==0xBBA0 and start['sequence']<e['sequence']<=op(0xBBB8)['sequence']];holds=[e for e in gates if e['fade_0087_008A'][0]<128];release=[e for e in gates if e['fade_0087_008A'][0]>=128]
 assert[e['frame']for e in holds]==list(range(2,21))and len(release)==1 and release[0]['frame']==21
 hold_records=[]
 for gate in holds:
  branch=op(0xBBA3,gate['frame'],gate['sequence']);returned=op(0xBBB7,gate['frame'],branch['sequence']);far=op(0xEE07,gate['frame'])
  assert branch['A']==gate['fade_0087_008A'][0]==1 and not branch['P']&128 and returned['SP']==gate['SP']and returned['stack_top_word_raw']==gate['stack_top_word_raw']and far['stack_top_word_raw']&65535==0xD4F7
  hold_records.append(dict(gate=gate,BPL_branch=branch,hold_return_before_RTS=returned,fresh_parent_far_call=far,scope='Fresh perNMI call; ECEE is not suspended acrossthese frames. Stage3Source isnot claimedimplemented.'))
 advances=[e for e in writes if e['physical_bank']==31 and e['opcode_PC']==0xEC81 and e['address']==0x88 and start['sequence']<e['sequence']<complete['sequence']and e['captured_RAM_byte_after_write']!=e['storage_byte_before_write']]
 assert[(e['frame'],e['captured_RAM_byte_after_write'])for e in advances]==[(6,1),(11,2),(16,3),(21,4)]
 palette=[e for e in writes if e['physical_bank']==31 and e['opcode_PC']==0xECB9 and start['sequence']<e['sequence']<=op(0xECBE,21)['sequence']and 0x100<=e['address']<0x120]
 assert len(palette)==128 and collections.Counter(e['frame']for e in palette)=={6:32,11:32,16:32,21:32}
 stage2_return=op(0xBB9F,1);assert stage2_return['RAM0500_0503'][1]==3 and stage2_return['fade_0087_008A'][0]==1
 stage_writes=[e for e in writes if e['address']==0x501 and e['physical_bank']==8 and e['opcode_PC']==0xBB9C];assert[(e['storage_byte_before_write'],e['captured_RAM_byte_after_write'])for e in stage_writes]==[(2,2),(2,3)];stages=[e for e in stage_writes if e['captured_RAM_byte_after_write']!=e['storage_byte_before_write']]
 farentry=op(0xEE07,1);farafter=op(0xEE4D,1);farreturn=op(0xEE52,1);bridge_return=op(0xD4FA,1);assert bridge_return['actual_PRG_banks'][1:3]==[12,13]
 late=[e for e in ops if e['physical_bank']==31 and e['opcode_PC']in(0xECBF,0xECEE)and e['sequence']>complete['sequence']];assert late and late[0]['frame']==24 and late[0]['opcode_PC']==0xECBF
 source_inputs=[e for e in events if e['full_snapshot_sequence']and((e['physical_bank']==8 and e['opcode_PC']in(0xA006,0xBAB3,0xBB93))or(e['physical_bank']==9 and e['opcode_PC']==0xC027))and e['RAM0500_0503'][1]==2]
 assert len(source_inputs)==4
 unsupported=[e for e in events if e['full_snapshot_sequence']and e['physical_bank']==8 and e['opcode_PC']==0xA006 and e['RAM0500_0503'][1]==3];assert[e['frame']for e in unsupported]==[2,21]
 return dict(case=case,initial_fade_0087_008A=initial['fade_0087_008A'],D4F5_middle_entry=op(0xD4F5,1),CC29_predecessor_entry=op(0xD4F0,1),
  phase2_Source_actual_software_entries=source_inputs,phase3_Source_unsupported_actual_inputs=unsupported,ECEE_entry=start,ECEE_request_write=request,ECEE_before_immediate_RTS=ret,same_caller_resumed_BB96=resume,
  phase2_BB99_before_supply=op(0xBB99,1),phase2_BB9C_after_supply=op(0xBB9C,1),phase2_to3_original_store=stages[0],phase2_to3_original_RMW_write_attempts=stage_writes,phase2_before_RTS=stage2_return,
  first_parent_far_entry=farentry,first_parent_far_after_callee=farafter,first_parent_far_before_RTS=farreturn,first_parent_bridge_return=bridge_return,
  sub3_hold_records=hold_records,fade_original_88_progression=advances,fade_original_0100_011F_writes=palette,fade_original_completion87_write=complete,
  sub3_completion_gate=release[0],sub3_native_cleanup_entry=op(0xBBB8,21),later_independent_palette_requests=late,
  observed=dict(request_frame=1,immediate_RTS_frame=1,phase2_return_frame=1,hold_frames=list(range(2,21)),hold_count=19,completion_frame=21,late_independent_request_frame=24,palette_store_attempts=128,phase2_Source_callees=4,phase3_Source_prefix_inputs=2),
  limits=['ECEE doesnot initialise8A;21frames is thisactualmother old8A4 only.','sub3hold/cleanup are originalNative observations, not newSourceclosure.','EE07 restorescodepair/E2, butF25F dataE1 sideeffects persist; full4banksandshadows retained.','No instantaneousN163/PPU/APU statecapture.'])

def completion_lifecycle(folder,case):
 events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()));ops=[e for e in events if e['kind']=='opcode_boundary']
 first=next(e for e in ops if e['physical_bank']==8 and e['opcode_PC']==0xBBB8);last=next(e for e in ops if e['sequence']>first['sequence']and e['physical_bank']==8 and e['opcode_PC']==0xBBB7);window=[e for e in events if first['sequence']<=e['sequence']<=last['sequence']]
 logical=[e for e in window if e['logical_completion_city_read']];adj=[e for e in window if e['logical_completion_adjacency_read']];leader=[e for e in window if e['logical_completion_leader_read']];stores=[e for e in window if e['logical_completion_city_store']];dummy=[e for e in window if e['completion_STA_dummy_bus_read']]
 assert first['frame']==last['frame']==21 and first['SP']+2==last['SP']and first['stack_top_word_raw']&65535==0xBBA7
 assert [e['value']for e in adj]==[2,12,11,3,1,255]and all(e['data_physical_bank']==16 for e in adj)
 entries=[e for e in window if e['kind']=='opcode_boundary'and e['physical_bank']==8 and e['opcode_PC']==0xBC00];assert len(entries)==6 and[e['pointer_0000_0001']for e in entries]==[0x6080,0x6040,0x6180,0x6160,0x6060,0x6020]
 assert len(stores)==len(dummy)==(8 if CASES[case]['natural']else 7)
 changed=[e for e in stores if e['storage_byte_before_write']!=e['physical_storage_byte_after_event']];same=[e for e in stores if e not in changed]
 if CASES[case]['natural']:assert not changed and all(e['opcode_PC']in(0xBC3C,0xBC43)for e in stores)
 else:assert len(changed)==1 and(changed[0]['opcode_PC'],changed[0]['address'],changed[0]['storage_byte_before_write'],changed[0]['physical_storage_byte_after_event'])==(0xBBDD,0x6080,1,2)
 assert all(e['actual_PRG_banks']==[16,8,9,31]for e in stores)
 profile=[e for e in events if e['logical_CC29_profile_ROM_read']];ptrwrites=[e for e in window if e['target_type']=='completion_pointer_RAM_write']
 return dict(case=case,scope='Same frozen28 imported ordinary-input continuation; only new independent29 observer supplies selected internal events.',BBB8_entry=first,parent_BBB7_before_RTS=last,BC00_entries=entries,logical_city_reads=logical,leader_record_reads=leader,adjacency_ROM_reads=adj,city_stores=stores,STA_dummy_bus_reads=dummy,changed_store_count=len(changed),same_value_store_count=len(same),changed_stores=changed,unchanged_stores=same,pointer_and_scratch_writes=ptrwrites,CC29_profile_ROM_reads=profile,all_selected_completion_events=window,observed_nontrivial_roster_swap=False,limits=['Six actual city visits do not impose a generic six-city bound; original Y wraps and table terminates atFF.','BC00 scans17..26 without treatingFF as an early terminator; Actual roster stores here select slot17; other visited cities scan all10 slots without a leader match.','Only the controlled ancestor changes city owner; fourteen roster writes across the routes all retain the original byte value.','No instantaneous N163/PPU/APU state. Later city controller lifecycle remains separate.'])

def aggregate(out,rom_path):
 repeat=out.parent/(out.name+'-repeat');checks=[];streams=[];results=[];lifecycles=[];completions=[];PNG=WAV=0;rom=Path(rom_path).read_bytes();assert digest(rom)==ROM_SHA
 for case,c in CASES.items():
  original_rows=None
  for variant in('original-control','observer'):
   first,second=out/case/variant,repeat/case/variant;a=json.loads((first/'validation.json').read_text());b=json.loads((second/'validation.json').read_text());assert a==b and a['status']=='passed'
   for name,p in a['artifact_sha256'].items():
    assert(first/name).read_bytes()==(second/name).read_bytes()and sha(first/name)==p['sha256'];checks.append(dict(case=case,first=rel(first/name),repeat=rel(second/name),**p));PNG+=name.endswith('.png');WAV+=name.endswith('.wav')
   rows=json.loads((first/'frame-services.json').read_text());assert len(rows)==c['frames']
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   parent_rows=json.loads((ROOT/'analysis/phase28/runtime'/case/'original-control/frame-services.json').read_text());assert len(parent_rows)==len(rows)and all(all(a[k]==b[k]for k in FIVE)for a,b in zip(rows,parent_rows))
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
  ob=observations(out/case/'observer',case);results.append(ob);lifecycles.append(palette_lifecycle(out/case/'observer',case));completions.append(completion_lifecycle(out/case/'observer',case))
  for e in [json.loads(x)for x in(out/case/'observer/events.jsonl').read_text().splitlines()]:
   if e['data_ROM_offset']is not None:assert rom[e['data_ROM_offset']]==e['value']
   if e['target_type']=='pointer_001A_001B_RAM_write':assert e['ZP_0000_002F'][e['address']&0x7FF]==e['value']
 write(out/'postbattle-observations.json',dict(schema='phase29-actual-postbattle-observations-v1',routes=results,limits=['Positive controlled ancestry is not claimed naturally reachable.','Instantaneous effects, subsequent supply return, and frame-end resources are separate.','11 original resource stores are7 changed bytes plus4 unchanged stores, not11 independent changed fields.']))
 write(out/'palette-lifecycle-observations.json',dict(schema='phase29-actual-asynchronous-palette-parent-observations-v1',routes=lifecycles,Source_stage3_closure_claim=False,old8A_dependency_explicit=True))
 write(out/'completion-lifecycle-observations.json',dict(schema='phase29-actual-postbattle-completion-observations-v1',routes=completions,Source_CPU_cases=0,limits=['Same imported mother/input continuations as frozen28, not a new naturally won battle.','Software contexts belong only to this independent observer. No instantaneous N163/PPU/APU capture.']))
 write(out/'repeat-artifact-checks.json',dict(status='passed',checks=checks,nonempty_artifact_checks=len(checks),full_serialized_buffers_not_normalized=True))
 summary=dict(completion_city_read_count=sum(len(x['logical_city_reads'])for x in completions),completion_adjacency_read_count=sum(len(x['adjacency_ROM_reads'])for x in completions),completion_leader_read_count=sum(len(x['leader_record_reads'])for x in completions),completion_city_store_count=sum(len(x['city_stores'])for x in completions),completion_changed_bytes=sum(x['changed_store_count']for x in completions),completion_same_value_stores=sum(x['same_value_store_count']for x in completions),completion_STA_dummy_read_count=sum(len(x['STA_dummy_bus_reads'])for x in completions),routes=2,natural_routes=1,controlled_ancestry_routes=1,core_variants=2,fresh_process_runs=8,original_first_frames=sum(c['frames']for c in CASES.values()),all_control_frames=4*sum(c['frames']for c in CASES.values()),original_checkpoints=sum(c['frames']for c in CASES.values()),nonempty_artifact_repeat_checks=len(checks),PNG_checks=PNG,WAV_checks=WAV,
  ECEE_requests=2,ECEE_immediate_RTS_returns=2,sub3_hold_checks=38,fade_completion_EC95_writes=2,phase3_native_releases=2,unchanged_phase28_original_fivebuffer_frames=96,observer_events=sum(r['observer_events']for r in results),full_software_snapshots=sum(len(r['software_entries'])for r in results),logical_G106_reads=sum(r['logical_read_count']for r in results),G106_STA_dummy_read_count=sum(r['STA_dummy_read_count']for r in results),G106_store_count=sum(r['store_count']for r in results),G106_changed_byte_count=sum(r['changed_byte_count']for r in results),G106_unchanged_store_count=sum(r['unchanged_write_count']for r in results),city_auxiliary_bus_events=sum(len(r['city_auxiliary_events'])for r in results),additional_core_memory_writes=0,cold_boots=0,state_imports=8,all_five_complete_buffers_equal_each_frame=True,all_complete_initial_API_buffers_equal=True,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,Source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase29-postbattle-parent-and-palette-native-v1',status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),summary=summary,streams=streams,case_ancestry={case:ancestry(case)for case in CASES},core_provenance=pin(out/'core-provenance/build.json'),completion_lifecycle='completion-lifecycle-observations.json',observations='postbattle-observations.json',palette_lifecycle='palette-lifecycle-observations.json',Source_CPU_cases=0,original_core_internal_CPU_trace=False,limits=['Imported state continuations, not new cold boots. Positive parent has19 declared numerical writes plus incompletely established earlier legacy preparation.','Fixed original vs distinct observer full initial/frame buffers exact; internal events exist only in independent observer.','No instantaneous N163, PPU or APU capture. Untaken paths remain separate CPU fixtures; no whole-ROM completion claim.'])
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
