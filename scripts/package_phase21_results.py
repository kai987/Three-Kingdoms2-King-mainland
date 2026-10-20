#!/usr/bin/env python3
"""Package v21 after its final audit, preserving the frozen v20 byte for byte.

Nothing is regenerated. A pre-existing v21 is an error. The canonical ZIP is
updated atomically only after exact allowlist, CRC, all source bytes, audit
pins and critical extraction have passed. Build toolchains stay excluded.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, os, shutil, tempfile

ROOT=Path(__file__).resolve().parents[1]
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OLD_AUDIT='e548b4cd1a3a1c0f1890236b982d20fa8e7c63f4f16ee9a11deb2d04d8916205'
OLD_ZIP='b7fcfa4882c0442d697cfe01ef2ab0df530d2d73efe0aa1ec43e1c201b697463'
ROOT_FILES=('README.md','requirements.txt','.gitignore','build/三国志2超级版.rebuilt.nes')
EXCLUDED_PARTS={'.toolchain','.venv','.venv-trace','node_modules','__pycache__','.git'}
PIN_GROUPS=('source_and_validator_sha256','artifact_and_dependency_sha256')

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

def atomic_receipt(path,raw):
 fd,name=tempfile.mkstemp(prefix='.phase21-receipt-',suffix='.json',dir=path.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8')as stream:stream.write(raw)
  os.replace(name,path)
 finally:
  if Path(name).exists():Path(name).unlink()

def main():
 audit_path=ROOT/'analysis/phase21/verification.json';audit=json.loads(audit_path.read_text())
 assert audit['status']=='passed'and audit['rebuilt_byte_identical']and audit['ROM_sha256']==ROM_SHA
 assert audit['old_v20_preserved_sha256']==OLD_ZIP and audit['old_phase20_audit_sha256']==OLD_AUDIT
 prior=ROOT/'build/三国志2超级版-逆向分析-v20.zip'
 version=ROOT/'build/三国志2超级版-逆向分析-v21.zip'
 canonical=ROOT/'build/三国志2超级版-逆向分析.zip'
 prior_audit_path=ROOT/'analysis/phase20/verification.json'
 assert not version.exists(),'A frozen v21 already exists; it must not be overwritten'
 assert sha(prior)==OLD_ZIP and sha(prior_audit_path)==OLD_AUDIT
 assert sha(ROOT/'build/三国志2超级版.rebuilt.nes')==ROM_SHA
 audit_sha=sha(audit_path)
 for group in PIN_GROUPS:
  assert isinstance(audit[group],dict)and audit[group],('Missing final audit pin group',group)
  for name,pin in audit[group].items():
   assert not Path(name).is_absolute()and '..'not in Path(name).parts,name
   assert isinstance(pin,str)and len(pin)==64,(name,'Invalid final SHA256')
   assert sha(ROOT/name)==pin,(name,'Stale final audit pin')
 files=[ROOT/name for name in ROOT_FILES]
 for folder in('source','scripts','analysis'):
  files.extend(path for path in(ROOT/folder).rglob('*')if path.is_file()and permitted(path))
 assert all(not path.is_symlink()for path in files),'Do not follow unreviewed archive symlinks'
 expected={str(path.relative_to(ROOT))for path in files};assert len(files)==len(expected)
 assert all(name in ROOT_FILES or Path(name).parts[0]in('source','scripts','analysis')for name in expected)
 for name in expected:
  assert not Path(name).is_absolute()and '..'not in Path(name).parts
  assert not set(Path(name).parts)&EXCLUDED_PARTS
  assert not any(part.startswith('exploratory')for part in Path(name).parts)
 assert str(prior.relative_to(ROOT))not in expected and str(version.relative_to(ROOT))not in expected
 fd,temp_name=tempfile.mkstemp(prefix='.phase21-package-',suffix='.zip',dir=ROOT/'build');os.close(fd)
 temporary=Path(temp_name);critical=set();source_checks=archive_pin_checks=0
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
   for group in PIN_GROUPS:
    for name,pin in audit[group].items():
     if name.startswith('.toolchain/'):
      assert name not in expected;continue
     assert name in expected,(name,'Pinned evidence absent from allowlist')
     with archive.open(name)as stream:assert digest_stream(stream)==pin,name
     archive_pin_checks+=1
   assert hashlib.sha256(archive.read('analysis/phase21/verification.json')).hexdigest()==audit_sha
   assert hashlib.sha256(archive.read('analysis/phase20/verification.json')).hexdigest()==OLD_AUDIT
   assert hashlib.sha256(archive.read('build/三国志2超级版.rebuilt.nes')).hexdigest()==ROM_SHA
   critical={name for name in expected if name.startswith('analysis/phase21/')and not name.endswith('.wav')}
   critical.update(ROOT_FILES)
   critical.update({'source/recovered/city_recruitment_services.py','source/recovered/city_recruitment_integration.py',
    'source/recovered/nestopia_context.py','scripts/capture_city_auxiliary_watchpoints.py','scripts/package_phase21_results.py'})
   assert critical<=expected
   with tempfile.TemporaryDirectory(prefix='three-kingdoms-phase21-extract-')as folder:
    for name in sorted(critical):assert sha(archive.extract(name,folder))==sha(ROOT/name),name
  # A long ZIP operation must not publish stale dependencies or old history.
  assert sha(audit_path)==audit_sha and sha(prior)==OLD_ZIP and sha(prior_audit_path)==OLD_AUDIT
  for group in PIN_GROUPS:
   for name,pin in audit[group].items():assert sha(ROOT/name)==pin,(name,'Changed while packaging')
  # Exclusive hardlink creation cannot overwrite a v21 made concurrently.
  os.link(temporary,version)
  assert sha(version)==sha(temporary)
  fd,canonical_temp=tempfile.mkstemp(prefix='.phase21-canonical-',suffix='.zip',dir=ROOT/'build');os.close(fd)
  try:
   shutil.copyfile(version,canonical_temp);assert sha(canonical_temp)==sha(version)
   assert sha(audit_path)==audit_sha and sha(prior)==OLD_ZIP and sha(prior_audit_path)==OLD_AUDIT
   os.replace(canonical_temp,canonical)
  finally:
   if Path(canonical_temp).exists():Path(canonical_temp).unlink()
  assert sha(canonical)==sha(version)and sha(prior)==OLD_ZIP and sha(prior_audit_path)==OLD_AUDIT
 finally:
  if temporary.exists():temporary.unlink()
 prior_audit=json.loads(prior_audit_path.read_text())
 history_pins={name:pin for group in PIN_GROUPS for name,pin in prior_audit[group].items()}
 receipt=dict(schema='phase21-postZIP-exact-allowlist-receipt-v1',version=21,status='passed',
  path=str(canonical),versioned_path=str(version),sha256=sha(version),archive_bytes=version.stat().st_size,
  file_count=len(expected),exact_allowlist_check='passed',CRC_check='passed',all_source_file_parity_checks=source_checks,
  archive_dependency_pin_checks=archive_pin_checks,audit_pin_group_counts={group:len(audit[group])for group in PIN_GROUPS},
  temporary_extraction_critical_file_checks=len(critical),canonical_versioned_byte_parity='passed',
  v20_preserved_sha256=sha(prior),phase20_audit_preserved_sha256=sha(prior_audit_path),
  audited_history_dependency_pins=audit.get('checks',{}).get('unchanged_phase20_dependency_pins',len(history_pins)),phase21_audit_sha256=audit_sha,
  validator_path='scripts/package_phase21_results.py',validator_sha256=sha(Path(__file__)),
  package_receipt_excluded_from_archive=True,toolchain_excluded_from_archive=True,original_ROM_and_rebuilt_SHA256=ROM_SHA)
 raw=json.dumps(receipt,ensure_ascii=False,indent=2)+'\n'
 atomic_receipt(ROOT/'analysis/phase21/package-receipt.json',raw)
 atomic_receipt(ROOT/'analysis/package-receipt.json',raw)
 print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
