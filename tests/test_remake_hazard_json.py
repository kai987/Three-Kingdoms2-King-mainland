"""Browser number serialization must preserve current pending-march save checksums."""
import json
from decimal import Decimal
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, digest
from remake.route_hazards import evaluate_leg


def browser_numbers(value):
    # JSON.parse -> JSON.stringify removes the .0 spelling from whole values.
    # Our real route numbers are bounded decimals, not JS unsafe integers or
    # exponent-format edge cases, so this models the relevant browser change.
    def number(text):
        value = float(text)
        return int(value) if value.is_integer() else value
    return json.loads(json.dumps(value), parse_float=number)


class HazardJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')

    def game(self, faction, month=7):
        game = Campaign(self.catalog)
        game.command('new', dict(faction=faction, seed=2026), 0)
        while game.state.month != month:
            game._complete_turn(game.state)
            game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.validate(game.state)
        return game

    def assert_browser_save_loads(self, game):
        original = game.export_save()
        downloaded = browser_numbers(original)
        content = {k: v for k, v in downloaded.items() if k != 'checksum'}
        self.assertEqual(digest(content), original['checksum'])
        restored = Campaign(self.catalog)
        restored.load_save(downloaded, 0)
        self.assertEqual(restored.to_dict(), game.to_dict())
        self.assertEqual(restored.export_save(), original)

    def integer_land_case(self):
        """Keep testing a real whole-valued route as its artwork evolves."""
        game = self.game('wu')
        for route in self.catalog.data['travel_routes']:
            a, b = route['from'], route['to']
            if (route['mode'] != 'land' or route.get('special')
                    or any(game.state.cities.get(city) is None or game.state.cities[city].owner != 'wu'
                           for city in (a, b)) or not game.state.cities[a].roster.officer_ids):
                continue
            quote = game._travel_path(game.state, a, b, 'wu', 'land')
            if (quote and len(quote['routes']) == 1 and not quote['routes'][0].get('hazard')
                    and type(quote['distance_km']) is int and type(quote['routes'][0]['land_km']) is int):
                return ('wu', 7, a, b, 'land', 'transfer', quote['distance_km'])
        self.fail('The current map must provide a real whole-valued friendly land route')

    def test_real_hazard_marches_survive_browser_download_without_new_checksum(self):
        cases = [
            # Whole percentages used to be Python floats 50.0 and 20.0.
            ('wei', 7, 'hanzhong', 'jingzhao', 'special', 'transfer', 50),
            ('wei', 10, 'hanzhong', 'jingzhao', 'special', 'transfer', 20),
            # The fractional one-third rule must retain its real precision.
            ('wei', 7, 'yinping', 'shujun', 'special', 'depart', 200 / 3),
            # Both monsoon speeds, with a real known and unknown sea chart.
            ('wu', 7, 'hepu', 'zhuya', 'sea', 'depart', 7.5),
            ('wu', 7, 'hepu', 'yizhou', 'explore', 'depart', 120),
            # A current whole-valued land leg and quote total.
            self.integer_land_case(),
        ]
        for faction, month, source, target, mode, command, expected in cases:
            with self.subTest(month=month, source=source, target=target, mode=mode):
                game = self.game(faction, month)
                officer = game.state.cities[source].roster.officer_ids[0]
                game.command(command, dict(source=source, target=target,
                    officers=[officer], route_mode=mode), game.revision)
                row = game.state.extension['travel']['marches'][0]
                leg = row['quote']['routes'][0]
                if mode == 'special':
                    self.assertEqual(leg['hazard']['loss_percent'], expected)
                elif mode in ('sea', 'explore'):
                    self.assertEqual(leg['hazard']['speed_km_per_day'], expected)
                else:
                    self.assertEqual(row['quote']['distance_km'], expected)
                    self.assertIs(type(leg['land_km']), int)
                self.assert_browser_save_loads(game)

    def test_fractional_leg_distances_can_sum_to_integral_quote_distance(self):
        data = self.catalog.data
        adjacent = {}
        for route in data['travel_routes']:
            if (route['mode'] != 'land' or route.get('special')
                    or {route['from'], route['to']} == {'yinping', 'shujun'}):
                continue
            distance = Decimal(str(route['distance_km']))
            if distance == distance.to_integral_value():
                continue
            for source, middle in ((route['from'], route['to']), (route['to'], route['from'])):
                for target, other, length in adjacent.get(middle, []):
                    total = distance + length
                    if target != source and total == total.to_integral_value():
                        legs = [evaluate_leg(data, route, source, middle, 7),
                                evaluate_leg(data, other, middle, target, 7)]
                        quote = Campaign._quote([source, middle, target], legs)
                        break
                else:
                    adjacent.setdefault(middle, []).append((source, route, distance))
                    continue
                break
            else:
                continue
            break
        else:
            self.fail('The current map must contain fractional legs with a whole-valued combined distance')
        self.assertTrue(all(type(leg['distance_km']) is float for leg in legs))
        self.assertEqual(quote['distance_km'], int(total))
        self.assertIs(type(quote['distance_km']), int)
        self.assertEqual(digest(browser_numbers(quote)), digest(quote))


if __name__ == '__main__':
    unittest.main()
