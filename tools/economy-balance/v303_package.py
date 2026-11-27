"""Build portable V3.0.3 split archives with independent SHA-256 manifests."""
from argparse import ArgumentParser
import json
from pathlib import Path
import re
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from common import ROOT, to_csv, to_json
from v3021_package import LIMIT, members, sanitized, verified, write_zip
from v3021_report import file_sha, read


def index_archive(path,kind):
    if path.stat().st_size>LIMIT:
        raise ValueError(f'Archive exceeds 100 MB: {path.name}')
    manifest,count=verified(path)
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f'ZIP CRC failed: {path.name}')
    external=path.with_name(path.stem+'-files.csv')
    external.write_text(manifest,encoding='utf-8')
    return dict(group=kind,archive=path.name,bytes=path.stat().st_size,files=count,
                sha256=file_sha(path),file_manifest=external.name,manifest_sha256=file_sha(external))


def partition(output,group,rows,start=1):
    if not rows:
        return []
    bundles=[]
    with TemporaryDirectory(dir=output,prefix='.compress-') as directory:
        draft=Path(directory)/'next.zip'
        weighted={}
        # Store a conservative measured upper bound per input file. This
        # keeps large raw waves compact without relying on compression guesses.
        for batch in batches(rows,950_000_000):
            write_zip(draft,batch)
            with ZipFile(draft) as staging:
                for file,name,origin in batch:
                    weighted[name]=staging.getinfo(name).compress_size+1_024+3*len(name.encode('utf-8'))
        size=0
        pending=[]
        for row in rows:
            estimate=weighted[row[1]]
            if size+estimate>LIMIT-1_000_000 and pending:
                bundles.append(pending)
                size,pending=0,[]
            pending.append(row)
            size+=estimate
        if pending:
            bundles.append(pending)
        result=[]
        for i,bundle in enumerate(bundles,start):
            name=f'v303-{group}'+('' if len(bundles)==1 and i==1 else f'-{i:02}')+'.zip'
            write_zip(draft,bundle)
            dest=output/name
            draft.replace(dest)
            result.append(index_archive(dest,group))
    return result


def batches(rows,limit):
    batch=[]
    size=0
    for row in rows:
        weight=row[0].stat().st_size
        if batch and size+weight>limit:
            yield batch
            batch,size=[],0
        batch.append(row)
        size+=weight
    if batch:
        yield batch


def raw_members(build,manifest,waves):
    for row in sorted(manifest['simulations'],key=lambda item:
            (item['wave'],item['economy_background'],item['scenario'],item['group'],item['seed'])):
        if (row['wave'] not in waves or row['status'] not in {'complete','natural_end'}
                or row['input']=='historical'):
            continue
        relative=Path(row['relative_path'])
        folder=build/row['input']/relative
        if file_sha(folder/'run-v302.json')!=row['run_sha256']:
            raise ValueError(f'Manifest run changed: {relative}')
        for file in sorted(folder.iterdir()):
            if file.is_file() and not file.is_symlink():
                actual=(Path('observations')/relative/file.name).as_posix()
                origin=(Path(row['input'])/relative/file.name).as_posix()
                yield file,actual,origin


def checksums(root,files):
    return ''.join(f'{file_sha(path)}  {path.relative_to(root).as_posix()}\n' for path in files)


