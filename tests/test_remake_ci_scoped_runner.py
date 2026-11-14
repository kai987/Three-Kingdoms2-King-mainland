"""Closed Python scopes and a real selected-catalog three-turn acceptance run."""
from copy import deepcopy
from contextlib import contextmanager
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.ci import run_campaign_tests as shards
from tools.ci import run_scoped_tests as scoped


def plan(**updates):
    result=dict(mode='scoped',full=False,native=False,groups=['boot'],python_groups=['global'],scenario_ids=[])
    result.update(updates);return result

@contextmanager
def one_catalog(data):
    source=json.loads((ROOT/'game/config/campaigns/index.json').read_text())
    entry=next(row for row in source['scenarios']if row['id']=='mainland194-06')
    compiled=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
    summary=next(row for row in compiled['summary']if row['id']==entry['id'])
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);canonical=root/'game/config/campaigns';outputs=root/'game/data/campaigns'
        (canonical/'scenarios').mkdir(parents=True);outputs.mkdir(parents=True)
        (canonical/'index.json').write_text(json.dumps(dict(schema=source['schema'],default=entry['id'],scenarios=[entry])))
        (canonical/entry['file']).write_bytes((ROOT/'game/config/campaigns'/entry['file']).read_bytes())
        (outputs/'index.json').write_text(json.dumps(dict(schema=compiled['schema'],default=entry['id'],catalogs=['campaigns/194-06.json'],summary=[summary])))
        (outputs/'194-06.json').write_text(json.dumps(data))
        yield root


