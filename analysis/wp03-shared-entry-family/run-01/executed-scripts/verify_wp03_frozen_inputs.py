#!/usr/bin/env python3
"""Root hash-only preservation of all pre-WP03 project work."""
from pathlib import Path
import argparse,hashlib,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-shared-entry-family';CACHE={}
def sha(p):
    s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if key not in CACHE:
        h=hashlib.sha256()
        with p.open('rb')as f:
            for block in iter(lambda:f.read(4194304),b''):h.update(block)
        t=p.stat();assert key==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns);CACHE[key]=h.hexdigest()
    return CACHE[key]
def read(p):return json.loads(p.read_text())
def work_files():
    paths=[]
    for folder in ('analysis','source','scripts','build','tools','.toolchain'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and not p.is_relative_to(OUT) and not (p.parent==ROOT/'scripts' and 'wp03' in p.name):paths.append(p)
    paths.extend(p for p in ROOT.iterdir()if p.is_file()and p.name!='.DS_Store')
    return sorted(set(paths))
def main(label):
    start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    anchors={'analysis/wp02-current-jsr-contract/verification.json':'5c08324983ccb93a02194350c4dc26421b3a6220eb57d8550ea162fa355681e6',
        '.toolchain/nestopia/nestopia_libretro.dylib':'924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a',
        'analysis/phase31/verification.json':'717bc872656ca43617e20888a921951fa086634672a7bbbad1ac148a445341ac',
        'analysis/closure-audit-20261018/verification.json':'fb4d10aafdeaa9eab76479bcb930377192481a4545ef5664b37926305882a987',
        'analysis/wp05-natural-nonempty/verification.json':'21feffa6e8b30a6b8d775537f19da2e3bfe1407ae78f026f37c481d8a25f4f1a',
        'analysis/wp08-shortest-continuity/verification.json':'00cc749b6ce12f0c913226baef32ecefbe109093ac21eca90393e2675974b5fb',
        'analysis/wp08-shortest-continuity/run-05/validation.json':'f1c76068998c8c800be5a5fc9f9081a474b271a61ea50cd0544c97858945efb5'}
    for name,digest in anchors.items():assert sha(ROOT/name)==digest,name
    assert sha(Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
    if label=='before':
        a=ROOT/'analysis/closure-audit-20261018';w=ROOT/'analysis/wp05-natural-nonempty';p=ROOT/'analysis/wp08-shortest-continuity'
        old=read(a/'input-hash-manifest.json');expected=dict(old['phase31_expected_maps']['artifact_and_dependency_sha256']);expected.update(old['additional_anchors'])
        expected.update({k:v['sha256']for k,v in old['phase32_residue_sha256_and_size'].items()})
        for directory,manifest in ((a,'output-hash-manifest.json'),(w,'artifact-manifest.json'),(p,'artifact-manifest.json')):
            expected.update({k:v['sha256']for k,v in read(directory/manifest)['files'].items()})
        wp02=ROOT/'analysis/wp02-current-jsr-contract'
        expected.update({k:v['sha256']for k,v in read(wp02/'artifact-manifest.json')['files'].items()})
        for row in read(wp02/'input-manifest.json')['scripts']:expected[row['path']]=row['sha256']
        wi=read(w/'input-manifest.json')
        for row in wi['scripts']+wi['source_files']+[wi['active_core'],wi['active_last_build']]:expected[row['path']]=row['sha256']
        for row in read(p/'input-manifest.json')['created_code_files']:expected[row['path']]=row['sha256']
        for name,digest in expected.items():
            q=Path(name)if Path(name).is_absolute()else ROOT/name;assert sha(q)==digest,name
        files={str(q.relative_to(ROOT)):dict(sha256=sha(q),bytes=q.stat().st_size)for q in work_files()}
        target=OUT/'frozen-work-inputs.json';assert not target.exists();target.write_text(json.dumps(dict(files=files,known_expected_paths=len(expected),anchors=anchors),ensure_ascii=False,indent=2)+'\n')
    else:
        original=read(OUT/'frozen-work-inputs.json');files=original['files']
        assert {str(p.relative_to(ROOT))for p in work_files()}==set(files)
        for name,row in files.items():
            q=ROOT/name;assert q.stat().st_size==row['bytes']and sha(q)==row['sha256'],name
    target=OUT/f'frozen-{label}.json';assert not target.exists()
    result=dict(status='passed',label=label,old_work_paths=len(files),missing_or_changed=[],
        full_work_manifest_sha256=sha(OUT/'frozen-work-inputs.json'),anchors=anchors,
        excluded_runtime_environment='.venv-trace, .DS_Store; runtime identity recorded separately',
        excluded_new_work='analysis/wp03-shared-entry-family and scripts/*wp03*',
        Source_CPU_Native_executions=0,seconds=round(time.monotonic()-start,3))
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label',choices=('before','after'));main(p.parse_args().label)
