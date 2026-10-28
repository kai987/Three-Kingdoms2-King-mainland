"""Historical road stops, dated corridors, food and native-reference parity.

The synthetic road bends through real city vertices, rather than adding city
stops by proximity. A missing opening city keeps the physical road continuous;
a living city participates in control, food and arrival routing.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
sys.path.insert(0, str(ROOT / 'source'))
from route_timing import apply_route_timing, compile_transit
from remake.campaign import canonical
from remake.march_core import CoreUnavailable, invoke, using_backend
from remake.march_supply import advance_unit, create, estimate, initial_days
from remake.route_network import available, effective, variants, valid_departure
from remake.travel import TravelCampaign

# Frozen from the approved b39563d canonical city positions and hazard rules.
# Geometry revisions may change distance/day quotes; these player choices stay.
POSITIONS_SHA = '91a45ddd1005028f4f20779946104df3bab590aab30a0c63c1d17f24a810d38d'
HAZARDS_SHA = '46a2caa869659c94dc754c38b3c1d61a09e997cca27643609602c268564a27f1'


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode()).hexdigest()


def fixture(availability=None):
    # Each 0.009 equatorial degrees rounds to1km. Three independent one-day
    # sections preserve the existing round-up-at-each-city timing policy.
    ids = ['s', 'a', 'b', 't']
    route = dict(id='s:t:land', **{'from': 's', 'to': 't'}, mode='land',
                 terrain='plain', days=999, land_km=999, sea_km=0, distance_km=999)
    if availability:
        route['availability'] = deepcopy(availability)
    data = dict(travel_rules=dict(speeds=dict(plain=30, mountain=15, desert=20, sea=70),
                                 detours=dict(plain=1, mountain=1.45, desert=1.3), embark_days=2),
                travel_hazards=dict(coastal_cities=[]),
                city_coordinates={city: [n*.009, 0] for n, city in enumerate(ids)},
                travel_routes=[route], sea_routes=[], exploration_routes=[], links=[['s', 't']])
    sections = [dict(**{'from': a, 'to': b}, parts=[dict(mode='land',
        start=[n*10, 0], end=[(n+1)*10, 0], length_px=10, chord_px=10)])
        for n, (a, b) in enumerate(zip(ids, ids[1:]))]
    geometry = dict(schema='tk2-route-geometry-v1', routes={'s:t:land': dict(
        **{'from': 's', 'to': 't'}, mode='land', city_sections=sections,
        parts=[dict(mode='land', start=[0, 0], end=[30, 0], length_px=30, chord_px=30)])})
    apply_route_timing(data, geometry, 'test-exact-city-sections')
    return data, geometry


def state_for(active=('s', 'a', 'b', 't'), owners=None, year=209, month=7):
    owners = owners or {}
    return SimpleNamespace(cities={city: SimpleNamespace(id=city, owner=owners.get(city, 'friendly'), grain=1000)
                                  for city in active}, year=year, month=month, turn=1,
                           player='friendly', officers={1: SimpleNamespace(
                               troops=900, alive=True, faction_id='friendly')},
                           soldiers={'lost': 0}, extension={'travel': {'discovered': []}})


def travel_for(data):
    travel = TravelCampaign()
    travel.catalog = SimpleNamespace(data=data, links={frozenset(p) for p in data['links']})
    return travel


def quote_for(data, state, source='s', target='t', adjacent=False):
    with using_backend('python'):
        return travel_for(data)._travel_path(state, source, target, 'friendly', 'land', adjacent=adjacent)


class HistoricalTransitTests(unittest.TestCase):
    def test_compilation_keeps_every_contiguous_variant_and_exact_section_distance(self):
        data, geometry = fixture()
        route = data['travel_routes'][0]
        self.assertEqual((route['distance_km'], route['land_km'], route['days']), (3, 3, 3))
        self.assertEqual(len(route['transit_variants']), 6)
        self.assertEqual(len({row['id'] for row in variants([route])}), 7)
        by_pair = {(row['from'], row['to']): row for row in route['transit_variants']}
        self.assertEqual(by_pair['s', 't']['via'], ['a', 'b'])
        self.assertEqual(by_pair['s', 't']['days'], 1)
        self.assertEqual(sum(by_pair[a, b]['distance_km'] for a, b in zip('sab', 'abt')), route['distance_km'])
        self.assertEqual(sum(by_pair[a, b]['days'] for a, b in zip('sab', 'abt')), route['days'])
        self.assertTrue(all('draw' not in row for row in route['transit_variants']),
                        'Logical stops never add another rendered copy of shared roads')
        original = deepcopy(geometry)
        apply_route_timing(data, geometry, 'test-exact-city-sections')
        self.assertEqual(geometry, original, 'Timing never rewrites city positions or path pieces')

    def test_friendly_and_empty_cities_are_actual_stops_enemy_city_blocks_through_march(self):
        data, _ = fixture()
        for owner in ('friendly', 'neutral'):
            state = state_for(owners={'a': owner, 'b': owner})
            before = canonical(data), canonical(vars(state)['extension'])
            for _ in range(3):
                quote = quote_for(data, state)
                self.assertEqual(quote['path'], ['s', 'a', 'b', 't'])
                self.assertEqual(len(quote['routes']), 3)
                self.assertEqual((quote['distance_km'], quote['days']), (3, 3))
            self.assertEqual((canonical(data), canonical(state.extension)), before)
        for city in ('a', 'b'):
            self.assertIsNone(quote_for(data, state_for(owners={city: 'enemy'})),
                              'A parent route must not jump over a living hostile intermediate city')

    def test_attack_reaches_first_city_and_cannot_skip_an_active_transit_city(self):
        data, _ = fixture()
        state = state_for(owners={'a': 'enemy', 't': 'enemy'})
        quote = quote_for(data, state, target='a', adjacent=True)
        self.assertEqual(quote['path'], ['s', 'a'])
        self.assertEqual(quote['routes'][0]['parent_route'], 's:t:land')
        self.assertIsNone(quote_for(data, state, adjacent=True))
        state.cities['a'].owner = 'friendly'
        state.cities['b'].owner = 'friendly'
        self.assertIsNone(quote_for(data, state, adjacent=True),
                          'Direct attack UI does not bypass friendly transit stops either')

    def test_absent_cities_are_continuous_road_sites_and_not_fake_food_stops(self):
        data, _ = fixture()
        for active, expected in ((('s', 't'), ['s', 't']),
                                 (('s', 'b', 't'), ['s', 'b', 't']),
                                 (('s', 'a', 't'), ['s', 'a', 't'])):
            state = state_for(active)
            quote = quote_for(data, state)
            self.assertEqual(quote['path'], expected)
            self.assertEqual(quote['distance_km'], 3)
            self.assertEqual(quote['days'], len(expected)-1)
            chosen = effective(data['travel_routes'], state.cities, 209, 7)
            self.assertTrue(all(row['from'] in active and row['to'] in active for row in chosen))
            self.assertTrue(all(not set(row['via']) & set(active) for row in chosen))
            self.assertEqual(initial_days(state, quote), quote['routes'][0]['days'])

    def test_availability_uses_inclusive_start_exclusive_end_including_transit_variants(self):
        window = {'from': [207, 7], 'to': [211, 7]}
        data, _ = fixture(window)
        for year, month, expected in ((207, 6, False), (207, 7, True), (211, 6, True), (211, 7, False)):
            with self.subTest(year=year, month=month):
                route = data['travel_routes'][0]
                self.assertEqual(available(route, year, month), expected)
                self.assertEqual(bool(quote_for(data, state_for(year=year, month=month))), expected)
                self.assertTrue(all(row.get('availability') == window for row in route['transit_variants']))
        self.assertTrue(available(data['travel_routes'][0]), 'Immutable validation can enumerate identities without a date')

    def test_disconnected_or_repeated_city_sections_are_rejected(self):
        data, geometry = fixture()
        route = data['travel_routes'][0]
        for broken in ('disconnected', 'repeated', 'unknown_city'):
            rows = deepcopy(geometry['routes'][route['id']]['city_sections'])
            if broken == 'disconnected':
                rows[1]['from'] = 's'
            elif broken == 'repeated':
                rows[1]['to'] = 's'
            else:
                rows[1]['to'] = 'missing'
                rows[2]['from'] = 'missing'
            with self.subTest(broken=broken), self.assertRaises((ValueError, KeyError)):
                compile_transit(deepcopy(route), rows, data['city_coordinates'], data['travel_rules'])

    def test_documented_july_207_closure_uses_restored_lulong_without_annual_loss_rule(self):
        data = json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        state = state_for(tuple(data['city_coordinates']))
        state.year, state.month = 207, 7
        quote = quote_for(data, state, 'yuyang', 'liaoxi', adjacent=True)
        self.assertEqual(quote['routes'][0]['id'], 'yuyang:liaoxi:lulong:land')
        self.assertIsNone(quote['routes'][0]['hazard'])
        coast = next(r for r in data['travel_routes'] if r['id']=='liaoxi:yuyang:land')
        for year, month, expected in ((207,6,True),(207,7,False),(207,8,True),(208,7,True)):
            self.assertEqual(available(coast,year,month),expected)

    def test_saved_bypass_is_checked_at_departure_before_a_city_is_founded(self):
        data, _ = fixture({'from': [207, 7]})
        parent = data['travel_routes'][0]
        bypass = next(row for row in parent['transit_variants']
                      if row['from']=='s' and row['to']=='t')
        catalog = SimpleNamespace(active_city_ids=lambda year, month:
                                  ['s','t'] if (year,month)<(208,1) else ['s','a','b','t'])
        self.assertFalse(valid_departure(parent,catalog,207,7),
                         'A raw painted parent cannot be injected as a playable bypass')
        self.assertFalse(valid_departure(bypass,catalog,207,6),
                         'Correct arithmetic cannot make an unopened road valid')
        self.assertTrue(valid_departure(bypass,catalog,207,12),
                        'An old in-flight receipt survives a new city appearing later')
        self.assertFalse(valid_departure(bypass,catalog,208,1),
                         'New departures cannot skip the newly founded city')

    def test_daily_food_is_loaded_to_real_friendly_stops_and_refilled_there(self):
        data, _ = fixture()
        for owner, expected_load, refills in (('friendly', 1, ['a', 'b']),
                                              ('neutral', 3, [])):
            state = state_for(owners={'a': owner, 'b': owner})
            quote = quote_for(data, state)
            self.assertEqual(estimate(state, [1], quote), expected_load)
            supply = create(state, [1], quote)
            journey = dict(quote=quote, supply=supply, risks=[])
            unit = dict(id=1, owner='friendly', officers=[1])
            events = []
            game = SimpleNamespace(_supply_event=lambda *args, **kwargs: events.append(kwargs))
            advance_unit(game, state, unit, journey, absolute_tick=3)
            self.assertEqual((supply['elapsed_days'], supply['route_days'], supply['consumed']), (3, 3, 3))
            self.assertEqual(supply['remaining'], 0)
            self.assertEqual(supply['shortage_days'], 0)
            self.assertEqual([r['source'] for r in supply['refills']], refills)
            self.assertEqual(supply['loaded']+supply['received']-supply['consumed'], 0)
            self.assertEqual(state.soldiers['lost'], 0)
        state = state_for(('s', 't'))
        quote = quote_for(data, state)
        supply = create(state, [1], quote)
        advance_unit(SimpleNamespace(_supply_event=lambda *a, **k: None), state,
                     dict(id=1, owner='friendly', officers=[1]),
                     dict(quote=quote, supply=supply, risks=[]), absolute_tick=1)
        self.assertEqual((supply['loaded'], supply['consumed'], supply['refills']), (1, 1, []))

    def test_all_29_catalogues_preserve_fixed_city_positions_and_hazard_rules(self):
        files = sorted((ROOT/'game/data/campaigns').glob('*.json'))
        files = [path for path in files if path.stem != 'index']
        self.assertEqual(len(files), 29)
        for path in files:
            data = json.loads(path.read_text())
            with self.subTest(scenario=path.stem):
                self.assertEqual(digest({city['id']: city['position'] for city in data['cities']}), POSITIONS_SHA)
                self.assertEqual(digest(data['travel_hazards']), HAZARDS_SHA)


class HistoricalTransitNativeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            with using_backend('rust'):
                invoke('allocate', troops=[], numerator=1, denominator=1)
        except CoreUnavailable as error:
            if os.environ.get('MARCH_CORE_BACKEND') == 'rust':
                raise
            raise unittest.SkipTest(f'Build Rust march core first: {error}')

    def test_active_inactive_control_and_year_boundary_paths_match_exactly(self):
        data, _ = fixture({'from': [207, 7], 'to': [211, 7]})
        for active in (('s', 'a', 'b', 't'), ('s', 'b', 't'), ('s', 't')):
            for middle_owner in ('friendly', 'neutral', 'enemy'):
                for year, month in ((207, 6), (207, 7), (211, 6), (211, 7)):
                    state = state_for(active, {'a': middle_owner, 'b': middle_owner}, year, month)
                    cities = [dict(id=city.id, owner=city.owner) for city in state.cities.values()]
                    for source, target, adjacent in (('s', 't', False), ('t', 's', False),
                                                     ('s', 't', True), ('s', 'a', True)):
                        expected = quote_for(data, state, source, target, adjacent)
                        with using_backend('rust'):
                            actual = invoke('path', data=data, cities=cities, year=year, month=month,
                                            discovered=[], source=source, target=target,
                                            owner='friendly', mode='land', adjacent=adjacent)
                        self.assertEqual(canonical(actual), canonical(expected),
                                         (active, middle_owner, year, month, source, target, adjacent))


if __name__ == '__main__':
    unittest.main()
