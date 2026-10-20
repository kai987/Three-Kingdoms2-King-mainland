#!/usr/bin/env python3
"""WP05 ordinary-input nonempty disposition replay. Execution is reserved to Root.

This new producer never writes emulated memory. Imports expose definitions only;
no historical capture or emulator is run by importing this module. A new route
may be supplied as pinned data with --case-spec; old outputs are never replaced.
"""
from pathlib import Path
import argparse,collections,ctypes as C,functools,hashlib,json,os,shutil,struct,subprocess,sys,wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from source.recovered.nestopia_context import NestopiaContext
import capture_native_postbattle_early as parent
serialized,ROM_SHA,CORE_SHA=parent.serialized,parent.ROM_SHA,parent.CORE_SHA
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def compare_files_exact(left,right):
 """Read both complete files, including serialized padding; never normalize."""
 left,right=Path(left),Path(right);assert not left.is_symlink()and not right.is_symlink()
 assert left.stat().st_size==right.stat().st_size,(left,right,'size differs')
 h=hashlib.sha256();size=0
 with left.open('rb')as a,right.open('rb')as b:
  while True:
   x,y=a.read(1024*1024),b.read(1024*1024);assert x==y,(left,right,'bytes differ')
   if not x:break
   h.update(x);size+=len(x)
 return dict(bytes=size,sha256=h.hexdigest())
def hardlink_identical(anchor,target,scope,expected):
 """Storage only: replace a verified new WP05 file with an identical hardlink."""
 anchor,target,scope=Path(anchor),Path(target),Path(scope).resolve();new=ROOT/'analysis/wp05-natural-nonempty'
 assert scope.is_relative_to(new.resolve()),'Only new wp05-natural-nonempty output may be deduplicated'
 for path in(anchor,target):
  assert not path.is_symlink()and path.resolve().is_relative_to(scope),'No old or external artifact may be linked'
 actual=compare_files_exact(anchor,target);assert actual==expected,(anchor,target,'receipt mismatch')
 if not os.path.samefile(anchor,target):
  temporary=target.with_name(target.name+'.hardlink-'+str(os.getpid()));assert not temporary.exists()
  try:os.link(anchor,temporary);os.replace(temporary,target)
  finally:
   if temporary.exists():temporary.unlink()
 assert os.path.samefile(anchor,target)and target.stat().st_size==actual['bytes']
 return dict(anchor=rel(anchor),target=rel(target),**actual,complete_byte_comparison_passed=True,storage_only=True)
def deduplicate_streams(anchor,target,scope,relation):
 """Only receipt-listed immutable capture files, never validation outputs."""
 av=json.loads((anchor/'validation.json').read_text());tv=json.loads((target/'validation.json').read_text());assert av['status']==tv['status']=='passed'
 same_variant=av['variant']==tv['variant'];assert av['case']==tv['case']
 if same_variant:assert av==tv
 rows=[]
 for name,expected in tv['artifact_sha256'].items():
  if av['artifact_sha256'].get(name)!=expected:
   assert not same_variant,(name,'repeat artifact mismatch')
   continue
  row=hardlink_identical(anchor/name,target/name,scope,expected);row['relation']=relation;rows.append(row)
 write(target/'storage-deduplication.json',dict(schema='wp05-natural-nonempty-byte-exact-hardlink-storage-v1',status='passed',relation=relation,checks=rows,byte_normalization=False,scope='Only new WP05 capture files; full byte comparison precedes hardlink replacement. Native observations and serialized bytes are unchanged.'))
 return rows
ORIGINAL=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER=ROOT/'.toolchain/wp05-observer-v2/observed/nestopia_libretro.dylib'
BUILD=ROOT/'analysis/wp05-natural-nonempty/core-provenance/build.json'
OBSERVER_SHA=json.loads(BUILD.read_text())['observer']['sha256']
UPSTREAM=ROOT/'.toolchain/wp05-observer-v2/upstream';RUN=ROOT/'analysis/wp05-natural-nonempty/runtime'
COMMIT=parent.COMMIT;WORDS=72;RECORD_BYTES=288;SNAPSHOT_BYTES=10240
FIVE=parent.FIVE
CASES={} # Root supplies a pinned, bounded ordinary-input case-spec; no inherited default execution.

