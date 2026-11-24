"""Route previews use the current campaign without changing it."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.browser_runtime import BrowserRuntime
from remake.errors import GameError
from remake.session import CampaignSession


GEOMETRY = json.loads((ROOT / 'game/config/route-geometry.json').read_text())['routes']


def opening(chapter, faction):
    path = ROOT / 'game/data/campaigns' / f'{chapter}.json'
    session = CampaignSession([path])
    session.command('new', {'scenario': next(iter(session.catalogs)), 'faction': faction,
                            'seed': 2026}, session.revision)
    return session


def preview(session, source, target):
    return session.preview_march(source, target, str(session.revision))


def quote_details(row):
    return {key: value for key, value in row.items() if key != 'segments'}


class MarchPreviewTests(unittest.TestCase):
    def test_xiaopei_and_xiapi_offer_land_and_river_in_both_directions(self):
        for faction, source, target, river_days in (
            ('shu', 'qiao', 'xiapi', 10), ('lubu', 'xiapi', 'qiao', 21),
        ):
            with self.subTest(source=source, target=target):
                session = opening('198-03', faction)
                result = preview(session, source, target)
                self.assertEqual((result['status'], result['restrictions'], result['detour']),
                                 ('available', [], None))
                self.assertCountEqual([row['mode'] for row in result['options']], ['land', 'river'])
                for option in result['options']:
                    mode = option['mode']
                    route_id = f'qiao:xiapi:{mode}'
                    self.assertEqual(option['path'], [source, target])
                    self.assertEqual(option['route_ids'], [route_id])
                    self.assertEqual(option['days'], {'land': 8, 'river': river_days}[mode])

                    geometry = GEOMETRY[route_id]
                    parts = geometry['parts'] if source == geometry['from'] else reversed(geometry['parts'])
                    self.assertIn(mode, [segment['mode'] for segment in option['segments']])
                    self.assertEqual(option['segments'], [
                        dict(mode=part['mode'], d=part['d'], route_id=route_id, one_way=False,
                             **{'from': source, 'to': target}) for part in parts])

    def test_one_way_yellow_river_uses_only_the_downstream_leg(self):
        early = opening('188-06', 'han_sui')
        downstream = preview(early, 'jincheng', 'shuofang')
        self.assertEqual(downstream['status'], 'available')
        self.assertEqual([quote_details(row) for row in downstream['options']],
            [dict(mode='river', days=15, modes=['river'],
                  path=['jincheng', 'shuofang'], route_ids=['jincheng:shuofang:river'])])
        river_id = 'jincheng:shuofang:river'
        segments = downstream['options'][0]['segments']
        self.assertEqual(segments, [
            dict(mode=part['mode'], d=part['d'], route_id=river_id,
                 one_way=part['mode'] == 'river', **{'from': 'jincheng', 'to': 'shuofang'})
            for part in GEOMETRY[river_id]['parts']])
        self.assertEqual(downstream['restrictions'], [])

        late = opening('235-01', 'wei')
        upstream = preview(late, 'shuofang', 'jincheng')
        self.assertEqual(upstream['status'], 'own_city')
        self.assertEqual(upstream['options'], [])
        self.assertEqual([quote_details(row) for row in upstream['restrictions']],
            [dict(reason='one_way', mode='river', route_id=river_id,
                  **{'from': 'jincheng', 'to': 'shuofang'})])
        self.assertEqual(upstream['restrictions'][0]['segments'], segments,
                         'The blocked route shows its permitted direction, even when inspecting upstream')
        self.assertEqual(upstream['detour']['kind'], 'transfer')
        self.assertEqual(upstream['detour']['path'], ['shuofang', 'anding', 'jincheng'])
        self.assertEqual(upstream['detour']['days'], 72)
        self.assertEqual(upstream['detour']['segments'], [
            dict(mode='land', d=GEOMETRY[route_id]['parts'][0]['d'], route_id=route_id,
                 one_way=False, **{'from': source, 'to': target})
            for route_id, source, target in (
                ('anding:shuofang:land', 'shuofang', 'anding'),
                ('anding:jincheng:land', 'anding', 'jincheng'))])

    def test_attack_can_stage_from_a_reachable_owned_city(self):
        session = opening('235-01', 'wei')
        result = preview(session, 'anding', 'wuyuan')
        self.assertEqual(result['status'], 'no_direct_route')
        self.assertEqual(result['options'], [])
        self.assertEqual(quote_details(result['detour']), dict(kind='staged_attack', via='shuofang',
            path=['anding', 'shuofang', 'wuyuan'], modes=['land'], days=53))
        self.assertEqual([(row['from'], row['to']) for row in result['detour']['segments']],
                         [('anding', 'shuofang'), ('shuofang', 'wuyuan')])
        exploration = preview(session, 'bohai', 'liaodong')
        self.assertEqual(exploration['status'], 'available')
        self.assertEqual([(item['mode'], item['days']) for item in exploration['options']],
                         [('explore', 75)])
        self.assertEqual([row['mode'] for row in exploration['options'][0]['segments']],
                         ['land', 'sea', 'land'])

    def test_diplomacy_blocks_an_otherwise_adjacent_target(self):
        session = opening('208-10', 'shu')
        result = preview(session, 'jiangxia', 'lujiang')
        self.assertEqual((result['status'], result['options'], result['detour']),
                         ('non_aggression', [], None))

    def test_yinping_legacy_direction_applies_without_a_one_way_flag(self):
        session = opening('217-07', 'shu')
        result = preview(session, 'shujun', 'yinping')
        self.assertEqual((result['status'], result['options']), ('no_direct_route', []))
        self.assertIn(dict(reason='one_way', mode='land', route_id='yinping:shujun:land',
                           **{'from': 'yinping', 'to': 'shujun'}),
                      [quote_details(row) for row in result['restrictions']])
        self.assertTrue(result['restrictions'][0]['segments'][0]['one_way'])
        self.assertEqual(result['detour']['path'], ['shujun', 'guanghan', 'yinping'])

    def test_settled_city_requires_stopping_on_the_road(self):
        session = opening('207-09', 'wei')
        result = preview(session, 'anping', 'zhao')
        self.assertEqual(result['options'], [])
        self.assertEqual([(row['reason'], row['via']) for row in result['restrictions']],
                         [('requires_stop', ['julu'])])
        self.assertEqual(result['detour']['path'], ['anping', 'julu', 'zhao'])
        self.assertEqual(result['detour']['days'], 8)
        sections = GEOMETRY['anping:wei:land']['city_sections']
        self.assertEqual([row['d'] for row in result['detour']['segments']],
                         [section['parts'][0]['d'] for section in sections[:2]])

    def test_temporarily_closed_and_not_yet_open_corridors(self):
        session = opening('207-09', 'wei')
        # Exercise the June/July route restrictions before Liaoxi became friendly.
        # An owned destination now also has a quicker transfer via Youbeiping.
        session.game.state.cities['liaoxi'].owner = 'wuhuan'
        for month, reason, date, active, restricted in (
            (6, 'not_yet_open', [207, 7], 'liaoxi:yuyang:land', 'yuyang:liaoxi:lulong:land'),
            (7, 'closed', [207, 8], 'yuyang:liaoxi:lulong:land', 'liaoxi:yuyang:land'),
        ):
            with self.subTest(month=month):
                session.game.state.month = month
                result = preview(session, 'yuyang', 'liaoxi')
                self.assertEqual([row['route_ids'] for row in result['options']], [[active]])
                self.assertEqual(result['restrictions'], [dict(reason=reason, mode='land',
                    date=date, route_id=restricted, **{'from': 'yuyang', 'to': 'liaoxi'})])

    def test_browser_route_quotes_are_read_only_and_bound_to_the_revision(self):
        session = opening('235-01', 'wei')
        scenario = next(iter(session.catalogs))
        runtime = BrowserRuntime({scenario: str(ROOT / 'game/data/campaigns/235-01.json')},
                                 session._scenario_previews(), scenario)
        runtime.session = session
        current = runtime.dispatch_json('/api/save')['body']
        journal = list(session.journal)
        url = '/api/march-preview?source=shuofang&target=jincheng'
        revision = session.revision
        response = runtime.dispatch_json(f'{url}&revision={revision}')
        self.assertEqual(response['status'], 200)
        self.assertEqual(json.loads(response['body']), preview(session, 'shuofang', 'jincheng'))
        same = runtime.dispatch_json(f'/api/march-preview?source=shuofang&target=shuofang&revision={revision}')
        self.assertEqual(json.loads(same['body'])['status'], 'same_city')
        self.assertEqual(runtime.dispatch_json(f'{url}&revision={revision - 1}')['status'], 409)
        self.assertEqual(runtime.dispatch_json(f'{url}&revision={revision}&target=anding')['status'], 400)
        self.assertEqual(runtime.dispatch_json(f'/api/march-preview?source=wuyuan&target=jincheng&revision={revision}')['status'], 400)
        self.assertEqual((session.revision, session.journal), (revision, journal))
        self.assertEqual(runtime.dispatch_json('/api/save')['body'], current)

    def test_transfer_preview_quotes_and_commits_the_same_supplied_detour(self):
        session = opening('217-07', 'shu')
        scenario = next(iter(session.catalogs))
        runtime = BrowserRuntime({scenario: str(ROOT / 'game/data/campaigns/217-07.json')},
                                 session._scenario_previews(), scenario)
        runtime.session = session
        state = session.game.state
        state.cities['guanghan'].grain = 0
        state.cities['nanjun'].grain = 0  # The destination never supplies a transfer.
        session.game.validate(state)
        before, journal = session.export_save(), list(session.journal)
        data = dict(source='shujun', target='nanjun', officers=[370], route_mode='fastest')
        request = dict(data, revision=session.revision)
        response = runtime.dispatch_json('/api/transfer-preview', 'POST', json.dumps(request))
        self.assertEqual(response['status'], 200)
        quote = json.loads(response['body'])
        self.assertEqual((quote['primary']['days'], quote['primary']['path'][1]), (45, 'guanghan'))
        detour = quote['detour']
        self.assertEqual((detour['days'], detour['path']),
                         (56, ['shujun', 'qianwei', 'jiangyang', 'bajun', 'fuling', 'badong', 'nanjun']))
        self.assertEqual(detour['segments'][0]['route_id'], 'shujun:qianwei:river')
        self.assertEqual((session.export_save(), session.journal), (before, journal))
        self.assertEqual(runtime.dispatch_json('/api/transfer-preview', 'POST',
            json.dumps(dict(request, revision=session.revision-1)))['status'], 409)
        self.assertEqual(runtime.dispatch_json('/api/transfer-preview', 'POST',
            json.dumps(dict(request, officers=[370, 370])))['status'], 400)
        self.assertEqual(runtime.dispatch_json('/api/transfer-preview', 'POST',
            json.dumps(dict(request, route_mode='invalid')))['status'], 400)

        land = session.preview_transfer(dict(request, route_mode='land'))
        self.assertEqual(land['primary']['modes'], ['land'])
        self.assertEqual((land['detour']['days'], land['detour']['modes']), (112, ['land']))

        source_grain = state.cities['shujun'].grain
        session.command('transfer', dict(data, supply_detour=True), session.revision)
        state = session.game.state
        row, = state.extension['travel']['marches']
        self.assertEqual(row['quote'], quote_details(detour))
        self.assertEqual(state.cities['shujun'].grain, source_grain-row['supply']['loaded'])
        saved = session.export_save()
        session.load_save(saved, session.revision)
        self.assertEqual(session.export_save(), saved)

    def test_no_supplied_detour_does_not_replace_the_normal_transfer(self):
        session = opening('217-07', 'shu')
        state = session.game.state
        request = dict(source='shujun', target='nanjun', officers=[370], route_mode='fastest')
        self.assertIsNone(session.preview_transfer(dict(request, revision=session.revision))['detour'])
        for key, city in state.cities.items():
            if city.owner == state.player and key != 'shujun':
                city.grain = 0
        before, revision = session.export_save(), session.revision
        preview = session.preview_transfer(dict(request, revision=revision))
        self.assertIsNone(preview['detour'])
        with self.assertRaisesRegex(GameError, '補給'):
            session.command('transfer', dict(request, supply_detour=True), revision)
        self.assertEqual((session.export_save(), session.revision), (before, revision))
        session.command('transfer', request, revision)
        row, = session.game.state.extension['travel']['marches']
        self.assertEqual(row['quote'], quote_details(preview['primary']))
