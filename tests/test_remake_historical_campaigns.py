"""Historically prompted campaigns use ordinary movement and combat."""
from copy import deepcopy
from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake.errors import GameError
from remake import battle_placement, civil_staff, historical_campaigns as history
from remake.historical_chapters import CHAPTERS
from remake.march_core import using_backend
from remake.officers import transfer_officers


class Headless(Campaign):
    def view(self):
        return {'revision': self.revision}


class HistoricalCampaignTests(unittest.TestCase):
    def setUp(self):
        backend = using_backend('python')
        backend.__enter__()
        self.addCleanup(backend.__exit__, None, None, None)

    def opening(self, scenario, faction, *, start_year=None, start_month=None, group=None):
        path = ROOT / 'game/data/campaigns' / (scenario + '.json')
        if start_year is None and start_month is None and group is None:
            catalog = Catalog(path)
        else:
            data = json.loads(path.read_bytes())
            if start_year is not None:
                data['start_year'] = start_year
                deaths = {row['person_id']: row['death_year'] for row in data['people']}
                for field in ('initial_officers', 'initial_free_officers'):
                    data[field] = [row for row in data[field] if deaths[row['person_id']] >= start_year]
                    for row in data[field]:
                        if deaths[row['person_id']] == start_year:
                            row['resolve_death_year'] = True
            if start_month is not None:
                data['start_month'] = start_month
            if group is not None:
                data['main_scenario']['group'] = group
            with TemporaryDirectory() as directory:
                fixture = Path(directory) / 'scenario.json'
                fixture.write_text(json.dumps(data, ensure_ascii=False))
                catalog = Catalog(fixture)
        game = Headless(catalog)
        game.command('new', {'faction': faction, 'seed': 2026, 'difficulty': 'normal'}, 0)
        return game

    def advance(self, game):
        self.assertEqual(game.state.phase, 'city')
        turn = game.state.turn
        game.command('end_turn', {}, game.revision)
        game.command('ai', {'turn': turn}, game.revision)

    def arrivals(self, game):
        if game.state.phase == 'arrivals':
            game.command('arrivals', {}, game.revision)

    def events(self, game, kind):
        return [event for event in game.state.extension['events']['items'] if event['kind'] == kind]

    def resume(self, game):
        saved = game.export_save()
        restored = Headless(game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        return restored

    def assert_unresolved_battle(self, game, attacker, defender, source, target):
        self.assertEqual(game.state.phase, 'battle')
        battle = game.state.battle
        self.assertEqual((battle['attacker'], battle['defender'], battle['source'], battle['target']),
                         (attacker, defender, source, target))
        self.assertEqual(game.state.cities[target].owner, defender)
        self.assertIsNone(battle['outcome'])
        self.assertNotIn(battle['id'], game.state.settled_battles)

    def march_to_battle(self, game, source, target, actor):
        grain_before = game.state.cities[source].grain
        game.command('depart', {'source': source, 'target': target, 'officers': [actor]}, game.revision)
        army, = game.state.extension['travel']['marches']
        self.assertEqual(army['quote']['path'], [source, target])
        self.assertGreater(army['quote']['days'], 0)
        self.assertGreater(army['arrival_turn'], army['departure_turn'])
        self.assertGreater(army['supply']['loaded'], 0)
        self.assertEqual(game.state.cities[source].grain, grain_before - army['supply']['loaded'])
        self.assertIsNone(game.state.battle)
        for _ in range(army['quote']['turns']):
            self.advance(game)
            self.arrivals(game)

    def allocate_from_reserves(self, game, city, officer, target):
        unit = game.state.officers[officer]
        city.reserves -= target - unit.troops
        unit.troops = target

    def test_guandu_calendar_once_and_real_yuan_expedition(self):
        game = self.opening('200-01', 'wei')
        self.assertFalse(self.events(game, history.GUANDU))
        for _ in range(3):
            self.advance(game)
            self.arrivals(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (200, 2, 1))
        event, = self.events(game, history.GUANDU)
        self.assertEqual((event['turn'], event['audience']), (game.state.turn, 'world'))
        self.assertEqual(set(event['factions']), {'yuan_shao', 'wei'})
        game = self.resume(game)
        # The revised 200 opening can produce an independent attack on Shouchun
        # at the rollover. Resolve it through normal commands before testing Yuan.
        if game.state.phase == 'battle':
            battle_id = game.state.battle['id']
            self.assertNotEqual(game.state.battle['attacker'], 'yuan_shao')
            while battle_placement.pending(game.state.battle):
                battle = game.state.battle
                actor = battle_placement.view(game, game.state, battle)['actor']
                point = battle['extended']['tactical']['positions'][str(actor)]
                game.command('battle_place', {'battle_id': battle_id, 'actor': actor, **point}, game.revision)
            game.command('retreat', {'battle_id': battle_id}, game.revision)
            game.command('settle', {'battle_id': battle_id}, game.revision)
            self.arrivals(game)
        self.advance(game)
        army = next(row for row in game.state.extension['travel']['marches']
                    if row['owner'] == 'yuan_shao' and row['kind'] == 'attack'
                    and game.state.cities[row['target']].owner == 'wei')
        self.assertGreater(army['arrival_turn'], army['departure_turn'])
        self.assertTrue(army['officers'])
        self.assertGreater(army['supply']['loaded'], 0)
        self.assertEqual(len(self.events(game, history.GUANDU)), 1)
        self.arrivals(game)
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual((game.state.battle['attacker'], game.state.battle['defender']),
                         ('yuan_shao', 'wei'))
        self.assertEqual(game.state.cities[army['target']].owner, 'wei')
        self.assertNotIn(game.state.battle['id'], game.state.settled_battles)

    def test_chibi_alliance_blocks_player_departure_atomically(self):
        game = self.opening('208-10', 'shu')
        event, = self.events(game, history.ALLIANCE)
        self.assertEqual((event['year'], event['month'], event['day']), (208, 10, 1))
        self.assertEqual(set(event['factions']), {'wu', 'shu'})
        self.assertFalse(self.events(game, history.SOUTH))
        self.assertFalse(game.state.extension['travel']['marches'])
        game = self.resume(game)
        source = game.state.cities['jiangxia']
        actor = source.roster.officer_ids[0]
        before = game.export_save()
        revision = game.revision
        with self.assertRaises(GameError):
            game.command('depart', {'source': source.id, 'target': 'qichun', 'officers': [actor]}, revision)
        self.assertEqual(game.revision, revision)
        self.assertEqual(game.export_save(), before)
        game.command('depart', {'source': source.id, 'target': 'yiyang', 'officers': [actor]}, revision)
        army, = game.state.extension['travel']['marches']
        self.assertEqual((army['owner'], army['target'], army['kind']), ('shu', 'yiyang', 'attack'))

    def test_chibi_cao_south_uses_actual_armies_and_arrival_battle(self):
        game = self.opening('208-10', 'shu')
        self.assertFalse(game.state.extension['travel']['marches'])
        for _ in range(6):
            self.assertFalse(self.events(game, history.SOUTH))
            self.advance(game)
            self.arrivals(game)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (208, 12, 1))
        self.assertEqual(len(self.events(game, history.ALLIANCE)), 1)
        event, = self.events(game, history.SOUTH)
        self.assertEqual((event['turn'], event['audience']), (game.state.turn, 'world'))
        self.assertIsNone(game.state.battle)
        self.advance(game)
        attacks = [row for row in game.state.extension['travel']['marches'] if row['kind'] == 'attack']
        self.assertFalse(any({row['owner'], game.state.cities[row['target']].owner} == {'wu', 'shu'}
                             for row in attacks))
        columns = [row for row in attacks if row['owner'] == 'wei']
        self.assertTrue(columns)
        self.assertTrue(all(game.state.cities[row['target']].owner in {'wu', 'shu'} for row in columns))
        self.assertTrue(all(row['quote']['days'] > 0 and row['supply']['loaded'] > 0 for row in columns))
        self.assertTrue(any(row['target'] == 'jiangxia' for row in columns))
        self.assertEqual(game.state.cities['jiangxia'].owner, 'shu')
        self.assertIsNone(game.state.battle)
        self.arrivals(game)
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual(game.state.battle['target'], 'jiangxia')
        self.assertEqual(game.state.cities['jiangxia'].owner, 'shu')
        self.assertNotIn(game.state.battle['id'], game.state.settled_battles)
        self.resume(game)

    def marriage_fixture(self, player):
        game = self.opening('208-10', player)
        # Keep the opening political situation while advancing the actual calendar.
        for _ in range(41):
            game._complete_turn(game.state)
            game._reconcile_factions(game.state)
            civil_staff.synchronize(game, game.state, monthly=game.state.day == 1)
        self.assertEqual((game.state.year, game.state.month, game.state.day), (209, 11, 21))
        game.validate(game.state)
        return game

    def test_sun_liu_marriage_moves_sun_shangxiang_to_liu_bei_and_survives_reload(self):
        for player in ('shu', 'wu'):
            with self.subTest(player=player):
                game = self.marriage_fixture(player)
                ident = game.catalog.ids['san14-candidate-0565']
                self.assertEqual(game.state.officers[ident].faction_id, 'wu')
                self.assertFalse(self.events(game, history.MARRIAGE))
                self.advance(game)
                self.assertEqual(game.state.phase, 'arrivals')
                before = deepcopy(game.state.officers[ident])
                before.faction_id = 'shu'
                self.arrivals(game)

                self.assertEqual(game.state.officers[ident], before)
                homes = [city.id for city in game.state.cities.values() if ident in city.roster.officer_ids]
                self.assertEqual(homes, ['jiangxia'])
                self.assertEqual(game.state.cities['wujun'].owner, 'wu')
                self.assertEqual(game.state.cities['jiangxia'].owner, 'shu')
                self.assertTrue(history.allied(game.state, 'wu', 'shu'))
                event, = self.events(game, history.MARRIAGE)
                self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                                 (209, 12, 1, 'world'))
                self.assertEqual(event['city_ids'], ['wujun', 'jiangxia'])
                self.assertEqual(event['factions'], ['shu', 'wu'])
                self.assertEqual(event['person_ids'],
                                 ['san14-candidate-0952', 'san14-candidate-0565', 'san14-candidate-0553'])
                self.assertFalse(any('san14-candidate-0565' in row['person_ids']
                                     for row in self.events(game, 'defection')))
                game = self.resume(game)
                before = game.export_save()
                history.process(game, game.state)
                self.assertEqual(game.export_save(), before)

    def test_sun_liu_marriage_requires_historical_alliance_and_available_rosters(self):
        game = self.marriage_fixture('wu')
        game._complete_turn(game.state)
        person = game.catalog.ids['san14-candidate-0565']
        for reason in ('outside month', 'hypothetical', 'no alliance', 'dead',
                       'changed allegiance', 'changed ruler', 'marching', 'pending successor', 'city full'):
            with self.subTest(reason=reason):
                state = deepcopy(game.state)
                if reason == 'outside month':
                    state.month = 11
                elif reason == 'no alliance':
                    state.extension.pop(history.RECEIPTS)
                elif reason == 'dead':
                    state.officers[person].alive = False
                elif reason == 'changed allegiance':
                    state.officers[person].faction_id = 'shu'
                elif reason == 'changed ruler':
                    state.extension['leaders']['wu'] = person
                elif reason == 'pending successor':
                    state.extension['pending_succession']['wu'] = {'candidates': [person]}
                before = game.to_dict(state)
                group = 'if' if reason == 'hypothetical' else game.catalog.data['main_scenario']['group']
                marching = {person} if reason == 'marching' else set()
                capacity = game.catalog.rules.city_officer_capacity if reason == 'city full' else 0
                with patch.dict(game.catalog.data['main_scenario'], group=group), \
                        patch.object(game, '_march_ids', return_value=marching), \
                        patch.object(game, '_city_occupancy', return_value=capacity), \
                        patch.object(state.rng, 'next', side_effect=AssertionError('event used RNG')):
                    history.process(game, state)
                self.assertEqual(game.to_dict(state), before)

    def test_changed_cities_and_if_opening_do_not_trigger(self):
        hypothetical = self.opening('208-10', 'shu', start_month=12, group='if')
        self.assertNotIn(history.RECEIPTS, hypothetical.state.extension)
        self.assertFalse(self.events(hypothetical, history.ALLIANCE))
        game = self.opening('208-10', 'shu', start_month=9)
        # Probe the event service with different live holdings or leaders.
        # The fixture also isolates date/city predicates from other AI rules.
        for reason in ('city changed', 'ruler changed'):
            with self.subTest(reason=reason):
                state = deepcopy(game.state)
                state.month = 10
                state.turn = 4
                if reason == 'city changed':
                    state.cities['nanjun'].owner = 'neutral'
                else:
                    ruler = state.extension['leaders']['wu']
                    state.extension['leaders']['wu'] = next(
                        i for i in state.cities['wujun'].roster.officer_ids if i != ruler)
                before = game.to_dict(state)
                with patch.object(state.rng, 'next', side_effect=AssertionError('event used RNG')):
                    history.process(game, state)
                self.assertEqual(game.to_dict(state), before)

    def test_trigger_itself_preserves_people_troops_resources_and_rng(self):
        game = self.opening('208-10', 'shu', start_month=9)
        state = deepcopy(game.state)
        state.month = 10
        state.turn = 4
        before = game.to_dict(state)
        with patch.object(state.rng, 'next', side_effect=AssertionError('event used RNG')):
            history.process(game, state)
        after = game.to_dict(state)
        for field in ('cities', 'officers', 'soldiers', 'rng', 'battle'):
            self.assertEqual(after[field], before[field])
        self.assertEqual(after['extension']['travel'], before['extension']['travel'])
        self.assertTrue(history.allied(state, 'wu', 'shu'))
        self.assertTrue(history.allied(state, 'shu', 'wu'))
        state.extension['ended_factions'].append('wei')
        self.assertFalse(history.allied(state, 'wu', 'shu'))

    def test_outbound_attack_returns_when_its_target_becomes_ally(self):
        game = self.opening('208-10', 'shu', start_month=9)
        for _ in range(2):
            self.advance(game)
            self.arrivals(game)
        self.assertEqual((game.state.month, game.state.day, game.state.phase), (9, 21, 'city'))
        actor = game.state.cities['jiangxia'].roster.officer_ids[0]
        game.command('depart', {'source': 'jiangxia', 'target': 'qichun', 'officers': [actor]}, game.revision)
        army = next(row for row in game.state.extension['travel']['marches'] if row['owner'] == 'shu')
        self.assertEqual((army['kind'], army['status']), ('attack', 'outbound'))
        self.advance(game)
        self.assertEqual((game.state.month, game.state.day), (10, 1))
        self.arrivals(game)
        self.assertEqual(len(self.events(game, history.ALLIANCE)), 1)
        self.assertIsNone(game.state.battle)
        self.assertEqual(game.state.cities['qichun'].owner, 'wu')
        returning = next(row for row in game.state.extension['travel']['marches'] if row['id'] == army['id'])
        self.assertEqual((returning['kind'], returning['status'], returning['target']),
                         ('transfer', 'returning', 'jiangxia'))
        self.assertEqual(returning['mission']['target'], 'qichun')
        self.assertGreater(returning['quote']['days'], 0)
        self.resume(game)

    def test_tongguan_coalition_and_real_cao_expedition(self):
        game = self.opening('211-07-tongguan', 'ma_teng')
        event, = self.events(game, history.TONGGUAN)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (211, 7, 1, 'world'))
        self.assertEqual(set(event['factions']), {'wei', 'ma_teng', 'han_sui'})
        self.assertEqual(set(event['person_ids']), {'san14-candidate-0521',
                                                    'san14-candidate-0769', 'san14-candidate-0166'})
        self.assertTrue(history.allied(game.state, 'ma_teng', 'han_sui'))
        self.assertTrue(history.allied(game.state, 'han_sui', 'ma_teng'))
        self.assertFalse(history.allied(game.state, 'ma_teng', 'wei'))
        self.assertFalse(game.state.extension['travel']['marches'])
        game = self.resume(game)
        source = game.state.cities['anding']
        before = game.export_save()
        with self.assertRaises(GameError):
            game.command('depart', {'source': source.id, 'target': 'jincheng',
                                    'officers': [source.roster.officer_ids[0]]}, game.revision)
        self.assertEqual(game.export_save(), before)
        self.advance(game)
        army, = [row for row in game.state.extension['travel']['marches']
                 if row['owner'] == 'wei' and row['target'] == 'fengyi' and row['kind'] == 'attack']
        self.assertEqual(army['source'], 'hongnong')
        self.assertGreater(army['arrival_turn'], army['departure_turn'])
        self.assertGreater(army['supply']['loaded'], 0)
        self.assertIsNone(game.state.battle)
        self.arrivals(game)
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual((game.state.battle['attacker'], game.state.battle['defender'],
                          game.state.battle['target']), ('wei', 'ma_teng', 'fengyi'))
        self.assertEqual(game.state.cities['fengyi'].owner, 'ma_teng')
        self.assertNotIn(game.state.battle['id'], game.state.settled_battles)
        self.assertEqual(len(self.events(game, history.TONGGUAN)), 1)
        later = deepcopy(game.state)
        later.month = 10
        self.assertFalse(history.allied(later, 'ma_teng', 'han_sui'))

    def test_tongguan_requires_present_front_and_historical_opening(self):
        game = self.opening('211-07-tongguan', 'ma_teng', start_month=6)
        self.assertFalse(self.events(game, history.TONGGUAN))
        state = deepcopy(game.state)
        state.month = 7
        state.turn = 4
        state.cities['fengyi'].owner = 'neutral'
        before = game.to_dict(state)
        history.process(game, state)
        self.assertEqual(game.to_dict(state), before)
        alternative = self.opening('211-07-tongguan', 'ma_teng', group='if')
        self.assertFalse(self.events(alternative, history.TONGGUAN))
        self.assertFalse(history.allied(alternative.state, 'ma_teng', 'han_sui'))

    def test_jingzhou_break_ends_an_inherited_alliance_once(self):
        actual = self.opening('219-07', 'gongsun')
        self.assertTrue(history.allied(actual.state, 'shu', 'wu'))
        self.assertFalse(self.events(actual, history.ALLIANCE))
        self.assertFalse(self.events(actual, history.ALLIANCE_ENDED))
        self.resume(actual)

        # Start the same forces at the month before the Jingzhou event so
        # unrelated campaigning cannot interrupt the public rollover test.
        game = self.opening('219-07', 'gongsun', start_month=9)
        separated = deepcopy(game.state)
        separated.month = 10
        separated.turn = 4
        for city in ('nanjun', 'yidu', 'badong'):
            separated.cities[city].owner = 'wei'
        history.process(game, separated)
        self.assertTrue(history.allied(separated, 'shu', 'wu'))
        self.assertNotIn(history.ALLIANCE_ENDED, separated.extension[history.RECEIPTS])
        for _ in range(3):
            self.assertTrue(history.allied(game.state, 'shu', 'wu'))
            self.assertFalse(self.events(game, history.ALLIANCE_ENDED))
            self.advance(game)
            self.arrivals(game)
        event, = self.events(game, history.ALLIANCE_ENDED)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (219, 10, 1, 'world'))
        self.assertEqual(set(event['factions']), {'shu', 'wu'})
        self.assertFalse(history.allied(game.state, 'shu', 'wu'))
        self.assertEqual(game.state.cities['nanjun'].owner, 'shu')
        self.assertEqual(game.state.cities['jiangxia'].owner, 'wu')
        game = self.resume(game)
        self.advance(game)
        self.assertEqual(len(self.events(game, history.ALLIANCE_ENDED)), 1)

    def test_yiling_ai_orders_a_real_eastern_attack_without_forcing_a_result(self):
        game = self.opening('221-07', 'wu')
        event, = self.events(game, history.YILING)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (221, 7, 1, 'world'))
        self.assertEqual(set(event['factions']), {'shu', 'wu'})
        self.assertFalse(history.allied(game.state, 'shu', 'wu'))
        self.assertFalse(game.state.extension['travel']['marches'])
        before = set(game.state.settled_battles)
        self.advance(game)
        self.arrivals(game)
        self.assertEqual((game.state.month, game.state.day, game.state.phase), (7, 11, 'city'))
        self.assertFalse(any(row['owner'] == 'shu' and row['kind'] == 'attack'
                             for row in game.state.extension['travel']['marches']))
        self.advance(game)
        army, = [row for row in game.state.extension['travel']['marches']
                 if row['owner'] == 'shu' and row['kind'] == 'attack']
        self.assertEqual((army['source'], army['target']), ('badong', 'yidu'))
        self.assertEqual(army['quote']['modes'], ['river'])
        self.assertGreater(army['arrival_turn'], army['departure_turn'])
        self.assertGreater(army['supply']['loaded'], 0)
        self.assertEqual(set(game.state.settled_battles), before)
        self.assertIsNone(game.state.battle)
        self.arrivals(game)
        self.assertEqual((game.state.day, game.state.phase), (21, 'battle'))
        self.assertEqual((game.state.battle['attacker'], game.state.battle['defender'],
                          game.state.battle['target']), ('shu', 'wu', 'yidu'))
        self.assertEqual(game.state.cities['yidu'].owner, 'wu')
        self.assertNotIn(game.state.battle['id'], game.state.settled_battles)
        self.resume(game)

    def test_yiling_player_can_take_the_existing_river_route_to_battle(self):
        game = self.opening('221-07', 'shu')
        self.assertEqual(len(self.events(game, history.YILING)), 1)
        actor = game.state.cities['badong'].roster.officer_ids[0]
        game.command('depart', {'source': 'badong', 'target': 'yidu',
                                'officers': [actor], 'route_mode': 'river'}, game.revision)
        army, = game.state.extension['travel']['marches']
        self.assertEqual(army['quote']['path'], ['badong', 'yidu'])
        self.assertEqual(army['quote']['modes'], ['river'])
        self.assertGreater(army['quote']['days'], 0)
        self.advance(game)
        self.arrivals(game)
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual((game.state.battle['attacker'], game.state.battle['defender'],
                          game.state.battle['target']), ('shu', 'wu', 'yidu'))
        self.assertEqual(game.state.cities['yidu'].owner, 'wu')
        self.assertNotIn(game.state.battle['id'], game.state.settled_battles)

    def test_surviving_chibi_pact_dissolves_before_yiling_can_depart(self):
        chibi = self.opening('208-10', 'shu')
        # Reuse the Chibi pact receipt in a controlled late-campaign position.
        # Skip its missing years and use Yiling's real forces and road graph.
        with patch.object(history, 'process'):
            game = self.opening('221-07', 'shu')
            self.advance(game)
            self.arrivals(game)
        self.assertEqual(game.state.phase, 'city')
        game.state.extension[history.RECEIPTS] = deepcopy(chibi.state.extension[history.RECEIPTS])
        old_turn = game.state.extension[history.RECEIPTS][history.ALLIANCE]
        actor = game.state.cities['badong'].roster.officer_ids[0]
        order = {'source': 'badong', 'target': 'yidu', 'officers': [actor], 'route_mode': 'river'}
        self.assertTrue(history.allied(game.state, 'shu', 'wu'))
        with self.assertRaises(GameError):
            game.command('depart', order, game.revision)

        turn_date = history._turn_date
        def fixture_date(catalog, turn):
            return turn_date(chibi.catalog if turn == old_turn else catalog, turn)
        with patch.object(history, '_turn_date', side_effect=fixture_date):
            history.process(game, game.state)
            transition = [event['kind'] for event in game.state.extension['events']['items']
                          if event['kind'] in {history.ALLIANCE_ENDED, history.YILING}]
            self.assertEqual(transition, [history.ALLIANCE_ENDED, history.YILING])
            self.assertFalse(history.allied(game.state, 'shu', 'wu'))
            game.command('depart', order, game.revision)
            army = next(row for row in game.state.extension['travel']['marches']
                        if row['owner'] == 'shu' and row['kind'] == 'attack')
            self.assertEqual((army['source'], army['target']), ('badong', 'yidu'))

    def test_hefei_defense_follows_an_actual_march_to_the_proxy(self):
        game = self.opening('215-08', 'wu')
        event, = self.events(game, history.HEFEI)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (215, 8, 1, 'world'))
        self.assertEqual(event['city_ids'], ['danyang', 'lujiang', 'jiujiang'])
        self.assertFalse(self.events(game, history.HEFEI_DEFENSE))
        game = self.resume(game)

        sun_quan = game.catalog.ids['san14-candidate-0553']
        zhang_liao = game.catalog.ids['san14-candidate-0663']
        # With even opening troops, the first ten defenders omit Zhang Liao.
        # Give him an ordinary garrison allocation without creating soldiers.
        self.allocate_from_reserves(game, game.state.cities['jiujiang'], zhang_liao, 999)
        self.march_to_battle(game, 'danyang', 'jiujiang', sun_quan)
        self.assert_unresolved_battle(game, 'wu', 'wei', 'danyang', 'jiujiang')
        defense, = self.events(game, history.HEFEI_DEFENSE)
        self.assertEqual(defense['person_ids'], ['san14-candidate-0663', 'san14-candidate-0553'])
        self.assertEqual(defense['turn'], game.state.turn)
        self.assertEqual(len(self.events(game, history.HEFEI)), 1)
        game = self.resume(game)

        # The player can withdraw and settle through the usual battle flow.
        battle = game.state.battle
        placement = battle_placement.view(game, game.state, battle)
        self.assertEqual(placement['actor'], sun_quan)
        point = battle['extended']['tactical']['positions'][str(sun_quan)]
        game.command('battle_place', {'battle_id': battle['id'], 'actor': sun_quan, **point}, game.revision)
        game.command('retreat', {'battle_id': battle['id']}, game.revision)
        self.assertEqual(game.state.battle['outcome'], 'retreat')
        game.command('settle', {'battle_id': battle['id']}, game.revision)
        self.assertEqual(game.state.cities['jiujiang'].owner, 'wei')
        self.assertIn(battle['id'], game.state.settled_battles)
        self.assertEqual(len(self.events(game, history.HEFEI_DEFENSE)), 1)

    def test_hanzhong_preparation_and_dingjun_battle_are_separate_stages(self):
        preparation = self.opening('217-07', 'shu')
        event, = self.events(preparation, history.HANZHONG_PREPARATION)
        self.assertEqual((event['year'], event['month'], event['day']), (217, 7, 1))
        self.assertFalse(self.events(preparation, history.HANZHONG))
        self.assertFalse(preparation.state.extension['travel']['marches'])
        self.resume(preparation)

        rollover = self.opening('217-07', 'shu', start_month=12)
        for _ in range(3):
            self.assertFalse(self.events(rollover, history.HANZHONG))
            self.advance(rollover)
            self.arrivals(rollover)
        advance, = self.events(rollover, history.HANZHONG)
        self.assertEqual((advance['year'], advance['month'], advance['day']), (218, 1, 1))
        self.assertEqual(len(self.events(rollover, history.HANZHONG_PREPARATION)), 1)

        # Put the actual 217 front at the start of 219, with the two generals
        # deployed to their fronts. Use normal orders and turn processing from there.
        game = self.opening('217-07', 'shu', start_year=219, start_month=1)
        opening, = self.events(game, history.HANZHONG)
        self.assertEqual((opening['year'], opening['month'], opening['day']), (219, 1, 1))
        self.assertFalse(self.events(game, history.DINGJUN))
        huang_zhong = game.catalog.ids['san14-candidate-0271']
        xiahou_yuan = game.catalog.ids['san14-candidate-0114']
        cities = game.state.cities
        transfer_officers(cities['zitong'].roster, cities['baxi'].roster, [huang_zhong])
        transfer_officers(cities['yinping'].roster, cities['hanzhong'].roster, [xiahou_yuan])
        self.allocate_from_reserves(game, cities['hanzhong'], xiahou_yuan, 999)
        self.march_to_battle(game, 'baxi', 'hanzhong', huang_zhong)
        self.assert_unresolved_battle(game, 'shu', 'wei', 'baxi', 'hanzhong')
        clash, = self.events(game, history.DINGJUN)
        self.assertEqual(clash['person_ids'], ['san14-candidate-0271', 'san14-candidate-0114'])
        self.assertEqual(clash['turn'], game.state.turn)
        self.assertTrue(game.state.officers[xiahou_yuan].alive)
        self.resume(game)

    def test_nanzhong_july_opening_allows_a_real_player_campaign(self):
        game = self.opening('225-07', 'shu')
        event, = self.events(game, history.NANZHONG)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (225, 7, 1, 'world'))
        self.assertEqual(event['person_ids'], ['san14-candidate-0440', 'san14-candidate-0845'])
        self.assertFalse(game.state.extension['travel']['marches'])
        game = self.resume(game)

        zhang_yi = game.catalog.ids['san14-candidate-0613']
        self.march_to_battle(game, 'zhuti', 'jianning', zhang_yi)
        self.assert_unresolved_battle(game, 'shu', 'nanman', 'zhuti', 'jianning')
        self.assertEqual(game.state.cities['zangke'].owner, 'nanman')
        self.assertEqual(len(self.events(game, history.NANZHONG)), 1)

    def test_liaodong_wei_ai_reaches_xiangping_with_ordinary_supply(self):
        game = self.opening('238-01', 'gongsun')
        event, = self.events(game, history.LIAODONG)
        self.assertEqual((event['year'], event['month'], event['day'], event['audience']),
                         (238, 1, 1, 'world'))
        self.assertEqual(event['city_ids'], ['liaoxi', 'liaodong'])
        self.assertFalse(game.state.extension['travel']['marches'])
        game = self.resume(game)

        self.advance(game)
        army, = [row for row in game.state.extension['travel']['marches']
                 if row['owner'] == 'wei' and row['target'] == 'liaodong' and row['kind'] == 'attack']
        self.assertEqual(army['quote']['path'], ['liaoxi', 'liaodong'])
        self.assertGreater(army['arrival_turn'], army['departure_turn'])
        self.assertGreater(army['quote']['days'], 0)
        self.assertGreater(army['supply']['loaded'], 0)
        self.assertIsNone(game.state.battle)
        self.arrivals(game)
        for _ in range(army['arrival_turn'] - game.state.turn):
            self.advance(game)
            self.arrivals(game)
        self.assert_unresolved_battle(game, 'wei', 'gongsun', 'liaoxi', 'liaodong')
        self.assertEqual(len(self.events(game, history.LIAODONG)), 1)

    def test_remaining_historical_chapters_emit_once_without_scripted_outcomes(self):
        scenarios = {
            '188-06': 'youzhou_pacification', '190-01': 'dong_zhuo_coalition',
            '191-10': 'sun_jian_jingzhou', '194-06': 'yanzhou_counteroffensive',
            '196-06': 'welcome_han_emperor', '198-03': 'xiapi_expedition',
            '202-06': 'liyang_campaign', '207-09': 'three_visits',
            '212-12': 'yizhou_campaign', '219-07': 'xiangfan',
            '227-02': 'memorial', '234-02': 'wuzhang',
            '249-01': 'gaopingling', '263-05': 'wei_invades_shu',
        }
        self.assertEqual(set(CHAPTERS), {f'historical_{name}' for name in scenarios.values()})
        for scenario, name in scenarios.items():
            with self.subTest(scenario=scenario):
                kind = f'historical_{name}'
                chapter = CHAPTERS[kind]
                player = chapter.leaders[0][0]
                opening_month = int(scenario[-2:])
                late = opening_month != chapter.start[1]
                game = self.opening(scenario, player)
                if late:
                    self.assertFalse(self.events(game, kind))
                    game = self.opening(scenario, player, start_month=chapter.start[1])
                event, = self.events(game, kind)
                self.assertEqual((event['year'], event['month'], event['day']), (*chapter.start, 1))
                self.assertEqual(event['audience'], 'world')
                self.assertEqual(event['person_ids'], list(chapter.people))
                self.assertEqual(event['city_ids'], list(chapter.cities))
                self.assertEqual(event['factions'], [owner for owner, _ in chapter.leaders])
                self.assertEqual(game.state.rng.draws, 0)
                self.assertIsNone(game.state.battle)
                self.assertFalse(game.state.extension['travel']['marches'])
                game = self.resume(game)
                original = game.export_save()
                history.process(game, game.state)
                self.assertEqual(game.export_save(), original)

                _, ruler = chapter.leaders[0]
                city, _ = chapter.holdings[0]
                conditions = ['ruler gone', 'city changed', 'outside window', 'hypothetical']
                if chapter.officers:
                    conditions.append('officer changed sides')
                for condition in conditions:
                    with self.subTest(condition=condition):
                        state = deepcopy(game.state)
                        state.extension[history.RECEIPTS].pop(kind)
                        group = game.catalog.data['main_scenario']['group']
                        if condition == 'ruler gone':
                            state.officers[game.catalog.ids[ruler]].alive = False
                        elif condition == 'officer changed sides':
                            person, _ = chapter.officers[0]
                            state.officers[game.catalog.ids[person]].faction_id = None
                        elif condition == 'city changed':
                            state.cities[city].owner = 'neutral'
                        elif condition == 'outside window':
                            state.year, state.month = chapter.start[0] - 1, 12
                        else:
                            group = 'if'
                        with patch.dict(game.catalog.data['main_scenario'], group=group):
                            history.process(game, state)
                        self.assertNotIn(kind, state.extension[history.RECEIPTS])

    def test_xiangfan_uses_real_xincheng_route_and_keeps_the_sun_liu_pact(self):
        game = self.opening('219-07', 'shu')
        event, = self.events(game, 'historical_xiangfan')
        self.assertIn('xiangyang', event['city_ids'])
        self.assertTrue(history.allied(game.state, 'shu', 'wu'))
        self.assertEqual(history.priority_targets(game.state, 'shu', {'xiangyang', 'yiyang', 'jiangxia'}),
                         ({'xiangyang', 'yiyang'}, 'xiangyang'))
        self.assertNotIn('xiangyang', game._neighbors('nanjun', game.state))
        actor = game.state.cities['xincheng'].roster.officer_ids[0]
        self.march_to_battle(game, 'xincheng', 'xiangyang', actor)
        self.assert_unresolved_battle(game, 'shu', 'wei', 'xincheng', 'xiangyang')
        self.assertTrue(history.allied(game.state, 'shu', 'wu'))
        self.resume(game)

        game = self.opening('219-07', 'shu')
        guan_yu = game.catalog.ids['san14-candidate-0147']
        self.march_to_battle(game, 'nanjun', 'yiyang', guan_yu)
        self.assert_unresolved_battle(game, 'shu', 'wei', 'nanjun', 'yiyang')

    def test_wei_invasion_launches_supplied_ai_armies_without_a_forced_surrender(self):
        game = self.opening('263-05', 'shu')
        self.assertTrue(self.events(game, 'historical_wei_invades_shu'))
        self.assertFalse(game.state.extension['travel']['marches'])
        self.advance(game)
        armies = [army for army in game.state.extension['travel']['marches']
                  if army['owner'] == 'wei' and army['kind'] == 'attack']
        self.assertTrue(armies)
        self.assertTrue(all(army['target'] in ('hanzhong', 'wudu') and army['supply']['loaded'] > 0
                            and army['arrival_turn'] > army['departure_turn'] for army in armies))
        self.assertEqual(game.state.cities['shujun'].owner, 'shu')
        self.assertEqual(game.state.cities['hanzhong'].owner, 'shu')
        self.assertIsNone(game.state.battle)

    def test_xiapi_remains_a_goal_until_a_legal_route_exists(self):
        game = self.opening('198-03', 'wei', start_month=9)
        self.assertTrue(self.events(game, 'historical_xiapi_expedition'))
        adjacent = {target for city in game.state.cities.values() if city.owner == 'wei'
                    for target in game._neighbors(city.id, game.state)}
        self.assertNotIn('xiapi', adjacent)
        self.assertEqual(history.priority_targets(game.state, 'wei', adjacent), (set(), None))
        game.state.cities['donghai'].owner = 'wei'
        self.assertIn('xiapi', game._neighbors('donghai', game.state))
        self.assertEqual(history.priority_targets(game.state, 'wei', {'xiapi'}), ({'xiapi'}, 'xiapi'))

    def test_new_campaigns_require_their_dates_people_and_live_fronts(self):
        cases = (
            ('215-08', 'wu', 7, 8, history.HEFEI, 'jiujiang', 'san14-candidate-0663'),
            ('217-07', 'shu', 6, 7, history.HANZHONG_PREPARATION, 'hanzhong', 'san14-candidate-0827'),
            ('225-07', 'shu', 2, 3, history.NANZHONG, 'zangke', 'san14-candidate-0440'),
            ('238-01', 'wei', 9, 8, history.LIAODONG, 'liaodong', 'san14-candidate-0344'),
        )
        for scenario, faction, initial, event_month, kind, city, person in cases:
            with self.subTest(event=kind):
                game = self.opening(scenario, faction, start_month=initial)
                self.assertFalse(self.events(game, kind))
                for condition in ('changed city', 'unavailable officer'):
                    with self.subTest(condition=condition):
                        state = deepcopy(game.state)
                        state.month = event_month
                        if condition == 'changed city':
                            state.cities[city].owner = 'neutral'
                        else:
                            state.officers[game.catalog.ids[person]].alive = False
                        before = game.to_dict(state)
                        with patch.object(state.rng, 'next', side_effect=AssertionError('event used RNG')):
                            history.process(game, state)
                        self.assertEqual(game.to_dict(state), before)
                alternative = self.opening(scenario, faction, start_month=event_month, group='if')
                self.assertFalse(self.events(alternative, kind))


if __name__ == '__main__':
    unittest.main()