HUMAN_ENTRIES=(0xCD16,0xCD2A,0xCD52,0xCDF2,0xCE56,0xCE76,0xCE9E,0xCF09,0xD2CD,0xD2E1,0xD310,0xD34B,0xD3AF,0xD3D7,0xD3F7,0xD462)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def pin(p):p=Path(p);return dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p))
def mother(case):return ROOT/CASES[case]['mother']
@functools.lru_cache(maxsize=None)
def ancestry(case):
 c=CASES[case]
 assert c['natural'] is True and c['ancestry_path'] and c['ancestry_sha256']
 ap=ROOT/c['ancestry_path'];assert sha(ap)==c['ancestry_sha256']
 a=json.loads(ap.read_text());assert a['additional_core_memory_writes']==0 and a['additional_preparation']==[]
 assert a['natural_ordinary_input_route'] and not a['controlled_ancestry']
 assert a['segmented_upstream_frames']==88463 and len(a['segments'])==6
 m=mother(case);assert sha(m)==c['mother_sha256']==a['mother']['sha256']
 assert a['mother']['path']==c['mother'] and a['parent_checkpoint']['frame']==c['parent_frame']
 assert a['parent_checkpoint']['state']==c['mother']
 for proof in a['required_input_pins']:
  assert sha(ROOT/proof['path'])==proof['sha256'],proof['path']
 return a

def plan(case):
 c=CASES[case]
 if c.get('plan_source'):
  path=ROOT/c['plan_source']
  if c.get('plan_sha256'):assert sha(path)==c['plan_sha256']
  rows=json.loads(path.read_text());result=[]
  for i,row in enumerate(rows):
   lo=max(c['plan_start'],row['start_frame']);hi=min(c['plan_end'],row['start_frame']+row['frames'])
   if hi>lo:result.append(dict(start_frame=lo-c['plan_start'],frames=hi-lo,buttons=row['buttons'],parent_step=i,parent_start_frame=row['start_frame']))
 elif c.get('direct_plan'):result=c['direct_plan']
 else:result=[dict(start_frame=0,frames=c['frames'],buttons=[])]
 assert sum(x['frames']for x in result)==c['frames'];cursor=0
 for row in result:assert row['start_frame']==cursor;cursor+=row['frames'];assert set(row['buttons'])<=set(('a','b','start','select','up','down','left','right'))
 return result

def fields(r,s):
 f=parent.fields(r,s);active=r[0x7A]in(3,4)and r[0x78]==3
 f.update(active_postbattle_controller=active and r[0x500]in(13,14,15),active_human_disposition=[r[0x500],r[0x501]]if active and r[0x500]in(13,14)else None,buttons_0081_0086=list(r[0x81:0x87]),all7_ruler_controllers=[s[0xF0A+8*i]for i in range(7)],raw_UI_roster_042C_043F=list(r[0x42C:0x440]),raw_selected_flags_0580_0593=list(r[0x580:0x594]),raw_destination_0540=r[0x540],raw_title_0540_0547=list(r[0x540:0x548]))
 f.update(packed_rulers_0507=r[0x507],origin_city_052A=r[0x52A],current_ruler_6F03=s[0xF03],cooperation_request_6F8B=s[0xF8B],unit_arrays_raw={hex(base):list(r[base:base+20])for base in(0x600,0x614,0x628,0x63C,0x650,0x664)},active_officer_records_raw12={str(ID):s[0x3C0+12*ID:0x3C0+12*(ID+1)].hex()for ID in set(r[0x664:0x678])if ID<237})
 return f

def decode_event(raw_record,frame=None,sequence=None):
 raw=tuple(struct.unpack('<72I',raw_record))if isinstance(raw_record,(bytes,bytearray,memoryview))else tuple(raw_record);assert len(raw)==72
 e=parent.decode_event(raw[:68],frame,sequence);unpack=lambda x:[(x>>(8*i))&255 for i in range(4)]
 a,b,c,d=[unpack(raw[k])for k in range(68,72)];e.update(buttons_0081_0086=a+b[:2],side_0504=b[2],raw_050B=b[3],UI_0540_0547=c+d)
 e['human_disposition_entry']=e['kind']=='opcode_boundary'and e['physical_bank']==13 and e['opcode_PC']in HUMAN_ENTRIES
 e['title_Start_bypass']=e['kind']=='opcode_boundary'and e['physical_bank']==9 and e['opcode_PC']==0xD7C3
 e['ruler_controller_write']=e['kind']=='write_attempt'and 0x6F0A<=e['address']<=0x6F3A and(e['address']-0x6F0A)%8==0
 e['postbattle_allocation_commit']=e['kind']=='write_attempt'and e['physical_bank']in(8,13)and 0x6000<=e['address']<0x8000
 e['day31_outcome_producer']=e['kind']=='write_attempt'and e['address']==0x514 and e['physical_bank']==9 and e['opcode_PC']==0xCF02
 e['main_E066_first_signature']=e['kind']=='opcode_boundary'and e['physical_bank']==31 and e['opcode_PC']==0xE066
 e['day31_controller_boundary']=e['kind']=='opcode_boundary'and e['physical_bank']==9 and e['opcode_PC']in(0xCD78,0xCD7D,0xCD80,0xCD84,0xCD89,0xCEAB,0xCF00,0xCF02,0xCF05,0xCF92)
 e['commander_outcome_producer']=e['kind']=='write_attempt'and e['address']==0x514 and e['physical_bank']==13 and e['opcode_PC']in(0xDD82,0xDD9E)
 if e['kind']=='write_attempt'and e['address']<0x2000:
  p=e['address']&2047
  if p==0x50B:e['captured_RAM_byte_after_write']=b[3]
  elif 0x540<=p<0x548:e['captured_RAM_byte_after_write']=(c+d)[p-0x540]
 ptr=e['pointer_0000_0001'];logical=(ptr+e['Y'])&65535;dummy=(ptr&0xFF00)|((ptr+e['Y'])&255)
 e['BDB8_logical_store']=e['kind']=='write_attempt'and e['physical_bank']==8 and e['opcode_PC']==0xBDB8 and e['address']==logical
 e['BDB8_STA_dummy_read']=e['kind']=='read'and e['physical_bank']==8 and e['opcode_PC']==0xBDB8 and e['address']==dummy
 e['original_selected_Push8_write']=e['kind']=='write_attempt'and e['physical_bank']==8 and 0x100<=e['address']<0x200
 if e['original_selected_Push8_write']:
  assert e['address']==0x100+((e['SP']+1)&255)
  e['Push8_SP_is_after_original_decrement']=True
  e['Push8_after_value']=e['stack_above_SP_4bytes'][0]
  assert e['Push8_after_value']==e['value']
 return e

