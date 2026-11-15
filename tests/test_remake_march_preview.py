"""Route previews use the current campaign without changing it."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.browser_runtime import BrowserRuntime
from remake.session import CampaignSession


def opening(chapter, faction):
    path = ROOT / 'game/data/campaigns' / f'{chapter}.json'
    session = CampaignSession([path])
    session.command('new', {'scenario': next(iter(session.catalogs)), 'faction': faction,
                            'seed': 2026}, session.revision)
    return session


def preview(session, source, target):
    return session.preview_march(source, target, str(session.revision))


class MarchPreviewTests(unittest.TestCase):
    def test_one_way_yellow_river_uses_only_the_downstream_leg(self):
        early = opening('188-06', 'han_sui')
        downstream = preview(early, 'jincheng', 'shuofang')
        self.assertEqual(downstream['status'], 'available')
        self.assertEqual(downstream['options'], [dict(mode='river', days=15, modes=['river'],
            path=['jincheng', 'shuofang'], route_ids=['jincheng:shuofang:river'])])
        self.assertEqual(downstream['restrictions'], [])

        late = opening('235-01', 'wei')
        upstream = preview(late, 'shuofang', 'jincheng')
        self.assertEqual(upstream['status'], 'own_city')
        self.assertEqual(upstream['options'], [])
        self.assertIn(dict(reason='one_way', mode='river', route_id='jincheng:shuofang:river',
                           **{'from': 'jincheng', 'to': 'shuofang'}), upstream['restrictions'])
        self.assertEqual(upstream['detour']['kind'], 'transfer')
        self.assertEqual(upstream['detour']['path'], ['shuofang', 'anding', 'jincheng'])
        self.assertEqual(upstream['detour']['days'], 72)

    def test_attack_can_stage_from_a_reachable_owned_city(self):
        session = opening('235-01', 'wei')
        result = preview(session, 'anding', 'wuyuan')
        self.assertEqual(result['status'], 'no_direct_route')
        self.assertEqual(result['options'], [])
        self.assertEqual(result['detour'], dict(kind='staged_attack', via='shuofang',
            path=['anding', 'shuofang', 'wuyuan'], modes=['land'], days=53))
        exploration = preview(session, 'bohai', 'liaodong')
        self.assertEqual(exploration['status'], 'available')
        self.assertEqual([(item['mode'], item['days']) for item in exploration['options']],
                         [('explore', 75)])

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
                           **{'from': 'yinping', 'to': 'shujun'}), result['restrictions'])
        self.assertEqual(result['detour']['path'], ['shujun', 'guanghan', 'yinping'])

    def test_settled_city_requires_stopping_on_the_road(self):
        session = opening('207-09', 'wei')
        result = preview(session, 'anping', 'zhao')
        self.assertEqual(result['options'], [])
        self.assertEqual([(row['reason'], row['via']) for row in result['restrictions']],
                         [('requires_stop', ['julu'])])
        self.assertEqual(result['detour']['path'], ['anping', 'julu', 'zhao'])
        self.assertEqual(result['detour']['days'], 8)

    def test_temporarily_closed_and_not_yet_open_corridors(self):
        session = opening('207-09', 'wei')
        # The chapter starts in September. Exercise the documented June/July transition.
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
