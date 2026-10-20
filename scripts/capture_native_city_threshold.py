#!/usr/bin/env python3
"""Short original-Nestopia observations of the dedicated city+1 consumer.

The baseline imports an unchanged natural mother. Other cases are explicitly
diagnostic numerical counterfactuals, not names/normal reachability proofs.
No officer, RNG, controller, request/result/readiness or PC is prepared.
"""
from pathlib import Path
import argparse, collections, ctypes as C, json, subprocess, sys, wave
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from capture_native_wild_recruitment import Capture as PreviousCapture,fields as previous_fields,VARIANTS,BUFFER_KEYS
from capture_boot_cooperation_flows import Capture as BootCapture,ROM_SHA,CORE_SHA,write,sha,digest,relative
from capture_city_auxiliary_watchpoints import decode_event
from source.recovered.nestopia_context import NestopiaContext

MOTHER=ROOT/'analysis/phase22/runtime/original-control/officer5-status2-frame14837.state'
CASES={
 'natural-money8888-aux0':None,
 'diagnostic-money257-aux0':(257,0),
 'diagnostic-money258-aux0':(258,0),
 'diagnostic-money512-aux0':(512,0),
 'diagnostic-money257-aux43':(257,43),
 'diagnostic-money257-aux44':(257,44),
}
AUX=(1,28,29,30,31)
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json',
 'state-transitions.json','flow-events.json','preparation.json','observation-summary.json','buffer-hashes.json','resource-events.json','auxiliary-events.json','consumer-observations.json')
EXPECTED={
 'natural-money8888-aux0':(8,8850,1000,7799,18,True),
 'diagnostic-money257-aux0':(7,218,700,8099,20,False),
 'diagnostic-money258-aux0':(8,220,1000,7799,18,True),
 'diagnostic-money512-aux0':(7,473,700,8099,20,False),
 'diagnostic-money257-aux43':(7,218,700,8099,20,False),
 'diagnostic-money257-aux44':(8,219,1000,7799,18,True),
}

def fields(ram,sram):
 f=previous_fields(ram,sram)
 f.update(all30_city_auxiliary_bytes=[[sram[32*c+off]for off in AUX]for c in range(30)],
  all30_city_word_plus1_plus2=[int.from_bytes(sram[32*c+1:32*c+3],'little')for c in range(30)],
  all30_city_gold=[int.from_bytes(sram[32*c+2:32*c+4],'little')for c in range(30)],
  all30_city_reserve=[int.from_bytes(sram[32*c+12:32*c+14],'little')for c in range(30)],
  domestic_city_0036=ram[0x36],domestic_selected_officer_0038=ram[0x38],domestic_selected_city_0039=ram[0x39],
  pointer20_21_raw=ram[0x20]|ram[0x21]<<8,
  numeric_officer5=dict(health=sram[0x3FC],loyalty=sram[0x3FF],status=sram[0x407]&3,
      raw12=sram[0x3FC:0x408].hex(),troops_raw16=int.from_bytes(sram[0x404:0x406],'little')))
 return f

