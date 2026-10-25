"""Compact worker views hydrate exactly; legacy transport and saves stay intact."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake.browser_runtime import BrowserRuntime
from remake.campaign import digest
from remake.session import CampaignSession
from remake.view_transport import ViewTransport
import remake.session as sessions
from campaign_fixtures import controlled_catalog


def hydrate(packet, cached=None, quotes=None):
    if packet.get('transport') != 'tk2-view-v1':
        return packet
    fixed = packet.get('static_catalog', cached)
    by_id = {str(row['id']): row for row in fixed['library']}
    view = deepcopy(packet['view'])
    view['catalog'] = dict(fixed, **view['catalog'])
    if 'travel_quotes' not in packet['view']['catalog']:
        view['catalog']['travel_quotes'] = quotes if quotes is not None else fixed['travel_quotes']
    view['catalog']['library'] = [dict(by_id[str(row['id'])], **row) for row in packet['view']['catalog']['library']]
    return view


class ViewTransportTests(unittest.TestCase):
    def setUp(self):
        catalog = controlled_catalog()
        with patch.object(sessions, 'Catalog', return_value=catalog):
            self.session = CampaignSession([ROOT/'controlled.json'])
        self.transport = ViewTransport()
        self.sha = catalog.sha256

    def test_full_and_cached_views_are_identical_after_real_commands(self):
        first = self.session.view()
        packet = self.transport.pack(first, self.sha)
        fixed = deepcopy(packet['static_catalog'])
        fixed['travel_quotes'] = first['catalog']['travel_quotes']
        self.assertEqual(hydrate(packet), first)
        token = packet['catalog_token']+':'+packet['quote_token']
        self.session.command('new', dict(faction='shu', seed=2026), 0)
        saved = self.session.export_save()
        initial_game = self.transport.pack(self.session.view(), self.sha, token)
        fixed['travel_quotes'] = self.session.view()['catalog']['travel_quotes']
        token = initial_game['catalog_token']+':'+initial_game['quote_token']
        for operation in (lambda: self.session.view(), lambda: self.session.command('allocate',
                          dict(city='xiangyang', officer=146, troops=200), self.session.revision)):
            value = operation()
            wire = self.transport.pack(value, self.sha, token)
            self.assertNotIn('static_catalog', wire)
            self.assertIn('quote_token', wire)
            self.assertEqual(hydrate(wire, fixed), value)
            self.assertLess(len(json.dumps(wire)), len(json.dumps(value)) * .6)
        before = self.session.export_save()
        self.transport.pack(self.session.view(), self.sha, token)
        self.assertEqual(self.session.export_save(), before)
        self.session.load_save(saved, self.session.revision)
        self.assertEqual(self.session.export_save(), saved)

    def test_unknown_or_evicted_tokens_resend_static_data_without_losing_dynamic_people(self):
        value = self.session.view()
        p = self.transport.pack(value, 'a')
        self.assertIn('static_catalog', self.transport.pack(value, 'a', 'unknown'))
        changed = deepcopy(value)
        changed['catalog']['library'][0].update(faction='shu', alive=True, year_state='retired', location='nanyang')
        self.assertEqual(hydrate(self.transport.pack(changed, 'a', p['catalog_token']), p['static_catalog']), changed)
        for key in ('b', 'c'):
            self.transport.pack(value, key)
        self.assertEqual(len(self.transport.catalogs), 2)
        self.assertEqual(hydrate(self.transport.pack(value, 'a')), value)
        self.assertEqual(self.transport.pack({'error': 'no'}, 'a'), {'error': 'no'})

    def test_newly_founded_factions_are_dynamic_even_with_the_same_catalog_token(self):
        before = self.session.view()
        packet = self.transport.pack(before, self.sha)
        self.assertNotIn('factions', packet['static_catalog'])
        after = deepcopy(before)
        after['catalog']['factions'].append(dict(id='newly-founded', name='新勢力', city='xiangyang'))
        wire = self.transport.pack(after, self.sha, packet['catalog_token'])
        self.assertNotIn('static_catalog', wire)
        self.assertEqual(hydrate(wire, packet['static_catalog']), after)

    def test_quote_cache_ignores_only_fields_that_do_not_change_routes(self):
        self.session.command('new', dict(faction='shu', seed=2026), 0)
        baseline = self.session.view()
        first = self.transport.pack(baseline, self.sha)
        self.assertEqual(hydrate(first), baseline)
        known = first['catalog_token'] + ':' + first['quote_token']
        city_id = next(iter(baseline['game']['cities']))
        officer_id = next(iter(baseline['game']['officers']))
        changes = {
            'troops': lambda view: view['game']['officers'][officer_id].update(troops=17),
            'gold': lambda view: view['game']['cities'][city_id].update(gold=9876),
            'day': lambda view: view['game'].update(day=21),
            'phase': lambda view: view['game'].update(phase='ai'),
            'revision': lambda view: view.update(revision=view['revision'] + 7),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                value = deepcopy(baseline)
                change(value)
                packet = self.transport.pack(value, self.sha, known)
                self.assertEqual(packet['quote_token'], first['quote_token'])
                self.assertNotIn('travel_quotes', packet['view']['catalog'])
                self.assertNotIn('static_catalog', packet)
                self.assertEqual(hydrate(packet, first['static_catalog'],
                    baseline['catalog']['travel_quotes']), value,
                    'only repeated wire data is omitted; all changed state survives hydration')
        before = self.session.export_save()
        self.transport.pack(self.session.view(), self.sha, known)
        self.assertEqual(self.session.export_save(), before, 'quote negotiation does not change save or RNG')

    def test_every_route_context_change_resends_quotes_and_hydrates_fully(self):
        self.session.command('new', dict(faction='shu', seed=2026), 0)
        baseline = self.session.view()
        first = self.transport.pack(baseline, self.sha)
        known = first['catalog_token'] + ':' + first['quote_token']
        city_id = next(iter(baseline['game']['cities']))
        changes = {
            'month': lambda view: view['game'].update(month=7),
            'owner': lambda view: view['game']['cities'][city_id].update(owner='wu'),
            'new_city': lambda view: view['game']['cities'].update(newly_founded=dict(
                baseline['game']['cities'][city_id], id='newly_founded')),
            'player': lambda view: view['game'].update(player='wei'),
            'discovered_route': lambda view: view['game']['extension']['travel']['discovered'].append('sea:new-link'),
            'source_sha': lambda view: None,
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                value = deepcopy(baseline)
                change(value)
                # Distinct route results make stale reuse visible even when the
                # controlled map would happen to retain the same shortest path.
                value['catalog']['travel_quotes'] = {'context': name, 'days': 4}
                source = self.sha + '-changed' if name == 'source_sha' else self.sha
                packet = self.transport.pack(value, source, known)
                self.assertNotEqual(packet['quote_token'], first['quote_token'])
                self.assertEqual(packet['view']['catalog']['travel_quotes'], value['catalog']['travel_quotes'])
                self.assertEqual(hydrate(packet, first['static_catalog'],
                    baseline['catalog']['travel_quotes']), value)
        # The former one-part token still avoids repeated immutable metadata,
        # but cannot claim to have cached the new quote context.
        legacy = self.transport.pack(baseline, self.sha, first['catalog_token'])
        self.assertNotIn('static_catalog', legacy)
        self.assertIn('travel_quotes', legacy['view']['catalog'])
        self.assertEqual(hydrate(legacy, first['static_catalog']), baseline)

    def test_scenario_switch_and_unknown_cache_resend_static_catalog(self):
        first_view = self.session.view()
        first = self.transport.pack(first_view, 'source-a')
        first_known = first['catalog_token'] + ':' + first['quote_token']
        other = deepcopy(first_view)
        other['catalog'].update(scenario_id='other-scenario', title='另一個劇本')
        other['catalog']['library'][0]['virtue'] = 86
        switched = self.transport.pack(other, 'source-b', first_known)
        self.assertIn('static_catalog', switched)
        self.assertNotEqual(switched['catalog_token'], first['catalog_token'])
        self.assertIn('travel_quotes', switched['view']['catalog'])
        self.assertEqual(hydrate(switched), other)
        back = self.transport.pack(first_view, 'source-a',
            switched['catalog_token'] + ':' + switched['quote_token'])
        self.assertIn('static_catalog', back, 'a changed scenario sends the metadata the caller lacks')
        self.assertEqual(hydrate(back), first_view)
        for known in ('', 'unknown-cache', '0' * 64 + ':' + '1' * 64):
            with self.subTest(known=known):
                recovered = self.transport.pack(first_view, 'source-a', known)
                self.assertIn('static_catalog', recovered)
                self.assertIn('travel_quotes', recovered['view']['catalog'])
                self.assertEqual(hydrate(recovered), first_view)
        self.transport.pack(other, 'source-b')
        self.transport.pack(other, 'source-c')
        self.assertNotIn('source-a', self.transport.catalogs)
        reloaded = self.transport.pack(first_view, 'source-a', '')
        self.assertIn('static_catalog', reloaded)
        self.assertEqual(hydrate(reloaded), first_view)

    def test_runtime_legacy_and_compact_paths_preserve_raw_saves_rng_and_errors(self):
        runtime = object.__new__(BrowserRuntime)
        runtime.session = self.session
        runtime._view_transport = ViewTransport()
        full = runtime.dispatch_json('/api/state')
        packet = json.loads(runtime.dispatch_compact_json('/api/state')['body'])
        self.assertEqual(hydrate(packet), json.loads(full['body']))
        body = json.dumps(dict(kind='new', payload=dict(faction='shu', seed=2026), revision=0))
        self.assertEqual(runtime.dispatch_compact_json('/api/command', 'POST', body, 'bad')['status'], 400)
        self.assertIsNone(self.session.game.state)
        # This controlled runtime does not need scenario loading for non-new commands.
        self.session.command('new', dict(faction='shu', seed=2026), 0)
        saved = runtime.dispatch_json('/api/save')
        self.assertEqual(runtime.dispatch_compact_json('/api/save'), saved)
        state_hash = digest(self.session.to_dict())
        body = json.dumps(dict(kind='allocate', payload=dict(city='xiangyang', officer=146, troops=200), revision=-1))
        self.assertEqual(runtime.dispatch_compact_json('/api/command', 'POST', body)['status'], 409)
        self.assertEqual(digest(self.session.to_dict()), state_hash)
        self.assertEqual(runtime.dispatch_compact_json('/api/save'), saved)

if __name__ == '__main__':
    unittest.main()
