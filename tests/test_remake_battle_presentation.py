"""Animation receipts describe committed effects without becoming gameplay data."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, SeedRng, canonical
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from remake import presentation
from remake.session import CampaignSession
from campaign_fixtures import controlled_catalog
from test_remake_tactical_ai import battle, actors, successful_rng
from test_remake_civil_staff_campaign import staff_catalog


SCENE_FIELDS = {'kind', 'battle_id', 'actor', 'target', 'own', 'counter', 'tactic',
                'effect', 'success', 'skipped', 'move', 'reply', 'before', 'after'}
SNAPSHOT_FIELDS = {'round', 'outcome', 'duel', 'units'}
UNIT_FIELDS = {'id', 'side', 'troops', 'health', 'energy', 'guard', 'stunned'}


class BattlePresentationTests(unittest.TestCase):
    def perform(self, game, kind, **payload):
        before = game.export_save()
        reference = Campaign(game.catalog)
        reference.load_save(json.loads(json.dumps(before, ensure_ascii=False)), 0)
        result = game.command(kind, payload, game.revision)
        # The identical command with recording disabled is the gameplay oracle.
        with patch.object(presentation, 'snapshot', return_value=None):
            reference.command(kind, deepcopy(payload), reference.revision)
        self.assertEqual(game.export_save(), reference.export_save())
        self.assertEqual(game.state.rng.draws, reference.state.rng.draws)
        self.assertEqual(game.catalog.sha256, before['catalog_sha256'])
        self.assertFalse(hasattr(game, '_presentation_capture'))
        self.assertNotIn('presentation', game.view())
        self.assertNotIn('presentation', game.export_save())
        receipt = result['presentation']
        self.assertEqual(set(receipt), {'schema', 'revision', 'scenes'})
        self.assertEqual(receipt['schema'], presentation.SCHEMA)
        self.assertEqual(receipt['revision'], game.revision)
        self.assertTrue(0 < len(receipt['scenes']) <= presentation.MAX_SCENES)
        for scene in receipt['scenes']:
            self.assertEqual(set(scene), SCENE_FIELDS)
            self.assertIn(scene['own'], {'attackers', 'defenders'})
            for key in ('counter', 'success', 'skipped'):
                self.assertIs(type(scene[key]), bool)
            for key in ('before', 'after'):
                snapshot = scene[key]
                self.assertEqual(set(snapshot), SNAPSHOT_FIELDS)
                self.assertLessEqual(len(snapshot['units']), 20)
                for unit in snapshot['units']:
                    self.assertEqual(set(unit), UNIT_FIELDS)
        return receipt['scenes']

    def unit(self, scene, when, ident):
        return next(row for row in scene[when]['units'] if row['id'] == ident)

    def test_actual_attack_and_ai_response_identify_a_different_counter_target(self):
        game = Campaign(controlled_catalog())
        game.state = game._new('shu', 2026)
        state = game.state
        selected = state.cities['xiangyang'].roster.officer_ids[:2]
        game._start_expanded_battle(state, state.cities['xiangyang'], state.cities['nanyang'], selected)
        b = state.battle; actor, other = b['attackers']; target = b['defenders'][0]
        choice = dict(kind='attack', actor=target['id'], target=other['id'])
        with patch('remake.tactical_ai.choose_action', return_value=choice):
            scenes = self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])
        self.assertEqual([(s['kind'], s['actor'], s['target'], s['counter']) for s in scenes],
            [('attack', actor['id'], target['id'], False),
             ('attack', target['id'], other['id'], True)])
        for scene in scenes:
            self.assertGreater(self.unit(scene, 'before', scene['target'])['troops'],
                               self.unit(scene, 'after', scene['target'])['troops'])
        self.assertEqual(self.unit(scenes[1], 'before', actor['id'])['troops'],
                         self.unit(scenes[1], 'after', actor['id'])['troops'])

    def test_all_sixteen_tactics_record_the_actual_success_cost_and_affected_units(self):
        for tid, (_, cost, effect, _) in enumerate(TACTICS):
            terrain = 'water' if effect in {'water', 'chain', 'flood'} else 'mountain' if effect == 'rock' else 'plain'
            with self.subTest(tactic=tid):
                game = battle(terrain)
                b, actor, target, _, _ = actors(game)
                successful_rng(game.state)
                if effect in {'trap', 'rock'}:
                    b['extended']['support'][str(target['id'])]['health'] = 2
                scenes = self.perform(game, 'tactic', battle_id=b['id'], actor=actor['id'],
                                      target=target['id'], tactic=tid)
                scene = scenes[0]
                self.assertEqual((scene['kind'], scene['tactic'], scene['effect']), ('tactic', tid, effect))
                self.assertTrue(scene['success']); self.assertFalse(scene['skipped'])
                self.assertEqual(self.unit(scene, 'after', actor['id'])['energy'],
                                 self.unit(scene, 'before', actor['id'])['energy'] - cost)
                if effect in {'area', 'crossbow', 'flood', 'inferno'}:
                    expected = min(len(b['defenders']), 3 if effect == 'area' else 2 if effect == 'crossbow' else 20)
                    changed = sum(u['troops'] != self.unit(scene, 'after', u['id'])['troops']
                                  for u in scene['before']['units'] if u['side'] == 'defenders')
                    self.assertEqual(changed, expected)

    def test_counter_tactic_is_flagged_and_failure_is_not_guessed_from_log_text(self):
        game = battle(three_enemies=False)
        b, actor, target, _, _ = actors(game)
        with patch('remake.tactical_ai.choose_action', return_value=dict(kind='tactic',
                actor=target['id'], target=actor['id'], tactic=15)):
            scenes = self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])
        self.assertEqual((scenes[-1]['kind'], scenes[-1]['counter'], scenes[-1]['tactic']), ('tactic', True, 15))
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        seed = next(i for i in range(1, 10000) if SeedRng(i).next() % 100 >= 95)
        game.state.rng = SeedRng(seed)
        b['log'] = ['unrelated translated text'] * 80
        scene = self.perform(game, 'tactic', battle_id=b['id'], actor=actor['id'],
                             target=target['id'], tactic=0)[0]
        self.assertFalse(scene['success'])
        self.assertEqual(self.unit(scene, 'before', target['id'])['troops'],
                         self.unit(scene, 'after', target['id'])['troops'])

    def test_ambush_precedes_action_and_its_losses_are_not_counted_twice(self):
        for routed in (False, True):
            with self.subTest(routed=routed):
                game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
                b['extended']['ambush'] = dict(actor=target['id'])
                if routed: actor['troops'] = 1
                scenes = self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])
                trap, action = scenes[:2]
                self.assertEqual((trap['kind'], trap['actor'], trap['target']), ('ambush', target['id'], actor['id']))
                self.assertEqual(trap['after'], action['before'])
                self.assertEqual(action['skipped'], routed)
                if routed:
                    self.assertFalse(action['success'])
                    self.assertEqual(action['before'], action['after'])

    def test_stunned_attack_is_a_precise_skipped_action(self):
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        b['extended']['support'][str(actor['id'])]['stunned'] = 1
        scene = self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])[0]
        self.assertTrue(scene['skipped']); self.assertFalse(scene['success'])
        self.assertEqual(self.unit(scene, 'before', actor['id'])['stunned'], 1)
        self.assertEqual(self.unit(scene, 'after', actor['id'])['stunned'], 0)
        self.assertEqual(self.unit(scene, 'before', target['id'])['troops'],
                         self.unit(scene, 'after', target['id'])['troops'])

    def test_duel_acceptance_real_reply_moves_withdrawal_and_last_hit(self):
        for move in ('strike', 'guard', 'feint', 'withdraw', 'last_hit'):
            with self.subTest(move=move):
                game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
                successful_rng(game.state)
                accepted = self.perform(game, 'duel_start', battle_id=b['id'], actor=actor['id'], target=target['id'])[0]
                self.assertTrue(accepted['success']); self.assertIsNotNone(accepted['after']['duel'])
                if move == 'last_hit':
                    game.state.battle['extended']['support'][str(target['id'])]['health'] = 2
                rng = deepcopy(game.state.rng); expected_reply = None if move == 'withdraw' else ('strike', 'guard', 'feint')[rng.next() % 3]
                scene = self.perform(game, 'duel_action', battle_id=b['id'],
                                     move='strike' if move == 'last_hit' else move)[0]
                self.assertEqual(scene['reply'], expected_reply)
                self.assertEqual(scene['move'], 'strike' if move == 'last_hit' else move)
                self.assertIsNotNone(scene['before']['duel'])
                if move in {'last_hit', 'withdraw'}: self.assertIsNone(scene['after']['duel'])
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        game.state.rng = SeedRng(next(i for i in range(1,10000) if SeedRng(i).next() % 100 >= 90))
        denied = self.perform(game, 'duel_start', battle_id=b['id'], actor=actor['id'], target=target['id'])[0]
        self.assertFalse(denied['success']); self.assertIsNone(denied['after']['duel'])

    def test_failed_command_rolls_back_and_cleans_all_pending_presentation(self):
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        saved, revision = game.export_save(), game.revision
        with patch.object(game, 'validate', side_effect=ValueError('controlled post-action failure')):
            with self.assertRaises(ValueError):
                game.command('attack', dict(battle_id=b['id'], actor=actor['id'], target=target['id']), revision)
        self.assertEqual(game.export_save(), saved); self.assertEqual(game.revision, revision)
        self.assertFalse(hasattr(game, '_presentation_capture'))
        with self.assertRaises(GameError):
            game.command('attack', dict(battle_id='stale', actor=actor['id'], target=target['id']), revision)
        self.assertFalse(hasattr(game, '_presentation_capture'))
        self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])

    def test_retreat_settle_idempotency_and_load_never_replay_receipts(self):
        game = battle(three_enemies=False); bid = game.state.battle['id']
        scene = self.perform(game, 'retreat', battle_id=bid)[0]
        self.assertEqual(scene['kind'], 'retreat'); self.assertIsNone(scene['actor'])
        self.assertEqual(scene['after']['outcome'], 'retreat')
        result = game.command('settle', dict(battle_id=bid), game.revision)
        self.assertNotIn('presentation', result)
        saved, revision = game.export_save(), game.revision
        self.assertNotIn('presentation', game.command('settle', dict(battle_id=bid), 0))
        self.assertEqual(game.export_save(), saved); self.assertEqual(game.revision, revision)
        loaded = Campaign(game.catalog)
        self.assertNotIn('presentation', loaded.load_save(saved, 0))

    def test_recording_is_bounded_and_ignores_ai_only_battles_and_direct_calls(self):
        game = battle(three_enemies=False)
        self.assertIsNone(presentation.snapshot(game, game.state))
        with presentation.capture(game) as scenes:
            for _ in range(presentation.MAX_SCENES + 3):
                before = presentation.snapshot(game, game.state)
                presentation.record(game, game.state, before, kind='attack', actor=146, target=123, own='attackers')
        self.assertEqual(len(scenes), presentation.MAX_SCENES)
        game = battle(three_enemies=False, player='wu')
        with presentation.capture(game) as scenes:
            game._resolve_ai_battle(game.state)
        self.assertEqual(scenes, [])
        self.assertFalse(hasattr(game, '_presentation_capture'))

    def test_session_forwards_only_the_current_successful_command_receipt(self):
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        with patch('remake.session.Catalog', return_value=game.catalog):
            session = CampaignSession([ROOT / 'controlled.json'])
        session.game = game
        result = session.command('attack', dict(battle_id=b['id'], actor=actor['id'], target=target['id']), session.revision)
        self.assertEqual(result['presentation']['revision'], session.revision)
        self.assertEqual(result['presentation']['scenes'][0]['kind'], 'attack')
        self.assertNotIn('presentation', session.view())
        saved = session.export_save()
        self.assertNotIn('presentation', session.load_save(saved, session.revision))
        self.assertEqual(canonical(session.export_save()), canonical(saved))

    def test_generated_actor_keeps_its_string_identity_through_real_effects(self):
        game = Campaign(staff_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        ident = game.state.extension['civil_staff']['cities']['nanjun']['candidate']['id']
        game.command('hire_staff', dict(city='nanjun', candidate=ident), game.revision)
        game.command('allocate', dict(city='nanjun', officer=ident, troops=999), game.revision)
        game._complete_turn(game.state)
        game._reconcile_factions(game.state)
        game._start_expanded_battle(game.state, game.state.cities['nanjun'],
                                   game.state.cities['jiangxia'], [ident])
        b = game.state.battle
        scenes = self.perform(game, 'attack', battle_id=b['id'], actor=ident, target=b['defenders'][0]['id'])
        self.assertEqual(scenes[0]['actor'], ident)
        self.assertEqual(self.unit(scenes[0], 'before', ident)['id'], ident)
        self.assertNotIn(ident, game.catalog.by_id)

    def test_completed_ai_turn_and_stale_attack_do_not_replay_receipts(self):
        game = battle(three_enemies=False); b, actor, target, _, _ = actors(game)
        stale = game.revision
        self.perform(game, 'attack', battle_id=b['id'], actor=actor['id'], target=target['id'])
        saved = game.export_save()
        with self.assertRaises(GameError):
            game.command('attack', dict(battle_id=b['id'], actor=actor['id'], target=target['id']), stale)
        self.assertEqual(game.export_save(), saved)
        self.assertFalse(hasattr(game, '_presentation_capture'))
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('end_turn', {}, game.revision)
        self.assertNotIn('presentation', game.command('ai', dict(turn=1), game.revision))
        saved, revision = game.export_save(), game.revision
        self.assertNotIn('presentation', game.command('ai', dict(turn=1), 0))
        self.assertEqual(game.export_save(), saved); self.assertEqual(game.revision, revision)


if __name__ == '__main__':
    unittest.main()
