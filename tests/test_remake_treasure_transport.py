"""Treasure is physical convoy cargo with bounded, conserved city storage."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, digest
from remake.errors import GameError
from remake import logistics, treasures
from test_remake_logistics import transport_catalog


class TreasureTransportTests(unittest.TestCase):
    def game(self, *, sea=False):
        game = Campaign(transport_catalog(sea=sea))
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('set_logistics', dict(city='xiangyang', policy=dict(target_city='nanjun')),
                     game.revision)
        return game

    def stock(self, game, city, amount):
        current = treasures.count(game.state, city)
        if current > amount:
            treasures.debit(game.state, city, current-amount, reason='spent')
        elif current < amount:
            treasures.credit(game.state, city, amount-current, reason='found')

    def dispatch(self, game, amount=9, *, mode='land', legacy=False):
        cargo = dict(gold=0, grain=0, reserves=0)
        if not legacy:
            cargo['treasure'] = amount
        return game.command('dispatch_transport', dict(source='xiangyang', target='nanjun',
            officers=[999], cargo=cargo, route_mode=mode), game.revision)

    def arrive(self, game):
        turn = min(row['journeys'][-1]['arrival_turn']
                   for row in game.state.extension['logistics']['convoys'])
        while game.state.turn < turn:
            game._complete_turn(game.state)
        game.state.phase = 'arrivals'
        game.command('arrivals', {}, game.revision)

    def next_arrival_check(self, game):
        game._complete_turn(game.state)
        game.state.phase = 'arrivals'
        game.command('arrivals', {}, game.revision)

    def test_legacy_three_field_payload_is_identical_to_explicit_zero_treasure(self):
        legacy, explicit = self.game(), self.game()
        self.dispatch(legacy, legacy=True)
        self.dispatch(explicit, 0)
        self.assertEqual(legacy.export_save(), explicit.export_save())
        self.assertEqual(legacy.state.rng, explicit.state.rng)
        self.assertEqual(legacy.state.extension['logistics']['schema'], 'tk2-logistics-v3')
        self.assertEqual(legacy.state.extension['logistics']['convoys'][0]['cargo']['treasure'], 0)

    def test_real_departure_arrival_and_return_preserve_inventory_and_escort(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        self.stock(game, 'nanjun', 0)
        ledger = deepcopy(game.state.extension['treasury']['ledger'])
        grain = game.state.cities['xiangyang'].grain
        self.dispatch(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual((treasures.count(game.state, 'xiangyang'), treasures.count(game.state, 'nanjun')), (0, 0))
        self.assertEqual(row['cargo']['treasure'], 9)
        self.assertLess(game.state.cities['xiangyang'].grain, grain)
        self.assertIn(999, logistics.marching_ids(game.state))
        saved = game.export_save()
        twin = Campaign(game.catalog)
        twin.load_save(saved, 0)
        self.assertEqual(twin.export_save(), saved)
        self.arrive(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertTrue(row['delivery_done'])
        self.assertEqual(row['cargo']['treasure'], 0)
        self.assertEqual(row['delivered']['treasure'], 9)
        self.assertEqual(treasures.count(game.state, 'nanjun'), 9)
        self.assertEqual(row['status'], 'returning')
        self.assertIn(999, logistics.marching_ids(game.state))
        self.arrive(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertIn(999, game.state.cities['xiangyang'].roster.officer_ids)
        self.assertNotIn(999, game.state.cities['nanjun'].roster.officer_ids)
        self.assertEqual(game.state.extension['treasury']['ledger'], ledger)
        game.validate(game.state)

    def test_full_destination_waits_then_returns_undelivered_treasure_in_real_time(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        self.stock(game, 'nanjun', 99)
        self.dispatch(game)
        self.arrive(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual((row['status'], row['reason']), ('waiting', 'resource_full'))
        self.assertEqual(row['cargo']['treasure'], 9)
        self.assertEqual(treasures.count(game.state, 'nanjun'), 99)
        consumed = row['journeys'][-1]['supply']['consumed']
        self.next_arrival_check(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual((row['status'], row['target']), ('returning', 'xiangyang'))
        self.assertEqual(len(row['journeys']), 2)
        self.assertGreater(row['journeys'][0]['supply']['consumed'], consumed)
        self.assertEqual(treasures.count(game.state, 'xiangyang'), 0)
        self.arrive(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual((treasures.count(game.state, 'xiangyang'), treasures.count(game.state, 'nanjun')), (9, 99))
        game.validate(game.state)

    def test_full_return_origin_keeps_cargo_waiting_without_clamping_or_duplication(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        self.stock(game, 'nanjun', 99)
        self.dispatch(game)
        self.stock(game, 'xiangyang', 99)
        self.arrive(game)
        self.next_arrival_check(game)
        self.arrive(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['status'], 'returning')
        self.assertEqual(row['cargo']['treasure'], 9)
        self.assertEqual(treasures.count(game.state, 'xiangyang'), 99)
        treasures.debit(game.state, 'xiangyang', 9, reason='spent')
        self.next_arrival_check(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(treasures.count(game.state, 'xiangyang'), 99)
        game.validate(game.state)

    def test_weather_uses_existing_single_roll_and_records_only_actual_treasure_loss(self):
        game = self.game(sea=True)
        self.stock(game, 'xiangyang', 99)
        self.stock(game, 'nanjun', 99)
        game.command('set_logistics', dict(city='xiangyang', policy=dict(allow_sea=True)), game.revision)
        before_draws = game.state.rng.draws
        before_loss = game.state.extension['treasury']['ledger']['lost']
        self.dispatch(game, 99, mode='fastest')
        self.assertEqual(game.state.rng.draws, before_draws+1)
        self.arrive(game)
        row = game.state.extension['logistics']['convoys'][0]
        risk = row['journeys'][0]['risks'][0]
        expected = 99*risk['survival_numerator']//risk['survival_denominator']
        self.assertEqual(row['cargo']['treasure'], expected)
        self.assertEqual(game.state.extension['treasury']['ledger']['lost'], before_loss+99-expected)
        saved, rng = game.export_save(), deepcopy(game.state.rng)
        logistics._apply_risks(game, game.state, row)
        self.assertEqual(game.export_save(), saved)
        self.assertEqual(game.state.rng, rng)
        game.validate(game.state)

    def test_extinction_records_lost_cargo_once_without_erasing_city_treasure(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        self.dispatch(game)
        cities = sum(treasures.count(game.state, key) for key in game.state.cities)
        before = game.state.extension['treasury']['ledger']['lost']
        for city in game.state.cities.values():
            if city.owner == 'shu':
                city.owner = 'wei'
        logistics.synchronize(game, game.state)
        treasures.synchronize(game, game.state)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(game.state.extension['treasury']['ledger']['lost'], before+9)
        self.assertEqual(sum(treasures.count(game.state, key) for key in game.state.cities), cities)
        logistics.synchronize(game, game.state)
        self.assertEqual(game.state.extension['treasury']['ledger']['lost'], before+9)
        treasures.validate(game, game.state)

    def test_bad_amounts_unknown_fields_and_forged_cargo_reject_atomically(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        valid = dict(source='xiangyang', target='nanjun', officers=[999], route_mode='land',
                     cargo=dict(gold=0, grain=0, reserves=0, treasure=9))
        for amount in (-1, 10, 100, True, 1.5, '3', None):
            payload = deepcopy(valid)
            payload['cargo']['treasure'] = amount
            saved, revision = game.export_save(), game.revision
            with self.subTest(amount=amount), self.assertRaises(GameError):
                game.command('dispatch_transport', payload, revision)
            self.assertEqual(game.export_save(), saved)
            self.assertEqual(game.revision, revision)
        invalid = deepcopy(valid)
        invalid['cargo']['extra'] = 1
        with self.assertRaises(GameError):
            game.command('dispatch_transport', invalid, game.revision)
        self.dispatch(game)
        saved = game.export_save()
        for field in ('cargo', 'initial_cargo', 'delivered'):
            bad = deepcopy(saved)
            bad['state']['extension']['logistics']['convoys'][0][field]['treasure'] += 1
            bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
            with self.subTest(field=field), self.assertRaises(GameError):
                game.load_save(bad, game.revision)
            self.assertEqual(game.export_save(), saved)

    def test_treasure_view_and_automatic_preview_never_spend_or_autotransport_it(self):
        game = self.game()
        self.stock(game, 'xiangyang', 9)
        self.stock(game, 'nanjun', 0)
        game.command('set_logistics', dict(city='xiangyang', policy=dict(enabled=True)), game.revision)
        before = game.export_save()
        view = logistics.view(game, game.state)
        self.assertEqual(game.export_save(), before)
        city = view['cities']['xiangyang']
        self.assertEqual(city['treasure_transport']['available'], 9)
        target = next(row for row in city['treasure_transport']['targets'] if row['target'] == 'nanjun')
        self.assertTrue(target['can_dispatch'])
        self.assertEqual(target['max_treasure'], 9)
        self.assertEqual(city['preview']['cargo']['treasure'], 0)
        self.assertTrue(logistics.auto_dispatch_city(game, game.state, 'xiangyang'))
        self.assertEqual(game.state.extension['logistics']['convoys'][0]['cargo']['treasure'], 0)
        self.assertEqual(treasures.count(game.state, 'xiangyang'), 9)


if __name__ == '__main__':
    unittest.main()
