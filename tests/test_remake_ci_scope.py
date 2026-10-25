"""Fail-closed CI planning and deployed (not merely green) release baselines."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


PLAN = module('tk2_scope_plan', ROOT / 'tools/ci/plan.py')
PUBLISHED = module('tk2_published_base', ROOT / 'tools/ci/published_base.py')


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'ci@example.invalid')
        self.git('config', 'user.name', 'CI fixture')
        entries = [dict(id='mainland' + date, year=int(date[:3]), month=int(date[4:6]),
                        file='scenarios/' + date + '.json') for date in ('184-02', '194-06', '217-07')]
        self.write(PLAN.INDEX, dict(schema='tk2-campaign-sources-v1', default='mainland184-02', scenarios=entries))
        for row in entries:
            self.write('game/config/campaigns/' + row['file'], dict(
                schema='tk2-campaign-override-v1', id=row['id'], overrides={'set': {'title': row['id']}}))
            self.write('game/data/campaigns/' + Path(row['file']).name, dict(
                id=row['id'], title=row['id'], initial_owners={'city': 'wei'},
                travel_rules={'geometry_sha256': '0' * 64}))
        self.write('game/data/campaigns/index.json', dict(schema='tk2-campaign-index-v1',
            default='mainland184-02', catalogs=['campaigns/' + Path(row['file']).name for row in entries], summary=[]))
        self.write('game/config/route-geometry.json', dict(schema='fixture-route', routes=[1],
            sources={name: self.sha(name) for name in self.source_paths()}))
        self.write('README.md', 'Documentation\n')
        self.base = self.save('Published baseline')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.path), *args], stderr=subprocess.DEVNULL).decode().strip()

    def write(self, name, value):
        path = self.path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + '\n' if isinstance(value, (dict, list)) else value)

    def read(self, name):
        return json.loads((self.path / name).read_text())

    def sha(self, name):
        return hashlib.sha256((self.path / name).read_bytes()).hexdigest()

    def source_paths(self):
        return ['game/config/campaigns/' + row['file'] for row in self.read(PLAN.INDEX)['scenarios']]

    def save(self, message='Changes'):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def plan(self, head=None, **kwargs):
        return PLAN.make_plan(self.path, self.base, head or self.git('rev-parse', 'HEAD'), **kwargs)


class ScopePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tk2-ci-scope-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Repository(self.temp.name)

    def changed(self, path, value='changed\n'):
        self.repo.write(path, value)
        return self.repo.save()

    def test_docs_allowlist_is_nonvacuous_and_excludes_audit_json(self):
        self.changed('README.zh-TW.md', '說明\n')
        self.changed('docs/nested/design.md', 'Plan\n')
        result = self.repo.plan(event_name='push', ref='refs/heads/main')
        self.assertEqual(result['mode'], 'docs')
        self.assertEqual(result['groups'], [])
        self.assertEqual(result['python_groups'], [])
        self.assertFalse(any(result[field] for field in ('web', 'native', 'rules', 'soak', 'resupply', 'publish')))
        self.changed('docs/unknown-audit.json', {})
        self.assertTrue(self.repo.plan()['full'])

    def test_cover_audio_and_all_icon_sizes_have_small_scopes(self):
        for path in ('game/loading-cover.js', 'game/loading-cover.css',
                     'game/assets/loading/cover.png', 'game/assets/site-icon-32.png',
                     'game/favicon.svg', 'game/audio.js', 'game/assets/audio/title.ogg',
                     'tests/test_remake_loading_cover.cjs'):
            self.repo.write(path, 'asset\n')
        self.repo.save()
        result = self.repo.plan()
        self.assertEqual(result['mode'], 'scoped')
        self.assertEqual(result['groups'], ['boot', 'audio', 'cloud'])
        self.assertFalse(any(result[field] for field in ('native', 'rules', 'soak', 'resupply')))
        self.assertEqual(result['python_groups'], ['global'])

    def test_real_cover_plan_selects_four_browser_cases_and_eight_viewports(self):
        for path in ('game/loading-cover.js', 'game/loading-cover.css', 'game/audio.js'):
            self.repo.write(path, 'cover change\n')
        self.repo.save()
        plan = self.repo.plan()
        target = self.repo.path / 'cover-plan.json'
        target.write_text(json.dumps(plan))
        output = subprocess.check_output(['node', str(ROOT / 'tools/browser-tests/scope.cjs'),
                                          '--plan', str(target)], cwd=ROOT, text=True)
        selection = json.loads(output)
        self.assertEqual(selection['groups'], ['boot', 'audio', 'cloud'])
        self.assertEqual({row['id'] for row in selection['cases']},
                         {'title-cover', 'recovery-title', 'dialogs-save', 'boot-retry'})
        self.assertEqual(len(selection['cases']) * 2, 8)

    def test_scenario_source_and_generated_fingerprints_do_not_widen_gameplay_scope(self):
        path = 'game/config/campaigns/scenarios/194-06.json'
        source = self.repo.read(path)
        source['overrides']['set']['title'] = 'Reviewed194'
        self.repo.write(path, source)
        geometry = self.repo.read('game/config/route-geometry.json')
        geometry['sources'][path] = self.repo.sha(path)
        self.repo.write('game/config/route-geometry.json', geometry)
        for date in ('184-02', '194-06', '217-07'):
            path = 'game/data/campaigns/' + date + '.json'
            data = self.repo.read(path)
            data['travel_rules']['geometry_sha256'] = '1' * 64
            if date == '194-06':
                data['title'] = 'Reviewed194'
            self.repo.write(path, data)
        self.repo.save()
        result = self.repo.plan()
        self.assertFalse(result['full'], result['reasons'])
        self.assertEqual(result['scenario_ids'], ['mainland194-06'])
        self.assertTrue(result['native'])
        self.assertFalse(result['rules'])
        self.assertFalse(result['soak'])
        self.assertIn('scenarios', result['groups'])
        self.assertEqual(result['python_groups'], ['global', 'scenarios', 'compat'])

    def test_unexplained_generated_gameplay_or_route_changes_fail_closed(self):
        path = 'game/data/campaigns/194-06.json'
        data = self.repo.read(path)
        data['initial_owners']['city'] = 'lubu'
        self.changed(path, data)
        self.assertTrue(self.repo.plan()['full'])

    def test_actual_route_changes_require_the_complete_matrix(self):
        geometry = self.repo.read('game/config/route-geometry.json')
        geometry['routes'] = [2]
        self.changed('game/config/route-geometry.json', geometry)
        result = self.repo.plan()
        self.assertTrue(all(result[key] for key in ('full', 'native', 'rules', 'soak', 'resupply')))

    def test_scenario_filename_does_not_hide_shared_rule_overrides(self):
        path = 'game/config/campaigns/scenarios/194-06.json'
        source = self.repo.read(path)
        source['overrides']['update'] = {'travel_rules': {'set': {'speed': 999}}}
        self.changed(path, source)
        result = self.repo.plan()
        self.assertTrue(result['full'])
        self.assertTrue(result['rules'])

    def test_route_fingerprint_optimization_requires_exact_changed_source_bytes(self):
        path = 'game/config/campaigns/scenarios/194-06.json'
        source = self.repo.read(path)
        source['overrides']['set']['title'] = 'New title'
        self.repo.write(path, source)
        geometry = self.repo.read('game/config/route-geometry.json')
        geometry['sources'][path] = 'f' * 64
        self.changed('game/config/route-geometry.json', geometry)
        self.assertTrue(self.repo.plan()['full'])

    def test_route_fingerprint_optimization_cannot_remove_source_coverage(self):
        path = 'game/config/campaigns/scenarios/194-06.json'
        source = self.repo.read(path)
        source['overrides']['set']['title'] = 'New title'
        self.repo.write(path, source)
        geometry = self.repo.read('game/config/route-geometry.json')
        del geometry['sources'][path]
        self.changed('game/config/route-geometry.json', geometry)
        self.assertTrue(self.repo.plan()['full'])

    def test_malformed_derived_json_objects_fail_closed_with_a_valid_plan(self):
        self.changed('game/data/campaigns/index.json', [])
        result = self.repo.plan()
        self.assertEqual(result['schema'], 'tk2-test-plan-v1')
        self.assertTrue(result['full'])
        self.assertEqual(result['scenario_ids'], [])
        self.assertEqual(result['python_groups'], ['all'])

    def test_history_decision_rows_select_their_ids_without_replaying_all_rules(self):
        path = 'game/config/references/scenario-history-review.json'
        ledger = dict(schema='tk2-scenario-history-review-v1', revision='old',
                      fictional_excluded=[], scenarios=[dict(id='mainland194-06', notes=[])])
        self.repo.write(path, ledger)
        self.repo.base = self.repo.save('Published historical ledger')
        ledger['scenarios'][0]['notes'] = ['Reviewed']
        self.changed(path, ledger)
        result = self.repo.plan()
        self.assertFalse(result['full'])
        self.assertEqual(result['scenario_ids'], ['mainland194-06'])
        self.assertFalse(result['rules'])
        ledger['scenarios'][0]['id'] = 'unindexed'
        self.changed(path, ledger)
        self.assertTrue(self.repo.plan()['full'])

    def test_shared_unknown_and_selector_changes_always_select_full(self):
        for path in ('game/config/campaigns/people.json', 'game/config/campaigns/shared.json',
                     'source/remake/campaign.py', 'crates/march-core/src/lib.rs',
                     'tools/ci/plan.py', '.github/workflows/remake.yml', 'unexpected.txt'):
            self.repo.write(path, 'shared\n')
        self.repo.save()
        result = self.repo.plan()
        self.assertEqual(result['groups'], list(PLAN.GROUPS))
        self.assertTrue(all(result[field] for field in ('full', 'web', 'native', 'rules', 'soak', 'resupply')))
        self.assertEqual(result['scenario_ids'], [])

    def test_global_ui_has_all_browser_groups_without_full_rule_matrix(self):
        self.changed('game/app.js')
        result = self.repo.plan()
        self.assertEqual(result['groups'], list(PLAN.GROUPS))
        self.assertFalse(any(result[field] for field in ('full', 'native', 'rules', 'soak')))
        self.assertEqual(result['scenario_ids'], ['mainland184-02', 'mainland194-06', 'mainland217-07'])
        self.assertTrue(result['resupply'])
        self.assertEqual(result['python_groups'], ['global'])

    def test_logistics_ui_selects_resupply_without_native_rule_replay(self):
        self.changed('game/domestic.js')
        result = self.repo.plan()
        self.assertIn('logistics', result['groups'])
        self.assertTrue(result['resupply'])
        self.assertFalse(result['native'])

    def test_accumulated_undeployed_changes_use_deployed_base_not_push_before(self):
        first = self.changed('game/audio.js')
        head = self.changed('game/domestic.js')
        event = dict(ref='refs/heads/main', before=first)
        result = self.repo.plan(head, event_name='push', event=event)
        self.assertEqual(result['base'], self.repo.base)
        self.assertIn('audio', result['groups'])
        self.assertIn('logistics', result['groups'])
        self.assertTrue(result['publish'])

    def test_added_renamed_and_deleted_ids_keep_provenance_but_run_full_current_set(self):
        index = self.repo.read(PLAN.INDEX)
        old = index['scenarios'][1]
        (self.repo.path / 'game/config/campaigns' / old['file']).unlink()
        index['scenarios'][1] = dict(id='mainland195-06', year=195, month=6, file='scenarios/195-06.json')
        self.repo.write(PLAN.INDEX, index)
        self.repo.write('game/config/campaigns/scenarios/195-06.json', dict(
            schema='tk2-campaign-override-v1', id='mainland195-06', overrides={}))
        self.repo.save()
        result = self.repo.plan()
        self.assertTrue(result['full'])
        self.assertEqual(result['scenario_ids'], [])
        self.assertEqual(result['removed_scenario_ids'], ['mainland194-06'])
        self.assertTrue({'mainland194-06', 'mainland195-06'} <= set(result['affected_scenario_ids']))
        # A new unindexed file must not be silently treated as an unrelated JSON.
        self.changed('game/config/campaigns/scenarios/205-01.json', dict(id='mainland205-01'))
        self.assertTrue(self.repo.plan()['full'])

    def test_deleted_scenario_without_index_update_and_invalid_index_fail_closed(self):
        (self.repo.path / 'game/config/campaigns/scenarios/194-06.json').unlink()
        self.repo.save()
        self.assertTrue(self.repo.plan()['full'])
        self.changed(PLAN.INDEX, dict(schema='unknown', scenarios=[]))
        self.assertTrue(self.repo.plan()['full'])

    def test_missing_invalid_nonancestor_and_empty_baselines_never_use_head_parent(self):
        head = self.changed('game/audio.js')
        for base in (None, '0' * 40, head):
            result = PLAN.make_plan(self.repo.path, base, head)
            self.assertTrue(result['full'], (base, result))
            self.assertFalse(result['docs_only'])
        self.repo.git('checkout', '-q', '--orphan', 'unrelated')
        self.repo.write('other.txt', 'other\n')
        other = self.repo.save()
        self.assertTrue(PLAN.make_plan(self.repo.path, other, head)['full'])

    def test_pull_request_uses_merge_base_not_unrelated_main_tip_changes(self):
        self.repo.git('checkout', '-q', '-b', 'feature', self.repo.base)
        feature = self.changed('game/audio.js')
        self.repo.git('checkout', '-q', 'main')
        main = self.changed('game/domestic.js')
        result = PLAN.make_plan(self.repo.path, None, feature, event_name='pull_request',
                               event={'pull_request': {'base': {'sha': main}}})
        self.assertEqual(result['base'], self.repo.base)
        self.assertEqual(result['changed_files'], ['game/audio.js'])
        self.assertFalse(result['publish'])

    def test_scheduled_and_manual_full_publish_policies(self):
        self.changed('README.md', 'docs\n')
        for event, ref, full, publish, expected in (
                ('schedule', 'refs/heads/main', False, False, False),
                ('workflow_dispatch', 'refs/heads/main', True, True, True),
                ('workflow_dispatch', 'refs/heads/feature', True, True, False),
                ('workflow_dispatch', 'refs/heads/main', True, False, False),
                ('pull_request', 'refs/heads/main', True, True, False)):
            result = self.repo.plan(event_name=event, ref=ref, force_full=full, publish=publish)
            self.assertTrue(result['full'])
            self.assertEqual(result['publish'], expected)

    def test_cli_fetches_deployed_base_and_emits_only_json(self):
        self.changed('game/audio.js')
        self.changed('game/domestic.js')
        helper = SimpleNamespace(resolve_published_base=lambda *args, **kwargs: {'sha': self.repo.base})
        output = io.StringIO()
        with patch.dict(sys.modules, {'published_base': helper}), \
                patch.object(PLAN.Path, 'cwd', return_value=self.repo.path), redirect_stdout(output):
            self.assertEqual(PLAN.main(['--head', self.repo.git('rev-parse', 'HEAD'), '--event-name',
                                        'push', '--ref', 'refs/heads/main', '--repository', 'owner/repo']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['base'], self.repo.base)
        self.assertTrue({'audio', 'logistics'} <= set(result['groups']))

    def test_cli_missing_deployment_history_never_uses_event_before(self):
        head = self.changed('game/audio.js')
        def unavailable(*args, **kwargs):
            raise RuntimeError('No actual deployment')
        helper = SimpleNamespace(resolve_published_base=unavailable)
        output = io.StringIO()
        with patch.dict(sys.modules, {'published_base': helper}), \
                patch.object(PLAN.Path, 'cwd', return_value=self.repo.path), redirect_stdout(output):
            PLAN.main(['--head', head, '--event-name', 'push', '--ref',
                       'refs/heads/main', '--repository', 'owner/repo'])
        result = json.loads(output.getvalue())
        self.assertTrue(result['full'])
        self.assertIsNone(result['base'])
        self.assertIn('No actual deployment', result['reasons'])


class PublishedBaselineTests(unittest.TestCase):
    repository = 'owner/repo'

    def fixture(self, *, skipped_latest=False):
        sha = 'a' * 40
        newer = 'b' * 40
        deployments = [dict(id=2, environment='github-pages', sha=newer),
                       dict(id=1, environment='github-pages', sha=sha)]
        def api(endpoint):
            prefix = 'repos/owner/repo'
            if endpoint.startswith(prefix + '/deployments?'):
                return deployments
            for ident, head in ((1, sha), (2, newer)):
                if endpoint.startswith(f'{prefix}/deployments/{ident}/statuses?'):
                    return [dict(state='success', log_url=f'https://github.com/owner/repo/actions/runs/{ident}',
                                 created_at=f'2026-10-{20 + ident:02}T00:00:00Z')]
                if endpoint == f'{prefix}/actions/runs/{ident}':
                    return dict(head_sha=head, head_branch='main', event='workflow_run', status='completed',
                                path='.github/workflows/pages.yml', run_attempt=1,
                                head_repository={'full_name': self.repository}, conclusion='success')
                if endpoint.startswith(f'{prefix}/actions/runs/{ident}/attempts/1/jobs?'):
                    return {'jobs': [dict(id=ident * 10, name='deploy', status='completed',
                        conclusion='skipped' if skipped_latest and ident == 2 else 'success',
                        steps=[dict(name='Deploy verified artifact', conclusion='success')])]}
            raise AssertionError('Unexpected or mutating API: ' + endpoint)
        return api

    def test_green_workflow_with_skipped_deploy_is_not_the_published_baseline(self):
        result = PUBLISHED.resolve_published_base(self.repository, api=self.fixture(skipped_latest=True))
        self.assertEqual(result['sha'], 'a' * 40)
        self.assertEqual(result['job_id'], 10)

    def test_latest_actual_deployment_and_current_head_exclusion(self):
        self.assertEqual(PUBLISHED.resolve_published_base(self.repository, api=self.fixture())['sha'], 'b' * 40)
        result = PUBLISHED.resolve_published_base(self.repository, exclude_head='b' * 40, api=self.fixture())
        self.assertEqual(result['sha'], 'a' * 40)

    def test_stops_after_first_trustworthy_active_deployment(self):
        original = self.fixture()
        calls = []
        def api(endpoint):
            calls.append(endpoint)
            return original(endpoint)
        result = PUBLISHED.resolve_published_base(self.repository, api=api)
        self.assertEqual(result['api_requests'], 4)
        self.assertEqual(len(calls), 4)
        self.assertFalse(any('/deployments/1/' in endpoint for endpoint in calls))

    def test_pending_new_deployment_preserves_active_previous_release(self):
        original = self.fixture()
        def api(endpoint):
            value = deepcopy(original(endpoint))
            if '/deployments/2/statuses?' in endpoint:
                value[0]['state'] = 'in_progress'
            return value
        result = PUBLISHED.resolve_published_base(self.repository, api=api)
        self.assertEqual(result['sha'], 'a' * 40)
        self.assertEqual(result['api_requests'], 5)

    def test_inactive_historical_success_is_not_an_active_baseline(self):
        original = self.fixture()
        def api(endpoint):
            value = deepcopy(original(endpoint))
            if '/statuses?' in endpoint:
                historical = deepcopy(value[0])
                value[0]['state'] = 'inactive'
                value.append(historical)
            return value
        with self.assertRaises(PUBLISHED.BaselineUnavailable):
            PUBLISHED.resolve_published_base(self.repository, api=api)

    def test_rollback_accepts_older_deployment_reactivated_with_latest_success(self):
        original = self.fixture()
        def api(endpoint):
            value = deepcopy(original(endpoint))
            if '/deployments/2/statuses?' in endpoint:
                value[0]['state'] = 'inactive'
            if '/deployments/1/statuses?' in endpoint:
                value[0]['created_at'] = '2026-10-25T12:00:00Z'
            return value
        result = PUBLISHED.resolve_published_base(self.repository, api=api)
        self.assertEqual(result['deployment_id'], 1)
        self.assertEqual(result['status_created_at'], '2026-10-25T12:00:00Z')

    def test_history_lookup_has_a_hard_read_budget(self):
        calls = []
        def api(endpoint):
            calls.append(endpoint)
            if '/deployments?' in endpoint:
                return [dict(id=i, environment='github-pages', sha='a' * 40) for i in range(1, 11)]
            return [dict(state='pending')]
        with self.assertRaisesRegex(PUBLISHED.BaselineUnavailable, 'exceeded24'):
            PUBLISHED.resolve_published_base(self.repository, api=api)
        self.assertEqual(len(calls), 24)

    def test_deployment_status_and_exact_deploy_step_must_both_succeed(self):
        original = self.fixture()
        for broken in ('status', 'step', 'repository'):
            def api(endpoint):
                value = deepcopy(original(endpoint))
                if broken == 'status' and '/deployments/2/statuses?' in endpoint:
                    value[0]['state'] = 'failure'
                if broken == 'step' and '/runs/2/attempts/' in endpoint:
                    value['jobs'][0]['steps'][0]['conclusion'] = 'skipped'
                if broken == 'repository' and endpoint.endswith('/runs/2'):
                    value['head_repository'] = None
                return value
            with self.subTest(broken=broken):
                result = PUBLISHED.resolve_published_base(self.repository, api=api)
                self.assertEqual(result['sha'], 'a' * 40)

    def test_missing_untrusted_or_inaccessible_baselines_fail_explicitly(self):
        with self.assertRaises(PUBLISHED.BaselineUnavailable):
            PUBLISHED.resolve_published_base(self.repository, api=lambda endpoint: [])
        with self.assertRaises(PUBLISHED.BaselineUnavailable):
            PUBLISHED.resolve_published_base('../repo', api=lambda endpoint: [])
        self.assertIsNone(PUBLISHED._run_id('https://evil.invalid/owner/repo/actions/runs/1', self.repository))
        with patch.object(PUBLISHED.subprocess, 'run', side_effect=OSError('denied')):
            with self.assertRaises(PUBLISHED.BaselineUnavailable):
                PUBLISHED.gh_api('repos/owner/repo/deployments')

    def test_gh_requests_are_get_only(self):
        with patch.object(PUBLISHED.subprocess, 'run', return_value=SimpleNamespace(stdout='[]')) as request:
            self.assertEqual(PUBLISHED.gh_api('repos/owner/repo/deployments'), [])
        self.assertEqual(request.call_args.args[0][:4], ['gh', 'api', '--method', 'GET'])


if __name__ == '__main__':
    unittest.main()
