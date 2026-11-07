"""ROM-free audit of native arrival-zone evidence, never a runtime deployment test."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_deployment_reference',
    ROOT/'tools/battle-deployment-original/build.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class NativeDeploymentReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(BUILD.OUTPUT.read_text())

    def test_all_native_cities_edges_and_zones_are_rederived_from_pinned_bytes(self):
        self.assertEqual(BUILD.check(self.reference),dict(cities=30,directed_native_neighbor_pairs=128,
            attacker_zones=91,defender_zones=53,native_data_anomalies=13))
        self.assertEqual(BUILD.build(self.reference['source_tables']),self.reference)

    def test_local_indices_are_not_a_compass_and_remain_paired_by_neighbor(self):
        top = BUILD.resolve_reference(self.reference,9,6)
        bottom = BUILD.resolve_reference(self.reference,9,26)
        self.assertEqual([top[side]['index'] for side in ('attackers','defenders')],[0,0])
        self.assertEqual([bottom[side]['index'] for side in ('attackers','defenders')],[2,1])
        self.assertEqual(top['attackers']['bounds'],dict(min_x=13,min_packed_y=0,
            max_x_exclusive=21,max_packed_y_exclusive=5))
        self.assertEqual(bottom['attackers']['bounds'],dict(min_x=0,min_packed_y=14,
            max_x_exclusive=6,max_packed_y_exclusive=20))
        self.assertTrue(self.reference['direction_semantics']['not_compass_indices'])
        self.assertIsNone(BUILD.resolve_reference(self.reference,9,9))
        self.assertIsNone(BUILD.resolve_reference(self.reference,9,0))
        with self.assertRaises(ValueError):BUILD.resolve_reference(self.reference,True,9)
        with self.assertRaises(ValueError):BUILD.resolve_reference(self.reference,9,30)

    def test_rectangles_are_half_open_in_packed_coordinates(self):
        bounds = BUILD.resolve_reference(self.reference,9,6)['attackers']['bounds']
        for x,y,wanted in ((13,0,True),(20,4,True),(12,0,False),(21,0,False),(13,5,False)):
            self.assertEqual(BUILD.in_rectangle(dict(x=x,packed_y=y),bounds),wanted)
        self.assertFalse(BUILD.native_cell_visible(dict(x=4,packed_y=20)))
        self.assertFalse(BUILD.native_cell_visible(dict(x=4,packed_y=15)))
        self.assertFalse(BUILD.native_cell_visible(dict(x=31,packed_y=10)))
        self.assertTrue(BUILD.native_cell_visible(dict(x=30,packed_y=19)))

    def test_explicit_safe_filter_has_ten_real_points_for_every_zone(self):
        maps = json.loads((ROOT/'game/assets/battlefields/index.json').read_text())['maps']
        terrain = set()
        minima = dict(attackers=99,defenders=99)
        for key,city in self.reference['cities'].items():
            for side,row in city['sides'].items():
                for zone in row['zones']:
                    original = deepcopy(zone)
                    points = BUILD.safe_visible_points(zone)
                    minima[side] = min(minima[side],len(points))
                    self.assertEqual(zone,original,'Auditing must not repair or rewrite native evidence')
                    self.assertGreaterEqual(len(points),10)
                    self.assertEqual(len(points),len({(p['x'],p['packed_y']) for p in points}))
                    for p in points:
                        self.assertIn(p,zone['default_points'])
                        self.assertTrue(BUILD.native_cell_visible(p))
                        self.assertTrue(BUILD.in_rectangle(p,zone['bounds']))
                        terrain.add(maps[key]['classes'][p['packed_y']-int(p['packed_y']>=16)][p['x']])
        self.assertEqual(minima,dict(attackers=13,defenders=14))
        self.assertTrue({3,4} <= terrain,'Native deployment is permitted on water and mountain')

    def test_native_duplicates_and_outside_points_are_kept_as_evidence(self):
        zone = self.reference['cities']['original-17']['sides']['defenders']['zones'][1]
        self.assertEqual(zone['default_points'][7],zone['default_points'][9])
        self.assertEqual(BUILD.unique_points(zone['default_points'])[9],dict(x=21,packed_y=14))
        outside = self.reference['cities']['original-00']['sides']['attackers']['zones'][0]
        self.assertEqual(outside['default_points'][5],dict(x=4,packed_y=20))
        self.assertNotIn(outside['default_points'][5],BUILD.safe_visible_points(outside))
        kinds = {row['kind'] for row in self.reference['native_data_anomalies']}
        self.assertEqual(kinds,{'outside_remake_visible_grid','outside_native_manual_deployment_rectangle',
            'duplicate_default_point_skipped_by_native_occupancy_scan'})

    def test_mutated_bytes_derived_zones_and_erased_anomalies_are_rejected(self):
        data = deepcopy(self.reference)
        row = data['source_tables']['attacker_zone_indices']
        row['hex'] = ('ff' if row['hex'][:2]!='ff' else '00')+row['hex'][2:]
        with self.assertRaises(ValueError):BUILD.check(data)
        data = deepcopy(self.reference)
        data['cities']['original-09']['neighbors'][0]['attacker_zone_index'] = 0
        with self.assertRaises(ValueError):BUILD.check(data)
        data = deepcopy(self.reference)
        data['native_data_anomalies'] = []
        with self.assertRaises(ValueError):BUILD.check(data)

    def test_reference_resolution_is_read_only_and_wrong_rom_is_rejected(self):
        before = deepcopy(self.reference)
        row = BUILD.resolve_reference(self.reference,9,6)
        row['attackers']['bounds']['min_x'] = 999
        self.assertEqual(self.reference,before)
        with self.assertRaises(ValueError):BUILD.source_tables(bytes(16+32*8192))


if __name__ == '__main__':
    unittest.main()