class Capture(PreviousCapture):
 def __init__(self,rom,out,core,case):
  self.case=case;self.resources=[];self.auxiliary_events=[];self.threshold_previous=None
  super().__init__(rom,out,core)
  if self.observer is not None:
   schema=json.loads((self.out/'event-schema.json').read_text())
   schema.update(schema='phase23-passive-city-threshold-events-v1',
    original_reference_case='analysis/phase23/runtime/'+case+'/original-control',
    original_reference_frames='analysis/phase23/runtime/'+case+'/original-control/frame-services.json',
    frame_identity='Local frame N after the same pinned mother import and declared diagnostic preparation; compare with this case original-control, never a historical frame number.')
   write(self.out/'event-schema.json',schema)
 def current(self):return fields(self.rt.memory(2),self.rt.memory(0))
 def observe(self,rt):
  super().observe(rt);f=self.current()
  for key in ('all30_city_auxiliary_bytes','all30_city_word_plus1_plus2','all30_city_gold','all30_city_reserve',
              'domestic_city_0036','domestic_selected_officer_0038','domestic_selected_city_0039','pointer20_21_raw','numeric_officer5'):
   self.rows[-1][key]=f[key]
  old=self.threshold_previous
  if old is not None:
   if old['all30_city_auxiliary_bytes']!=f['all30_city_auxiliary_bytes']:
    self.auxiliary_events.append(dict(frame=rt.frames,before=old['all30_city_auxiliary_bytes'],after=f['all30_city_auxiliary_bytes']))
   change={key:dict(before=old[key],after=f[key])for key in('all30_city_gold','all30_city_reserve','numeric_officer5')if old[key]!=f[key]}
   if change:self.resources.append(dict(frame=rt.frames,changes=change,request=f['cooperation_status_6F8B'],
       phase=f['domestic_phase_6F5B'],budget=f['domestic_budget_6F5D']))
  self.threshold_previous=f
  self.snap('actual-frame-%03d'%rt.frames,'Actual newly rendered original-core frame; no inferred notification')
 def prepare(self):
  config=CASES[self.case]
  if config is None:return
  gold,aux=config;self.preparation_begin('diagnostic-city2-numerical-counterfactual')
  for address,value in((0x6042,gold&255),(0x6043,gold>>8),(0x6041,aux)):
   view=(C.c_ubyte*8192).from_address(self.rt.core.retro_get_memory_data(0));old=view[address-0x6000]
   if old!=value:
    self.preparation.append(dict(frame=self.rt.frames,kind='SRAM',address=address,before=old,after=value,
      reason=('Diagnostic ordinary gold amount before original consumer; not a natural gameplay or city+1 name claim.'if address!=0x6041 else'Diagnostic raw city+1 threshold counterfactual only; official meaning remains unconfirmed.')))
    view[address-0x6000]=value
  # Parent only saves the already-declared before/after images; no new write.
  self.preparation_end()
 def run_flow(self):
  self.inherit(MOTHER);assert self.current()['cooperation_status_6F8B']==0 and self.current()['ruler_6F03']==4
  self.prepare();self.prepared_initial_fields=self.current();self.threshold_previous=self.current()
  (self.out/'prepared-initial.state').write_bytes(self.serialized())
  start=self.rt.frames
  while self.current()['cooperation_status_6F8B']!=255:
   assert self.rt.frames-start<120,'Bounded original request did not return'
   self.step(1,(),'Ordinary no-button original main/NMI/IRQ; never inject request/ready/strategy')
  assert self.current()['ruler_6F03']==4
  self.snap('actual-request-FF-settled','Actual original request FF; later city/ruler work is outside this short window')
 def finish(self,formal=False):
  self.snap('final');BootCapture.finish(self,exploratory=False);(self.out/'full-flow.wav').rename(self.out/'full-audio.wav')
  write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
  write(self.out/'resource-events.json',self.resources);write(self.out/'auxiliary-events.json',self.auxiliary_events)
  write(self.out/'buffer-hashes.json',[dict(frame=r['frame'],**{k:r[k]for k in BUFFER_KEYS},
   whole_serialized_state_bytes=r['whole_serialized_state_bytes'])for r in self.rows])
  summary=dict(status='observed',case=self.case,frames=self.rt.frames,preparation=self.preparation,
   initial_fields=self.prepared_initial_fields,final_fields=self.current(),resource_events=self.resources,
   original_auxiliary_frame_changes=self.auxiliary_events,full_audio=self.wav,
   scope='Short imported original-Nestopia request window; no official field name or unused inference.')
  write(self.out/('observation-summary.json'if formal else'exploration-summary.json'),summary)
  return summary

