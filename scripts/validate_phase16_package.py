#!/usr/bin/env python3
"""Check the exact ZIP allowlist and extraction, then preserve version16."""
from pathlib import Path
from zipfile import ZipFile
import hashlib,json,shutil,tempfile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    canonical=ROOT/'build/三国志2超级版-逆向分析.zip'
    version=ROOT/'build/三国志2超级版-逆向分析-v16.zip'
    prior=ROOT/'build/三国志2超级版-逆向分析-v15.zip'
    assert sha(prior)=='61ae5cd75614806ea3fa05fc94a23094443555b622947e635ad24fdece973a5b'
    expected={n for n in ['README.md','requirements.txt','.gitignore','build/三国志2超级版.rebuilt.nes']}
    for folder in ['scripts','source','analysis']:
        expected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts
                        and not any(part.startswith('exploratory') for part in p.parts)
                        and p.name!='package-receipt.json')
    critical={p.relative_to(ROOT).as_posix() for p in (ROOT/'analysis/phase16/succession/actual-callee-inputs').glob('*') if p.is_file()}
    critical.update('source/recovered/'+n for n in ['field_semantics.py','battle_succession.py','exact_audio_requests.py',
                    'postbattle_graphics.py','postbattle_loyalty_bridge.py','integrated_scene_services.py','game_engine.py','scene_coordinator.py'])
    critical.update('analysis/phase16/'+n for n in ['README.md','verification.json','source-integration.json',
                    'index.html','browser-validation.json','browser-proof.png','runtime/evidence.json','runtime/validation.json'])
    critical.add('build/三国志2超级版.rebuilt.nes')
    assert len(critical)>=66
    with ZipFile(canonical) as z:
        names=z.namelist();assert len(names)==len(set(names)) and set(names)==expected
        assert z.testzip() is None
        for name in names:
            assert not set(Path(name).parts)&{'.toolchain','.venv','.venv-trace','node_modules','__pycache__'}
            assert '..' not in Path(name).parts and not Path(name).is_absolute()
        source_checks=0
        for name in names:
            if name.startswith('source/'):
                assert z.read(name)==(ROOT/name).read_bytes(),name;source_checks+=1
        with tempfile.TemporaryDirectory(prefix='three-kingdoms-phase16-extraction-') as directory:
            for name in sorted(critical):
                extracted=Path(z.extract(name,directory));assert sha(extracted)==sha(ROOT/name),name
    digest=sha(canonical)
    if version.exists():assert sha(version)==digest
    else:shutil.copy2(canonical,version)
    assert sha(version)==digest
    receipt_path=ROOT/'analysis/package-receipt.json'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['sha256']==digest and receipt['phase16_verified_source_archive_parity']=='passed'
    receipt.update(version=16,versioned_path=str(version),exact_allowlist_check='passed',
                   duplicate_path_check='passed',forbidden_entries_check='passed',
                   all_source_file_parity_checks=source_checks,
                   temporary_extraction_critical_file_checks=len(critical),
                   v15_preserved_sha256=sha(prior),canonical_versioned_byte_parity='passed',
                   final_validator_path='scripts/validate_phase16_package.py',
                   final_validator_sha256=sha(Path(__file__)))
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['version','file_count','archive_bytes','sha256','all_source_file_parity_checks','temporary_extraction_critical_file_checks','exact_allowlist_check']},ensure_ascii=False))

if __name__=='__main__':main()
