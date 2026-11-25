"""Package evidence, provenance and reports without shipping game assets or saves."""
from argparse import ArgumentParser
import json
from pathlib import Path
from platform import python_version
from zipfile import ZIP_DEFLATED, ZipFile

from common import ROOT, git, sha256, to_json


OUTPUTS = (
    'travel-routes-v1-v2.csv', 'route-seasonal-costs-v1-v2.csv', 'river-segment-supply-v2.csv',
    'march-supply-cases-v2.csv', 'cargo-attrition-cases-v2.csv', 'transport-conservation-v2.csv',
    'minimum-grain-route-cases.csv', 'war-budget-v2.csv', 'ai-recruitment-budget-cases.csv',
    'ai-expedition-budget-cases.csv', 'strategic-grain-reserves.csv', 'scenario-logistics-summary.csv',
    'long-term-economy-comparison.csv', 'long-term-military-comparison.csv', 'long-term-shortage-comparison.csv',
    'simulation-manifest.json', 'route-validation.json', 'case-validation.json', 'data-dictionary.md',
)
VERSIONS = (
    'source/remake', 'crates/march-core/src', 'crates/march-core/Cargo.lock',
    'game/config', 'game/data/campaigns', 'game/app.js', 'game/domestic.js', 'game/events.js',
    'game/browser-client.js', 'game/browser-engine-worker.js', 'game/march-worker.js',
    'game/serve.py', 'game/wasm/manifest.json', 'tools/web-runtime/package-lock.json',
)


def runtime_snapshot(ident):
    paths=git('ls-tree','-r','--name-only',ident,'--',*VERSIONS).decode().splitlines()
    return {name:sha256(git('show',f'{ident}:{name}')) for name in paths}


def assemble(data, logs, bundle):
    for name in OUTPUTS:
        if not (data/name).is_file():
            raise ValueError(f'Missing validation data: {name}')
    cohort=json.loads((data/'simulation-manifest.json').read_text(encoding='utf-8'))
    head=git('rev-parse','HEAD').decode().strip()
    base=cohort['groups']['A']
    entries={}
    for path in sorted((ROOT/'docs/logistics-v2').glob('*.md')):
        entries['docs/'+path.name]=path
    for name in OUTPUTS:
        entries['data/'+name]=data/name
    for path in sorted(data.glob('observed/*/*/*/*/*')):
        if path.name in ('monthly.csv','factions.csv','cities.csv','capture-recovery.csv','run.json'):
            entries['data/'+path.relative_to(data).as_posix()]=path
    for dirname in ('battles','battles-baseline','experiments'):
        for path in sorted((data/dirname).glob('*')):
            if path.suffix in ('.csv','.json') and path.is_file():
                entries['data/'+path.relative_to(data).as_posix()]=path
    for path in sorted(logs.glob('*')):
        if path.suffix in ('.log','.json') and path.is_file():
            entries['checks/'+path.name]=path
    if not any(key.startswith('data/observed/') for key in entries):
        raise ValueError('No bundled observer outputs')
    manifest=dict(schema='tk2-logistics-v2-evidence-1',code_head=head,branch=git('branch','--show-current').decode().strip(),
        branch_push=False,python=python_version(),runtime=cohort['groups'],
        source_changes=git('diff','--name-status',base,head).decode().splitlines(),
        build_rules=json.loads((ROOT/'game/wasm/manifest.json').read_text(encoding='utf-8')),
        source_worktree_diff_sha256=sha256(git('diff','HEAD','--binary','--',*VERSIONS)),
        runtime_source_sha256={ident:runtime_snapshot(ident) for ident in sorted(set(cohort['groups'].values())|{head})},
        distributed_files={name:dict(sha256=sha256(path.read_bytes()),bytes=path.stat().st_size)
                           for name,path in entries.items()})
    output=data/'validation-manifest.json'
    to_json(output,manifest)
    entries['data/validation-manifest.json']=output
    bundle.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(bundle,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in entries.items():
            archive.write(path,name)
    with ZipFile(bundle) as archive:
        assert archive.testzip() is None
        for name,entry in manifest['distributed_files'].items():
            assert sha256(archive.read(name))==entry['sha256'],name
    print(json.dumps(dict(bundle=str(bundle),entries=len(entries),bytes=bundle.stat().st_size,
                          sha256=sha256(bundle.read_bytes())),ensure_ascii=False))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--logs',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    args=parser.parse_args()
    assemble(args.data,args.logs,args.bundle)
