"""Grain shortage forecasts, real transports and allied relief receipts."""
import unittest

from test_remake_diplomacy import diplomacy_catalog
from remake import command_books, diplomacy, domestic, grain_relief
from remake.campaign import Campaign
from remake.errors import GameError


class GrainReliefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = diplomacy_catalog()

    def start(self):
        game = Campaign(self.catalog)
        game.command('new', dict(faction='shu', seed=2026), 0)
        diplomacy._pool(game.state)['treaties']['shu|wu'] = game.state.turn + 20
        return game

    def forecast(self, game, city):
        return grain_relief.forecasts(game, game.state, 'shu')[city]

    def test_forecast_and_automatic_dispatch_cover_third_turn_before_other_orders(self):
        game = self.start()
        state = game.state
        target = state.cities['yingchuan']
        target.grain = self.forecast(game, target.id).monthly - 1
        self.assertEqual(self.forecast(game, target.id).zero_in, 3)
        domestic.appointments(state, 'shu')['civil'] = 146
        # Jiangxia is closer than Xiangyang but has less grain.
        near = state.cities['jiangxia']
        near.grain = 10000
        state.extension['logistics']['cities'][near.id]['policy']['reserve_officers'] = 0
        self.assertEqual(grain_relief.aid_cities(game, state, 'shu')[target.id]['amount'], 0)
        before = near.grain
        game.command('end_turn', {}, game.revision)
        state = game.state
        row, = state.extension['logistics']['convoys']
        self.assertEqual((row['source'], row['target']), (near.id, target.id))
        self.assertEqual(row['cargo']['grain'], 2)
        self.assertEqual(state.cities[near.id].grain, before - 2 - row['journeys'][0]['supply']['loaded'])
        self.assertEqual(state.extension['command_books']['factions']['shu']['orders'][0]['kind'],
                         'dispatch_transport')
        self.assertEqual(self.forecast(game, target.id).zero_in, None)
        lost = state.soldiers['lost']
        for _ in range(3):
            game._complete_turn(game.state)
            if game.state.phase == 'arrivals':
                game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.soldiers['lost'], lost)
        self.assertEqual(game.state.cities[target.id].grain, 1)

    def request(self, game, city='jiangxia'):
        game.command('diplomacy', dict(action='request_grain', city='xiangyang',
                     envoy=146, target='wu', aid_city=city), game.revision)
        return game.state.extension['events']['items'][-1]['details']

    def test_first_three_accept_and_fourth_requires_friendly_relations_after_load(self):
        game = self.start()
        diplomacy._change_relation(game.state, 'shu', 'wu', -20)
        for number in range(1, 6):
            state = game.state
            command_books.initialize(game, state)
            state.extension['officer_actions'].pop('146', None)
            state.cities['jiangxia'].grain = 0
            predicted = 2 * self.forecast(game, 'jiangxia').monthly
            stocks = sum(city.grain for city in state.cities.values())
            if number == 5:
                diplomacy._change_relation(state, 'shu', 'wu', 65)
            old_score = diplomacy.relation(state, 'shu', 'wu')
            result = self.request(game)
            accepted = number != 4
            self.assertEqual(result, dict(action='request_grain', success=accepted,
                score=min(100, old_score + 5) if accepted else old_score - 5,
                duration=0, grain=predicted, request_number=number,
                aid_reason='accepted' if accepted else 'relations'))
            self.assertEqual(game.state.cities['jiangxia'].grain, predicted if accepted else 0)
            self.assertEqual(sum(city.grain for city in game.state.cities.values()), stocks)
            self.assertEqual(diplomacy._section(game.state, 'grain_aid'), {'shu|wu':number})
            save = game.export_save(compact=True)
            restored = Campaign(game.catalog)
            restored.load_save(save, 0)
            self.assertEqual(restored.export_save(compact=True), save)
            game = restored

    def test_reserved_ally_grain_and_unthreatened_cities_cannot_be_used(self):
        game = self.start()
        state = game.state
        before = game.export_save()
        with self.assertRaises(GameError):
            self.request(game)
        self.assertEqual(game.export_save(), before)
        # The ally keeps its own two-month buffer. A refusal dispatches no grain.
        donor = state.cities['nanjun']
        donor.grain = 2 * grain_relief.forecasts(game, state, 'wu')[donor.id].monthly
        state.extension['logistics']['cities'][donor.id]['policy']['reserve_grain'] = 0
        state.cities['jiangxia'].grain = 0
        donor_stock = donor.grain
        self.assertEqual(self.request(game)['aid_reason'], 'insufficient_surplus')
        self.assertEqual(game.state.cities[donor.id].grain, donor_stock)
        self.assertEqual(game.state.cities['jiangxia'].grain, 0)

    def test_delegated_supply_uses_available_ally_aid_before_paying_at_market(self):
        game = self.start()
        state = game.state
        city = state.cities['jiangxia']
        city.grain = 0
        domestic.appointments(state, 'shu')['civil'] = 146
        gold = city.gold
        expected = 2 * self.forecast(game, city.id).monthly

        game.command('end_turn', {}, game.revision)

        receipt = next(row for row in game.state.extension['events']['items']
                       if row['kind'] == 'diplomacy_result' and row['city_ids'] == [city.id])
        self.assertEqual(receipt['details']['aid_reason'], 'accepted')
        self.assertEqual(game.state.cities[city.id].grain, expected)
        self.assertEqual(game.state.cities[city.id].gold, gold)
        self.assertFalse(any(row['kind'] == 'grain_traded' and row['city_ids'] == [city.id]
                             for row in game.state.extension['events']['items']))

    def test_delegated_supply_buys_after_ally_refuses(self):
        game = self.start()
        state = game.state
        city = state.cities['jiangxia']
        city.grain = 0
        state.cities['nanjun'].grain = 0
        domestic.appointments(state, 'shu')['civil'] = 146
        limit = 2 * self.forecast(game, city.id).monthly
        self.assertEqual(self.request(game)['aid_reason'], 'insufficient_surplus')

        game.command('end_turn', {}, game.revision)

        events = [row for row in game.state.extension['events']['items'] if row['city_ids'] == [city.id]]
        self.assertEqual([row['kind'] for row in events], ['diplomacy_result', 'grain_traded'])
        self.assertTrue(events[-1]['details']['emergency'])
        self.assertGreater(events[-1]['details']['grain'], 0)
        self.assertLessEqual(events[-1]['details']['grain'], limit)
