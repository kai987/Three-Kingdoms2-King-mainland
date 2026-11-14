"""Short benchmark-harness checks; daily observations do not run in unit CI."""
from copy import deepcopy
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from campaign_fixtures import controlled_catalog,confirm_default_placement
from remake.campaign import Campaign,digest
from remake.march_core import using_backend

spec = importlib.util.spec_from_file_location('campaign_balance', ROOT/'tools/campaign-balance/run.py')
balance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(balance)


def settings(policy='defensive', **overrides):
    result = dict(era='middle', scenario='217-07', faction='shu', seed=3, policy=policy,
                difficulty='normal', backend='python', turns=1,
                max_seconds=30, max_commands=2000)
    result.update(overrides)
    return result


class CampaignBalanceTests(unittest.TestCase):
    def test_short_player_policies_use_real_commands_and_reproduce_the_same_save(self):
        catalog = controlled_catalog()
        catalog_sha = digest(catalog.data)
        results = []
        with using_backend('python'):
            for _ in range(2):
                result = balance.BalanceReplay(catalog, settings()).run_bounded()
                self.assertEqual(result['completed_turns'], 1)
                self.assertEqual(result['outcome'], 'unresolved')
                self.assertEqual(result['stop_reason'], 'turn_limit')
                self.assertEqual(result['commands']['new'], 1)
                self.assertEqual(result['commands']['end_turn'], 1)
                self.assertIn('set_domestic', result['commands'])
                self.assertEqual(result['timeline'][0]['turn'], 1)
                self.assertEqual(result['timeline'][-1]['turn'], 2)
                results.append(result)
        for key in ('final_save_sha256', 'command_sha256', 'final_rng', 'timeline'):
            self.assertEqual(results[0][key], results[1][key], key)
        self.assertEqual(digest(catalog.data), catalog_sha)

    def test_offensive_policy_issues_a_paid_departure_without_injecting_troops(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings('offensive'))
            before = deepcopy(replay.game.state.soldiers)
            replay.administer()
            self.assertGreater(replay.commands['depart'], 0)
            self.assertEqual(replay.game.state.soldiers, before)
            self.assertEqual(replay.game.state.turn, 1)
            self.assertGreater(replay.game.state.extension['travel']['counter'], 0)
            self.assertTrue(all(row['owner'] == 'shu' for row in replay.game.state.extension['travel']['marches']))

    def test_offensive_policy_skips_allied_targets_and_still_attacks_neutral_cities(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings('offensive'))
            city = replay.game.state.cities['xiangyang']
            replay.command('diplomacy', action='alliance', target='wei', duration=12,
                           city=city.id, envoy=city.roster.officer_ids[-1])
            attack_option = balance.StrategicAI.attack_option
            with patch.object(balance.StrategicAI, 'attack_option', autospec=True,
                              side_effect=attack_option) as options:
                replay.attack()

            targets = [call.args[2] for call in options.call_args_list]
            self.assertEqual({target.owner for target in targets}, {'neutral'})
            self.assertEqual(replay.commands['depart'], 1)
            marches = replay.game.state.extension['travel']['marches']
            self.assertEqual([march['target'] for march in marches], ['nanjun'])

    def test_transport_policy_is_an_ordinary_office_policy_not_a_free_cargo_grant(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings('transport'))
            before = balance.soak.snapshot(replay.game)
            replay.administer()
            after = balance.soak.snapshot(replay.game)
            policy = replay.game.state.extension['domestic']['factions']['shu']['policy']
            self.assertEqual(policy['task_order'], ['transport', 'recruit', 'personnel'])
            for key in ('resources', 'soldiers', 'rng'):
                self.assertEqual(before[key], after[key])
            self.assertEqual(replay.commands['depart'], 0)

    def test_first_invasion_is_read_from_a_real_hostile_departure(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings())
            ident = replay.game.state.cities['xiangyang'].roster.officer_ids[0]
            replay.command('depart', source='xiangyang', target='nanyang',
                           officers=[ident], route_mode='land')
            self.assertEqual(replay.first_invasion, {'shu': 1})

    def test_front_staff_metrics_exclude_active_battle_units_and_are_read_only(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings())
            ids = list(replay.game.state.cities['xiangyang'].roster.officer_ids)
            replay.command('depart', source='xiangyang', target='nanyang',
                           officers=ids, route_mode='land')
            replay.command('end_turn')
            for _ in range(10):
                state = replay.game.state
                if state.phase == 'battle':
                    break
                if state.phase == 'ai':
                    replay.command('ai', turn=state.turn)
                elif state.phase == 'arrivals':
                    replay.command('arrivals')
                else:
                    self.fail('Expected an actual arriving battle, got '+state.phase)
            self.assertEqual(replay.game.state.phase, 'battle')
            # The metrics case observes a ready battle. Suppress only this
            # headless driver's response shortcut while real confirmations run.
            game=replay.game
            with patch.object(game,'view',side_effect=lambda:Campaign.view(game)):
                confirm_default_placement(game)
            before = replay.game.export_save()
            result = balance.metrics(replay.game)
            self.assertIn('xiangyang', result['factions']['shu']['short_fronts'])
            self.assertEqual(replay.game.export_save(), before)

    def test_inherited_balance_driver_confirms_actual_pending_arrival_before_combat(self):
        with using_backend('python'):
            replay=balance.BalanceReplay(controlled_catalog(),settings(max_seconds=60))
            replay.command('depart',source='xiangyang',target='nanyang',officers=[146],route_mode='land')
            replay.command('end_turn')
            for _ in range(10):
                state=replay.game.state
                if state.phase=='battle':break
                if state.phase=='ai':replay.command('ai',turn=state.turn)
                elif state.phase=='arrivals':replay.command('arrivals')
                else:self.fail('Expected an actual incoming deployment, got '+state.phase)
            self.assertEqual(replay.game.state.battle['extended']['placement']['confirmed'],0)
            replay.resolve()
            self.assertEqual(replay.commands['battle_place'],1)
            self.assertEqual(replay.game.state.phase,'city')
            replay.game.validate(replay.game.state)

    def test_cap_is_unresolved_and_never_reported_as_a_player_loss(self):
        with using_backend('python'):
            replay = balance.BalanceReplay(controlled_catalog(), settings())
            replay.spec['max_commands'] = replay.commands.total()
            result = replay.run_bounded()
        self.assertEqual(result['outcome'], 'unresolved')
        self.assertEqual(result['stop_reason'], 'commands')
        self.assertEqual(result['completed_turns'], 0)
        result['spec']['policy'] = 'defensive'
        group = balance.summarize([result])[0]
        self.assertEqual((group['wins'], group['losses'], group['unresolved']), (0, 0, 1))
        self.assertIsNone(group['resolved_only_win_rate'])

    def test_supervisor_returns_last_atomic_checkpoint_on_a_hard_timeout(self):
        observed = dict(spec=settings(), outcome='unresolved', stop_reason='in_progress',
                        completed_turns=2, timeline=[dict(turn=3)])
        def timeout(command, **options):
            checkpoint = Path(command[command.index('--checkpoint')+1])
            balance._write(checkpoint, observed)
            raise subprocess.TimeoutExpired(command, options['timeout'])
        with patch.object(balance.subprocess, 'run', side_effect=timeout):
            result = balance.execute(settings())
        self.assertEqual(result['stop_reason'], 'hard_wall_time')
        self.assertEqual(result['outcome'], 'unresolved')
        self.assertEqual(result['timeline'], observed['timeline'])

    def test_matrix_does_not_silently_truncate_or_duplicate_requested_cases(self):
        rows = balance.plan(['early', 'middle', 'late'], None, [3, 2026], balance.POLICIES,
                            turns=6, max_seconds=30, max_commands=1000,
                            difficulty='normal', backend='python')
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({digest(row) for row in rows}), 36)
        self.assertEqual({row['scenario'] for row in rows}, {'184-02', '217-07', '263-05'})
        self.assertEqual(balance.distribution([0, 20, 100]),
                         dict(total=120, minimum=0, median=20, maximum=100))
        with tempfile.TemporaryDirectory() as folder:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                balance.main(['--seeds', '3', '2026', '--max-runs', '18', '--output', str(Path(folder)/'no.json')])
            self.assertFalse((Path(folder)/'no.json').exists())

    def test_comparison_marks_wall_time_samples_as_incomparable(self):
        current = dict(spec=settings(), outcome='unresolved', stop_reason='turn_limit',
                       policy_version=balance.POLICY_VERSION,
                       catalog_sha256='catalog', completed_turns=1, final_save_sha256='current')
        prior = deepcopy(current)
        self.assertTrue(balance.comparison([current], dict(runs=[prior]))[0]['comparable'])
        prior['stop_reason'] = 'hard_wall_time'
        self.assertFalse(balance.comparison([current], dict(runs=[prior]))[0]['comparable'])
        prior['stop_reason'] = 'commands'
        self.assertFalse(balance.comparison([current], dict(runs=[prior]))[0]['comparable'])

    def test_bad_comparison_is_rejected_before_executing_any_campaign(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'bad.json', Path(folder)/'out.json'
            source.write_text(json.dumps(dict(schema='unsupported', runs=[])))
            with patch.object(balance, 'execute') as execute, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                balance.main(['--compare', str(source), '--output', str(output)])
            execute.assert_not_called()
            self.assertFalse(output.exists())

    def test_duplicate_comparison_keys_are_rejected_in_either_record_order(self):
        first = dict(spec=settings(), outcome='win', stop_reason='terminal',
                     policy_version=balance.POLICY_VERSION,
                     catalog_sha256='catalog', completed_turns=1, final_save_sha256='first')
        last = dict(deepcopy(first), outcome='loss', final_save_sha256='last')
        for records in ([first, last], [last, first]):
            with self.subTest(order=[row['outcome'] for row in records]):
                with self.assertRaisesRegex(ValueError, 'Duplicate comparison key'):
                    balance.comparison([first], dict(runs=records))
                with self.assertRaisesRegex(ValueError, 'Duplicate comparison key'):
                    balance.comparison(records, dict(runs=[first]))
                with tempfile.TemporaryDirectory() as folder:
                    source, output = Path(folder)/'duplicates.json', Path(folder)/'out.json'
                    source.write_text(json.dumps(dict(schema=balance.SCHEMA, runs=records)))
                    stderr = io.StringIO()
                    with patch.object(balance, 'execute') as execute, redirect_stderr(stderr), self.assertRaises(SystemExit):
                        balance.main(['--compare', str(source), '--output', str(output)])
                    execute.assert_not_called()
                    self.assertIn('Duplicate comparison key', stderr.getvalue())
                    self.assertFalse(output.exists())

        other_seed = deepcopy(last)
        other_seed['spec']['seed'] = 2026
        self.assertEqual(len(balance.comparison([first, other_seed], dict(runs=[first, other_seed]))), 2,
                         'Distinct seeds remain separate legitimate comparison cases')


if __name__ == '__main__':
    unittest.main()
