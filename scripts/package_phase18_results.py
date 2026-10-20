#!/usr/bin/env python3
"""Package final phase18 evidence with exact allowlist and source parity."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,shutil,tempfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 r=json.loads((ROOT/'analysis/phase18/verification.json').read_text());assert r['status']=='passed'and r['rebuilt_byte_identical']
 prior=ROOT/'build/三国志2超级版-逆向分析-v17.zip';assert sha(prior)==r['old_v17_preserved_sha256']
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for name,digest in r[group].items():assert sha(ROOT/name)==digest,name
 files=[ROOT/n for n in('README.md','requirements.txt','.gitignore','build/三国志2超级版.rebuilt.nes')]
 for folder in('scripts','source','analysis'):
  files.extend(p for p in(ROOT/folder).rglob('*')if p.is_file()and '__pycache__'not in p.parts and not any(n.startswith('exploratory')for n in p.parts)and p.name!='package-receipt.json')
 expected={str(p.relative_to(ROOT))for p in files};assert len(files)==len(expected)
 canonical=ROOT/'build/三国志2超级版-逆向分析.zip';version=ROOT/'build/三国志2超级版-逆向分析-v18.zip'
 assert not version.exists(),'Do not overwrite a previously frozen v18'
 with ZipFile(canonical,'w',compression=ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
 with ZipFile(canonical)as z:
  assert set(z.namelist())==expected and len(z.namelist())==len(expected)and z.testzip()is None
  for n in z.namelist():assert not set(Path(n).parts)&{'.toolchain','.venv','.venv-trace','node_modules','__pycache__'}and not Path(n).is_absolute()and '..'not in Path(n).parts
  sources=0
  for n in z.namelist():
   if n.startswith('source/'):assert z.read(n)==(ROOT/n).read_bytes();sources+=1
  for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
   for n,digest in r[group].items():
    if n.startswith('.toolchain/'):assert n not in expected;continue
    assert n in expected and hashlib.sha256(z.read(n)).hexdigest()==digest,n
  critical={n for n in expected if n.startswith('analysis/phase18/')and not n.endswith('.wav')}
  critical.update({'source/recovered/city_auxiliary_services.py','source/recovered/city_auxiliary_integration.py','build/三国志2超级版.rebuilt.nes'})
  with tempfile.TemporaryDirectory(prefix='three-kingdoms-phase18-extract-')as folder:
   for n in sorted(critical):assert sha(z.extract(n,folder))==sha(ROOT/n),n
 shutil.copy2(canonical,version);assert sha(canonical)==sha(version)
 assert sha(prior)==r['old_v17_preserved_sha256']
 receipt=dict(version=18,path=str(canonical),versioned_path=str(version),sha256=sha(canonical),archive_bytes=canonical.stat().st_size,file_count=len(expected),
  exact_allowlist_check='passed',CRC_check='passed',all_source_file_parity_checks=sources,temporary_extraction_critical_file_checks=len(critical),
  canonical_versioned_byte_parity='passed',v17_preserved_sha256=sha(prior),validator_path='scripts/package_phase18_results.py',validator_sha256=sha(Path(__file__)))
 (ROOT/'analysis/package-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
