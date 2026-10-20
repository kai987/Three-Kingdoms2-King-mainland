#!/usr/bin/env python3
"""Hash-only preservation of239563 existing paths for the bounded consumer."""
from pathlib import Path
import argparse,hashlib,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp08-real-continuation';PREV=ROOT/'analysis/wp07-palette-packet-consumer';CACHE={}
def sha(p):
 s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if key not in CACHE:
  h=hashlib.sha256()
  with p.open('rb')as f:
   for b in iter(lambda:f.read(4194304),b''):h.update(b)
  t=p.stat();assert key==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns);CACHE[key]=h.hexdigest()
 return CACHE[key]
def read(p):return json.loads(p.read_text())
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def paths():
 out=[]
 for d in('analysis','source','scripts','build','tools','.toolchain'):
  out.extend(p for p in(ROOT/d).rglob('*')if p.is_file()and not p.is_relative_to(OUT)and not(p.parent==ROOT/'scripts'and'wp08_real_continuation'in p.name))
 out.extend(p for p in ROOT.iterdir()if p.is_file()and p.name!='.DS_Store');return sorted(set(out))
def main(label):
 start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
 assert sha(PREV/'verification.json')=='0da2a9c11ac80d27be812734f6f4d7b028b0f24fe2f11763ca816fb698355015'
 assert sha(PREV/'artifact-manifest.json')=='e8a7304f0f3e095e4a78f277ae401d97a1abe0189c24bce876cd3af81e4423f1'
 assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')=='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
 assert sha(Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 if label=='before':
  expected=dict(read(PREV/'frozen-work-inputs.json')['files']);assert len(expected)==239528
  for n,row in read(PREV/'artifact-manifest.json')['files'].items():assert n not in expected;expected[n]=row
  for p in(PREV/'artifact-manifest.json',PREV/'verification.json'):
   n=str(p.relative_to(ROOT));assert n not in expected;expected[n]=dict(sha256=sha(p),bytes=p.stat().st_size)
  assert len(expected)==239558
  for row in read(PREV/'input-manifest.json')['current_producers']:
   assert row['path']not in expected;expected[row['path']]=dict(sha256=row['sha256'],bytes=row['bytes'])
  assert len(expected)==239563
  assert {str(p.relative_to(ROOT))for p in paths()}==set(expected)
  for n,row in expected.items():
   p=ROOT/n;assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],n
  save('frozen-work-inputs.json',dict(files=expected,ancestral_paths=239528,prior_package_files=30,prior_scripts=5,
   exclusions='Only analysis/wp08-real-continuation and scripts/*wp08_real_continuation*; runtime.venv-trace/root.DS_Store excluded.'))
 else:
  expected=read(OUT/'frozen-work-inputs.json')['files'];assert {str(p.relative_to(ROOT))for p in paths()}==set(expected)
  for n,row in expected.items():
   p=ROOT/n;assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],n
 result=dict(status='passed',label=label,old_work_paths=len(expected),missing_or_changed=[],ancestral_paths=239528,prior_package_files=30,prior_scripts=5,
  frozen_manifest_sha256=sha(OUT/'frozen-work-inputs.json'),Source_CPU_Native_executions=0,seconds=round(time.monotonic()-start,3))
 save(f'frozen-{label}.json',result);print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('label',choices=('before','after'));main(p.parse_args().label)
