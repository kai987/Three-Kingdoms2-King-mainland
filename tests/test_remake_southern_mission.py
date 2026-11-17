"""The historical voyage, construction budgets and saved troop ledger."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import domestic, southern_mission as mission
from remake.campaign import Campaign, Catalog, GameError


class Headless(Campaign):
    def view(self):
        return {}


class SouthernMissionTests(unittest.TestCase):
    def start(self, scenario='249-01', faction='wu'):
        catalog = Catalog(ROOT / 'game/data/campaigns' / f'{scenario}.json')
        game = Headless(catalog)
        game.command('new', {'faction': faction, 'seed': 2026}, 0)
        return game

    def command(self, game, kind, **payload):
        game.command(kind, payload, game.revision)

    def next_turn(self, game):
        self.command(game, 'end_turn')
        with patch.object(game, '_expanded_ai', lambda state, _: game._complete_turn(state)):
            self.command(game, 'ai', turn=game.state.turn)
        if game.state.phase == 'arrivals':
            self.command(game, 'arrivals')

    def realm_events(self, game):
        stream = game.state.extension['events']
        return [row['kind'] for row in [*stream.get('milestones', []), *stream['items']]
                if row['kind'] in mission.EVENTS]

    def reach_offer(self, game):
        self.assertEqual(self.realm_events(game), [mission.DEPARTED])
        while mission.view(game, game.state)['stage'] == 'survey':
            self.next_turn(game)
        self.assertEqual(self.realm_events(game), [mission.DEPARTED, mission.LANDED])
        self.assertEqual(game.state.cities['luzon'].owner, 'neutral')

    def round_trip(self, game):
        save = game.export_save()
        restored = Headless(game.catalog)
        restored.load_save(save, 0)
        self.assertEqual(restored.export_save(), save)
        return restored

    def test_offers_once_in_window_and_decline_leaves_the_island_empty(self):
        self.assertIsNone(mission.view(earlier := self.start('238-01'), earlier.state))
        self.assertIsNone(mission.view(other := self.start(faction='wei'), other.state))
        game = self.start()
        self.reach_offer(game)
        before = game.export_save()
        with self.assertRaises(GameError):
            self.command(game, mission.COMMAND, action='build', port='kuaiji', troops=9999)
        self.assertEqual(game.export_save(), before)
        self.command(game, mission.COMMAND, action='decline')
        game = self.round_trip(game)
        self.next_turn(game)
        self.assertEqual(mission.view(game, game.state)['stage'], 'declined')
        self.assertEqual(game.state.cities['luzon'].owner, 'neutral')
        self.assertEqual(self.realm_events(game), [mission.DEPARTED, mission.LANDED])

    def test_fleet_survives_typhoon_and_building_pauses_until_stocks_return(self):
        game = self.start()
        self.reach_offer(game)
        winter = mission.view(game, game.state)['routes'][0]['wind_days']
        while game.state.month != 6:
            self.next_turn(game)
        project = mission.view(game, game.state)
        self.assertGreater(project['routes'][0]['wind_days'], winter)
        self.assertEqual(project['routes'][0]['storm_max'], 20)
        city = game.state.cities['kuaiji']
        domestic.add_reserves(game, game.state, city, 40_000, recruited=True)
        city.gold += 100_000
        city.grain += 100_000
        game.validate(game.state)
        # Choose a storm with the real two-stage weather rule while keeping the
        # rest of the campaign deterministic independently of monthly draws.
        with patch.object(type(game.state.rng), 'next', side_effect=(0, 1)):
            self.command(game, mission.COMMAND, action='build', port='kuaiji', troops=40_000)
        travelling = mission.view(game, game.state)
        self.assertEqual(travelling['fleet']['storm_days'], 20)
        self.assertEqual(travelling['fleet']['arrival'] - travelling['fleet']['turn'],
                         (travelling['fleet']['wind_days'] + 29) // 10)
        self.assertEqual(mission.in_transit_troops(game.state), 40_000)
        game = self.round_trip(game)
        while mission.view(game, game.state)['stage'] == 'sailing':
            self.next_turn(game)
            self.assertEqual(mission.in_transit_troops(game.state), 40_000)
        self.assertEqual(game.state.cities['luzon'].owner, 'neutral')
        project = mission.view(game, game.state)
        source_ids = project['sources']
        for ident in source_ids:
            game.state.cities[ident].grain = 0
        # Even monthly income cannot pay the next full work allocation from
        # an empty food pool in this isolated turn.
        with patch.object(game, '_monthly_calendar'):
            self.next_turn(game)
        paused = mission.view(game, game.state)
        self.assertTrue(paused['paused'])
        self.assertEqual(paused['worked'], 0)
        game = self.round_trip(game)
        game.state.cities['kuaiji'].grain = 80_000
        for worked in range(10, 90, 10):
            self.next_turn(game)
            self.assertEqual(mission.view(game, game.state)['worked'], worked)
            self.assertEqual(game.state.cities['luzon'].owner, 'neutral')
        self.next_turn(game)
        self.assertEqual(mission.view(game, game.state)['stage'], 'built')
        self.assertEqual(game.state.cities['luzon'].owner, 'wu')
        self.assertEqual(game.state.cities['luzon'].reserves, 40_000)
        self.assertEqual(self.realm_events(game), list(mission.EVENTS))
        self.assertEqual(mission.in_transit_troops(game.state), 0)
        self.round_trip(game)

    def test_inverse_work_schedule_is_rounded_to_a_day(self):
        self.assertEqual([mission.work_days(n) for n in (10_000, 20_000, 40_000, 80_000, 160_000)],
                         [360, 180, 90, 45, 23])


if __name__ == '__main__':
    unittest.main()
