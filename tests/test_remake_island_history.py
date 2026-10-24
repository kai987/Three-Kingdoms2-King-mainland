"""Island history describes evidence without inventing occupation or governors."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))
from build_campaigns import apply_patch
from remake.campaign import Campaign, Catalog
from remake.session import CampaignSession
from campaign_fixtures import controlled_catalog

ISLANDS = ('zhuya', 'yizhou')
SGZ47 = 'https://zh.wikisource.org/zh-hant/三國志/卷47'


def read(path):
    return json.loads((ROOT / path).read_text())


def after_monthly_healing(officers):
    """Account for ordinary +8 recovery without ignoring any other field."""
    expected = deepcopy(officers)
    for officer in expected.values():
        if officer['alive']:
            officer['health'] = min(officer['profile']['health_max'], officer['health'] + 8)
    return expected


def island_catalog(start, occupied=None):
    """Four controlled nodes; all six real identities survive the tested dates."""
    data = controlled_catalog().data
    active = ['nanyang', 'xiangyang', *ISLANDS]
    people = sorted((p for p in data['people']
        if type(p.get('birth_year')) is int and p['birth_year'] <= 200
        and type(p.get('service_year')) is int and p['service_year'] <= 217
        and type(p.get('death_year')) is int and p['death_year'] >= 250),
        key=lambda p: p['runtime_id'])[:6]
    assert len(people) == 6
    data.update(id=f'controlled-island-history-{start[0]}-{start[1]:02d}',
        start_year=start[0], start_month=start[1], active_cities=active,
        city_foundings={}, initial_owners=dict(nanyang='wei', xiangyang='shu',
                                             zhuya='neutral', yizhou='neutral'))
    data['factions'] = [dict(id=side, name=side, captain=people[index * 3]['name'],
                            city=active[index], color=color)
        for index, (side, color) in enumerate((('wei', '#ff0000'), ('shu', '#0000ff')))]
    data['initial_officers'] = [dict(person_id=p['person_id'], city=active[index // 3],
                                     troops=300, ruler=index % 3 == 0)
        for index, p in enumerate(people)]
    if occupied in ISLANDS:
        data['initial_owners'][occupied] = 'wei'
        data['initial_officers'][2]['city'] = occupied
    data['faction_rulers'] = {side: people[index * 3]['runtime_id']
        for index, side in enumerate(('wei', 'shu'))}
    data['appearance_locations'] = {p['person_id']: p['city'] for p in data['initial_officers']}
    data['initial_city_resources'] = {city: dict(gold=100, grain=200, reserves=0) for city in active}
    data['city_income'] = {city: dict(gold=0, grain=0, reserves=0) for city in active}
    history = read('game/config/campaigns/shared.json')['catalog']['city_history']
    for city in ISLANDS:
        data['city_history'][city] = deepcopy(history[city])
    data['links'] = [active[:2]]
    data['travel_routes'] = [dict(id='controlled:island-history', **{'from': active[0], 'to': active[1]},
        mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'islands.json'
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        return Catalog(path)


class IslandHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = read('game/config/campaigns/shared.json')['catalog']
        cls.sources = [apply_patch(cls.shared, read('game/config/campaigns/' + entry['file'])['overrides'])
            for entry in read('game/config/campaigns/index.json')['scenarios']]

    def test_all_23_historical_and_6_if_sources_keep_neutral_islands_and_full_history(self):
        self.assertEqual(len(self.sources), 29)
        self.assertEqual(sum(bool(row['main_scenario'].get('fictional')) for row in self.sources), 6)
        dlc = {'mainland198-03', 'mainland202-06', 'mainland211-07-tongguan', 'mainland215-08'}
        for data in self.sources:
            with self.subTest(scenario=data['id']):
                if data['id'] in dlc:
                    self.assertFalse(data['main_scenario'].get('fictional', False))
                for city in ISLANDS:
                    self.assertEqual(data['initial_owners'][city], 'neutral')
                    self.assertIn(city, data['active_cities'])
                    self.assertEqual(data['city_profiles'][city]['tier'], 'normal')
                    self.assertFalse(any(row['city'] == city for row in data['initial_officers']),
                                     'Do not fabricate an island governor or serving garrison')
                    rule = data['city_history'][city]
                    self.assertEqual(rule['kind'], 'island_region')
                    self.assertEqual(rule['neutral_label'], '岛屿地区（中立）')
                    self.assertEqual(rule['neutral_label_ja'], '島嶼地域（中立）')
                    self.assertFalse(rule['automatic_owner_change'])
                    self.assertIsNone(rule['occupation_date'])
                    self.assertTrue(rule['detail'])
                    self.assertIn('本作', rule['detail_ja'])
                    self.assertIn('プレイ中の実際の占領は変更しません', rule['summary_i18n']['ja'])
                    self.assertIn('進行中的實際占領不因此修改', rule['summary_i18n']['zh-Hant'])
                    self.assertNotIn(city, data['city_foundings'])
                    if data['id'] in ('mainland184-02', 'mainland188-06'):
                        self.assertIn('opening', rule, 'Keep the previous dated opening provenance')

    def test_chronology_records_original_events_without_filling_unknown_months(self):
        zhuya, yizhou = (self.shared['city_history'][city] for city in ISLANDS)
        self.assertIn('海南', zhuya['detail'])
        self.assertIn('徐聞', zhuya['detail'])
        self.assertIn('伝本', zhuya['detail_ja'])
        self.assertIn('台湾', yizhou['detail_ja'])
        self.assertEqual([(r['year'], r['month']) for r in zhuya['chronology']], [(239, None), (242, 7)])
        self.assertEqual(zhuya['chronology'][0]['precision'], 'later_transmitted_fragment_year_only')
        self.assertEqual([(r['year'], r['month']) for r in yizhou['chronology']], [(230, 1), (231, 2)])
        for city, rule in (('zhuya', zhuya), ('yizhou', yizhou)):
            with self.subTest(city=city):
                urls = [row['url'] if isinstance(row, dict) else row for row in rule['sources']]
                self.assertIn(SGZ47, urls)
                for entry in rule['chronology']:
                    self.assertIs(entry['is_island_occupation'], False)
                    self.assertIn(entry['source'], urls)
                self.assertNotIn('owner', rule)
                self.assertNotIn('garrisons', rule)
        self.assertTrue(any('宋書/卷38' in row['url'] for row in zhuya['sources']))
        self.assertTrue(any('三國志/卷61' in row['url'] for row in zhuya['sources']))

    def test_crossing_230_231_239_242_dates_never_assigns_islands_or_generates_governors(self):
        for start, end in (((229, 12), (230, 1)), ((231, 1), (231, 2)),
                           ((238, 12), (239, 1)), ((242, 6), (242, 7))):
            with self.subTest(start=start):
                game = Campaign(island_catalog(start))
                game.command('new', dict(faction='wei', seed=2026), 0)
                # Isolate historical note transitions from optional treasury jobs.
                for policy in game.state.extension['treasury']['factions'].values():
                    policy.update(enabled=False,gold_floor=0)
                before = game.to_dict()
                for _ in range(3):
                    turn = game.state.turn
                    game.command('end_turn', {}, game.revision)
                    game.command('ai', {'turn': turn}, game.revision)
                self.assertEqual((game.state.year, game.state.month), end)
                for city in ISLANDS:
                    self.assertEqual(game.state.cities[city].owner, 'neutral')
                    self.assertEqual(game.to_dict()['cities'][city], before['cities'][city])
                self.assertEqual(game.to_dict()['officers'], after_monthly_healing(before['officers']))
                self.assertEqual(game.to_dict()['rng'], before['rng'])
                self.assertEqual(game.to_dict()['soldiers'], before['soldiers'])
                self.assertFalse(any(row['kind'] in ('city_founded', 'city_captured') and
                    set(row['city_ids']).intersection(ISLANDS)
                    for row in game.state.extension['events']['items']))

    def test_current_generated_previews_and_city_information_include_bilingual_history_read_only(self):
        index = read('game/data/campaigns/index.json')
        paths = [ROOT / 'game/data' / name for name in index['catalogs']]
        session = CampaignSession(paths)
        session.command('new', dict(faction='wei', seed=2026), 0)
        before = session.export_save()
        full = session.view()
        self.assertEqual(len(full['catalog']['scenarios']), 29)
        for chapter in full['catalog']['scenarios']:
            for city in ISLANDS:
                with self.subTest(scenario=chapter['id'], city=city):
                    history = chapter['city_history'][city]
                    self.assertEqual(chapter['initial_owners'][city], 'neutral')
                    self.assertEqual(history['summary_i18n'], self.shared['city_history'][city]['summary_i18n'])
                    preview = session.preview_city(chapter['id'], city)['city']
                    self.assertEqual(preview['owner'], 'neutral')
                    self.assertEqual(preview['owner_name'], history['neutral_label'])
                    self.assertEqual(preview['history']['detail_ja'], history['detail_ja'])
                    self.assertEqual(preview['history']['chronology'], history['chronology'])
                    self.assertEqual(preview['officers'], [])
        for city in ISLANDS:
            self.assertEqual(full['catalog']['city_history'][city]['detail_ja'],
                             self.shared['city_history'][city]['detail_ja'])
        self.assertEqual(session.export_save(), before,
                         'Opening city previews and live city-info metadata cannot mutate save or RNG')

    def test_existing_actual_control_is_never_reset_by_historical_expedition_notes(self):
        for start, city in (((229, 12), 'yizhou'), ((242, 6), 'zhuya')):
            with self.subTest(start=start, city=city):
                game = Campaign(island_catalog(start, occupied=city))
                game.command('new', dict(faction='wei', seed=2026), 0)
                # Isolate historical note transitions from optional treasury jobs.
                for policy in game.state.extension['treasury']['factions'].values():
                    policy.update(enabled=False,gold_floor=0)
                before = game.to_dict()
                for _ in range(3):
                    turn = game.state.turn
                    game.command('end_turn', {}, game.revision)
                    game.command('ai', {'turn': turn}, game.revision)
                self.assertEqual(game.state.cities[city].owner, 'wei')
                self.assertEqual(game.to_dict()['cities'][city], before['cities'][city])
                self.assertEqual(game.to_dict()['officers'], after_monthly_healing(before['officers']))
                self.assertEqual(game.to_dict()['soldiers'], before['soldiers'])


if __name__ == '__main__':
    unittest.main()
