"""The selective CI gate cannot turn skipped or altered checks into a release."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci_gate', ROOT / 'tools/ci/gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
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


if __name__ == '__main__':
    unittest.main()
