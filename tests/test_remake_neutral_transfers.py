"""Neutral transit is movement permission, never ownership or attack reach."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake import civil_staff, domestic, logistics, treasures
from remake.errors import GameError
from remake.march_core import using_backend
from remake.march_supply import estimate
from remake.travel import TravelCampaign
from campaign_fixtures import controlled_catalog
from test_remake_march_core import neutral_transit_config, route_state


CHAIN = ['nanyang', 'nanjun', 'yiyang', 'runan', 'yingchuan']


def synchronize(game, state, **options):
    """Manual fixtures mirror transaction reconciliation without running work."""
    logistics.synchronize(game, state)
    domestic.synchronize(game, state)
    civil_staff.synchronize(game, state, **options)
    treasures.synchronize(game, state)


def transit_catalog():
    data = deepcopy(controlled_catalog().data)
    active = ['nanyang', 'xiangyang', 'nanjun', 'jiangxia', 'yiyang', 'runan', 'yingchuan']
    owners = ['wei', 'shu', 'neutral', 'wu', 'neutral', 'neutral', 'wei']
    data.update(id='controlled-neutral-transit', active_cities=active,
                initial_owners=dict(zip(active, owners)))
    data['initial_city_resources'] = {key: deepcopy(data['initial_resources']) for key in active}
    data['city_income'] = {key: dict(gold=0, grain=0, reserves=0) for key in active}
    pairs = list(zip(CHAIN, CHAIN[1:]))
    # A shorter corridor through an enemy must remain unusable for transfers.
    pairs += [('nanyang', 'xiangyang'), ('xiangyang', 'yingchuan')]
    data['links'] = [list(pair) for pair in pairs]
    data['travel_routes'] = [dict(id=f'transit:{a}:{b}', **{'from': a, 'to': b},
        mode='land', terrain='plain', distance_km=30 if 'xiangyang' in (a, b) else 210,
        land_km=30 if 'xiangyang' in (a, b) else 210, sea_km=0,
        days=1 if 'xiangyang' in (a, b) else 7) for a, b in pairs]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'transit.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class NeutralTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = transit_catalog()

    def new_game(self):
        game = Campaign(self.catalog)
        game.command('new', dict(faction='wei', seed=2026), 0)
        return game

    def restore(self, game, backend):
        saved = game.export_save()
        with using_backend(backend):
            restored = Campaign(game.catalog)
            restored.load_save(saved, 0)
            self.assertEqual(restored.export_save(), saved)
            return restored

    def queue(self, game):
        ident = game.state.cities[CHAIN[0]].roster.officer_ids[0]
        game.command('transfer', dict(source=CHAIN[0], target=CHAIN[-1],
                     officers=[ident], route_mode='land'), game.revision)
        return ident

    def arrive(self, game):
        arrival = game.state.extension['travel']['marches'][0]['arrival_turn']
        while game.state.turn < arrival:
            game._complete_turn(game.state)
        self.assertEqual(game.state.phase, 'arrivals')
        game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.phase, 'city')

    def test_long_neutral_chain_has_no_city_count_limit_in_either_backend(self):
        data = neutral_transit_config()
        travel = TravelCampaign()
        travel.catalog = SimpleNamespace(data=data)
        cities = [dict(id=key, owner='wei' if key in ('s', 't') else
                       'shu' if key == 'enemy' else 'neutral') for key in data['city_coordinates']]
        state = route_state(cities, 4, player='wei')
        expected = ['s', *(f'n{i:02}' for i in range(1, 33)), 't']
        for backend in ('python', 'rust'):
            with self.subTest(backend=backend), using_backend(backend):
                quote = travel._travel_path(state, 's', 't', 'wei', 'land')
                self.assertEqual(quote['path'], expected)
                self.assertEqual((quote['days'], quote['turns'], quote['grain_per_officer']), (33, 4, 165))
                self.assertEqual(travel._travel_view(state)['travel_quotes']['s:t:land'], quote)

    def test_preview_and_execution_cross_multiple_neutral_cities_without_occupying_them(self):
        for backend, alternate in (('python', 'rust'), ('rust', 'python')):
            with self.subTest(backend=backend), using_backend(backend):
                game = self.new_game()
                before = game.export_save()
                quote = game._travel_path(game.state, CHAIN[0], CHAIN[-1], 'wei', 'land')
                bulk = game._travel_view(game.state)['travel_quotes']
                self.assertEqual(quote['path'], CHAIN)
                self.assertEqual((quote['days'], quote['turns'], quote['grain_per_officer']), (28, 3, 20))
                self.assertEqual(bulk[f'{CHAIN[0]}:{CHAIN[-1]}:land'], quote)
                self.assertEqual(bulk[f'{CHAIN[0]}:{CHAIN[1]}:land']['path'], CHAIN[:2])
                self.assertNotIn(f'{CHAIN[0]}:{CHAIN[2]}:land', bulk)
                self.assertNotIn(f'{CHAIN[0]}:{CHAIN[3]}:land', bulk)
                self.assertIsNone(game._travel_path(game.state, CHAIN[0], CHAIN[-1], 'wei', 'land', adjacent=True))
                self.assertEqual(game.export_save(), before)
                neutral_cities = {key: deepcopy(game.state.cities[key]) for key in CHAIN[1:-1]}
                grain = game.state.cities[CHAIN[0]].grain
                rng = deepcopy(game.state.rng)
                ident = self.queue(game)
                self.assertEqual(game.state.cities[CHAIN[0]].grain, grain - estimate(game.state,[ident],quote))
                self.assertEqual(game.state.extension['travel']['marches'][0]['supply']['consumed'],0)
                game = self.restore(game, alternate)
                self.arrive(game)
                self.assertIn(ident, game.state.cities[CHAIN[-1]].roster.officer_ids)
                self.assertNotIn(ident, game.state.cities[CHAIN[0]].roster.officer_ids)
                self.assertFalse(game.state.extension['travel']['marches'])
                self.assertEqual(game.state.rng, rng)
                for key, city in neutral_cities.items():
                    self.assertEqual(game.state.cities[key], city)
                self.restore(game, alternate)

    def test_enemy_intermediate_city_blocks_preview_and_transaction_without_side_effects(self):
        for backend in ('python', 'rust'):
            with self.subTest(backend=backend), using_backend(backend):
                game = self.new_game()
                game.state.cities[CHAIN[2]].owner = 'shu'
                synchronize(game, game.state, checks=False)
                game.validate(game.state)
                before = game.export_save()
                self.assertIsNone(game._travel_path(game.state, CHAIN[0], CHAIN[-1], 'wei', 'land'))
                self.assertNotIn(f'{CHAIN[0]}:{CHAIN[-1]}:land', game._travel_view(game.state)['travel_quotes'])
                with self.assertRaises(GameError):
                    self.queue(game)
                self.assertEqual(game.export_save(), before)
                self.assertFalse(game.state.extension['travel']['marches'])

    def test_neutral_or_enemy_destination_cannot_be_a_transfer_target(self):
        for backend in ('python', 'rust'):
            for owner in ('neutral', 'shu'):
                with self.subTest(backend=backend, owner=owner), using_backend(backend):
                    game = self.new_game()
                    game.state.cities[CHAIN[-1]].owner = owner
                    synchronize(game, game.state, checks=False)
                    game.validate(game.state)
                    before = game.export_save()
                    self.assertIsNone(game._travel_path(game.state, CHAIN[0], CHAIN[-1], 'wei', 'land'))
                    self.assertNotIn(f'{CHAIN[0]}:{CHAIN[-1]}:land', game._travel_view(game.state)['travel_quotes'])
                    with self.assertRaises(GameError):
                        self.queue(game)
                    self.assertEqual(game.export_save(), before)

    def test_intermediate_neutral_or_friendly_changes_remain_passable_after_save_load(self):
        for backend, alternate in (('python', 'rust'), ('rust', 'python')):
            with self.subTest(backend=backend), using_backend(backend):
                game = self.new_game()
                ident = self.queue(game)
                game.state.cities[CHAIN[2]].owner = 'wei'
                synchronize(game, game.state, checks=False)
                game.validate(game.state)
                game = self.restore(game, alternate)
                self.arrive(game)
                self.assertIn(ident, game.state.cities[CHAIN[-1]].roster.officer_ids)
                self.assertEqual(game.state.cities[CHAIN[1]].owner, 'neutral')
                self.assertEqual(game.state.cities[CHAIN[2]].owner, 'wei')

    def test_new_enemy_or_lost_destination_requires_a_real_supplied_return_after_reload(self):
        for backend, alternate in (('python', 'rust'), ('rust', 'python')):
            for key, owner in ((CHAIN[2], 'shu'), (CHAIN[-1], 'neutral'), (CHAIN[-1], 'shu')):
                with self.subTest(backend=backend, city=key, owner=owner), using_backend(backend):
                    game = self.new_game()
                    ident = self.queue(game)
                    troops, rng = game.state.officers[ident].troops, deepcopy(game.state.rng)
                    grain = game.state.cities[CHAIN[0]].grain
                    loaded = game.state.extension['travel']['marches'][0]['supply']['loaded']
                    initial_lost = game.state.soldiers['lost']
                    other_grain = {city:game.state.cities[city].grain for city in CHAIN[1:]}
                    game.state.cities[key].owner = owner
                    synchronize(game, game.state, checks=False)
                    game.validate(game.state)
                    # A changed owner does not invalidate an in-flight save.
                    # A blocked checkpoint or changed destination then starts
                    # physical travel home, with the same daily food service.
                    game = self.restore(game, alternate)
                    self.assertTrue(game.state.extension['travel']['marches'])
                    saw_return = False;consumed = 0
                    for _ in range(12):
                        if not game.state.extension['travel']['marches']:break
                        game._complete_turn(game.state)
                        row = game.state.extension['travel']['marches'][0]
                        if game.state.phase == 'arrivals':
                            game.command('arrivals', {}, game.revision)
                        if game.state.extension['travel']['marches']:
                            row = game.state.extension['travel']['marches'][0]
                        if row['status'] == 'returning':
                            saw_return = True
                            self.assertEqual(row['quote']['path'][-1], CHAIN[0])
                            self.assertEqual(row['quote']['path'][0], row['journey_source'])
                            self.assertGreater(row['quote']['days'], 0)
                            self.assertEqual(row['history'][0]['supply']['closed_tick'],
                                             row['supply']['start_tick'])
                        consumed = row['supply']['consumed'] + sum(
                            trip['supply']['consumed'] for trip in row['history'])
                        if game.state.extension['travel']['marches']:
                            game = self.restore(game, alternate)
                    self.assertTrue(saw_return)
                    self.assertFalse(game.state.extension['travel']['marches'])
                    self.assertIn(ident, game.state.cities[CHAIN[0]].roster.officer_ids)
                    self.assertNotIn(ident, game.state.cities[CHAIN[-1]].roster.officer_ids)
                    self.assertEqual(game.state.soldiers['lost']-initial_lost,
                                     troops-game.state.officers[ident].troops)
                    self.assertEqual(game.state.cities[CHAIN[0]].grain, grain+loaded-consumed)
                    self.assertEqual({city:game.state.cities[city].grain for city in CHAIN[1:]}, other_grain)
                    self.assertEqual(game.state.rng, rng)
                    self.restore(game, alternate)


if __name__ == '__main__':
    unittest.main()
