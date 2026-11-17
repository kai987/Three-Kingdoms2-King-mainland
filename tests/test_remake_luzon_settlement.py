import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog


class HeadlessCampaign(Campaign):
    def view(self):
        return {'revision': self.revision}


class LuzonSettlementTests(unittest.TestCase):
    def test_seaborne_foundation_and_save_use_the_real_arrival_queue(self):
        game = HeadlessCampaign(Catalog(ROOT / 'game/data/campaigns/200-01.json'))

        def command(kind, **payload):
            game.command(kind, payload, game.revision)

        def next_turn():
            command('end_turn')
            # Isolate expedition timing from attacks in distant mainland cities.
            with patch.object(game, '_expanded_ai', lambda state, _: game._complete_turn(state)):
                command('ai', turn=game.state.turn)
            if game.state.phase == 'arrivals':
                command('arrivals')

        def sail(source, target, officer):
            command('depart', source=source, target=target, officers=[officer],
                    route_mode='sea', battle_grain=100)
            return game.state.extension['travel']['marches'][0]['quote']

        command('new', faction='wu', seed=2026)
        self.assertEqual(set(game._neighbors('luzon', game.state)), {'yizhou'})
        self.assertEqual(game.state.cities['luzon'].owner, 'neutral')
        officer = game.state.cities['kuaiji'].roster.officer_ids[0]
        quote = sail('kuaiji', 'yizhou', officer)
        for _ in range(quote['turns']):
            next_turn()
        command('settle', battle_id=game.state.battle['id'])
        if game.state.phase == 'arrivals':
            command('arrivals')
        next_turn()

        quote = sail('yizhou', 'luzon', officer)
        self.assertEqual(quote['path'], ['yizhou', 'luzon'])
        self.assertEqual(quote['modes'], ['sea'])
        for _ in range(quote['turns'] - 1):
            next_turn()
            self.assertEqual(game.state.cities['luzon'].owner, 'neutral')
        next_turn()

        island = game.state.cities['luzon']
        self.assertEqual(island.owner, 'wu')
        self.assertGreater(island.grain, 0)
        self.assertEqual(island.roster.officer_ids, [officer])
        self.assertNotIn(officer, game.state.cities['yizhou'].roster.officer_ids)
        self.assertIsNone(game.state.battle)
        events = [row for row in game.state.extension['events']['items']
                  if row['city_ids'] and row['city_ids'][0] == 'luzon' and row['kind'] == 'city_founded']
        self.assertEqual([row['details'] for row in events], [{'parent': 'yizhou', 'settlement': True}])

        restored = HeadlessCampaign(game.catalog)
        restored.load_save(game.export_save(), 0)
        self.assertEqual(restored.export_save(), game.export_save())
