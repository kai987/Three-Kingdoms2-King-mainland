"""The soak harness must preserve transactions, saves and reference parity.

The multi-year real-catalog matrix is a separate CI job, not repeated by every
unittest discovery. These small controlled cases verify the harness itself.
"""
import importlib.util
from copy import deepcopy
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
    def test_pending_castle_encounter_uses_public_form_orders_steps_and_exact_restore(self):
        from test_remake_tactical_ai import battle
        from test_remake_battle_siege import castle_contact
        replay=soak.Replay(controlled_catalog(),'shu',2026,'python')
        replay.game=battle(three_enemies=False)
        b,actor,target,_=castle_contact(replay.game)
        replay.command('attack',battle_id=b['id'],actor=actor['id'],target=target['id'])
        replay.restore()
        replay.resolve()
        for kind in ('siege_form','siege_orders','siege_step'):
            self.assertGreater(replay.commands[kind],0)
        self.assertNotEqual(replay.game.state.phase,'battle')
        replay.restore()

    def early_legs(self):
        # These small values test coverage gates; real campaign execution and
        # physical/save/RNG parity have their own tests below and in release CI.
        def leg(name, faction, completed, succession):
            return dict(name=name, faction=faction, backends=['python', 'rust'], parity=True,
                result=dict(completed_turns=completed, requested_turns=72,
                    coverage=dict(crossed_year=True, player_successions=int(succession)),
                    succession=[dict(turn=34, previous=1, successor=2)] if succession else [],
                    final=dict(phase='finished' if completed < 72 else 'city',
                               outcome='defeat' if completed < 72 else None)))
        return [leg('huangjin_succession', 'yellow_turban', 35, True),
                leg('han_continuity', 'han', 72, False)]

    def test_early_terminal_rebellion_cannot_replace_the_complete_independent_han_leg(self):
        legs = self.early_legs()
        coverage = soak.require_early_coverage(legs, 72)
        self.assertEqual(coverage['continuity_completed_turns'], 72)
        self.assertEqual(coverage['rebellion_completed_turns'], 35)
        self.assertEqual(coverage['rebellion_player_successions'], 1)
        with self.assertRaisesRegex(AssertionError, 'both independent campaigns'):
            soak.require_early_coverage(legs[:1], 72)
        incomplete = deepcopy(legs)
        incomplete[1]['result']['completed_turns'] = 71
        with self.assertRaisesRegex(AssertionError, 'complete every requested turn'):
            soak.require_early_coverage(incomplete, 72)
        incomplete = deepcopy(legs)
        incomplete[0]['result']['final']['phase'] = 'city'
        with self.assertRaisesRegex(AssertionError, 'validated terminal result'):
            soak.require_early_coverage(incomplete, 72)
        incomplete = deepcopy(legs)
        incomplete[0]['result']['succession'] = []
        with self.assertRaisesRegex(AssertionError, 'real ruler succession'):
            soak.require_early_coverage(incomplete, 72)

    def test_early_either_leg_without_backend_parity_blocks_release(self):
        for index in range(2):
            legs = self.early_legs()
            legs[index]['parity'] = False
            with self.assertRaisesRegex(AssertionError, 'exact Python/Rust parity'):
                soak.require_early_coverage(legs, 72)

    def test_early_does_not_swallow_either_legs_soldier_conservation_failure(self):
        for index in range(2):
            first = self.early_legs()[0]
            first.pop('name')
            results = [first] if index else []
            with patch.object(soak, 'run_leg', side_effect=[*results, AssertionError('Soldier conservation failed')]):
                with self.assertRaisesRegex(AssertionError, 'Soldier conservation failed'):
                    soak.run_case('early', 3)

    def test_independent_leg_compares_full_rng_state_and_transcript_before_reporting_parity(self):
        catalog = controlled_catalog()
        with using_backend('python'):
            result = soak.Replay(catalog, 'shu', 3, 'python').run(1)
        for field in ('rng', 'command_sha256', 'final_save_sha256'):
            left, right = deepcopy(result), deepcopy(result)
            right['backend'] = 'rust'
            if field == 'rng':
                right['final']['rng']['draws'] += 1
            else:
                right[field] = 'altered'
            with patch.object(soak.Replay, 'run', side_effect=[left, right]):
                with self.assertRaisesRegex(AssertionError, 'state/save/RNG/transcript divergence'):
                    soak.run_leg(catalog, 'shu', 3, ('python', 'rust'), 1)

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
            self.assertTrue(all(0 <= replay.game.state.officers[i].troops <= 1000 for i in ids))

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
