"""Actual commands, arrivals, saves and AI all use the authoritative grid/AP."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, digest
from remake import battle_grid as grid
from remake.errors import GameError
from campaign_fixtures import controlled_catalog, reach_battle


WAIT = dict(kind='wait', actor=None, target=None, tactic=None, score=0)


class TacticalCampaignTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(controlled_catalog())
        self.command('new', faction='shu', seed=2026)
        self.command('depart', source='xiangyang', target='nanyang', officers=[146])
        reach_battle(self.game)

    def command(self, kind, **payload):
        return self.game.command(kind, payload, self.game.revision)

    def actors(self):
        battle = self.game.state.battle
        return battle, battle['attackers'][0], battle['defenders'][0]

    def approach(self, *, reserve=4):
        """Walk actual cheapest paths, legally passing days to retain attack AP."""
        for _ in range(100):
            state = self.game.state
            battle, actor, target = self.actors()
            source, distances, previous = grid._paths(state, battle, actor)
            point = battle['extended']['tactical']['positions'][str(target['id'])]
            goals = [(distances[p], p[1], p[0], p) for p in
                ((point['x']-1, point['y']), (point['x']+1, point['y']),
                 (point['x'], point['y']-1), (point['x'], point['y']+1)) if p in distances]
            goal = min(goals)[-1]
            if goal == source and battle['extended']['tactical']['points']['attackers'] >= reserve:
                return
            path = [goal]
            while path[-1] != source:
                path.append(previous[path[-1]])
            path.reverse()
            available = battle['extended']['tactical']['points']['attackers'] - reserve
            affordable = [p for p in path[1:] if distances[p] <= available]
            if affordable:
                x, y = affordable[-1]
                self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=x, y=y)
            else:
                # Isolate movement and player kernels from policy choices.
                # The real side/day/AP transition still executes normally.
                with patch('remake.tactical_ai.choose_action', return_value=WAIT):
                    self.command('battle_wait', battle_id=battle['id'])
        self.fail('The real army failed to reach contact in100valid commands')

    def test_real_arrival_rejects_remote_attack_before_rng_or_any_spending(self):
        battle, actor, target = self.actors()
        self.assertTrue(grid.attack_reason(battle, actor, target, 'attackers'))
        before, revision = self.game.export_save(), self.game.revision
        with self.assertRaises(GameError):
            self.command('attack', battle_id=battle['id'], actor=actor['id'], target=target['id'])
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(self.game.revision, revision)

    def test_real_move_spends_quoted_ap_without_rng_or_strategic_orders(self):
        battle, actor, _ = self.actors()
        options = self.game.view()['catalog']['battle_tactical']['actors'][str(actor['id'])]['reachable']
        destination = min(options, key=lambda p: (p['cost'], p['y'], p['x']))
        before = deepcopy(self.game.state)
        points = battle['extended']['tactical']['points']['attackers']
        self.command('battle_move', battle_id=battle['id'], actor=actor['id'],
            x=destination['x'], y=destination['y'])
        current = self.game.state.battle['extended']['tactical']
        self.assertEqual(current['points']['attackers'], points-destination['cost'])
        self.assertEqual(current['positions'][str(actor['id'])], {key: destination[key] for key in ('x', 'y')})
        self.assertEqual(self.game.state.rng, before.rng)
        self.assertEqual(self.game.state.extension['command_books'], before.extension['command_books'])
        self.assertEqual(self.game.state.soldiers, before.soldiers)

    def test_same_unit_walks_then_attacks_repeatedly_without_free_enemy_counter(self):
        self.approach()
        battle, actor, target = self.actors()
        before = deepcopy(self.game.state)
        points = battle['extended']['tactical']['points']['attackers']
        own_troops = actor['troops']
        initial_target = target['troops']
        with patch.object(self.game, '_counter', side_effect=AssertionError('No per-attack free counter')):
            for _ in range(2):
                battle, actor, target = self.actors()
                self.command('attack', battle_id=battle['id'], actor=actor['id'], target=target['id'])
        battle, actor, target = self.actors()
        self.assertEqual(actor['troops'], own_troops)
        self.assertLess(target['troops'], initial_target)
        self.assertEqual(battle['extended']['tactical']['points']['attackers'], points-4)
        self.assertEqual(self.game.state.rng.draws, before.rng.draws+2)
        self.assertEqual(self.game.state.extension['command_books'], before.extension['command_books'])

    def test_wait_drives_real_enemy_movement_and_returns_control_to_player(self):
        battle, _, _ = self.actors()
        before = deepcopy(battle['extended']['tactical'])
        orders = deepcopy(self.game.state.extension['command_books'])
        with patch.object(self.game, '_execute_battle_move', wraps=self.game._execute_battle_move) as move:
            self.command('battle_wait', battle_id=battle['id'])
        current = self.game.state.battle['extended']['tactical']
        self.assertGreater(move.call_count, 0)
        self.assertEqual(current['side'], 'attackers')
        self.assertNotEqual(current['positions'], before['positions'])
        self.assertEqual(self.game.state.extension['command_books'], orders)
        self.game.validate(self.game.state)

    def test_save_roundtrip_preserves_cells_points_and_bootstraps_old_battle_once(self):
        battle, actor, _ = self.actors()
        destination = min(self.game.view()['catalog']['battle_tactical']['actors'][str(actor['id'])]['reachable'],
                          key=lambda p: (p['cost'], p['y'], p['x']))
        self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=destination['x'], y=destination['y'])
        saved = self.game.export_save()
        restored = Campaign(self.game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        old = deepcopy(saved)
        del old['state']['battle']['extended']['tactical']
        old['checksum'] = digest({key: value for key, value in old.items() if key != 'checksum'})
        restored.load_save(old, restored.revision)
        self.assertEqual(vars(restored.state.rng), vars(self.game.state.rng))
        self.assertEqual(restored.state.soldiers, self.game.state.soldiers)
        self.assertEqual(restored.state.battle['attackers'], self.game.state.battle['attackers'])
        self.assertEqual(restored.state.battle['defenders'], self.game.state.battle['defenders'])
        self.assertIn('tactical', restored.state.battle['extended'])
        migrated = restored.export_save()
        restored.load_save(migrated, restored.revision)
        self.assertEqual(restored.export_save(), migrated)

    def test_bad_moves_and_present_malformed_tactical_save_are_rejected_atomically(self):
        battle, actor, target = self.actors()
        point = battle['extended']['tactical']['positions'][str(target['id'])]
        for x, y in ((-1, 0), (31, 0), (1, True), (point['x'], point['y'])):
            saved = self.game.export_save()
            with self.assertRaises(GameError):
                self.command('battle_move', battle_id=battle['id'], actor=actor['id'], x=x, y=y)
            self.assertEqual(self.game.export_save(), saved)
        saved = self.game.export_save()
        for edit in (
            lambda row: row.update(points={'attackers': True, 'defenders': 10}),
            lambda row: row.update(points={'attackers': 60, 'defenders': 10}),
            lambda row: row['positions'][str(actor['id'])].update(x=31),
            lambda row: row['positions'].update({str(actor['id']): deepcopy(point)}),
            lambda row: row.update(schema='bad'),
            lambda row: row.update(passed={'attackers': True, 'defenders': False}),
        ):
            bad = deepcopy(saved)
            edit(bad['state']['battle']['extended']['tactical'])
            bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
            with self.assertRaises(GameError):
                self.game.load_save(bad, self.game.revision)
            self.assertEqual(self.game.export_save(), saved)

    def test_legacy_defender_battle_keeps_player_decision_without_replaying_enemy_turn(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game._start_expanded_battle(game.state, game.state.cities['nanyang'],
                                    game.state.cities['xiangyang'], [123])
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual(game._player_sides(game.state)[0], 'defenders')
        before = deepcopy(game.state)
        legacy = deepcopy(game.export_save())
        del legacy['state']['battle']['extended']['tactical']
        legacy['checksum'] = digest({key: value for key, value in legacy.items() if key != 'checksum'})
        restored = Campaign(game.catalog)
        restored.load_save(legacy, 0)
        tactical = restored.state.battle['extended']['tactical']
        self.assertEqual(tactical['side'], 'defenders')
        self.assertEqual(tactical['passed'], dict(attackers=True, defenders=False))
        self.assertEqual(restored.state.rng, before.rng)
        self.assertEqual(restored.state.soldiers, before.soldiers)
        self.assertEqual(restored.state.officers, before.officers)
        self.assertEqual(restored.state.extension['command_books'], before.extension['command_books'])
        self.assertEqual(restored.state.battle['attackers'], before.battle['attackers'])
        self.assertEqual(restored.state.battle['defenders'], before.battle['defenders'])
        view = restored.view()['catalog']['battle_tactical']
        self.assertTrue(view['can_end'])
        self.assertTrue(any(row['can_act'] for row in view['actors'].values()))
        migrated = restored.export_save()
        restored.load_save(migrated, restored.revision)
        self.assertEqual(restored.export_save(), migrated, 'Existing positions, passed sides and AP never refresh on reload')
        with patch('remake.tactical_ai.choose_action', return_value=WAIT):
            restored.command('battle_wait', dict(battle_id=restored.state.battle['id']), restored.revision)
        self.assertEqual(restored.state.phase, 'battle')
        self.assertEqual(restored.state.battle['round'], before.battle['round']+1)
        self.assertEqual(restored.state.battle['extended']['tactical']['side'], 'defenders')
        self.assertEqual(restored.state.rng, before.rng)
        self.assertEqual(restored.state.soldiers, before.soldiers)
        self.assertEqual(restored.state.extension['command_books'], before.extension['command_books'])
        restored.validate(restored.state)

    def test_thirty_day_limit_retreats_attackers_without_advancing_strategy_calendar(self):
        before = deepcopy(self.game.state)
        with patch('remake.tactical_ai.choose_action', return_value=WAIT):
            for _ in range(30):
                self.command('battle_wait', battle_id=self.game.state.battle['id'])
        state = self.game.state
        self.assertEqual(state.phase, 'result')
        self.assertEqual((state.battle['outcome'], state.battle['extended']['withdrawn']), ('retreat', 'attackers'))
        self.assertEqual((state.year, state.month, state.day, state.turn),
                         (before.year, before.month, before.day, before.turn))
        self.assertEqual(state.rng, before.rng)
        self.assertEqual(state.extension['command_books'], before.extension['command_books'])
        self.game.validate(state)

    def test_ai_versus_ai_uses_real_paths_shared_points_and_conserves_soldiers(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='wu', seed=2026), 0)
        state = game.state
        game._start_expanded_battle(state, state.cities['xiangyang'], state.cities['nanyang'], [146])
        orders = deepcopy(state.extension['command_books'])
        with patch.object(game, '_execute_battle_move', wraps=game._execute_battle_move) as move, \
             patch.object(grid, 'spend', wraps=grid.spend) as spend:
            game._resolve_ai_battle(state)
        self.assertGreater(move.call_count, 0)
        self.assertEqual({call.args[1] for call in spend.call_args_list}, set(grid.SIDES))
        self.assertIsNone(state.battle)
        self.assertEqual(len(state.settled_battles), 1)
        self.assertEqual(state.extension['command_books'], orders)
        game.validate(state)
        current = sum(city.reserves for city in state.cities.values()) + sum(o.troops for o in state.officers.values())
        self.assertEqual(current + state.soldiers['lost'], state.soldiers['initial'] + state.soldiers['recruited'])


if __name__ == '__main__':
    unittest.main()
