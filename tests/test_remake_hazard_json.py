"""Browser number serialization must preserve genuine v11 save checksums."""
import json
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
        cls.catalog = Catalog(ROOT / 'game/data/main-scenarios-v11/217-07.json')

    def game(self, faction, month=7):
        game = Campaign(self.catalog)
        game.command('new', dict(faction=faction, seed=2026), 0)
        while game.state.month != month:
            game._complete_month(game.state)
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
            # A published 315.0 km land leg and 315.0 km quote total.
            ('wu', 7, 'changsha', 'guiyang', 'land', 'transfer', 315),
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
        legs = [evaluate_leg(data, next(r for r in data['travel_routes'] if r['id'] == ident),
            source, target, 7) for ident, source, target in [
                ('anding:fufeng:land', 'anding', 'fufeng'),
                ('fufeng:hanzhong:land', 'fufeng', 'hanzhong')]]
        self.assertEqual([r['distance_km'] for r in legs], [278.4, 274.6])
        quote = Campaign._quote(['anding', 'fufeng', 'hanzhong'], legs)
        self.assertEqual(quote['distance_km'], 553)
        self.assertIs(type(quote['distance_km']), int)
        self.assertEqual(digest(browser_numbers(quote)), digest(quote))


if __name__ == '__main__':
    unittest.main()
