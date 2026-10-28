"""Exact native castle capture/crop provenance, without ROM or emulation."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('original_siege_checker',ROOT/'tools/siege-original/check.py')
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
spec=importlib.util.spec_from_file_location('siege_asset_server',ROOT/'game/serve.py')
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def png_bytes(pixels,width,height):
    def chunk(kind,raw):
        return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
    rows=b''.join(b'\0'+pixels[y*width*4:(y+1)*width*4]for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')


class OriginalSiegeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((checker.OUT/'index.json').read_text())
        cls.files={checker.PREFIX+p.name:p.read_bytes()for p in checker.OUT.iterdir()}

    def validate(self,data=None,changes=None):
        files={**self.files,**(changes or {})}
        return checker.validate(self.data if data is None else data,files.__getitem__)

    def test_all_shipped_native_pixels_are_exact_and_do_not_require_original_inputs(self):
        report=checker.check()
        self.assertEqual(report['formations'],6)
        self.assertEqual(report['castle_wall_cells'],18)
        self.assertEqual(report['table_bytes'],549)
        self.assertEqual(report['pngs'],56)
        self.assertEqual(report['exact4x'],21)
        self.assertEqual(report['clean_native_sprites'],8)
        self.assertEqual(report['difference_candidates_not_sprites'],13)
        self.assertFalse(report['checker_requires_rom'])
        self.assertGreater(report['pixels_checked'],1000000)
        for forbidden in ('.nes','.state','.bin','.dylib'):
            self.assertFalse(any(p.name.endswith(forbidden)for p in checker.OUT.iterdir()))
        source=(ROOT/'tools/siege-original/check.py').read_text()
        self.assertNotIn('from PIL',source)
        self.assertNotIn('import PIL',source)

    def test_capture_witness_cannot_claim_natural_play_or_hide_fixture_changes(self):
        for key,value in [('controlled_fixture',False),('natural_gameplay',True),('rom_sha256','0'*64),('runtime_requires_rom',True)]:
            with self.subTest(key=key):
                data=deepcopy(self.data);data[key]=value
                with self.assertRaises(ValueError):self.validate(data)
        for row in self.data['source_provenance']:
            value=json.loads(self.files[row['path']]);self.assertFalse(value['rom_modified'])
            self.assertNotIn('/Users/',json.dumps(value));self.assertNotIn('/tmp/',json.dumps(value))
        self.assertEqual(len(json.loads(self.files[self.data['source_provenance'][0]['path']])['changes']),6)

    def test_static_allowlist_contains_every_declared_image_and_data_file_only(self):
        actual=server.siege_static_assets(ROOT/'game')
        self.assertEqual(set(actual),set(self.files))
        for path,(relative,mime)in actual.items():
            self.assertEqual(relative,path.lstrip('/'))
            self.assertEqual(mime,'image/png'if path.endswith('.png')else'application/json; charset=utf-8')
        self.assertFalse(any(path.endswith(('.nes','.state','.bin','.dylib'))for path in actual))

    def test_native_crop_must_match_captured_pixels_even_with_a_new_hash(self):
        data=deepcopy(self.data);row=data['assets']['formation-0'];raw=self.files[row['path']]
        actual=bytearray(checker.pixels(raw,(row['width'],row['height'])));actual[0]^=255
        changed=png_bytes(actual,row['width'],row['height']);row['sha256']=checker.sha(changed)
        with self.assertRaisesRegex(ValueError,'Native crop/derivative pixel mismatch'):
            self.validate(data,{row['path']:changed})

    def test_fourfold_background_must_repeat_each_source_pixel_exactly(self):
        data=deepcopy(self.data);row=data['assets']['siege-background-4x'];raw=self.files[row['path']]
        actual=bytearray(checker.pixels(raw,(1024,640)));actual[(10*1024+10)*4]^=1
        changed=png_bytes(actual,1024,640);row['sha256']=checker.sha(changed)
        with self.assertRaisesRegex(ValueError,'Native crop/derivative pixel mismatch'):
            self.validate(data,{row['path']:changed})

    def test_difference_candidates_cannot_be_mislabeled_as_clean_runtime_sprites(self):
        names=[key for key,row in self.data['assets'].items()if row.get('classification')=='retained-background-difference-candidate']
        self.assertEqual(len(names),13)
        for key in names:
            row=self.data['assets'][key];self.assertFalse(row['clean_sprite_verified']);self.assertFalse(row['runtime_eligible'])
        for key in ['siege-piece-enemy-general','siege-formation-enemy-0']:
            with self.subTest(key=key):
                data=deepcopy(self.data);data['assets'][key]['runtime_eligible']=True;data['assets'][key]['clean_sprite_verified']=True
                with self.assertRaisesRegex(ValueError,'cannot be advertised'):
                    self.validate(data)

    def test_original_pattern_transparency_preserves_armor_with_the_same_gray_rgb(self):
        row=self.data['assets']['native-sprite-general-friendly']
        pixels=checker.pixels(self.files[row['path']],(16,16))
        gray=(167,181,188)
        opaque_gray=sum(tuple(pixels[i:i+3])==gray and pixels[i+3]==255 for i in range(0,len(pixels),4))
        transparent_gray=sum(tuple(pixels[i:i+3])==gray and pixels[i+3]==0 for i in range(0,len(pixels),4))
        self.assertGreater(opaque_gray,0,'Original gray armor is a distinct non-background pattern index')
        self.assertGreater(transparent_gray,0,'Original gray ground must become transparent')
        for key in checker.CHR_HASHES:
            row=self.data['assets'][key];self.assertTrue(row['clean_sprite_verified'])
            alpha=checker.pixels(self.files[row['path']],(16,16))[3::4]
            self.assertEqual(set(alpha),{0,255})

    def test_native_chr_and_transparency_cannot_be_invented_with_new_hashes(self):
        data=deepcopy(self.data);row=data['assets']['native-sprite-general-friendly'];operation=row['source']['operations'][0]
        operation['transparent_index']=3
        with self.assertRaisesRegex(ValueError,'Wrong original background pattern index'):
            self.validate(data)
        data=deepcopy(self.data);operation=data['assets']['native-sprite-general-friendly']['source']['operations'][0]
        tile=operation['tiles'][0];raw=bytearray.fromhex(tile['hex']);raw[0]^=1;tile['hex']=raw.hex();tile['sha256']=checker.sha(raw)
        operation['chr_composite_sha256']=checker.sha(b''.join(bytes.fromhex(tile['hex'])for tile in operation['tiles']))
        with self.assertRaisesRegex(ValueError,'Unverified native CHR composite'):
            self.validate(data)

    def test_native_tables_reject_a_formation_edit_even_if_file_is_rehashed(self):
        data=deepcopy(self.data);data['tables']['formations'][0]['x'][0]=2
        table=data['data']['native_tables'];raw=(json.dumps(data['tables'])+'\n').encode();table['sha256']=checker.sha(raw)
        with self.assertRaisesRegex(ValueError,'Formation differs from native source table'):
            self.validate(data,{table['path']:raw})
        data=deepcopy(self.data);data['tables']['castle_layout']['classes'][0][0]=5
        table=data['data']['native_tables'];raw=(json.dumps(data['tables'])+'\n').encode();table['sha256']=checker.sha(raw)
        with self.assertRaisesRegex(ValueError,'collision classes differ'):
            self.validate(data,{table['path']:raw})

    def test_pinned_table_chunk_cannot_be_replaced_with_self_consistent_forged_data(self):
        tables=deepcopy(self.data['tables']);row=tables['source_chunks']['formation_x']
        raw=bytearray.fromhex(row['hex']);raw[0]^=1;row['hex']=raw.hex();row['sha256']=checker.sha(raw)
        with self.assertRaisesRegex(ValueError,'Native source chunk changed'):
            checker.validate_tables(tables)

    def test_capture_bytes_hash_and_source_output_hash_must_both_match(self):
        data=deepcopy(self.data);row=data['captures']['capture-prelude1.png'];raw=bytearray(self.files[row['path']]);raw[-5]^=1
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            self.validate(data,{row['path']:bytes(raw)})
        data=deepcopy(self.data);row=data['captures']['capture-prelude1.png'];row['sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            self.validate(data)

    def test_unsafe_sources_unknown_operations_and_outside_rectangles_are_refused(self):
        for path in ['/tmp/private.png','/assets/siege-original/../private.png','https://example.com/a.png','/assets/siege-original/sub/a.png']:
            with self.subTest(path=path):
                data=deepcopy(self.data);data['assets']['formation-0']['source']['screenshot']=path
                with self.assertRaises(ValueError):self.validate(data)
        for patch in [{'operations':[{'kind':'generated_inpainting'}]},{'source_rect':[0,0,257,240]}]:
            with self.subTest(patch=patch):
                data=deepcopy(self.data);data['assets']['formation-0']['source'].update(patch)
                with self.assertRaises(ValueError):self.validate(data)

    def test_symlinks_unlisted_files_and_wrong_dimensions_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            link=Path(folder)/'linked';link.symlink_to(checker.OUT,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                checker.check(link)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'listed.png').symlink_to(checker.OUT/'formation-0.png')
            with self.assertRaisesRegex(ValueError,'Symlink'):
                checker.safe_read(path,checker.PREFIX+'listed.png')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            for source in checker.OUT.iterdir():
                (path/source.name).write_bytes(source.read_bytes())
            (path/'unlisted.png').write_bytes(b'not a manifest asset')
            with self.assertRaisesRegex(ValueError,'Unexpected or missing'):
                checker.check(path)
        raw=self.files[self.data['assets']['formation-0']['path']]
        with self.assertRaises(ValueError):checker.pixels(raw,(32,33))


if __name__=='__main__':unittest.main()
