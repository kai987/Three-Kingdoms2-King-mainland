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
from remake.campaign import Campaign, Catalog, SeedRng, canonical, digest
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


def observe_controlled(game, output=None):
    """Install a declared fixture before observation; never a natural run."""
    spec = settings(game.catalog, faction=game.state.player, seed=game.state.seed)
    replay = checkpoints.CheckpointReplay(game.catalog, spec, 'python', output=output)
    saved = checkpoints.encoded(game.export_save())
    replay.game.load_save(saved, replay.game.revision)
    assert checkpoints.encoded(replay.game.export_save()) == saved
    return replay


def controlled_contacts():
    from browser_siege_fixture import fixture
    from remake import battle_grid
    row = fixture()
    game = Campaign(Catalog(ROOT/'game/data/campaigns/208-10.json'))
    game.load_save(row['save'], 0)
    battle = game.state.battle
    positions = battle['extended']['tactical']['positions']
    actor, fort = row['actor'], row['fort']
    enemy = next(u['id'] for u in battle['defenders'] if u['id'] != fort)
    field = battle_grid._field(battle)
    x, y = (positions[str(actor)][axis] for axis in ('x','y'))
    point = next((px,py) for px,py in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
        if 0 <= px < 31 and 0 <= py < 19 and field['classes'][py][px] != 5)
    old = deepcopy(positions[str(enemy)])
    blocker = next((key for key,p in positions.items()
        if key != str(enemy) and (p['x'],p['y']) == point), None)
    if blocker is not None:
        positions[blocker] = old
    positions[str(enemy)] = dict(x=point[0],y=point[1])
    game.validate(game.state)
    assert battle_grid.siege_context(battle, actor, enemy) is None
    assert battle_grid.siege_context(battle, actor, fort) is not None
    return game, actor, enemy, fort


def contact_cycle(replay, actor, target):
    ident = replay.game.state.battle['id']
    replay.command('attack', battle_id=ident, actor=actor, target=target)
    replay.command('siege_form', battle_id=ident, formation=0)
    replay.command('siege_orders', battle_id=ident,
                   orders={kind:'wait' for kind in ('infantry','archer','cavalry','general')})
    replay.command('siege_step', battle_id=ident)
    replay.command('siege_withdraw', battle_id=ident)