class ScopedRunnerTests(unittest.TestCase):
    def test_required_scoped_suites_reject_skips_and_empty_runs(self):
        class MissingDependency(unittest.TestCase):
            @unittest.skip('missing required fixture dependency')
            def test_must_run(self):pass
        result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(MissingDependency))
        self.assertTrue(result.wasSuccessful())
        with self.assertRaisesRegex(ValueError,'Required Python tests skipped'):scoped.validate_required_result(result,'python')
        empty=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite())
        with self.assertRaisesRegex(ValueError,'Required Python suite was empty'):scoped.validate_required_result(empty,'python')

    def test_registry_is_explicit_complete_and_unknown_modules_fail_closed(self):
        registry,_=shards.load_registry()
        expected={path.relative_to(ROOT).as_posix()for path in shards.discover_files()}
        self.assertEqual(set(registry['modules']),expected)
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);tests=root/'tests';tests.mkdir();(tests/'test_remake_future.py').write_text('raise AssertionError("must not import")\n')
            path=root/'registry.json';path.write_text(json.dumps(dict(schema='tk2-ci-python-groups-v1',modules={})))
            with self.assertRaisesRegex(ValueError,'unregistered=.*test_remake_future'):
                shards.load_registry(path,tests,root)
            path.write_text(json.dumps(dict(schema='tk2-ci-python-groups-v1',modules={'tests/test_remake_missing.py':dict(tier='global',groups=[])})))
            with self.assertRaisesRegex(ValueError,'missing=.*test_remake_missing'):
                shards.load_registry(path,tests,root)

    def test_ui_browser_groups_do_not_select_backend_replays(self):
        registry,_=shards.load_registry();identities,_=scoped.inventory()
        ui=plan(groups=sorted(shards.GROUPS),scenario_ids=sorted(identities))
        execution=scoped.execution_plan(ui,registry)
        self.assertEqual(execution['python_groups'],['global'])
        self.assertEqual(execution['scenario_ids'],[])
        self.assertFalse(execution['native_required'])
        for name in execution['files']:self.assertEqual(registry['modules'][name]['tier'],'global')
        self.assertNotIn('tests/test_remake_march_core.py',execution['files'])
        self.assertNotIn('tests/test_remake_march_save_compat.py',execution['files'])
        self.assertNotIn('tests/test_remake_ci_scoped_runner.py',execution['files'])

    def test_portrait_scope_runs_the_portrait_suite_with_global_contracts(self):
        registry, _ = shards.load_registry()
        value = plan(groups=['boot', 'cloud', 'portraits'], python_groups=['global', 'portraits'])
        execution = scoped.execution_plan(value, registry)
        global_modules = {name for name, row in registry['modules'].items() if row['tier'] == 'global'}
        self.assertEqual(set(execution['files']), global_modules | {'tests/test_remake_portraits.py'})
        self.assertEqual(execution['scenario_ids'], [])
        self.assertFalse(execution['native_required'])

    def test_selected_scenario_retains_save_hash_oracles_without_pure_vector_matrix(self):
        registry,_=shards.load_registry()
        selected=plan(native=True,groups=['boot','save','cloud','scenarios'],python_groups=['global','scenarios','compat'],scenario_ids=['mainland194-06'])
        execution=scoped.execution_plan(selected,registry,backend='both')
        self.assertIn('tests/test_remake_194_frontier_review.py',execution['files'])
        self.assertIn('tests/test_remake_march_save_compat.py',execution['files'])
        self.assertNotIn('tests/test_remake_march_core.py',execution['files'])
        self.assertNotIn('tests/test_remake_historical_scenarios.py',execution['files'])
        self.assertEqual(execution['scenario_ids'],['mainland194-06'])
        self.assertEqual(execution['backends'],['python','rust'])
        broken=deepcopy(selected);broken['native']=False
        with self.assertRaisesRegex(ValueError,'native artifact'):scoped.execution_plan(broken,registry)
        broken=deepcopy(selected);broken['scenario_ids']=['mainland999-01']
        with self.assertRaisesRegex(ValueError,'Unknown current scenario'):scoped.execution_plan(broken,registry)

    def test_july_225_scope_runs_its_roster_regressions(self):
        registry, _ = shards.load_registry()
        july_225 = plan(native=True, groups=['boot', 'cloud', 'scenarios'],
                        python_groups=['global', 'scenarios', 'compat'],
                        scenario_ids=['mainland225-07'])
        module = 'tests/test_remake_nanzhong_225_setup.py'
        relevant = scoped.execution_plan(july_225, registry)
        self.assertIn(module, relevant['files'])
        self.assertNotIn('tests/test_remake_historical_scenarios.py', relevant['files'])
        unrelated = scoped.execution_plan(dict(july_225, scenario_ids=['mainland227-02']), registry)
        self.assertNotIn(module, unrelated['files'])

    def test_full_plan_delegates_every_original_file_in_all_twelve_unfiltered_invocations(self):
        registry,_=shards.load_registry()
        full=plan(mode='full',full=True,native=True,groups=sorted(shards.GROUPS),python_groups=['all'])
        execution=scoped.execution_plan(full,registry,backend='both')
        self.assertEqual(execution['files'],sorted(registry['modules']))
        self.assertEqual(execution['shards'],6)
        self.assertEqual(len(execution['full_invocations']),12)
        for backend in('python','rust'):
            calls=[r for r in execution['full_invocations']if r['backend']==backend]
            self.assertEqual([r['argv'][-3]for r in calls],['1','2','3','4','5','6'])
            self.assertTrue(all(r['argv'][-2:]==['--shards','6']for r in calls))
            self.assertTrue(all('--filter'not in r['argv']for r in calls))
            selected=[]
            for call in calls:
                single=scoped.execution_plan(full,registry,backend=backend,shard=int(call['argv'][-3]),shards=6)
                self.assertEqual(len(single['full_invocations']),1)
                selected.extend(single['files'])
            self.assertEqual(sorted(selected),sorted(registry['modules']))
            self.assertEqual(len(selected),len(set(selected)))
        single=scoped.execution_plan(full,registry,backend='rust',shard=2,shards=6)
        self.assertEqual(len(single['full_invocations']),1)
        self.assertEqual(single['full_invocations'][0]['argv'][-4:],['--shard','2','--shards','6'])
        for count in(1,3,4,5,7):
            with self.assertRaisesRegex(ValueError,'exactly 6'):
                scoped.execution_plan(full,registry,backend='rust',shard=1,shards=count)

    def test_boot_list_only_cli_is_inventory_only_and_has_an_auditable_report(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'plan.json';report=Path(folder)/'report.json';path.write_text(json.dumps(plan()))
            result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/ci/run_scoped_tests.py'),'--plan',str(path),'--list-only','--report',str(report)],cwd=ROOT,text=True,capture_output=True,check=True)
            document=json.loads(result.stdout)
            self.assertEqual(document,json.loads(report.read_text()))
            self.assertEqual(document['status'],'planned');self.assertEqual(document['scenario_ids'],[])
            self.assertEqual(document['backends'],['python']);self.assertEqual(document['global_catalog_count'],29)
            self.assertNotIn('scenario_smoke',document)
            self.assertNotIn('scenarios',document['python_groups'])

    def test_scoped_matrix_partitions_every_selected_module_and_keeps_campaigns_in_catalog_lane(self):
        registry, _ = shards.load_registry()
        selected = plan(native=True, groups=['map', 'scenarios'],
                        python_groups=['global', 'scenarios', 'compat'],
                        scenario_ids=['mainland194-06', 'mainland225-07'])
        for scope in (plan(), selected):
            with self.subTest(scenarios=scope['scenario_ids']):
                original = scoped.execution_plan(scope, registry, backend='python')
                first, second, catalog = [scoped.execution_plan(scope, registry, backend='python', lane=lane)
                                          for lane in scoped.SCOPED_LANES]
                self.assertCountEqual(first['files'] + second['files'], original['files'])
                self.assertEqual(first['scenario_ids'], [])
                self.assertEqual(second['scenario_ids'], [])
                self.assertEqual(first['backends'], ['python'])
                self.assertEqual(second['backends'], ['python'])
                self.assertEqual(catalog['files'], [])
                self.assertEqual(catalog['backends'], [])
                self.assertEqual(catalog['scenario_ids'], original['scenario_ids'])
                self.assertGreater(first['estimated_ms'], 0)
                self.assertGreater(second['estimated_ms'], 0)

    def test_scoped_report_gate_rejects_missing_module_or_cross_backend_coverage(self):
        registry, registry_sha = shards.load_registry()
        selected = plan(head='a' * 40, native=True, groups=['scenarios'],
                        python_groups=['global', 'scenarios', 'compat'],
                        scenario_ids=['mainland225-07'])
        identities, _ = scoped.inventory()
        with tempfile.TemporaryDirectory() as folder:
            reports = Path(folder)
            paths = {}
            documents = {}
            for lane in scoped.SCOPED_LANES:
                report = scoped.execution_plan(selected, registry, backend='python', lane=lane)
                report.update(status='passed', registry_sha256=registry_sha)
                if lane == 'catalogs':
                    report['global_catalog_checks'] = dict(status='passed', catalog_count=len(identities),
                                                           catalogs=[dict(id=ident) for ident in identities])
                    report['selected_source_checks'] = dict(status='passed', scenario_ids=selected['scenario_ids'])
                    report['scenario_smoke'] = [dict(id='mainland225-07', backends=['python', 'rust'],
                                                    turns=3, cross_backend_save_checks=4)]
                else:
                    report['module_runs'] = [dict(backend='python', cases=1, errors=0, failures=0, skipped=0,
                                                  module_ms=dict.fromkeys(report['files'], 1))]
                directory = reports / f'scoped-report-{lane}-{selected["head"]}'
                directory.mkdir()
                paths[lane] = directory / 'scoped-report.json'
                documents[lane] = report
                paths[lane].write_text(json.dumps(report))

            scoped.verify_scoped_reports(selected, registry, registry_sha, reports, backend='python')
            bad_module = deepcopy(documents['modules-1'])
            del bad_module['module_runs'][0]['module_ms'][bad_module['files'][0]]
            paths['modules-1'].write_text(json.dumps(bad_module))
            with self.assertRaisesRegex(ValueError, 'Incomplete unittest execution'):
                scoped.verify_scoped_reports(selected, registry, registry_sha, reports, backend='python')
            paths['modules-1'].write_text(json.dumps(documents['modules-1']))

            bad_catalog = deepcopy(documents['catalogs'])
            bad_catalog['scenario_smoke'][0]['backends'] = ['python']
            paths['catalogs'].write_text(json.dumps(bad_catalog))
            with self.assertRaisesRegex(ValueError, 'Incomplete selected scenario coverage'):
                scoped.verify_scoped_reports(selected, registry, registry_sha, reports, backend='python')
            paths['catalogs'].unlink()
            paths['catalogs'].parent.rmdir()
            with self.assertRaisesRegex(ValueError, 'Missing or unexpected scoped CI reports'):
                scoped.verify_scoped_reports(selected, registry, registry_sha, reports, backend='python')

    def test_all_current_catalog_ids_and_references_are_cheaply_validated(self):
        result=scoped.global_catalog_checks()
        self.assertEqual(result['status'],'passed');self.assertEqual(result['catalog_count'],29)
        self.assertEqual(len({row['id']for row in result['catalogs']}),29)
        self.assertTrue(all(len(row['sha256'])==64 for row in result['catalogs']))

    def test_global_raw_checks_reject_unindexed_and_dangling_references(self):
        source=json.loads((ROOT/'game/config/campaigns/index.json').read_text())
        entry=next(row for row in source['scenarios']if row['id']=='mainland194-06')
        compiled=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        summary=next(row for row in compiled['summary']if row['id']==entry['id'])
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);canonical=root/'game/config/campaigns';outputs=root/'game/data/campaigns'
            (canonical/'scenarios').mkdir(parents=True);outputs.mkdir(parents=True)
            (canonical/'index.json').write_text(json.dumps(dict(schema=source['schema'],default=entry['id'],scenarios=[entry])))
            (canonical/entry['file']).write_bytes((ROOT/'game/config/campaigns'/entry['file']).read_bytes())
            (outputs/'index.json').write_text(json.dumps(dict(schema=compiled['schema'],default=entry['id'],catalogs=['campaigns/194-06.json'],summary=[summary])))
            data=json.loads((ROOT/'game/data/campaigns/194-06.json').read_text())
            data['initial_officers'][0]['person_id']='unknown-person'
            (outputs/'194-06.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'invalid initial officer reference'):scoped.global_catalog_checks(root)
            (outputs/'unindexed.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Unindexed/stale compiled'):scoped.global_catalog_checks(root)

    def test_global_counts_owned_rosters_and_keeps_free_officers_separate(self):
        original=json.loads((ROOT/'game/data/campaigns/194-06.json').read_text())
        too_many=deepcopy(original);city=too_many['initial_officers'][0]['city']
        too_many['initial_officers']=[dict(row,city=city)for row in too_many['initial_officers'][:100]]
        with one_catalog(too_many)as root:
            with self.assertRaisesRegex(ValueError,'initial city officer capacity exceeded'):scoped.global_catalog_checks(root)
        wrong_owner=deepcopy(original);person=wrong_owner['initial_officers'][0]['person_id']
        wrong_owner['era_assignments'][person]['faction']='unknown-faction'
        with one_catalog(wrong_owner)as root:
            with self.assertRaisesRegex(ValueError,'initial owned posting and city owner disagree'):scoped.global_catalog_checks(root)
        free=deepcopy(original);free['initial_free_officers']=free['initial_free_officers'][:100]
        for row in free['initial_free_officers']:
            row['city']=city;free['era_assignments'][row['person_id']]['city']=city
        with one_catalog(free)as root:self.assertEqual(scoped.global_catalog_checks(root)['catalog_count'],1)

    def test_real_194_current_source_opening_three_turns_and_cross_backend_saves(self):
        self.assertEqual(scoped.check_selected_sources(['mainland194-06'])['scenario_ids'],['mainland194-06'])
        result=scoped.scenario_smoke(['mainland194-06'],('python','rust'))
        self.assertEqual(len(result),1);row=result[0]
        self.assertEqual((row['id'],row['turns']),('mainland194-06',3))
        self.assertEqual(row['backends'],['python','rust']);self.assertEqual(row['cross_backend_save_checks'],4)
        self.assertGreater(row['commands']['new'],0);self.assertGreater(row['commands']['end_turn'],0)
        self.assertGreater(row['commands']['ai'],0);self.assertGreater(row['rng']['draws'],0)
        self.assertEqual(len(row['save_sha256']),64)


if __name__=='__main__':unittest.main()
