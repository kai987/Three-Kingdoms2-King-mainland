"""Command-backed calendar and travel events, including atomic failure receipts.

Controlled current catalogs retain actual stable people/map IDs. Shortened test
chronology and one test sea route isolate transitions, not historical claims.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, GameError
from remake import civil_staff, domestic, logistics, march_supply
from campaign_fixtures import controlled_catalog


def catalog_with(change):
    data = deepcopy(controlled_catalog().data)
    # Leave both AI factions unable to spend on personnel or reinforcements;
    # these fixtures test the real command/turn pipeline, not AI economics.
    for city in data['initial_city_resources'].values():
        city['gold'] = 0
    for city in data['city_income'].values():
        city.update(gold=0, grain=0, reserves=0)
    for row in data['people']:
        if any(row['person_id'] == initial['person_id'] for initial in data['initial_officers']):
            row['death_year'] = 300
    change(data)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'events.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


def start(catalog, faction='shu', seed=2026):
    game = Campaign(catalog)
    game.command('new', dict(faction=faction, seed=seed), 0)
    return game


def tick(game):
    turn = game.state.turn
    game.command('end_turn', {}, game.revision)
    revision = game.revision
    game.command('ai', dict(turn=turn), revision)
    return turn, revision


def events(game, kind):
    return [row for row in game.state.extension['events']['items'] if row['kind'] == kind]


def sailing_catalog():
    def change(data):
        # Real coastal map nodes; the short, isolated route is test-only.
        mapping = {'xiangyang': 'hepu', 'nanjun': 'yizhou'}
        data['id'] = 'event-sailing-current-rules'
        data['start_month'] = 7
        data['active_cities'] = [mapping.get(city, city) for city in data['active_cities']]
        data['initial_owners'] = {'nanyang': 'wei', 'hepu': 'shu', 'yizhou': 'shu', 'jiangxia': 'wu'}
        for row in data['initial_officers']:
            row['city'] = mapping.get(row['city'], row['city'])
        for faction in data['factions']:
            faction['city'] = mapping.get(faction['city'], faction['city'])
        data['appearance_locations'] = {person: mapping.get(city, city) for person, city in data['appearance_locations'].items()}
        data['initial_city_resources'] = {mapping.get(city, city): values for city, values in data['initial_city_resources'].items()}
        data['city_income'] = {mapping.get(city, city): values for city, values in data['city_income'].items()}
        data['links'] = []
        data['travel_routes'] = []
        data['travel_hazards']['coastal_cities'] = ['hepu', 'yizhou']
        data['exploration_routes'] = [dict(id='explore:hepu:yizhou', **{'from': 'hepu', 'to': 'yizhou'},
            mode='sea', terrain='sea', distance_km=120, land_km=0, sea_km=120, days=4, exploration=True)]
    return catalog_with(change)


class CampaignEventTransitionTests(unittest.TestCase):
    def test_actual_monthly_new_year_and_first_appearance_are_once_and_stable(self):
        appearing = 'san14-candidate-0002'
        def change(data):
            data['start_month'] = 12
            person = next(row for row in data['people'] if row['person_id'] == appearing)
            person.update(birth_year=190, service_year=218, death_year=260)
            data['appearance_locations'][appearing] = 'xiangyang'
            data['appearance_windows'][appearing] = [dict(start=[218, 1], end=[260, 12], city='xiangyang')]
        game = start(catalog_with(change))
        self.assertNotIn(game.catalog.ids[appearing], game.state.officers)
        for _ in range(2):
            tick(game)
            self.assertFalse(events(game, 'new_year'))
            self.assertFalse(events(game, 'officer_appeared'))
        turn, prior_revision = tick(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (218, 1, 1))
        new_year = events(game, 'new_year')
        appearance = events(game, 'officer_appeared')
        self.assertEqual(len(new_year), 1)
        self.assertEqual(new_year[0]['details'], dict(year=218))
        self.assertEqual(len(appearance), 1)
        self.assertEqual(appearance[0]['person_ids'], [appearing])
        self.assertEqual(appearance[0]['city_ids'], ['xiangyang'])
        self.assertEqual(appearance[0]['audience'], 'world')
        self.assertIsNone(game.state.officers[game.catalog.ids[appearing]].faction_id)
        self.assertEqual(appearance[0]['turn'], game.state.turn)
        saved = game.export_save()
        game.command('ai', dict(turn=turn), prior_revision)
        self.assertEqual(game.export_save(), saved)
        loaded = Campaign(game.catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)
        tick(loaded)
        self.assertEqual(events(loaded, 'new_year'), new_year)
        self.assertEqual(events(loaded, 'officer_appeared'), appearance)

    def test_ruler_death_releases_real_troops_and_records_the_actual_successor(self):
        ruler = 'san14-candidate-0952'
        def change(data):
            data['start_month'] = 12
            next(row for row in data['people'] if row['person_id'] == ruler)['death_year'] = 217
            next(row for row in data['initial_officers'] if row['person_id'] == ruler)['resolve_death_year'] = True
        game = start(catalog_with(change))
        ident = game.catalog.ids[ruler]
        original = game.state.officers[ident].troops
        reserves = game.state.cities['xiangyang'].reserves
        successor = max((i for i in game.state.cities['xiangyang'].roster.officer_ids if i != ident),
            key=lambda i: (game.state.officers[i].profile.virtue, -i))
        for _ in range(3):
            tick(game)
        death = events(game, 'officer_death')
        self.assertEqual(events(game, 'succession'), [], 'A provisional player ruler is not yet a committed choice')
        pending=game.state.extension['pending_succession']['shu']
        self.assertIn(successor,pending['candidates'])
        game.command('choose_successor',dict(officer=successor),game.revision)
        succession = events(game, 'succession')
        self.assertEqual(len(death), 1)
        self.assertEqual(death[0]['person_ids'], [ruler])
        self.assertEqual(death[0]['details'], dict(released_troops=original))
        self.assertEqual(death[0]['city_ids'], ['xiangyang'])
        self.assertEqual(death[0]['factions'], ['shu'])
        self.assertFalse(game.state.officers[ident].alive)
        self.assertEqual(game.state.cities['xiangyang'].reserves, reserves + original)
        self.assertEqual(game.state.extension['leaders']['shu'], successor)
        self.assertEqual(len(succession), 1)
        self.assertEqual(succession[0]['person_ids'], [game.state.officers[successor].person_id])
        self.assertEqual(succession[0]['details'], dict(previous=ruler))
        self.assertFalse(events(game, 'faction_ended'))
        tick(game)
        self.assertEqual(events(game, 'officer_death'), death)
        self.assertEqual(events(game, 'succession'), succession)
        game.validate(game.state)

    def test_no_heir_ends_real_faction_and_player_defeat_only_for_that_player(self):
        ruler = 'san14-candidate-0124'
        def change(data):
            data['start_month'] = 12
            next(row for row in data['people'] if row['person_id'] == ruler)['death_year'] = 217
            next(row for row in data['initial_officers'] if row['person_id'] == ruler)['resolve_death_year'] = True
        for player in ('shu', 'wei'):
            with self.subTest(player=player):
                game = start(catalog_with(change), faction=player)
                for _ in range(3):
                    turn, prior_revision = tick(game)
                ended = events(game, 'faction_ended')
                self.assertEqual(len(ended), 1)
                self.assertEqual(ended[0]['factions'], ['wei'])
                self.assertEqual(game.state.cities['nanyang'].owner, 'neutral')
                self.assertIsNone(game.state.extension['leaders']['wei'])
                if player == 'wei':
                    self.assertEqual(game.state.phase, 'finished')
                    self.assertEqual(game.state.extension['outcome'], 'defeat')
                    self.assertEqual(len(events(game, 'campaign_defeat')), 1)
                    self.assertEqual(events(game, 'campaign_defeat')[0]['factions'], ['wei'])
                else:
                    self.assertEqual(game.state.phase, 'city')
                    self.assertFalse(events(game, 'campaign_defeat'))
                saved = game.export_save()
                game.command('ai', dict(turn=turn), prior_revision)
                self.assertEqual(game.export_save(), saved)
                loaded = Campaign(game.catalog)
                loaded.load_save(saved, 0)
                self.assertEqual(loaded.export_save(), saved)

    def test_dated_city_event_orders_new_city_before_parent_and_preserves_resources(self):
        def change(data):
            data['start_month'] = 12
            data['city_foundings'] = {'baxi': dict(year=218, month=1, parent='xiangyang', resource_divisor=4)}
            data['city_income']['baxi'] = dict(gold=0, grain=0, reserves=0)
        game = start(catalog_with(change))
        original = {field: getattr(game.state.cities['xiangyang'], field) for field in ('gold', 'grain', 'reserves')}
        for _ in range(3):
            tick(game)
        found = events(game, 'city_founded')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['city_ids'], ['baxi', 'xiangyang'])
        self.assertEqual(found[0]['details'], dict(parent='xiangyang'))
        self.assertEqual(found[0]['factions'], ['shu'])
        self.assertEqual(game.state.cities['baxi'].owner, 'shu')
        for field, amount in original.items():
            self.assertEqual(getattr(game.state.cities['baxi'], field), amount // 4)
            self.assertEqual(getattr(game.state.cities['xiangyang'], field), amount - amount // 4)
        tick(game)
        self.assertEqual(events(game, 'city_founded'), found)
        game.validate(game.state)

    def sailing(self, troops=None):
        game = start(sailing_catalog())
        ident = game.catalog.ids['san14-candidate-0147']
        if troops is not None:
            game.command('allocate', dict(city='hepu', officer=ident, troops=troops), game.revision)
        game.command('transfer', dict(source='hepu', target='yizhou', officers=[ident], route_mode='explore'), game.revision)
        march = deepcopy(game.state.extension['travel']['marches'][0])
        self.assertEqual(march['arrival_turn'], game.state.turn + 1)
        self.assertFalse(events(game, 'march_weather'))
        self.assertFalse(events(game, 'route_discovered'))
        tick(game)
        self.assertEqual(game.state.phase, 'arrivals')
        return game, ident, march

    def test_weather_discovery_and_friendly_arrival_commit_once_after_saved_departure(self):
        game, ident, march = self.sailing()
        before_rng = deepcopy(game.state.rng)
        old_lost = game.state.soldiers['lost']
        loaded = Campaign(game.catalog)
        loaded.load_save(game.export_save(), 0)
        original_troops = loaded.state.officers[ident].troops
        loaded.command('arrivals', {}, loaded.revision)
        weather = events(loaded, 'march_weather')
        discovery = events(loaded, 'route_discovered')
        arrival = events(loaded, 'march_arrived')
        self.assertEqual(tuple(map(len, (weather, discovery, arrival))), (1, 1, 1))
        self.assertEqual(weather[0]['person_ids'], [loaded.state.officers[ident].person_id])
        self.assertEqual(weather[0]['city_ids'], ['hepu', 'yizhou'])
        self.assertEqual(weather[0]['details']['march_id'], march['id'])
        self.assertEqual(weather[0]['details']['lost'], original_troops - loaded.state.officers[ident].troops)
        self.assertEqual(loaded.state.soldiers['lost'] - old_lost, weather[0]['details']['lost'])
        self.assertTrue(80 <= weather[0]['details']['risks'][0]['loss_percent'] <= 90)
        self.assertEqual(discovery[0]['details'], {'from': 'hepu', 'to': 'yizhou'})
        self.assertEqual(loaded.state.extension['travel']['discovered'], ['explore:hepu:yizhou'])
        self.assertEqual(arrival[0]['details'], dict(march_id=march['id'], officers=1))
        self.assertIn(ident, loaded.state.cities['yizhou'].roster.officer_ids)
        self.assertFalse(loaded.state.extension['travel']['marches'])
        self.assertEqual(loaded.state.rng, before_rng)
        saved, revision = loaded.export_save(), loaded.revision
        with self.assertRaises(GameError):
            loaded.command('arrivals', {}, revision)
        self.assertEqual(loaded.export_save(), saved)
        self.assertEqual(loaded.revision, revision)
        tick(loaded)
        self.assertEqual(events(loaded, 'march_weather'), weather)
        self.assertEqual(events(loaded, 'route_discovered'), discovery)
        self.assertEqual(events(loaded, 'march_arrived'), arrival)

    def test_total_weather_loss_returns_without_discovery_or_arrival(self):
        game, ident, march = self.sailing(troops=1)
        game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.officers[ident].troops, 0)
        self.assertEqual(len(events(game, 'march_weather')), 1)
        self.assertEqual(events(game, 'march_weather')[0]['details']['lost'], 1)
        returned = events(game, 'march_returned')
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned[0]['details'], dict(march_id=march['id'], reason='army_lost'))
        self.assertFalse(events(game, 'route_discovered'))
        self.assertFalse(events(game, 'march_arrived'))
        self.assertFalse(events(game, 'battle_started'))
        self.assertFalse(game.state.extension['travel']['discovered'])
        self.assertIn(ident, game.state.cities['hepu'].roster.officer_ids)
        game.validate(game.state)

    def test_captured_island_starts_real_reverse_voyage_without_discovering_or_teleporting(self):
        game, ident, march = self.sailing()
        # Controlled ownership change after departure: move the existing friendly
        # residents out intact, then use the actual arrival invalidation branch.
        target = game.state.cities['yizhou']
        game.state.cities['hepu'].roster.officer_ids.extend(target.roster.officer_ids)
        target.roster.officer_ids.clear()
        target.owner = 'wei'
        # This controlled capture bypasses the command transaction that normally
        # updates local personnel ownership; do not run candidate/payroll checks.
        logistics.synchronize(game, game.state)
        domestic.synchronize(game, game.state)
        civil_staff.synchronize(game, game.state, checks=False)
        game.validate(game.state)
        before_troops = game.state.officers[ident].troops
        before_rng = deepcopy(game.state.rng)
        game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.officers[ident].troops, before_troops)
        self.assertEqual(game.state.rng.draws,before_rng.draws+1,
            'The new return voyage owns its normal monsoon roll; the original weather is not applied')
        self.assertFalse(events(game, 'march_returned'),'An island changing ownership does not instantly return its officers to the origin')
        returning=game.state.extension['travel']['marches'][0]
        self.assertEqual(returning['id'],march['id'])
        self.assertEqual((returning['status'],returning['reason']),('returning','target_changed'))
        self.assertEqual(returning['mission'],march['mission'])
        self.assertEqual((returning['journey_source'],returning['target']),('yizhou','hepu'))
        self.assertEqual(returning['quote']['path'],['yizhou','hepu'])
        self.assertEqual(returning['quote']['days'],18,'120km at the existing 7.5km/day headwind speed plus two embarkation days')
        self.assertEqual(returning['arrival_turn'],game.state.turn+2)
        self.assertEqual(march_supply.current_city(returning),'yizhou')
        self.assertEqual(returning['supply']['route_days'],0)
        self.assertIn(ident,game._march_ids(game.state),'A returning officer remains physically in transit')
        self.assertEqual(len(returning['history']),1)
        self.assertFalse(any(risk['applied'] for risk in returning['history'][0]['risks']))
        self.assertFalse(any(risk['applied'] for risk in returning['risks']))
        retreat=events(game,'march_retreat')
        self.assertEqual(len(retreat),1)
        self.assertEqual(retreat[0]['details'],dict(unit_kind='march',unit_id=march['id'],
            grain=0,lost=0,shortage_days=0,reason='target_changed'))
        self.assertEqual(retreat[0]['city_ids'],['hepu'])
        self.assertFalse(events(game, 'march_weather'))
        self.assertFalse(events(game, 'route_discovered'))
        self.assertFalse(events(game, 'march_arrived'))
        game.validate(game.state)

    def test_failed_commit_rolls_back_weather_events_losses_and_discovery_then_retries_once(self):
        game, ident, march = self.sailing()
        saved, revision = game.export_save(), game.revision
        validate = game.validate
        staged = []
        def reject(candidate):
            validate(candidate)
            staged.extend(row['kind'] for row in candidate.extension['events']['items'])
            self.assertGreater(candidate.soldiers['lost'], saved['state']['soldiers']['lost'])
            self.assertEqual(candidate.extension['travel']['discovered'], ['explore:hepu:yizhou'])
            raise ValueError('Controlled commit failure after domain validation')
        with patch.object(game, 'validate', reject):
            with self.assertRaisesRegex(ValueError, 'Controlled commit failure'):
                game.command('arrivals', {}, revision)
        self.assertTrue({'march_weather', 'route_discovered', 'march_arrived'} <= set(staged))
        self.assertEqual(game.export_save(), saved)
        self.assertEqual(game.revision, revision)
        game.command('arrivals', {}, revision)
        self.assertEqual(len(events(game, 'march_weather')), 1)
        self.assertEqual(len(events(game, 'route_discovered')), 1)
        self.assertEqual(len(events(game, 'march_arrived')), 1)
        self.assertEqual(events(game, 'march_arrived')[0]['details']['march_id'], march['id'])
        game.validate(game.state)


if __name__ == '__main__':
    unittest.main()
