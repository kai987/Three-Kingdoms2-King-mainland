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

    def test_full_plan_delegates_every_original_file_in_all_six_unfiltered_invocations(self):
        registry,_=shards.load_registry()
        full=plan(mode='full',full=True,native=True,groups=sorted(shards.GROUPS),python_groups=['all'])
        execution=scoped.execution_plan(full,registry,backend='both')
        self.assertEqual(execution['files'],sorted(registry['modules']))
        self.assertEqual(len(execution['full_invocations']),6)
        for backend in('python','rust'):
            calls=[r for r in execution['full_invocations']if r['backend']==backend]
            self.assertEqual([r['argv'][-3]for r in calls],['1','2','3'])
            self.assertTrue(all(r['argv'][-2:]==['--shards','3']for r in calls))
            self.assertTrue(all('--filter'not in r['argv']for r in calls))
        single=scoped.execution_plan(full,registry,backend='rust',shard=2,shards=3)
        self.assertEqual(len(single['full_invocations']),1)
        self.assertEqual(single['full_invocations'][0]['argv'][-4:],['--shard','2','--shards','3'])

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
