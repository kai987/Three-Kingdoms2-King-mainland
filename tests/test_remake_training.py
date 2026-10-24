"""Training affects real attacks and preserves deployed/new-recruit weighting."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign
from remake import domestic, treasures
from remake.tactical_ai import expected_attack
from campaign_fixtures import controlled_catalog
from test_remake_tactical_ai import battle, actors


class TrainingDegreeTests(unittest.TestCase):
    def test_real_attack_training_levels_change_damage_without_extra_rng(self):
        losses, rngs, estimates = [], [], []
        for degree in (0, 70, 100):
            game = battle(three_enemies=False)
            b, actor, target, _, _ = actors(game)
            b['extended']['support'][str(actor['id'])]['morale'] = degree
            saved = game.export_save()
            estimates.append(expected_attack(b, actor, target,
                             game.catalog.data['rules']['battle_damage_percent']))
            self.assertEqual(game.export_save(), saved, 'AI evaluation cannot draw or alter training')
            before, draws = target['troops'], game.state.rng.draws
            # Isolate this one real player command from a separate AI response.
            with patch('remake.tactical_ai.choose_action', return_value=None):
                game.command('attack', dict(battle_id=b['id'], actor=actor['id'],
                                           target=target['id']), game.revision)
            current = next(u for u in game.state.battle['defenders'] if u['id'] == target['id'])
            losses.append(before - current['troops'])
            rngs.append(deepcopy(game.state.rng))
            self.assertEqual(game.state.rng.draws - draws, 1)
            game.validate(game.state)
        self.assertLess(losses[0], losses[1])
        self.assertLess(losses[1], losses[2])
        self.assertLess(estimates[0], estimates[1])
        self.assertLess(estimates[1], estimates[2])
        self.assertEqual(rngs, [rngs[0]] * 3, 'Training does not create extra random checks')

    def game(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        return game

    def test_departed_training_is_frozen_while_local_training_changes(self):
        game = self.game(); state = game.state
        source, target = state.cities['xiangyang'], state.cities['nanyang']
        row = state.extension['domestic']['cities'][source.id]
        row['morale'] = 95
        domestic.on_departure(game, state, [146], source.id)
        row['morale'] = 10
        self.assertEqual(domestic.unit_morale(game, state, 146), 95)
        game._start_expanded_battle(state, source, target, [146])
        self.assertEqual(state.battle['extended']['support']['146']['morale'], 95)
        self.assertEqual(row['morale'], 10)
        treasures.synchronize(game,state)
        game.validate(state)
        saved = game.export_save()
        loaded = Campaign(game.catalog); loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)

    def test_untrained_recruits_weight_existing_garrison_without_changing_identity(self):
        game = self.game(); state = game.state; city = state.cities['xiangyang']
        row = state.extension['domestic']['cities'][city.id]; row['morale'] = 100
        troops = city.reserves + sum(state.officers[i].troops for i in city.roster.officer_ids)
        ids, rng = list(city.roster.officer_ids), deepcopy(state.rng)
        domestic.add_reserves(game, state, city, 100, recruited=True)
        self.assertEqual(row['morale'], (troops * 100 + 100 * 50) // (troops + 100))
        self.assertLess(row['morale'], 100)
        self.assertEqual(city.roster.officer_ids, ids); self.assertEqual(state.rng, rng)
        game.validate(state)


if __name__ == '__main__':
    unittest.main()
