"""Daily travelling rations are saved inventory, not an instant journey fee."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import civil_staff, domestic, logistics, march_supply
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog
from test_remake_domestic import domestic_catalog


def supply_catalog(*, days=25, transfer=False):
    data = deepcopy((domestic_catalog() if transfer else controlled_catalog()).data)
    data['id'] = 'controlled-daily-supply'
    data['city_income'] = {key: dict(gold=0,grain=0,reserves=0) for key in data['active_cities']}
    for route in data['travel_routes']:
        if {route['from'],route['to']} == {'xiangyang','nanjun'}:
            route.update(days=days,distance_km=days*30,land_km=days*30)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'supply.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


class MarchSupplyTests(unittest.TestCase):
    def game(self, **options):
        game = Campaign(supply_catalog(**options))
        game.command('new',dict(faction='shu',seed=2026),0)
        return game

    def advance(self, game):
        game._complete_turn(game.state)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)

    def restore(self, game):
        saved = game.export_save()
        loaded = Campaign(game.catalog)
        loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        return loaded

    def queue(self, game, *, transfer=False):
        source = game.state.cities['xiangyang']
        ident = source.roster.officer_ids[1]
        game.command('transfer' if transfer else 'depart',dict(source='xiangyang',target='nanjun',
            officers=[ident],route_mode='land'),game.revision)
        return ident, game.state.extension['travel']['marches'][0]

    def test_cumulative_rounding_and_last_partial_period(self):
        game = self.game()
        quote = dict(days=11)
        supply = march_supply.create(game.state,[146],quote)
        expected = march_supply.required_grain(game.state.officers[146].troops,1,11)
        self.assertEqual(supply['loaded'],expected)
        first = march_supply.consume(supply,1,quote,2)
        self.assertEqual(first,march_supply.required_grain(supply['troops'],1,10))
        self.assertEqual(march_supply.consume(supply,1,quote,2),0)
        last = march_supply.consume(supply,1,quote,3)
        self.assertEqual(first+last,expected)
        self.assertEqual((supply['elapsed_days'],supply['remaining']),(11,0))
        self.assertEqual(march_supply.consume(supply,1,quote,1000),0)

    def test_attack_and_transfer_tick_real_days_roundtrip_and_never_rebill_arrival(self):
        for transfer in (False,True):
            with self.subTest(transfer=transfer):
                game = self.game(transfer=transfer)
                before = game.state.cities['xiangyang'].grain
                rng = deepcopy(game.state.rng)
                soldiers = deepcopy(game.state.soldiers)
                ident,row = self.queue(game,transfer=transfer)
                budget = march_supply.estimate(game.state,[ident],row['quote'])
                self.assertEqual(game.state.cities['xiangyang'].grain,before-budget)
                self.assertEqual((row['supply']['loaded'],row['supply']['consumed'],
                                  row['supply']['remaining']),(budget,0,budget))
                for elapsed in (10,20,25):
                    self.advance(game)
                    row = game.state.extension['travel']['marches'][0]
                    self.assertEqual(row['supply']['elapsed_days'],elapsed)
                    self.assertEqual(row['supply']['consumed'],march_supply.required_grain(
                        row['supply']['troops'],1,elapsed))
                    snapshot = game.export_save()
                    self.assertEqual(game._process_march_supply(game.state),0)
                    self.assertEqual(game.export_save(),snapshot)
                    game = self.restore(game)
                grain = sum(c.grain for c in game.state.cities.values())
                self.assertEqual(game.state.rng,rng)
                self.assertEqual(game.state.soldiers,soldiers)
                game.command('arrivals',{},game.revision)
                self.assertEqual(sum(c.grain for c in game.state.cities.values()),grain)
                self.assertFalse(game.state.extension['travel']['marches'])
                if transfer:
                    self.assertIn(ident,game.state.cities['nanjun'].roster.officer_ids)
                else:
                    self.assertEqual(game.state.phase,'battle')

    def test_low_origin_grain_after_departure_cannot_starve_or_charge_enemy(self):
        game = self.game(transfer=True)
        _,row = self.queue(game,transfer=True)
        game.state.cities['xiangyang'].grain = 0
        self.advance(game)
        self.assertEqual(game.state.cities['xiangyang'].grain,0)
        self.assertGreater(row['supply']['consumed'],0)
        game.state.cities['xiangyang'].owner = 'wei'
        game._prune_marches(game.state)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertEqual(game.state.cities['xiangyang'].grain,0)

    def test_cancel_before_route_end_refunds_only_remaining_inventory_once(self):
        game = self.game(transfer=True)
        before = game.state.cities['xiangyang'].grain
        ident,row = self.queue(game,transfer=True)
        self.advance(game)
        spent = row['supply']['consumed']
        game.state.officers[ident].faction_id = None
        game._prune_marches(game.state)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertEqual(game.state.cities['xiangyang'].grain,before-spent)
        game._prune_marches(game.state)
        self.assertEqual(game.state.cities['xiangyang'].grain,before-spent)

    def test_too_little_loading_budget_rejects_atomically(self):
        game = self.game()
        game.state.cities['xiangyang'].grain = 0
        before = game.export_save()
        with self.assertRaises(GameError):
            self.queue(game)
        self.assertEqual(game.export_save(),before)

    def test_supply_save_tampering_rejected_without_changing_current_campaign(self):
        game = self.game(transfer=True)
        self.queue(game,transfer=True)
        saved = game.export_save()
        for key,delta in (('consumed',1),('remaining',1),('troops',1),('elapsed_days',10)):
            with self.subTest(key=key):
                bad = deepcopy(saved)
                bag = bad['state']['extension']['travel']['marches'][0]['supply']
                bag[key] += delta
                bad['checksum'] = digest({k:v for k,v in bad.items() if k != 'checksum'})
                with self.assertRaises((ValueError,GameError)):
                    game.load_save(bad,game.revision)
                self.assertEqual(game.export_save(),saved)

    def test_self_consistent_supply_cursor_rollback_cannot_recreate_eaten_grain(self):
        game = self.game(transfer=True)
        self.queue(game,transfer=True)
        self.advance(game)
        saved = game.export_save()
        bad = deepcopy(saved)
        bag = bad['state']['extension']['travel']['marches'][0]['supply']
        self.assertGreater(bag['consumed'],0)
        bag.update(elapsed_days=0,consumed=0,remaining=bag['loaded'])
        bad['checksum'] = digest({k:v for k,v in bad.items() if k != 'checksum'})
        with self.assertRaises((ValueError,GameError)):
            game.load_save(bad,game.revision)
        self.assertEqual(game.export_save(),saved)


class ConvoySupplyTests(unittest.TestCase):
    def game(self):
        game = Campaign(supply_catalog(transfer=True))
        game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_logistics',dict(city='xiangyang',policy=dict(target_city='nanjun')),game.revision)
        return game

    def dispatch(self, game, grain=200):
        game.command('dispatch_transport',dict(source='xiangyang',target='nanjun',officers=[999],
            cargo=dict(gold=100,grain=grain,reserves=300),route_mode='land'),game.revision)
        return game.state.extension['logistics']['convoys'][0]

    def advance_due(self, game):
        row = game.state.extension['logistics']['convoys'][0]
        while game.state.turn < row['journeys'][-1]['arrival_turn']:
            game._complete_turn(game.state)
        game.state.phase = 'arrivals'
        game.command('arrivals',{},game.revision)

    def test_convoy_loading_cargo_separation_and_return_rations(self):
        game = self.game()
        before = game.state.cities['xiangyang'].grain
        row = self.dispatch(game)
        budget = row['journeys'][0]['supply']['loaded']
        self.assertEqual(game.state.cities['xiangyang'].grain,before-200-budget)
        self.assertEqual(row['cargo']['grain'],200)
        self.assertEqual(row['journeys'][0]['supply']['consumed'],0)
        game.state.cities['nanjun'].owner = 'wei'
        logistics.synchronize(game,game.state)
        domestic.synchronize(game,game.state)
        civil_staff.synchronize(game,game.state,checks=False)
        self.advance_due(game)
        row = game.state.extension['logistics']['convoys'][0]
        returning = row['journeys'][-1]['supply']
        self.assertEqual(row['status'],'returning')
        self.assertEqual(row['journeys'][0]['supply']['remaining'],0)
        self.assertEqual(returning['from_cargo'],returning['loaded'])
        self.assertEqual(row['cargo']['grain'],200-returning['loaded'])
        saved = game.export_save()
        loaded = Campaign(game.catalog); loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        self.advance_due(loaded)
        self.assertFalse(loaded.state.extension['logistics']['convoys'])
        self.assertEqual(loaded.state.cities['xiangyang'].grain,before-budget-returning['loaded'])

    def test_no_grain_for_return_waits_without_free_trip_or_negative_cargo(self):
        game = self.game()
        self.dispatch(game,grain=0)
        game.state.cities['nanjun'].owner = 'wei'
        logistics.synchronize(game,game.state)
        domestic.synchronize(game,game.state)
        civil_staff.synchronize(game,game.state,checks=False)
        self.advance_due(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual((row['status'],row['reason']),('waiting','insufficient_grain'))
        self.assertEqual(len(row['journeys']),1)
        supply,cargo = deepcopy(row['journeys'][0]['supply']),deepcopy(row['cargo'])
        game._complete_turn(game.state)
        game.command('arrivals',{},game.revision)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['cargo'],cargo)
        self.assertEqual(row['journeys'][0]['supply'],supply)
        self.assertEqual(row['cargo']['grain'],0)
        game.validate(game.state)

    def test_convoy_supply_cursor_rollback_is_rejected_atomically(self):
        game = self.game()
        self.dispatch(game)
        game._complete_turn(game.state)
        saved = game.export_save()
        bad = deepcopy(saved)
        bag = bad['state']['extension']['logistics']['convoys'][0]['journeys'][0]['supply']
        self.assertGreater(bag['consumed'],0)
        bag.update(elapsed_days=0,consumed=0,remaining=bag['loaded'])
        bad['checksum'] = digest({k:v for k,v in bad.items() if k != 'checksum'})
        with self.assertRaises((ValueError,GameError)):
            game.load_save(bad,game.revision)
        self.assertEqual(game.export_save(),saved)


if __name__ == '__main__':
    unittest.main()
