"""Cheap completeness checks for the CI split; never import the campaign suite."""
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
RUNNER = ROOT / 'tools/ci/run_campaign_tests.py'
spec = importlib.util.spec_from_file_location('campaign_ci_shards', RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CampaignCiShardTests(unittest.TestCase):
    def test_three_shards_cover_every_file_exactly_once(self):
        complete = runner.discover_files()
        self.assertTrue(complete)
        groups = [runner.select_shard(complete, index, 3) for index in (1, 2, 3)]
        self.assertEqual(sorted(path for group in groups for path in group), sorted(complete))
        for index, group in enumerate(groups):
            self.assertEqual(group, complete[index::3])
            for other in groups[index + 1:]:
                self.assertFalse(set(group) & set(other))
        self.assertLessEqual(max(map(len, groups)) - min(map(len, groups)), 1)

    def test_list_only_cli_has_no_unlisted_or_duplicate_files(self):
        records = []
        for index in (1, 2, 3):
            result = subprocess.run([sys.executable, '-B', str(RUNNER), '--shard', str(index),
                                     '--shards', '3', '--list-only'],
                                    cwd=ROOT, text=True, capture_output=True, check=True)
            record = json.loads(result.stdout)
            self.assertEqual(record['shard'], index)
            self.assertEqual(record['file_count'], len(record['files']))
            records.extend(record['files'])
        expected = [path.relative_to(ROOT).as_posix() for path in runner.discover_files()]
        self.assertEqual(sorted(records), expected)
        self.assertEqual(len(records), len(set(records)))

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
