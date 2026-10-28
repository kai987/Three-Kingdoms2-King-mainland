"""Cheap completeness checks for the CI split; never import the campaign suite."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/ci/run_campaign_tests.py'
spec = importlib.util.spec_from_file_location('campaign_ci_shards', RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CampaignCiShardTests(unittest.TestCase):
    def test_explicit_scope_registry_covers_every_current_module(self):
        registry, checksum = runner.load_registry()
        self.assertEqual(set(registry['modules']),
                         {path.relative_to(ROOT).as_posix() for path in runner.discover_files()})
        self.assertEqual(len(checksum), 64)
        self.assertEqual(registry['modules']['tests/test_remake_march_save_compat.py']['tier'],
                         'compatibility')
        self.assertEqual(registry['modules']['tests/test_remake_march_core.py']['tier'], 'related')

    def test_six_shards_cover_every_file_exactly_once(self):
        complete = runner.discover_files()
        self.assertTrue(complete)
        self.assertEqual(runner.SHARD_COUNT, 6)
        groups = runner.partition_files(complete)
        self.assertEqual(sorted(path for group in groups for path in group), sorted(complete))
        for index, group in enumerate(groups):
            self.assertEqual(group, complete[index::6])
            for other in groups[index + 1:]:
                self.assertFalse(set(group) & set(other))
        self.assertLessEqual(max(map(len, groups)) - min(map(len, groups)), 1)
        # Each former shard is split in two, retaining all its original files.
        for index in range(3):
            self.assertEqual(sorted(groups[index] + groups[index + 3]), complete[index::3])

    def test_partition_contract_rejects_changed_count_duplicates_and_empty_shards(self):
        complete = runner.discover_files()
        for count in (1, 3, 4, 5, 7):
            with self.assertRaisesRegex(ValueError, 'exactly 6'):
                runner.partition_files(complete, count)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            runner.partition_files(complete + complete[:1])
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            runner.partition_files(complete[:5])

    def test_list_only_cli_has_no_unlisted_or_duplicate_files(self):
        expected = [path.relative_to(ROOT).as_posix() for path in runner.discover_files()]
        for backend in ('python', 'rust'):
            records = []
            for index in range(1, 7):
                result = subprocess.run([sys.executable, '-B', str(RUNNER), '--shard', str(index),
                                         '--shards', '6', '--list-only'],
                                        cwd=ROOT, text=True, capture_output=True, check=True,
                                        env={**os.environ, 'MARCH_CORE_BACKEND': backend})
                record = json.loads(result.stdout)
                self.assertEqual((record['backend'], record['shard'], record['shards']), (backend, index, 6))
                self.assertEqual(record['file_count'], len(record['files']))
                records.extend(record['files'])
            self.assertEqual(sorted(records), expected)
            self.assertEqual(len(records), len(set(records)))

    def test_cli_and_workflow_enforce_the_same_six_shard_contract(self):
        result = subprocess.run([sys.executable, '-B', str(RUNNER), '--shard', '1',
                                 '--shards', '3', '--list-only'],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exactly 6', result.stderr)
        workflow = (ROOT / '.github/workflows/web-checks.yml').read_text()
        rules = workflow.split('  campaign-rules:\n', 1)[1].split('  campaign-soak:\n', 1)[0]
        self.assertIn('backend: [python, rust]', rules)
        self.assertIn('shard: [1, 2, 3, 4, 5, 6]', rules)
        self.assertIn('--shards 6', rules)
        self.assertIn('timeout-minutes: 20', rules)

    def test_loader_retains_standard_module_hooks_and_source_imports(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sys, 'path', sys.path[:]):
            root = Path(directory)
            tests, source = root / 'tests', root / 'source'
            tests.mkdir(); source.mkdir()
            (source / 'ci_shard_source_marker.py').write_text('VALUE = 42\n')
            module = tests / 'test_remake_ci_loader_fixture.py'
            module.write_text('import unittest\nfrom ci_shard_source_marker import VALUE\n'
                              'class Example(unittest.TestCase):\n'
                              ' def test_marker(self): self.assertEqual(VALUE, 42)\n'
                              'def load_tests(loader, tests, pattern):\n'
                              ' return tests\n')
            try:
                suite = runner.load_suite([module], tests, source)
                self.assertEqual(suite.countTestCases(), 1)
                result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                self.assertTrue(result.wasSuccessful())
            finally:
                sys.modules.pop('test_remake_ci_loader_fixture', None)
                sys.modules.pop('ci_shard_source_marker', None)


if __name__ == '__main__':
    unittest.main()