def start_observer(rt,out):
 if not hasattr(rt.core,'nestopia_wp05_enable'):return None
 core=rt.core
 for n in('enable','begin_frame'):f=getattr(core,'nestopia_wp05_'+n);f.argtypes=[C.c_uint];f.restype=None
 for n in('count','overflow','words','snapshot_count','snapshot_overflow'):getattr(core,'nestopia_wp05_'+n).restype=C.c_uint
 core.nestopia_wp05_data.restype=C.POINTER(C.c_uint32);core.nestopia_wp05_snapshot_data.restype=C.POINTER(C.c_ubyte);assert core.nestopia_wp05_words()==WORDS
 original=core.retro_run
 def run():core.nestopia_wp05_begin_frame(rt.frames+1);original()
 core.retro_run=run;core.nestopia_wp05_enable(7)
 old=json.loads((ROOT/'analysis/phase30/runtime/natural-stage1-mode0/observer/event-schema.json').read_text())
 write(out/'event-schema.json',dict(schema='wp05-natural-nonempty-passive-nonempty-disposition-ABI-v1',words=72,bytes_per_record=288,raw_layout=old['raw_layout']+['RAM0081_0084_buttons_packed4','RAM0085_0086_0504_050B_packed4','RAM0540_0543_UI_packed4','RAM0544_0547_UI_packed4'],sequence='One-based globally contiguous in each fresh process; begin_frame only clears buffered records.',cycle='Actual original cycles.count including original per-frame rebasing.',opcode_PC=old['opcode_PC'],before_after='Word44 is const physical backing before the original write; word17 is WRAM backing after it. Packed RAM domains capture the current backing at the event boundary. Unlike the old68-word ABI, new words68/69 also capture buttons0081..0086, side0504 and raw050B; words70/71 capture raw0540..0547. No transient hardware state is inferred.',scope='Narrow physical8 early/commit boundaries, physical13 human13/14 entries/actual transfer bodies, physical9 actual day31 CD78/CEAB/CF02 outcome path (and retained ordinary Start+A boundaries), selected fixed mapper/far/87 transitions; full150auxiliary bus domain and all7 ruler-controller writes independent of selected PC.',snapshot=dict(bytes=10240,layout='2K RAM followed by8K WRAM',method='Const physical backing copy; no device/bus API',scope='First public human phase/body per process, actual early allocation/BD96/BDB8 entries, day31 CD78/CEAB/CF02, and E066 once per first (global,NMI,battle-main,battle-phase) signature. Up to1024 signatures, explicit overflow. No claim all instructions or all callbacks.',instantaneous_N163_PPU_APU_captured=False),overflow='Hard fail; no discarded accepted evidence.'))
 return dict(raw=(out/'bus-events.bin').open('wb'),decoded=(out/'events.jsonl').open('w'),snap=(out/'snapshots.bin').open('wb'),index=(out/'snapshot-index.jsonl').open('w'),count=0,snapshot_count=0,sequence=0,kinds=collections.Counter())

