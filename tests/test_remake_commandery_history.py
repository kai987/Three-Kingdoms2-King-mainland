"""Dated commandery openings, authoritative paths and monthly city initialization."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import city_development, facilities, treasures
from remake.campaign import Campaign, Catalog
from remake.map_presentation import city_names


class CommanderyHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = {path.stem: Catalog(path) for path in (ROOT / 'game/data/campaigns').glob('*.json')
                        if path.name != 'index.json'}
        cls.review = json.loads((ROOT / 'game/config/campaigns/commandery-history.json').read_text())
        cls.geometry = json.loads((ROOT / 'game/config/route-geometry.json').read_text())['routes']

    def test_all_openings_have_exact_city_domains_resources_and_roads(self):
        self.assertEqual(len(self.catalogs), 29)
        for scenario, catalog in self.catalogs.items():
            game = Campaign(catalog)
            state = game._new(next(iter(catalog.factions)), 2026)
            active = set(state.cities)
            self.assertEqual(active, set(catalog.data['initial_owners']), scenario)
            self.assertEqual(active, set(catalog.active_city_ids(state.year, state.month)), scenario)
            routes = game._known_routes(state)
            for city in self.review['new_sites']:
                with self.subTest(scenario=scenario, city=city):
                    self.assertTrue(all(value > 0 for value in catalog.data['city_income'][city].values()))
                    roads = [route for route in routes if city in (route['from'], route['to'])]
                    if city not in active:
                        peer = self.review['new_sites'][city]['parent']
                        self.assertIsNone(game._travel_path(state, peer, city, state.cities[peer].owner,
                                                            'land', adjacent=True))
                        continue
                    self.assertTrue(any({road['from'], road['to']} <= active for road in roads))
                    self.assertEqual(state.cities[city].owner, catalog.data['city_history'][city]['opening']['owner'])
                    for road in roads:
                        self.assertGreater(road['days'], 0)
                        for segment in self.geometry[road['id']]['parts']:
                            self.assertGreater(segment['length_px'], 0)
        self.assertEqual(self.geometry['langya:dongguan:land']['parts'][0]['end'], [1038, 275])
        self.assertTrue({'yiyang', 'yiyang_runan'} <= self.catalogs['225-07'].map_cities.keys())

    def test_historical_dates_and_owners(self):
        for scenario, expected in {
            '184-02': dict(liang='han', pengcheng='han', daifang=None),
            '194-06': dict(pengcheng='tao_qian', guangwei='ma_teng', xijun='neutral', xihai=None),
            '198-03': dict(pengcheng='lubu', dongguan=None, chengyang=None),
            '200-01': dict(pengcheng='wei', dongguan='wei', chengyang='wei', daifang=None),
            '207-09': dict(daifang='gongsun', lelang='gongsun', lean='wei', nanxiang=None),
            '208-10': dict(nanxiang='wei', daifang='gongsun'),
            '215-08': dict(zhangwu='wei', leling='wei', leping='wei', guangwei=None),
            '219-07': dict(yiyang_runan='wei', guangwei=None),
            '221-07': dict(guangping='wei', yiyang_runan='wei', guangwei='wei', ruyin=None),
            '227-02': dict(ruyin='wei', guangwei='wei', daifang='gongsun'),
            '234-02': dict(guangwei='wei', ruyin='wei'),
            '238-01': dict(daifang='gongsun'),
            '249-01': dict(daifang='wei', lelang='wei', ruyin='wei', zhangwu='wei'),
            '263-05': dict(ruyin=None, zhangwu=None, xijun='wei', shixing=None, shian=None),
        }.items():
            owners = self.catalogs[scenario].data['initial_owners']
            self.assertEqual({city: owners.get(city) for city in expected}, expected, scenario)
        old = self.catalogs['200-01']
        self.assertEqual(city_names(old, 200, 1)['guangwei'], '永阳')
        self.assertEqual(city_names(old, 221, 1)['xicheng'], '魏兴')
        gap = self.catalogs['215-08']
        self.assertNotIn('guangwei', gap.active_city_ids(220, 10))
        self.assertIn('guangwei', gap.active_city_ids(220, 11))
        self.assertEqual(city_names(gap, 220, 11)['guangwei'], '广魏')
        self.assertNotIn('daifang', old.active_city_ids(203, 12))
        self.assertIn('daifang', old.active_city_ids(204, 1))
        late = self.catalogs['263-05']
        self.assertNotIn('zhangwu', late.active_city_ids(264, 12))
        self.assertIn('zhangwu', late.active_city_ids(265, 1))
        self.assertNotIn('ruyin', late.active_city_ids(265, 12))
        self.assertIn('ruyin', late.active_city_ids(266, 1))

    def test_new_castles_have_room_at_native_map_scale(self):
        data = json.loads((ROOT / 'game/assets/map-presentation.json').read_text())
        pixels = {(x + dx, y + dy) for x, y in data['castle_fill_pixels'] + data['castle_outline_pixels']
                  for dx in range(4) for dy in range(4)}
        positions = self.catalogs['249-01'].map_cities
        stamps = {key: {(city['position'][0] + x, city['position'][1] + y) for x, y in pixels}
                  for key, city in positions.items()}
        for key in self.review['new_sites']:
            overlaps = [other for other in stamps if other != key and stamps[key] & stamps[other]]
            self.assertFalse(overlaps, (key, overlaps))

    def test_same_month_openings_balance_stocks_and_run_each_initializer_once(self):
        game = Campaign(self.catalogs['263-05'])
        state = game._new('wu', 2026)
        before = {key: (state.cities[key].owner, state.cities[key].gold, state.cities[key].grain,
                        state.cities[key].reserves) for key in ('guiyang', 'lingling', 'hejian')}
        old_rng = (state.rng.state, state.rng.draws)
        with (patch.object(facilities, 'synchronize', wraps=facilities.synchronize) as facility,
              patch.object(city_development, 'synchronize', wraps=city_development.synchronize) as development,
              patch.object(treasures, 'synchronize', wraps=treasures.synchronize) as treasury):
            state.year, state.month = 264, 12
            game._open_dated_cities(state)
            self.assertTrue({'shixing', 'shian'}.isdisjoint(state.cities))
            state.year, state.month = 265, 1
            game._open_dated_cities(state)
            opened = game.to_dict(state)
            game._open_dated_cities(state)
            self.assertEqual(game.to_dict(state), opened)
            for initializer in (facility, development, treasury):
                initializer.assert_called_once_with(game, state)
        for city, parent in (('shixing', 'guiyang'), ('shian', 'lingling'), ('zhangwu', 'hejian')):
            child, original = state.cities[city], state.cities[parent]
            self.assertEqual(child.owner, before[parent][0])
            self.assertFalse(child.roster.officer_ids)
            for field, value in zip(('gold', 'grain', 'reserves'), before[parent][1:]):
                self.assertEqual(getattr(child, field), value // 4)
                self.assertEqual(getattr(original, field) + getattr(child, field), value)
        self.assertEqual((state.rng.state, state.rng.draws), old_rng)
