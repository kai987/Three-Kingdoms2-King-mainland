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
from remake import historical_campaigns as history
from remake.march_core import using_backend


class Headless(Campaign):
    def view(self):
        return {'revision': self.revision}


class HistoricalCampaignTests(unittest.TestCase):
    def setUp(self):
        backend = using_backend('python')
        backend.__enter__()
        self.addCleanup(backend.__exit__, None, None, None)

    def opening(self, scenario, faction, *, start_month=None, group=None):
        path = ROOT / 'game/data/campaigns' / (scenario + '.json')
        if start_month is None and group is None:
            catalog = Catalog(path)
        else:
            data = json.loads(path.read_bytes())
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


if __name__ == '__main__':
    unittest.main()
