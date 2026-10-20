#!/usr/bin/env python3
"""Read-only aggregate: preserved phase18 plus phase19's explicit contracts."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,wave
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase19'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OLD_AUDIT='ec1a0ffb23f9db5cbceaf4a86ee69957fb65bebde8ddaf6d25d103de894e1f9b'
OLD_ZIP='013cc14299fa45a796d4497a7a6c6927f548fc4fcb3883d7a459133e00e759cf'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 assert(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
 prior_path=ROOT/'analysis/phase18/verification.json';assert sha(prior_path)==OLD_AUDIT
 prior=read(prior_path);assert prior['status']=='passed';pins={};counts=Counter()
 def pin(name,digest=None):
  p=Path(name);p=p if p.is_absolute()else ROOT/p;key=str(p.relative_to(ROOT))
  assert not any(n.startswith('exploratory')for n in p.parts),key
  actual=sha(p);assert digest is None or digest==actual,(key,digest,actual)
  if key in pins:assert pins[key]==actual
  pins[key]=actual;return actual
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for name,digest in prior[group].items():pin(name,digest);counts['unchanged_phase18_dependency_pins']+=1
 pin(prior_path);assert sha(ROOT/'build/三国志2超级版-逆向分析-v18.zip')==OLD_ZIP
 regression=dict(status='passed',prior_audit_sha256=OLD_AUDIT,prior_v18_archive_sha256=OLD_ZIP,
  preserved_dependency_count=counts['unchanged_phase18_dependency_pins'],new_validation_of_old_execution=False)
 (OUT/'regression').mkdir(exist_ok=True)
 (OUT/'regression/frozen-phase18.json').write_text(json.dumps(regression,indent=2)+'\n')
 static=read(OUT/'fields-static/analysis-summary.json');assert static['status']=='analyzed'
 pointer_check=read(OUT/'fields-static/verification.json');assert pointer_check['status']=='passed'
 assert pointer_check['source_CPU_cases']==0 and pointer_check['original_factory_contract_CPU_checks']==3584
 assert pointer_check['model_guard_check_count']>=33
 for group in('source_and_validator_sha256','artifact_sha256'):
  for name,digest in pointer_check[group].items():pin(name,digest)
 counts['pointer_model_guard_checks']=pointer_check['model_guard_check_count']
 counts['original_factory_contract_CPU_checks']=pointer_check['original_factory_contract_CPU_checks']
 for filename,n in [('all-indirect-accesses.json',1526),('access-contracts.json',589),('new-indirect-accesses.json',45)]:
  access=read(OUT/'fields-static'/filename);rows=access['accesses'];assert len(rows)==n
  assert len({(r['physical_bank'],r['cpu'])for r in rows})==n
  assert Counter(r['classification']for r in rows)==access['classification_counts']
  for r in rows:
   contract=r.get('address_contract')or{}
   if r['classification']=='proved_disjoint_auxiliary_address_domain'and 'auxiliary_address_intersection_count'in contract:
    assert contract['auxiliary_address_intersection_count']==0
  for r in rows:
   if 'raw_hex'in r:
    raw=bytes.fromhex(r['raw_hex']);off=16+r['physical_bank']*8192+(r['cpu']&8191)
    assert rom[off:off+len(raw)]==raw
  counts['complete_per_access_rows']+=n
 service=read(OUT/'services/validation.json');assert service['status']=='passed'
 assert not service.get('quick',False)and service.get('failed_count',0)==0
 assert service.get('source_original_CPU_callbacks',0)==0
 assert not service.get('production_IR_interpretation',False)
 for row in service['cases']:
  assert row['all_RAM_byte_count']==2048 and row['all_SRAM_byte_count']==8192
  assert row['pure_source_CPU_callbacks']==0
 counts['new_source_CPU_cases']=len(service['cases'])
 integration=read(OUT/'source-integration.json');assert integration['status']=='passed'
 assert integration['rom_cpu_sequence_count']==2 and integration['actual_caller_RTS_count']==0
 assert integration['source_original_CPU_callbacks']==0 and not integration['source_IR_interpretation']
 for row in integration['rows']:
  assert row['preparation']==[]and row['original_CPU_prelude_instructions']>0
  assert row['main_updates']==2 and row['explicit_NMI_arrivals']==2
  assert all(e['all_RAM_SRAM_registers_IO_banks_N163_equal']for e in row['events'])
 state=read(OUT/'state-format/validation.json');assert state['status']=='passed'
 assert state['snapshot_count']>=318 and state['original_core_roundtrip_count']>=5
 assert state['all_shadow_mismatch_snapshots_roundtripped']
 assert state['core']['core_sha256']=='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
 assert state['N163_boundary_transition_checks']==1025
 assert not state['Native_instruction_trace']and state['source_guard_count']>=12
 for r in(integration,service,state):
  for name,digest in r['source_sha256'].items():pin(name,digest)
  for name,digest in r.get('artifact_sha256',{}).items():pin(name,digest)
 interleave=read(OUT/'cpu/consumer-sequences.json')
 assert interleave['status']=='passed'and interleave['rom_cpu_sequence_count']==4 and interleave['failed_count']==0
 assert interleave['source_original_CPU_callbacks']==0 and not interleave['production_IR_interpretation']
 for row in interleave['rows']:
  assert row['postentry_memory_injections']==0 and row['all_services_pure_source']
  assert row['all_RAM_byte_count']==2048 and row['all_SRAM_byte_count']==8192
  assert row['completion_kind']=='actual_caller_RTS_after_genuine_NMI2_consumer'
  assert all(e['full_scope_equal']for e in row['events'])
 for name,digest in interleave['source_sha256'].items():pin(name,digest)
 counts['new_CPU_consumer_parent_sequences']=4
 runtime=read(OUT/'runtime/validation.json');evidence=read(OUT/'runtime/evidence.json')
 assert runtime['status']==evidence['status']=='passed'
 assert runtime['evidence_sha256']==sha(OUT/'runtime/evidence.json')
 assert all(runtime[k]==v for k,v in evidence['summary'].items())
 for dep in evidence['dependency_pins']:pin(dep['path'],dep['sha256'])
 assert runtime['original_F8_observed']is False and runtime['F8_consumer_or_return_verified']is False
 for folder in sorted((OUT/'runtime').iterdir()):
  if not folder.is_dir()or not(folder/'validation.json').exists():continue
  v=read(folder/'validation.json');repeat=read(folder/'repeat-validation.json')
  assert v['status']==repeat['status']=='passed'
  assert repeat['all_hashes_equal']and repeat['whole_serialized_buffers_exact']
  assert len(repeat['artifacts'])==repeat['nonempty_artifact_checks']
  for artifact in repeat['artifacts']:
   assert artifact['equal']and artifact['bytes']>0
   for base in(folder,ROOT/repeat['second_run']):
    path=base/artifact['artifact'];assert path.stat().st_size==artifact['bytes'];pin(path,artifact['sha256'])
  counts['native_nonempty_double_artifacts']+=len(repeat['artifacts'])
  frames=read(folder/'frame-services.json');points=read(folder/'checkpoints.json')
  assert len(frames)==v['frames']and len(points)==v['checkpoint_count']
  assert all(row['frame']==i+1 for i,row in enumerate(frames))
  for point in points:
   row=frames[point['frame']-1]
   with Image.open(folder/point['image'])as img:
    assert img.size==(256,240)and hashlib.sha256(img.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   for key in('RAM','SRAM','state'):assert(folder/point[key]).stat().st_size>0
   assert sha(folder/point['RAM'])==row['RAM_sha256']and sha(folder/point['SRAM'])==row['SRAM_sha256']
   assert sha(folder/point['state'])==row['whole_serialized_state_sha256']
  with wave.open(str(folder/'full-audio.wav'),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000)
   counts['original_PCM_sample_pairs']+=w.getnframes()
  counts['native_cases']+=1;counts['native_first_run_frames']+=len(frames);counts['native_checkpoints']+=len(points)
 assert counts['native_cases']>=4
 assert counts['native_first_run_frames']==runtime['frames_first_run']
 assert counts['native_checkpoints']==runtime['checkpoint_count']
 assert counts['native_nonempty_double_artifacts']==runtime['nonempty_repeat_artifact_checks']
 assert counts['original_PCM_sample_pairs']==runtime['PCM_stereo_sample_frames_first_run']
 coverage=read(OUT/'coverage-comparison.json')
 assert coverage['old_static_positions']==739 and coverage['old_dynamic_in_static']==267
 assert coverage['old_missing_positions']==472 and coverage['newly_executed_old_missing_positions']==471
 assert coverage['remaining_old_missing_positions']==1
 browser=read(OUT/'browser-static-check.json');qa=read(OUT/'browser-validation.json')
 assert browser['status']==qa['status']=='passed'
 assert sha(OUT/'index.html')==browser['HTML_sha256']==qa['HTML_sha256']
 assert all(row['passed']for row in qa['checks'])and qa['console']==[]
 assert len(qa['sources'])==3 and len(qa['native'])==len(qa['audio'])==4
 for row in qa['sources']:assert sha(ROOT/'source/recovered'/row['file'])==row['sha256']and row['full_UTF8_equal']
 for row in qa['native']:
  assert row['frame_values_equal']and row['checkpoint_values_equal']and row['PNG_paths_SHA256_equal']
  assert all(p['complete']and p['w']==256 and p['h']==240 for p in row['imageStates'])
 assert all(row['passed']and row['WAV_SHA256_verified']for row in qa['audio'])
 shot=ROOT/qa['screenshot']['path'];assert sha(shot)==qa['screenshot']['sha256']
 assert shot.stat().st_size==qa['screenshot']['bytes']and qa['screenshot']['original_capture_bytes_preserved']
 with Image.open(shot)as img:assert img.format=='JPEG'and img.width==qa['viewport']['DOM_width']
 for name,digest in browser['dependency_pins'].items():pin(name,digest)
 # Every phase19 artifact is pinned, including all raw native frames/media and
 # upstream state-format source. Explorer directories never enter this receipt.
 for p in sorted(OUT.rglob('*')):
  if p.is_file()and '__pycache__'not in p.parts and not any(n.startswith('exploratory')for n in p.parts)and p.name!='verification.json':pin(p)
 sources={str(p.relative_to(ROOT)):sha(p)for folder in('source','scripts')for p in(ROOT/folder).rglob('*')if p.is_file()and '__pycache__'not in p.parts}
 result=dict(schema='phase19-preserved-ROM-additive-source-and-Native-audit-v1',status='passed',
  ROM_sha256=ROM_SHA,rebuilt_byte_identical=True,old_v18_preserved_sha256=OLD_ZIP,
  old_phase18_audit_sha256=OLD_AUDIT,checks=dict(counts),
  source_and_validator_sha256=sources,artifact_and_dependency_sha256=pins,
  limits=['Snapshot CPU registers are not an original-core per-instruction trace.',
   'Full pointer proofs cover their declared CFG/domain only; unknown accesses remain unknown.',
   'City+1 and +28..31 official labels remain unconfirmed; no unused/padding theorem is claimed.',
   'Original-core bounded negative observations do not prove the unobserved request branch cannot occur.'])
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='passed',checks=dict(counts),source_pins=len(sources),artifact_pins=len(pins)),ensure_ascii=False))
if __name__=='__main__':main()
