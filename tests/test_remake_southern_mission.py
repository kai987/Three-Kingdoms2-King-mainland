"""The historical voyage, construction budgets and saved troop ledger."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import domestic, southern_mission as mission
from remake.campaign import Campaign, Catalog, GameError
from campaign_fixtures import advance_month


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

    def advance_to_january(self, game, year):
        state = game.state
        while (state.year, state.month) < (year - 1, 12):
            advance_month(game)
            game._reconcile_factions(state)
        for _ in range(3):
            self.next_turn(game)
        self.assertEqual((game.state.year, game.state.month), (year, 1))

    def begin_mission(self):
        game = self.start('238-01')
        self.advance_to_january(game, mission.DEPARTURE_YEAR)
        return game

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

    def test_the_249_opening_keeps_envoys_abroad_without_replaying_departure(self):
        game = self.start()
        ids = [game.catalog.ids[pid] for pid in mission.ENVOYS]
        self.assertEqual([game.catalog.name(ident) for ident in ids], ['朱應', '康泰'])
        self.assertTrue(all(ident not in game.state.officers for ident in ids))
        self.assertEqual(self.realm_events(game), [])
        for pid in mission.ENVOYS:
            plan = game.catalog.data['era_assignments'][pid]['appearance_plan']
            self.assertEqual((plan['mission_departure_year'], plan['start']),
                             (244, [251, 1]))
        self.round_trip(game)
        late = self.start('263-05')
        self.assertTrue(all(ident not in late.state.officers for ident in ids))

    def test_envoys_return_to_wu_in_251_even_if_kuaiji_has_fallen(self):
        for captured in (False, True):
            with self.subTest(captured=captured):
                game = self.start()
                if captured:
                    game.state.cities['kuaiji'].owner = 'wei'
                ids = [game.catalog.ids[pid] for pid in mission.ENVOYS]
                self.assertTrue(all(ident not in game.state.officers for ident in ids))
                self.advance_to_january(game, mission.RETURN_YEAR)
                state = game.state
                for ident in ids:
                    home = next(city for city in state.cities.values() if ident in city.roster.officer_ids)
                    self.assertEqual(home.owner, 'wu')
                    self.assertEqual(home.id == 'kuaiji', not captured)
                    officer = state.officers[ident]
                    self.assertEqual((officer.faction_id, officer.troops), ('wu', 0))
                    self.assertNotIn(str(ident), state.extension['free_locations'])
                    appearance = next(row for row in state.extension['events']['items']
                                      if row['kind'] == 'officer_appeared'
                                      and row['person_ids'] == [state.officers[ident].person_id])
                    self.assertEqual((appearance['factions'], appearance['city_ids']), (['wu'], [home.id]))
                game.validate(state)
                self.assertEqual(self.realm_events(game), [])
                self.round_trip(game)

    def test_offers_once_in_window_and_decline_leaves_the_island_empty(self):
        self.assertIsNone(mission.view(earlier := self.start('238-01'), earlier.state))
        self.assertIsNone(mission.view(other := self.start(faction='wei'), other.state))
        game = self.begin_mission()
        departure = next(row for row in game.state.extension['events']['items']
                         if row['kind'] == mission.DEPARTED)
        self.assertEqual((departure['year'], departure['person_ids']), (244, list(mission.ENVOYS)))
        self.assertTrue(all(game.catalog.ids[pid] not in game.state.officers for pid in mission.ENVOYS))
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
        game = self.begin_mission()
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
