from hashlib import file_digest
import json
from pathlib import Path, PurePosixPath
import sys
from zipfile import ZipFile,ZIP_DEFLATED,ZIP_STORED

source=Path(sys.argv[1]).resolve()
target=Path(sys.argv[2])
prefix=PurePosixPath(sys.argv[3])
name=sys.argv[4]
folder=target/'bundles'
folder.mkdir(parents=True,exist_ok=True)
pending=folder/f'{name}.tmp'
archive=folder/f'{name}.zip'

def digest(value):
 with value.open('rb') as stream:
  return file_digest(stream,'sha256').hexdigest()

files=[p for p in sorted(source.rglob('*')) if p.is_file()]
assert files
members=[]
with ZipFile(pending,'w',compression=ZIP_DEFLATED,compresslevel=6) as container:
 for path in files:
  member=str(prefix/path.relative_to(source))
  container.write(path,member,compress_type=ZIP_STORED if path.suffix=='.gz' else ZIP_DEFLATED)
  members.append(dict(path=member,bytes=path.stat().st_size,sha256=digest(path)))
with ZipFile(pending) as container:
 assert container.testzip() is None
 assert container.namelist()==[row['path'] for row in members]
 for row in members:
  with container.open(row['path']) as contents:
   assert file_digest(contents,'sha256').hexdigest()==row['sha256']
 assert pending.stat().st_size<100_000_000
pending.replace(archive)
record=dict(path=str(archive.relative_to(target)),bytes=archive.stat().st_size,sha256=digest(archive),
            members=members)
(folder/f'{name}.manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{archive.name} {len(members)} members, {record["bytes"]} bytes')
