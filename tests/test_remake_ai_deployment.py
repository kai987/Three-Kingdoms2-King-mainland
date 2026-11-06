"""Pure AI formation planning against independent unchanged-ROM CPU witnesses.

The numeric witnesses below were observed by py65 from the Archive's captured
B130 caller and declared RAM vectors. CI uses only these numbers and the
shipped native data; it does not execute a ROM, Archive code or CPU emulator.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake import battle_deployment as deployment,battle_ai_deployment as ai

# Original CPU, target4/source11, ten participants; commander is not sorted.
# martial(slot)=40+(slot*17)%60. Each tuple is in final ordered slot order.
CPU_ORDER = [0,7,3,6,2,9,5,1,8,4]
CPU_GROUPS = {
 ('defenders',0):[0,1,1,1,2,2,3,3,4,4],
 ('defenders',1):[0,1,1,2,3,3,3,4,4,4],
 ('defenders',2):[0,1,1,1,2,2,3,3,3,4],
 ('attackers',0):[0,1,1,1,1,2,2,3,4,4],
 ('attackers',1):[0,1,1,1,2,2,2,3,3,4],
 ('attackers',2):[0,1,1,1,2,2,2,3,4,4],
}
CPU_POINTS = {
 ('defenders',0):[(20,14),(19,18),(17,11),(20,10),(17,17),(22,18),(19,14),(20,13),(20,17),(24,17)],
 ('defenders',1):[(20,14),(19,18),(17,11),(17,17),(19,14),(20,13),(21,14),(20,17),(24,17),(22,13)],
 ('defenders',2):[(20,14),(19,18),(17,11),(20,10),(17,17),(22,18),(19,14),(20,13),(21,14),(20,17)],
 ('attackers',0):[(2,16),(11,18),(11,19),(10,18),(8,18),(10,19),(9,19),(3,16),(3,14),(3,17)],
 ('attackers',1):[(2,16),(11,18),(11,19),(10,18),(10,19),(9,19),(8,19),(3,16),(2,14),(3,14)],
 ('attackers',2):[(2,16),(11,18),(11,19),(10,18),(10,19),(9,19),(8,19),(3,16),(3,14),(3,17)],
}
# Each four-digit word is the independent CPU's group1..4 count for the
# next noncommander count1..9. Profiles0..2 defend;3..5 attack.
CPU_COUNT_ROWS = (
 '1000 1100 2100 2110 3110 3210 3211 3221 3222',
 '0010 0110 0120 1120 1121 2121 2131 2132 2133',
 '0100 0110 1110 1210 1220 2220 2221 2222 3231',
 '1000 2000 2100 2101 3101 3111 3211 4211 4212',
 '1000 1100 1110 2110 2111 2211 2221 3221 3321',
 '1000 1100 2100 2110 2111 2211 3211 3311 3312',
)
OWNERS = ('other','yuan_shao','wei')


class AIDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT/'game/data/campaigns/208-10.json').read_text())
        cls.cities = {row['id']:row for row in raw['cities']}
        cls.reference,cls.bindings = deployment._library()
        cls.fields = json.loads((ROOT/'game/assets/battlefields/index.json').read_text())['maps']
        cls.representatives = {}
        for city,mid in cls.bindings.items():
            cls.representatives.setdefault(mid,city)

    def fixture(self,target_index=4,source_index=11,*,count=10,family=2,side='defenders',martials=None):
        target = self.representatives[f'original-{target_index:02d}']
        source = self.representatives[f'original-{source_index:02d}']
        catalog = SimpleNamespace(map_cities=self.cities)
        row = self.fields[f'original-{target_index:02d}'];camp = row['camps'][0]
        field = dict(classes=tuple(tuple(line)for line in row['classes']),camp=(camp['x'],camp['y']))
        battle = dict(source=source,target=target,attacker=OWNERS[family],defender=OWNERS[family],
            attackers=[dict(id=30+i,martial=(40+(i*17)%60))for i in range(count)],
            defenders=[dict(id=20+i,martial=(40+(i*17)%60))for i in range(count)],extended={})
        if martials is not None:
            for unit,value in zip(battle[side],martials):unit['martial'] = value
        battle['extended']['deployment'] = deployment.plan(catalog,battle,field)['provenance']
        return catalog,battle,field

    def assert_legal(self,catalog,battle,field,side,plan,occupied=()):
        order = plan['order'];positions = plan['positions']
        self.assertEqual(order[0],str(battle[side][0]['id']))
        self.assertEqual(set(order),{str(unit['id'])for unit in battle[side]})
        self.assertEqual(set(positions),set(order))
        self.assertEqual(len(plan['groups']),len(order))
        self.assertEqual(plan['groups'][0],0)
        zone = deployment.placement_zone(catalog,battle,field,side)
        cells = {(point['x'],point['y'])for point in zone['cells']}
        used = set(occupied)
        for key in order:
            point = positions[key]
            self.assertEqual(set(point),{'x','y'})
            pair = point['x'],point['y']
            self.assertIn(pair,cells)
            self.assertNotIn(pair,used)
            used.add(pair)
        for repair in plan['repairs']:
            self.assertIn(repair['id'],order)
            self.assertIn(repair['reason'],{'outside_grid','outside_zone','occupied'})

    def test_stable_original_factions_lineages_and_expanded_generic_family(self):
        originals = {'dong_zhuo':(0,0),'yuan_shao':(1,1),'wei':(2,2),'wu':(0,3),
                     'shu':(2,4),'liu_zhang':(1,5),'ma_teng':(0,6)}
        for name,(family,slot) in originals.items():
            self.assertEqual(ai.family_for(name),dict(family=family,policy='original_faction',original_slot=slot))
        for name,family,slot in [('sun_jian',0,3),('liu_yan',1,5)]:
            self.assertEqual(ai.family_for(name),dict(family=family,policy='lineage_alias',original_slot=slot))
        for name in ('han_sui','song_jian','meng_huo','unknown-expanded-faction'):
            self.assertEqual(ai.family_for(name),dict(family=0,policy='expanded_default',original_slot=None))

    def test_six_full_army_vectors_match_independent_original_cpu(self):
        for side in ('defenders','attackers'):
            for family in range(3):
                with self.subTest(side=side,family=family):
                    catalog,battle,field = self.fixture(family=family,side=side)
                    result = ai.plan(catalog,battle,field,side)
                    offset = 20 if side=='defenders'else 30
                    order = [str(offset+i)for i in CPU_ORDER]
                    self.assertEqual(result['order'],order)
                    self.assertEqual(result['groups'],CPU_GROUPS[side,family])
                    self.assertEqual(result['profile'],family+(3 if side=='attackers'else 0))
                    self.assertEqual(result['binding'],ai.family_for(OWNERS[family]))
                    self.assertEqual(result['repairs'],[])
                    for key,(x,py) in zip(order,CPU_POINTS[side,family]):
                        self.assertEqual(result['intended'][key],dict(x=x,packed_y=py))
                        self.assertEqual(result['positions'][key],dict(x=x,y=py-int(py>=16)))
                    self.assert_legal(catalog,battle,field,side,result)

    def test_real_captured_four_defenders_have_original_strategy_positions(self):
        catalog,battle,field = self.fixture(count=4,family=1)
        # True captured IDs and martial bytes; commander8 stays before90/89.
        battle['defenders'] = [dict(id=i,martial=m)for i,m in [(8,70),(51,89),(191,90),(167,35)]]
        result = ai.plan(catalog,battle,field,'defenders')
        self.assertEqual(result['order'],['8','191','51','167'])
        self.assertEqual(result['groups'],[0,2,3,3])
        self.assertEqual([result['intended'][key]for key in result['order']],
            [dict(x=x,packed_y=y)for x,y in [(20,14),(17,17),(19,14),(20,13)]])
        self.assertEqual(result['repairs'],[])

    def test_equal_martial_uses_original_repeated_greater_equal_swaps(self):
        for side in ('defenders','attackers'):
            catalog,battle,field = self.fixture(side=side,martials=[75]*10)
            before = deepcopy(battle)
            result = ai.plan(catalog,battle,field,side)
            offset = 20 if side=='defenders'else 30
            # CPU witness: not stable sort, not reversed; nine equal
            # noncommanders rotate their last element to the front.
            self.assertEqual(result['order'],[str(offset+i)for i in [0,9,1,2,3,4,5,6,7,8]])
            self.assertEqual(battle,before)

    def test_all128_pairs_both_sides_three_families_and_one_to_ten_are_legal(self):
        checked,terrain = 0,set()
        for target_map,city in self.reference.items():
            target = int(target_map.removeprefix('original-'))
            for neighbor in city['neighbors']:
                source = neighbor['source_original_city_index']
                for side in ('defenders','attackers'):
                    for family in range(3):
                        for count in range(1,11):
                            catalog,battle,field = self.fixture(target,source,count=count,family=family,side=side)
                            result = ai.plan(catalog,battle,field,side)
                            self.assert_legal(catalog,battle,field,side,result)
                            own = battle[side]
                            expected = [own[0]]+sorted(own[1:],key=lambda unit:-unit['martial'])
                            self.assertEqual(result['order'],[str(unit['id'])for unit in expected])
                            profile = family+(3 if side=='attackers'else 0)
                            counts = '0000' if count==1 else CPU_COUNT_ROWS[profile].split()[count-2]
                            self.assertEqual(result['groups'],[0]+[group for group,amount in
                                enumerate(counts,1)for _ in range(int(amount))])
                            if side=='defenders':
                                self.assertEqual(result['positions'][str(own[0]['id'])],dict(zip(('x','y'),field['camp'])))
                            terrain.update(field['classes'][p['y']][p['x']]for p in result['positions'].values())
                            checked += 1
        self.assertEqual(checked,128*2*3*10)
        self.assertTrue({3,4}<=terrain,'NativeAI is allowed to deploy on water and mountains')

    def test_duplicate_and_outside_native_ai_points_are_repaired_from_real_defaults(self):
        for target,source,side,family,reason in [(25,27,'attackers',2,'occupied'),
                                                (15,17,'defenders',2,'outside_zone'),
                                                (26,29,'defenders',0,'outside_zone')]:
            catalog,battle,field = self.fixture(target,source,side=side,family=family)
            result = ai.plan(catalog,battle,field,side)
            self.assertIn(reason,[row['reason']for row in result['repairs']])
            self.assert_legal(catalog,battle,field,side,result)
            defaults = deployment.placement_zone(catalog,battle,field,side)['defaults']
            used = set()
            for key in result['order']:
                intended = result['intended'][key]
                wanted = dict(x=intended['x'],y=intended['packed_y']-int(intended['packed_y']>=16))
                repair = next((row for row in result['repairs']if row['id']==key),None)
                if repair is not None:
                    wanted = next(point for point in defaults if(point['x'],point['y'])not in used)
                self.assertEqual(result['positions'][key],wanted)
                used.add((wanted['x'],wanted['y']))

    def test_preoccupied_coordinate_is_skipped_without_changing_original_intention(self):
        catalog,battle,field = self.fixture()
        plain = ai.plan(catalog,battle,field,'defenders')
        point = plain['positions']['20'];occupied = ((point['x'],point['y']),)
        result = ai.plan(catalog,battle,field,'defenders',occupied=occupied)
        self.assertEqual(result['intended'],plain['intended'])
        self.assertIn(dict(id='20',reason='occupied'),result['repairs'])
        self.assert_legal(catalog,battle,field,'defenders',result,occupied)

    def test_ai_positions_leave_human_default_capacity_for_all_pairs_and_families(self):
        checked = 0
        minima = dict(attackers=100,defenders=100)
        for target_map,city in self.reference.items():
            target = int(target_map.removeprefix('original-'))
            for neighbor in city['neighbors']:
                source = neighbor['source_original_city_index']
                for ai_side,human_side in [('defenders','attackers'),('attackers','defenders')]:
                    for family in range(3):
                        for ai_count in range(1,11):
                            catalog,battle,field = self.fixture(target,source,side=ai_side,family=family)
                            battle[ai_side] = battle[ai_side][:ai_count]
                            result = ai.plan(catalog,battle,field,ai_side)
                            occupied = {(point['x'],point['y'])for point in result['positions'].values()}
                            defaults = deployment.placement_zone(catalog,battle,field,human_side)['defaults']
                            available = [point for point in defaults if(point['x'],point['y'])not in occupied]
                            self.assertGreaterEqual(len(available),10)
                            minima[human_side] = min(minima[human_side],len(available)-9)
                            for point in available[:10]:
                                self.assertNotIn((point['x'],point['y']),occupied)
                                occupied.add((point['x'],point['y']))
                            self.assertEqual(len(occupied),ai_count+10)
                            checked += 1
        self.assertEqual(checked,128*2*3*10)
        self.assertEqual(minima,dict(attackers=4,defenders=5))

    def test_plan_is_pure_no_rng_no_tactical_read_or_shared_result_mutation(self):
        catalog,battle,field = self.fixture()
        catalog.rng = SimpleNamespace(next=lambda:self.fail('AI placement must not draw RNG'))
        battle['extended']['tactical'] = dict(positions={'deliberate-invalid-old-position':None},points=None)
        before = deepcopy((catalog.map_cities,battle,field))
        original = ai.plan(catalog,battle,field,'defenders')
        edited = deepcopy(original);edited['positions']['20']['x'] = 999
        edited['binding']['family'] = 999
        self.assertEqual(ai.plan(catalog,battle,field,'defenders'),original)
        self.assertEqual((catalog.map_cities,battle,field),before)
        battle['defender_captain'] = 9999
        self.assertEqual(ai.plan(catalog,battle,field,'defenders'),original,
                         'Inheritance must not move a faction to the new ruler name profile')

    def test_invalid_side_army_identity_martial_and_capacity_fail_purely(self):
        catalog,battle,field = self.fixture()
        for kind in ('side','empty','eleventh','duplicate','canonical_collision','bool_id',
                     'missing_id','bool_martial','negative_martial','large_martial','missing_martial'):
            invalid = deepcopy(battle);side = 'defenders'
            if kind=='side':side = 'both'
            elif kind=='empty':invalid[side] = []
            elif kind=='eleventh':invalid[side].append(dict(id=999,martial=60))
            elif kind=='duplicate':invalid[side][1]['id'] = invalid[side][0]['id']
            elif kind=='canonical_collision':invalid[side][1]['id'] = str(invalid[side][0]['id'])
            elif kind=='bool_id':invalid[side][0]['id'] = True
            elif kind=='missing_id':del invalid[side][0]['id']
            elif kind=='bool_martial':invalid[side][0]['martial'] = True
            elif kind=='negative_martial':invalid[side][0]['martial'] = -1
            elif kind=='large_martial':invalid[side][0]['martial'] = 256
            else:del invalid[side][0]['martial']
            before = deepcopy(invalid)
            with self.subTest(kind=kind),self.assertRaises(ValueError):ai.plan(catalog,invalid,field,side)
            self.assertEqual(invalid,before)
        zone = deployment.placement_zone(catalog,battle,field,'defenders')
        occupied = [(point['x'],point['y'])for point in zone['defaults']]
        before = deepcopy(battle)
        with self.assertRaises(ValueError):ai.plan(catalog,battle,field,'defenders',occupied=occupied)
        self.assertEqual(battle,before)

    def test_generated_string_identity_and_byte_martial_boundaries_remain_supported(self):
        catalog,battle,field = self.fixture(count=3)
        battle['defenders'] = [dict(id='civil-staff:10',martial=0),dict(id='civil-staff:2',martial=255),dict(id=100,martial=100)]
        result = ai.plan(catalog,battle,field,'defenders')
        self.assertEqual(result['order'],['civil-staff:10','civil-staff:2','100'])
        self.assert_legal(catalog,battle,field,'defenders',result)


if __name__=='__main__':
    unittest.main()
