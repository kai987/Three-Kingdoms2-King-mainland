"""ROM-free checks of pinned native AI profile data and independent CPU counts."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_ai_deployment_reference',
    ROOT/'tools/battle-deployment-original/ai_reference.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)

# Independent originalCPU B130 witnesses, each row for1..9 noncommanders.
# No runtime/source implementation or emulator is consulted in these tests.
CPU_COUNTS = (
 ((1,0,0,0),(1,1,0,0),(2,1,0,0),(2,1,1,0),(3,1,1,0),(3,2,1,0),(3,2,1,1),(3,2,2,1),(3,2,2,2)),
 ((0,0,1,0),(0,1,1,0),(0,1,2,0),(1,1,2,0),(1,1,2,1),(2,1,2,1),(2,1,3,1),(2,1,3,2),(2,1,3,3)),
 ((0,1,0,0),(0,1,1,0),(1,1,1,0),(1,2,1,0),(1,2,2,0),(2,2,2,0),(2,2,2,1),(2,2,2,2),(3,2,3,1)),
 ((1,0,0,0),(2,0,0,0),(2,1,0,0),(2,1,0,1),(3,1,0,1),(3,1,1,1),(3,2,1,1),(4,2,1,1),(4,2,1,2)),
 ((1,0,0,0),(1,1,0,0),(1,1,1,0),(2,1,1,0),(2,1,1,1),(2,2,1,1),(2,2,2,1),(3,2,2,1),(3,3,2,1)),
 ((1,0,0,0),(1,1,0,0),(2,1,0,0),(2,1,1,0),(2,1,1,1),(2,2,1,1),(3,2,1,1),(3,3,1,1),(3,3,1,2)),
)


class NativeAIDeploymentReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(BUILD.OUTPUT.read_text())

    def test_pinned_three_data_spans_rederive_six_profiles_and_fifty_four_counts(self):
        self.assertEqual(BUILD.check(self.reference),dict(profiles=6,count_records=54,groups=4,original_slots=7))
        self.assertEqual(BUILD.build(self.reference['source_tables']),self.reference)
        tables = self.reference['source_tables']
        self.assertEqual(set(tables),{'defender_group_offsets','attacker_group_offsets','profiles'})
        for name,cpu,length,sha in [
            ('defender_group_offsets','B30E',4,'9b2cf966adf226a8e2028886d77bf2b63fcaa7aa571d5916af87e2c6b7fe2f8e'),
            ('attacker_group_offsets','B36D',4,'b2f3c5d4cef4b82ac0599dfa620c941a371480c01d12f492bf256ff88c274316'),
            ('profiles','B3FD',108,'a70cd1fc0a10600d3e662ac844e1c871b7911d255e966307b4914516f88f8cb5')]:
            row = tables[name];raw = bytes.fromhex(row['hex'])
            self.assertEqual((row['physical_bank'],row['cpu'],len(raw),row['length']),(8,cpu,length,length))
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)
            self.assertEqual(row['sha256'],sha)
            self.assertEqual(row['rom_file_offset'],16+8*8192+(int(cpu,16)&8191))

    def test_all_profile_counts_match_independent_original_cpu(self):
        self.assertEqual(len(self.reference['profiles']),6)
        for index,profile in enumerate(self.reference['profiles']):
            self.assertEqual((profile['index'],profile['side'],profile['family']),
                (index,'defenders'if index<3 else'attackers',index%3))
            self.assertEqual(tuple(tuple(row)for row in profile['counts']),CPU_COUNTS[index])
            for number,counts in enumerate(profile['counts'],1):
                self.assertEqual(len(counts),4)
                self.assertEqual(sum(counts),number)
                self.assertTrue(all(type(count)is int and count>=0 for count in counts))

    def test_native_group_offsets_and_fixed_original_slots_are_preserved(self):
        self.assertEqual(self.reference['group_byte_offsets'],dict(defenders=[2,8,12,20],attackers=[2,12,22,28]))
        self.assertEqual(self.reference['original_slot_families'],[0,1,2,0,2,1,0])
        rules = self.reference['rules']
        self.assertEqual((rules['commander_group'],rules['commander_point_byte_offset']),(0,0))
        self.assertIn('>=',rules['noncommander_order'])
        self.assertIn('not the current successor',rules['faction'])
        self.assertIn('No C447',rules['native_legality'])
        self.assertIn('No random call',rules['rng'])
        # No stale original scratch cache is required to plan a lone commander.
        self.assertIn('only commander placed',rules['zero_noncommanders'])

    def test_mutated_source_bytes_hash_addresses_and_source_key_set_are_rejected(self):
        for change in ('byte','hash','address','length','missing','extra'):
            data = deepcopy(self.reference);tables = data['source_tables'];row = tables['profiles']
            if change=='byte':row['hex'] = 'ff'+row['hex'][2:]
            elif change=='hash':row['sha256'] = '0'*64
            elif change=='address':row['cpu'] = 'B3FE'
            elif change=='length':row['length'] = 107
            elif change=='missing':del tables['attacker_group_offsets']
            else:tables['extra'] = deepcopy(row)
            with self.subTest(change=change),self.assertRaises(ValueError):BUILD.check(data)

    def test_tampered_derived_profiles_original_slots_offsets_rules_and_extra_fields_are_rejected(self):
        for change in ('counts','family','side','slot','offset','rule','top_extra'):
            data = deepcopy(self.reference)
            if change=='counts':data['profiles'][0]['counts'][0] = [0,1,0,0]
            elif change=='family':data['profiles'][0]['family'] = 2
            elif change=='side':data['profiles'][0]['side'] = 'attackers'
            elif change=='slot':data['original_slot_families'][0] = 1
            elif change=='offset':data['group_byte_offsets']['attackers'][1] = 8
            elif change=='rule':data['rules']['rng'] = 'One random draw'
            else:data['unrecognized'] = 1
            with self.subTest(change=change),self.assertRaises(ValueError):BUILD.check(data)

    def test_build_is_readonly_and_results_do_not_alias_source(self):
        before = deepcopy(self.reference['source_tables'])
        result = BUILD.build(self.reference['source_tables'])
        result['source_tables']['profiles']['hex'] = ''
        self.assertEqual(self.reference['source_tables'],before)
        self.assertEqual(BUILD.build(before),self.reference)
        with self.assertRaises(ValueError):BUILD.source_tables(bytes(16+32*8192))

    def test_command_line_check_needs_only_shipped_data_and_standard_python(self):
        result = subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/battle-deployment-original/ai_reference.py'),'--check'],
            cwd=ROOT,check=True,capture_output=True,text=True)
        self.assertEqual(json.loads(result.stdout),dict(profiles=6,count_records=54,groups=4,original_slots=7))
        self.assertEqual(result.stderr,'')


if __name__=='__main__':
    unittest.main()
