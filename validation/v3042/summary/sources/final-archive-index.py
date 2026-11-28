from hashlib import file_digest
from pathlib import Path
from zipfile import ZipFile
import json
import sys

root=Path(sys.argv[1])
def file_sha(path):
 with path.open('rb') as stream:
  return file_digest(stream,'sha256').hexdigest()

bundles=[]
for p in sorted((root/'bundles').glob('*.manifest.json')):
 manifest=json.loads(p.read_bytes())
 path=root/manifest['path']
 assert manifest['bytes']==path.stat().st_size and manifest['sha256']==file_sha(path)
 assert path.stat().st_size<100_000_000
 with ZipFile(path) as z:
  assert z.testzip() is None
  assert z.namelist()==[r['path'] for r in manifest['members']]
  for r in manifest['members']:
   with z.open(r['path']) as stream:
    assert file_digest(stream,'sha256').hexdigest()==r['sha256']
 bundles.append(dict(path=manifest['path'],bytes=manifest['bytes'],sha256=manifest['sha256'],
                     members=len(manifest['members']),index=p.relative_to(root).as_posix()))
(root/'bundle-index.json').write_text(json.dumps(bundles,indent=2)+'\n',encoding='utf-8')
rows=[]
ignored={'SHA256SUMS.txt','FILE-INDEX.json'}
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.relative_to(root).as_posix() in ignored:
  continue
 assert not p.is_symlink() and p.suffix!='.tmp',p
 rows.append(dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=file_sha(p)))
(root/'FILE-INDEX.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
indexed=rows+[dict(path='FILE-INDEX.json',sha256=file_sha(root/'FILE-INDEX.json'))]
(root/'SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in indexed),encoding='utf-8')
print(json.dumps(dict(bundles=len(bundles),files=len(indexed),archive_bytes=sum(r['bytes'] for r in bundles),
                      largest_bundle=max(r['bytes'] for r in bundles)),indent=2))
