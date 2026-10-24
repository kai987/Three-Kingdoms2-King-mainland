"""The new risk move shares authoritative effects; old normal duels stay exact."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, SeedRng, digest
from remake.errors import GameError
from remake import presentation
from remake.officers import OfficerProfile
import test_remake_tactical_ai as tactical_fixture
from test_remake_tactical_ai import battle, actors, successful_rng


def active_duel(seed, *, own_health=80, enemy_health=80, round_number=1):
    game = battle(three_enemies=False)
    b, a, t, _, _ = actors(game)
    successful_rng(game.state)
    game.command('duel_start', dict(battle_id=b['id'], actor=a['id'], target=t['id']), game.revision)
    b, a, t, _, _ = actors(game)
    assert b['extended']['duel'] is not None
    b['extended']['support'][str(a['id'])]['health'] = own_health
    b['extended']['support'][str(t['id'])]['health'] = enemy_health
    b['extended']['duel']['round'] = round_number
    game.state.rng = SeedRng(seed)
    game.validate(game.state)
    return game


class DesperateDuelTests(unittest.TestCase):
    def perform(self, game, move='desperate'):
        bid = game.state.battle['id']
        result = game.command('duel_action', dict(battle_id=bid, move=move), game.revision)
        self.assertEqual(len(result['presentation']['scenes']), 1, 'The exchange is not followed by a second tactical attack')
        return result['presentation']['scenes'][0]

    def healths(self, game):
        b, a, t, _, _ = actors(game)
        return tuple(b['extended']['support'][str(u['id'])]['health'] for u in (a, t))

    def test_success_cutoff29_doubles_damage_and_only_spends_real_draws(self):
        # Captured SeedRng5: reply=strike, quality29, ordinary base15.
        game = active_duel(5)
        scene = self.perform(game)
        self.assertEqual(self.healths(game), (66, 50))
        self.assertEqual(game.state.rng.draws, 4)
        self.assertEqual((scene['move'], scene['reply'], scene['success']), ('desperate', 'strike', True))
        self.assertEqual(scene['before']['duel']['round'], 1)
        self.assertEqual(scene['after']['duel']['round'], 2)

    def test_quality30_fails_and_minimum_self_loss_is10(self):
        # Seed30193: quality30 rejects the hit; low-five-bit0 means self-loss10.
        game = active_duel(30193)
        scene = self.perform(game)
        self.assertEqual(self.healths(game), (60, 80))
        self.assertEqual(game.state.rng.draws, 5)
        self.assertFalse(scene['success'])
        self.assertIn('本方舍命一击失手，自损体力10。', game.state.battle['extended']['duel']['log'])

    def test_failure_self_loss30_and_rejected_values31_to21_are_not_moduloed(self):
        # Seed3908 accepts masked20=>30. Seed10 rejects28 and22, then15=>25.
        for seed, expected_health, draws, loss in [(3908, 41, 5, 30), (10, 46, 7, 25)]:
            with self.subTest(seed=seed):
                game = active_duel(seed)
                self.assertFalse(self.perform(game)['success'])
                self.assertEqual(self.healths(game), (expected_health, 80))
                self.assertEqual(game.state.rng.draws, draws)
                self.assertIn(f'本方舍命一击失手，自损体力{loss}。', game.state.battle['extended']['duel']['log'])

    def test_guard_applies_after_doubling_and_keeps_its_real_reply(self):
        # Seed226: base14 doubles to28; guard reduces28//3=9, not(14//3)*2.
        game = active_duel(226)
        scene = self.perform(game)
        self.assertEqual((scene['reply'], scene['success']), ('guard', True))
        self.assertEqual(self.healths(game), (76, 71))
        self.assertEqual(game.state.rng.draws, 4)

    def test_wounded_ai_uses_same_move_without_a_policy_rng_draw(self):
        # Normal strike choice at health30 becomes desperate. One existing AI
        # choice draw plus the actual attacks' draws, no extra strategy draw.
        game = active_duel(4, enemy_health=30)
        scene = self.perform(game, 'guard')
        self.assertEqual(scene['reply'], 'desperate')
        self.assertEqual(self.healths(game), (74, 25))
        self.assertEqual(game.state.rng.draws, 4)
        healthy = active_duel(4, enemy_health=31)
        other = self.perform(healthy, 'guard')
        self.assertEqual(other['reply'], 'strike')
        self.assertEqual(healthy.state.rng.draws, 3)
        failing = active_duel(1, enemy_health=30)
        scene = self.perform(failing, 'guard')
        self.assertEqual(scene['reply'], 'desperate')
        self.assertEqual(self.healths(failing), (80, 1))
        self.assertEqual(failing.state.battle['extended']['duel_history'][-1]['result'], '本方单挑胜出')

    def test_both_self_losses_can_rout_without_death_negative_hp_or_extra_attack(self):
        game = active_duel(4, own_health=20, enemy_health=20)
        before = deepcopy(game.state.battle)
        scene = self.perform(game)
        self.assertFalse(scene['success'])
        self.assertEqual(scene['reply'], 'desperate')
        self.assertEqual(self.healths(game), (1, 1))
        b, a, t, _, _ = actors(game)
        self.assertEqual((a['troops'], t['troops']), (0, 0))
        self.assertIsNone(b['extended']['duel'])
        self.assertEqual(b['extended']['duel_history'][-1]['result'], '双方负伤退场')
        self.assertTrue(game.state.officers[a['id']].alive)
        self.assertTrue(game.state.officers[t['id']].alive)
        self.assertEqual(sum(u['start'] for side in ('attackers', 'defenders') for u in before[side]),
                         sum(u['start'] for side in ('attackers', 'defenders') for u in b[side]))
        game.validate(game.state)

    def test_twentieth_round_finishes_and_cannot_charge_again(self):
        game = active_duel(5, round_number=20)
        stocks = {key: (c.gold, c.grain, c.reserves) for key, c in game.state.cities.items()}
        self.perform(game)
        b = game.state.battle
        self.assertIsNone(b['extended']['duel'])
        self.assertEqual(b['extended']['duel_history'][-1]['result'], '二十合未分胜负')
        self.assertEqual(stocks, {key: (c.gold, c.grain, c.reserves) for key, c in game.state.cities.items()})
        saved = game.export_save()
        with self.assertRaises(GameError):
            self.perform(game)
        self.assertEqual(game.export_save(), saved)

    def test_save_replay_and_presentation_toggle_are_exact(self):
        for seed in (5, 30193, 10):
            with self.subTest(seed=seed):
                game = active_duel(seed)
                saved = game.export_save()
                reference = Campaign(game.catalog)
                reference.load_save(deepcopy(saved), 0)
                scene = self.perform(game)
                with patch.object(presentation, 'snapshot', return_value=None):
                    result = reference.command('duel_action', dict(battle_id=reference.state.battle['id'], move='desperate'), reference.revision)
                self.assertNotIn('presentation', result)
                self.assertEqual(game.export_save(), reference.export_save())
                self.assertNotIn('presentation', game.export_save())
                self.assertNotIn('weapon', game.state.battle['extended']['duel'] or {})
                self.assertEqual(scene['after']['units'], presentation_snapshot(game))

    def test_invalid_phase_identity_and_stale_revision_are_atomic(self):
        game = active_duel(5)
        for payload, revision in [
            ({'battle_id': 'stale', 'move': 'desperate'}, game.revision),
            ({'battle_id': game.state.battle['id'], 'move': 'not-a-move'}, game.revision),
            ({'battle_id': game.state.battle['id'], 'move': 'desperate'}, game.revision - 1),
        ]:
            saved = game.export_save()
            with self.assertRaises(GameError):game.command('duel_action', payload, revision)
            self.assertEqual(game.export_save(), saved)
        game.state.phase = 'city'
        saved = game.export_save()
        with self.assertRaises(GameError):self.perform(game)
        self.assertEqual(game.export_save(), saved)

    def test_preexisting_four_moves_keep_original_saved_state_rng_and_receipts(self):
        baseline = json.loads((ROOT / 'tests/fixtures/duel-pre-desperate-baseline.json').read_text())
        self.assertEqual(baseline['source_commit'], 'eea539c579af3f72c130c160a00fe9ccaa28e6e0')
        self.assertEqual(len(baseline['vectors']), 32)
        for row in baseline['vectors']:
            with self.subTest(seed=row['seed'], move=row['move']):
                # This artifact predates the charisma/health/loyalty dataset.
                # Replay its retained inputs, rather than replacing its frozen
                # output hashes when an unrelated source-stat policy changes.
                current_catalog = tactical_fixture.controlled_catalog

                def original_stat_catalog():
                    catalog = current_catalog()
                    for ident, person in catalog.by_id.items():
                        previous = person['pre_campaign_stat_policy_v1']
                        person['profile'] = deepcopy(previous['profile'])
                        person.pop('initialization', None)
                        catalog.profiles[ident] = OfficerProfile(**person['profile'])
                    return catalog

                with patch.object(tactical_fixture, 'controlled_catalog', side_effect=original_stat_catalog):
                    game = active_duel(row['seed'])
                scene = self.perform(game, row['move'])
                state = game.to_dict()
                self.assertEqual(state['extension']['logistics']['schema'], 'tk2-logistics-v3')
                self.assertFalse(state['extension']['logistics']['convoys'])
                # Preserve the frozen pre-desperate artifact byte for byte;
                # project the unrelated empty cargo schema and initial treasury.
                state['extension'].pop('treasury')
                state['extension'].pop('facilities')
                state['extension']['logistics']['schema'] = 'tk2-logistics-v1'
                self.assertEqual(digest(state), row['state_sha256'])
                self.assertEqual(vars(game.state.rng), row['rng'])
                self.assertEqual(scene, row['presentation'])


def presentation_snapshot(game):
    """Read the same actual health/troops fields without opening a recorder."""
    b = game.state.battle
    return [dict(id=u['id'], side=side, troops=u['troops'], **{
        key: b['extended']['support'][str(u['id'])][key]
        for key in ('health', 'energy', 'guard', 'stunned')})
        for side in ('attackers', 'defenders') for u in b[side]]


if __name__ == '__main__':
    unittest.main()
