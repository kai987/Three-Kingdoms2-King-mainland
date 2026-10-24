"""River travel uses current, actual ten-day supply and ordinary saved orders."""
from copy import deepcopy
import json
from math import ceil
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, Catalog, canonical
from remake import logistics
from remake.march_core import using_backend
from remake.route_hazards import evaluate_leg
from test_remake_domestic import domestic_catalog
from test_remake_march_core import river_config


def river_catalog(*, only=False):
    data = deepcopy(domestic_catalog().data)
    data['id'] = 'controlled-river-current'
    data['travel_rules'].update(deepcopy(river_config()['travel_rules']))
    for row in data['travel_routes']:
        if {row['from'], row['to']} == {'xiangyang', 'nanjun'}:
            row.update(distance_km=1200, land_km=1200, days=40)
    river = deepcopy(river_config()['travel_routes'][0])
    river.update(id='controlled:xiangyang:nanjun:river', **{'from': 'xiangyang', 'to': 'nanjun'})
    for segment in river['river_segments']:
        segment['downstream_from'] = 'nanjun'
    if only:
        data['travel_routes'] = [row for row in data['travel_routes']
            if {row['from'], row['to']} != {'xiangyang', 'nanjun'}]
    data['travel_routes'].append(river)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'river.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class RiverRouteTests(unittest.TestCase):
    def game(self, *, only=False, player='shu'):
        game = Campaign(river_catalog(only=only))
        game.command('new', dict(faction=player, seed=2026), 0)
        return game

    def reload(self, game):
        saved = game.export_save()
        loaded = Campaign(game.catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(canonical(loaded.export_save()), canonical(saved))
        return loaded

    def advance_ai_turn(self, game):
        turn = game.state.turn
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=turn), game.revision)
        self.assertEqual(game.state.turn, turn + 1)
        game.validate(game.state)

    def test_both_reaches_direction_access_and_embark_are_constant_in_all_months(self):
        data = river_config()
        raw = data['travel_routes'][0]
        before = deepcopy(raw)
        for month in range(1, 13):
            for source, target, days, flow, speeds in (
                    ('s', 't', 28, 'upstream', [20, 22.5]),
                    ('t', 's', 16, 'downstream', [50, 35])):
                quote = evaluate_leg(data, raw, source, target, month)
                self.assertEqual(quote['days'], days)
                self.assertEqual(quote['flow'], flow)
                self.assertIsNone(quote['speed_km_per_day'])
                self.assertEqual([r['speed_km_per_day'] for r in quote['river_segments']], speeds)
                self.assertEqual(quote['land_access_days'], 2)
                self.assertEqual(quote['embark_days'], 1)
                self.assertIsNone(quote['hazard'])
        self.assertEqual(raw, before)

    def test_playable_jiangxia_changsha_has_distinct_land_and_surveyed_river_routes(self):
        data = Catalog(ROOT / 'game/data/campaigns/217-07.json').data
        direct = [row for row in data['travel_routes']
            if {row['from'], row['to']} == {'jiangxia', 'changsha'}]
        self.assertEqual(sorted(row['mode'] for row in direct), ['land', 'river'])
        raw = next(row for row in direct if row['mode'] == 'river')
        self.assertEqual(raw['river_segments'][0]['speed_key'], 'yangtze')
        self.assertTrue(all(r['speed_key']=='xiang' for r in raw['river_segments'][1:]))
        self.assertTrue(all(r['downstream_from'] == 'changsha' for r in raw['river_segments']))
        self.assertAlmostEqual(sum(r['distance_km'] for r in raw['river_segments']), raw['river_km'], places=1)
        for source, target, flow in (('jiangxia', 'changsha', 'upstream'),
                                     ('changsha', 'jiangxia', 'downstream')):
            expected = (ceil(raw['land_km'] / data['travel_rules']['speeds']['plain'])
                + ceil(sum(r['distance_km'] / data['travel_rules']['river_speeds'][r['speed_key']][flow]
                    for r in raw['river_segments'])) + data['travel_rules']['river_embark_days'])
            for month in range(1, 13):
                quote = evaluate_leg(data, raw, source, target, month)
                self.assertEqual(quote['days'], expected)
                self.assertEqual(quote['flow'], flow)
                self.assertIsNone(quote['hazard'])

    def test_land_and_sea_modes_never_take_river_but_fastest_can(self):
        game = self.game(only=True)
        before = game.export_save()
        for mode in ('land', 'sea', 'explore'):
            self.assertIsNone(game._travel_path(game.state, 'xiangyang', 'nanjun', 'shu', mode))
        river = game._travel_path(game.state, 'xiangyang', 'nanjun', 'shu', 'river')
        fastest = game._travel_path(game.state, 'xiangyang', 'nanjun', 'shu', 'fastest')
        self.assertEqual(river, fastest)
        self.assertEqual(river['modes'], ['river'])
        quotes = game._travel_view(game.state)['travel_quotes']
        self.assertEqual(quotes['xiangyang:nanjun:river'], river)
        self.assertNotIn('xiangyang:nanjun:land', quotes)
        self.assertNotIn('xiangyang:nanjun:sea', quotes)
        self.assertEqual(game.export_save(), before)

    def test_river_transfer_spends_daily_grain_without_storm_or_rng_and_survives_three_ai_turns(self):
        game = self.game()
        ident = 999
        troops = game.state.officers[ident].troops
        rng = game.state.rng.draws
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[ident],
            route_mode='river'), game.revision)
        march = game.state.extension['travel']['marches'][0]
        self.assertEqual(march['quote']['days'], 28)
        self.assertEqual(march['risks'], [])
        self.assertEqual(game.state.rng.draws, rng)
        for tick in range(1, 4):
            self.advance_ai_turn(game)
            game = self.reload(game)
            march = game.state.extension['travel']['marches'][0]
            self.assertEqual(march['supply']['route_days'], min(28, tick * 10))
            self.assertGreater(march['supply']['consumed'], 0)
            self.assertFalse(march['supply']['starvation'])
            self.assertEqual(march['risks'], [])
            self.assertEqual(game.state.officers[ident].troops, troops)
        game.command('arrivals', {}, game.revision)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertIn(ident, game.state.cities['nanjun'].roster.officer_ids)
        self.reload(game)

    def test_safe_automatic_transport_uses_inland_water_when_ocean_is_disabled(self):
        for player in ('shu', 'wei'):
            game = self.game(player=player)
            policy = dict(enabled=True, target_city='nanjun', allow_sea=False,
                allow_special=False, target_gold=1500, target_grain=4500,
                target_reserves=1500, target_officers=0)
            if player == 'shu':
                game.command('set_logistics', dict(city='xiangyang', policy=policy), game.revision)
            else:
                # AI and player pass the same city policy into the same service;
                # this controlled city is a front, so do not replace it with the
                # ordinary AI rear-city target heuristic during this unit case.
                logistics._pool(game.state)['cities']['xiangyang']['policy'].update(policy)
            source, target = (game.state.cities[key] for key in ('xiangyang', 'nanjun'))
            selected = logistics._safe_quote(game, game.state, source, target,
                logistics._pool(game.state)['cities']['xiangyang']['policy'])
            self.assertEqual(selected[1]['modes'], ['river'])
            self.assertEqual(selected[1]['days'], 28)
            rng = game.state.rng.draws
            self.assertTrue(logistics.auto_dispatch_city(game, game.state, 'xiangyang'))
            convoy = game.state.extension['logistics']['convoys'][0]
            self.assertEqual(convoy['journeys'][0]['quote']['modes'], ['river'])
            self.assertEqual(convoy['journeys'][0]['risks'], [])
            self.assertEqual(game.state.rng.draws, rng)
            game = self.reload(game)
            while not game.state.extension['logistics']['convoys'][0]['delivery_done']:
                game._complete_turn(game.state)
                game.state.phase = 'arrivals'
                game.command('arrivals', {}, game.revision)
                game = self.reload(game)
            convoy = game.state.extension['logistics']['convoys'][0]
            self.assertEqual(convoy['status'], 'returning')
            returning = convoy['journeys'][-1]
            self.assertEqual(returning['quote']['days'], 16)
            self.assertEqual(returning['quote']['routes'][0]['flow'], 'downstream')
            self.assertEqual(returning['risks'], [])
            for _ in range(2):
                game._complete_turn(game.state)
                game.state.phase = 'arrivals'
                game.command('arrivals', {}, game.revision)
                game = self.reload(game)
            self.assertFalse(game.state.extension['logistics']['convoys'])

    def test_saved_river_speed_flow_or_mode_tampering_is_rejected(self):
        game = self.game()
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[999],
            route_mode='river'), game.revision)
        for field, value in (('flow', 'downstream'), ('speed_km_per_day', 120)):
            bad = deepcopy(game.state)
            bad.extension['travel']['marches'][0]['quote']['routes'][0][field] = value
            with self.assertRaises(ValueError):
                game.validate(bad)
        bad = deepcopy(game.state)
        row = bad.extension['travel']['marches'][0]
        row['mode'] = row['mission']['mode'] = 'land'
        with self.assertRaisesRegex(ValueError, 'land march uses water'):
            game.validate(bad)


if __name__ == '__main__':
    unittest.main()
