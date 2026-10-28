"""Browser transport parity, bounded catalog loading and isolated transactions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.browser_runtime import BrowserRuntime, MAX_BODY_BYTES
from remake.campaign import Catalog
from remake.session import CampaignSession
from campaign_fixtures import controlled_catalog


class BrowserRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.paths = {}
        base = controlled_catalog().data
        for index in range(3):
            data = deepcopy(base)
            identity = 'controlled-browser-' + str(index)
            data.update(id=identity, title='受控浏览器剧本' + str(index))
            path = Path(cls.directory.name) / (identity + '.json')
            path.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')
            cls.paths[identity] = str(path)
        cls.identities = list(cls.paths)
        original = CampaignSession([Path(path) for path in cls.paths.values()])
        cls.previews = original._scenario_previews()
        del original

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.runtime = BrowserRuntime(self.paths, self.previews, self.identities[0])

    def request(self, path, payload=None, *, runtime=None, method=None):
        response = (runtime or self.runtime).dispatch_json(
            path, method or ('GET' if payload is None else 'POST'),
            None if payload is None else json.dumps(payload, ensure_ascii=False))
        return response['status'], json.loads(response['body'])

    def start(self, index=0, *, runtime=None):
        runtime = runtime or self.runtime
        status, result = self.request('/api/command', dict(kind='new',
            payload=dict(scenario=self.identities[index], faction='shu', seed=2026),
            revision=runtime.session.revision), runtime=runtime)
        self.assertEqual(status, 200, result)
        return result

    def snapshot(self):
        session = self.runtime.session
        return deepcopy((session.to_dict(), session.revision, session.journal,
                         session.game.catalog.sha256))

    def test_lazy_constructor_and_full_openings_without_catalog_rescan(self):
        with patch('remake.session.Catalog', wraps=Catalog) as loader:
            runtime = BrowserRuntime(self.paths, self.previews, self.identities[0])
        self.assertEqual(loader.call_count, 1)
        self.assertEqual(list(runtime.session.catalogs), [self.identities[0]])
        with patch.object(runtime.session, '_scenario_previews',
                          wraps=runtime.session._scenario_previews) as openings:
            status, result = self.request('/api/state', runtime=runtime)
        self.assertEqual(status, 200)
        self.assertIsNone(result['game'])
        self.assertEqual(result['catalog']['scenarios'], self.previews)
        self.assertEqual(openings.call_count, 1)
        self.assertEqual(list(runtime.session.catalogs), [self.identities[0]])

    def test_new_commands_and_save_bytes_match_local_campaign(self):
        local = CampaignSession([Path(self.paths[self.identities[0]])])
        local._opening_previews = deepcopy(self.previews)
        payload = dict(scenario=self.identities[0], faction='shu', seed=2026)
        expected = local.command('new', payload, 0)
        status, actual = self.request('/api/command',
            dict(kind='new', payload=payload, revision=0))
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)
        allocation = dict(city='xiangyang', officer=146, troops=250)
        expected = local.command('allocate', allocation, local.revision)
        status, actual = self.request('/api/command', dict(kind='allocate',
            payload=allocation, revision=self.runtime.session.revision))
        self.assertEqual(status, 200)
        self.assertEqual(actual, expected)
        self.assertEqual(self.runtime.dispatch_json('/api/save'), dict(status=200,
            body=json.dumps(local.export_save(), ensure_ascii=False, allow_nan=False)))
        saved = self.runtime.dispatch_json('/api/save')['body']
        status, _ = self.request('/api/load', dict(save=json.loads(saved),
                                                  revision=self.runtime.session.revision))
        self.assertEqual(status, 200)
        self.assertEqual(self.runtime.dispatch_json('/api/save')['body'], saved)

    def test_preview_and_march_reads_do_not_draw_rng_or_change_current_game(self):
        self.start()
        before = self.snapshot()
        for identity in self.identities:
            status, result = self.request('/api/city-preview?scenario=' + identity + '&city=xiangyang')
            self.assertEqual(status, 200)
            self.assertEqual(result['scenario'], identity)
            status, config = self.request('/api/march-config?scenario=' + identity)
            self.assertEqual(status, 200)
            self.assertIn('travel_routes', config)
            self.assertEqual(self.snapshot(), before)
        status, result = self.request('/api/march-status')
        self.assertEqual(status, 200)
        self.assertEqual(result['engine'], 'python')
        self.assertEqual(self.snapshot(), before)

    def test_tactical_move_and_side_end_reach_the_domain_through_the_fixed_worker_api(self):
        view=self.start()
        def command(kind, **payload):
            status,value=self.request('/api/command',dict(kind=kind,payload=payload,
                revision=self.runtime.session.revision))
            self.assertEqual(status,200,value)
            return value
        view=command('depart',source='xiangyang',target='nanyang',officers=[146])
        for _ in range(20):
            phase=view['game']['phase']
            if phase=='battle':break
            if phase=='city':view=command('end_turn')
            elif phase=='ai':view=command('ai',turn=view['game']['turn'])
            elif phase=='arrivals':view=command('arrivals')
            else:self.fail('Unexpected phase before the real arrival: '+phase)
        self.assertEqual(view['game']['phase'],'battle')
        battle=view['game']['battle']
        reachable=view['catalog']['battle_tactical']['actors']['146']['reachable']
        destination=min(reachable,key=lambda p:(p['cost'],p['y'],p['x']))
        before=deepcopy(view['game'])
        view=command('battle_move',battle_id=battle['id'],actor=146,
            x=destination['x'],y=destination['y'])
        tactical=view['game']['battle']['extended']['tactical']
        self.assertEqual(tactical['positions']['146'],{key:destination[key] for key in ('x','y')})
        self.assertEqual(tactical['points']['attackers'],
            before['battle']['extended']['tactical']['points']['attackers']-destination['cost'])
        self.assertEqual(view['game']['rng'],before['rng'])
        view=command('battle_wait',battle_id=battle['id'])
        self.assertEqual(view['game']['battle']['extended']['tactical']['side'],'attackers')
        self.assertGreater(view['game']['battle']['round'],before['battle']['round'])

    def test_cache_never_evicts_active_game_and_is_bounded_at_two(self):
        self.start()
        cache = self.runtime.session.catalogs
        for identity in [self.identities[1], self.identities[2], self.identities[1]]:
            status, _ = self.request('/api/march-config?scenario=' + identity)
            self.assertEqual(status, 200)
            self.assertEqual(len(cache), 2)
            self.assertIn(self.identities[0], cache)
            self.assertIn(identity, cache)
        self.start(2)
        self.assertEqual(self.runtime.session.game.catalog.data['id'], self.identities[2])
        self.assertEqual(len(cache), 2)
        self.request('/api/march-config?scenario=' + self.identities[1])
        self.assertEqual(set(cache), {self.identities[2], self.identities[1]})
        self.start(1)
        self.assertEqual(self.runtime.session.game.catalog.data['id'], self.identities[1])
        self.assertEqual(len(cache), 2)
        self.assertEqual(self.request('/api/state')[1]['catalog']['scenarios'], self.previews)

    def test_cross_scenario_load_retains_catalog_identity_and_rng(self):
        self.start(1)
        save = self.runtime.dispatch_json('/api/save')['body']
        self.start(2)
        self.start(0)
        self.assertNotIn(self.identities[1], self.runtime.session.catalogs)
        status, _ = self.request('/api/load', dict(save=json.loads(save),
            revision=self.runtime.session.revision))
        self.assertEqual(status, 200)
        self.assertEqual(self.runtime.dispatch_json('/api/save')['body'], save)
        self.assertEqual(self.runtime.session.game.catalog.data['id'], self.identities[1])
        self.assertEqual(len(self.runtime.session.catalogs), 2)

    def test_two_workers_have_independent_games_and_revisions(self):
        other = BrowserRuntime(self.paths, self.previews, self.identities[0])
        baseline = other.dispatch_json('/api/state')
        self.start()
        self.assertEqual(other.dispatch_json('/api/state'), baseline)
        self.assertEqual(other.session.revision, 0)
        self.assertIsNone(other.session.game.state)

    def test_failed_commands_and_loads_keep_state_rng_revision_and_game(self):
        self.start()
        before = self.snapshot()
        game = self.runtime.session.game
        invalid = self.runtime.session.export_save()
        invalid['scenario'] = self.identities[1]
        invalid['checksum'] = 'invalid'
        cases = [
            ('/api/command', dict(kind='new', payload=dict(scenario='unknown', faction='shu', seed=1), revision=1), 400),
            ('/api/command', dict(kind='new', payload=dict(scenario=self.identities[1], faction='missing', seed=1), revision=1), 400),
            ('/api/command', dict(kind='allocate', payload=dict(city='nanyang', officer=146, troops=250), revision=1), 400),
            ('/api/command', dict(kind='allocate', payload=dict(city='xiangyang', officer=146, troops=250), revision=0), 409),
            ('/api/load', dict(save=invalid, revision=1), 400),
            ('/api/load', dict(save=self.runtime.session.export_save(), revision=0), 409),
        ]
        for path, payload, expected in cases:
            with self.subTest(path=path, payload=payload.get('kind')):
                status, result = self.request(path, payload)
                self.assertEqual(status, expected, result)
                self.assertIs(self.runtime.session.game, game)
                self.assertEqual(self.snapshot(), before)

    def test_unknown_paths_methods_and_query_ambiguity_are_rejected(self):
        self.start()
        before = self.snapshot()
        identity = self.identities[0]
        paths = [
            '/api/cloud-config', '/api/python', '/api/../state', '//api/state',
            'https://evil.example/api/state', '/api/state#x', '/api/state#', '/api/state?',
            '/api/state?x=1', '/api/state\n', '/api/state\\',
            '/api/march-config', '/api/march-config?scenario=' + identity + '&scenario=' + identity,
            '/api/march-config?scenario=' + identity + '&extra=1',
            '/api/march-config?scenario=%ZZ', '/api/march-config?scenario=%ff',
            '/api/march-config?scenario=../../private',
            '/api/city-preview?scenario=' + identity,
            '/api/city-preview?scenario=' + identity + '&city=xiangyang&city=xiangyang',
            '/api/city-preview?scenario=' + identity + '&city=unknown',
            '/api/state?' + 'a' * 2048,
        ]
        for path in paths:
            with self.subTest(path=path):
                status, _ = self.request(path)
                self.assertIn(status, (400, 404))
                self.assertEqual(self.snapshot(), before)
        for path, method in [('/api/state', 'POST'), ('/api/command', 'GET'),
                             ('/api/load', 'DELETE'), ('/api/state', 'get')]:
            self.assertEqual(self.runtime.dispatch_json(path, method)['status'], 405)
        self.assertEqual(self.runtime.dispatch_json('/api/state', 'GET', '{}')['status'], 400)
        self.assertEqual(self.snapshot(), before)

    def test_strict_json_shapes_numbers_duplicates_depth_and_size(self):
        self.start()
        before = self.snapshot()
        invalid = [
            None, {}, '[]', '{}', 'null', '{', b'\xff',
            '{"kind":"new","kind":"ai","payload":{},"revision":1}',
            '{"kind":"ai","payload":{"turn":NaN},"revision":1}',
            '{"kind":"ai","payload":{"turn":Infinity},"revision":1}',
            '{"kind":"ai","payload":{"turn":1e9999},"revision":1}',
            '{"kind":"ai","payload":{},"revision":true}',
            '{"kind":"exec","payload":{},"revision":1}',
            '{"kind":"ai","payload":[],"revision":1}',
            '{"kind":"ai","payload":{},"revision":1,"exec":"ignored"}',
            '{"kind":"ai","payload":' + '[' * 65 + '0' + ']' * 65 + ',"revision":1}',
            '"' + 'a' * MAX_BODY_BYTES + '"', '\ud800',
        ]
        for body in invalid:
            with self.subTest(body_type=type(body).__name__):
                result = self.runtime.dispatch_json('/api/command', 'POST', body)
                self.assertIn(result['status'], (400, 413))
                self.assertEqual(self.snapshot(), before)
        for body in ('{}', '{"save":{},"revision":true}',
                     '{"save":[],"revision":1}', '{"save":{},"revision":1,"extra":0}'):
            self.assertEqual(self.runtime.dispatch_json('/api/load', 'POST', body)['status'], 400)
        self.assertEqual(self.snapshot(), before)

    def test_missing_download_and_wrong_catalog_never_replace_current_game(self):
        paths = dict(self.paths)
        paths[self.identities[1]] = str(Path(self.directory.name) / 'not-yet-downloaded.json')
        runtime = BrowserRuntime(paths, self.previews, self.identities[0])
        self.start(runtime=runtime)
        before = runtime.dispatch_json('/api/save')
        status, result = self.request('/api/march-config?scenario=' + self.identities[1], runtime=runtime)
        self.assertEqual(status, 503)
        self.assertNotIn(self.directory.name, json.dumps(result))
        self.assertEqual(runtime.dispatch_json('/api/save'), before)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wrong.json'
            path.write_bytes(Path(self.paths[self.identities[0]]).read_bytes())
            paths[self.identities[1]] = str(path)
            runtime = BrowserRuntime(paths, self.previews, self.identities[0])
            self.assertEqual(runtime.dispatch_json('/api/march-config?scenario=' + self.identities[1])['status'], 503)
            self.assertEqual(list(runtime.session.catalogs), [self.identities[0]])

    def test_configuration_does_not_load_unlisted_or_mutate_caller_previews(self):
        previews = deepcopy(self.previews)
        runtime = BrowserRuntime(self.paths, previews, self.identities[0])
        previews[0]['city_names']['nanyang'] = 'corrupted'
        self.assertEqual(self.request('/api/state', runtime=runtime)[1]['catalog']['scenarios'], self.previews)
        for paths, rows, initial in [
            ({}, self.previews, self.identities[0]),
            (self.paths, self.previews[:-1], self.identities[0]),
            (self.paths, self.previews + [self.previews[0]], self.identities[0]),
            (self.paths, self.previews, 'unlisted'),
            ({**self.paths, self.identities[1]: 'relative.json'}, self.previews, self.identities[0]),
        ]:
            with self.assertRaises(ValueError):
                BrowserRuntime(paths, rows, initial)

    def test_python_backend_is_forced_without_changing_host_environment(self):
        with patch.dict('os.environ', {'MARCH_CORE_BACKEND': 'rust'}), \
             patch('remake.march_core._load', side_effect=AssertionError('native adapter was used')):
            runtime = BrowserRuntime(self.paths, self.previews, self.identities[0])
            self.start(runtime=runtime)
            self.assertEqual(runtime.dispatch_json('/api/march-status')['status'], 200)

    def test_stale_completed_ai_retry_retains_domain_idempotency(self):
        self.start()
        turn = self.runtime.session.game.state.turn
        status, _ = self.request('/api/command', dict(kind='end_turn', payload={},
            revision=self.runtime.session.revision))
        self.assertEqual(status, 200)
        payload = dict(kind='ai', payload=dict(turn=turn), revision=self.runtime.session.revision)
        status, _ = self.request('/api/command', payload)
        self.assertEqual(status, 200)
        before = self.snapshot()
        status, _ = self.request('/api/command', payload)
        self.assertEqual(status, 200)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