class NaturalCheckpointTests(unittest.TestCase):
    def test_fixed_strata_do_not_collapse_encounters_or_condition_kinds(self):
        extension = dict(conditions={'units':{'1':{'kind':'phantom','remaining':2},
            '2':{'kind':'chain','remaining':3},'3':{'kind':'qimen','remaining':1},
            '4':{'kind':'chain','remaining':0}}}, siege={'stage':'formation','mode':'field'})
        state = SimpleNamespace(phase='battle',battle={'extended':extension})
        state.battle['defenders'] = [dict(id=3,troops=0)]
        before = deepcopy(state)
        self.assertEqual(checkpoints.observed_strata(state),
            ('condition_phantom','condition_chain','condition_qimen','field_formation'))
        self.assertEqual(state, before)
        self.assertIn('condition_qimen',checkpoints.observed_strata(state),
                      'A retained positive Qimen ledger is evidence even with zero troops')
        self.assertEqual((len(checkpoints.STRATA),len(checkpoints.ENCOUNTERS)),(11,6))
        for mode, label in (('field','field'),('siege','fort')):
            for stage in checkpoints.STAGES:
                extension['siege'] = dict(mode=mode,stage=stage)
                self.assertIn(label+'_'+stage, checkpoints.observed_strata(state))
        extension['siege'].pop('mode')
        self.assertIn('fort_combat', checkpoints.observed_strata(state))
        extension['siege']['mode'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'encounter mode'):
            checkpoints.observed_strata(state)
        extension['siege'] = None
        extension['conditions']['units']['3']['kind'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'condition kind'):
            checkpoints.observed_strata(state)
        state.phase = 'result'
        self.assertEqual(checkpoints.observed_strata(state), ())

    def test_field_then_fort_keeps_legacy_first_witness_and_probes_each_real_snapshot_once(self):
        with using_backend('python'), tempfile.TemporaryDirectory() as folder:
            game, actor, enemy, fort = controlled_contacts()
            replay = observe_controlled(game, Path(folder))
            actual, calls = replay.game, []
            original = checkpoints.soak.HeadlessCampaign.command
            def counted(game, kind, *args, **kwargs):
                if game is not actual:
                    calls.append(kind)
                return original(game, kind, *args, **kwargs)
            with patch.object(checkpoints.soak.HeadlessCampaign, 'command', counted):
                contact_cycle(replay, actor, enemy)
                legacy = {key:deepcopy(replay.captures[key]) for key in checkpoints.KINDS if key in replay.captures}
                first_files = {row['file']:json.loads((Path(folder)/row['file']).read_text()) for row in legacy.values()}
                contact_cycle(replay, actor, fort)
            self.assertEqual({key:replay.captures[key] for key in legacy}, legacy)
            for filename, saved in first_files.items():
                self.assertEqual(json.loads((Path(folder)/filename).read_text()), saved)
            self.assertEqual(len(calls), 12, 'Six distinct committed states require two backend commands each, not one pair per alias')
            observed = replay.observation()
            self.assertEqual(observed['physical_saves'],dict(captured=6,verified=6,verified_backend_commands=12))
            self.assertEqual(len(list(Path(folder).glob('*.save.json'))),6)
            detail = observed['strata']
            self.assertEqual(detail['coverage']['encounters']['verified_count'],6)
            self.assertEqual(detail['coverage']['encounters']['verified_status'],'complete')
            self.assertEqual(detail['coverage']['verified_count'],6)
            self.assertEqual(detail['coverage']['verified_status'],'partial')
            for row in detail['checkpoints']:
                expected = 'field' if row['kind'].startswith('field_') else 'siege'
                self.assertEqual(row['encounter_mode'], expected)
                self.assertEqual(row['encounter_context']['mode'], expected)
                self.assertEqual(row['continuation']['status'], 'verified')
                self.assertEqual(len(row['continuation']['probes']),2)

    def test_new_fort_only_pending_witness_is_incomplete_after_legacy_stages_verified(self):
        game, actor, enemy, fort = controlled_contacts()
        def stop_at_new_fort(replay, turns):
            replay.game.load_save(game.export_save(), replay.game.revision)
            contact_cycle(replay, actor, enemy)
            replay.command('attack', battle_id=replay.game.state.battle['id'], actor=actor, target=fort)
            return {'backend':replay.backend}
        with patch.object(checkpoints.CheckpointReplay, 'run', stop_at_new_fort):
            row, _ = checkpoints.run_leg(game.catalog, settings(game.catalog,faction='wei'), 'python', observe=True)
        self.assertEqual((row['verification_status'],row['stop_reason']),('incomplete','pending_without_continuation'))
        obs = row['observation']
        self.assertEqual(obs['pending_without_continuation'],[])
        self.assertEqual(obs['strata']['pending_without_continuation'],['fort_formation'])
        self.assertEqual(obs['strata']['coverage']['observed_count'],4)
        self.assertEqual(obs['strata']['coverage']['verified_count'],3)

    def test_nonzero_strata_preserve_observer_off_and_both_main_backend_parity(self):
        game, actor, _, fort = controlled_contacts()
        def same_public_path(replay, turns):
            replay.game.load_save(game.export_save(),replay.game.revision)
            ident = replay.game.state.battle['id']
            replay.command('attack',battle_id=ident,actor=actor,target=fort)
            replay.command('siege_form',battle_id=ident,formation=0)
            replay.command('siege_withdraw',battle_id=ident)
            if replay.observe and replay.backend == 'rust':
                # Test diagnostic accounting normalization, never gameplay or
                # a natural sample. Warm native counters need not be equal.
                for capture in replay.captures.values():
                    for probe in capture['continuation'].get('probes',[]):
                        probe['native_calls'] += 7
            return dict(backend=replay.backend,command_sha256=replay.transcript.hexdigest())
        with tempfile.TemporaryDirectory() as folder, patch.object(checkpoints.CheckpointReplay,'run',same_public_path):
            report=checkpoints.run(game.catalog,settings(game.catalog,faction='wei'),folder)
        self.assertEqual(report['verification_status'],'passed')
        self.assertEqual(report['parity'],'passed')
        self.assertEqual(report['detailed_coverage']['denominator'],11)
        self.assertEqual(report['detailed_coverage']['verified_count'],2)
        self.assertTrue(all(leg['observer_did_not_change_policy']for leg in report['legs']))

    def test_legacy_fort_mode_metadata_is_normalized_without_mutating_the_save(self):
        with using_backend('python'):
            game, actor, _, fort = controlled_contacts()
            game.command('attack',dict(battle_id=game.state.battle['id'],actor=actor,target=fort),game.revision)
            game.state.battle['extended']['siege'].pop('mode')
            game.validate(game.state)
            replay = observe_controlled(game)
            replay.command('siege_form',battle_id=game.state.battle['id'],formation=0)
            row = replay.captures['fort_orders']
            self.assertEqual(row['encounter_mode_source'],'legacy_default')
            self.assertEqual(row['encounter_context']['mode'],'siege')
            self.assertNotIn('mode',replay.capture_saves['fort_orders']['state']['battle']['extended']['siege'])
            replay.command('siege_orders',battle_id=game.state.battle['id'],
                orders={kind:'wait' for kind in ('infantry','archer','cavalry','general')})
            self.assertEqual(replay.captures['fort_orders']['continuation']['status'],'verified')

    def test_phantom_then_chain_and_qimen_capture_separate_paid_public_states(self):
        from test_remake_chain_campaign import prepared, ZHU_GE, WAIT
        from remake import battle_grid
        with using_backend('python'):
            game, roles, _, _ = prepared()
            battle = game.state.battle
            points = battle['extended']['tactical']['positions']
            field = battle_grid._field(battle)
            source = points[str(ZHU_GE)]
            victim = roles['remote']
            occupied = {(p['x'],p['y']) for key,p in points.items() if key != str(victim)}
            candidates = [(x,y) for y in range(19) for x in range(31)
                if field['classes'][y][x] in (0,4) and (x,y) not in occupied
                and max(abs(x-source['x']),abs(y-source['y'])) <= 5]
            x,y = min(candidates,key=lambda p:(max(abs(p[0]-source['x']),abs(p[1]-source['y'])),p[1],p[0]))
            points[str(victim)] = dict(x=x,y=y)
            # One disclosed controlled initial seed; no gate, duration or RNG
            # result is replaced while any actual command/probe executes.
            game.state.seed=3; game.state.rng=SeedRng(3); game.validate(game.state)
            replay = observe_controlled(game)
            ident = battle['id']
            replay.command('tactic',battle_id=ident,actor=ZHU_GE,target=victim,tactic=2)
            with patch('remake.tactical_ai.choose_action',return_value=WAIT):
                replay.command('tactic',battle_id=ident,actor=ZHU_GE,target=roles['center'],tactic=10)
                self.assertEqual(replay.stratum_counts['condition_chain'],1, 'Three affected units count as one observed committed state')
                replay.command('battle_wait',battle_id=ident)
                replay.command('tactic',battle_id=ident,actor=ZHU_GE,target=victim,tactic=15)
                replay.command('battle_wait',battle_id=ident)
            self.assertEqual(replay.captures['active_conditions']['condition_kinds'],['phantom'])
            detail = replay.observation()['strata']
            self.assertEqual(detail['coverage']['conditions']['verified_count'],3)
            self.assertEqual(detail['coverage']['conditions']['denominator'],3)
            self.assertEqual(detail['coverage']['conditions']['verified_status'],'complete')
            self.assertEqual(detail['coverage']['verified_count'],3)
            self.assertEqual(detail['coverage']['denominator'],11)
            for kind in checkpoints.CONDITIONS:
                self.assertEqual(replay.captures['condition_'+kind]['continuation']['status'],'verified')

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