def drain(rt,obs,out,case):
 if obs is None:return
 core=rt.core;assert core.nestopia_wp05_overflow()==core.nestopia_wp05_snapshot_overflow()==0
 n=core.nestopia_wp05_count();raw=C.string_at(core.nestopia_wp05_data(),n*RECORD_BYTES);obs['raw'].write(raw)
 count=core.nestopia_wp05_snapshot_count();snap=C.string_at(core.nestopia_wp05_snapshot_data(),count*SNAPSHOT_BYTES);obs['snap'].write(snap);local=0
 for words in struct.iter_unpack('<72I',raw):
  e=decode_event(words,rt.frames,obs['sequence']+1);obs['sequence']=e['sequence'];obs['count']+=1;obs['kinds'][e['kind']]+=1;obs['decoded'].write(json.dumps(e,separators=(',',':'))+'\n')
  if e['full_snapshot_sequence']:
   local+=1;obs['snapshot_count']+=1;assert e['full_snapshot_sequence']==obs['snapshot_count'];payload=snap[(local-1)*SNAPSHOT_BYTES:local*SNAPSHOT_BYTES];r,s=payload[:2048],payload[2048:];assert list(r[:48])==e['ZP_0000_002F']
   prefix='callee-%04d-%04X'%(obs['snapshot_count'],e['opcode_PC']);(out/(prefix+'-ram.bin')).write_bytes(r);(out/(prefix+'-sram.bin')).write_bytes(s)
   row=dict(snapshot_sequence=obs['snapshot_count'],event_sequence=e['sequence'],frame=rt.frames,physical_bank=e['physical_bank'],entry=e['opcode_PC'],byte_offset=(obs['snapshot_count']-1)*SNAPSHOT_BYTES,bytes=SNAPSHOT_BYTES,RAM_sha256=digest(r),SRAM_sha256=digest(s),sha256=digest(payload),actual_registers=dict(a=e['A'],x=e['X'],y=e['Y'],p=e['P'],sp=e['SP'],pc=e['opcode_PC']),actual_PRG_banks=e['actual_PRG_banks'],stack_top_word_raw=e['stack_top_word_raw'],actual_battle_state=list(r[0x500:0x502]),actual_outcome=r[0x514],actual_side_0504=r[0x504],actual_mode_6F91=s[0xF91],actual_050B=r[0x50B],actual_UI_0540_0547=list(r[0x540:0x548]),actual_global_007A=r[0x7A],actual_NMI_0078=r[0x78],actual_day_0506=r[0x506],actual_working_officers_6FA1_6FB5=list(s[0xFA1:0xFB6]),actual_origin_escape_destination_052A_052C=list(r[0x52A:0x52D]),actual_city_records_6000_63BF=s[:0x3C0].hex(),actual_active_officers_0664_0677=list(r[0x664:0x678]),actual_ruler_records_6F07_6F3E=[s[0xF07+8*i:0xF0F+8*i].hex()for i in range(7)],snapshot_role='main_E066_first_signature'if e['main_E066_first_signature']else'actual_selected_preopcode_software_context',capture_core_sha256=rt.info['core_sha256'],mother=pin(mother(case)),additional_core_memory_writes=0,known_inherited_preparation_byte_writes=ancestry(case)['known_inherited_preparation_byte_writes'],instantaneous_N163_PPU_APU_captured=False,origin='Independent WP05 passive observer actual pre-opcode software context; not fixed-core internal trace.',exported_RAM=prefix+'-ram.bin',exported_SRAM=prefix+'-sram.bin')
   write(out/(prefix+'.json'),row);obs['index'].write(json.dumps(row,separators=(',',':'))+'\n')
 assert local==count

