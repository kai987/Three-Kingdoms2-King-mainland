#!/usr/bin/env python3
"""Create a new v20 archive only after the final read-only audit has passed.

Production/Native evidence is not regenerated. Existing v19 is rehashed before
and after; existing v20 is always an error. The canonical ZIP is replaced only
after allowlist, CRC, pinned bytes, source parity and extraction checks pass.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, os, shutil, tempfile
ROOT=Path(__file__).resolve().parents[1]
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OLD_AUDIT='2f232a65b1ecfb1322d909c38e5e813f2a3b24cf222fe189561191258eb77359'
OLD_ZIP='2f0fdf6f3755db09715d5f9149ef84ea0a39dbe6531e41361410ce92db703ba2'
ROOT_FILES=('README.md','requirements.txt','.gitignore','build/三国志2超级版.rebuilt.nes')
EXCLUDED_PARTS={'.toolchain','.venv','.venv-trace','node_modules','__pycache__','.git'}
def digest_stream(stream):
 h=hashlib.sha256()
 for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def sha(path):
 with Path(path).open('rb')as stream:return digest_stream(stream)
def permitted(path):
 relative=path.relative_to(ROOT)
 return(not any(part.startswith('exploratory')for part in relative.parts)
  and not set(relative.parts)&EXCLUDED_PARTS and relative.name!='package-receipt.json'
  and relative.name!='.DS_Store'and relative.suffix not in('.pyc','.pyo'))
def main():
 audit_path=ROOT/'analysis/phase20/verification.json';audit=json.loads(audit_path.read_text())
 assert audit['status']=='passed'and audit['rebuilt_byte_identical']and audit['ROM_sha256']==ROM_SHA
 assert audit['old_v19_preserved_sha256']==OLD_ZIP and audit['old_phase19_audit_sha256']==OLD_AUDIT
 assert audit['checks']['unchanged_phase19_dependency_pins']==20538
 assert audit['checks']['new_source_CPU_parent_cases']==639
 prior=ROOT/'build/三国志2超级版-逆向分析-v19.zip'
 version=ROOT/'build/三国志2超级版-逆向分析-v20.zip'
 canonical=ROOT/'build/三国志2超级版-逆向分析.zip'
 assert not version.exists(),'A frozen v20 already exists; it must not be overwritten'
 assert sha(prior)==OLD_ZIP and sha(ROOT/'analysis/phase19/verification.json')==OLD_AUDIT
 assert sha(ROOT/'build/三国志2超级版.rebuilt.nes')==ROM_SHA
 audit_sha=sha(audit_path)
 groups=('source_and_validator_sha256','artifact_and_dependency_sha256')
 for group in groups:
  for name,digest in audit[group].items():assert sha(ROOT/name)==digest,(name,'Stale final audit pin')
 files=[ROOT/name for name in ROOT_FILES]
 for folder in('source','scripts','analysis'):
  files.extend(path for path in(ROOT/folder).rglob('*')if path.is_file()and permitted(path))
 assert all(not path.is_symlink()for path in files),'Do not follow unreviewed archive symlinks'
 expected={str(path.relative_to(ROOT))for path in files};assert len(files)==len(expected)
 assert all(name in ROOT_FILES or Path(name).parts[0]in('source','scripts','analysis')for name in expected)
 assert all(not Path(name).is_absolute()and '..'not in Path(name).parts for name in expected)
 for name in expected:
  assert not set(Path(name).parts)&EXCLUDED_PARTS
  assert not any(part.startswith('exploratory')for part in Path(name).parts)
 assert str(prior.relative_to(ROOT))not in expected and str(version.relative_to(ROOT))not in expected
 fd,temp_name=tempfile.mkstemp(prefix='.phase20-package-',suffix='.zip',dir=ROOT/'build');os.close(fd)
 temporary=Path(temp_name);critical=set();source_checks=0
 try:
  with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True)as archive:
   for path in sorted(files):archive.write(path,str(path.relative_to(ROOT)))
  with ZipFile(temporary)as archive:
   assert len(archive.namelist())==len(expected)and set(archive.namelist())==expected
   assert archive.testzip()is None,'CRC failure'
   for name in expected:
    assert archive.getinfo(name).file_size==(ROOT/name).stat().st_size,name
    if name.startswith('source/'):
     assert archive.read(name)==(ROOT/name).read_bytes(),name;source_checks+=1
   for group in groups:
    for name,digest in audit[group].items():
     if name.startswith('.toolchain/'):
      assert name not in expected;continue
     assert name in expected,(name,'Pinned evidence absent from allowlist')
     with archive.open(name)as stream:assert digest_stream(stream)==digest,name
   assert hashlib.sha256(archive.read('analysis/phase20/verification.json')).hexdigest()==audit_sha
   assert hashlib.sha256(archive.read('build/三国志2超级版.rebuilt.nes')).hexdigest()==ROM_SHA
   critical={name for name in expected if name.startswith('analysis/phase20/')and not name.endswith('.wav')}
   critical.update(ROOT_FILES)
   critical.update({'source/recovered/negotiation_services.py','source/recovered/negotiation_integration.py','source/recovered/nestopia_context.py'})
   assert critical<=expected
   with tempfile.TemporaryDirectory(prefix='three-kingdoms-phase20-extract-')as folder:
    for name in sorted(critical):assert sha(archive.extract(name,folder))==sha(ROOT/name),name
  # Recheck live dependencies after a potentially long archive operation.
  assert sha(audit_path)==audit_sha and sha(prior)==OLD_ZIP
  for group in groups:
   for name,digest in audit[group].items():assert sha(ROOT/name)==digest,(name,'Changed while packaging')
  # Atomic exclusive creation cannot overwrite a v20 produced concurrently.
  os.link(temporary,version)
  assert sha(version)==sha(temporary)
  fd,canonical_temp=tempfile.mkstemp(prefix='.phase20-canonical-',suffix='.zip',dir=ROOT/'build');os.close(fd)
  try:
   shutil.copyfile(version,canonical_temp);assert sha(canonical_temp)==sha(version)
   os.replace(canonical_temp,canonical)
  finally:
   if Path(canonical_temp).exists():Path(canonical_temp).unlink()
  assert sha(canonical)==sha(version)and sha(prior)==OLD_ZIP
 finally:
  if temporary.exists():temporary.unlink()
 receipt=dict(schema='phase20-postZIP-exact-allowlist-receipt-v1',version=20,status='passed',
  path=str(canonical),versioned_path=str(version),sha256=sha(version),archive_bytes=version.stat().st_size,
  file_count=len(expected),exact_allowlist_check='passed',CRC_check='passed',all_source_file_parity_checks=source_checks,
  temporary_extraction_critical_file_checks=len(critical),canonical_versioned_byte_parity='passed',
  v19_preserved_sha256=sha(prior),phase19_audit_preserved_sha256=OLD_AUDIT,
  audited_history_dependency_pins=20538,phase20_audit_sha256=audit_sha,
  validator_path='scripts/package_phase20_results.py',validator_sha256=sha(Path(__file__)),
  package_receipt_excluded_from_archive=True,original_ROM_and_rebuilt_SHA256=ROM_SHA)
 raw=json.dumps(receipt,ensure_ascii=False,indent=2)+'\n'
 (ROOT/'analysis/package-receipt.json').write_text(raw)
 (ROOT/'analysis/phase20/package-receipt.json').write_text(raw)
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
