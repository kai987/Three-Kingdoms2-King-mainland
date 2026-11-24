"""Strategic orders rendezvous two allied columns without duplicating troops."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

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
                    battle = game.state.battle
                    self.assertTrue(game.view()['catalog']['battle_reinforcements']['can_decline'])
                    game.command('battle_decline_support', {'battle_id': battle['id']}, game.revision)
                    self.assertIsNone(game.state.battle)
                    self.assertFalse(game.state.extension['travel']['marches'])

    def test_ai_ally_can_reinforce_attackers_or_defenders_on_battle_days(self):
        from remake import battle_grid, battle_reinforcements

        for player, side in (('shu', 'attackers'), ('wei', 'defenders')):
            with self.subTest(side=side):
                game = Campaign(_catalog(wu_days=2, budget=2))
                game.command('new', dict(faction=player,seed=2026), 0)
                state = game.state
                home, target = state.cities['xiangyang'], state.cities['nanyang']
                envoy = (home if player == 'shu' else target).roster.officer_ids[0]
                game.command('diplomacy', dict(action='alliance', city=home.id if player == 'shu' else target.id,
                                              target='wu', envoy=envoy, duration=12), game.revision)
                state = game.state
                home, target = state.cities[home.id], state.cities[target.id]
                game._start_expanded_battle(state, home, target, home.roster.officer_ids[:1])
                battle = state.battle
                for _ in range(4):
                    game._end_tactical_side(state)
                arrivals = battle_reinforcements.joined(battle)
                allied_ids = [ident for ident, arrival in arrivals.items() if arrival['owner'] == 'wu']
                self.assertEqual(len(allied_ids), 2)
                self.assertEqual(battle['round'], 3)
                self.assertEqual({arrivals[ident]['side'] for ident in allied_ids}, {side})
                allied = [unit for unit in battle[side] if str(unit['id']) in allied_ids]
                self.assertEqual(len(allied), 2)
                self.assertTrue(all(not battle_grid.player_controls(state, battle, unit) for unit in allied))
                self.assertEqual(state.turn, 1)
                game.validate(state)
                restored = Campaign(game.catalog)
                restored.load_save(game.export_save(compact=True), 0)
                self.assertEqual(restored.export_save(), game.export_save())

    def test_player_ally_can_join_either_side_or_let_ai_resolve(self):
        from remake import battle_grid, battle_reinforcements

        for ally, side in (('shu', 'attackers'), ('wei', 'defenders')):
            with self.subTest(side=side), patch('remake.tactical_ai.choose_action', return_value=None):
                game = Campaign(_catalog(shu_days=10, wu_days=2))
                game.command('new', dict(faction='wu', seed=2026), 0)
                wu_city = game.state.cities['jiangxia']
                game.command('diplomacy', dict(action='alliance', city=wu_city.id, target=ally,
                    envoy=wu_city.roster.officer_ids[0], duration=12), game.revision)
                state = game.state
                home, target = state.cities['xiangyang'], state.cities['nanyang']
                game._queue_march(state, home, target, home.roster.officer_ids[:1], 'attack')
                game._complete_turn(state)
                game.command('arrivals', {}, game.revision)
                if side == 'attackers':
                    column, = game.state.extension['travel']['marches']
                    self.assertEqual(column['reason'], 'allied_support_window')
                    game._complete_turn(game.state)
                    game.command('arrivals', {}, game.revision)
                battle = game.state.battle
                self.assertEqual(game.state.phase, 'battle')
                self.assertEqual(battle_grid.player_side(game.state, battle), side)
                offer = game.view()['catalog']['battle_reinforcements']
                self.assertTrue(offer['can_decline'])
                source, = offer['sources']
                ident = source['officers'][0]
                payload = {'battle_id': battle['id']}

                declined = Campaign(game.catalog)
                declined.load_save(game.export_save(compact=True), 0)
                declined.command('battle_decline_support', payload, declined.revision)
                self.assertIsNone(declined.state.battle)
                with self.assertRaisesRegex(GameError, '主戰勢力'):
                    game.command('retreat', payload, game.revision)

                game.command('battle_reinforce', dict(payload, source=source['city'],
                    route=source['routes'][0]['id'], officers=[ident]), game.revision)
                self.assertFalse(game.view()['catalog']['battle_reinforcements']['can_decline'])
                for _ in range(3):
                    if str(ident) in battle_reinforcements.joined(game.state.battle):
                        break
                    game.command('battle_wait', payload, game.revision)
                battle = game.state.battle
                self.assertEqual(battle_reinforcements.joined(battle)[str(ident)]['side'], side)
                self.assertTrue(battle_grid.player_controls(game.state, battle, {'id': ident}))
                self.assertTrue(all(not battle_grid.player_controls(game.state, battle, unit)
                                    for unit in battle[side] if unit['id'] != ident))

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
