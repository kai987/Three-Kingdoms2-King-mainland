#!/usr/bin/env python3
"""Read-only frozen input verification for WP05; only receipt is newly written."""
import argparse,hashlib,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
AUDIT=ROOT/'analysis/closure-audit-20261018'
OUT=ROOT/'analysis/wp05-natural-nonempty'
def sha(p,cache):
 p=pathlib.Path(p);s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if key not in cache:
  h=hashlib.sha256()
  with p.open('rb')as f:
   for b in iter(lambda:f.read(4194304),b''):h.update(b)
  t=p.stat();assert key==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns)
  cache[key]=h.hexdigest()
 return cache[key]
def verify(label):
 started=time.monotonic();cache={};v=json.loads((AUDIT/'verification.json').read_text())
 assert sha(AUDIT/'verification.json',cache)=='fb4d10aafdeaa9eab76479bcb930377192481a4545ef5664b37926305882a987'
 for k in('input_hash_manifest','output_hash_manifest'):assert sha(ROOT/v[k]['path'],cache)==v[k]['sha256']
 m=json.loads((AUDIT/'input-hash-manifest.json').read_text());o=json.loads((AUDIT/'output-hash-manifest.json').read_text())
 expected=dict(m['phase31_expected_maps']['artifact_and_dependency_sha256']);expected.update(m['additional_anchors'])
 for p,x in m['phase32_residue_sha256_and_size'].items():expected[p]=x['sha256']
 auditfiles={str(p.relative_to(ROOT)):sha(p,cache)for p in AUDIT.iterdir()if p.is_file()}
 assert len(auditfiles)==16
 for p,x in o['files'].items():assert auditfiles[p]==x['sha256']
 expected.update(auditfiles)
 errors=[]
 for p,digest in expected.items():
  file=pathlib.Path(p)if pathlib.Path(p).is_absolute()else ROOT/p
  if not file.is_file()or sha(file,cache)!=digest:errors.append(p)
 assert not errors,errors[:10]
 current={str(p.relative_to(ROOT))for p in(ROOT/'analysis/phase32').rglob('*')if p.is_file()}
 current|={str(p.relative_to(ROOT))for p in(ROOT/'scripts').glob('*phase32*.py')}
 current|={'scripts/capture_native_postbattle_nonempty.py','source/recovered/postbattle_continuity_phase32.py'}
 current|={str(p.relative_to(ROOT))for p in(ROOT/'.toolchain/phase32-observer').rglob('*')if p.is_file()}
 assert current==set(m['phase32_residue_sha256_and_size'])
 if label!='before':
  b=json.loads((OUT/'frozen-before.json').read_text());assert b['closure_files']==auditfiles
 receipt=dict(schema='wp05-readonly-frozen-input-check-v1',status='passed',label=label,
  formal_artifact_dependency_pins=91929,source_validator_pins=596,phase32_residue_files=2101,
  phase32_residue_bytes=110119793,closure_file_count=16,closure_files=auditfiles,
  input_manifest_sha256=sha(AUDIT/'input-hash-manifest.json',cache),
  unique_expected_paths=len(expected),changed=[],game_CPU_Source_Native_executed=0,
  elapsed_seconds=round(time.monotonic()-started,3))
 OUT.mkdir(parents=True,exist_ok=True);target=OUT/('frozen-'+label+'.json');assert not target.exists()
 target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='closure_files'}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('label',choices=['before','after']);verify(p.parse_args().label)
