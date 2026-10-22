"""Rendered roads calibrate to geography without changing campaign rules."""
from copy import deepcopy
from hashlib import sha256
import json
from math import atan2, ceil, cos, dist, radians, sin, sqrt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
sys.path.insert(0, str(ROOT / 'source'))
import build_campaigns
from route_timing import apply_route_timing, metric
from remake.march_core import using_backend
from remake.route_hazards import evaluate_leg
from remake.travel import TravelCampaign

# One equatorial degree on the game's spherical Earth, independently known.
EQUATOR_DEGREE = 111.19508372419142


def geographic_distance(first, second):
    lon1, lat1 = map(radians, first)
    lon2, lat2 = map(radians, second)
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.009 * 2 * atan2(sqrt(h), sqrt(max(0, 1-h)))


def curve(mode='land', start=(0, 0), end=(100, 0), length=150):
    return dict(mode=mode, start=list(start), end=list(end), length_px=length,
                chord_px=dist(start, end))


def fixture(mode='land', terrain='plain'):
    route = dict(id='a:b:'+mode, **{'from': 'a', 'to': 'b'}, mode=mode, terrain=terrain,
                 distance_km=99999, land_km=99999, sea_km=0, days=99999)
    data = dict(travel_rules=dict(speeds=dict(plain=30, mountain=15, desert=20, sea=70),
                                 detours=dict(plain=1.18, mountain=1.45, desert=1.3), embark_days=2),
                travel_hazards={}, city_coordinates={'a': [0, 0], 'b': [1, 0]},
                travel_routes=[route], sea_routes=[], exploration_routes=[])
    parts = [curve()]
    if mode == 'sea':
        route.update(geo=[[1, 0], [3, 0]], sea_km=99999)
        data['city_coordinates']['b'] = [4, 0]
        parts = [curve('land', length=150), curve('sea', (100, 0), (300, 0), 250),
                 curve('land', (300, 0), (400, 0), 200)]
    row = {**{k: route[k] for k in ('id', 'from', 'to', 'mode')}, 'parts': parts}
    return data, dict(schema='tk2-route-geometry-v1', routes={route['id']: row})


