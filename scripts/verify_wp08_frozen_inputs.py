#!/usr/bin/env python3
"""Hash-only preservation check for all accepted inputs preceding WP08."""
from pathlib import Path
import argparse,hashlib,json,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp08-shortest-continuity';CACHE={}
def sha(p):
 s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if key not in CACHE:
  h=hashlib.sha256()
  with p.open('rb')as f:
   for b in iter(lambda:f.read(4194304),b''):h.update(b)
  t=p.stat();assert key==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns);CACHE[key]=h.hexdigest()
 return CACHE[key]
def read(p):return json.loads(p.read_text())
def main(label):
 start=time.monotonic();a=ROOT/'analysis/closure-audit-20261018';p=ROOT/'analysis/wp05-natural-nonempty'
 assert sha(a/'verification.json')=='fb4d10aafdeaa9eab76479bcb930377192481a4545ef5664b37926305882a987'
 assert sha(p/'verification.json')=='21feffa6e8b30a6b8d775537f19da2e3bfe1407ae78f026f37c481d8a25f4f1a'
 av=read(a/'verification.json');pv=read(p/'verification.json')
 for v in(av,pv):
  for k in('input_manifest','artifact_manifest','input_hash_manifest','output_hash_manifest'):
   if k in v:assert sha(ROOT/v[k]['path'])==v[k]['sha256']
 m=read(a/'input-hash-manifest.json');o=read(a/'output-hash-manifest.json');w=read(p/'artifact-manifest.json');i=read(p/'input-manifest.json')
 expected=dict(m['phase31_expected_maps']['artifact_and_dependency_sha256']);expected.update(m['additional_anchors'])
 expected.update({k:v['sha256']for k,v in m['phase32_residue_sha256_and_size'].items()})
 expected.update({k:v['sha256']for k,v in o['files'].items()})
 expected.update({str((a/n).relative_to(ROOT)):sha(a/n)for n in('output-hash-manifest.json','verification.json')})
 expected.update({k:v['sha256']for k,v in w['files'].items()})
 expected.update({str((p/n).relative_to(ROOT)):sha(p/n)for n in('artifact-manifest.json','verification.json')})
 for row in i['scripts']+i['source_files']+[i['active_core'],i['active_last_build']]:expected[row['path']]=row['sha256']
 actual_wp05={str(x.relative_to(ROOT))for x in p.rglob('*')if x.is_file()}
 assert actual_wp05==set(w['files'])|{str((p/n).relative_to(ROOT))for n in('artifact-manifest.json','verification.json')}
 assert len(list(a.iterdir()))==16 and len(w['files'])==7000
 for key,value in expected.items():
  file=Path(key)if Path(key).is_absolute()else ROOT/key
  assert file.is_file()and sha(file)==value,key
 target=OUT/('frozen-'+label+'.json');assert not target.exists();OUT.mkdir(parents=True,exist_ok=True)
 d=dict(schema='wp08-readonly-frozen-input-verification-v1',status='passed',label=label,unique_expected_paths=len(expected),
  old_phase31_artifact_pins=91929,old_source_script_pins=596,old32_residue_paths=2101,closure_paths=16,
  WP05_manifest_paths=7000,WP05_total_artifact_paths=len(actual_wp05),WP05_current_scripts=6,WP05_active_sources=6,WP05_core_binaries=2,
  missing_or_changed=[],expected_map_sha256=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(),
  game_Source_CPU_Native_executed=0,seconds=round(time.monotonic()-start,3))
 if label=='after':assert read(OUT/'frozen-before.json')['expected_map_sha256']==d['expected_map_sha256']
 target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps(d),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('label',choices=['before','after']);main(parser.parse_args().label)
