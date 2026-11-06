"""Bounded observer-harness checks, separate from real-catalog evidence.

Small controlled catalogs isolate harness failures. Only the separate CLI's
unchanged shipped-catalog replays count as natural campaign observations.
"""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from campaign_fixtures import controlled_catalog
from remake import battle_placement, march_core
from remake.campaign import canonical, digest
from remake.march_core import using_backend

spec = importlib.util.spec_from_file_location('natural_checkpoints', ROOT/'tools/campaign-checkpoints/run.py')
checkpoints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoints)


def settings(catalog=None, **changes):
    values = dict(faction='shu', seed=2026, turns=1, max_commands=200, max_seconds=30)
    values.update(changes)
    return checkpoints.settings(catalog or controlled_catalog(), **values)


def public_battle(replay):
    ids = replay.game.state.cities['xiangyang'].roster.officer_ids[:3]
    replay.command('depart', source='xiangyang', target='nanyang', officers=ids, route_mode='land')
    replay.command('end_turn')
    for _ in range(10):
        state = replay.game.state
        if state.phase == 'battle':
            return
        if state.phase == 'ai':
            replay.command('ai', turn=state.turn)
        elif state.phase == 'arrivals':
            replay.command('arrivals')
        else:
            raise AssertionError('Unexpected controlled fixture phase '+state.phase)
    raise AssertionError('Controlled public arrival did not reach battle')


def next_place(replay):
    state, battle = replay.game.state, replay.game.state.battle
    row = battle_placement.view(replay.game, state, battle)
    return dict(battle_id=battle['id'], actor=row['actor'],
                **battle['extended']['tactical']['positions'][str(row['actor'])])


