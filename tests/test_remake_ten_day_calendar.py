"""Ten-day strategy turns, monthly accounting and exact march/calendar boundaries."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, GameError, digest
from campaign_fixtures import controlled_catalog


class TenDayCalendarTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(controlled_catalog())
        self.game.command('new', dict(faction='shu', seed=2026), 0)

    def test_three_turns_advance_one_fixed30_day_month_and_reset_city_actions(self):
        game = self.game
        rng = deepcopy(game.state.rng)
        for turn, month, day in ((2, 11, 11), (3, 11, 21), (4, 12, 1)):
            for city in game.state.cities.values():
                city.action_used = True
            game._complete_turn(game.state)
            game.validate(game.state)
            self.assertEqual((game.state.turn, game.state.month, game.state.day), (turn, month, day))
            self.assertEqual(game.state.phase, 'city')
            self.assertTrue(all(not city.action_used for city in game.state.cities.values()))
            self.assertEqual(game.state.completed_ai_turns, list(range(1, turn)))
        self.assertEqual(game.state.rng, rng)

    def test_income_and_healing_settle_once_monthly_instead_of_three_times(self):
        game = self.game
        officer = game.state.officers[999]
        officer.health = officer.profile.health_max - 20
        stocks = {key: (c.gold, c.grain, c.reserves) for key, c in game.state.cities.items()}
        for _ in range(2):
            game._complete_turn(game.state)
            self.assertEqual({key: (c.gold, c.grain, c.reserves) for key, c in game.state.cities.items()}, stocks)
            self.assertEqual(officer.health, officer.profile.health_max - 20)
        game._complete_turn(game.state)
        for key, city in game.state.cities.items():
            income = game.catalog.data['city_income'][key] if city.owner != 'neutral' else dict(gold=0, grain=0, reserves=0)
            self.assertEqual((city.gold, city.grain, city.reserves),
                tuple(stocks[key][i] + income[field] for i, field in enumerate(('gold', 'grain', 'reserves'))))
        self.assertEqual(officer.health,
            min(officer.profile.health_max, officer.profile.health_max - 20 + game.catalog.data['rules']['monthly_heal']))

    def test_new_year_and_lifetime_receipts_only_at_december_lower_to_january_upper(self):
        game = self.game
        for _ in range(3):
            game._complete_turn(game.state)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (217, 12, 1))
        for _ in range(2):
            game._complete_turn(game.state)
            self.assertEqual(game.state.year, 217)
            self.assertFalse(game.state.year_events)
        game._complete_turn(game.state)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (218, 1, 1))
        self.assertEqual(game.state.calendar_cursor, 218)
        events = game.state.year_events.copy()
        game._complete_turn(game.state)
        self.assertEqual(game.state.year_events, events)
        game.validate(game.state)

    def test_march_21_days_takes_three_turns_and_cannot_arrive_at20_days(self):
        catalog = controlled_catalog()
        route = next(r for r in catalog.data['travel_routes'] if r['from'] == 'xiangyang' and r['to'] == 'nanjun')
        route.update(days=21, distance_km=630, land_km=630)
        game = Campaign(catalog)
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('depart', dict(source='xiangyang', target='nanjun', officers=[999]), game.revision)
        march = game.state.extension['travel']['marches'][0]
        self.assertEqual(march['quote']['days'], 21)
        self.assertEqual(march['quote']['turns'], 3)
        self.assertEqual(march['arrival_turn'], 4)
        self.assertEqual(march['departure_day'], 1)
        for _ in range(2):
            game._complete_turn(game.state)
            self.assertEqual(game.state.phase, 'city')
        game._complete_turn(game.state)
        self.assertEqual(game.state.phase, 'arrivals')
        game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.phase, 'battle')
        self.assertTrue(set(march['officers']) <= set(game.state.cities['xiangyang'].roster.officer_ids))
        game.validate(game.state)

    def test_each_upper_middle_lower_turn_executes_ai_and_receipt_is_atomic(self):
        game = self.game
        for day in (11, 21, 1):
            prior = game.state.turn
            game.command('end_turn', {}, game.revision)
            game.command('ai', dict(turn=prior), game.revision)
            self.assertEqual(game.state.day, day)
            self.assertEqual(game.state.phase, 'city')
            self.assertIn(prior, game.state.completed_ai_turns)
            saved, revision = game.export_save(), game.revision
            game.command('ai', dict(turn=prior), revision - 1)
            self.assertEqual(game.export_save(), saved)
            self.assertEqual(game.revision, revision)
        self.assertEqual(game.state.month, 12)

    def test_each_ai_faction_acts_together_in_stable_order(self):
        game = self.game
        for city in game.state.cities.values():
            if city.owner not in (game.state.player, 'neutral'):
                game.state.soldiers['lost'] += city.reserves
                city.reserves = 0
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=1), game.revision)
        reports = [r for r in game.state.extension['ai_reports'] if r['turn'] == 1]
        factions = [r['faction'] for r in reports]
        self.assertEqual(set(factions), {'wei', 'wu'})
        self.assertEqual(factions, sorted(factions))
        game.validate(game.state)

    def test_player_defense_arrival_save_and_settlement_do_not_tick_twice(self):
        catalog = controlled_catalog()
        catalog.data['rules']['ai_max_attacks_per_turn'] = 1
        # Keep a second player city so losing the arrival battle can resume.
        catalog.data['initial_owners']['nanjun'] = 'shu'
        for row in catalog.data['initial_officers']:
            if row['city'] == 'xiangyang':
                row['troops'] = 15
        game = Campaign(catalog)
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=1), game.revision)
        self.assertEqual((game.state.turn, game.state.month, game.state.day), (2, 11, 11))
        self.assertEqual(game.state.completed_ai_turns, [1])
        self.assertEqual(game.state.phase, 'arrivals')
        game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual(game.state.battle['defender'], 'shu')
        self.assertTrue(game.state.extension['travel']['battle_arrival'])
        saved = game.export_save()
        loaded = Campaign(catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)
        battle_id = loaded.state.battle['id']
        loaded.command('retreat', dict(battle_id=battle_id), loaded.revision)
        loaded.command('settle', dict(battle_id=battle_id), loaded.revision)
        self.assertEqual(loaded.state.phase, 'arrivals')
        loaded.command('arrivals', {}, loaded.revision)
        self.assertEqual(loaded.state.phase, 'city')
        self.assertEqual((loaded.state.turn, loaded.state.month, loaded.state.day), (2, 11, 11))
        self.assertEqual(loaded.state.completed_ai_turns, [1])
        # Repeated receipt must not restart AI or add another ten-day tick.
        settled, revision = loaded.export_save(), loaded.revision
        loaded.command('ai', dict(turn=1), revision - 1)
        loaded.command('settle', dict(battle_id=battle_id), revision - 1)
        self.assertEqual(loaded.export_save(), settled)
        self.assertEqual(loaded.revision, revision)
        loaded.command('end_turn', {}, loaded.revision)
        loaded.command('ai', dict(turn=2), loaded.revision)
        self.assertEqual((loaded.state.turn, loaded.state.month, loaded.state.day), (3, 11, 21))
        self.assertEqual(loaded.state.completed_ai_turns, [1, 2])
        loaded.validate(loaded.state)

    def test_middle_and_lower_saves_roundtrip_and_bad_day_or_turn_reject_atomically(self):
        game = self.game
        for _ in range(2):
            game._complete_turn(game.state)
            saved = game.export_save()
            loaded = Campaign(game.catalog)
            loaded.load_save(saved, 0)
            self.assertEqual(loaded.export_save(), saved)
            for key, value in (('day', 10), ('day', 1), ('turn', game.state.turn + 1)):
                bad = deepcopy(saved)
                bad['state'][key] = value
                bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
                with self.assertRaises(GameError):
                    loaded.load_save(bad, loaded.revision)
                self.assertEqual(loaded.export_save(), saved)


if __name__ == '__main__':
    unittest.main()
