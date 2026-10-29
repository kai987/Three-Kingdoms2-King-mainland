"""Original tactical flags are exact retained pixels, not browser font glyphs."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('original_marker_checker',ROOT/'tools/battle-markers-original/check.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class OriginalBattleMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files={checker.PREFIX+p.name:p.read_bytes()for p in checker.OUT.iterdir()}
        cls.files[checker.WITNESS]=(ROOT/'game/assets/battle-original/witness-tactical.png').read_bytes()
        cls.data=json.loads(cls.files[checker.PREFIX+'index.json'])

    def validate(self,data=None,changes=None):
        return checker.validate(self.data if data is None else data,{**self.files,**(changes or {})}.__getitem__)

    def proof_change(self,edit):
        data=deepcopy(self.data);proof=json.loads(self.files[data['provenance']['path']]);edit(proof)
        blob=(json.dumps(proof)+'\n').encode();data['provenance']['sha256']=checker.sha(blob)
        return data,{data['provenance']['path']:blob}

    def test_all_three_armies_zero_to_ten_and_both_commanders_are_exact(self):
        result=checker.check()
        self.assertEqual((result['frames'],result['cpu_cases']),(132,132))
        self.assertEqual(result['native_size'],[16,16]);self.assertEqual(result['atlas'],[704,768])
        self.assertTrue(result['exact4x']);self.assertEqual(result['native_callback_pixels'],256)
        self.assertFalse(result['checker_requires_rom']);self.assertFalse(result['checker_requires_emulator'])
        self.assertEqual({p.name for p in checker.OUT.iterdir()},checker.FILES)

    def test_white_black_army_glyphs_and_native_commander_badge_are_retained(self):
        native=checker.pixels(self.files[self.data['native_atlas']['path']],(176,192));ours=[]
        for army in range(3):
            row=self.data['frames'][f'friendly:{army}:10'];rect=[v//4 for v in row['source_rect']]
            raw=checker.crop(native,176,rect);ours.append(raw)
            self.assertEqual({tuple(raw[i:i+3])for i in range(0,len(raw),4)},{(0,0,0),(255,255,255)})
            commander=self.data['frames'][f'friendly:{army}:10:commander'];marked=checker.crop(native,176,[v//4 for v in commander['source_rect']])
            self.assertNotEqual(raw,marked);self.assertEqual(raw[16*8*4:],marked[16*8*4:],'Commander badge cannot alter the army glyph')
        self.assertEqual(len(set(ours)),3)

    def test_missing_swapped_or_unknown_frame_is_rejected(self):
        for edit in ('missing','swap','unknown','bool'):
            data=deepcopy(self.data)
            if edit=='missing':del data['frames']['friendly:0:1']
            elif edit=='swap':data['frames']['friendly:0:1']['source_rect']=[0,0,64,64]
            elif edit=='unknown':data['frames']['friendly:3:1']=deepcopy(data['frames']['friendly:0:1'])
            else:data['frames']['friendly:0:1']['teams']=True
            with self.subTest(edit=edit),self.assertRaises(ValueError):self.validate(data)

    def test_rehashed_palette_chr_row_and_cpu_cases_cannot_replace_originals(self):
        edits=[lambda p:p['palette_rgb'][2].__setitem__(0,200),
            lambda p:p['source_chunks']['marker_chr'].update(hex='00'*1024,sha256=checker.sha(bytes(1024))),
            lambda p:p['source_chunks']['top_tile_rows'].update(hex='00'*66,sha256=checker.sha(bytes(66))),
            lambda p:p['cpu_witness_cases'][0][-1].__setitem__(0,0),
            lambda p:p['army_type'].update(record_byte_index=8)]
        for index,edit in enumerate(edits):
            data,changed=self.proof_change(edit)
            with self.subTest(edit=index),self.assertRaises(ValueError):self.validate(data,changed)

    def test_native_and_four_times_pixel_changes_are_rejected_even_if_rehashed(self):
        for field in ('native_atlas','atlas'):
            data=deepcopy(self.data);row=data[field];raw=bytearray(checker.pixels(self.files[row['path']],(row['width'],row['height'])));raw[4]^=1
            blob=checker.builder.png(bytes(raw),row['width'],row['height']);row['sha256']=checker.sha(blob)
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate(data,{row['path']:blob})

    def test_witness_frame_and_unlisted_paths_cannot_be_substituted(self):
        with self.assertRaises(ValueError):self.validate(changes={checker.WITNESS:b'forged'})
        for path in ('/etc/passwd','/assets/battle-markers-original/../witness.png','/assets/battle-markers-original/unlisted.png'):
            data=deepcopy(self.data);data['atlas']['path']=path
            with self.subTest(path=path),self.assertRaises(ValueError):self.validate(data)

    def test_symlinks_and_extra_files_are_rejected_without_reading_original_inputs(self):
        with tempfile.TemporaryDirectory()as directory:
            parent=Path(directory);target=parent/'assets';target.mkdir()
            for path,raw in self.files.items():
                if path.startswith(checker.PREFIX):(target/Path(path).name).write_bytes(raw)
            self.assertEqual(checker.check(target)['frames'],132)
            (target/'history.state').write_bytes(b'not allowed')
            with self.assertRaises(ValueError):checker.check(target)
            (target/'history.state').unlink()
            raw=(target/'markers-native.png').read_bytes();(target/'markers-native.png').unlink()
            external=parent/'external-native-marker.png';external.write_bytes(raw)
            try:
                (target/'markers-native.png').symlink_to(external)
                with self.assertRaises(ValueError):checker.check(target)
            finally:external.unlink()


if __name__=='__main__':unittest.main()
