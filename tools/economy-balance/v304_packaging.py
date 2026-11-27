"""Write independently extractable validation archives for V3.0.3.1 and V3.0.4."""
from argparse import ArgumentParser
from pathlib import Path
import re
from shutil import copyfile
from tempfile import TemporaryDirectory

from common import TOOL_ROOT, to_csv, to_json
from v3021_package import members
from v3021_report import file_sha, read
from v303_package import checksums, partition

TOOL = Path(__file__).parent
PREFIX = {'3031':'v3031','304-prototype':'v304-prototype'}


def portable(raw):
    raw=raw.replace(str(TOOL_ROOT),'<WORKTREE>').replace(str(Path.home()),'<HOME>')
    raw=re.sub(r'/(?:private/)?var/folders/[^\s"\']+', '<TEMP_PATH>',raw)
    return re.sub(r'/Users/[^/\s"\']+', '<HOST_HOME>',raw)


def copy_portable(path,dest):
    raw=path.read_text(encoding='utf-8',errors='replace')
    body=portable(raw)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(body,encoding='utf-8')
    return dict(file=path.name,original_sha256=file_sha(path),portable_sha256=file_sha(dest),
                host_paths_redacted=raw!=body)


def raw_members(build, wave):
    if wave=='five':
        pattern='G*/observed/five/*/*/*/*/*/*/run-v302.json'
    else:
        pattern=f'G1/observed/{wave}/*/*/*/*/*/*/run-v302.json'
    for path in sorted(build.glob(pattern)):
        record=read(path)
        if record['outcome'] not in ('complete','natural_end'):
            raise ValueError(f'Incomplete run: {path.relative_to(build)}')
        if record['source']!=(build/'frozen-source.txt').read_text().strip():
            raise ValueError(f'Run source differs: {path.relative_to(build)}')
        if portable(path.read_text())!=path.read_text():
            raise ValueError(f'Run contains host evidence paths: {path.relative_to(build)}')
        for file in sorted(path.parent.iterdir()):
            if file.is_file() and not file.is_symlink():
                relative=file.relative_to(build).as_posix()
                yield file,'observations/'+relative,relative


def group_raw(build, output):
    output.mkdir(parents=True,exist_ok=True)
    archived=[]
    for wave,name,count in (('five','five-year',16),('long','twenty-year',6),('holdout','holdout',4)):
        rows=list(raw_members(build,wave))
        if sum(path.name=='run-v302.json' for path,_,_ in rows)!=count:
            raise ValueError(f'{wave}: expected {count} real simulations')
        archived.extend(partition(output,name,rows,prefix='v3031'))
        print(name,[row['bytes'] for row in archived if row['group']==name],flush=True)
    to_json(output/'raw-index.json',archived)


def technical_files(build, work):
    logs=build/'logs'
    allowed={'.log','.txt','.exit'}
    rows=[copy_portable(path,work/'logs'/path.name) for path in sorted(logs.iterdir())
          if path.is_file() and path.suffix in allowed and not path.name.startswith('package')]
    if not rows:
        raise ValueError('No actual technical reports available')
    to_csv(work/'log-provenance.csv',rows)
    result=members(work,'checks/technical')
    for path in sorted((build/'browser').rglob('*.png')):
        if path.is_file():
            key='browser/'+path.relative_to(build/'browser').as_posix()
            result.append((path,'checks/technical/'+key,key))
    return result


def seal(args):
    summary, output, work = args.summary,args.output,args.build
    code=summary/'sources'
    core=summary/'checks'
    code.mkdir(parents=True,exist_ok=True)
    copyfile(TOOL/'v304_recalculate.py',code/'v304_recalculate.py')
    output.mkdir(parents=True,exist_ok=True)
    prefix=PREFIX[args.version]
    source=(work/'frozen-source.txt').read_text().strip()
    manifest=code/'validation-manifest.json'
    sums=summary/'SHA256SUMS.txt'
    inputs=[p for p in sorted(summary.rglob('*')) if p.is_file() and p not in {manifest,sums}]
    for path in inputs:
        if portable(path.read_text(encoding='utf-8'))!=path.read_text(encoding='utf-8'):
            raise ValueError(f'Review or redact host path before packaging {path.relative_to(summary)}')
    to_json(manifest,dict(format='three-kingdoms-portable-validation-v1',version=args.version,source=source,
        files={path.relative_to(summary).as_posix():file_sha(path) for path in inputs},
        simulation_manifest='data/simulation-manifest.json',technical_gate_manifest='checks/technical-gates.json'))
    sums.write_text(checksums(summary,[*inputs,manifest]),encoding='utf-8')
    archives=partition(output,'summary',members(summary,f'validation/v{args.version}/summary'),prefix=prefix)
    if len(archives)!=1 or archives[0]['bytes']>20_000_000:
        raise ValueError('Core readable data must fit within a single 20 MB summary ZIP')
    if args.version=='3031':
        archives.extend(read(output/'raw-index.json'))
    with TemporaryDirectory(prefix='portable-logs-') as temporary:
        cleaned=Path(temporary)
        archives.extend(partition(output,'technical',technical_files(work,cleaned),prefix=prefix))
    if args.version=='3031':
        root=work/'derived-observations'
        detail=[(path,'derived-observations/'+path.name,'derived-observations/'+path.name)
                for path in sorted(root.glob('*.csv')) if not path.name.endswith('-full.csv')]
        archives.extend(partition(output,'slot-observations',detail,prefix=prefix))
    replay=[]
    for path in args.checkpoints:
        replay.append((path,'replays/checkpoints/'+path.name,'checkpoint-inputs/'+path.name))
    if args.version=='3031':
        for path in sorted((work/'checks').glob('convoy-3634-turn-*.json.gz')):
            replay.append((path,'replays/checks/'+path.name,'checks/'+path.name))
        for name in ('fixed-capacity-replay-traces.json','historical-3634-replay.json','historical-1860-relief-review.json'):
            path=core/name
            if path.is_file():
                replay.append((path,'replays/evidence/'+name,'summary/checks/'+name))
    else:
        for path in sorted((work/'controlled-samples').glob('*')):
            if path.is_file():
                replay.append((path,'controls/'+path.name,'controlled/'+path.name))
    archives.extend(partition(output,'replays' if args.version=='3031' else 'controls',replay,prefix=prefix))
    index=output/f'{prefix}-package-index.json'
    to_json(index,dict(version=args.version,source=source,validation_sha256=file_sha(manifest),archives=archives))
    sums_files=[output/item[key] for item in archives for key in ('archive','file_manifest')]
    (output/'SHA256SUMS.txt').write_text(checksums(output,[*sums_files,index]),encoding='utf-8')
    print(index,flush=True)


def main():
    parser=ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    raw=sub.add_parser('raw')
    raw.add_argument('build',type=Path)
    raw.add_argument('output',type=Path)
    final=sub.add_parser('seal')
    final.add_argument('version',choices=tuple(PREFIX))
    final.add_argument('build',type=Path)
    final.add_argument('summary',type=Path)
    final.add_argument('output',type=Path)
    final.add_argument('--checkpoints',type=Path,nargs='*',default=[])
    args=parser.parse_args()
    if args.action=='raw':
        group_raw(args.build,args.output)
    else:
        seal(args)


if __name__=='__main__':
    main()