def capture(rom,core,out,case):
 c=CASES[case];m=mother(case);assert sha(rom)==ROM_SHA and sha(ORIGINAL)==CORE_SHA and sha(m)==c['mother_sha256']and sha(core)in(CORE_SHA,OBSERVER_SHA)
 out=Path(out).resolve();assert out.is_relative_to(ROOT/'analysis/wp05-natural-nonempty');out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'Refuse overwritten Native outputs';rt=ServiceRuntime(rom,out,core);obs=start_observer(rt,out);rows=[];points=[];anc=ancestry(case);steps=plan(case)
 try:
  (out/'pre-import-initial.state').write_bytes(serialized(rt));rt.load_state(m)
  (out/'initial.state').write_bytes(serialized(rt));(out/'initial-ram.bin').write_bytes(rt.memory(2));(out/'initial-sram.bin').write_bytes(rt.memory(0));initial=fields(rt.memory(2),rt.memory(0));write(out/'initial-fields.json',initial);write(out/'initial-api-state.json',dict(RGB_callback_received=rt.frame is not None,PCM_bytes=len(rt.pcm),audio_callbacks=len(rt.audio_calls),five_buffer_video_boundary='First actual video/audio callback frame; no initial RGB is fabricated before retro_run.'));assert rt.frame is None and len(rt.pcm)==0
  assert all(initial[k]==v for k,v in c.get('expected_initial',{}).items())
  def observe(runtime):
   r,s=rt.memory(2),rt.memory(0);state=serialized(rt);ctx=NestopiaContext.parse(state);pcm=rt.pcm_frame();drain(rt,obs,out,case);label='frame-%05d'%rt.frames
   row=dict(frame=rt.frames,parent_route_frame=c['parent_frame']+rt.frames,**{key:digest(raw)for key,raw in zip(FIVE,(r,s,rt.frame.tobytes(),pcm,state))},whole_serialized_state_bytes=len(state),PCM_bytes=len(pcm),PCM_stop_byte=len(rt.pcm),actual_saved_CPU_registers=ctx.registers,actual_saved_PRG_banks=list(ctx.prg_banks),**fields(r,s));rows.append(row)
   for name,raw in((label+'.state',state),(label+'-ram.bin',r),(label+'-sram.bin',s)):(out/name).write_bytes(raw)
   rt.frame.save(out/(label+'.png'));points.append(dict(label=label,frame=rt.frames,image=label+'.png',state=label+'.state',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',fields={k:v for k,v in row.items()if not k.endswith('sha256')}))
  for step in steps:rt.run(step['frames'],tuple(step['buttons']),observe)
  if c.get('expected_first'):assert rows[0]['battle_0500_0501']==c['expected_first']
  wav=rt.save_wav(out/'full-audio.wav');wav['path']='full-audio.wav';write(out/'frame-services.json',rows);write(out/'checkpoints.json',points);write(out/'input-plan.json',steps);write(out/'audio-callbacks.json',rt.audio_calls);write(out/'preparation.json',anc);write(out/'case-spec.json',c)
  events=None
  if obs:
   for n in('raw','decoded','snap','index'):obs[n].close()
   events=dict(count=obs['count'],full_RAM_SRAM_snapshots=obs['snapshot_count'],kinds=dict(obs['kinds']),overflow=0)
  artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(out.iterdir())if p.is_file()and p.stat().st_size and p.name not in('validation.json','repeat-validation.json')}
  deps=[Path(__file__),ROOT/'scripts/capture_native_postbattle_early.py',ROOT/'scripts/capture_native_postbattle_completion.py',ROOT/'scripts/capture_native_postbattle_parent.py',ROOT/'scripts/capture_native_postbattle_pointer.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'scripts/nes_runtime.py',ROOT/'source/recovered/nestopia_context.py',m,m.with_name(m.stem+'-ram.bin'),m.with_name(m.stem+'-sram.bin')]
  for k in('plan_source','ancestry_path','case_spec_source'):
   if c.get(k):deps.append(ROOT/c[k])
  for value in anc.values():
   if isinstance(value,dict)and'path'in value and'sha256'in value:deps.append(ROOT/value['path'])
  receipt=dict(schema='wp05-natural-nonempty-native-nonempty-disposition-stream-v1',status='passed',case=case,variant='observer'if obs else'original-control',ROM_sha256=ROM_SHA,core=rt.info,ancestry=anc,mother=pin(m),state_imported=True,cold_boot=False,additional_core_memory_writes=0,known_inherited_preparation_byte_writes=anc['known_inherited_preparation_byte_writes'],natural_ordinary_input_route=c['natural'],controlled_ancestry=not c['natural'],frames=rt.frames,checkpoint_count=len(points),input_step_count=len(steps),initial_fields=initial,final_fields=fields(rt.memory(2),rt.memory(0)),full_audio=wav,observer_events=events,artifact_sha256=artifacts,dependency_pins=[pin(p)for p in dict.fromkeys(deps)],full_serialized_buffers_not_normalized=True,original_core_internal_CPU_trace=False,Source_CPU_cases=0,execution_owner='Root_only',limits=['Imported original ordinary-input route, not a new cold boot. Historical PCM/state identity is not asserted.','Only independent WP05 observer supplies selected CPU events; instantaneous N163/PPU/APU not captured.','Observed modes/callers are reported from raw events, never assumed from the route name.','This natural route adds no preparation or memory writes; ancestry is the first five frozen31 segments plus the frozen32 7610-frame prefix, not the later ten-segment duel chain.'])
  write(out/'validation.json',receipt);print(json.dumps(dict(case=case,variant=receipt['variant'],frames=rt.frames,events=events)),flush=True)
 finally:rt.close()

def provenance(out):
 j=json.loads(BUILD.read_text());assert j['status']=='passed_build_identity_not_runtime'
 assert sha(OBSERVER)==j['observer']['sha256']==OBSERVER_SHA
 assert sha(UPSTREAM/'libretro/nestopia_libretro.dylib')==OBSERVER_SHA
 assert j['explicit_final_link_proven']
 assert j['ABI']['words']==WORDS and j['ABI']['bytes_per_record']==RECORD_BYTES
 assert j['include_touch_rebuild_byte_identical'] and j['runtime_equivalence_proven'] is False
 assert not(out/'core-provenance').exists()
 shutil.copytree(BUILD.parent,out/'core-provenance')

def observations(folder):
 result=dict(schema='wp05-natural-nonempty-observed-nonempty-disposition-v1',event_count=0,full_software_snapshots=0,human_entries=[],software_inputs=[],actual_BC46_calls=[],mode_targets=[],actual_early_JSR_boundaries=[],outcome_0514_original_writes=[],commander_outcome_producer_writes=[],day31_outcome_producer_writes=[],day31_boundaries=[],main_E066_software_entries=[],title_Start_bypass=[],ruler_controller_writes=[],postbattle_SRAM_writes=[],auxiliary_bus_events=[],controller_byte_reads=[],Source_CPU_cases=0,limits=['Saved0514may be inherited scratch; commander_outcome_producer_writes classifies physical13 DD82/DD9E; day31_outcome_producer_writes separately classifies physical9 CF02 STA0514, including same-value writes. Other raw0514 writers remain separately listed.','A physical8 BB36/BC46 mode2 observation must remain separate from Source controlled cases.','Human entry samples retain first pc/main/phase occurrence; complete raw stream and perkey counts are separate.','Selected data here is a display/context projection; complete original events are never truncated.','JSR+3 is only a derived expected return PC until an actual BB39/BB8F opcode event with the original caller SP is observed.'])
 previous=None;human_counts=collections.Counter();kinds=collections.Counter();pending_calls=[]
 with(folder/'events.jsonl').open()as stream:
  for line in stream:
   e=json.loads(line);result['event_count']+=1;kinds[e['kind']]+=1
   if e['full_snapshot_sequence']:result['full_software_snapshots']+=1;result['software_inputs'].append(e)
   if e['human_disposition_entry']:
    key=(e['opcode_PC'],*e['RAM0500_0503'][:2]);human_counts[key]+=1
    if human_counts[key]==1:result['human_entries'].append(e)
   if e['early_controller_byte_read']:result['controller_byte_reads'].append(e)
   if e['title_Start_bypass']:result['title_Start_bypass'].append(e)
   if e['ruler_controller_write']:result['ruler_controller_writes'].append(e)
   if e['postbattle_allocation_commit']:result['postbattle_SRAM_writes'].append(e)
   if e['target_type']=='city_auxiliary_bus':result['auxiliary_bus_events'].append(e)
   if e['kind']=='write_attempt'and e['address']<0x2000 and(e['address']&2047)==0x514:result['outcome_0514_original_writes'].append(e)
   if e['commander_outcome_producer']:result['commander_outcome_producer_writes'].append(e)
   if e['day31_outcome_producer']:result['day31_outcome_producer_writes'].append(e)
   if e['day31_controller_boundary']:result['day31_boundaries'].append(e)
   if e['main_E066_first_signature']:result['main_E066_software_entries'].append(e)
   if e['kind']=='opcode_boundary':
    if e['physical_bank']==8:
     if e['opcode_PC']in(0xBC52,0xBD59,0xBD67):result['mode_targets'].append(e)
     if e['opcode_PC']in(0xBB36,0xBB8C):result['actual_early_JSR_boundaries'].append(e)
     if e['opcode_PC']==0xBC46:
      known=previous is not None and previous['physical_bank']==8 and previous['opcode_PC']in(0xBB36,0xBB8C)
      row=dict(entry=e,mode=e['postbattle_mode_6F91'],actual_previous_watched_opcode=previous,actual_transfer_PC=previous['opcode_PC']if known else None,transfer_not_inferred_from_return_stack=True)
      if known:
       assert previous['SP']==e['SP']+2 and e['stack_top_word_raw']&65535==previous['opcode_PC']+2
       row['derived_expected_return_PC']=previous['opcode_PC']+3;pending_calls.append(row)
      result['actual_BC46_calls'].append(row)
     if e['opcode_PC']in(0xBB39,0xBB8F):
      matches=[c for c in pending_calls if c['derived_expected_return_PC']==e['opcode_PC']and c['actual_previous_watched_opcode']['SP']==e['SP']]
      if matches:
       row=matches[-1];row['observed_return_boundary']=e;row['real_return_PC']=e['opcode_PC'];row['return_PC_and_SP_observed']=True;pending_calls.remove(row)
    previous=e
 result['raw_kind_counts']=dict(kinds);result['human_entry_counts']=[dict(opcode_PC=k[0],main=k[1],phase=k[2],count=v)for k,v in sorted(human_counts.items())]
 return result

def aggregate(out,rom_path):
 repeat=out.parent/(out.name+'-repeat');routes=[];checks=[];PNGs=WAVs=0;ROM=Path(rom_path).read_bytes();assert digest(ROM)==ROM_SHA
 for first in sorted(out.glob('*/original-control')):
  case=first.parent.name
  if not(first/'validation.json').exists():continue
  config=json.loads((first/'case-spec.json').read_text());original_rows=None
  for variant in('original-control','observer'):
   a=out/case/variant;b=repeat/case/variant;v=json.loads((a/'validation.json').read_text());v2=json.loads((b/'validation.json').read_text());assert v==v2 and v['status']=='passed'
   for name,p in v['artifact_sha256'].items():
    assert compare_files_exact(a/name,b/name)==p;checks.append(dict(case=case,variant=variant,first=rel(a/name),repeat=rel(b/name),**p));PNGs+=name.endswith('.png');WAVs+=name.endswith('.wav')
   rows=json.loads((a/'frame-services.json').read_text());assert len(rows)==config['frames']
   if original_rows is None:original_rows=rows
   assert rows==original_rows
   for name in('pre-import-initial.state','initial.state','initial-ram.bin','initial-sram.bin','input-plan.json','full-audio.wav','initial-api-state.json'):compare_files_exact(a/name,out/case/'original-control'/name)
   callbacks=json.loads((a/'audio-callbacks.json').read_text());assert len(callbacks)==len(rows)
   with wave.open(str(a/'full-audio.wav'))as w:
    assert(w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,2,2);whole=hashlib.sha256()
    for row,cb in zip(rows,callbacks):
     pcm=w.readframes(cb['stereo_sample_frames']);whole.update(pcm);assert len(pcm)==row['PCM_bytes']and digest(pcm)==row['PCM_sha256']==cb['pcm_sha256']and w.tell()*4==row['PCM_stop_byte'];label='frame-%05d'%row['frame']
     r=(a/(label+'-ram.bin')).read_bytes();s=(a/(label+'-sram.bin')).read_bytes();state=(a/(label+'.state')).read_bytes();ctx=NestopiaContext.parse(state)
     assert(ctx.ram,ctx.sram,ctx.registers,list(ctx.prg_banks))==(r,s,row['actual_saved_CPU_registers'],row['actual_saved_PRG_banks'])and digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']and digest(state)==row['whole_serialized_state_sha256']and all(row[k]==x for k,x in fields(r,s).items())
     for name in(label+'.state',label+'-ram.bin',label+'-sram.bin',label+'.png'):compare_files_exact(a/name,out/case/'original-control'/name)
     with Image.open(a/(label+'.png'))as image:image.load();assert image.size==(256,240)and image.mode=='RGB'and digest(image.tobytes())==row['RGB_sha256']
    assert not w.readframes(1)and whole.hexdigest()==v['full_audio']['PCM_sha256']and w.tell()*4==v['full_audio']['PCM_bytes']
   write(a/'repeat-validation.json',dict(status='passed',first=rel(a),second=rel(b),artifact_checks=len(v['artifact_sha256']),all_bytes_exact=True,script_sha256=sha(__file__)))
   deduplicate_streams(a,b,out.parent,'fresh_repeat_after_complete_byte_comparison')
  folder=out/case/'observer';ob=observations(folder);record_count=0
  with(folder/'bus-events.bin').open('rb')as raw,(folder/'events.jsonl').open()as decoded:
   for i,line in enumerate(decoded,1):
    block=raw.read(RECORD_BYTES);assert len(block)==RECORD_BYTES;event=json.loads(line);assert decode_event(block,sequence=i)==event
    if event['data_ROM_offset']is not None:assert ROM[event['data_ROM_offset']]==event['value']
    record_count=i
   assert not raw.read(1)and record_count==ob['event_count']
  write(out/case/'observations.json',ob)
  routes.append(dict(case=case,frames=config['frames'],case_spec=case+'/original-control/case-spec.json',natural_ordinary_input_route=config['natural'],controlled_ancestry=not config['natural'],ancestry=json.loads((out/case/'original-control/preparation.json').read_text()),original=case+'/original-control/validation.json',observer=case+'/observer/validation.json',observations=case+'/observations.json',observer_events=ob['event_count'],software_snapshots=ob['full_software_snapshots'],BC46_modes=dict(collections.Counter(str(c['mode'])for c in ob['actual_BC46_calls'])),BB36_calls=sum(e['opcode_PC']==0xBB36 for e in ob['actual_early_JSR_boundaries']),outcome0514_writes=len(ob['outcome_0514_original_writes']),day31_outcome_producer_writes=len(ob['day31_outcome_producer_writes']),main_E066_software_entries=len(ob['main_E066_software_entries'])))
 files={};inodes={}
 for x in checks:
  for key in('first','repeat'):
   path=ROOT/x[key];st=path.stat();files[x[key]]=st.st_size;inodes[(st.st_dev,st.st_ino)]=st.st_size
 storage=dict(schema='wp05-natural-nonempty-byte-exact-hardlink-storage-v1',status='passed',captured_file_paths=len(files),logical_path_bytes=sum(files.values()),unique_inode_count=len(inodes),unique_inode_logical_bytes=sum(inodes.values()),logical_duplicate_bytes=sum(files.values())-sum(inodes.values()),all_paths_preserved=True,serialized_buffers_normalized=False,old_phase_files_modified=False,limits='Hardlinks only deduplicate new WP05 storage after a complete byte comparison. They do not normalize or alter Native buffers; each original and observer run executed in a fresh process before linking.')
 write(out/'storage-deduplication.json',storage)
 summary=dict(routes=len(routes),natural_routes=sum(x['natural_ordinary_input_route']for x in routes),controlled_ancestry_routes=sum(x['controlled_ancestry']for x in routes),fresh_process_runs=4*len(routes),first_original_frames=sum(x['frames']for x in routes),all_control_frames=4*sum(x['frames']for x in routes),nonempty_repeat_checks=len(checks),PNG_checks=PNGs,WAV_checks=WAVs,observer_events=sum(x['observer_events']for x in routes),software_snapshots=sum(x['software_snapshots']for x in routes),additional_core_memory_writes=0,cold_boots=0,state_imports=4*len(routes),all_five_complete_buffers_equal_each_frame=True,initial_API_state_RAM_SRAM_equal=True,first_actual_callback_five_complete_buffers_equal=True,initial_pre_run_RGB_available=False,all_artifacts_repeat_exact=True,full_serialized_buffers_not_normalized=True,storage_deduplication=pin(out/'storage-deduplication.json'),Source_CPU_cases=0,failed_count=0)
 write(out/'repeat-artifact-checks.json',dict(status='passed',checks=checks));e=dict(schema='wp05-natural-nonempty-native-postbattle-nonempty-v1',status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),core_provenance=pin(out/'core-provenance/build.json'),summary=summary,routes=routes,original_core_internal_CPU_trace=False,limits=['New imported windows, not cold boots. Ancestry natural/controlled and any upstream single-run probes remain explicitly distinct.','Comparison is within each new run schedule; historical PCM/state replay identity is not asserted.','Source CPU cases and independent pointer-contract tests are not Native frames.','Instantaneous N163/PPU/APU not captured; software snapshot alone cannot supply real device state.'])
 write(out/'evidence.json',e);write(out/'validation.json',dict(schema=e['schema'],status='passed',ROM_sha256=ROM_SHA,script_sha256=sha(__file__),evidence_sha256=sha(out/'evidence.json'),**summary));print(json.dumps(summary),flush=True)

def load_case_spec(path):
 j=json.loads(Path(path).read_text());case=j.pop('case');assert case and '/'not in case and '..'not in case and j['additional_core_memory_writes']==0
 assert j['natural'] is True and j['ancestry_path'] and j['ancestry_sha256'] and j['plan_sha256'];j['case_spec_source']=rel(path);CASES[case]=j;ancestry(case);return case

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--root-execution-authorized',action='store_true');p.add_argument('--route');p.add_argument('--case-spec',type=Path);p.add_argument('--out',type=Path,default=RUN);p.add_argument('--child',type=Path);p.add_argument('--core',type=Path);p.add_argument('--smoke',type=Path);p.add_argument('--limit-frames',type=int);p.add_argument('--aggregate-only',action='store_true');a=p.parse_args();assert a.root_execution_authorized,'Only Root is authorized to execute Native flows';assert sha(a.rom)==ROM_SHA
 if a.case_spec:
  case=load_case_spec(a.case_spec);assert not a.route or a.route==case;a.route=case
 if a.aggregate_only:aggregate(a.out.resolve(),a.rom);return
 assert a.route in CASES
 if a.limit_frames:
  c=dict(CASES[a.route]);c['frames']=a.limit_frames
  if c.get('plan_source'):c['plan_end']=c['plan_start']+a.limit_frames
  elif c.get('direct_plan'):raise ValueError('Provide a bounded smoke case-spec for multi-input plans')
  CASES[a.route]=c
 if a.child or a.smoke:capture(a.rom,a.core or ORIGINAL,a.child or a.smoke,a.route);return
 out=a.out.resolve();assert out.is_relative_to(ROOT/'analysis/wp05-natural-nonempty');repeat=out.parent/(out.name+'-repeat');assert not(out/a.route).exists()and not(repeat/a.route).exists(),'Refuse overwrite of a completed route';out.mkdir(parents=True,exist_ok=True)
 if not(out/'core-provenance/build.json').exists():provenance(out)
 else:
  old=json.loads((out/'core-provenance/build.json').read_text());assert old['observer']['sha256']==sha(OBSERVER)==OBSERVER_SHA
 for target in(out,repeat):
  for variant,core in(('original-control',ORIGINAL),('observer',OBSERVER)):
   cmd=[sys.executable,str(Path(__file__).resolve()),str(a.rom.resolve()),'--root-execution-authorized','--child',str(target/a.route/variant),'--route',a.route,'--core',str(core)]
   if a.case_spec:cmd+=['--case-spec',str(a.case_spec.resolve())]
   subprocess.run(cmd,check=True)
   current=target/a.route/variant
   if target==repeat:deduplicate_streams(out/a.route/variant,current,out.parent,'fresh_repeat_after_complete_byte_comparison')
   elif variant=='observer':deduplicate_streams(target/a.route/'original-control',current,out.parent,'cross_core_identical_capture_files_after_complete_byte_comparison')
 aggregate(out,a.rom)
if __name__=='__main__':main()
