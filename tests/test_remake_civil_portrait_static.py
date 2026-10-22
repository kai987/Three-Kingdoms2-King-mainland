"""Civil HD sprites have an exact static allowlist and retained native files."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('civil_portrait_server',ROOT/'game/serve.py')
serve=importlib.util.module_from_spec(spec);spec.loader.exec_module(serve)
spec=importlib.util.spec_from_file_location('civil_portrait_png',ROOT/'game/build_portrait_manifest.py')
png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)


class CivilPortraitStaticTests(unittest.TestCase):
    def prepare(self,folder,metadata=None):
        here=Path(folder)/'game';base=here/'assets/civil-staff/enhanced';base.mkdir(parents=True)
        value=metadata or dict(schema='tk2-civil-portraits-v1',width=128,height=160,
            portraits={'clerk-1':dict(path='/assets/civil-staff/enhanced/clerk-1.png',width=128,height=160)})
        (base/'index.json').write_text(json.dumps(value));(base/'clerk-1.png').write_bytes(b'fixture PNG')
        return here,base

    def test_three_shipped_variants_match_source_and_output_hashes_and_dimensions(self):
        base=ROOT/'game/assets/civil-staff/enhanced';data=json.loads((base/'index.json').read_text())
        self.assertTrue(data['originals_retained']);self.assertEqual(data['shared_templates'],3)
        self.assertEqual(set(data['portraits']),{'clerk-1','clerk-2','clerk-3'})
        for key,row in data['portraits'].items():
            original=ROOT/'game'/row['source_path'].lstrip('/');enhanced=ROOT/'game'/row['path'].lstrip('/')
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),row['source_sha256'])
            self.assertEqual(hashlib.sha256(enhanced.read_bytes()).hexdigest(),row['sha256'])
            self.assertEqual(png.png_pixels(original.read_bytes(),(32,40))[0],(32,40))
            size,pixels=png.png_pixels(enhanced.read_bytes(),(128,160));self.assertEqual(size,(128,160))
            self.assertEqual(hashlib.sha256(pixels).hexdigest(),row['pixel_sha256'])
            self.assertLessEqual(row['qa']['palette_size'],16);self.assertEqual(row['qa']['alpha_changes'],0)
        paths=serve.civil_portrait_static_assets(ROOT/'game')
        self.assertEqual(set(paths),{'/assets/civil-staff/enhanced/index.json'}|{row['path']for row in data['portraits'].values()})

    def test_wrong_names_paths_sizes_and_unlisted_files_are_never_public(self):
        for replacement in ('/assets/civil-staff/enhanced/../clerk-1.png','/assets/civil-staff/enhanced/clerk-2.png',
                            '/assets/civil-staff/enhanced/clerk-1.png?x=1','/assets/civil-staff/enhanced/clerk-1.svg',
                            'https://example.com/a.png'):
            with self.subTest(path=replacement),tempfile.TemporaryDirectory() as folder:
                data=dict(schema='tk2-civil-portraits-v1',width=128,height=160,portraits={'clerk-1':dict(path=replacement,width=128,height=160),'clerk-4':dict(path='/assets/civil-staff/enhanced/clerk-4.png',width=128,height=160)})
                here,base=self.prepare(folder,data);(base/'clerk-4.png').write_bytes(b'not allowed')
                self.assertEqual(set(serve.civil_portrait_static_assets(here)),{'/assets/civil-staff/enhanced/index.json'})

    def test_symlinks_are_rejected_at_registration_and_after_registration(self):
        for target in ('clerk-1.png','index.json','enhanced','civil-staff','assets'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as folder:
                here,base=self.prepare(folder);assets=serve.civil_portrait_static_assets(here)
                selected=base/target if target in ('clerk-1.png','index.json')else base if target=='enhanced' else base.parent if target=='civil-staff' else here/'assets'
                destination=Path(folder)/('moved-'+target);selected.rename(destination);selected.symlink_to(destination,target_is_directory=destination.is_dir())
                self.assertNotIn('/assets/civil-staff/enhanced/clerk-1.png',serve.civil_portrait_static_assets(here))
                url='/assets/civil-staff/enhanced/'+('index.json'if target=='index.json'else'clerk-1.png')
                with self.assertRaises(FileNotFoundError):serve.static_file_bytes(here,assets[url][0])

    def test_missing_or_invalid_manifest_never_scans_directory(self):
        for value in ('{',json.dumps([]),json.dumps({'schema':'other'})):
            with tempfile.TemporaryDirectory() as folder:
                here,base=self.prepare(folder);(base/'index.json').write_text(value)
                self.assertNotIn('/assets/civil-staff/enhanced/clerk-1.png',serve.civil_portrait_static_assets(here))


if __name__=='__main__':unittest.main()
