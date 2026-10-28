"""Historical route decisions keep topology, terrain and chronology explicit."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
from build_campaigns import apply_patch
from route_timing import apply_route_timing


class HistoricalRoadSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = json.loads((ROOT/'game/config/campaigns/shared.json').read_text())['catalog']
        cls.scenarios = json.loads((ROOT/'game/config/campaigns/index.json').read_text())['scenarios']

    def test_xu_wan_regional_channel_is_present_in_all_openings_without_moving_a_city(self):
        for entry in self.scenarios:
            source = json.loads((ROOT/'game/config/campaigns'/entry['file']).read_text())
            data = apply_patch(self.shared, source['overrides'])
            routes = [r for r in data['travel_routes'] if r['id']=='yingchuan:nanyang:land']
            with self.subTest(scenario=entry['id']):
                self.assertEqual(len(routes), 1)
                self.assertEqual(sum(set(e)=={'yingchuan','nanyang'} for e in data['links']), 1)
                row = routes[0]
                positions = {city['id']:city['position'] for city in data['cities']}
                self.assertEqual(row['draw'][0]['points'][0], positions['yingchuan'])
                self.assertEqual(row['draw'][-1]['points'][-1], positions['nanyang'])
                self.assertIs(row['history']['is_proven_exact_Han_alignment'], False)
                self.assertNotIn('availability',row,'A 197 mention is not a road construction date')
                self.assertEqual(positions, {city['id']:city['position'] for city in self.shared['cities']})

    def test_lulong_is_a_dated_alternative_not_an_overwrite_of_coastal_road(self):
        pair=[r for r in self.shared['travel_routes'] if {r['from'],r['to']}=={'liaoxi','yuyang'}]
        self.assertEqual({r['id'] for r in pair}, {'liaoxi:yuyang:land','yuyang:liaoxi:lulong:land'})
        coast=next(r for r in pair if r['id']=='liaoxi:yuyang:land')
        mountain=next(r for r in pair if r['id']=='yuyang:liaoxi:lulong:land')
        self.assertEqual(coast['terrain'],'plain')
        self.assertNotIn('availability',coast)
        self.assertEqual(mountain['terrain'],'mountain')
        self.assertEqual(mountain['availability'], {'from':[207,7]})
        self.assertEqual(sum(set(e)=={'liaoxi','yuyang'} for e in self.shared['links']),1)
        self.assertIs(mountain['history']['is_proven_exact_Han_alignment'],False)

    def test_cross_ridge_roads_cost_more_than_equal_plain_curves_without_city_terrain_changes(self):
        wanted={'badong:yidu:land','lingling:linhe:land','changsha:luling:land',
                'guiyang:luling:land','guiyang:linhe:land'}
        for row in self.shared['travel_routes']:
            if row['id'] not in wanted:
                continue
            with self.subTest(route=row['id']):
                self.assertEqual(row['terrain'],'mountain')
                route=deepcopy(row)
                data=dict(travel_routes=[route],sea_routes=[],exploration_routes=[],
                          travel_rules=deepcopy(self.shared['travel_rules']),
                          city_coordinates=self.shared['city_coordinates'])
                shape=dict(mode='land',start=[0,0],end=[100,0],length_px=130,chord_px=100)
                geometry=dict(schema='tk2-route-geometry-v1',routes={row['id']:dict(
                    **{k:row[k] for k in ('from','to','mode')},parts=[shape])})
                apply_route_timing(data,geometry,'test')
                mountain_days=route['days']
                route['terrain']='plain'
                apply_route_timing(data,geometry,'test')
                self.assertGreater(mountain_days,route['days'])
                self.assertEqual(row['history']['timing_policy'],'coarse_land_corridor_terrain_not_city_terrain')

    def test_chenliu_henei_independent_corridor_does_not_cross_xu_or_luoyang_centers(self):
        route=next(r for r in self.shared['travel_routes'] if r['id']=='chenliu:henei:land')
        points=route['draw'][0]['points']
        positions={city['id']:city['position'] for city in self.shared['cities']}
        self.assertEqual(points[0],positions['chenliu'])
        self.assertEqual(points[-1],positions['henei'])
        self.assertNotIn(positions['yingchuan'],points)
        self.assertNotIn(positions['henan'],points)
        self.assertIs(route['history']['is_proven_exact_Han_alignment'],False)


if __name__ == '__main__':
    unittest.main()
