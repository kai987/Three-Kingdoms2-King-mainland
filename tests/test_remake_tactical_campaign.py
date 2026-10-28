"""Actual commands, arrivals, saves and AI all use the authoritative grid/AP."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, SeedRng, digest
from remake import battle_grid as grid
from remake.errors import GameError
from campaign_fixtures import controlled_catalog, reach_battle
from test_remake_tactical_ai import battle as contact_battle


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

    def test_repeated_attacks_include_contact_replies_without_free_enemy_turn(self):
        self.approach()
        battle, actor, target = self.actors()
        before = deepcopy(self.game.state)
        points = battle['extended']['tactical']['points']['attackers']
        own_troops = actor['troops']
        initial_target = target['troops']
        with patch.object(self.game, '_counter', side_effect=AssertionError('No free whole-side AI response')):
            for _ in range(2):
                battle, actor, target = self.actors()
                self.command('attack', battle_id=battle['id'], actor=actor['id'], target=target['id'])
        battle, actor, target = self.actors()
        self.assertLess(actor['troops'], own_troops)
        self.assertLess(target['troops'], initial_target)
        self.assertEqual(battle['extended']['tactical']['points']['attackers'], points-4)
        self.assertEqual(self.game.state.rng.draws, before.rng.draws+4)
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


class ContactRetaliationTests(unittest.TestCase):
    """A contact encounter is bilateral; it is not a free enemy policy turn."""
    def setUp(self):
        self.game = contact_battle(three_enemies=False)

    def units(self):
        b = self.game.state.battle
        return b, b['attackers'][0], b['defenders'][0]

    def attack(self):
        b, actor, target = self.units()
        return self.game.command('attack', dict(battle_id=b['id'], actor=actor['id'],
                                  target=target['id']), self.game.revision)

    def test_contact_attack_has_one_reply_two_real_draws_and_one_ap_payment(self):
        b, actor, target = self.units()
        before = deepcopy(self.game.state)
        with patch('remake.tactical_ai.choose_action', side_effect=AssertionError('No free enemy turn')), \
                patch.object(self.game, '_counter', side_effect=AssertionError('No legacy response')):
            result = self.attack()
        after, actor, target = self.units()
        self.assertLess(actor['troops'], before.battle['attackers'][0]['troops'])
        self.assertLess(target['troops'], before.battle['defenders'][0]['troops'])
        points = after['extended']['tactical']['points']
        self.assertEqual(points['attackers'], before.battle['extended']['tactical']['points']['attackers']-2)
        self.assertEqual(points['defenders'], before.battle['extended']['tactical']['points']['defenders'])
        self.assertEqual(after['extended']['tactical']['side'], 'attackers')
        self.assertEqual(self.game.state.rng.draws, before.rng.draws+2)
        self.assertEqual(self.game.state.extension['command_books'], before.extension['command_books'])
        first, reply = result['presentation']['scenes']
        self.assertEqual((first['actor'], first['target'], first['counter']), (actor['id'], target['id'], False))
        self.assertEqual((reply['actor'], reply['target'], reply['counter'], reply['own']),
                         (target['id'], actor['id'], True, 'defenders'))
        self.assertEqual(first['after'], reply['before'])
        self.assertTrue(reply['success']); self.assertFalse(reply['skipped'])

    def test_reply_uses_surviving_troops_and_both_existing_guard_counters(self):
        b, actor, target = self.units()
        support = b['extended']['support']
        support[str(actor['id'])]['guard'] = 2
        support[str(target['id'])]['guard'] = 2
        support[str(actor['id'])]['morale'] = 100
        support[str(target['id'])]['morale'] = 25
        seen = []
        damage = self.game._damage
        def observe(state, first, second):
            seen.append((first['id'], second['id'], first['troops'], second['troops'],
                         state.battle['extended']['support'][str(first['id'])]['morale']))
            return damage(state, first, second)
        with patch.object(self.game, '_damage', side_effect=observe):
            result = self.attack()
        b, actor, target = self.units()
        first, reply = result['presentation']['scenes']
        target_after_hit = next(u['troops'] for u in first['after']['units'] if u['id']==target['id'])
        self.assertEqual([(r[0], r[1], r[4]) for r in seen],
                         [(actor['id'], target['id'], 100), (target['id'], actor['id'], 25)])
        self.assertEqual(seen[1][2], target_after_hit, 'The defeated soldiers do not attack again')
        self.assertEqual(b['extended']['support'][str(actor['id'])]['guard'], 1)
        self.assertEqual(b['extended']['support'][str(target['id'])]['guard'], 1)
        self.assertEqual(reply['before'], first['after'])

    def test_routed_defender_cannot_reply_or_draw_a_second_damage_roll(self):
        b, actor, target = self.units(); target['troops'] = 1
        troops, draws = actor['troops'], self.game.state.rng.draws
        result = self.attack()
        b, actor, target = self.units()
        self.assertEqual(target['troops'], 0)
        self.assertEqual(actor['troops'], troops)
        self.assertEqual(self.game.state.rng.draws, draws+1)
        self.assertEqual(len(result['presentation']['scenes']), 1)
        self.assertEqual((self.game.state.phase, b['outcome']), ('result', 'victory'))

    def test_zero_defender_ap_does_not_disable_its_in_encounter_reply(self):
        b, actor, target = self.units()
        b['extended']['tactical']['points']['defenders'] = 0
        troops = actor['troops']
        result = self.attack()
        b, actor, target = self.units()
        self.assertLess(actor['troops'], troops)
        self.assertEqual(b['extended']['tactical']['points']['defenders'], 0)
        self.assertTrue(result['presentation']['scenes'][1]['counter'])

    def test_reply_does_not_activate_a_second_tactical_ambush_command(self):
        b, actor, target = self.units()
        b['extended']['ambush'] = dict(actor=actor['id'])
        draws = self.game.state.rng.draws
        result = self.attack()
        b, actor, target = self.units()
        self.assertEqual([scene['kind'] for scene in result['presentation']['scenes']], ['attack', 'attack'])
        self.assertEqual(b['extended']['ambush'], dict(actor=actor['id']))
        self.assertEqual(self.game.state.rng.draws, draws+2)

    def test_reply_can_route_the_initiator_and_resolve_defeat(self):
        b, actor, target = self.units(); actor['troops'] = 1
        draws = self.game.state.rng.draws
        result = self.attack()
        b, actor, target = self.units()
        self.assertEqual(actor['troops'], 0)
        self.assertGreater(target['troops'], 0)
        self.assertEqual(self.game.state.rng.draws, draws+2)
        self.assertEqual(len(result['presentation']['scenes']), 2)
        self.assertEqual((self.game.state.phase, b['outcome']), ('result', 'defeat'))

    def test_stunned_defender_uses_its_one_skip_without_a_damage_draw(self):
        b, actor, target = self.units()
        b['extended']['support'][str(target['id'])]['stunned'] = 1
        troops, draws = actor['troops'], self.game.state.rng.draws
        result = self.attack()
        b, actor, target = self.units(); reply = result['presentation']['scenes'][1]
        self.assertTrue(reply['counter']); self.assertTrue(reply['skipped']); self.assertFalse(reply['success'])
        self.assertEqual(actor['troops'], troops)
        self.assertEqual(self.game.state.rng.draws, draws+1)
        self.assertEqual(b['extended']['support'][str(target['id'])]['stunned'], 0)

    def test_stunned_initiator_does_not_create_an_unprovoked_reply(self):
        b, actor, target = self.units()
        b['extended']['support'][str(actor['id'])]['stunned'] = 1
        before = deepcopy(b); draws = self.game.state.rng.draws
        result = self.attack()
        b, actor, target = self.units()
        self.assertEqual([u['troops'] for side in grid.SIDES for u in b[side]],
                         [u['troops'] for side in grid.SIDES for u in before[side]])
        self.assertEqual(self.game.state.rng.draws, draws)
        self.assertEqual(len(result['presentation']['scenes']), 1)
        self.assertTrue(result['presentation']['scenes'][0]['skipped'])

    def test_ai_initiated_contact_uses_the_same_two_way_kernel(self):
        b, attacker, defender = self.units()
        row = b['extended']['tactical']; row['side'] = 'defenders'
        before = deepcopy(self.game.state)
        with patch.object(self.game, '_damage', wraps=self.game._damage) as damage:
            self.game._perform_battle_action(self.game.state,
                dict(kind='attack', actor=defender['id'], target=attacker['id']),
                'defenders', 'attackers', finish=False, counter=True)
        b, attacker, defender = self.units()
        self.assertEqual(damage.call_count, 2)
        self.assertLess(attacker['troops'], before.battle['attackers'][0]['troops'])
        self.assertLess(defender['troops'], before.battle['defenders'][0]['troops'])
        self.assertEqual(row['points']['defenders'], before.battle['extended']['tactical']['points']['defenders']-2)
        self.assertEqual(row['points']['attackers'], before.battle['extended']['tactical']['points']['attackers'])
        self.assertEqual(self.game.state.rng.draws, before.rng.draws+2)

    def test_tactics_do_not_receive_an_ordinary_contact_reply(self):
        from remake.campaign_expansion import TACTICS
        b, actor, target = self.units()
        troops = actor['troops']; points = deepcopy(b['extended']['tactical']['points'])
        with patch.object(self.game, '_contact_retaliation', side_effect=AssertionError('Not a melee encounter')):
            result = self.game.command('tactic', dict(battle_id=b['id'], actor=actor['id'],
                target=target['id'], tactic=0), self.game.revision)
        b, actor, target = self.units()
        self.assertEqual(actor['troops'], troops)
        self.assertTrue(all(scene['kind']=='tactic' for scene in result['presentation']['scenes']))
        self.assertEqual(b['extended']['tactical']['points']['attackers'], points['attackers']-TACTICS[0][1])
        self.assertEqual(b['extended']['tactical']['points']['defenders'], points['defenders'])

    def test_contact_exchange_estimates_reply_risk_without_sampling_or_mutation(self):
        from remake.campaign_expansion import TACTICS
        from remake.tactical_ai import candidates, expected_contact_exchange
        b, actor, target = self.units()
        before = deepcopy(self.game.state)
        with patch.object(SeedRng, 'next', side_effect=AssertionError('No RNG lookahead')):
            outgoing, reply = expected_contact_exchange(b, actor, target)
            row = next(row for row in candidates(self.game.state, b, 'attackers', 'defenders',
                'plain', TACTICS, depth=0) if row['kind']=='attack')
        self.assertGreater(outgoing, 0); self.assertGreater(reply, 0)
        self.assertLess(row['score'], outgoing, 'AI accounts for the contact opponent replying')
        self.assertEqual(self.game.state, before)
        b['extended']['support'][str(target['id'])]['stunned'] = 1
        self.assertEqual(expected_contact_exchange(b, actor, target), (outgoing, 0))

    def test_contact_save_and_stale_retry_never_repeat_retaliation(self):
        self.attack()
        saved = self.game.export_save(); revision = self.game.revision
        restored = Campaign(self.game.catalog); restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        b, actor, target = self.units()
        with self.assertRaises(GameError):
            self.game.command('attack', dict(battle_id=b['id'], actor=actor['id'], target=target['id']), revision-1)
        self.assertEqual(self.game.export_save(), saved)
        for game in (self.game, restored):
            battle = game.state.battle
            game.command('attack', dict(battle_id=battle['id'], actor=battle['attackers'][0]['id'],
                target=battle['defenders'][0]['id']), game.revision)
        self.assertEqual(restored.export_save(), self.game.export_save())


if __name__ == '__main__':
    unittest.main()
