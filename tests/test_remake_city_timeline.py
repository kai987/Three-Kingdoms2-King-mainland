"""Dated proxy names and city production without rewriting actual campaigns."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))
from remake.campaign import Campaign, Catalog, GameError, digest
from remake.city_economy import income_at, profile_at
from remake.map_presentation import city_names
from remake.session import CampaignSession
from remake.view_transport import ViewTransport
import remake.session as sessions
from build_campaigns import apply_patch as source_patch
from campaign_fixtures import controlled_catalog


def read(path):
    return json.loads((ROOT / path).read_text())


def timeline_catalog(start):
    data = controlled_catalog().data
    active = ['qiao', 'dongjun']
    people = sorted((p for p in data['people']
        if type(p.get('birth_year')) is int and p['birth_year'] <= 200
        and type(p.get('service_year')) is int and p['service_year'] <= 217
        and type(p.get('death_year')) is int and p['death_year'] >= 230),
        key=lambda p: p['runtime_id'])[:6]
    assert len(people) == 6
    data.update(id=f'controlled-city-timeline-{start[0]}-{start[1]:02d}',
                start_year=start[0], start_month=start[1], active_cities=active,
                city_foundings={}, initial_owners=dict(qiao='wei', dongjun='shu'))
    data['factions'] = [dict(id=owner, name=owner, captain=people[index * 3]['name'],
                            city=active[index], color=color)
        for index, (owner, color) in enumerate((('wei', '#ff0000'), ('shu', '#0000ff')))]
    data['initial_officers'] = [dict(person_id=p['person_id'], city=active[index // 3],
                                     troops=300, ruler=index % 3 == 0)
        for index, p in enumerate(people)]
    data['faction_rulers'] = {owner: people[index * 3]['runtime_id']
                            for index, owner in enumerate(('wei', 'shu'))}
    data['appearance_locations'] = {row['person_id']: row['city'] for row in data['initial_officers']}
    data['initial_city_resources'] = dict(qiao=dict(gold=101, grain=205, reserves=0),
                                         dongjun=dict(gold=0, grain=0, reserves=0))
    data['city_income'] = dict(qiao=dict(gold=35, grain=90, reserves=0),
                              dongjun=dict(gold=0, grain=0, reserves=0))
    data['city_scale_rules'] = read('game/config/city-scale-rules.json')
    data['city_profiles']['qiao']['tier'] = 'normal'
    opening_income = income_at(data, 'qiao', *start)
    data['city_profiles']['qiao'] = profile_at(data, 'qiao', *start)
    data['city_profiles']['dongjun'] = profile_at(data, 'dongjun', *start)
    data['city_income']['qiao'] = opening_income
    data['city_history']['qiao'] = read('game/config/campaigns/shared.json')['catalog']['city_history']['qiao']
    data['links'] = [active]
    data['travel_routes'] = [dict(id='controlled:city-timeline', **{'from': active[0], 'to': active[1]},
        mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'timeline.json'
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        return Catalog(path)


def next_turn(game):
    turn = game.state.turn
    game.command('end_turn', {}, game.revision)
    game.command('ai', {'turn': turn}, game.revision)


def dated_events(game, kind):
    return [row for row in game.state.extension['events']['items'] if row['kind'] == kind]


def after_monthly_healing(officers):
    """Only the established +8 capped recovery may change these officers."""
    expected = deepcopy(officers)
    for officer in expected.values():
        if officer['alive']:
            officer['health'] = min(officer['profile']['health_max'], officer['health'] + 8)
    return expected


class CityTimelineTests(unittest.TestCase):
    def new_game(self, start):
        game = Campaign(timeline_catalog(start))
        game.command('new', dict(faction='wei', seed=2026), 0)
        # Isolate the calendar/name test from optional treasury spending.
        for policy in game.state.extension['treasury']['factions'].values():
            policy.update(enabled=False,gold_floor=0)
        return game

    def test_all_29_source_chapters_inherit_names_and_preserve_opening_proxy_notes(self):
        shared = read('game/config/campaigns/shared.json')['catalog']
        entries = read('game/config/campaigns/index.json')['scenarios']
        self.assertEqual(len(entries), 29)
        for entry in entries:
            source = read('game/config/campaigns/' + entry['file'])
            catalog = SimpleNamespace(data=source_patch(shared, source['overrides']))
            with self.subTest(scenario=entry['id']):
                self.assertEqual(city_names(catalog, 218, 12)['qiao'], '小沛')
                self.assertEqual(city_names(catalog, 219, 1)['qiao'], '譙郡')
                self.assertEqual(city_names(catalog, 221, 1)['qiao'], '譙郡')
                rule = catalog.data['city_history']['qiao']
                self.assertIs(rule['announce_name_changes'], True)
                self.assertIn('不同城池', rule['detail'])
                self.assertIn('別の都市', rule['detail_ja'])
                if entry['id'] == 'mainland198-03':
                    self.assertEqual(rule['scenario_opening_proxies'][0]['faction'], 'shu')
                if entry['id'] in ('mainland184-02', 'mainland188-06'):
                    self.assertIn('opening', rule)

    def test_219_real_month_rollover_changes_only_display_name_once(self):
        game = self.new_game((218, 12))
        initial = game.to_dict()
        self.assertEqual(city_names(game.catalog, 218, 12)['qiao'], '小沛')
        for day in (11, 21):
            next_turn(game)
            self.assertEqual(game.state.day, day)
            self.assertEqual(dated_events(game, 'city_renamed'), [])
        next_turn(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (219, 1, 1))
        self.assertEqual(city_names(game.catalog, 219, 1)['qiao'], '譙郡')
        event, = dated_events(game, 'city_renamed')
        self.assertEqual(event['details'], dict(from_name='小沛', to_name='譙郡'))
        self.assertEqual(event['city_ids'], ['qiao'])
        self.assertEqual(event['factions'], ['wei'])
        self.assertEqual(event['audience'], 'world')
        self.assertEqual(dated_events(game, 'city_upgraded'), [])
        self.assertEqual((game.state.cities['qiao'].gold, game.state.cities['qiao'].grain), (136, 295))
        self.assertEqual(game.state.cities['qiao'].owner, initial['cities']['qiao']['owner'])
        self.assertEqual(game.to_dict()['officers'], after_monthly_healing(initial['officers']))
        self.assertEqual(game.to_dict()['soldiers'], initial['soldiers'])
        self.assertEqual(game.to_dict()['rng'], initial['rng'])
        saved = game.export_save()
        twin = Campaign(game.catalog)
        twin.load_save(saved, 0)
        self.assertEqual(twin.export_save(), saved)
        for _ in range(3):
            next_turn(twin)
        self.assertEqual(dated_events(twin, 'city_renamed'), [event])

    def test_221_real_rollover_upgrades_qiao_and_only_adds_current_month_income(self):
        game = self.new_game((220, 12))
        initial = game.to_dict()
        for _ in range(3):
            next_turn(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (221, 1, 1))
        self.assertEqual((game.state.cities['qiao'].gold, game.state.cities['qiao'].grain), (171, 385))
        event, = dated_events(game, 'city_upgraded')
        self.assertEqual(event['city_ids'], ['qiao'])
        self.assertEqual(event['details'], dict(from_tier='normal', to_tier='large',
                                              income=dict(gold=70, grain=180, reserves=0)))
        self.assertEqual(dated_events(game, 'city_renamed'), [])
        self.assertEqual(game.to_dict()['officers'], after_monthly_healing(initial['officers']))
        self.assertEqual(game.to_dict()['soldiers'], initial['soldiers'])
        self.assertEqual(game.to_dict()['rng'], initial['rng'])
        for _ in range(3):
            next_turn(game)
        self.assertEqual(dated_events(game, 'city_upgraded'), [event])
        self.assertEqual((game.state.cities['qiao'].gold, game.state.cities['qiao'].grain), (241, 565))

    def test_late_opening_never_backfills_name_or_size_events(self):
        for start, tier in (((219, 1), 'normal'), ((221, 1), 'large'), ((225, 7), 'large')):
            with self.subTest(start=start):
                game = self.new_game(start)
                self.assertEqual(city_names(game.catalog, *start)['qiao'], '譙郡')
                self.assertEqual(game.catalog.data['city_profiles']['qiao']['tier'], tier)
                self.assertEqual(game.catalog.data['city_profiles']['dongjun']['tier'], 'normal')
                self.assertEqual(dated_events(game, 'city_renamed'), [])
                self.assertEqual(dated_events(game, 'city_upgraded'), [])
                for _ in range(3):
                    next_turn(game)
                self.assertEqual(dated_events(game, 'city_renamed'), [])
                self.assertEqual(dated_events(game, 'city_upgraded'), [])

    def test_compact_session_names_follow_live_date_without_mutating_opening_preview(self):
        catalog = timeline_catalog((218, 12))
        with patch.object(sessions, 'Catalog', return_value=catalog):
            session = CampaignSession([ROOT / 'controlled-timeline.json'])
        session.command('new', dict(faction='wei', seed=2026), 0)
        transport = ViewTransport()
        opening = session.view()
        first = transport.pack(opening, catalog.sha256)
        known = first['catalog_token'] + ':' + first['quote_token']
        for _ in range(3):
            next_turn(session.game)
        saved = session.export_save()
        current = session.view()
        wire = transport.pack(current, catalog.sha256, known)
        self.assertNotIn('static_catalog', wire)
        self.assertEqual(next(c['name'] for c in wire['view']['catalog']['cities'] if c['id'] == 'qiao'), '譙郡')
        self.assertEqual(current['catalog']['scenarios'][0]['city_names']['qiao'], '小沛')
        self.assertEqual(session.export_save(), saved)

    def test_forged_name_event_payload_or_calendar_is_rejected_atomically(self):
        game = self.new_game((218, 12))
        for _ in range(3):
            next_turn(game)
        original, revision = game.export_save(), game.revision
        for field, value in (('day', 11), ('month', 2), ('city_ids', ['dongjun']),
                             ('person_ids', ['san14-candidate-0001']),
                             ('from_name', '歷史小沛改名'), ('to_name', 'wrong')):
            with self.subTest(field=field):
                bad = deepcopy(original)
                event = next(row for row in bad['state']['extension']['events']['items'] if row['kind'] == 'city_renamed')
                if field in ('from_name', 'to_name'):
                    event['details'][field] = value
                else:
                    event[field] = value
                bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
                with self.assertRaises(GameError):
                    game.load_save(bad, revision)
                self.assertEqual(game.export_save(), original)
                self.assertEqual(game.revision, revision)


if __name__ == '__main__':
    unittest.main()
