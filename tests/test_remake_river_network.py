"""Shared water trunks, real city approaches and backend metadata parity."""
from collections import Counter
from copy import deepcopy
import json
from math import ceil, dist
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'game'), str(ROOT / 'source')]
from river_network import build, compile_network
from remake.march_core import using_backend
from remake.route_hazards import evaluate_leg


class SharedRiverNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / 'game/config/river-network.json').read_text())
        shared = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']
        cls.positions = {row['id']: row['position'] for row in shared['cities']}
        cls.compiled = build()

    def test_fixed_city_nodes_and_shared_junctions_compile_without_mutating_sources(self):
        spec = self.spec
        before = deepcopy(spec)
        routes = compile_network(spec, self.positions)
        self.assertEqual(spec, before)
        self.assertEqual(len(routes), 45)
        self.assertEqual(len({row['id'] for row in routes}), len(routes))
        self.assertEqual(self.compiled['reach_count'], 49)
        for route in routes:
            self.assertEqual(route['draw'][0]['points'][0], self.positions[route['from']])
            self.assertEqual(route['draw'][-1]['points'][-1], self.positions[route['to']])
            for a, b in zip(route['draw'], route['draw'][1:]):
                self.assertEqual(a['points'][-1], b['points'][0])
            self.assertEqual(len(route['geo']), len(route['river_segments']) + 1)
            self.assertEqual([part['mode'] for part in route['draw']],
                             ['land'] + ['river'] * len(route['river_segments']) + ['land'])

    def test_every_water_reach_and_city_approach_is_reused_instead_of_redrawn(self):
        canonical = {row['id']: row['points'] for row in self.spec['reaches']}
        usage = Counter()
        for route in self.compiled['routes']:
            for part, segment in zip(route['draw'][1:-1], route['river_segments']):
                identity = part['reach_id']
                self.assertEqual(segment['reach_id'], identity)
                self.assertIn(part['points'], (canonical[identity], list(reversed(canonical[identity]))))
                usage[identity] += 1
            for city, part in ((route['from'], route['draw'][0]), (route['to'], route['draw'][-1])):
                expected = self.spec['ports'][city]['access']
                self.assertEqual(part['access_id'], city)
                self.assertIn(part['points'], (expected, list(reversed(expected))))
        self.assertEqual(set(usage), set(canonical))
        self.assertEqual(usage['yangtze:dongting:jiangxia'], 3)
        self.assertEqual(usage['yangtze:pengli:lujiang'], 2)
        self.assertEqual(usage['xiang:changsha:yuan'], 2)

    def test_dated_optional_ports_do_not_cut_the_main_river_when_city_is_absent(self):
        bypasses = {row['optional_port_bypass']: row for row in self.spec['connections']
                    if 'optional_port_bypass' in row}
        self.assertEqual(set(bypasses), {'yidu', 'wuchang'})
        reached = Counter()
        for path in (ROOT / 'game/data/campaigns').glob('*.json'):
            if path.name == 'index.json':
                continue
            catalog = json.loads(path.read_text())
            active = set(catalog['active_cities'])
            for city, row in bypasses.items():
                if city not in active and {row['from'], row['to']} <= active:
                    route = next(route for route in self.compiled['routes']
                                 if (route['from'], route['to']) == (row['from'], row['to']))
                    self.assertEqual([part['reach_id'] for part in route['draw'][1:-1]], row['reaches'])
                    reached[city] += 1
        self.assertTrue(all(reached[city] > 0 for city in bypasses))
        early = json.loads((ROOT / 'game/data/campaigns/207-09.json').read_text())
        self.assertNotIn('yidu', early['active_cities'])
        self.assertTrue({'badong', 'nanjun'} <= set(early['active_cities']))

    def test_unverified_upper_navigation_is_removed_without_claiming_all_boats_impossible(self):
        ids = {row['id'] for row in self.compiled['routes']}
        self.assertNotIn('tianshui:fufeng:river', ids)
        self.assertNotIn('wenshan:shujun:river', ids)
        self.assertIn('fufeng:jingzhao:river', ids)
        self.assertIn('shujun:qianwei:river', ids)
        land = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']['travel_routes']
        land_pairs = {frozenset((r['from'], r['to'])) for r in land if r['mode'] == 'land'}
        self.assertIn(frozenset(('tianshui', 'fufeng')), land_pairs)
        self.assertIn(frozenset(('wenshan', 'shujun')), land_pairs)

    def test_gan_mainstem_bypasses_linchuan_and_linchuan_is_an_explicit_land_transfer(self):
        routes = {r['id']: r for r in self.compiled['routes']}
        trunk = routes['luling:yuzhang:river']
        self.assertEqual([p['reach_id'] for p in trunk['draw'][1:-1]],
                         ['gan:luling:middle', 'gan:middle:yuzhang'])
        self.assertNotIn('gan:linchuan', self.spec['nodes'])
        self.assertNotIn('luling:linchuan:river', routes)
        transfer = routes['linchuan:yuzhang:river']
        self.assertEqual(transfer['history']['classification'], 'authorial_land_transfer_to_gan_landing')
        self.assertEqual(self.spec['ports']['linchuan']['node'], 'gan:middle')
        self.assertIn('旴水', transfer['history']['basis'])

    def test_wo_branch_reuses_the_huai_trunk_and_documents_the_pre219_city_proxy(self):
        routes = {r['id']: r for r in self.compiled['routes']}
        wo = routes['qiao:jiujiang:river']
        huai = routes['runan:jiujiang:river']
        self.assertEqual(wo['draw'][-2], huai['draw'][-2])
        self.assertEqual(wo['river_segments'][0]['river_id'], 'wo')
        self.assertIn('小沛', wo['history']['basis'])
        self.assertIn('非首通年代', wo['history']['basis'])
        self.assertNotIn('availability', wo)
        self.assertTrue(all(segment['downstream_from'] == 'qiao' for segment in wo['river_segments']))
        water = ET.parse(ROOT / 'game/map-source/historic-water.svg').getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        group = water.find('.//svg:g[@data-authorial-addition="wo-huai"]', ns)
        self.assertIsNotNone(group)
        self.assertTrue(group.findall('svg:rect', ns))
        self.assertTrue(all(rect.attrib['fill'] == '#002af8' and rect.attrib['width'] == '2'
                            for rect in group.findall('svg:rect', ns)))

    def test_named_river_polylines_stay_on_existing_water_and_never_invent_terrain(self):
        water = set()
        svg = ET.parse(ROOT / 'game/map-source/historic-water.svg').getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        for group in svg.findall('.//svg:g[@data-river]', ns):
            for rect in group.findall('.//svg:rect', ns):
                x, y, w, h = (int(rect.attrib[key]) for key in ('x', 'y', 'width', 'height'))
                water.update((xx - 136, yy) for xx in range(x, x + w) for yy in range(y, y + h))
        wei = json.loads((ROOT / 'game/config/water-corrections.json').read_text())['wei']
        for a, b in zip(wei['points'], wei['points'][1:]):
            count = max(abs(b[0]-a[0]), abs(b[1]-a[1])) * 2
            for i in range(count + 1):
                x = round(a[0] + (b[0]-a[0]) * i / count)
                y = round(a[1] + (b[1]-a[1]) * i / count)
                water.update((x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
        for reach in self.spec['reaches']:
            for a, b in zip(reach['points'], reach['points'][1:]):
                count = max(1, ceil(dist(a, b)))
                for i in range(count + 1):
                    x = round(a[0] + (b[0]-a[0]) * i / count)
                    y = round(a[1] + (b[1]-a[1]) * i / count)
                    self.assertTrue(any((x+dx, y+dy) in water for dx in range(-1, 2) for dy in range(-1, 2)),
                                    (reach['id'], (x, y)))

    def test_all_named_segments_survive_python_rust_quotes_without_ocean_weather(self):
        rules = json.loads((ROOT / 'game/config/route-corridors.json').read_text())['river_rules']
        data = dict(travel_rules=dict(deepcopy(rules), speeds=dict(plain=30)), travel_hazards={})
        for original in self.compiled['routes']:
            raw = deepcopy(original)
            raw.update(distance_km=100, land_km=30, river_km=70, sea_km=0, days=5)
            for segment in raw['river_segments']:
                segment['distance_km'] = 70 / len(raw['river_segments'])
            before = deepcopy(raw)
            for source, target in ((raw['from'], raw['to']), (raw['to'], raw['from'])):
                previous = None
                for month in (1, 7):
                    for backend in ('python', 'rust'):
                        with self.subTest(route=raw['id'], source=source, month=month, backend=backend), using_backend(backend):
                            quote = evaluate_leg(data, raw, source, target, month)
                        self.assertIsNone(quote['hazard'])
                        for plain, quoted in zip(raw['river_segments'], quote['river_segments']):
                            for key in ('reach_id', 'river_id', 'name_tc', 'name_ja', 'speed_key'):
                                self.assertEqual(quoted[key], plain[key])
                            self.assertEqual(quoted['flow'], 'downstream' if plain['downstream_from'] == source else 'upstream')
                        if previous is None:
                            previous = quote
                        else:
                            self.assertEqual(quote, previous)
            self.assertEqual(raw, before)

    def test_invalid_networks_fail_before_producing_partial_city_routes(self):
        for value in (True, float('nan'), float('inf')):
            bad = deepcopy(self.spec)
            next(iter(bad['nodes'].values()))['position'][0] = value
            with self.assertRaises(ValueError):
                compile_network(bad, self.positions)
        bad = deepcopy(self.spec)
        bad['connections'].append(deepcopy(bad['connections'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate playable'):
            compile_network(bad, self.positions)
        bad = deepcopy(self.spec)
        bad['connections'][0]['reaches'].reverse()
        # Pick a multi-reach connection so reversal actually disconnects it.
        row = next(row for row in bad['connections'] if len(row['reaches']) > 1)
        row['reaches'].reverse()
        with self.assertRaisesRegex(ValueError, 'Disconnected'):
            compile_network(bad, self.positions)
        bad = deepcopy(self.spec)
        bad['connections'][0]['history'] = {'classification': 'unsupported'}
        with self.assertRaisesRegex(ValueError, 'Invalid reviewed river history'):
            compile_network(bad, self.positions)


if __name__ == '__main__':
    unittest.main()
