#!/usr/bin/env python3
"""Package reproducible analysis outputs; exclude runtimes and exploratory results."""
from pathlib import Path
import hashlib
import json
import argparse
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.parse_args() # --help exits before any verification or ZIP mutation.
target=ROOT/'build/三国志2超级版-逆向分析.zip'
phase17=json.loads((ROOT/'analysis/phase17/verification.json').read_text())
assert phase17['status']=='passed' and phase17['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase17[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase17_receipts={key:row['receipt_path'] for key,row in phase17['areas'].items()}
phase17_receipts.update({'source-integration':phase17['source_integration_receipt_path'],'native':'analysis/phase17/runtime/validation.json'})
phase17_evidence={key:row['evidence_path'] for key,row in phase17['areas'].items()}
phase17_evidence.update({'native':phase17['native_evidence_path']})
for group,paths in [('receipt_sha256',phase17_receipts),('evidence_sha256',phase17_evidence)]:
    for key,digest in phase17[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase17/browser-validation.json').read_bytes()).hexdigest()==phase17['browser_receipt_sha256']
phase16=json.loads((ROOT/'analysis/phase16/verification.json').read_text())
assert phase16['status']=='passed' and phase16['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase16[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase16_receipts={key:row['receipt_path'] for key,row in phase16['areas'].items()}
phase16_receipts['audio-genuine-call-inputs']='analysis/phase16/audio-requests/actual-callers.json'
phase16_receipts.update({'source-integration':phase16['source_integration_receipt_path'],'native':'analysis/phase16/runtime/validation.json'})
phase16_evidence={key:row['evidence_path'] for key,row in phase16['areas'].items()}
phase16_evidence.update({'native':phase16['native_evidence_path']})
for group,paths in [('receipt_sha256',phase16_receipts),('evidence_sha256',phase16_evidence)]:
    for key,digest in phase16[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase16/browser-validation.json').read_bytes()).hexdigest()==phase16['browser_receipt_sha256']
phase15=json.loads((ROOT/'analysis/phase15/verification.json').read_text())
assert phase15['status']=='passed' and phase15['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase15[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase15_receipts={key:row['receipt_path'] for key,row in phase15['areas'].items()}
phase15_receipts['audio-genuine-call-inputs']='analysis/phase15/audio-domain/writer-provenance.json'
phase15_receipts.update({'source-integration':phase15['source_integration_receipt_path'],'native':'analysis/phase15/runtime/validation.json'})
phase15_evidence={key:row['evidence_path'] for key,row in phase15['areas'].items()}
phase15_evidence.update({'native':phase15['native_evidence_path']})
for group,paths in [('receipt_sha256',phase15_receipts),('evidence_sha256',phase15_evidence)]:
    for key,digest in phase15[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase15/browser-validation.json').read_bytes()).hexdigest()==phase15['browser_receipt_sha256']
phase14=json.loads((ROOT/'analysis/phase14/verification.json').read_text())
assert phase14['status']=='passed' and phase14['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase14[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase14_receipts={key:row['receipt_path'] for key,row in phase14['areas'].items()}
phase14_receipts.update({'source-integration':phase14['source_integration_receipt_path'],'native':'analysis/phase14/runtime/validation.json'})
phase14_evidence={key:row['evidence_path'] for key,row in phase14['areas'].items()}
phase14_evidence.update({'native':phase14['native_evidence_path']})
for group,paths in [('receipt_sha256',phase14_receipts),('evidence_sha256',phase14_evidence)]:
    for key,digest in phase14[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase14/browser-validation.json').read_bytes()).hexdigest()==phase14['browser_receipt_sha256']
phase13=json.loads((ROOT/'analysis/phase13/verification.json').read_text())
assert phase13['status']=='passed' and phase13['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase13[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase13_receipts={key:row['receipt_path'] for key,row in phase13['areas'].items()}
phase13_receipts.update({'source-integration':phase13['source_integration_receipt_path'],
                        'native':'analysis/phase13/runtime/validation.json'})
phase13_evidence={key:row['evidence_path'] for key,row in phase13['areas'].items()}
phase13_evidence.update({'dependency-discovery':'analysis/phase13/dependencies/inventory.json',
                        'native':phase13['native_evidence_path']})
for group,paths in [('receipt_sha256',phase13_receipts),('evidence_sha256',phase13_evidence)]:
    for key,digest in phase13[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase13/browser-validation.json').read_bytes()).hexdigest()==phase13['browser_receipt_sha256']
phase12=json.loads((ROOT/'analysis/phase12/verification.json').read_text())
assert phase12['status']=='passed' and phase12['rebuilt_byte_identical']
for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
    for name,expected in phase12[group].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase12_receipts={key:row['receipt_path'] for key,row in phase12['areas'].items()}
phase12_receipts.update({'source-integration':phase12['source_integration_receipt_path'],
                        'native':'analysis/phase12/runtime/validation.json'})
phase12_evidence={key:row['evidence_path'] for key,row in phase12['areas'].items()}
phase12_evidence.update({'dependency-discovery':'analysis/phase12/dependencies/catalog.json',
                        'native':phase12['native_evidence_path']})
for group,paths in [('receipt_sha256',phase12_receipts),('evidence_sha256',phase12_evidence)]:
    for key,digest in phase12[group].items():
        assert hashlib.sha256((ROOT/paths[key]).read_bytes()).hexdigest()==digest,paths[key]
assert hashlib.sha256((ROOT/'analysis/phase12/browser-validation.json').read_bytes()).hexdigest()==phase12['browser_receipt_sha256']
phase11=json.loads((ROOT/'analysis/phase11/verification.json').read_text())
assert phase11['status']=='passed' and phase11['rebuilt_byte_identical']
for name,expected in phase11['source_and_validator_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase10=json.loads((ROOT/'analysis/phase10/verification.json').read_text())
assert phase10['status']=='passed' and phase10['rebuilt_byte_identical']
for name,expected in phase10['source_and_validator_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
phase9=json.loads((ROOT/'analysis/phase9/verification.json').read_text())
assert phase9['status']=='passed' and phase9['rebuilt_byte_identical']
for name,expected in phase9['source_and_validator_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
files=[ROOT/'README.md',ROOT/'requirements.txt',ROOT/'.gitignore']
for folder in ['scripts','source','analysis']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and not any(part.startswith('exploratory') for part in p.parts)
                 and p.name!='package-receipt.json')
files.append(ROOT/'build/三国志2超级版.rebuilt.nes')
target.parent.mkdir(parents=True,exist_ok=True)
with ZipFile(target,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(files):
        z.write(p,p.relative_to(ROOT).as_posix())
with ZipFile(target) as z:
    assert z.testzip() is None
    assert z.read('build/三国志2超级版.rebuilt.nes')==(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase17[group].items():
            if Path(name).parts[0]=='.toolchain':
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase17_receipts),('evidence_sha256',phase17_evidence)]:
        for key,digest in phase17[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase17/verification.json','analysis/phase17/index.html',
                 'analysis/phase17/README.md','analysis/phase17/browser-validation.json',
                 'analysis/phase17/browser-proof.png','analysis/phase17/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native17=json.loads(z.read('analysis/phase17/runtime/evidence.json'))
    artifact_checks17=0
    for row in native17['native_cases']:
        base='analysis/phase17/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact'];other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks17+=1
    assert len(native17['native_cases'])==3
    assert artifact_checks17==phase17['native']['nonempty_repeat_artifact_checks']==2429
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase16[group].items():
            if Path(name).parts[0]=='.toolchain':
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase16_receipts),('evidence_sha256',phase16_evidence)]:
        for key,digest in phase16[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase16/verification.json','analysis/phase16/index.html',
                 'analysis/phase16/README.md','analysis/phase16/browser-validation.json',
                 'analysis/phase16/browser-proof.png','analysis/phase16/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native16=json.loads(z.read('analysis/phase16/runtime/evidence.json'))
    artifact_checks16=0
    for row in native16['native_cases']:
        base='analysis/phase16/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact'];other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks16+=1
    assert len(native16['native_cases'])==4
    assert artifact_checks16==phase16['native']['nonempty_repeat_artifact_checks']==1076
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase15[group].items():
            if Path(name).parts[0]=='.toolchain':
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase15_receipts),('evidence_sha256',phase15_evidence)]:
        for key,digest in phase15[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase15/verification.json','analysis/phase15/index.html',
                 'analysis/phase15/README.md','analysis/phase15/browser-validation.json',
                 'analysis/phase15/browser-proof.png','analysis/phase15/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native15=json.loads(z.read('analysis/phase15/runtime/evidence.json'))
    artifact_checks15=0
    for row in native15['native_cases']:
        base='analysis/phase15/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact'];other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks15+=1
    assert len(native15['native_cases'])==4
    assert artifact_checks15==phase15['native']['nonempty_repeat_artifact_checks']
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase14[group].items():
            if Path(name).parts[0]=='.toolchain':
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase14_receipts),('evidence_sha256',phase14_evidence)]:
        for key,digest in phase14[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase14/verification.json','analysis/phase14/index.html',
                 'analysis/phase14/README.md','analysis/phase14/browser-validation.json',
                 'analysis/phase14/browser-proof.png','analysis/phase14/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native14=json.loads(z.read('analysis/phase14/runtime/evidence.json'))
    artifact_checks14=0
    for row in native14['native_cases']:
        base='analysis/phase14/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact'];other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks14+=1
    assert artifact_checks14==phase14['native']['nonempty_repeat_artifact_checks']==864
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase13[group].items():
            if Path(name).parts[0]=='.toolchain':
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase13_receipts),('evidence_sha256',phase13_evidence)]:
        for key,digest in phase13[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase13/verification.json','analysis/phase13/index.html',
                 'analysis/phase13/README.md','analysis/phase13/browser-validation.json',
                 'analysis/phase13/browser-proof.png','analysis/phase13/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native13=json.loads(z.read('analysis/phase13/runtime/evidence.json'))
    artifact_checks13=0
    for row in native13['native_cases']:
        base='analysis/phase13/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact'];other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks13+=1
    assert artifact_checks13==phase13['native']['nonempty_repeat_artifact_checks']==204
    for group in ('source_and_validator_sha256','artifact_and_dependency_sha256'):
        for name,expected in phase12[group].items():
            if Path(name).parts[0]=='.toolchain':
                # The core hash is verified on disk; executable runtimes are
                # deliberately excluded from this source/evidence archive.
                assert name not in z.namelist(),name
                continue
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for group,paths in [('receipt_sha256',phase12_receipts),('evidence_sha256',phase12_evidence)]:
        for key,digest in phase12[group].items():
            name=paths[key]
            assert z.read(name)==(ROOT/name).read_bytes(),name
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    for name in ['analysis/phase12/verification.json','analysis/phase12/index.html',
                 'analysis/phase12/README.md','analysis/phase12/browser-validation.json',
                 'analysis/phase12/browser-proof.png','analysis/phase12/runtime/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    native12=json.loads(z.read('analysis/phase12/runtime/evidence.json'))
    artifact_checks12=0
    for row in native12['native_cases']:
        base='analysis/phase12/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact']
            other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks12+=1
    assert artifact_checks12==phase12['native']['nonempty_repeat_artifact_checks']==200
    for name,expected in phase11['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase11/verification.json','analysis/phase11/source-integration.json',
                 'analysis/phase11/browser-validation.json','analysis/phase11/browser-proof.png',
                 'analysis/phase11/index.html','analysis/phase11/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for area,expected in phase11['receipt_sha256'].items():
        name={'source-integration':'analysis/phase11/source-integration.json',
              'native':'analysis/phase11/runtime/validation.json'}.get(area,f'analysis/phase11/{area}/validation.json')
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area,expected in phase11['evidence_sha256'].items():
        name='analysis/phase11/runtime/evidence.json'if area=='native'else f'analysis/phase11/{area}/evidence.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    native=json.loads(z.read('analysis/phase11/runtime/evidence.json'))
    for row in native['native_cases']:
        base='analysis/phase11/runtime/'+row['case']
        repeated=json.loads(z.read(base+'/repeat-validation.json'))
        for artifact in repeated['artifacts']:
            name=base+'/'+artifact['artifact']
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            other=repeated['second_run']+'/'+artifact['artifact']
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
    phase5=json.loads((ROOT/'analysis/phase5/verification.json').read_text())
    assert phase5['status']=='passed'
    # The ZIP must contain exactly the verified source, not an older package copy.
    for name,expected in phase5['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase5/verification.json','analysis/phase5/source-integration.json',
                 'analysis/phase5/index.html','analysis/phase5/README.md']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    phase6=json.loads((ROOT/'analysis/phase6/verification.json').read_text())
    assert phase6['status']=='passed'
    for name,expected in phase6['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase6/verification.json','analysis/phase6/source-integration.json',
                 'analysis/phase6/index.html','analysis/phase6/README.md',
                 'analysis/phase6/global/program.json','analysis/phase6/global/state-catalog.json',
                 'analysis/phase6/factions/ending-program.json','source/README.md','analysis/index.html']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for area,expected in phase6['receipt_sha256'].items():
        name=f'analysis/phase6/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area in ('messages','ownership-commit','unification-ending'):
        replay=json.loads(z.read(f'analysis/phase6/runtime/{area}/repeat-validation.json'))
        for artifact in replay['artifacts']:
            name=f'analysis/phase6/runtime/{area}/{artifact["path"]}'
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
    phase7=json.loads((ROOT/'analysis/phase7/verification.json').read_text())
    assert phase7['status']=='passed'
    for name,expected in phase7['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase7/verification.json','analysis/phase7/source-integration.json',
                 'analysis/phase7/index.html','analysis/phase7/README.md',
                 'analysis/phase7/controller/program.json','analysis/phase7/controller/state-catalog.json',
                 'analysis/phase7/decisions/evidence.json','analysis/phase7/secondary-origin.json',
                 'analysis/phase7/browser-validation.json']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for area,expected in phase7['receipt_sha256'].items():
        name=f'analysis/phase7/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    assert hashlib.sha256(z.read('analysis/phase7/secondary-origin.json')).hexdigest()==phase7['secondary_origin_sha256']
    for area in ('natural-turn','cpu-call'):
        replay=json.loads(z.read(f'analysis/phase7/runtime/{area}/repeat-validation.json'))
        for artifact in replay['artifacts']:
            name=f'analysis/phase7/runtime/{area}/{artifact["artifact"]}'
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
    phase8=json.loads((ROOT/'analysis/phase8/verification.json').read_text())
    assert phase8['status']=='passed' and phase8['rebuilt_byte_identical']
    for name,expected in phase8['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase8/verification.json','analysis/phase8/source-integration.json',
                 'analysis/phase8/index.html','analysis/phase8/README.md',
                 'analysis/phase8/browser-validation.json','analysis/phase8/browser-proof.png',
                 'analysis/phase8/runtime/README.md','analysis/phase8/runtime/evidence.json',
                 'source/README.md','README.md','analysis/index.html']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for area,expected in phase8['receipt_sha256'].items():
        name=f'analysis/phase8/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area,expected in phase8['evidence_sha256'].items():
        name=f'analysis/phase8/{area}/evidence.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area in ('ambush-chain','ordinary-cast','cpu-call','cpu-expiry'):
        name=f'analysis/phase8/runtime/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==phase8['runtime_validation_sha256'][area],name
        replay=json.loads(z.read(f'analysis/phase8/runtime/{area}/repeat-validation.json'))
        for artifact in replay['artifacts']:
            name=f'analysis/phase8/runtime/{area}/{artifact["artifact"]}'
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
    assert phase9['fully_recovered_effect_ids']==list(range(16)) and not phase9['external_effect_ids']
    for name,expected in phase9['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase9/verification.json','analysis/phase9/source-integration.json',
                 'analysis/phase9/index.html','analysis/phase9/README.md',
                 'analysis/phase9/browser-validation.json','analysis/phase9/browser-proof.png',
                 'analysis/phase9/runtime/README.md','analysis/phase9/runtime/evidence.json',
                 'analysis/phase9/runtime/validation.json','analysis/phase9/settlement/README.md',
                 'analysis/phase9/settlement/original-ranges.asm']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for area,expected in phase9['receipt_sha256'].items():
        name=f'analysis/phase9/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area,expected in phase9['evidence_sha256'].items():
        name=f'analysis/phase9/{area}/evidence.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    for area,expected in phase9['runtime_validation_sha256'].items():
        name=f'analysis/phase9/runtime/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        replay=json.loads(z.read(f'analysis/phase9/runtime/{area}/repeat-validation.json'))
        for artifact in replay['artifacts']:
            name=f'analysis/phase9/runtime/{area}/{artifact["artifact"]}'
            other=f'{replay["second_run"]}/{artifact["artifact"]}'
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0,name
            assert hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
        name=f'analysis/phase9/runtime/{area}/frame-fields.json'
        other=f'{replay["second_run"]}/frame-fields.json'
        assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
    assert not any(any(part.startswith('exploratory')for part in Path(name).parts)for name in z.namelist())
    for name,expected in phase10['source_and_validator_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for name in ['analysis/phase10/verification.json','analysis/phase10/source-integration.json',
                 'analysis/phase10/terrain-validation.json','analysis/phase10/index.html','analysis/phase10/README.md',
                 'analysis/phase10/browser-validation.json','analysis/phase10/browser-proof.png',
                 'analysis/phase10/runtime/README.md','analysis/phase10/runtime/evidence.json','analysis/phase10/runtime/validation.json']:
        assert z.read(name)==(ROOT/name).read_bytes(),name
    for key,filename in [('receipt_sha256','validation.json'),('evidence_sha256','evidence.json')]:
        for area,expected in phase10[key].items():
            name=f'analysis/phase10/{area}/{filename}'
            assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
    artifact_checks=0
    for area,expected in phase10['runtime_validation_sha256'].items():
        name=f'analysis/phase10/runtime/{area}/validation.json'
        assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
        replay=json.loads(z.read(f'analysis/phase10/runtime/{area}/repeat-validation.json'))
        for artifact in replay['artifacts']:
            name=f'analysis/phase10/runtime/{area}/{artifact["artifact"]}'
            other=f'{replay["second_run"]}/{artifact["artifact"]}'
            assert z.read(name)==z.read(other)==(ROOT/name).read_bytes(),name
            assert len(z.read(name))==artifact['bytes']>0 and hashlib.sha256(z.read(name)).hexdigest()==artifact['sha256'],name
            artifact_checks+=1
    assert artifact_checks==phase10['repeat_artifact_checks']==392
    count=len(z.namelist())
receipt={'path':str(target),'file_count':count,'archive_bytes':target.stat().st_size,
         'phase17_verified_source_archive_parity':'passed',
         'phase17_rom_cpu_cases':phase17['rom_cpu_case_count'],
         'phase17_source_guard_cases':phase17['source_guard_case_count'],
         'phase17_integration_rom_cpu_cases':phase17['integration_rom_cpu_case_count'],
         'phase17_native_summary':native17['summary'],
         'phase17_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase17['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase17_verification_sha256':hashlib.sha256((ROOT/'analysis/phase17/verification.json').read_bytes()).hexdigest(),
         'phase16_verified_source_archive_parity':'passed',
         'phase16_rom_cpu_cases':phase16['rom_cpu_case_count'],
         'phase16_source_guard_cases':phase16['source_guard_case_count'],
         'phase16_integration_rom_cpu_cases':phase16['integration_rom_cpu_case_count'],
         'phase16_native_summary':native16['summary'],
         'phase16_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase16['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase16_verification_sha256':hashlib.sha256((ROOT/'analysis/phase16/verification.json').read_bytes()).hexdigest(),
         'phase15_verified_source_archive_parity':'passed',
         'phase15_rom_cpu_cases':phase15['rom_cpu_case_count'],
         'phase15_source_guard_cases':phase15['source_guard_case_count'],
         'phase15_integration_rom_cpu_cases':phase15['integration_rom_cpu_case_count'],
         'phase15_native_summary':native15['summary'],
         'phase15_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase15['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase15_verification_sha256':hashlib.sha256((ROOT/'analysis/phase15/verification.json').read_bytes()).hexdigest(),
         'phase14_verified_source_archive_parity':'passed',
         'phase14_rom_cpu_cases':phase14['rom_cpu_case_count'],
         'phase14_source_guard_cases':phase14['source_guard_case_count'],
         'phase14_integration_rom_cpu_cases':phase14['integration_rom_cpu_case_count'],
         'phase14_native_summary':native14['summary'],
         'phase14_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase14['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase14_verification_sha256':hashlib.sha256((ROOT/'analysis/phase14/verification.json').read_bytes()).hexdigest(),
         'phase13_verified_source_archive_parity':'passed',
         'phase13_rom_cpu_cases':phase13['rom_cpu_case_count'],
         'phase13_source_guard_cases':phase13['source_guard_case_count'],
         'phase13_integration_rom_cpu_cases':phase13['integration_rom_cpu_case_count'],
         'phase13_native_summary':native13['summary'],
         'phase13_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase13['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase13_verification_sha256':hashlib.sha256((ROOT/'analysis/phase13/verification.json').read_bytes()).hexdigest(),
         'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'zip_crc_check':'passed',
         'phase12_verified_source_archive_parity':'passed',
         'phase12_rom_cpu_cases':phase12['rom_cpu_case_count'],
         'phase12_source_guard_cases':phase12['source_guard_case_count'],
         'phase12_integration_rom_cpu_cases':phase12['integration_rom_cpu_case_count'],
         'phase12_native_summary':native12['summary'],
         'phase12_verified_runtime_dependencies_excluded':{name:digest for name,digest in phase12['artifact_and_dependency_sha256'].items() if Path(name).parts[0]=='.toolchain'},
         'phase12_verification_sha256':hashlib.sha256((ROOT/'analysis/phase12/verification.json').read_bytes()).hexdigest(),
         'phase11_verified_source_archive_parity':'passed',
         'phase11_rom_cpu_cases':phase11['rom_cpu_case_count'],
         'phase11_source_guard_cases':phase11['source_guard_case_count'],
         'phase11_native_summary':native['summary'],
         'phase11_verification_sha256':hashlib.sha256((ROOT/'analysis/phase11/verification.json').read_bytes()).hexdigest(),
         'phase5_verified_source_archive_parity':'passed',
         'phase6_verified_source_archive_parity':'passed',
         'phase6_rom_cpu_comparison_count':phase6['rom_cpu_comparison_count'],
         'phase6_source_only_guard_count':phase6['source_only_guard_count'],
         'phase6_integration_checks':phase6['integration_case_count'],
         'phase6_repeat_artifact_checks':phase6['original_core_repeat_artifact_checks'],
         'phase6_verification_sha256':hashlib.sha256((ROOT/'analysis/phase6/verification.json').read_bytes()).hexdigest(),
         'phase7_verified_source_archive_parity':'passed',
         'phase7_rom_cpu_cases':phase7['rom_cpu_case_count'],
         'phase7_source_guard_cases':phase7['source_guard_case_count'],
         'phase7_integration_checks':phase7['integration_case_count'],
         'phase7_repeat_artifact_checks':phase7['repeat_artifact_checks'],
         'phase7_verification_sha256':hashlib.sha256((ROOT/'analysis/phase7/verification.json').read_bytes()).hexdigest(),
         'phase8_verified_source_archive_parity':'passed',
         'phase8_rom_cpu_cases':phase8['rom_cpu_case_count'],
         'phase8_source_guard_cases':phase8['source_guard_case_count'],
         'phase8_integration_rom_cpu_cases':phase8['integration_rom_cpu_case_count'],
         'phase8_native_core_field_checks':phase8['native_core_field_comparison_count'],
         'phase8_native_core_frames':phase8['native_core_frame_count'],
         'phase8_repeat_artifact_checks':phase8['repeat_artifact_checks'],
         'phase8_verification_sha256':hashlib.sha256((ROOT/'analysis/phase8/verification.json').read_bytes()).hexdigest(),
         'phase9_verified_source_archive_parity':'passed',
         'phase9_rom_cpu_cases':phase9['rom_cpu_case_count'],
         'phase9_source_guard_cases':phase9['source_guard_case_count'],
         'phase9_integration_rom_cpu_cases':phase9['integration_rom_cpu_case_count'],
         'phase9_integration_source_guard_cases':phase9['integration_source_guard_case_count'],
         'phase9_native_core_field_checks':phase9['native_core_field_comparison_count'],
         'phase9_native_core_cases':phase9['native_core_case_count'],
         'phase9_native_core_frames':phase9['native_core_frame_count'],
         'phase9_repeat_artifact_checks':phase9['repeat_artifact_checks'],
         'phase9_verification_sha256':hashlib.sha256((ROOT/'analysis/phase9/verification.json').read_bytes()).hexdigest(),
         'phase10_verified_source_archive_parity':'passed',
         'phase10_rom_cpu_cases':phase10['rom_cpu_case_count'],
         'phase10_source_guard_cases':phase10['source_guard_case_count'],
         'phase10_integration_rom_cpu_cases':phase10['integration_rom_cpu_case_count'],
         'phase10_terrain_rom_cpu_cases':phase10['terrain_rom_cpu_case_count'],
         'phase10_native_core_cases':phase10['native_core_case_count'],
         'phase10_native_core_frames':phase10['native_core_frame_count'],
         'phase10_repeat_artifact_checks':phase10['repeat_artifact_checks'],
         'phase10_PCM_stereo_sample_frames_full':phase10['PCM_stereo_sample_frames_full'],
         'phase10_verification_sha256':hashlib.sha256((ROOT/'analysis/phase10/verification.json').read_bytes()).hexdigest(),
         'phase5_rom_differential_cases':phase5['rom_differential_case_count'],
         'phase5_verification_sha256':hashlib.sha256((ROOT/'analysis/phase5/verification.json').read_bytes()).hexdigest(),
         'includes':['analysis','scripts','source','README','6502 adapter patch','byte-identical rebuilt ROM'],
         'excludes':['Ghidra toolchain','node_modules','Python environments','exploratory results']}
(ROOT/'analysis/package-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
