"""The soak harness must preserve transactions, saves and reference parity.

The multi-year real-catalog matrix is a separate CI job, not repeated by every
unittest discovery. These small controlled cases verify the harness itself.
"""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog

spec = importlib.util.spec_from_file_location('campaign_soak', ROOT / 'tools/campaign-soak/run.py')
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)


class CampaignSoakTests(unittest.TestCase):
    def test_no_battle_choice_fails_instead_of_forcing_a_retreat(self):
        with using_backend('python'):
            replay = soak.Replay(controlled_catalog(), 'shu', 3, 'python')
            ident = replay.game.state.cities['xiangyang'].roster.officer_ids[0]
            replay.command('depart', source='xiangyang', target='nanyang', officers=[ident], route_mode='land')
            replay.command('end_turn')
            replay.command('ai', turn=1)
            with patch.object(soak, 'choose_action', return_value=None), self.assertRaisesRegex(AssertionError, 'No legal battle action'):
                replay.resolve()
            self.assertEqual(replay.commands['retreat'], 0)
            self.assertEqual(replay.game.state.phase, 'battle')

    def test_cross_year_public_transactions_save_rng_and_backend_trace_match(self):
        catalog = controlled_catalog()
        results = []
        for backend in ('python', 'rust'):
            with using_backend(backend):
                replay = soak.Replay(catalog, 'shu', 2026, backend)
                results.append(replay.run(6))
        for result in results:
            self.assertEqual(result['completed_turns'], 6)
            self.assertEqual(result['final']['date'], [218, 1, 1])
            self.assertTrue(result['coverage']['crossed_year'])
            self.assertGreaterEqual(len(result['checkpoints']), 3)
            self.assertEqual(result['commands']['end_turn'], 6)
            self.assertEqual(result['commands']['ai'], 6)
        left, right = [{k: v for k, v in r.items() if k != 'backend'} for r in results]
        self.assertEqual(left, right, 'Every committed state hash, save and RNG must agree')

    def test_administration_uses_public_commands_and_conserves_resources(self):
        with using_backend('python'):
            replay = soak.Replay(controlled_catalog(), 'shu', 3, 'python')
            before = replay.game.export_save()
            replay.administer()
            self.assertEqual(replay.game.journal[-1]['kind'], 'set_domestic')
            self.assertEqual(replay.game.state.turn, 1)
            self.assertEqual(replay.game.state.rng.draws, before['state']['rng']['draws'])
            self.assertEqual(replay.game.state.soldiers, before['state']['soldiers'])
            city = replay.game.state.cities['xiangyang']
            initial = before['state']['cities']['xiangyang']
            ids = city.roster.officer_ids
            self.assertEqual(city.reserves+sum(replay.game.state.officers[i].troops for i in ids),
                initial['reserves']+sum(before['state']['officers'][str(i)]['troops'] for i in ids))
            self.assertTrue(all(0 <= replay.game.state.officers[i].troops <= 999 for i in ids))

    def test_faction_offices_choose_from_all_cities_in_the_real_184_opening(self):
        catalog = soak.Catalog(ROOT/'game/data/campaigns/184-02.json')
        with using_backend('python'):
            replay = soak.Replay(catalog,'yellow_turban',2026,'python')
            state = replay.game.state
            cities = [c for c in state.cities.values() if c.owner==state.player]
            present = [i for c in cities for i in c.roster.officer_ids
                       if soak.domestic._present(replay.game,state,c,i)]
            civil = min(present,key=lambda i:(-state.officers[i].profile.intellect,soak.ref_sort_key(i)))
            military = min((i for i in present if i!=civil),
                key=lambda i:(-state.officers[i].profile.martial_strength,soak.ref_sort_key(i)))
            self.assertNotIn(civil,cities[0].roster.officer_ids,
                             'This real opening exercises a capable official outside the first city')
            rng = (state.rng.state,state.rng.draws)
            replay.administer()
            post = soak.domestic.appointments(replay.game.state,state.player)
            self.assertEqual((post['civil'],post['military']),(civil,military))
            self.assertEqual((replay.game.state.rng.state,replay.game.state.rng.draws),rng)

    def test_observations_do_not_treat_legitimate_waiting_as_corruption(self):
        with using_backend('python'):
            replay = soak.Replay(controlled_catalog(), 'shu', 3, 'python')
            result = replay.run(1)
        result['final']['waiting_convoys'] = 1
        result['final']['oldest_convoy_turns'] = 40
        rows = soak.observations(result)
        self.assertIn('convoy_backlog', [r['kind'] for r in rows])
        self.assertFalse(any(r['kind'] == 'early_finish' for r in rows))


if __name__ == '__main__':
    unittest.main()
