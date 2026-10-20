#!/usr/bin/env python3
"""Offline provenance wording correction; no game/CPU/Native execution."""
from pathlib import Path
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp02-current-jsr-contract';OLD=OUT/'documentation-revisions/review-01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rel(p):return str(p.relative_to(ROOT))
def record(p):return dict(path=rel(p),sha256=sha(p),bytes=p.stat().st_size)
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    assert sha(OLD/'verification.json')=='bbc9b7ca1a46ed88faf0f8734e29b1a7e658f739cc721109d6236e55682ce476'
    for name,row in read(OLD/'artifact-manifest.json')['files'].items():
        p=ROOT/name
        if p==OUT/'README.md':p=OLD/'README.md'
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],name
    for name in ('input-manifest.json','artifact-manifest.json','verification.json'):
        assert (OLD/name).read_bytes()==(OUT/name).read_bytes()
    code=Path(__file__).resolve();ast.parse(code.read_text());runtime=read(OUT/'run-01/execution-inputs.json')['runtime']
    assert sha(Path(runtime['executable']))==runtime['executable_sha256']
    for name,value in runtime['py65_python_files'].items():assert sha(Path(name))==value
    note=OUT/'documentation-revision.json';assert not note.exists()
    write(note,dict(schema='wp02-provenance-wording-revision-v1',revision=2,Source_CPU_Native_executions=0,
        previous_verification=record(OLD/'verification.json'),previous_README=record(OLD/'README.md'),current_README=record(OUT/'README.md'),
        corrections=['AC7B controlled initial X is assigned spec.index by host; nominal spec.registers.x is C3, actual segment input REG is authoritative.',
                     'Appendix references main runtime identity; no independent appendix at-run Python/py65 snapshot was captured.'],
        main_CPU_receipt_unchanged=record(OUT/'run-01/validation.json'),appendix_CPU_receipt_unchanged=record(OUT/'samevalue-appendix/run-01/validation.json'),
        current_runtime_pins_match=True,current_py65_file_count=len(runtime['py65_python_files']),
        appendix_independent_at_run_runtime_snapshot=None,current_check_is_not_retroactive_snapshot=True))
    inputs=read(OLD/'input-manifest.json');inputs['documentation_revision']=2;inputs['scripts'].append(record(code));inputs['documentation_revision_record']=record(note)
    write(OUT/'input-manifest.json',inputs)
    files={rel(p):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))
           if p.is_file()and p not in(OUT/'artifact-manifest.json',OUT/'verification.json')}
    write(OUT/'artifact-manifest.json',dict(schema='wp02-artifact-hash-manifest-v1',documentation_revision=2,files=files,excludes=['artifact-manifest.json','verification.json']))
    final=read(OLD/'verification.json');final['documentation_revision']=2
    final['input_manifest']=record(OUT/'input-manifest.json');final['artifact_manifest']=record(OUT/'artifact-manifest.json')
    final['documentation_revision_record']=record(note);final['artifact_paths_before_self_and_final']=len(files)
    write(OUT/'verification.json',final)
    print(json.dumps(dict(status='passed_documentation_refresh',artifact_pins=len(files),verification_sha256=sha(OUT/'verification.json'),CPU_executions=0)))
if __name__=='__main__':main()
