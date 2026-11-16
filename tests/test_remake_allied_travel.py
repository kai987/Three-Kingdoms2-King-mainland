"""Strategic orders rendezvous two allied columns without duplicating troops."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from campaign_fixtures import controlled_catalog
from remake.campaign import Campaign, Catalog
from remake.errors import GameError
from remake.strategic_ai import StrategicAI


def _catalog(*, shu_days=20, wu_days=10, budget=0):
    data = deepcopy(controlled_catalog().data)
    data['rules']['ai_max_attacks_per_turn'] = budget
    real = json.loads((Path(__file__).resolve().parents[1] / 'game/data/campaigns/217-07.json').read_text())
    added = {row['person_id'] for row in data['initial_officers']}
    reinforcements = (row for row in real['initial_officers'] if row['person_id'] not in added)
    for city, count in (('xiangyang', 2), ('jiangxia', 4)):
        for _ in range(count):
            person = next(reinforcements)['person_id']
            data['initial_officers'].append(dict(person_id=person, city=city, troops=600, ruler=False))
            data['appearance_locations'][person] = city
    shu = data['travel_routes'][0]
    shu.update(days=shu_days, distance_km=shu_days*30, land_km=shu_days*30)
    data['links'].append(['jiangxia','nanyang'])
    data['travel_routes'].append(dict(id='controlled:jiangxia:nanyang',
        **{'from':'jiangxia', 'to':'nanyang'}, mode='land', terrain='plain',
        days=wu_days, distance_km=wu_days*30, land_km=wu_days*30, sea_km=0))
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / 'controlled-allies.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


def _alliance(game, duration=12):
    envoy = game.state.cities['xiangyang'].roster.officer_ids[-1]
    game.command('diplomacy', dict(action='alliance', city='xiangyang', target='wu',
                                  envoy=envoy, duration=duration), game.revision)


class AlliedAttackTravelTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(_catalog())
        self.game.command('new', dict(faction='shu', seed=2026), 0)

    def depart(self, officers):
        return self.game.command('depart', dict(source='xiangyang', target='nanyang', officers=officers),
                                 self.game.revision)

    def arrivals(self):
        self.game._complete_turn(self.game.state)
        self.game.command('arrivals', {}, self.game.revision)

    def test_joined_arrival_waits_for_partner_and_rejects_more_than_ten(self):
        game = self.game
        _alliance(game)
        state = game.state
        source, target = state.cities['jiangxia'], state.cities['nanyang']
        allies = source.roster.officer_ids[:]
        game._queue_march(state, source, target, allies, 'attack')
        player = state.cities['xiangyang'].roster.officer_ids[:]
        self.assertEqual((len(allies), len(player)), (5, 6))
        self.assertEqual(game.view()['catalog']['allied_attacks']['nanyang']['remaining'], 5)
        before = game.export_save()
        with self.assertRaisesRegex(GameError, '5名武將'):
            self.depart(player)
        self.assertEqual(game.export_save(), before)

        self.depart(player[:5])
        self.arrivals()
        self.assertIsNone(game.state.battle)
        waiting, approaching = game.state.extension['travel']['marches']
        self.assertEqual((waiting['status'], waiting['reason']), ('waiting','allied_rendezvous'))
        self.assertEqual(waiting['supply']['route_days'], waiting['quote']['days'])
        self.assertLess(approaching['supply']['route_days'], approaching['quote']['days'])
        waiting_nutrition = waiting['supply']['remaining'] * 1000 + waiting['supply']['credit_units']
        self.assertEqual(approaching['target'], target.id)
        saved = game.export_save()
        game.load_save(saved, game.revision)

        self.arrivals()
        battle = game.state.battle
        self.assertEqual((battle['attacker'], battle['defender']), ('shu', 'wei'))
        self.assertEqual([unit['id'] for unit in battle['attackers']], player[:5] + allies)
        sources = battle['extended']['coalition']['sources']
        self.assertEqual(sources, {**{str(i):'xiangyang' for i in player[:5]},
                                   **{str(i):'jiangxia' for i in allies}})
        self.assertFalse(game.state.extension['travel']['marches'])
        provisions = battle['extended']['coalition']['provisions']
        self.assertEqual(set(provisions), {'shu', 'wu'})
        self.assertLess(provisions['wu'], waiting_nutrition)
        saved = game.export_save()
        game.load_save(saved, game.revision)
        self.assertEqual(game.export_save(), saved)

    def test_expiry_while_columns_travel_does_not_merge_them(self):
        game = Campaign(_catalog(shu_days=10, wu_days=20))
        game.command('new', dict(faction='shu', seed=2026), 0)
        self.game = game
        _alliance(game, duration=1)
        state = game.state
        source = state.cities['jiangxia']
        game._queue_march(state, source, state.cities['nanyang'], source.roster.officer_ids, 'attack')
        player = state.cities['xiangyang'].roster.officer_ids[:5]
        self.depart(player)
        self.arrivals()
        self.assertNotIn('coalition', game.state.battle['extended'])
        self.assertEqual([unit['id'] for unit in game.state.battle['attackers']], player)
        self.assertEqual(len(game.state.extension['travel']['marches']), 1)

    def test_lone_arrived_ally_offers_one_chance_to_depart_in_support(self):
        for join in (False, True):
            with self.subTest(join=join):
                game = Campaign(_catalog())
                game.command('new', dict(faction='shu', seed=2026), 0)
                self.game = game
                _alliance(game)
                state = game.state
                source = state.cities['jiangxia']
                game._queue_march(state, source, state.cities['nanyang'], source.roster.officer_ids, 'attack')
                self.arrivals()
                row, = game.state.extension['travel']['marches']
                self.assertEqual((game.state.phase, row['reason']), ('city','allied_support_window'))
                self.assertEqual(game.view()['catalog']['allied_attacks']['nanyang']['remaining'], 5)
                game.load_save(game.export_save(), game.revision)
                if join:
                    player = game.state.cities['xiangyang'].roster.officer_ids[:5]
                    self.depart(player)
                    self.arrivals()
                    waiting = game.state.extension['travel']['marches'][0]
                    self.assertEqual(waiting['reason'], 'allied_rendezvous')
                    self.arrivals()
                    self.assertIn('coalition', game.state.battle['extended'])
                else:
                    self.arrivals()
                    self.assertEqual(game.state.battle_counter, 1)
                    self.assertIsNone(game.state.battle)
                    self.assertFalse(game.state.extension['travel']['marches'])

    def test_ai_plan_respects_remaining_officer_slots(self):
        game = Campaign(_catalog(budget=2))
        game.command('new', dict(faction='shu', seed=2026), 0)
        self.game = game
        _alliance(game)
        player = game.state.cities['xiangyang'].roster.officer_ids[:]
        self.depart(player)
        ai = StrategicAI(game, game.state)
        plan = ai.plan('wu')
        self.assertEqual(plan['target'], 'nanyang')
        self.assertEqual(len(plan['orders'][0]['officers']), 4)
        self.assertTrue(ai.depart(game.state.cities['jiangxia'], plan))
        self.assertEqual(game.view()['catalog']['allied_attacks']['nanyang']['remaining'], 0)
        game.validate(game.state)
