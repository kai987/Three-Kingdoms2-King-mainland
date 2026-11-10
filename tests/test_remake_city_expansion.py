"""Playable 266-map additions in historical and hypothetical campaign openings."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'game')]
from build_campaigns import apply_patch
from remake.campaign import Campaign, Catalog
from remake.city_economy import apply_opening_sizes
from remake.map_presentation import city_names
from remake.march_core import using_backend


OLD_COUNTIES = {'hefei', 'guangling', 'chaisang', 'xicheng', 'shangyong', 'yiling'}
FOUNDINGS = {'changli': (244, 9), 'pingyang': (247, 5), 'hengyang': (257, 2),
             'xiangdong': (257, 2), 'jianping': (260, 1)}
ADDITIONS = OLD_COUNTIES | FOUNDINGS.keys()


def read(path):
    return json.loads((ROOT / path).read_bytes())


class Headless(Campaign):
    def view(self):
        return {'revision': self.revision}


class CityExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = read('game/config/campaigns/shared.json')['catalog']
        cls.city_scale = read('game/config/city-scale-rules.json')
        index = read('game/config/campaigns/index.json')
        cls.entries = {row['id']: row for row in index['scenarios']}
        cls.catalogs = {
            scenario: Catalog(ROOT / 'game/data/campaigns' / (scenario.removeprefix('mainland') + '.json'))
            for scenario in cls.entries
        }
        cls.plan = read('game/config/campaigns/city-expansion-openings.json')['scenarios']
        cls.chronology = read('game/config/campaigns/city-chronology-openings.json')

    def start(self, scenario, faction=None):
        catalog = self.catalogs[scenario]
        game = Headless(catalog)
        game.command('new', {'faction': faction or next(iter(catalog.factions)),
                             'seed': 2026, 'difficulty': 'normal'}, 0)
        return game

    def test_all_29_openings_preserve_legacy_locations_and_use_dated_rosters(self):
        self.assertEqual(len(self.catalogs), 29)
        self.assertEqual(set(self.plan), set(self.catalogs))
        legacy = {row['id']: row['position'] for row in self.shared['cities']}
        for scenario, catalog in self.catalogs.items():
            date = (catalog.data['start_year'], catalog.data['start_month'])
            with self.subTest(scenario=scenario):
                source = read('game/config/campaigns/' + self.entries[scenario]['file'])
                original = apply_patch(self.shared, source.get('overrides', {}))
                apply_opening_sizes(original, self.city_scale)
                expected = OLD_COUNTIES | {city for city, opening in FOUNDINGS.items() if opening <= date}
                plan = self.plan[scenario]
                self.assertEqual(set(plan['owners']), expected)
                game = self.start(scenario)
                state = game.state
                reviewed_owners = {key: owner for key, owner in self.chronology['owners'][scenario].items()
                                   if owner is not None}
                self.assertEqual(set(state.cities), set(original['active_cities']) | expected | reviewed_owners.keys())
                self.assertEqual(set(state.cities), set(catalog.active_city_ids(*date)))
                self.assertEqual(set(catalog.map_cities), set(legacy) | ADDITIONS)
                self.assertEqual({key: catalog.map_cities[key]['position'] for key in legacy}, legacy)
                self.assertEqual({key: catalog.data['city_coordinates'][key] for key in legacy},
                                 self.shared['city_coordinates'])
                legacy_owners = original['initial_owners'] | reviewed_owners
                self.assertEqual({key: state.cities[key].owner for key in legacy_owners}, legacy_owners)
                for field in ('initial_city_resources', 'city_income'):
                    self.assertEqual({key: catalog.data[field][key] for key in legacy}, original[field])
                self.assertEqual({key: state.cities[key].owner for key in expected}, plan['owners'])
                for city in expected | reviewed_owners.keys() | {'gaoliang', 'xiping'}:
                    self.assertTrue(set(game._neighbors(city, state)).intersection(state.cities), city)
                    self.assertTrue(game._city_occupancy(state, state.cities[city]) <= 99, city)
                    if state.cities[city].owner == 'neutral':
                        self.assertEqual(state.cities[city].roster.officer_ids, [])
                for city, people in plan['garrisons'].items():
                    for person in people:
                        officer = state.officers[catalog.ids[person]]
                        self.assertIn(catalog.ids[person], state.cities[city].roster.officer_ids)
                        self.assertEqual(officer.faction_id, state.cities[city].owner)
                        self.assertTrue(officer.alive)
                self.assertEqual(state.rng.draws, 0)

    def test_reviewed_old_county_roads_owners_and_historical_garrisons(self):
        for scenario, city, owner, people in [
            ('mainland184-02', 'wuchang', 'neutral', ()),
            ('mainland196-06', 'jianan', 'wang_lang', ()),
            ('mainland208-10', 'wuchang', 'wu', ('0303',)),
            ('mainland234-02', 'wuchang', 'wu', ('0902',)),
            ('mainland238-01', 'wuchang', 'wu', ('0902',)),
            ('mainland249-01', 'wuchang', 'wu', ('0430', '0985')),
        ]:
            with self.subTest(scenario=scenario, city=city):
                game = self.start(scenario)
                state = game.state
                self.assertEqual(state.cities[city].owner, owner)
                people = {'san14-candidate-' + person for person in people}
                self.assertEqual({state.officers[i].person_id for i in state.cities[city].roster.officer_ids}, people)
                self.assertEqual({p['person_id'] for p in game.catalog.data['city_history'][city]['garrisons']}, people)
        for chapter, origin, destination, mode in [
            ('mainland184-02', 'jiangxia', 'wuchang', 'land'),
            ('mainland184-02', 'qichun', 'wuchang', 'river'),
            ('mainland196-06', 'poyang', 'jianan', 'land'),
            ('mainland217-07', 'xindu', 'jianan', 'land'),
            ('mainland263-05', 'linhai', 'jianan', 'land'),
        ]:
            with self.subTest(chapter=chapter, origin=origin, destination=destination):
                game = self.start(chapter)
                quote = game._travel_path(game.state, origin, destination, game.state.cities[origin].owner,
                                          mode, adjacent=True)
                self.assertEqual(quote['path'], [origin, destination])
                self.assertGreater(quote['days'], 0)

    def test_primary_source_garrisons_and_late_ownership(self):
        for scenario, city, owner, people in [
            ('mainland200-01', 'hefei', 'wei', ('0956',)),
            ('mainland215-08', 'hefei', 'wei', ('0663', '0913', '0102')),
            ('mainland219-07', 'xicheng', 'shu', ('0455',)),
            ('mainland219-07', 'shangyong', 'shu', ('0463',)),
            ('mainland249-01', 'chaisang', 'wu', ('0900',)),
            ('mainland263-05', 'yiling', 'wu', ('0833',)),
            ('mainland263-05', 'hefei', 'wei', ('0650',)),
        ]:
            with self.subTest(scenario=scenario, city=city):
                game = self.start(scenario, owner)
                roster = game.state.cities[city].roster.officer_ids
                self.assertEqual(game.state.cities[city].owner, owner)
                self.assertLessEqual({'san14-candidate-' + person for person in people},
                                     {game.state.officers[ident].person_id for ident in roster})
        late = self.start('mainland263-05').state
        self.assertEqual({city: late.cities[city].owner for city in FOUNDINGS},
                         dict(changli='wei', pingyang='wei', hengyang='wu', xiangdong='wu', jianping='wu'))

    def test_both_era_name_cutovers_keep_the_same_city_ids(self):
        catalog = self.catalogs['mainland263-05']
        for city, date, expected in [
            ('yiling', (221, 7), '夷陵'),
            ('yiling', (222, 12), '夷陵'),
            ('yiling', (223, 1), '西陵'),
            ('hepu', (227, 12), '合浦'),
            ('hepu', (228, 1), '珠官'),
            ('hepu', (249, 1), '珠官'),
            ('hepu', (258, 9), '珠官'),
            ('hepu', (258, 10), '合浦'),
            ('hepu', (263, 5), '合浦'),
        ]:
            with self.subTest(city=city, date=date):
                self.assertEqual(city_names(catalog, *date)[city], expected)

    def test_active_expansion_routes_have_contiguous_geometry_and_real_quotes(self):
        with using_backend('python'):
            game = self.start('mainland263-05')
            active = set(game.state.cities)
            roads = {city for city in ADDITIONS if any(
                route['mode'] == 'land' and city in (route['from'], route['to'])
                and {route['from'], route['to']} <= active for route in game._known_routes(game.state))}
            self.assertEqual(roads, ADDITIONS)
            for source, target, mode in [
                ('hefei', 'danyang', 'land'), ('guangling', 'danyang', 'river'),
                ('chaisang', 'qichun', 'river'), ('xicheng', 'hanzhong', 'river'),
                ('shangyong', 'xincheng', 'land'), ('yiling', 'yidu', 'river'),
                ('yingchuan', 'xiangyang', 'land'), ('taiyuan', 'pingyang', 'land'),
                ('pingyang', 'hedong', 'land'),
                ('hengyang', 'changsha', 'river'), ('xiangdong', 'hengyang', 'river'),
                ('jianping', 'badong', 'river'),
            ]:
                with self.subTest(source=source, target=target, mode=mode):
                    route = next(route for route in game._known_routes(game.state)
                                 if {route['from'], route['to']} == {source, target}
                                 and route['mode'] == mode)
                    points = route['draw']
                    positions = game.catalog.map_cities
                    self.assertEqual(points[0]['points'][0], positions[route['from']]['position'])
                    self.assertEqual(points[-1]['points'][-1], positions[route['to']]['position'])
                    for first, second in zip(points, points[1:]):
                        self.assertEqual(first['points'][-1], second['points'][0])
                    quote = game._travel_path(game.state, source, target, game.state.cities[source].owner,
                                              mode, adjacent=True)
                    self.assertGreater(quote['days'], 0)
                    self.assertGreater(quote['distance_km'], 0)
                    if mode == 'river':
                        self.assertEqual(quote['path'], [source, target])
                        self.assertEqual(quote['modes'], ['river'])
                        self.assertIsNone(quote['routes'][0]['hazard'])

    def test_liaoxi_coast_has_one_corridor_and_uses_changli_only_when_active(self):
        trunk = 'liaodong:liaoxi:land'
        for scenario, stops in [('mainland238-01', ['liaoxi']),
                                ('mainland249-01', ['changli', 'liaoxi'])]:
            with self.subTest(scenario=scenario), using_backend('python'):
                game = self.start(scenario)
                state = game.state
                # Find exactly the playable sections of the single painted road.
                coast = [route for route in game._known_routes(state)
                         if route.get('parent_route') == trunk]
                chain = ['liaodong', *stops]
                self.assertEqual([(route['from'], route['to']) for route in coast],
                                 list(zip(chain, chain[1:])))
                self.assertTrue(all('draw' not in route for route in coast))
                self.assertEqual(len([route for route in game.catalog.data['travel_routes']
                                      if route['id'] == trunk]), 1)
                owner = state.cities['liaodong'].owner
                self.assertTrue(game._travel_path(state, 'liaodong', stops[0], owner,
                                                  'land', adjacent=True))
                self.assertEqual(bool(game._travel_path(state, 'liaodong', 'liaoxi', owner,
                                                       'land', adjacent=True)), len(stops) == 1)
                self.assertEqual(bool(game._travel_path(state, 'taiyuan', 'pingyang',
                                                       state.cities['taiyuan'].owner,
                                                       'land', adjacent=True)), len(stops) > 1)


if __name__ == '__main__':
    unittest.main()
