"""Arrival pairs, regional directions and pure20-unit initial deployment."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake import battle_deployment as deployment


class DirectionalDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT/'game/data/campaigns/208-10.json').read_text())
        cls.cities = {row['id']:row for row in catalog['cities']}
        cls.bindings = json.loads((ROOT/'game/config/battlefield-city-bindings.json').read_text())['cities']
        cls.fields = json.loads((ROOT/'game/assets/battlefields/index.json').read_text())['maps']
        cls.reference = json.loads((ROOT/'game/config/references/original-battle-deployment-v1.json').read_text())['cities']
        cls.representatives = {}
        for city,row in cls.bindings.items():
            cls.representatives.setdefault(row['map_id'],city)

    def catalog(self):
        return SimpleNamespace(map_cities=deepcopy(self.cities))

    def field(self,target):
        row = self.fields[self.bindings[target]['map_id']]
        camp = row['camps'][0]
        return dict(classes=tuple(tuple(line) for line in row['classes']),camp=(camp['x'],camp['y']))

    def battle(self,source='wuwei',target='jincheng',count=10):
        return dict(source=source,target=target,attackers=[dict(id=i) for i in range(1,count+1)],
            defenders=[dict(id=i) for i in range(101,101+count)],extended={})

    def assert_legal(self,battle,plan):
        positions = list(plan['positions'].values())
        self.assertEqual(len(positions),len({(p['x'],p['y']) for p in positions}))
        metadata = plan['provenance']
        row = self.reference[metadata['target_map']]
        for side,singular in (('attackers','attacker'),('defenders','defender')):
            bounds = row['sides'][side]['zones'][metadata[singular+'_zone']]['bounds']
            for unit in battle[side]:
                point = plan['positions'][str(unit['id'])]
                x,y = point['x'],point['y']
                self.assertTrue(0 <= x < 31 and 0 <= y < 19)
                packed_y = y+int(y >= 15)
                self.assertTrue(bounds['min_x'] <= x < bounds['max_x_exclusive'])
                self.assertTrue(bounds['min_packed_y'] <= packed_y < bounds['max_packed_y_exclusive'])

    def test_native_neighbor_pairs_use_two_distinct_original_attack_directions(self):
        catalog = self.catalog()
        top = deployment.plan(catalog,self.battle(),self.field('jincheng'))
        bottom = deployment.plan(catalog,self.battle(source='shujun'),self.field('jincheng'))
        self.assertEqual((top['provenance']['policy'],top['provenance']['attacker_zone'],
            top['provenance']['defender_zone']),('native_pair',0,0))
        self.assertEqual((bottom['provenance']['attacker_zone'],bottom['provenance']['defender_zone']),(2,1))
        # Fixed source data, not a reflection or a second copy of the planner.
        self.assertEqual(top['positions']['1'],dict(x=19,y=1))
        self.assertEqual(bottom['positions']['1'],dict(x=2,y=18))
        self.assertEqual(top['positions']['101'],dict(x=14,y=10))
        self.assertEqual(bottom['positions']['101'],dict(x=14,y=10))

    def test_actual_final_city_takes_priority_over_the_origin_city(self):
        catalog,battle = self.catalog(),self.battle()
        quoted = deployment.plan(catalog,battle,self.field('jincheng'),arrival_city='shujun')
        self.assertEqual(quoted['provenance']['arrival_city'],'shujun')
        self.assertEqual(quoted['provenance']['arrival_map'],'original-26')
        self.assertEqual(quoted['provenance']['paired_source_map'],'original-26')
        self.assertEqual(quoted['positions']['1'],dict(x=2,y=18))
        # Origin coordinates cannot override an actual native neighbor pair.
        catalog.map_cities['shujun']['position'] = [999999,-999999]
        self.assertEqual(deployment.plan(catalog,battle,self.field('jincheng'),arrival_city='shujun'),quoted)

    def test_regional_same_template_arrivals_choose_real_north_and_south_edges(self):
        catalog,battle = self.catalog(),self.battle(source='xiping')
        catalog.map_cities['jincheng']['position'] = [500,500]
        catalog.map_cities['xiping']['position'] = [500,100]
        north = deployment.plan(catalog,battle,self.field('jincheng'))
        catalog.map_cities['xiping']['position'] = [500,900]
        south = deployment.plan(catalog,battle,self.field('jincheng'))
        self.assertEqual(north['provenance']['policy'],'regional_direction')
        self.assertEqual(north['provenance']['arrival_map'],'original-09')
        self.assertEqual((north['provenance']['attacker_zone'],south['provenance']['attacker_zone']),(0,2))
        self.assertEqual((north['provenance']['paired_source_map'],south['provenance']['paired_source_map']),
                         ('original-06','original-26'))
        self.assertLess(north['positions']['1']['y'],10)
        self.assertGreater(south['positions']['1']['y'],10)

    def test_all128_native_pairs_place_twenty_unique_units_and_allow_water_mountains(self):
        catalog,seen_terrain,count = self.catalog(),set(),0
        for target_map,row in self.reference.items():
            target = self.representatives[target_map]
            field = self.field(target)
            for neighbor in row['neighbors']:
                source = self.representatives[f"original-{neighbor['source_original_city_index']:02d}"]
                battle = self.battle(source,target)
                plan = deployment.plan(catalog,battle,field)
                self.assertEqual(plan['provenance']['policy'],'native_pair')
                self.assertEqual(len(plan['positions']),20)
                self.assertEqual(plan['positions']['101'],dict(zip(('x','y'),field['camp'])))
                self.assert_legal(battle,plan)
                deployment.validate_provenance(catalog,battle,field,plan['provenance'])
                seen_terrain.update(field['classes'][p['y']][p['x']] for p in plan['positions'].values())
                count += 1
        self.assertEqual(count,128)
        self.assertTrue({3,4} <= seen_terrain)

    def test_every_expanded_city_has_a_bounded_regionally_labeled_fallback(self):
        catalog,count = self.catalog(),0
        for target,binding in self.bindings.items():
            neighbors = {r['source_original_city_index'] for r in self.reference[binding['map_id']]['neighbors']}
            source = next(city for city,row in self.bindings.items() if city != target
                and int(row['map_id'].removeprefix('original-')) not in neighbors)
            battle = self.battle(source,target)
            plan = deployment.plan(catalog,battle,self.field(target))
            self.assertEqual(plan['provenance']['policy'],'regional_direction')
            self.assertEqual(plan['provenance']['arrival_city'],source)
            self.assert_legal(battle,plan)
            count += 1
        self.assertEqual(count,126)

    def test_original_outside_points_and_duplicate_defaults_are_safely_skipped(self):
        catalog = self.catalog()
        outside = deployment.plan(catalog,self.battle('fanyang','liaodong'),self.field('liaodong'))
        # Native slot5 is(4,packed20); take the next real point, not a clamp.
        self.assertEqual(outside['positions']['6'],dict(x=6,y=17))
        source = self.representatives['original-18']
        target = self.representatives['original-17']
        duplicate = deployment.plan(catalog,self.battle(source,target),self.field(target))
        # Native defender slots7/9 repeat(21,13); the tenth unit uses slot10.
        self.assertEqual(duplicate['positions']['110'],dict(x=21,y=14))
        self.assertEqual(len({(p['x'],p['y'])for p in duplicate['positions'].values()}),20)

    def test_missing_or_zero_arrival_geometry_has_a_stable_documented_tie_break(self):
        catalog,battle = self.catalog(),self.battle(source='xiping')
        catalog.map_cities['xiping']['position'] = catalog.map_cities['jincheng']['position'][:]
        zero = deployment.plan(catalog,battle,self.field('jincheng'))
        del catalog.map_cities['xiping']['position']
        missing = deployment.plan(catalog,battle,self.field('jincheng'))
        self.assertEqual(missing,zero)
        self.assertEqual(zero['provenance']['paired_source_map'],'original-06')
        catalog.map_cities['controlled-arrival'] = dict(position=[500,100])
        unbound = deployment.plan(catalog,battle,self.field('jincheng'),arrival_city='controlled-arrival')
        self.assertEqual(unbound['provenance']['policy'],'regional_direction')
        self.assertIsNone(unbound['provenance']['arrival_map'])

    def test_planning_is_pure_and_returned_metadata_cannot_mutate_cached_sources(self):
        catalog,battle,field = self.catalog(),self.battle(),self.field('jincheng')
        catalog.rng = SimpleNamespace(next=lambda: self.fail('Planning must not draw RNG'))
        before = deepcopy((catalog.map_cities,battle,field))
        original = deployment.plan(catalog,battle,field)
        edited = deepcopy(original)
        edited['positions']['1']['x'] = 999
        edited['provenance']['policy'] = 'corrupted'
        self.assertEqual(deployment.plan(catalog,battle,field),original)
        self.assertEqual((catalog.map_cities,battle,field),before)

    def test_metadata_validation_does_not_redeploy_moved_or_converted_armies(self):
        catalog,battle,field = self.catalog(),self.battle(),self.field('jincheng')
        plan = deployment.plan(catalog,battle,field)
        battle['extended']['tactical'] = dict(positions=deepcopy(plan['positions']),points=dict(attackers=3,defenders=0))
        battle['extended']['tactical']['positions']['1'] = dict(x=7,y=8)
        battle['attackers'].extend(battle['defenders'][:9]);del battle['defenders'][:9]
        before = deepcopy(battle)
        self.assertIsNone(deployment.validate_provenance(catalog,battle,field,plan['provenance']))
        self.assertEqual(battle,before)
        with self.assertRaises(ValueError):deployment.plan(catalog,battle,field)
        for patch in ({'schema':'bad'},{'policy':'north'},{'attacker_zone':True},{'defender_zone':2},
                      {'target_map':'original-00'},{'arrival_map':None},{'paired_source_map':'original-26'},
                      {'arrival_city':'absent'},{'extra':1}):
            forged = {**plan['provenance'],**patch}
            with self.assertRaises(ValueError):deployment.validate_provenance(catalog,battle,field,forged)
        forged = deepcopy(plan['provenance']);del forged['arrival_city']
        with self.assertRaises(ValueError):deployment.validate_provenance(catalog,battle,field,forged)
        self.assertEqual(battle,before)

    def test_unknown_test_targets_keep_fallback_and_invalid_new_units_fail_without_changes(self):
        catalog,battle = self.catalog(),self.battle(target='controlled-target')
        before = deepcopy(battle)
        self.assertIsNone(deployment.plan(catalog,battle,{}))
        self.assertEqual(battle,before)
        battle = self.battle();field = self.field('jincheng')
        for change in ('duplicate','string_collision','bool','eleventh','wrong_field','bad_arrival'):
            invalid,geometry = deepcopy(battle),deepcopy(field)
            kwargs = {}
            if change == 'duplicate':invalid['defenders'][0]['id'] = 1
            elif change == 'string_collision':invalid['defenders'][0]['id'] = '1'
            elif change == 'bool':invalid['attackers'][0]['id'] = True
            elif change == 'eleventh':invalid['attackers'].append(dict(id=11))
            elif change == 'wrong_field':geometry['camp'] = (0,0)
            else:kwargs['arrival_city'] = 'absent'
            saved = deepcopy((invalid,geometry))
            with self.assertRaises(ValueError):deployment.plan(catalog,invalid,geometry,**kwargs)
            self.assertEqual((invalid,geometry),saved)


if __name__ == '__main__':
    unittest.main()