def capture(rom,out,case,variant,formal=False):
 c=Capture(rom,out,VARIANTS[variant],case)
 try:
  c.run_flow();summary=c.finish(formal)
  if c.observer is not None:c.observer['binary'].flush();c.observer['JSON'].flush()
  observations=[]
  if c.observer is not None:
   for line in(c.out/'events.jsonl').read_text().splitlines():
    e=json.loads(line)
    if e['physical_bank']==10 and e['opcode_PC']==0xBD97 and e['target_type']=='city_auxiliary':observations.append(e)
  summary['dedicated_consumer_events']=observations
  annotations=[]
  for e in observations:
   assert e['kind']=='read' and e['address']==0x6041 and e['Y']==1
   before=c.prepared_initial_fields if e['frame']==1 else c.rows[e['frame']-2]
   after=c.rows[e['frame']-1]
   annotations.append(dict(raw_event=e,
    frame_start_city2_raw32=before['all30_city_records_raw32'][2],frame_end_city2_raw32=after['all30_city_records_raw32'][2],
    frame_start_gold=before['all30_city_gold'][2],frame_end_gold=after['all30_city_gold'][2],
    frame_start_overlapping_word=before['all30_city_word_plus1_plus2'][2],frame_end_overlapping_word=after['all30_city_word_plus1_plus2'][2],
    scope='The bus event captures the actual +1 byte only. Gold/+2 are actual whole-SRAM frame envelopes, not a claimed opcode-instant field captured by this ABI. Independent actual-context CPU evidence is separate.'))
  write(c.out/'consumer-observations.json',annotations)
  write(c.out/('observation-summary.json'if formal else'exploration-summary.json'),summary)
  if formal:
   n,gold,troops,reserve,budget,accepted=EXPECTED[case];f=c.current();initial=c.prepared_initial_fields
   assert c.rt.frames==n and f['cooperation_status_6F8B']==255 and f['ruler_6F03']==4
   assert(f['all30_city_gold'][2],f['numeric_officer5']['troops_raw16'],f['all30_city_reserve'][2],f['domestic_budget_6F5D'])==(gold,troops,reserve,budget)
   assert not c.auxiliary_events and not c.wild_events
   assert len(c.preparation)==(0 if CASES[case] is None else 2 if CASES[case][1]==0 else 3)
   assert all(x['address']in(0x6041,0x6042,0x6043)and x['kind']=='SRAM'for x in c.preparation)
   if c.observer is not None:
    assert len(observations)==(2 if accepted else 1) and observations[0]['frame']==4
    assert observations[0]['value']==initial['all30_city_auxiliary_bytes'][2][0]
   for row in c.rows[:4]:assert row['all30_city_gold'][2]==initial['all30_city_gold'][2]
   first=c.rows[4]if accepted else c.rows[3]
   if accepted:assert first['all30_city_gold'][2]==initial['all30_city_gold'][2]and first['domestic_budget_6F5D']==28
   groups=[]
   for group in c.preparation_groups:
    q=dict(group)
    for key in('before','after'):q[key]={k:dict(path=name,bytes=(c.out/name).stat().st_size,sha256=sha(c.out/name))for k,name in group[key].items()}
    groups.append(q)
   artifacts={};empty=[]
   for path in sorted(c.out.iterdir()):
    if not path.stat().st_size:empty.append(path.name);continue
    if path.suffix in('.png','.bin','.state','.wav','.jsonl')or path.name in FORMAL or path.name=='event-schema.json':
     artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
   dependencies=[Path(__file__),ROOT/'scripts/capture_native_wild_recruitment.py',ROOT/'scripts/capture_city_auxiliary_watchpoints.py',
    ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/capture_campaign_flows.py',ROOT/'scripts/capture_succession_flows.py',
    ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',
    MOTHER,MOTHER.with_name(MOTHER.stem+'-ram.bin'),MOTHER.with_name(MOTHER.stem+'-sram.bin'),
    ROOT/'analysis/phase22/runtime/original-control/validation.json',ROOT/'analysis/phase22/runtime/validation.json',ROOT/'analysis/phase21/runtime/core-provenance/build.json']
   validation=dict(schema='phase23-native-city-threshold-v1',status='passed',case=case,variant=variant,
    ROM_sha256=ROM_SHA,rom_modified=False,core=c.rt.info,AV=c.rt.av_info,cold_boot=False,state_imported=True,
    mother_state=relative(MOTHER),mother_sha256=sha(MOTHER),
    inherited_context=dict(natural_ordinary_buttons=True,inherited_preparation_byte_writes=0,
     parent_case='analysis/phase22/runtime/original-control/validation.json',
     scope='Phase22 original-core officer5 real recruitment checkpoint; its zero-preparation route imported phase14 natural city. Neither historical route is replayed or copied here.'),
    natural_gameplay=CASES[case] is None,controlled_diagnostic=CASES[case] is not None,
    official_city_plus1_name=None,preparation=c.preparation,preparation_groups=groups,
    additional_core_memory_writes=len(c.preparation),additional_core_memory_writes_after_declared_preparation=0,
    status_location_roster_troops_RNG_PC_request_result_ready_prepared=False,
    initial_fields=initial,final_fields=f,frames=n,checkpoint_count=len(c.points),input_step_count=len(c.plan),
    full_audio=c.wav,all_five_complete_buffers_hashed_each_frame=True,
    full_serialized_buffers_not_normalized=True,fresh_process_per_run=True,
    Native_internal_CPU_trace=False,observer_core_sparse_CPU_events=c.observer is not None,source_CPU_comparisons=0,
    verified_effects=dict(initial_true_gold=initial['all30_city_gold'][2],initial_aux1=initial['all30_city_auxiliary_bytes'][2][0],
     initial_overlapping_word=initial['all30_city_word_plus1_plus2'][2],initial_reserve=8099,initial_officer5_troops=700,
     first_BD97_local_frame=4,gate_acceptance_effect_observed=accepted,
     first_reinforcement_effect_frame=5 if accepted else None,reinforcement_true_gold_unchanged=accepted,
     reinforcement_reserve_delta=-300 if accepted else 0,reinforcement_budget_delta=-2 if accepted else 0,
     final_gold=gold,final_reserve=reserve,final_officer5_troops=troops,final_budget=budget,
     original_request_FF=True,original_city_auxiliary_writes_observed=0,
     source_and_native_scope='Current branch effects are Native observations. The overlapping-word comparison is attributed using ROM/static and independent CPU evidence, not an invented bus +2 capture.'),
    observer_events=None if c.observer is None else dict(count=c.observer['count'],raw='bus-events.bin',decoded='events.jsonl',schema='event-schema.json',overflow=0),
    artifact_sha256=artifacts,excluded_empty_VRAM=empty,excluded_snapshot_metadata_JSON=sorted(x+'.json'for x in c.labels),formal_JSON=list(FORMAL),
    dependency_pins=[dict(path=relative(p),sha256=sha(p))for p in dependencies],
    limits=['One natural and five explicitly prepared diagnostic configurations from the same natural snapshot; none starts cold.',
     'Gold and raw auxiliary writes are diagnostics, not evidence of a natural +1 writer or official name.',
     'The unchanged passive core captures actual BD97 +1 bus reads. Unhooked +2/gold values remain labeled frame envelopes.',
     'Only the complete original request0→FF window is included; it is not a monthly cycle or the old complete phase22 route.',
     'The original core has saved register snapshots and frame buffers, not an internal instruction trace.'])
   write(c.out/'validation.json',validation)
  print(json.dumps(dict(case=case,variant=variant,frames=c.rt.frames,writes=len(c.preparation),
   initial=[summary['initial_fields']['all30_city_gold'][2],summary['initial_fields']['all30_city_word_plus1_plus2'][2],summary['initial_fields']['all30_city_reserve'][2],summary['initial_fields']['numeric_officer5']['troops_raw16']],
   final=[summary['final_fields']['all30_city_gold'][2],summary['final_fields']['all30_city_word_plus1_plus2'][2],summary['final_fields']['all30_city_reserve'][2],summary['final_fields']['numeric_officer5']['troops_raw16']],
   BD97_events=len(observations),aux_original_changes=len(c.auxiliary_events))),flush=True)
  return summary
 finally:c.close()

