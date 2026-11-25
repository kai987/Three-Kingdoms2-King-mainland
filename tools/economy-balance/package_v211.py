"""Package explicit validation paths and verify the finished ZIP against its hashes."""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from common import TOOL_ROOT


def sources(args):
    for folder,root,extensions in (
        ('docs',TOOL_ROOT/'docs/logistics-v211',{'.md'}),
        ('data',args.data,{'.json','.csv','.md'}),
        ('checks',args.checks,{'.log','.json','.md','.png','.tsv','.txt','.sh'}),
        ('data/observed',args.observed,{'.json','.csv'}),
    ):
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix in extensions:
                if path.name.startswith('guandu-') or 'catalogs' in path.relative_to(root).parts:
                    continue
                relative=f'{folder}/{path.relative_to(root).as_posix()}'
                yield relative,path


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--checks',type=Path,required=True)
    parser.add_argument('--observed',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    files=list(sources(args))
    paths={name for name,_ in files}
    required={'data/simulation-manifest.json','data/validation-manifest.json',
              'data/summary.json','docs/README.md','data/pairwise.csv'}
    if len(paths)!=len(files) or not required<=paths:
        raise ValueError('Inconsistent archive input paths')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    draft=args.output.with_suffix('.tmp')
    checksums={}
    with ZipFile(draft,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in files:
            raw=path.read_bytes()
            checksums[name]=sha256(raw).hexdigest()
            archive.writestr(name,raw)
        archive.writestr('sha256.txt',''.join(f'{digest}  {name}\n' for name,digest in sorted(checksums.items())))
    with ZipFile(draft) as archive:
        if archive.testzip() is not None or len(archive.namelist())!=len(files)+1:
            raise ValueError('Archive did not validate')
        for name,digest in checksums.items():
            if sha256(archive.read(name)).hexdigest()!=digest:
                raise ValueError(f'Archive checksum mismatch for {name}')
    draft.replace(args.output)
    with args.output.open('rb') as stream:
        from hashlib import file_digest
        digest=file_digest(stream,'sha256').hexdigest()
    print(f'{len(files)} verified files, {args.output.stat().st_size} bytes, SHA-256 {digest}')


if __name__=='__main__':
    raise SystemExit(main())
