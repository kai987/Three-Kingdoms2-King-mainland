"""Build and verify independently extractable V2.3 evidence archives."""
from argparse import ArgumentParser
import csv
from hashlib import file_digest
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from common import sha256, to_json
from v23_report import portable_bytes, published_gates

MAX_BYTES = 95_000_000


def checksum(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def members(folder, prefix):
    return [(path, f'{prefix}/{path.relative_to(folder).as_posix()}')
            for path in sorted(folder.rglob('*')) if path.is_file()]


def write_zip(path, entries):
    details=[]
    index=f'package-index/{path.stem}/FILE-INDEX.csv'
    hashes=f'package-index/{path.stem}/SHA256SUMS.txt'
    with ZipFile(path, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for source,name in entries:
            if name.startswith('logs/') or name.startswith('commands/'):
                raw=portable_bytes(source.read_bytes())
                archive.writestr(name,raw)
                details.append(dict(path=name,bytes=len(raw),sha256=sha256(raw)))
            else:
                archive.write(source,name)
                details.append(dict(path=name,bytes=source.stat().st_size,sha256=checksum(source)))
        table=StringIO(newline='')
        writer=csv.DictWriter(table, fieldnames=('path','bytes','sha256'),lineterminator='\n')
        writer.writeheader()
        writer.writerows(details)
        raw=table.getvalue().encode()
        archive.writestr(index,raw)
        sums=''.join(f"{row['sha256']}  {row['path']}\n" for row in details)
        archive.writestr(hashes,sums+f'{sha256(raw)}  {index}\n')

    with ZipFile(path) as archive:
        assert archive.testzip() is None, path
        assert len(archive.namelist())==len(set(archive.namelist()))==len(details)+2
        for record in details:
            with archive.open(record['path']) as stream:
                assert file_digest(stream,'sha256').hexdigest()==record['sha256'],record['path']
    assert path.stat().st_size<MAX_BYTES, path
    return dict(file=path.name,bytes=path.stat().st_size,sha256=checksum(path),files=len(details)+2)


def partitions(cases):
    active=[]
    used=0
    for inputs in cases:
        size=sum(path.stat().st_size for path,_ in inputs)
        if size>=MAX_BYTES:
            raise ValueError(f'The original files for {inputs[0][1]} require an individual split')
        if active and used+size >= MAX_BYTES:
            yield active
            active,used=[],0
        active.extend(inputs)
        used+=size
    if active:
        yield active


def build(source, target):
    gates=published_gates(source)
    metadata=source/'published-gates'
    for name,details in gates.items():
        to_json(metadata/f'{name}.json',details)
    technical=[(source/gate['log'],gate['log']) for gate in gates.values()]
    technical+=members(metadata,'checks')
    technical+=members(source/'technical','regression')
    technical+=members(source/'evidence','archived-evidence')
    technical+=members(source/'provenance','provenance')
    technical.extend((source/name,name) for name in ('frozen-source.txt','frozen-tree.txt',
                                                    'compatibility/compatibility.json'))
    plans={
        'v23-summary':[members(target/'summary','summary')],
        'v23-technical':[technical],
    }
    climate=source/'climate-frozen'
    for phase,label in (('calibrate','calibration'),('holdout','holdout')):
        files=sorted([*climate.glob(f'{phase}-*'),*climate.glob(f'agricultural-climate-{label}.*')])
        if phase=='holdout':
            files.extend(climate/name for name in ('city-climate-audit.csv','climate-region-monthly-probability.csv'))
        plans[f'v23-climate-{label}']=[[(path,f'climate/{path.name}') for path in files]]
    for name,waves in (
        ('v23-rapid',('quick','exceptional','locality')),
        ('v23-five-year',('five','holdout')),
        ('v23-twenty-year',('long',)),
    ):
        directories=sorted(path.parent for wave in waves for path in
                           (source/'campaigns'/wave).glob('*/*/run-v23.json'))
        plans[name]=[members(path,path.relative_to(source).as_posix()) for path in directories]
    totals=[]
    archives=target/'archives'
    archives.mkdir(parents=True,exist_ok=True)
    for name,cases in plans.items():
        packs=list(partitions(cases))
        if not packs:
            raise ValueError(f'No inputs for {name}')
        for part,entries in enumerate(packs,1):
            filename=f'{name}.zip' if len(packs)==1 else f'{name}-{part:02d}.zip'
            result=write_zip(archives/filename,entries)
            totals.append(result)
            print(result,flush=True)
    to_json(archives/'archive-index.json',totals)
    (archives/'SHA256SUMS.txt').write_text(''.join(f"{row['sha256']}  {row['file']}\n" for row in totals),
                                           encoding='utf-8')
    return totals


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('target',type=Path)
    args=parser.parse_args()
    build(args.source.resolve(),args.target.resolve())
