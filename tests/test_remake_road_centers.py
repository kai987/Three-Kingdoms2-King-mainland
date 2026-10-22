"""Reviewed city hubs move precisely; independent road junctions stay put."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('road_centers', ROOT / 'game/road_centers.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fixture():
    return dict(schema='tk2-road-center-source-v1',
        ground=dict(asset='/assets/road-ground.png', sha256='approved-ground', world=[0, 0, 100, 100]),
        provenance=dict(page_sha256='approved-page'),
        original_paths=['M10 0L15 0', 'M15 0L25 0L30 10',
                        'M15 0L15 15L30 20', 'M25 0L40 0',
                        'M124 120L150 150', 'M124 120L124 120', 'M10 0L10 0'],
        segments=[dict(index=0, points=[[10, 0], [15, 0]], radius=3),
                  dict(index=1, points=[[15, 0], [25, 0], [30, 10]], radius=3),
                  dict(index=2, points=[[15, 0], [15, 15], [30, 20]], radius=3),
                  dict(index=3, points=[[25, 0], [40, 0]], radius=3),
                  dict(index=4, points=[[124, 120], [150, 150]], radius=9)],
        hubs=[dict(city='a', old_hub=[15, 0], nodes_to_collapse=[[10, 0], [15, 0]],
                   center_branch_segment_indices=[0],
                   logical_relations=[dict(**{'from': 'a', 'to': 'b'}), dict(**{'from': 'a', 'to': 'c'})])],
        protected_hubs=[dict(city='a', junction=[25, 0], reason='A distinct b-to-c road uses this fork')],
        crossings=[dict(d='M50 0L50 4', stroke='#51371e', width=5.4)])


class RoadCenterBuilderTests(unittest.TestCase):
    def test_obsolete_baked_harbour_approach_is_erased_without_becoming_a_road(self):
        source = fixture()
        source['erased_access_paths'] = [dict(id='old-port', city='a',
            d='M9 1L44 8L52 14', reason='Replaced by the shared northern approach')]
        before = deepcopy(source)
        result = builder.build(source, {'a': [9, 1]})
        self.assertTrue(result['mask_d'].endswith(source['erased_access_paths'][0]['d']))
        self.assertNotIn(source['erased_access_paths'][0]['d'], result['paint_d'])
        self.assertEqual(result['erased_access_paths'], source['erased_access_paths'])
        result['erased_access_paths'][0]['d'] = 'changed'
        self.assertEqual(source, before)
        source['erased_access_paths'][0]['city'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'obsolete harbour'):
            builder.build(source, {'a': [9, 1]})

    def test_exact_hub_moves_keep_protected_junctions_and_native_connectors(self):
        source = fixture()
        result = builder.build(source, {'a': [9, 1], 'b': [30, 10], 'c': [30, 20]})
        rows = {r['index']: r for r in result['changes']}
        self.assertEqual(set(rows), {0, 1, 2})
        self.assertTrue(rows[0]['deleted'])
        self.assertEqual((rows[0]['new_d'], rows[0]['new_points']), ('', []))
        self.assertEqual(rows[1]['new_points'], [[9, 1], [25, 0], [30, 10]])
        self.assertEqual(rows[2]['new_points'], [[9, 1], [15, 15], [30, 20]])
        self.assertEqual(rows[1]['affected_cities'], ['a'])
        self.assertEqual(result['hubs'][0]['center'], [9, 1])
        self.assertIn(source['original_paths'][3], result['paint_d'])
        self.assertTrue(result['paint_d'].endswith(source['original_paths'][-1]))
        self.assertNotIn(source['original_paths'][4], result['paint_d'])
        self.assertNotIn(source['original_paths'][5], result['paint_d'])
        self.assertEqual([r['index'] for r in result['removed_obsolete_paths']], [4, 5])
        self.assertEqual([r['old_d'] for r in result['removed_obsolete_paths']], source['original_paths'][4:6])
        self.assertEqual(result['crossings'], source['crossings'])
        self.assertEqual(result['mask_d'], ''.join(r['old_d']+r['new_d'] for r in result['changes']))
        self.assertTrue(rows[1]['new_d'].startswith('M9 1'))
        self.assertTrue(rows[1]['new_d'].endswith('L30 10'))

    def test_registered_city_inside_a_changed_curve_is_an_actual_arrival(self):
        source = fixture()
        # [25,0] stays fixed, and it is also a registered city center. A Q at
        # that vertex would round around the city instead of reaching it.
        result = builder.build(source, {'a': [9, 1], 'b': [25, 0], 'c': [30, 20]})
        road = next(row for row in result['changes'] if row['index'] == 1)
        self.assertEqual(road['new_d'], 'M9 1L25 0M25 0L30 10')
        self.assertNotIn('Q25 0', road['new_d'])

    def test_rounding_uses_the_saved_radius_and_original_32_percent_cut(self):
        source = fixture()
        source['segments'][2].update(points=[[15, 0], [10, 11], [20, 11]], radius=3)
        result = builder.build(source, {'a': [10, 1]})
        road = next(row for row in result['changes'] if row['index'] == 2)
        self.assertEqual(road['new_d'], 'M10 1L10 8Q10 11 13 11L20 11')
        source['segments'][2]['radius'] = 0
        flat = builder.build(source, {'a': [10, 1]})
        self.assertEqual(next(r for r in flat['changes'] if r['index']==2)['new_d'], 'M10 1L10 11L20 11')

    def test_nearby_unregistered_points_never_expand_the_reviewed_mapping(self):
        source = fixture()
        # A point one pixel away from the approved old hub stays unchanged.
        source['segments'][2]['points'][1] = [16, 0]
        result = builder.build(source, {'a': [10, 1]})
        road = next(row for row in result['changes'] if row['index']==2)
        self.assertEqual(road['new_points'], [[10, 1], [16, 0], [30, 20]])

    def test_inputs_stay_immutable_and_rebuild_is_deterministic(self):
        source, positions = fixture(), {'a': [9, 1], 'b': [30, 10], 'c': [30, 20]}
        before, original_positions = deepcopy(source), deepcopy(positions)
        first, second = builder.build(source, positions), builder.build(source, positions)
        self.assertEqual(first, second)
        self.assertEqual(source, before)
        self.assertEqual(positions, original_positions)
        first['ground']['world'][0] = 999
        first['hubs'][0]['nodes_to_collapse'][0][0] = 999
        first['protected_hubs'][0]['junction'][0] = 999
        first['crossings'][0]['width'] = 999
        self.assertEqual(source, before)
        self.assertEqual(builder.build(source, positions), second)

    def test_unrelated_hubs_and_noncollapsed_branch_deletions_are_rejected(self):
        source = fixture()
        source['hubs'][0]['nodes_to_collapse'].append([25, 0])
        with self.assertRaisesRegex(ValueError, 'protected'):
            builder.build(source, {'a': [9, 1]})
        source = fixture()
        source['hubs'][0]['logical_relations'].append({'from': 'b', 'to': 'c'})
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            builder.build(source, {'a': [9, 1]})
        source = fixture()
        source['hubs'][0]['center_branch_segment_indices'] = [1]
        with self.assertRaisesRegex(ValueError, 'does not collapse'):
            builder.build(source, {'a': [9, 1]})

    def test_local_corridor_branches_reach_shared_junctions_and_city_centers(self):
        source = fixture()
        source['corridor_repairs'] = [dict(id='shared-trunk', cities=['a', 'b'], strokes=[
            dict(index=1, points=[[9, 1], [20, 5], [30, 10]], radius=3),
            dict(index=3, points=[[20, 5], [40, 0]], radius=3),
            dict(index=2, points=[], radius=0)])]
        positions = {'a': [9, 1], 'b': [30, 10]}
        before, original_positions = deepcopy(source), deepcopy(positions)
        result = builder.build(source, positions)
        rows = {row['index']: row for row in result['changes']}
        # A branch endpoint in the middle of another stroke is an actual
        # junction, even though it is not itself a registered city center.
        self.assertEqual(rows[1]['new_d'], 'M9 1L20 5M20 5L30 10')
        self.assertEqual(rows[3]['new_d'], 'M20 5L40 0')
        self.assertNotIn('Q20 5', rows[1]['new_d'])
        self.assertTrue(rows[2]['deleted'])
        self.assertEqual(rows[2]['new_points'], [])
        self.assertEqual(rows[1]['affected_cities'], ['a', 'b'])
        self.assertEqual(source, before)
        self.assertEqual(positions, original_positions)
        result['corridor_repairs'][0]['strokes'][0]['points'][0][0] = 999
        self.assertEqual(source, before, 'Output metadata cannot mutate reviewed input')
        self.assertEqual(builder.build(source, positions)['corridor_repairs'], before['corridor_repairs'])

    def test_invalid_corridor_strokes_are_rejected_before_rendering(self):
        valid = dict(index=1, points=[[9, 1], [30, 10]], radius=3)
        cases = [
            ('unknown-index', dict(valid, index=999)),
            ('boolean-index', dict(valid, index=True)),
            ('single-point', dict(valid, points=[[9, 1]])),
            ('nonfinite-x', dict(valid, points=[[float('inf'), 1], [30, 10]])),
            ('nonfinite-y', dict(valid, points=[[9, 1], [30, float('nan')]])),
            ('nonfinite-radius', dict(valid, radius=float('inf'))),
            ('negative-radius', dict(valid, radius=-1)),
        ]
        for name, stroke in cases:
            with self.subTest(name=name):
                source = fixture()
                source['corridor_repairs'] = [dict(id='repair', cities=['a'], strokes=[stroke])]
                with self.assertRaisesRegex(ValueError, 'finite number pairs|corridor stroke'):
                    builder.build(source, {'a': [9, 1]})
        for name, repairs in (
            ('duplicate-stroke', [dict(id='repair', cities=['a'], strokes=[valid, valid])]),
            ('duplicate-across-corridors', [dict(id='one', cities=['a'], strokes=[valid]),
                                          dict(id='two', cities=['a'], strokes=[valid])]),
            ('unknown-city', [dict(id='repair', cities=['missing'], strokes=[valid])]),
            ('duplicate-id', [dict(id='repair', cities=['a'], strokes=[]),
                              dict(id='repair', cities=['a'], strokes=[valid])]),
        ):
            with self.subTest(name=name):
                source = fixture()
                source['corridor_repairs'] = repairs
                with self.assertRaisesRegex(ValueError, 'corridor stroke|road corridor'):
                    builder.build(source, {'a': [9, 1]})

    def test_current_three_corridors_share_single_trunks_without_local_cycles(self):
        source = json.loads((ROOT / 'game/config/road-centers.json').read_text())
        catalog = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']
        positions = {city['id']: city['position'] for city in catalog['cities']}
        before = deepcopy(source)
        result = builder.build(source, positions)
        rows = {row['index']: row for row in result['changes']}
        repairs = {repair['id']: repair for repair in result['corridor_repairs']}
        self.assertEqual(set(repairs), {'dongping-changyi', 'jinan-linzi', 'shanggu-ji'})
        for identity, repair in repairs.items():
            parents, edges = {}, set()

            def root(node):
                parents.setdefault(node, node)
                while parents[node] != node:
                    node = parents[node]
                return node

            for stroke in repair['strokes']:
                row = rows[stroke['index']]
                self.assertEqual(row['new_points'], stroke['points'])
                self.assertEqual(row['deleted'], not bool(stroke['points']))
                points = [tuple(point) for point in row['new_points']]
                self.assertEqual(len(points), len(set(points)), identity)
                for a, b in zip(points, points[1:]):
                    edge = tuple(sorted((a, b)))
                    self.assertNotIn(edge, edges, identity + ': shared sections are drawn once')
                    edges.add(edge)
                    left, right = root(a), root(b)
                    self.assertNotEqual(left, right, identity + ': no local return loop')
                    parents[left] = right
        self.assertEqual([index for index in (213, 223, 229, 238, 184, 220)
                          if rows[index]['deleted']], [213, 223, 229, 238, 184, 220])
        # One Dongping–Changyi trunk meets the west branches precisely and
        # both cities are reached at their icon centers.
        self.assertEqual(rows[222]['new_points'][0], positions['dongping'])
        self.assertEqual(rows[222]['new_points'][-1], rows[224]['new_points'][0])
        self.assertEqual(rows[224]['new_points'][-1], positions['shanyang'])
        self.assertEqual(rows[221]['new_points'][0], positions['shanyang'])
        self.assertEqual(rows[201]['new_points'][0], positions['jiyin'])
        self.assertEqual(rows[201]['new_points'][-1], rows[212]['new_points'][0])
        # Jinan joins the southwestern trunk before Linzi; no separate
        # parallel stroke runs from the joining point into Linzi.
        join = [980.5, 222.5]
        self.assertEqual(rows[247]['new_points'][0], positions['jinan'])
        self.assertEqual(rows[247]['new_points'][-1], join)
        self.assertEqual(rows[237]['new_points'][-1], positions['qi'])
        self.assertIn('L980.5 222.5M980.5 222.5', rows[237]['new_d'])
        self.assertNotIn('Q980.5 222.5', rows[237]['new_d'])
        linzi_strokes = [row['index'] for row in repairs['jinan-linzi']['strokes']
                        if positions['qi'] in row['points']]
        self.assertEqual(linzi_strokes, [237])
        self.assertEqual(rows[183]['new_points'][-1], positions['shanggu'])
        self.assertEqual(rows[193]['new_points'][0], positions['shanggu'])
        self.assertEqual(rows[214]['new_points'][-1], positions['yan'])
        self.assertEqual(source, before)

    def test_current_reviewed_source_reaches_anding_and_preserves_catalogs(self):
        path = ROOT / 'game/config/road-centers.json'
        if not path.exists():
            self.skipTest('Current road-center source is not installed yet')
        source = json.loads(path.read_text())
        catalog_paths = sorted((ROOT / 'game/data/campaigns').glob('*.json'))
        before = {p: p.read_bytes() for p in catalog_paths}
        catalog = json.loads((ROOT / 'game/data/campaigns/217-07.json').read_text())
        positions = {city['id']: city['position'] for city in catalog['cities']}
        result = builder.build(source, positions)
        rows = {row['index']: row for row in result['changes']}
        self.assertEqual(rows[55]['new_points'][-1], positions['anding'])
        self.assertTrue(rows[61]['deleted'])
        self.assertEqual(rows[62]['new_points'][0], positions['anding'])
        self.assertIn('M434 270', rows[62]['new_d'])
        self.assertIn('L434 270', rows[55]['new_d'])
        self.assertEqual(next(r for r in result['hubs'] if r['city']=='anding')['center'], [434,270])
        self.assertEqual([r['index'] for r in result['removed_obsolete_paths']], [4,339])
        for index, path in enumerate(source['original_paths'][268:], start=268):
            if index != 339:
                self.assertIn(path, result['paint_d'])
        self.assertEqual(before, {p: p.read_bytes() for p in catalog_paths})


if __name__ == '__main__':
    unittest.main()
