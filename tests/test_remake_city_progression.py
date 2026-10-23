"""City growth is a dated production change, never an inventory/history reset."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, GameError, digest
from remake.city_economy import income_at, profile_at
from remake.session import CampaignSession
from remake.view_transport import ViewTransport
import remake.session as sessions
from campaign_fixtures import controlled_catalog


def growth_catalog(start=(239, 12)):
    """Two controlled cities and six actual period-eligible identities.

    This isolates the released calendar/AI/transaction services. No artificial
    future dates or incoming receipts are inserted into a live game. The AI
    city has neither money nor monthly income, preventing unrelated recruitment
    and training from obscuring the size-upgrade resource assertions.
    """
    data = controlled_catalog().data
    active = ['danyang', 'nanyang']
    members = sorted((person for person in data['people']
        if type(person.get('birth_year')) is int and person['birth_year'] <= 220
        and type(person.get('service_year')) is int and person['service_year'] <= 239
        and type(person.get('death_year')) is int and person['death_year'] >= 250),
        key=lambda person: person['runtime_id'])[:6]
    assert len(members) == 6
    data.update(id=f'controlled-city-growth-{start[0]}-{start[1]:02d}',
                start_year=start[0], start_month=start[1],
                active_cities=active, city_foundings={},
                initial_owners={'danyang': 'wei', 'nanyang': 'shu'})
    data['factions'] = [dict(id=owner, name=owner, captain=members[index * 3]['name'],
                            city=active[index], color=color)
                       for index, (owner, color) in enumerate((('wei', '#ff0000'), ('shu', '#0000ff')))]
    data['initial_officers'] = [dict(person_id=person['person_id'], city=active[index // 3],
                                     troops=300, ruler=index % 3 == 0)
                                for index, person in enumerate(members)]
    data['faction_rulers'] = {owner: members[index * 3]['runtime_id']
                             for index, owner in enumerate(('wei', 'shu'))}
    data['appearance_locations'] = {row['person_id']: row['city'] for row in data['initial_officers']}
    data['initial_city_resources'] = {'danyang': dict(gold=101, grain=205, reserves=0),
                                      'nanyang': dict(gold=0, grain=0, reserves=0)}
    data['city_income'] = {'danyang': dict(gold=35, grain=90, reserves=0),
                           'nanyang': dict(gold=0, grain=0, reserves=0)}
    opening_income = income_at(data, 'danyang', *start)
    data['city_profiles']['danyang'] = profile_at(data, 'danyang', *start)
    data['city_income']['danyang'] = opening_income
    data['links'] = [['danyang', 'nanyang']]
    data['travel_routes'] = [dict(id='controlled:city-growth', **{'from': 'danyang', 'to': 'nanyang'},
        mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'growth.json'
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        return Catalog(path)


def next_turn(game):
    turn = game.state.turn
    game.command('end_turn', {}, game.revision)
    game.command('ai', {'turn': turn}, game.revision)
    return turn


def upgrades(game):
    return [row for row in game.state.extension['events']['items'] if row['kind'] == 'city_upgraded']


class CityProgressionTests(unittest.TestCase):
    def new_game(self, start=(239, 12)):
        game = Campaign(growth_catalog(start))
        game.command('new', dict(faction='wei', seed=2026), 0)
        return game

    def test_three_real_ten_day_turns_upgrade_once_and_add_only_the_new_months_income(self):
        game = self.new_game()
        initial = game.to_dict()
        self.assertEqual(upgrades(game), [])
        for day in (11, 21):
            previous_turn = next_turn(game)
            self.assertEqual((game.state.year, game.state.month, game.state.day), (239, 12, day))
            self.assertEqual(game.state.cities['danyang'].gold, 101)
            self.assertEqual(game.state.cities['danyang'].grain, 205)
            self.assertEqual(upgrades(game), [])
            saved = game.export_save()
            game.command('ai', dict(turn=previous_turn), -1)
            self.assertEqual(game.export_save(), saved, 'An acknowledged AI receipt is read-only')
        previous_turn = next_turn(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day, game.state.turn), (240, 1, 1, 4))
        city = game.state.cities['danyang']
        self.assertEqual((city.gold, city.grain, city.reserves), (154, 340, 0),
                         'Only 53 gold/135 grain income is added; no opening stock or free soldiers')
        self.assertEqual(city.owner, 'wei', 'Growth must retain actual ownership instead of historical Wu')
        self.assertEqual(game.to_dict()['soldiers'], initial['soldiers'])
        self.assertEqual(game.to_dict()['rng'], initial['rng'])
        self.assertEqual(set(game.state.cities), set(initial['cities']))
        for key, values in initial['cities'].items():
            self.assertEqual(game.to_dict()['cities'][key]['roster'], values['roster'])
        self.assertEqual(set(game.to_dict()['officers']), set(initial['officers']))
        self.assertTrue(all(officer.troops == 300 for officer in game.state.officers.values()))
        event, = upgrades(game)
        self.assertEqual((event['year'], event['month'], event['day']), (240, 1, 1))
        self.assertEqual(event['city_ids'], ['danyang'])
        self.assertEqual(event['factions'], ['wei'])
        self.assertEqual(event['audience'], 'world')
        self.assertEqual(event['details'], dict(from_tier='large', to_tier='giant',
                                               income=dict(gold=53, grain=135, reserves=0)))
        saved, revision = game.export_save(), game.revision
        game.command('ai', dict(turn=previous_turn), revision - 1)
        self.assertEqual(game.export_save(), saved)
        self.assertEqual(game.revision, revision)
        twin = Campaign(game.catalog)
        twin.load_save(saved, 0)
        self.assertEqual(twin.export_save(), saved, 'Reading a save cannot replay a growth event')
        twin.command('ai', dict(turn=previous_turn), -1)
        self.assertEqual(twin.export_save(), saved)
        for _ in range(3):
            next_turn(twin)
        self.assertEqual((twin.state.year, twin.state.month, twin.state.day), (240, 2, 1))
        self.assertEqual(upgrades(twin), [event], 'The next monthly settlement must not repeat the upgrade')
        self.assertEqual((twin.state.cities['danyang'].gold, twin.state.cities['danyang'].grain), (207, 475))

    def test_a_post_240_opening_is_already_giant_and_never_replays_the_upgrade(self):
        for start in ((240, 1), (249, 1)):
            with self.subTest(start=start):
                game = self.new_game(start)
                self.assertEqual(game.catalog.data['city_profiles']['danyang']['tier'], 'giant')
                self.assertEqual(game.catalog.data['city_income']['danyang'], dict(gold=53, grain=135, reserves=0))
                self.assertEqual(upgrades(game), [])
                for _ in range(3):
                    next_turn(game)
                self.assertEqual(upgrades(game), [])
                self.assertEqual((game.state.cities['danyang'].gold, game.state.cities['danyang'].grain), (154, 340))

    def test_compact_session_views_update_size_and_income_with_the_same_cached_catalog(self):
        catalog = growth_catalog()
        with patch.object(sessions, 'Catalog', return_value=catalog):
            session = CampaignSession([ROOT / 'controlled-growth.json'])
        session.command('new', dict(faction='wei', seed=2026), 0)
        transport = ViewTransport()
        opening = session.view()
        first = transport.pack(opening, catalog.sha256)
        self.assertEqual(opening['catalog']['city_profiles']['danyang']['tier'], 'large')
        self.assertEqual(opening['catalog']['city_income']['danyang'], dict(gold=35, grain=90, reserves=0))
        for field in ('city_profiles', 'city_income'):
            self.assertNotIn(field, first['static_catalog'])
        known = first['catalog_token'] + ':' + first['quote_token']
        for _ in range(3):
            next_turn(session.game)
        saved = session.export_save()
        current = session.view()
        wire = transport.pack(current, catalog.sha256, known)
        self.assertNotIn('static_catalog', wire)
        self.assertEqual(wire['catalog_token'], first['catalog_token'])
        self.assertEqual(wire['view']['catalog']['city_profiles']['danyang']['tier'], 'giant')
        self.assertEqual(wire['view']['catalog']['city_income']['danyang'], dict(gold=53, grain=135, reserves=0))
        for field in ('city_profiles', 'city_income'):
            self.assertEqual(wire['view']['catalog'][field], current['catalog'][field])
        self.assertEqual(current['catalog']['scenarios'][0]['city_profiles']['danyang']['tier'], 'large',
                         'An opening scenario preview remains tied to its own starting date')
        self.assertEqual(catalog.data['city_profiles']['danyang']['tier'], 'large')
        self.assertEqual(catalog.data['city_income']['danyang'], dict(gold=35, grain=90, reserves=0))
        self.assertEqual(session.export_save(), saved, 'Full/compact view reads must not modify state or RNG')
        restored = session.load_save(saved, session.revision)
        self.assertEqual(restored['catalog']['city_profiles']['danyang']['tier'], 'giant')
        self.assertEqual(restored['catalog']['city_income']['danyang'], dict(gold=53, grain=135, reserves=0))
        self.assertEqual(session.export_save(), saved)

    def test_forged_growth_event_date_tier_or_income_is_rejected_atomically(self):
        game = self.new_game()
        for _ in range(3):
            next_turn(game)
        original, revision = game.export_save(), game.revision
        for field, value in (('day', 11), ('month', 2), ('to_tier', 'normal'), ('income', dict(gold=999, grain=999, reserves=1))):
            with self.subTest(field=field):
                bad = deepcopy(original)
                event = next(row for row in bad['state']['extension']['events']['items'] if row['kind'] == 'city_upgraded')
                if field in ('day', 'month'):
                    event[field] = value
                else:
                    event['details'][field] = value
                bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
                with self.assertRaises(GameError):
                    game.load_save(bad, revision)
                self.assertEqual(game.export_save(), original)
                self.assertEqual(game.revision, revision)


if __name__ == '__main__':
    unittest.main()
