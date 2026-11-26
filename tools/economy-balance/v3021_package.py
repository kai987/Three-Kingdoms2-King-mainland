"""Write and independently verify the V3.0.2.1 acceptance ZIPs and indexes."""
from argparse import ArgumentParser
import csv
import io
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from common import ROOT, TOOL_ROOT, to_csv, to_json
from v3021_report import file_sha, sha256_stream

LIMIT = 100_000_000
def member_csv(files):
    text = io.StringIO(newline='')
    writer = csv.writer(text,lineterminator='\n')
    writer.writerow(('member','source_path','size','sha256'))
    for path, name, origin in files:
        writer.writerow((name,origin,path.stat().st_size,file_sha(path)))
    return text.getvalue()


def write_zip(path, files):
    manifest = member_csv(files)
    with ZipFile(path,'w',compression=ZIP_DEFLATED,compresslevel=3) as archive:
        for file, name, _ in files:
            archive.write(file,name,compress_type=ZIP_STORED if file.suffix in ('.gz','.png','.zip') else ZIP_DEFLATED)
        archive.writestr('FILE-MANIFEST.csv',manifest)
    return manifest


def verified(path):
    with ZipFile(path) as archive:
        manifest = archive.read('FILE-MANIFEST.csv').decode()
        entries = list(csv.DictReader(io.StringIO(manifest)))
        if len(archive.namelist())!=1+len(entries) or len({row['member'] for row in entries})!=len(entries):
            raise ValueError(f'Membership mismatch for {path.name}')
        for row in entries:
            with archive.open(row['member']) as stream:
                if sha256_stream(stream)!=row['sha256'] or archive.getinfo(row['member']).file_size!=int(row['size']):
                    raise ValueError(f'Hash mismatch for {row["member"]}')
    return manifest,len(entries)


def archive_group(folder, group, files, *, limit=LIMIT):
    if not files:
        return []
    dest = folder/f'v3021-{group}.zip'
    with TemporaryDirectory(dir=folder) as scratch:
        tmp = Path(scratch)/'candidate.zip'
        write_zip(tmp,files)
        if tmp.stat().st_size<=limit:
            tmp.replace(dest)
            pending = [dest]
        else:
            partitions, batch, size = [], [], 0
            for item in files:
                n = item[0].stat().st_size
                if batch and size+n+200_000>limit:
                    partitions.append(batch)
                    batch,size=[],0
                batch.append(item)
                size += n
            if batch:
                partitions.append(batch)
            pending = []
            for index, members in enumerate(partitions,1):
                target = folder/f'v3021-{group}-{index:02}.zip'
                write_zip(tmp,members)
                if tmp.stat().st_size>limit:
                    raise ValueError(f'{group} part {index} exceeds size limit')
                tmp.replace(target)
                pending.append(target)
    output = []
    for archive in pending:
        csv_manifest, count = verified(archive)
        catalog = folder/f'{archive.stem}-files.csv'
        catalog.write_text(csv_manifest,encoding='utf-8')
        output.append(dict(group=group,archive=archive.name,size=archive.stat().st_size,
            sha256=file_sha(archive),files=count,file_manifest=catalog.name,manifest_sha256=file_sha(catalog)))
    return output


def raw_files(root, waves):
    paths = []
    for wave in waves:
        for run in sorted((root/wave).rglob('run-v302.json')):
            if '_working' in run.relative_to(root).parts:
                continue
            record = json.loads(run.read_text())
            if record['outcome'] not in ('complete','natural_end'):
                continue
            paths.extend((p, f'observed/{p.relative_to(root)}', f'frozen-run/observed/{p.relative_to(root)}')
                          for p in sorted(run.parent.iterdir()) if p.is_file())
    return paths


def sanitized(raw, cleaned):
    provenance = []
    for path in sorted(raw.glob('*.log')):
        if path.name=='package-output.log':
            continue
        body = path.read_text(encoding='utf-8',errors='replace')
        body = body.replace(str(TOOL_ROOT),'<GAME_WORKTREE>').replace(str(ROOT),'<RUNTIME_WORKTREE>')
        body = body.replace(str(Path.home()),'<HOME>')
        body = re.sub(r'/private/var/folders/[^\s\'"]+', '<TEMP_PATH>', body)
        output = cleaned/path.name
        output.write_text(body,encoding='utf-8')
        original_sha, packaged_sha = file_sha(path),file_sha(output)
        provenance.append(dict(log=path.name,original_sha256=original_sha,
                               packaged_sha256=packaged_sha,transformed=original_sha!=packaged_sha))
    if provenance:
        to_csv(cleaned/'log-provenance.csv',provenance)


def members(root, prefix):
    return [(file,f'{prefix}/{file.relative_to(root)}',f'{prefix}/{file.relative_to(root)}')
            for file in sorted(root.rglob('*')) if file.is_file() and not file.is_symlink()]


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('summary',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Specify an empty output directory')
    args.output.mkdir(parents=True,exist_ok=True)
    results = archive_group(args.output,'summary',members(args.summary,'validation/v3021/summary'),limit=20_000_000)
    if len(results)!=1:
        raise ValueError('Expected a single summary archive')
    for group, waves in (('five-year',('winter','dry','relay')),('twenty-year',('long',)),('holdout',('holdout',))):
        results.extend(archive_group(args.output,group,raw_files(args.build/'final/observed',waves)))
    with TemporaryDirectory(dir=args.output) as temp:
        clean = Path(temp)
        sanitized(args.build/'logs',clean)
        technical = members(clean,'checks/logs')+members(args.build/'browser','checks/browser')
        technical += [(p,f'checks/{p.name}',f'checks/{p.name}') for p in sorted((args.build/'checks').iterdir())
                      if p.suffix=='.exit']
        results.extend(archive_group(args.output,'technical',technical))
    replays = members(args.build/'checkpoints','checkpoints')
    names = ('g1-','g2-','return-')
    replays += [(p,f'checks/{p.name}',f'checks/{p.name}') for p in sorted((args.build/'checks').glob('*.json'))
                if p.name.startswith(names)]
    results.extend(archive_group(args.output,'replays',replays))
    info=dict(version=3021,source=(args.build/'final-source.txt').read_text().strip(),packages=results)
    index=args.output/'v3021-package-index.json'
    to_json(index,info)
    verified_files = [index,*[args.output/row[field] for row in results for field in ('archive','file_manifest')]]
    (args.output/'SHA256SUMS.txt').write_text(''.join(f'{file_sha(p)}  {p.name}\n' for p in verified_files))
    print(json.dumps(info,ensure_ascii=False))


if __name__=='__main__':
    main()
