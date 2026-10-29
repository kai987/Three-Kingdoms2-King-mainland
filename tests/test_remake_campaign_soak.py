"""The soak harness must preserve transactions, saves and reference parity.

The multi-year real-catalog matrix is a separate CI job, not repeated by every
unittest discovery. These small controlled cases verify the harness itself.
"""
import importlib.util
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog

spec = importlib.util.spec_from_file_location('campaign_soak', ROOT / 'tools/campaign-soak/run.py')
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)
spec_ci = importlib.util.spec_from_file_location('campaign_soak_ci', ROOT / 'tools/campaign-soak/ci.py')
ci = importlib.util.module_from_spec(spec_ci)
spec_ci.loader.exec_module(ci)


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


class CampaignSoakCITests(unittest.TestCase):
    HEAD='a'*40
    RUN_ID=12345
    ATTEMPT=2

    @classmethod
    def setUpClass(cls):
        with using_backend('python'):
            cls.base=soak.Replay(controlled_catalog(),'shu',3,'python').run(1)

    def records(self):
        # Structural gate vectors reuse real result shapes. They do not claim
        # to be long campaigns; actual CI fragments always run the fixed CASES.
        def result(duration,terminal=False):
            row={k:deepcopy(v) for k,v in self.base.items() if k!='backend'}
            row.update(requested_turns=duration,completed_turns=35 if terminal else duration,
                       succession=[dict(turn=34,previous=1,successor=2)])
            row['coverage'].update(crossed_year=True,player_successions=1)
            row['final'].update(phase='finished' if terminal else 'city',outcome='defeat' if terminal else None)
            return row
        records=[]
        for case,seed,backend in ci.EXECUTIONS:
            duration=ci.soak.CASES[case]['turns'];sha=ci.catalog_sha(case)
            backends=['python','rust'] if backend=='both' else [backend]
            report=dict(case=case,scenario=ci.soak.CASES[case]['scenario'],seed=seed,
                        catalog_sha256=sha,backends=backends,parity=backend=='both')
            if case=='early':
                legs=[]
                for name,faction,terminal in [('huangjin_succession','yellow_turban',True),
                                              ('han_continuity','han',False)]:
                    value=result(duration,terminal)
                    legs.append(dict(name=name,faction=faction,backends=['python','rust'],parity=True,
                                     result=value,observations=ci.soak.observations(value)))
                report.update(legs=legs,coverage=ci.soak.require_early_coverage(legs,duration))
            else:
                value=result(duration)
                report.update(faction=ci.soak.CASES[case]['faction'],result=value,
                              observations=ci.soak.observations(value))
            records.append(dict(schema=ci.SCHEMA,head=self.HEAD,run_id=self.RUN_ID,run_attempt=self.ATTEMPT,
                policy=ci.POLICY,case=case,seed=seed,backend=backend,catalog_sha256=sha,
                requested_turns=duration,report=report,failure=None,elapsed_seconds=123.5))
        return records

    def merge(self,records,**changes):
        return ci.merge(records,**dict(dict(head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT,
                                            execution_result='success'),**changes))

    def test_middle_only_execution_matrix_and_mandatory_join_match_workflow(self):
        self.assertEqual(len(ci.EXECUTIONS),8)
        self.assertEqual(ci.soak.CASES['middle']['turns'],144)
        workflow=(ROOT/'.github/workflows/web-checks.yml').read_text()
        executor=workflow.split('  campaign-soak-replay:\n',1)[1].split('  campaign-soak:\n',1)[0]
        matrix=re.findall(r'- \{case: (\w+), seed: (\d+), backend: (\w+)\}',executor)
        self.assertEqual([(case,int(seed),backend) for case,seed,backend in matrix],list(ci.EXECUTIONS))
        self.assertIn('timeout-minutes: 20',executor)
        self.assertNotIn('--turns',executor)
        self.assertIn('ci.py fragment',executor)
        self.assertIn('${{ github.run_attempt }}',executor)
        join=workflow.split('  campaign-soak:\n',1)[1].split('  source-and-browser:\n',1)[0]
        self.assertIn('needs: [scope, campaign-soak-replay]',join)
        self.assertIn("if: always() && needs.scope.outputs.soak == 'true'",join)
        self.assertIn('EXECUTION_RESULT: ${{ needs.campaign-soak-replay.result }}',join)
        self.assertIn('campaign-soak-execution-*-${{ github.sha }}-attempt-${{ github.run_attempt }}',join)
        self.assertIn('merge-multiple: false',join)
        self.assertIn('ci.py merge',join)
        gate=workflow.split('  gate:\n',1)[1]
        self.assertIn('campaign-soak, web-build',gate)

    def test_complete_fragments_merge_without_mutation_and_only_then_gain_parity(self):
        records=self.records();before=deepcopy(records)
        self.assertFalse(next(r for r in records if r['backend']=='python')['report']['parity'])
        merged=self.merge(records)
        self.assertEqual((merged['execution_count'],len(merged['cases'])),(8,6))
        self.assertEqual({(row['case'],row['seed']) for row in merged['cases']},
                         {(case,seed) for case in ci.soak.CASES for seed in (3,2026)})
        self.assertTrue(all(row['parity'] and row['backends']==['python','rust'] for row in merged['cases']))
        self.assertEqual(records,before)

    def test_missing_duplicate_and_failed_executor_results_never_merge(self):
        records=self.records()
        for index in range(len(records)):
            with self.subTest(missing=index),self.assertRaises(ValueError):
                self.merge(records[:index]+records[index+1:])
            with self.subTest(duplicate=index),self.assertRaises(ValueError):
                self.merge(records+[records[index]])
        for outcome in ('failure','cancelled','timed_out','skipped',None,'in_progress'):
            with self.subTest(outcome=outcome),self.assertRaises(ValueError):
                self.merge(records,execution_result=outcome)

    def test_fragment_commit_attempt_catalog_policy_case_seed_and_backend_are_bound(self):
        edits=[lambda r:r.update(head='b'*40),lambda r:r.update(run_id=self.RUN_ID+1),
               lambda r:r.update(run_attempt=self.ATTEMPT-1),lambda r:r.update(policy='different'),
               lambda r:r.update(catalog_sha256='0'*64),lambda r:r.update(schema='different'),
               lambda r:r.update(case='unknown'),lambda r:r.update(seed=2025),
               lambda r:r.update(backend='both'),lambda r:r.update(requested_turns=143),
               lambda r:r.update(failure={'error':'failed'}),lambda r:r.update(run_id=True),
               lambda r:r['report'].update(parity=True),
               lambda r:r['report'].update(backends=['python','rust']),
               lambda r:r['report'].update(seed=2026),lambda r:r['report'].update(faction='shu')]
        for index,edit in enumerate(edits):
            records=self.records();record=next(r for r in records if r['case']=='middle' and r['backend']=='python')
            edit(record)
            with self.subTest(edit=index),self.assertRaises(ValueError):self.merge(records)

    def test_every_nested_state_rng_save_checkpoint_and_transcript_difference_blocks_parity(self):
        edits=[lambda r:r['final']['rng'].update(draws=r['final']['rng']['draws']+1),
               lambda r:r['final']['rng'].update(state=r['final']['rng']['state']^1),
               lambda r:r['initial']['resources'].update(gold=r['initial']['resources']['gold']+1),
               lambda r:r['samples'].append(deepcopy(r['final'])),
               lambda r:r['checkpoints'][0].update(checksum='0'*64),
               lambda r:r['commands'].update(end_turn=r['commands']['end_turn']+1),
               lambda r:r['commands'].update(new=True),
               lambda r:r['commands'].update(new=float(r['commands']['new'])),
               lambda r:r['transport_receipts'].update(transport_arrived=1),
               lambda r:r.update(command_sha256='0'*64),lambda r:r.update(final_save_sha256='0'*64)]
        for index,edit in enumerate(edits):
            records=self.records();record=next(r for r in records if r['case']=='middle' and r['backend']=='rust')
            edit(record['report']['result'])
            with self.subTest(edit=index),self.assertRaisesRegex(ValueError,'state/save/RNG/transcript divergence'):
                self.merge(records)

    def test_identical_but_incomplete_duration_or_missing_succession_cannot_pass(self):
        for edit in [lambda r:r.update(completed_turns=143),
                     lambda r:r['coverage'].update(crossed_year=False),lambda r:r.update(succession=[]),
                     lambda r:r.pop('command_sha256')]:
            records=self.records()
            for record in records:
                if record['case']=='middle':edit(record['report']['result'])
            with self.assertRaises(ValueError):self.merge(records)

    def test_even_matching_nested_nonfinite_values_are_rejected(self):
        for value in (float('nan'),float('inf'),float('-inf')):
            records=self.records()
            for record in records:
                if record['case']=='middle':
                    record['report']['result']['initial']['resources']['gold']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.merge(records)

    def test_fragment_runs_original_full_duration_entrypoint_and_preserves_failures(self):
        template=next(r for r in self.records() if r['case']=='middle' and r['seed']==3 and r['backend']=='python')
        with patch.object(ci.soak,'run_case',return_value=template['report']) as run:
            record=ci.fragment('middle',3,'python',head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT,progress=True)
        run.assert_called_once_with('middle',3,('python',),progress=True)
        self.assertFalse(record['report']['parity'])
        self.assertEqual(record['requested_turns'],144)
        ci.validate_execution(record,head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT)
        error=RuntimeError('real replay failure');error.soak_context={'save':{'rng':'untouched'}}
        with patch.object(ci.soak,'run_case',side_effect=error):
            failed=ci.fragment('middle',3,'rust',head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT)
        self.assertIsNone(failed['report'])
        self.assertEqual(failed['failure']['context'],error.soak_context)
        with self.assertRaises(ValueError):ci.validate_execution(failed,head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT)
        for case in ('early','late'):
            template=next(r for r in self.records() if r['case']==case and r['seed']==3)
            with patch.object(ci.soak,'run_case',return_value=template['report']) as run:
                ci.fragment(case,3,'both',head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT)
            run.assert_called_once_with(case,3,('python','rust'),progress=False)
            with self.assertRaises(ValueError):
                ci.fragment(case,3,'python',head=self.HEAD,run_id=self.RUN_ID,attempt=self.ATTEMPT)

    def test_merge_cli_reads_only_current_run_attempt_and_rejects_stale_or_unexpected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inputs=root/'inputs';inputs.mkdir();output=root/'result.json'
            for index,record in enumerate(self.records()):
                (inputs/f'{index}.json').write_text(json.dumps(record))
            args=['merge','--head',self.HEAD,'--run-id',str(self.RUN_ID),'--attempt',str(self.ATTEMPT),
                  '--input-dir',str(inputs),'--execution-result','success','--output',str(output)]
            with redirect_stdout(io.StringIO()):self.assertEqual(ci.main(args),0)
            self.assertEqual(json.loads(output.read_text())['execution_count'],8)
            duplicate=inputs/'duplicate-artifact';duplicate.mkdir()
            (duplicate/'0.json').write_bytes((inputs/'0.json').read_bytes())
            with redirect_stdout(io.StringIO()):self.assertEqual(ci.main(args),1)
            self.assertIn('Duplicate replay execution',json.loads(output.read_text())['error'])
            (duplicate/'0.json').unlink();duplicate.rmdir()
            record=json.loads((inputs/'0.json').read_text());record['run_attempt']-=1
            (inputs/'0.json').write_text(json.dumps(record))
            with redirect_stdout(io.StringIO()):self.assertEqual(ci.main(args),1)
            self.assertIn('mismatch',json.loads(output.read_text())['error'])
            (inputs/'unexpected.txt').write_text('not an execution')
            with redirect_stdout(io.StringIO()):self.assertEqual(ci.main(args),1)
            self.assertIn('Unexpected replay artifact file',json.loads(output.read_text())['error'])


if __name__ == '__main__':
    unittest.main()