def aggregate(out):
 out=Path(out).resolve();second=out.parent/(out.name+'-repeat');cases=[];observers=[];logical_writes=0;frames=0;artifacts=images=audio=points=0;events_count=0
 for case in CASES:
  streams={}
  for variant in VARIANTS:
   first=out/case/variant;repeat=second/case/variant
   a=json.loads((first/'validation.json').read_text());b=json.loads((repeat/'validation.json').read_text());assert a==b and a['status']=='passed'
   for pin in a['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
   for name,pin in a['artifact_sha256'].items():
    p,q=first/name,repeat/name
    assert p.stat().st_size==q.stat().st_size==pin['bytes']>0 and sha(p)==sha(q)==pin['sha256'];artifacts+=1
    if p.suffix=='.png':
     with Image.open(p)as im:im.load();assert im.size==(256,240)and im.mode=='RGB'
     images+=1
    elif p.suffix=='.wav':
     with wave.open(str(p))as w:
      assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000)
      assert digest(w.readframes(w.getnframes()))==a['full_audio']['PCM_sha256']
     audio+=1
   check=json.loads((first/'checkpoints.json').read_text())
   for point in check:
    context=NestopiaContext.parse((first/point['state']).read_bytes())
    assert context.ram==(first/point['RAM']).read_bytes()and context.sram==(first/point['SRAM']).read_bytes()
   write(first/'repeat-validation.json',dict(status='passed',case=case,variant=variant,
    first_run=relative(first),second_run=relative(repeat),all_nonempty_artifact_bytes_exact=True,
    artifact_checks=len(a['artifact_sha256']),full_serialized_buffers_not_normalized=True,validation_bytes_exact=sha(first/'validation.json')==sha(repeat/'validation.json')))
   streams[variant]=a
  one,two=out/case/'original-control',out/case/'observer'
  hashes=json.loads((one/'buffer-hashes.json').read_text());assert hashes==json.loads((two/'buffer-hashes.json').read_text())
  assert len(hashes)==EXPECTED[case][0]
  for name in('initial.state','initial-ram.bin','initial-sram.bin','prepared-initial.state','mother-input.state','full-audio.wav','input-plan.json'):
   assert sha(one/name)==sha(two/name)
  for group in streams['original-control']['preparation_groups']:
   before=(one/group['before']['SRAM']['path']).read_bytes();after=(one/group['after']['SRAM']['path']).read_bytes()
   assert[(i+0x6000,a,b)for i,(a,b)in enumerate(zip(before,after))if a!=b]==[(w['address'],w['before'],w['after'])for w in sorted(group['writes'],key=lambda x:x['address'])]
   assert(one/group['before']['RAM']['path']).read_bytes()==(one/group['after']['RAM']['path']).read_bytes()
  raw=(two/'bus-events.bin').read_bytes();decoded=[json.loads(x)for x in(two/'events.jsonl').read_text().splitlines()]
  assert len(raw)==72*len(decoded)
  for i,e in enumerate(decoded):assert decode_event(raw[i*72:(i+1)*72],sequence=i+1)==e
  assert not any(e['target_type']=='city_auxiliary'and e['kind']=='write_attempt'for e in decoded)
  events_count+=len(decoded)
  a=streams['original-control'];frames+=a['frames'];points+=a['checkpoint_count'];logical_writes+=a['additional_core_memory_writes']
  check=json.loads((one/'checkpoints.json').read_text())
  cases.append(dict(case=case,folder=case+'/original-control',frames=a['frames'],
   validation=case+'/original-control/validation.json',repeat_validation=case+'/original-control/repeat-validation.json',
   checkpoints=case+'/original-control/checkpoints.json',frame_services=case+'/original-control/frame-services.json',input_plan=case+'/original-control/input-plan.json',
   full_audio=dict(path=case+'/original-control/full-audio.wav',**a['full_audio']),images={p['label']:case+'/original-control/'+p['image']for p in check},
   preparation=a['preparation'],preparation_groups=a['preparation_groups'],verified_effects=a['verified_effects'],
   cold_boot=False,state_imported=True,natural_gameplay=a['natural_gameplay'],controlled_diagnostic=a['controlled_diagnostic']))
  observers.append(dict(case=case,folder=case+'/observer',validation=case+'/observer/validation.json',
   repeat_validation=case+'/observer/repeat-validation.json',events=case+'/observer/events.jsonl',raw_ABI=case+'/observer/bus-events.bin',
   consumer_observations=case+'/observer/consumer-observations.json',event_count=len(decoded)))
 summary=dict(status='passed',native_configurations=6,natural_configurations=1,controlled_diagnostic_configurations=5,
  original_core_first_run_frames=frames,original_core_repeated_frames=frames*2,first_run_frames_both_core_variants=frames*2,total_control_frames_all_runs=frames*4,
  core_variants=2,fresh_process_runs=24,state_imports_all_runs=24,cold_boot_runs=0,
  original_core_first_run_checkpoints=points,nonempty_artifact_checks=artifacts,decoded_PNG_checks=images,full_WAV_checks=audio,
  preparation_byte_writes_across_six_configurations=logical_writes,physical_preparation_byte_writes_all_runs=logical_writes*4,
  inherited_preparation_byte_writes=0,additional_request_result_ready_RNG_PC_writes=0,
  all_five_complete_buffers_match_each_frame=True,all_nonempty_artifacts_repeat_exact=True,
  observer_event_count=events_count,original_auxiliary_writes_observed=0,source_CPU_cases=0,failed_count=0)
 evidence=dict(schema='phase23-native-city-threshold-flows-v1',status='passed',summary=summary,native_cases=cases,observer_runs=observers,
  ROM_sha256=ROM_SHA,original_core_sha256=CORE_SHA,observer_core_sha256=sha(VARIANTS['observer']),script_sha256=sha(__file__),
  mother_state=relative(MOTHER),mother_sha256=sha(MOTHER),
  limits=['Prepared counterfactuals discriminate this consumer only; they do not establish natural city+1 semantics or a writer.',
   'Actual +1 bus values and full-frame city records are separate scopes; no +2 instantaneous read is invented.',
   'Zero observed auxiliary writes is a bounded negative observation, never an unused/padding or reserved-field proof.'])
 write(out/'evidence.json',evidence);write(out/'validation.json',dict(schema=evidence['schema'],**summary,evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(__file__)))
 (out/'README.md').write_text('''# 阶段23：城市重叠字门槛短窗口

六案共享阶段22原核心实际录用于禁后的自然母档，导入后仅7或8帧原无键输入，直到原请求0→FF。本轮不冷启动、不重跑阶段22长路线；祖先准备0。第一案新增写入0，后五案是明确诊断：只改城2金币+2/+3，最后两案另改原+1为43/44；不准备兵、武将状态、名册、PC、RNG、请求、答复或ready。

[证据](evidence.json) · [回执](validation.json) · [新脚本](../../../scripts/capture_native_city_threshold.py)

首个BD97都在局部第4帧。各组前3帧原寄存器相同，城金币保持初值。自然金8888/aux0、金258/aux0、金257/aux44三案，第5帧兵700→1000、库存8099→7799、预算30→28；该帧金币仍8888/258/257。金257/aux0、金512/aux0、金257/aux43三案保持兵700和库存8099。实际金258<300可以补，实际金512>300未补；固定金257时重叠字299/300出现不同效果。这是重叠LE16(+1,+2)比较的诊断证据，不是城市+1正式名称。

完整请求后另有发展花金：三补兵案最终金8850/220/219，三不补兵案最终金218/473/218。这些是整个请求的结算，不能说补兵统一扣300金或把最终金币当门槛输入。

冻结阶段21观察核心仅实际记录BD97读取的+1总线字节。consumer-observations另附前一帧和同帧末完整city32B、金和重叠字，清楚标作frame envelope；未hook的+2瞬时值不伪装成原core内部trace。独立CPU实际上下文的精确前序由另一份证据负责。六案没有观察到150个城市辅助字节的原写尝试，仅为所跑短路径的局部负观察，不证明unused、padding或reserved，也没有找到新自然+1写者。

每配置原核心与冻结观察核心各fresh双跑，逐帧完整RGB、PCM、2048B RAM、8192B SRAM及完整serialized API buffer精确相等；所有非空PNG/rawstate/RAM/SRAM/WAV和正式JSON双跑全文相等。完整state不截断、补零或归一化；0B VRAM和绝对路径metadata JSON独立排除。每一个原帧均保留实际PNG和完整内存/state，不制造初始尚无新帧的PNG。
''')
 print(json.dumps(summary),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--case',choices=tuple(CASES),default=next(iter(CASES)));p.add_argument('--variant',choices=tuple(VARIANTS),default='observer')
 p.add_argument('--formal-run',action='store_true');p.add_argument('--verify-replay',action='store_true');p.add_argument('--aggregate',action='store_true')
 a=p.parse_args()
 if a.aggregate:aggregate(a.out);return
 if a.verify_replay:
  for case in CASES:
   for variant in VARIANTS:
    for out in(a.out,a.out.parent/(a.out.name+'-repeat')):
     subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(out/case/variant),'--case',case,'--variant',variant,'--formal-run'],check=True)
  aggregate(a.out);return
 capture(a.rom,a.out,a.case,a.variant,a.formal_run)

if __name__=='__main__':main()
