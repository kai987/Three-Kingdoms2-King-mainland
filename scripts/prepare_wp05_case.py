#!/usr/bin/env python3
"""Pin the exact historical branch used by WP05. No emulator execution."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp05-natural-nonempty'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def pin(p):p=Path(p);return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def write(p,j):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def main():
 registry=ROOT/'analysis/phase31/ancestry/natural-AI-mode2/ancestry.json';old=json.loads(registry.read_text())
 previous=None
 for s in old['segments'][:5]:
  assert s['additional_core_memory_writes']==0 and s['new_preparation']==[]
  for key in('initial_state','final_state','input_plan','complete_frame_hash_log','original_result'):
   ref=s[key];assert sha(ROOT/ref['path'])==ref['sha256']
  if previous:assert s['initial_state']['sha256']==previous
  previous=s['final_state']['sha256']
 prefix=ROOT/'analysis/phase32/ancestry-prefix/day30';p=json.loads((prefix/'prefix.json').read_text())
 mother=prefix/'final.state';initial=prefix/'initial.state'
 assert p['frames']==7610 and p['additional_core_memory_writes']==0 and p['state_imports']==1
 assert sha(initial)==previous==old['segments'][5]['initial_state']['sha256']
 assert sha(mother)==p['final_state_sha256']=='570e3443291672e859ecd014c73fc272d8d7f724ce5f192fa279bbc01766a175'
 parent_plan=ROOT/old['segments'][5]['input_plan']['path'];plan=json.loads(parent_plan.read_text())
 assert sha(parent_plan)==old['segments'][5]['input_plan']['sha256']
 clipped=[]
 for i,row in enumerate(plan):
  lo=max(7610,row['start_frame']);hi=min(7993,row['start_frame']+row['frames'])
  if hi>lo:clipped.append(dict(start_frame=lo-7610,frames=hi-lo,buttons=row['buttons'],parent_step=i,parent_start_frame=row['start_frame']))
 assert [(r['frames'],r['buttons'])for r in clipped]==[(172,[]),(2,['a']),(180,[]),(2,['a']),(27,[])]
 prefixseg=dict(index=6,name='frozen32-original-only-segment06-prefix',frames=7610,
  state_import_at_start=True,new_preparation=[],additional_core_memory_writes=0,
  initial_state=pin(initial),final_state=pin(mother),final_RAM=pin(prefix/'final-ram.bin'),final_SRAM=pin(prefix/'final-sram.bin'),
  input_plan=pin(parent_plan),input_plan_range=[0,7610],complete_frame_hash_log=pin(prefix/'frame-buffer-hashes.json'),
  original_result=pin(prefix/'prefix.json'),historical_comparison=pin(prefix/'historical-comparison.json'),
  fresh_repeat_claim=False,internal_CPU_trace=False)
 required={}
 def collect(obj):
  if isinstance(obj,dict):
   if 'path'in obj and 'sha256'in obj:
    assert sha(ROOT/obj['path'])==obj['sha256'];required[obj['path']]=obj
   for v in obj.values():collect(v)
  elif isinstance(obj,list):
   for v in obj:collect(v)
 collect(old['segments'][:5]);collect(prefixseg);collect(old['root_frozen_ancestor']);collect(pin(registry))
 a=dict(schema='wp05-exact-natural-branch-ancestry-v1',status='verified_content_lineage_not_fresh_repeat',
  natural_ordinary_input_route=True,controlled_ancestry=False,
  known_inherited_preparation_byte_writes=old['known_inherited_preparation_byte_writes'],
  known_inherited_preparation=old['known_inherited_preparation'],
  unknown_inherited_preparation_count=None,
  unknown_preparation_scope='No unrecorded preparation is asserted absent. Earlier frozen22 provenance is inherited within its own declared scope; no newly added numerical, PC, RNG, ready, result or roster writes.',
  earlier_ancestor_cold_boot=old['earlier_ancestor_cold_boot'],additional_preparation=[],additional_core_memory_writes=0,
  new_case_state_imported=True,new_case_cold_boot=False,segments=old['segments'][:5]+[prefixseg],
  segmented_upstream_frames=sum(s['frames']for s in old['segments'][:5])+7610,
  upstream_original_core_runs=6,upstream_fresh_repeat_claim=False,upstream_internal_CPU_trace=False,
  root_frozen_ancestor=old['root_frozen_ancestor'],mother=pin(mother),
  parent_checkpoint=dict(frame=7610,state=str(mother.relative_to(ROOT)),receipt=pin(prefix/'final.json')),
  required_input_pins=list(required.values()),excluded_later_segments=[7,8,9,10],
  excluded_later_duel_mother=old['mother'],
  limits=['This branch ends before the old segment06 conclusion. Later segments07..10 and total141636 are not ancestors of this mother.',
   'Six historical original-only runs with state imports; they are not a new coldboot, full-run fresh repeat or uninterrupted CPU trace.',
   'Only the new bounded WP05 window will receive four-fresh-process equivalence testing.'])
 assert a['segmented_upstream_frames']==88463
 ap=OUT/'ancestry.json';write(ap,a)
 c=dict(case='natural-day31-nonempty',mother=str(mother.relative_to(ROOT)),mother_sha256=sha(mother),parent_frame=7610,
  frames=383,natural=True,additional_core_memory_writes=0,ancestry_path=str(ap.relative_to(ROOT)),ancestry_sha256=sha(ap),
  plan_source=str(parent_plan.relative_to(ROOT)),plan_sha256=sha(parent_plan),plan_start=7610,plan_end=7993,
  expected_initial=dict(global_007A=4,NMI_0078=3,battle_0500_0501=[7,7],early_mode_6F91=10),
  intended_goal='Candidate only until observed: actual day31 CF02 writer, nonempty mode2, officer67 allocation to city16 and true BB39 return.')
 write(OUT/'case-spec.json',c);write(OUT/'planned-input.json',clipped)
 print(json.dumps(dict(case=c['case'],frames=c['frames'],upstream_frames=a['segmented_upstream_frames'],mother=c['mother'],known_preparation=a['known_inherited_preparation_byte_writes'])),flush=True)
if __name__=='__main__':main()
