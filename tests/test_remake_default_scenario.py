"""New menus start184 without changing explicit selections or current saves."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.browser_runtime import BrowserRuntime
from remake.session import CampaignSession, DEFAULT_SCENARIO

SPEC = importlib.util.spec_from_file_location('tk2_default_build_web', ROOT / 'game/build_web.py')
WEB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEB)


class DefaultScenarioTests(unittest.TestCase):
    paths = [ROOT / 'game/data/campaigns' / (date + '.json')
             for date in ('263-05', '184-02', '190-01')]

    def test_first_menu_chooses_yellow_turban_independently_of_catalog_order(self):
        for paths in (self.paths, self.paths[::-1], self.paths[1:] + self.paths[:1]):
            with self.subTest(order=[path.stem for path in paths]):
                session = CampaignSession(paths)
                view = session.view()
                self.assertEqual(view['catalog']['scenario_id'], DEFAULT_SCENARIO)
                self.assertIsNone(view['game'])
                self.assertEqual(session.revision, 0)
                self.assertEqual(session.game.catalog.data['start_year'], 184)
                self.assertEqual(session.game.catalog.data['start_month'], 2)
                self.assertIn('yellow_turban', session.game.catalog.factions)

    def test_explicit_start_and_partial_catalogs_never_depend_on_list_order(self):
        session = CampaignSession(self.paths, initial_scenario='mainland263-05')
        self.assertEqual(session.game.catalog.data['id'], 'mainland263-05')
        with self.assertRaisesRegex(ValueError, 'Unknown initial scenario'):
            CampaignSession(self.paths, initial_scenario='unknown')
        partial = [self.paths[0], self.paths[2]]
        for paths in (partial, partial[::-1]):
            self.assertEqual(CampaignSession(paths).game.catalog.data['id'], 'mainland190-01')
        self.assertEqual(CampaignSession([self.paths[0]]).game.catalog.data['id'], 'mainland263-05')

    def test_manual_scenario_new_and_signed_load_keep_the_selected_campaign(self):
        session = CampaignSession(self.paths)
        session.command('new', dict(scenario='mainland263-05', faction='wei', seed=2026), 0)
        saved = session.export_save()
        for _ in range(2):
            self.assertEqual(session.view()['catalog']['scenario_id'], 'mainland263-05')
            self.assertEqual(session.export_save(), saved)
        # A new game without a scenario keeps the user's current selection;
        # the184 default is a constructor choice, not a command override.
        session.command('new', dict(faction='wei', seed=2026), session.revision)
        self.assertEqual(session.game.catalog.data['id'], 'mainland263-05')
        session.command('new', dict(scenario=DEFAULT_SCENARIO,
                                   faction='yellow_turban', seed=2026), session.revision)
        session.load_save(saved, session.revision)
        self.assertEqual(session.game.catalog.data['id'], 'mainland263-05')
        self.assertEqual(session.export_save(), saved)

    def test_browser_default_and_explicit_initial_selection_are_both_respected(self):
        session = CampaignSession(self.paths)
        # Catalog stores raw bytes, not its filesystem location.
        paths = {json.loads(path.read_text())['id']: str(path.resolve()) for path in self.paths}
        previews = session._scenario_previews()
        for initial in (None, 'mainland263-05'):
            with self.subTest(initial=initial):
                runtime = BrowserRuntime(paths, previews) if initial is None else BrowserRuntime(paths, previews, initial)
                response = runtime.dispatch_json('/api/state')
                self.assertEqual(response['status'], 200)
                view = json.loads(response['body'])
                self.assertEqual(view['catalog']['scenario_id'], initial or DEFAULT_SCENARIO)
                self.assertIsNone(view['game'])
                self.assertEqual(len(runtime.session.catalogs), 1)


class StaticDefaultManifestTests(unittest.TestCase):
    def build_manifest(self, folder, identities):
        # Exercise the real manifest selection with tiny substituted assets;
        # do not copy the full release or regenerate any catalog for this test.
        rows = [dict(id=identity) for identity in identities]
        with patch.object(WEB, 'static_allowlist', return_value={'index.html': 'index.html'}), \
                patch.object(WEB, 'copy_pyodide'), \
                patch.object(WEB, 'write_cloud_config'), \
                patch.object(WEB, 'runtime_catalogs', return_value=(rows, {})), \
                patch.object(WEB, 'python_bundle', return_value={}):
            WEB.build(folder)
        return json.loads((folder / 'runtime/engine-manifest.json').read_text())

    def test_release_selects184_instead_of_the_last_manifest_entry(self):
        with tempfile.TemporaryDirectory(prefix='tk2-default-manifest-') as directory:
            manifest = self.build_manifest(Path(directory) / 'minimal-release',
                                           [DEFAULT_SCENARIO, 'mainland263-05'])
            self.assertEqual(manifest['initial_scenario'], DEFAULT_SCENARIO)
            self.assertNotEqual(manifest['initial_scenario'], manifest['catalogs'][-1]['id'])

    def test_release_fails_clearly_when_the_required_default_is_missing(self):
        with tempfile.TemporaryDirectory(prefix='tk2-default-manifest-') as directory:
            with self.assertRaisesRegex(ValueError, 'default Yellow Turban campaign'):
                self.build_manifest(Path(directory) / 'minimal-release', ['mainland263-05'])


if __name__ == '__main__':
    unittest.main()