class RouteTimingTests(unittest.TestCase):
    def test_local_calibration_uses_curve_ratio_instead_of_a_global_pixel_scale(self):
        data, geometry = fixture()
        rules, coords, source = deepcopy(data['travel_rules']), deepcopy(data['city_coordinates']), deepcopy(geometry)
        apply_route_timing(data, geometry, 'current-geometry')
        route = data['travel_routes'][0]
        self.assertEqual(route['distance_km'], 196.8)
        self.assertEqual(route['distance_km'], round(EQUATOR_DEGREE * 1.5 * 1.18, 1))
        self.assertEqual(route['days'], 7)
        self.assertEqual(route['timing_geometry']['parts'][0]['shape_ratio'], 1.5)
        enlarged, enlarged_geometry = fixture()
        enlarged_geometry['routes'][route['id']]['parts'] = [curve(end=(1000, 0), length=1500)]
        apply_route_timing(enlarged, enlarged_geometry, 'larger-art')
        self.assertEqual(enlarged['travel_routes'][0]['distance_km'], route['distance_km'])
        self.assertEqual(enlarged['travel_routes'][0]['days'], route['days'])
        self.assertEqual(geometry, source)
        self.assertEqual(data['city_coordinates'], coords)
        for key in ('speeds', 'detours', 'embark_days'):
            self.assertEqual(data['travel_rules'][key], rules[key])
        self.assertEqual(data['travel_rules']['geometry_sha256'], 'current-geometry')

    def test_terrain_speed_is_applied_after_the_same_geographic_curve(self):
        results = {}
        for terrain in ('plain', 'mountain', 'desert'):
            data, geometry = fixture(terrain=terrain)
            # Equal detours isolate the terrain's speed contribution.
            data['travel_rules']['detours'] = dict(plain=1, mountain=1, desert=1)
            apply_route_timing(data, geometry, 'geometry')
            route = data['travel_routes'][0]
            self.assertEqual(route['land_km'], 166.8)
            results[terrain] = route['days']
        self.assertEqual(results, {'plain': 6, 'mountain': 12, 'desert': 9})

    def test_sea_time_includes_both_calibrated_approaches_and_embarkation(self):
        data, geometry = fixture(mode='sea', terrain='sea')
        data['sea_routes'] = deepcopy(data['travel_routes'])
        data['exploration_routes'] = deepcopy(data['travel_routes'])
        apply_route_timing(data, geometry, 'geometry')
        route = data['travel_routes'][0]
        self.assertEqual((route['land_km'], route['sea_km'], route['distance_km'], route['days']),
                         (459.2, 278.0, 737.2, 22))
        self.assertEqual(route, data['sea_routes'][0])
        self.assertEqual(route, data['exploration_routes'][0])
        self.assertEqual(route['days'], ceil(459.2/30) + ceil(278/70) + 2)
        # The queue rounds the entire itinerary once at ten-day boundaries.
        self.assertEqual(TravelCampaign._quote(['a', 'b'], [route])['turns'], 3)
        for days, turns in ((10, 1), (11, 2), (20, 2), (21, 3)):
            self.assertEqual(TravelCampaign._quote(['a', 'b'], [dict(route, days=days)])['turns'], turns)

    def test_stale_distances_are_replaced_but_special_and_monsoon_rules_are_retained(self):
        data, geometry = fixture(terrain='mountain')
        apply_route_timing(data, geometry, 'geometry')
        route = data['travel_routes'][0]
        self.assertEqual((route['distance_km'], route['days']), (241.8, 17))
        data['travel_hazards'] = dict(yinping={'from': 'a', 'to': 'b', 'time_multiplier': 2,
                                               'survival_numerator': 1, 'survival_denominator': 3})
        with using_backend('python'):
            quote = evaluate_leg(data, route, 'a', 'b', 7)
        self.assertEqual((quote['base_days'], quote['days']), (9, 18))
        self.assertEqual((quote['hazard']['survival_numerator'], quote['hazard']['survival_denominator']), (1, 3))
        data['travel_hazards'] = dict(ziwu={'from': 'a', 'to': 'b'})
        with using_backend('python'):
            rain, dry = [evaluate_leg(data, route, 'a', 'b', month) for month in (7, 4)]
        self.assertEqual((rain['days'], dry['days']), (36, 18))
        self.assertEqual((rain['hazard']['loss_percent'], dry['hazard']['loss_percent']), (50, 20))
        data, geometry = fixture(mode='sea', terrain='sea')
        apply_route_timing(data, geometry, 'geometry')
        before = deepcopy(data)
        with using_backend('python'):
            tail = evaluate_leg(data, data['travel_routes'][0], 'a', 'b', 7)
            head = evaluate_leg(data, data['travel_routes'][0], 'b', 'a', 7)
        self.assertEqual((tail['days'], head['days']), (21, 56))
        self.assertEqual((tail['hazard']['speed_km_per_day'], head['hazard']['speed_km_per_day']), (120, 7.5))
        self.assertEqual((tail['hazard']['loss_percent_min'], tail['hazard']['loss_percent_max']), (80, 90))
        self.assertEqual(data, before, 'Quotes do not mutate route data or draw RNG')

    def test_unknown_endpoints_missing_curves_and_inconsistent_copies_are_rejected(self):
        for key, value in (('from', 'other'), ('to', 'other'), ('mode', 'sea')):
            data, geometry = fixture()
            geometry['routes']['a:b:land'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'mismatched rendered route'):
                apply_route_timing(data, geometry, 'geometry')
        data, geometry = fixture()
        geometry['routes'].clear()
        with self.assertRaisesRegex(ValueError, 'Missing or mismatched'):
            apply_route_timing(data, geometry, 'geometry')
        data, geometry = fixture(mode='sea', terrain='sea')
        data['sea_routes'] = [dict(data['travel_routes'][0], geo=[[.5, 0], [3.5, 0]])]
        with self.assertRaisesRegex(ValueError, 'inconsistent timing copies'):
            apply_route_timing(data, geometry, 'geometry')
        for part in (curve(length=99), dict(curve(), chord_px=99), curve(end=(0, 0), length=1),
                     curve(length=float('nan')), curve(length=-1)):
            with self.subTest(part=part), self.assertRaisesRegex(ValueError, 'Invalid compiled route curve'):
                metric(part)

    def test_changed_source_or_draw_is_rejected_before_catalog_generation(self):
        for field in ('draw', 'other-source'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root/'game/config').mkdir(parents=True)
                navigation = root/'game/config/navigation-geometry.json'
                navigation.write_text(json.dumps(dict(schema='sea-mask-navigation-geometry-v1',
                    land_roads=[dict(draw=[dict(mode='land', points=[[0, 0], [10, 0]])])])))
                expected = sha256(navigation.read_bytes()).hexdigest()
                geometry = dict(schema='tk2-route-geometry-v1', sources={'game/config/navigation-geometry.json': expected})
                (root/'game/config/route-geometry.json').write_text(json.dumps(geometry))
                (root/'game/route_timing.py').write_text('source fingerprint\n')
                if field == 'draw':
                    source = json.loads(navigation.read_text())
                    source['land_roads'][0]['draw'][0]['points'][1][0] = 20
                    navigation.write_text(json.dumps(source))
                else:
                    navigation.write_text(navigation.read_text()+'\n')
                with patch.object(build_campaigns, 'ROOT', root), self.assertRaisesRegex(ValueError, 'geometry source differs'):
                    build_campaigns.load_sources()


