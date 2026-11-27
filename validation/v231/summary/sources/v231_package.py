"""Split audit evidence into independent, checksum-verified archives."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile
import json

from common import to_json
from v23_package import MAX_BYTES, checksum, members, write_zip
from v23_report import portable_bytes, published_gates


def split(entries):
    current=[]
    size=0
    for path,name in entries:
        weight=path.stat().st_size
        if weight>=MAX_BYTES:
            raise ValueError(f'An individual file needs a format-aware split: {name}')
        if current and size+weight>=MAX_BYTES:
            yield current
            current,size=[],0
        current.append((path,name))
        size+=weight
    if current:
        yield current


def campaign_members(root,waves,prefix='campaigns'):
    for wave in waves:
        for run in sorted((root/'campaigns'/wave).glob('*/*/run-v231.json')):
            data=json.loads(run.read_text())
            if data['outcome'] in ('complete','natural_end'):
                yield from members(run.parent,f'{prefix}/{run.parent.relative_to(root/"campaigns").as_posix()}')


def build(source,older,target):
    archives=target/'archives'
    archives.mkdir(parents=True,exist_ok=True)
    metadata=source/'archive-metadata'
    metadata.mkdir(exist_ok=True)
    technical=[]
    for name,gate in published_gates(source).items():
        public=metadata/gate['log']
        public.parent.mkdir(parents=True,exist_ok=True)
        public.write_bytes(portable_bytes((source/gate['log']).read_bytes()))
        assert checksum(public)==gate['log_sha256']
        technical.append((public,gate['log']))
    for name in ('full-browser-results.json','baseline-identity.json','observer-equivalence.json',
                 'browser-test-source.json'):
        original=source/'checks'/name
        if original.is_file():
            public=metadata/name
            public.write_bytes(portable_bytes(original.read_bytes()))
            technical.append((public,'checks/'+name))
    technical.extend((path,name) for path,name in members(source/'technical','technical')
                     if '/interrupted-browser/' not in name)
    for p in sorted((source/'compatibility').glob('*.json')):
        technical.append((p,f'compatibility/{p.name}'))
    technical.extend((source/name,f'provenance/{name}') for name in ('frozen-source.txt',) if (source/name).is_file())
    technical.extend((path,f'provenance/{path.name}') for path in sorted(source.glob('plan-*.json')))
    plans={
        'v231-summary':members(target/'summary','summary'),
        'v231-technical':technical,
        'v231-rapid':list(campaign_members(source,('quick',))),
        'v231-five-year':list(campaign_members(source,('five',))),
        'v231-holdout':list(campaign_members(source,('holdout',))),
        'v231-twenty-year':list(campaign_members(source,('long',))),
        'v231-root-cause':[*campaign_members(older,('root',)),*members(source/'replays','replays'),
                          *members(source/'performance','performance')],
    }
    additional=list(campaign_members(source/'detailed',('long',),'channel-audit'))
    if additional:
        plans['v231-channel-audit']=additional
    index=[]
    mapped=[]
    for label,entries in plans.items():
        blocks=list(split(entries))
        if not blocks:
            raise ValueError(f'No validated data for {label}')
        for index_part,block in enumerate(blocks,1):
            name=f'{label}.zip' if len(blocks)==1 else f'{label}-{index_part:02d}.zip'
            index.append(write_zip(archives/name,block))
            with ZipFile(archives/name) as archive:
                for original in archive.namelist():
                    if not original.startswith('package-index/'):
                        mapped.append(dict(archive=name,original_path=original,bytes=archive.getinfo(original).file_size))
            print(index[-1],flush=True)
    if (archives/'v231-summary.zip').stat().st_size>=20_000_000:
        raise ValueError('Summary is larger than 20 MB')
    to_json(archives/'archive-index.json',dict(archives=index,files=mapped))
    (archives/'SHA256SUMS.txt').write_text(''.join(f"{row['sha256']}  {row['file']}\n" for row in index),encoding='utf-8')
    (target/'README.md').write_text(
       '# V2.3.1 验收归档\n\n[可直接阅读的汇总](summary/) · [分片索引](archives/archive-index.json) · '
       '[ZIP 校验](archives/SHA256SUMS.txt)\n\n'
       '各包均可独立解压，包内保留源目录及逐文件 SHA-256。汇总直接保存 Markdown、CSV 和 JSON。\n',
       encoding='utf-8')
    return index


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    for key in ('source','older','target'):
        parser.add_argument(key,type=Path)
    args=parser.parse_args()
    build(args.source,args.older,args.target)
