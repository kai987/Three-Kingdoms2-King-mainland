#!/usr/bin/env python3
"""Hash-only documentation correction, preserving the superseded receipts."""
from pathlib import Path
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/wp08-shortest-continuity'
ARCHIVE=OUT/'documentation-revisions/review-01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rel(p):return str(p.relative_to(ROOT))
def record(p):return dict(path=rel(p),sha256=sha(p),bytes=p.stat().st_size)
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def main():
    assert sha(ARCHIVE/'verification.json')=='cc8b931cdad0a0c798338dca1c2b479f521e80ab7f1b1e91dcca4020525d1cc3'
    old=read(ARCHIVE/'artifact-manifest.json')
    for name,row in old['files'].items():
        path=ROOT/name
        if path==OUT/'README.md':path=ARCHIVE/'README.md'
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],name
    for name in ('input-manifest.json','artifact-manifest.json','verification.json'):
        assert (OUT/name).read_bytes()==(ARCHIVE/name).read_bytes()
    code=Path(__file__).resolve();ast.parse(code.read_text())
    assert 'PostbattleReleaseController.return_to_city' in (OUT/'README.md').read_text()
    assert '本次没有独立调用该 owner' in (OUT/'README.md').read_text()
    revision=OUT/'metadata-revision.json';assert not revision.exists()
    write(revision,dict(schema='wp08-documentation-revision-v1',revision=2,
        reason='Correct actual full-D4F0 Source owner attribution; midpoint bridge remains a separate historical interface.',
        previous_README=record(ARCHIVE/'README.md'),current_README=record(OUT/'README.md'),
        previous_verification=record(ARCHIVE/'verification.json'),
        actual_run_unchanged=record(OUT/'run-05/validation.json'),
        Source_CPU_Native_executions=0,game_source_modified=False))
    inputs=read(ARCHIVE/'input-manifest.json');inputs['documentation_revision']=2
    inputs['created_code_files'].append(record(code));inputs['metadata_revision']=record(revision)
    write(OUT/'input-manifest.json',inputs)
    files={rel(p):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))
           if p.is_file() and p not in (OUT/'artifact-manifest.json',OUT/'verification.json')}
    write(OUT/'artifact-manifest.json',dict(schema='wp08-artifact-hash-manifest-v1',documentation_revision=2,files=files,
        excluded_self_and_final_verification=['artifact-manifest.json','verification.json']))
    verification=read(ARCHIVE/'verification.json');verification['documentation_revision']=2
    verification['artifact_manifest']=record(OUT/'artifact-manifest.json')
    verification['input_manifest']=record(OUT/'input-manifest.json')
    verification['metadata_revision']=record(revision)
    verification['artifact_paths_before_self_and_final']=len(files)
    write(OUT/'verification.json',verification)
    print(json.dumps(dict(status='passed_documentation_only_refresh',artifact_pins=len(files),
        verification_sha256=sha(OUT/'verification.json'),Source_CPU_Native_executions=0)))
if __name__=='__main__':main()
