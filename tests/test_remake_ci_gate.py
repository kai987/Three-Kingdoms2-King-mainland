"""The selective CI gate cannot turn skipped or altered checks into a release."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci_gate', ROOT / 'tools/ci/gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
with patch.object(sys, 'path', [str(ROOT / 'tools/ci'), *sys.path]):
    import pr_reuse
HEAD = 'a' * 40


def plan(mode='scoped', **changes):
    full, docs = mode == 'full', mode == 'docs'
    value = dict(schema='tk2-test-plan-v1', head=HEAD, base='b' * 40,
                 mode=mode, full=full, docs_only=docs, web=not docs,
                 native=full, rules=full, soak=full, resupply=full,
                 publish=not docs, groups=sorted(gate.GROUPS) if full else
                 [] if docs else ['boot', 'audio', 'save', 'cloud'], scenario_ids=[],
                 python_groups=['all'] if full else [] if docs else ['global'])
    value.update(changes)
    return value


def outcomes(value):
    return {'scope': {'result': 'success'}, **{name: {'result': 'success' if required else 'skipped'}
            for name, required in gate.required_jobs(value).items()}}


class ScopeGateTests(unittest.TestCase):
    def test_full_scoped_and_docs_have_explicit_required_jobs(self):
        for mode in ('full', 'scoped', 'docs'):
            value = plan(mode)
            gate.validate_plan(value, HEAD)
            gate.verify_jobs(value, outcomes(value))
        expected = gate.required_jobs(plan())
        self.assertTrue(expected['browser-ui'])
        self.assertTrue(expected['scoped-tests'])
        self.assertFalse(expected['campaign-soak'])
        self.assertEqual([name for name, run in gate.required_jobs(plan('docs')).items() if run], ['docs-check'])

    def test_required_failure_cancel_skip_and_missing_result_all_fail(self):
        value = plan()
        for result in ('failure', 'cancelled', 'skipped', None):
            needs = outcomes(value)
            needs['browser-ui']['result'] = result
            with self.subTest(result=result), self.assertRaises(ValueError):
                gate.verify_jobs(value, needs)
        for mutation in ('missing', 'extra', 'scope'):
            needs = outcomes(value)
            if mutation == 'missing': del needs['browser-ui']
            elif mutation == 'extra': needs['unregistered'] = {'result': 'success'}
            else: needs['scope']['result'] = 'failure'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                gate.verify_jobs(value, needs)

    def test_plan_cannot_remove_full_checks_or_publish_documentation(self):
        bad = [plan('full', rules=False), plan('full', groups=['boot']),
               plan('docs', publish=True), plan(native=False, python_groups=['global', 'compat']),
               plan(groups=['boot', 'unregistered']), plan(groups=['boot', 'boot']),
               plan(web='true'), plan(head='not-a-commit')]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError): gate.validate_plan(value)
        with self.assertRaises(ValueError): gate.validate_plan(plan(), 'c' * 40)
        gate.validate_plan(plan(groups=sorted(gate.GROUPS), scenario_ids=['mainland194-06']))

    def test_summary_quotes_filenames_and_lists_skipped_groups(self):
        value = plan(changed_files=['`\nmalicious.md'], reasons=['cover change'])
        text = gate.summary(value)
        self.assertIn('not needed for this scope', text)
        self.assertNotIn('`\nmalicious.md', text)

    def test_exact_artifact_matches_and_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runtime').mkdir()
            raw = b'approved static entry'
            (root / 'index.html').write_bytes(raw)
            files = {'index.html': dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())}
            digest = hashlib.sha256((json.dumps(files, separators=(',', ':')) + '\n').encode()).hexdigest()
            identity = dict(schema='tk2-static-build-v1', commit=HEAD, files=files, content_sha256=digest)
            (root / 'runtime/build.json').write_text(json.dumps(identity))
            gate.verify_artifact(root, HEAD, digest)
            for mutation in ('file', 'extra', 'head', 'hash', 'symlink'):
                with self.subTest(mutation=mutation):
                    if mutation == 'file': (root / 'index.html').write_bytes(b'changed')
                    elif mutation == 'extra': (root / 'unexpected.txt').write_text('extra')
                    elif mutation == 'symlink': (root / 'alias').symlink_to(root / 'index.html')
                    with self.assertRaises(ValueError):
                        gate.verify_artifact(root, 'c' * 40 if mutation == 'head' else HEAD,
                                             '0' * 64 if mutation == 'hash' else digest)
                    (root / 'index.html').write_bytes(raw)
                    for path in ('unexpected.txt', 'alias'):
                        (root / path).unlink(missing_ok=True)

    def test_documentation_checks_local_links_without_running_game(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q'); git('config', 'user.email', 'ci@example.invalid'); git('config', 'user.name', 'CI fixture')
            (root / 'target.md').write_text('target\n')
            (root / 'README.md').write_text('before\n')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            (root / 'README.md').write_text('[local](target.md) [web](https://example.invalid/)\n')
            git('add', '.'); git('commit', '-qm', 'docs'); head = git('rev-parse', 'HEAD')
            value = plan('docs', base=base, head=head)
            gate.check_docs(value, root)
            (root / 'README.md').write_text('[missing](missing.md)\n')
            git('add', '.'); git('commit', '-qm', 'broken'); value['head'] = git('rev-parse', 'HEAD')
            with self.assertRaisesRegex(ValueError, 'Broken repository link'):
                gate.check_docs(value, root)


class PRVerificationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'ci@example.invalid')
        self.git('config', 'user.name', 'CI fixture')
        (self.root / 'game.txt').write_text('before\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        (self.root / 'game.txt').write_text('after\n')
        self.git('commit', '-qam', 'squash merge')
        self.head = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.tested = self.git('commit-tree', self.tree, '-p', self.base, '-m', 'tested merge')
        self.release = plan('full', head=self.head, base=self.base, reasons=[])
        self.candidate = dict(repository='kai987/game', number=3, feature='f' * 40,
                              base=self.base, run_id=30, attempt=2)
        self.proof = pr_reuse.receipt(self.root, dict(self.release, head=self.tested, publish=False),
                                      'kai987/game', 3, 'f' * 40, 30, 2)
        self.commit = dict(sha=self.tested, tree={'sha': self.tree},
                           parents=[{'sha': self.base}, {'sha': 'f' * 40}])

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def test_equal_tree_uses_pr_checks_but_requires_local_build(self):
        self.assertNotEqual(self.tested, self.head)
        evidence = pr_reuse.verify(self.root, self.release, self.candidate, self.proof,
                                   api=lambda _: self.commit)
        self.assertEqual(evidence, dict(number=3, run_id=30, attempt=2, head=self.tested, tree=self.tree))
        value = dict(self.release, pr_reuse=evidence)
        needs = outcomes(value)
        for job in gate.JOBS:
            if job != 'web-build':
                needs[job]['result'] = 'skipped'
        gate.verify_jobs(value, needs)
        for name, result in [('web-build', 'skipped'), ('browser-ui', 'failure'),
                             ('browser-ui', 'success'), ('scope', 'cancelled')]:
            invalid = deepcopy(needs)
            invalid[name]['result'] = result
            with self.subTest(name=name, result=result), self.assertRaises(ValueError):
                gate.verify_jobs(value, invalid)
        with self.assertRaises(ValueError):
            gate.validate_plan(dict(value, publish=False))

    def test_scope_tree_run_attempt_and_tested_merge_parents_must_match(self):
        for proof, commit in (
                (dict(self.proof, tree='d' * 40), self.commit),
                (dict(self.proof, attempt=1), self.commit),
                (dict(self.proof, number=4), self.commit),
                (dict(self.proof, plan=plan('scoped', head=self.tested, publish=False)), self.commit),
                (self.proof, dict(self.commit, tree={'sha': 'd' * 40})),
                (self.proof, dict(self.commit, parents=[{'sha': 'd' * 40}, {'sha': 'f' * 40}])),
                (self.proof, dict(self.commit, parents=[{'sha': self.base}, {'sha': 'd' * 40}]))):
            with self.subTest(proof=proof, commit=commit), self.assertRaises(ValueError):
                pr_reuse.verify(self.root, self.release, self.candidate, proof, api=lambda _: commit)
        scoped = plan('scoped', head=self.head, groups=['boot', 'scenarios'], native=True,
                      scenario_ids=['mainland184-02', 'mainland217-07'])
        pr_plan = dict(scoped, head=self.tested, publish=False)
        pr_reuse.verify(self.root, scoped, self.candidate, dict(self.proof, plan=pr_plan), api=lambda _: self.commit)
        with self.assertRaisesRegex(ValueError, 'exact release plan'):
            pr_reuse.verify(self.root, scoped, self.candidate, dict(self.proof, plan=dict(
                pr_plan, scenario_ids=['mainland217-07'])), api=lambda _: self.commit)

    def test_find_requires_same_repository_completed_run_and_receipt_step(self):
        repo = dict(full_name='kai987/game')
        pull = dict(number=3, merge_commit_sha=self.head, merged_at='2026-11-10T09:01:00Z',
                    base=dict(ref='main', repo=repo), head=dict(sha='f' * 40, ref='codex/fix', repo=repo))
        run = dict(id=30, run_attempt=2, event='pull_request', status='completed', conclusion='success',
                   path=pr_reuse.WORKFLOW, head_sha='f' * 40, head_branch='codex/fix', head_repository=repo,
                   updated_at='2026-11-10T09:00:00Z', pull_requests=[])
        job = dict(name='verify / gate', status='completed', conclusion='success', head_sha='f' * 40,
                   run_id=30, run_attempt=2,
                   steps=[dict(name='Upload PR verification receipt', conclusion='success')])
        event = dict(ref='refs/heads/main', after=self.head, before=self.base, forced=False)

        def api(endpoint):
            if '/pulls?' in endpoint:
                return [pull]
            if '/runs?' in endpoint:
                return {'workflow_runs': [run]}
            self.assertIn('/runs/30/attempts/2/jobs?', endpoint)
            return {'jobs': [job]}

        self.assertEqual(pr_reuse.find('kai987/game', self.head, event, api=api), self.candidate)
        for target, changes in ((run, {'conclusion': 'failure'}), (run, {'status': 'in_progress'}),
                                (run, {'updated_at': '2026-11-10T09:02:00Z'}),
                                (job, {'steps': []}), (job, {'run_attempt': 1}), (pull, {'merged_at': None}),
                                (pull['head'], {'repo': {'full_name': 'fork/game'}}),
                                (event, {'forced': True})):
            with self.subTest(changes=changes), patch.dict(target, changes), self.assertRaises(ValueError):
                pr_reuse.find('kai987/game', self.head, event, api=api)

    def test_missing_receipt_falls_back_to_full_and_keeps_publication(self):
        path = self.root / 'test-plan.json'
        pr_reuse.write(path, plan(head=self.head, base=self.base, reasons=[]))
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/ci/pr_reuse.py'), 'decide', '--plan', str(path)],
                       cwd=self.root, env={**os.environ, 'GITHUB_SHA': self.head, 'GITHUB_REPOSITORY': 'kai987/game'},
                       capture_output=True, check=True)
        fallback = gate.read_json(path)
        self.assertTrue(fallback['full'])
        self.assertTrue(fallback['publish'])
        self.assertNotIn('pr_reuse', fallback)
        self.assertTrue(gate.required_jobs(fallback)['browser-ui'])


if __name__ == '__main__':
    unittest.main()