class NaturalCheckpointTests(unittest.TestCase):
    def test_committed_kind_detection_is_separate_and_read_only(self):
        extension = dict(placement={'confirmed':1, 'order':['1','2']},
            conditions={'units':{'2':{'kind':'phantom', 'remaining':2}}},
            siege={'stage':'combat', 'mode':'field'}, duel={'actor':1,'target':2})
        state = SimpleNamespace(phase='battle', battle={'extended':extension})
        before = deepcopy(state)
        self.assertEqual(checkpoints.observed_kinds(state),
                         ('partial_placement','active_conditions','siege_combat','duel'))
        self.assertEqual(state, before)
        for confirmed in (0, 2, True):
            extension['placement']['confirmed'] = confirmed
            self.assertNotIn('partial_placement', checkpoints.observed_kinds(state))
        for stage in ('formation','orders','combat'):
            extension['siege']['stage'] = stage
            self.assertIn('siege_'+stage, checkpoints.observed_kinds(state))
        extension['conditions']['units'] = {}
        self.assertNotIn('active_conditions', checkpoints.observed_kinds(state))
        state.phase = 'result'
        self.assertEqual(checkpoints.observed_kinds(state), ())

    def test_output_refuses_nonempty_files_repository_and_symlink_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); repository = base/'repo'; repository.mkdir()
            outside = base/'safe'
            self.assertEqual(checkpoints.output_directory(outside, root=repository), outside.resolve())
            (outside/'prior-evidence.json').write_text('retained')
            for value in (None, outside, repository, repository/'new'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    checkpoints.output_directory(value, root=repository)
            self.assertEqual((outside/'prior-evidence.json').read_text(), 'retained')
            file = base/'file'; file.write_text('user file')
            with self.assertRaises(ValueError):
                checkpoints.output_directory(file, root=repository)
            alias = base/'link'; alias.symlink_to(repository, target_is_directory=True)
            with self.assertRaises(ValueError):
                checkpoints.output_directory(alias/'uncreated', root=repository)
            self.assertFalse((repository/'uncreated').exists())

    def test_strict_budgets_faction_and_closed_index_names(self):
        catalog = controlled_catalog()
        for changes in ({'seed':True}, {'seed':0}, {'seed':0x100000000}, {'turns':True},
                {'turns':0}, {'turns':361}, {'max_commands':0}, {'max_commands':True},
                {'max_seconds':True}, {'max_seconds':float('nan')}, {'max_seconds':4},
                {'faction':'absent'}, {'faction':[]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                settings(catalog, **changes)
        for name in ('../209-06', 'index', 'mainland209-06', '/tmp/209-06', 'missing', True):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checkpoints.indexed_catalog(name)
        real = checkpoints.indexed_catalog('209-06')
        self.assertEqual(real.data['id'], 'mainland209-06')

    def test_zero_natural_hits_remain_zero_and_observer_keeps_original_policy(self):
        catalog = controlled_catalog(); before = digest(catalog.data)
        with tempfile.TemporaryDirectory() as folder:
            report = checkpoints.run(catalog, settings(catalog), folder, backends=('python',))
        self.assertEqual(report['verification_status'], 'passed')
        self.assertEqual(report['parity'], 'single_backend_only')
        self.assertEqual(report['coverage_status'], 'unobserved')
        row = report['legs'][0]
        self.assertTrue(row['observer_did_not_change_policy'])
        self.assertEqual(row['observed']['result'], row['baseline']['result'])
        self.assertEqual(row['observed']['campaign_outcome'], 'unresolved')
        self.assertEqual(row['observed']['stop_reason'], 'turn_limit')
        self.assertEqual(row['observed']['observation']['observation_counts'], dict.fromkeys(checkpoints.KINDS,0))
        self.assertEqual(row['observed']['observation']['checkpoints'], [])
        self.assertEqual(digest(catalog.data), before)

    def test_real_partial_save_next_public_command_matches_full_clone_state(self):
        catalog = controlled_catalog()
        with using_backend('python'), tempfile.TemporaryDirectory() as folder:
            replay = checkpoints.CheckpointReplay(catalog, settings(catalog), 'python', output=Path(folder))
            public_battle(replay)
            replay.command('battle_place', **next_place(replay))
            first = deepcopy(replay.captures['partial_placement'])
            saved = json.loads((Path(folder)/first['file']).read_text())
            self.assertEqual(first['placement'], {'confirmed':1,'count':3})
            self.assertEqual(first['continuation']['status'], 'pending_without_continuation')
            self.assertEqual(saved, checkpoints.encoded(replay.game.export_save()))
            before_rng = deepcopy(replay.game.state.rng)
            replay.command('battle_place', **next_place(replay))
            row = replay.captures['partial_placement']
            self.assertEqual(row['continuation']['status'], 'verified')
            self.assertEqual(row['continuation']['before_checksum'], first['checksum'])
            self.assertEqual(row['continuation']['after_checksum'], replay.game.export_save()['checksum'])
            self.assertEqual(row['continuation']['command'], 'battle_place')
            self.assertEqual(row['continuation']['probes'][0]['rng'],
                             dict(state=before_rng.state, draws=before_rng.draws))
            self.assertEqual(replay.game.state.rng, before_rng)
            self.assertEqual(len(replay.captures), 1, 'Later partial positions do not replace the first witness')
            self.assertEqual(replay.observation_counts['partial_placement'], 2)
            self.assertEqual(replay.pending, [])
            self.assertEqual(json.loads((Path(folder)/first['file']).read_text()), saved)

    def test_probe_contexts_restore_main_backend_without_requiring_formation_native_calls(self):
        # Both backend contexts are real and explicit. Formation-only command
        # continuation is pure gameplay logic, so zero native calls is valid.
        with using_backend('python'):
            replay = checkpoints.CheckpointReplay(controlled_catalog(), settings(), 'python')
            public_battle(replay); replay.command('battle_place', **next_place(replay))
            replay.command('battle_place', **next_place(replay))
            probes = replay.captures['partial_placement']['continuation']['probes']
            self.assertEqual([row['backend'] for row in probes], ['python','rust'])
            self.assertTrue(all(row['complete_save_equal'] and row['native_calls'] >= 0 for row in probes))
            self.assertEqual(march_core._mode(), 'python')

    def test_preceding_checkpoint_mismatch_rejects_before_another_actual_command(self):
        with using_backend('python'):
            replay = checkpoints.CheckpointReplay(controlled_catalog(), settings(), 'python')
            public_battle(replay); replay.command('battle_place', **next_place(replay))
            # Explicitly bypass the observer once to simulate a broken caller.
            # This is still a real public transaction on this controlled game.
            checkpoints.soak.Replay.command(replay, 'battle_place', **next_place(replay))
            before = replay.game.export_save(); count = sum(replay.commands.values())
            with self.assertRaisesRegex(AssertionError, 'immediately preceding'):
                replay.command('battle_place', **next_place(replay))
            self.assertEqual(replay.game.export_save(), before)
            self.assertEqual(sum(replay.commands.values()), count)

    def test_probe_rejects_actual_rng_mutation_and_restores_context_on_error(self):
        with using_backend('python'):
            replay = checkpoints.CheckpointReplay(controlled_catalog(), settings(), 'python')
            public_battle(replay); replay.command('battle_place', **next_place(replay))
            actual = replay.game
            original = checkpoints.soak.HeadlessCampaign.command
            def corrupt_clone(game, *args, **kwargs):
                result = original(game, *args, **kwargs)
                if game is not actual:
                    actual.state.rng.next()  # Deliberate harness-fault injection, never a natural run.
                return result
            with patch.object(checkpoints.soak.HeadlessCampaign, 'command', corrupt_clone):
                with self.assertRaisesRegex(AssertionError, 'mutated the actual game'):
                    replay.command('battle_place', **next_place(replay))
            self.assertEqual(march_core._mode(), 'python')
            self.assertEqual(replay.captures['partial_placement']['continuation']['status'], 'pending_without_continuation')

    def test_command_limit_is_incomplete_not_a_campaign_loss_or_pass(self):
        catalog = controlled_catalog()
        with tempfile.TemporaryDirectory() as folder:
            report = checkpoints.run(catalog, settings(catalog,max_commands=1), folder, backends=('python',))
            persisted = json.loads((Path(folder)/'report.json').read_text())
        self.assertEqual(report, persisted)
        self.assertEqual(report['verification_status'], 'incomplete')
        row = report['legs'][0]['observed']
        self.assertEqual(row['stop_reason'], 'command_limit')
        self.assertEqual(row['campaign_outcome'], 'unresolved')
        self.assertEqual(row['completed_turns'], 0)
        self.assertEqual(row['commands'], {'new':1})
        self.assertIsNone(report['legs'][0]['baseline'])

    def test_execution_budget_and_pending_continuation_never_count_as_verified(self):
        catalog = controlled_catalog()
        with patch.object(checkpoints.CheckpointReplay, 'run', side_effect=AssertionError('Phase resolution exceeded 4000 ordinary commands')):
            row, _ = checkpoints.run_leg(catalog, settings(catalog), 'python', observe=True)
        self.assertEqual((row['verification_status'], row['stop_reason']), ('incomplete','execution_budget'))
        def stop_after_first(replay, turns):
            public_battle(replay); replay.command('battle_place', **next_place(replay))
            return {'backend':replay.backend}
        with patch.object(checkpoints.CheckpointReplay, 'run', stop_after_first):
            row, _ = checkpoints.run_leg(catalog, settings(catalog), 'python', observe=True)
        self.assertEqual((row['verification_status'], row['stop_reason']), ('incomplete','pending_without_continuation'))
        self.assertEqual(row['observation']['pending_without_continuation'], ['partial_placement'])

    def test_expired_wall_budget_does_not_issue_another_public_command(self):
        now = [0.0]
        with using_backend('python'):
            replay = checkpoints.CheckpointReplay(controlled_catalog(), settings(), 'python', clock=lambda:now[0])
            before = replay.game.export_save()
            now[0] = 30
            with self.assertRaisesRegex(checkpoints.VerificationLimit, 'wall_time'):
                replay.command('end_turn')
            self.assertEqual(replay.game.export_save(), before)

    def test_baseline_result_difference_blocks_a_false_observer_equivalence_claim(self):
        original = checkpoints.CheckpointReplay.run
        def changed_result(replay, turns):
            result = original(replay, turns)
            if replay.observe:
                result['command_sha256'] = 'not-the-original-transcript'
            return result
        with tempfile.TemporaryDirectory() as folder, patch.object(checkpoints.CheckpointReplay, 'run', changed_result):
            report = checkpoints.run(controlled_catalog(), settings(), folder, backends=('python',))
        self.assertEqual(report['verification_status'], 'failed')
        self.assertFalse(report['legs'][0]['observer_did_not_change_policy'])
        self.assertEqual(report['parity'], 'unverified')

    def test_wall_budget_crossed_on_the_final_command_is_still_incomplete(self):
        original = checkpoints.CheckpointReplay.run
        def expired_after_run(replay, turns):
            result = original(replay, turns)
            replay.started -= replay.spec['max_seconds']
            return result
        with patch.object(checkpoints.CheckpointReplay, 'run', expired_after_run):
            row, _ = checkpoints.run_leg(controlled_catalog(), settings(), 'python', observe=True)
        self.assertEqual((row['verification_status'], row['stop_reason']), ('incomplete','wall_time'))
        self.assertEqual(row['campaign_outcome'], 'unresolved')

    def test_cli_incomplete_returns_nonzero_and_traversal_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'uncreated'
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                checkpoints.main(['--scenario','../index','--output-dir',str(output)])
            self.assertFalse(output.exists())
            printed = io.StringIO()
            with patch.object(checkpoints, 'indexed_catalog', return_value=controlled_catalog()), \
                    redirect_stderr(io.StringIO()), redirect_stdout(printed):
                code = checkpoints.main(['--faction','shu','--max-commands','1',
                                         '--backends','python','--output-dir',str(output)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(printed.getvalue())['verification_status'], 'incomplete')
            self.assertEqual(json.loads((output/'report.json').read_text())['verification_status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