class FullCatalogRouteTimingTests(unittest.TestCase):
    def test_all_current_catalog_routes_use_current_curves_and_keep_the_logical_graph(self):
        read = lambda name: json.loads((ROOT/name).read_text())
        geometry_path = ROOT/'game/config/route-geometry.json'
        geometry = json.loads(geometry_path.read_text())
        fingerprint = sha256(geometry_path.read_bytes()+(ROOT/'game/route_timing.py').read_bytes()).hexdigest()
        shared = read('game/config/campaigns/shared.json')['catalog']
        navigation = read('game/config/navigation-geometry.json')
        index = read('game/config/campaigns/index.json')
        self.assertEqual(len(index['scenarios']), 25)
        checked, changed, copies = 0, 0, {}
        for scenario in index['scenarios']:
            source = read('game/config/campaigns/'+scenario['file'])
            original = build_campaigns.apply_patch(shared, source.get('overrides', {}))
            compiled = read('game/data/campaigns/'+scenario['id'].removeprefix('mainland')+'.json')
            expected_links = original['links']+[[r['from'], r['to']] for r in navigation['land_roads']]
            self.assertEqual(compiled['links'], expected_links, scenario['id'])
            self.assertEqual(compiled['city_coordinates'], original['city_coordinates'])
            self.assertEqual(compiled['cities'], original['cities'])
            self.assertEqual(compiled['travel_rules']['geometry_sha256'], fingerprint)
            for key in ('speeds', 'detours', 'embark_days'):
                self.assertEqual(compiled['travel_rules'][key], original['travel_rules'][key])
            self.assertEqual(compiled['travel_hazards'], original['travel_hazards'])
            for field in ('travel_routes', 'sea_routes', 'exploration_routes'):
                expected_ids = [r['id'] for r in original[field]]
                if field == 'travel_routes':
                    expected_ids += [f"{r['from']}:{r['to']}:land" for r in navigation['land_roads']]
                self.assertEqual([r['id'] for r in compiled[field]], expected_ids, (scenario['id'], field))
                old_rows = {r['id']: r for r in original[field]}
                for route in compiled[field]:
                    row = geometry['routes'][route['id']]
                    self.assertEqual({k: row[k] for k in ('from', 'to', 'mode')},
                                     {k: route[k] for k in ('from', 'to', 'mode')})
                    metrics = route['timing_geometry']['parts']
                    self.assertEqual(len(metrics), len(row['parts']))
                    for actual, part in zip(metrics, row['parts']):
                        self.assertAlmostEqual(part['chord_px'], dist(part['start'], part['end']), delta=.002)
                        self.assertGreaterEqual(part['length_px']+.002, part['chord_px'])
                        self.assertEqual(actual['shape_ratio'], round(max(1, part['length_px']/part['chord_px']) if part['chord_px'] else 1, 9))
                    coords, rules = compiled['city_coordinates'], compiled['travel_rules']
                    if route['mode'] == 'land':
                        part = row['parts'][0]
                        straight = geographic_distance(coords[route['from']], coords[route['to']])
                        expected_land = round(straight * part['length_px']/part['chord_px'] * rules['detours'][route['terrain']], 1)
                        self.assertEqual(route['land_km'], expected_land)
                        self.assertEqual(route['sea_km'], 0)
                        self.assertEqual(route['days'], ceil(expected_land/rules['speeds'][route['terrain']]))
                    else:
                        self.assertEqual([m['mode'] for m in metrics], ['land', 'sea', 'land'])
                        ratios = [max(1, p['length_px']/p['chord_px']) if p['chord_px'] else 1 for p in row['parts']]
                        ports = route['geo']
                        expected_land = round((geographic_distance(coords[route['from']], ports[0])*ratios[0]
                                               + geographic_distance(ports[-1], coords[route['to']])*ratios[2])
                                              * rules['detours']['plain'], 1)
                        expected_sea = round(geographic_distance(ports[0], ports[-1])*ratios[1], 1)
                        self.assertEqual((route['land_km'], route['sea_km']), (expected_land, expected_sea))
                        self.assertEqual(route['days'], ceil(route['land_km']/rules['speeds']['plain'])
                                         + ceil(route['sea_km']/rules['speeds']['sea']) + rules['embark_days'])
                    self.assertEqual(route['distance_km'], round(route['land_km']+route['sea_km'], 1))
                    physical = {k: route[k] for k in ('distance_km', 'land_km', 'sea_km', 'days', 'timing_geometry')}
                    if route['id'] in copies:
                        self.assertEqual(physical, copies[route['id']], (scenario['id'], field, route['id']))
                    copies[route['id']] = physical
                    if route['id'] in old_rows and any(route[k] != old_rows[route['id']][k] for k in ('distance_km', 'days')):
                        changed += 1
                    checked += 1
        self.assertGreater(checked, 9000)
        self.assertGreater(changed, 0, 'The rebuild must replace stale source-era distances')


if __name__ == '__main__':
    unittest.main()