def package(args):
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Use an empty archive output directory')
    manifest=read(args.summary/'data/simulation-manifest.json')
    status=read(args.summary/'data/report-status.json')
    command_names=('v303_experiments.py','v303_capacity_audit.py','v303_replay_checks.py',
                   'v303_report.py','v303_package.py','v303_delivery.py','v303_recalculate.py')
    saved=args.summary/'sources'
    copyfile(ROOT/'tools/economy-balance/v303_recalculate.py',saved/'v303_recalculate.py')
    hashes={name:file_sha(ROOT/'tools/economy-balance'/name) for name in command_names}
    summary_index=saved/'validation-manifest.json'
    sums=args.summary/'SHA256SUMS.txt'
    prior=[p for p in sorted(args.summary.rglob('*')) if p.is_file() and p not in (summary_index,sums)]
    to_json(summary_index,dict(format='three-kingdoms-v303-validation-v1',source=status['source'],
        map_sha256=manifest['map_sha256'],simulation_manifest_sha256=file_sha(args.summary/'data/simulation-manifest.json'),
        engine_base=manifest['baseline_release'],tools=hashes,
        candidate_runs=status['states'],files={p.relative_to(args.summary).as_posix():file_sha(p) for p in prior}))
    sums.write_text(checksums(args.summary,[*prior,summary_index]),encoding='utf-8')
    args.output.mkdir(parents=True,exist_ok=True)
    archives=partition(args.output,'summary',members(args.summary,'validation/v303/summary'))
    if len(archives)!=1:
        raise ValueError('Expected a single summary archive')
    for group,waves in (('quick',{'quick'}),('five-year',{'five'}),('twenty-year',{'long'}),('holdout',{'holdout'})):
        archives.extend(partition(args.output,group,list(raw_members(args.build,manifest,waves))))
    with TemporaryDirectory(dir=args.output,prefix='.technical-') as directory:
        clean=Path(directory)
        sanitized(args.build/'logs',clean)
        # Redact host-dependent temporary directories without changing results.
        for path in clean.glob('*.log'):
            raw=path.read_text(encoding='utf-8')
            portable=re.sub(r'/var/folders/[^\s\'"]+', '<TEMP_PATH>', raw)
            if raw!=portable:
                path.write_text(portable,encoding='utf-8')
        to_csv(clean/'log-provenance.csv',[
            dict(log=name.name,original_sha256=file_sha(args.build/'logs'/name.name),
                 packaged_sha256=file_sha(name),
                 transformed=file_sha(args.build/'logs'/name.name)!=file_sha(name))
            for name in sorted(clean.glob('*.log'))])
        technical=members(clean,'checks/logs')
        browser=args.build/'browser'
        technical.extend((p,'checks/browser/'+p.relative_to(browser).as_posix(),
                          'browser/'+p.relative_to(browser).as_posix())
                         for p in sorted(browser.rglob('*.png')))
        technical.extend((p,'checks/'+p.name,'checks/'+p.name)
                         for p in sorted((args.build/'checks').glob('*.exit')))
        technical.extend((p,'tools/'+p.name,'tools/economy-balance/'+p.name)
                         for p in (ROOT/'tools/economy-balance'/name for name in command_names))
        archives.extend(partition(args.output,'technical',technical))
    replay_files=[]
    for path in args.checkpoints:
        replay_files.append((path,f'checkpoints/{path.name}',f'checkpoint-inputs/{path.name}'))
    for path in sorted((args.build/'checks').glob('*.json')):
        if (path.name.startswith('historical-') or '-released' in path.name or '-disabled' in path.name
                or '-capacity-' in path.name or path.name=='save-parity.json'):
            replay_files.append((path,f'checks/{path.name}',f'checks/{path.name}'))
    for filename in ('fixed-capacity-replay-traces.json','fixed-replay-inputs.json','historical-1860-original.json'):
        path=args.summary/'checks'/filename
        if path.is_file():
            replay_files.append((path,f'checks/{filename}',f'validation/v303/summary/checks/{filename}'))
    archives.extend(partition(args.output,'capacity-replays',replay_files))
    package_index=args.output/'v303-package-index.json'
    to_json(package_index,dict(version=303,source=status['source'],map_sha256=manifest['map_sha256'],
        validation_sha256=file_sha(summary_index),archives=archives))
    audited=[package_index,*[args.output/row[key] for row in archives for key in ('archive','file_manifest')]]
    (args.output/'SHA256SUMS.txt').write_text(checksums(args.output,audited),encoding='utf-8')
    return archives


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('summary',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--checkpoints',nargs='*',type=Path,default=[])
    args=parser.parse_args()
    print(json.dumps(package(args),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
