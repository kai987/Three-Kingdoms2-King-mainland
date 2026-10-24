"""Convoys use actual travel, arrival, resource and save transactions."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import civil_staff, domestic, equipment, logistics, treasures
from remake.officers import YearState, initialize_officer, year_state
from test_remake_domestic import domestic_catalog


def transport_catalog(*, sea=False, long=False):
    data = deepcopy(domestic_catalog().data)
    data['id'] = 'controlled-transport'
    for row in data['travel_routes']:
        if {row['from'], row['to']} == {'xiangyang', 'nanjun'}:
            if sea:
                row.update(mode='sea', terrain='sea', distance_km=300, land_km=0, sea_km=300, days=10)
            elif long:
                row.update(distance_km=900, land_km=900, days=30)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'transport.json'; p.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(p)


class LogisticsTests(unittest.TestCase):
    def game(self, **options):
        game = Campaign(transport_catalog(**options))
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('set_logistics', dict(city='xiangyang', policy=dict(target_city='nanjun')), game.revision)
        return game

    def dispatch(self, game, *, ids=None, mode='land', cargo=None):
        if ids is None: ids = [999]
        cargo = cargo or dict(gold=100, grain=200, reserves=300)
        return game.command('dispatch_transport', dict(source='xiangyang', target='nanjun', officers=ids,
            cargo=cargo, route_mode=mode), game.revision)

    def advance_due(self, game):
        target = min(row['journeys'][-1]['arrival_turn'] for row in game.state.extension['logistics']['convoys'])
        while game.state.turn < target:
            game._complete_turn(game.state)
        game.state.phase = 'arrivals'
        game.command('arrivals', {}, game.revision)

    def sync(self, game):
        civil_staff.synchronize(game, game.state, checks=False)
        logistics.synchronize(game, game.state)
        domestic.synchronize(game, game.state)
        treasures.synchronize(game, game.state)
        if 'equipment' in game.state.extension:
            equipment.synchronize(game, game.state)

    def fill(self, game, city_id, count):
        city = game.state.cities[city_id]
        for ident, row in game.catalog.by_id.items():
            if len(city.roster.officer_ids) >= count: break
            if ident in game.state.officers: continue
            definition = game.catalog.definitions[row['person_id']]
            if year_state(definition, game.state.year) != YearState.AVAILABLE: continue
            officer = initialize_officer(definition, ident, game.catalog.profiles[ident], year=game.state.year,
                faction_id=city.owner, loyalty=80, troops=0, rules=game.catalog.rules)
            game.state.officers[ident] = officer
            city.roster.officer_ids.append(ident)
        self.assertEqual(len(city.roster.officer_ids), count)
        self.sync(game); game.validate(game.state)

    def fails(self, game, payload, kind='dispatch_transport'):
        before, cursor = game.export_save(), game.revision
        with self.assertRaises((GameError, ValueError)):
            game.command(kind, payload, cursor)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.revision, cursor)

    def test_actual_dispatch_arrival_cargo_and_personnel_are_conserved(self):
        game = self.game()
        source = game.state.cities['xiangyang']; target = game.state.cities['nanjun']
        before = dict(gold=source.gold, grain=source.grain, reserves=source.reserves)
        destination = dict(gold=target.gold, grain=target.grain, reserves=target.reserves)
        self.dispatch(game)
        row = game.state.extension['logistics']['convoys'][0]
        source, target = game.state.cities['xiangyang'], game.state.cities['nanjun']
        self.assertEqual(source.gold, before['gold'] - 100)
        self.assertEqual(source.reserves, before['reserves'] - 300)
        self.assertEqual(logistics.in_transit_reserves(game.state), 300)
        self.assertEqual(target.gold, destination['gold'])
        self.assertIn(999, source.roster.officer_ids); self.assertNotIn(999, target.roster.officer_ids)
        self.assertIn(999, game._march_ids(game.state))
        self.assertTrue(source.action_used)
        snapshot = game.export_save()
        for _ in range(3): logistics.view(game, game.state)
        self.assertEqual(snapshot, game.export_save())
        loaded = Campaign(game.catalog); loaded.load_save(snapshot, 0)
        self.assertEqual(loaded.export_save(), snapshot)
        self.advance_due(game)
        target = game.state.cities['nanjun']
        self.assertEqual(target.gold, destination['gold'] + 100)
        row=game.state.extension['logistics']['convoys'][0]
        return_food=sum(r['grain'] for r in row['journeys'][-1]['supply']['refills'] if r['kind']=='city')
        self.assertEqual(target.grain, destination['grain'] + 200-return_food)
        self.assertEqual(target.reserves, destination['reserves'] + 300)
        self.assertTrue(row['delivery_done']);self.assertEqual(row['status'],'returning')
        self.assertNotIn(999,target.roster.officer_ids)
        self.assertIn(999,game.state.cities['xiangyang'].roster.officer_ids)
        self.assertIn(999,logistics.marching_ids(game.state))
        self.advance_due(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertFalse(logistics.marching_ids(game.state))
        self.assertIn('city:nanjun', game.state.extension['logistics']['receipts'])
        game.validate(game.state)

    def test_returning_escorts_never_count_as_permanent_front_administrators(self):
        game = self.game()
        target = game.state.cities['nanjun']
        before = civil_staff._effective_count(game.state, target)
        self.dispatch(game)
        self.assertEqual(civil_staff._effective_count(game.state, game.state.cities['nanjun']), before)
        game.state.cities['nanjun'].owner = 'wei'
        self.assertEqual(civil_staff._effective_count(game.state, game.state.cities['nanjun']), before)
        # More than three turns away must not suppress a current staff shortage.
        data = deepcopy(transport_catalog(long=True).data)
        data['id'] = 'controlled-inbound-four-turns'
        next(r for r in data['travel_routes'] if r['from'] == 'xiangyang' and r['to'] == 'nanjun').update(distance_km=1500, land_km=1500, days=50)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'long.json'; p.write_text(json.dumps(data))
            game = Campaign(Catalog(p)); game.command('new', dict(faction='shu', seed=2026), 0)
        before = civil_staff._effective_count(game.state, game.state.cities['nanjun'])
        self.dispatch(game)
        self.assertGreater(game.state.extension['logistics']['convoys'][0]['journeys'][0]['arrival_turn'] - game.state.turn, 3)
        self.assertEqual(civil_staff._effective_count(game.state, game.state.cities['nanjun']), before)

    def test_arrival_training_counts_delivered_reserves_without_temporary_escort_troops(self):
        game = self.game()
        game.state.extension['domestic']['cities']['xiangyang']['morale'] = 90
        game.state.extension['domestic']['cities']['nanjun']['morale'] = 50
        target = game.state.cities['nanjun']
        before = domestic._garrison_troops(game, game.state, target)
        self.dispatch(game)
        expected = (before * 50 + 300 * 90) // (before + 300)
        self.advance_due(game)
        self.assertEqual(domestic.morale(game.state, 'nanjun'), expected)
        game.validate(game.state)

    def test_source_capture_does_not_delete_cargo_when_destination_stays_friendly(self):
        game = self.game()
        target = deepcopy(game.state.cities['nanjun'])
        self.dispatch(game)
        # Model surviving residents evacuating; only the convoy remains in the
        # captured source roster until the actual arrival moves its escort.
        source = game.state.cities['xiangyang']
        evacuated = [i for i in source.roster.officer_ids if i != 999]
        game.state.cities['nanjun'].roster.officer_ids.extend(evacuated)
        source.roster.officer_ids[:] = [999]
        game.state.cities['xiangyang'].owner = 'wei'
        self.sync(game)
        self.assertEqual(logistics.in_transit_reserves(game.state), 300)
        self.advance_due(game)
        self.assertEqual(game.state.cities['nanjun'].gold, target.gold + 100)
        self.assertEqual(game.state.cities['nanjun'].reserves, target.reserves + 300)
        self.assertIn(999, game.state.cities['nanjun'].roster.officer_ids)
        # The refuge is the actual unloading node; there is no zero-day queue.
        self.assertFalse(game.state.extension['logistics']['convoys'])

    def test_manual_limits_and_malformed_requests_are_atomic(self):
        game = self.game()
        valid = dict(source='xiangyang', target='nanjun', officers=[999],
                     cargo=dict(gold=100, grain=200, reserves=300), route_mode='land')
        for patch in (dict(source=[]), dict(target={}), dict(officers=[True]), dict(officers=['999']),
                      dict(officers=[999, 999]), dict(route_mode=[]), dict(cargo=dict(gold=-1, grain=0, reserves=0)),
                      dict(cargo=dict(gold=501, grain=0, reserves=0)), dict(officers=[951, 146, 999])):
            self.fails(game, dict(valid, **patch))
        self.fails(game, dict(city='xiangyang', policy=dict(target_city=[])), kind='set_logistics')
        self.dispatch(game)
        self.fails(game, valid)
        self.fails(game, dict(city='xiangyang', civil=999), kind='set_domestic')
        self.fails(game, dict(city='xiangyang', officer=999, troops=100), kind='allocate')

    def test_safe_search_uses_longer_land_detour_without_mutating_catalog(self):
        game = Campaign(Catalog(ROOT / 'game/data/campaigns/217-07.json'))
        game.command('new', dict(faction='shu', seed=2026), 0)
        # Neutral nodes are legal transit points, while the final city is friendly.
        for city in game.state.cities.values(): city.owner = 'shu'
        before = deepcopy(game.catalog.data)
        direct = game._travel_path(game.state, 'yinping', 'shujun', 'shu', 'special')
        safe = logistics._safe_path(game, game.state, 'yinping', 'shujun', 'shu', 'land',
                                   dict(allow_sea=False, allow_special=False))
        self.assertIsNotNone(direct); self.assertIsNotNone(safe)
        self.assertGreater(len(safe['path']), 2)
        self.assertFalse(any(leg.get('hazard') for leg in safe['routes']))
        self.assertEqual(game.catalog.data, before)

    def test_marching_source_officers_do_not_satisfy_actual_guard_retention(self):
        game = self.game(long=True)
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[146, 999], route_mode='land'), game.revision)
        game._complete_turn(game.state)
        self.assertEqual(len(game.state.cities['xiangyang'].roster.officer_ids), 4)
        proposed, reason = logistics.preview(game, game.state, 'xiangyang')
        self.assertIsNone(proposed); self.assertEqual(reason, 'no_spare_officer')
        self.fails(game, dict(source='xiangyang', target='nanjun', officers=[439], route_mode='land',
                             cargo=dict(gold=0, grain=0, reserves=0)))

    def test_personnel_only_automatic_support_uses_permanent_transfer_not_an_empty_convoy(self):
        game=self.game()
        game.command('set_logistics',dict(city='xiangyang',policy=dict(enabled=True,
            target_gold=0,target_grain=0,target_reserves=0,target_officers=1)),game.revision)
        proposed,reason=logistics.preview(game,game.state,'xiangyang')
        self.assertIsNone(proposed);self.assertEqual(reason,'no_surplus')
        self.assertTrue(logistics.auto_dispatch_city(game,game.state,'xiangyang'))
        self.assertFalse(game.state.extension['logistics']['convoys'])
        rows=game.state.extension['travel']['marches']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'transfer')
        self.assertEqual(rows[0]['target'],'nanjun')
        self.assertEqual(len(rows[0]['officers']),1)
        self.assertTrue(game.state.cities['xiangyang'].action_used)
        before=game.export_save()
        self.assertFalse(logistics.auto_dispatch_city(game,game.state,'xiangyang'))
        self.assertEqual(game.export_save(),before)
        game.validate(game.state)

    def test_below_reserve_source_cannot_create_a_false_dispatch_preview(self):
        for resource in ('gold', 'grain', 'reserves'):
            game = self.game()
            game.command('set_logistics', dict(city='xiangyang', policy=dict(enabled=True)), game.revision)
            source = game.state.cities['xiangyang']
            reserve = game.state.extension['logistics']['cities'][source.id]['policy']['reserve_' + resource]
            # Move soldiers rather than deleting them when lowering reserves.
            if resource == 'reserves':
                game.state.cities['nanjun'].reserves += source.reserves - reserve + 1
            setattr(source, resource, reserve - 1)
            before = game.export_save()
            proposed, reason = logistics.preview(game, game.state, source.id)
            self.assertIsNone(proposed); self.assertEqual(reason, 'insufficient_resources')
            self.assertFalse(logistics.auto_dispatch_city(game, game.state, source.id))
            self.assertEqual(before, game.export_save())

    def test_target_capture_returns_over_real_time_and_does_not_reserve_enemy_slots(self):
        game = self.game()
        origin = deepcopy(game.state.cities['xiangyang'])
        self.dispatch(game)
        game.state.cities['nanjun'].owner = 'wei'
        game._reconcile_factions(game.state); self.sync(game)
        self.assertEqual(logistics._inbound(game.state, 'nanjun'), dict(gold=0, grain=0, reserves=0, treasure=0, officers=0))
        self.advance_due(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['status'], 'returning')
        self.assertGreater(row['journeys'][-1]['arrival_turn'], game.state.turn)
        self.assertEqual(logistics.in_transit_reserves(game.state), 300)
        game.validate(game.state)
        self.advance_due(game)
        source = game.state.cities['xiangyang']
        self.assertEqual(source.gold, origin.gold)
        self.assertEqual(source.reserves, origin.reserves)
        self.assertLess(source.grain, origin.grain)
        self.assertIn(999, source.roster.officer_ids)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        game.validate(game.state)

    def test_full_destination_accepts_cargo_without_inserting_escorts_or_repeating_delivery(self):
        game = self.game()
        self.dispatch(game)
        self.fill(game, 'nanjun', 99)
        self.advance_due(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['status'], 'returning');self.assertTrue(row['delivery_done'])
        self.assertEqual(logistics.in_transit_reserves(game.state), 0)
        before = game.export_save()
        logistics.process_arrivals(game, game.state)
        self.assertEqual(before, game.export_save())
        self.advance_due(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(game._city_occupancy(game.state, game.state.cities['nanjun']), 99)
        self.assertGreater(game.state.extension['logistics']['receipts'][str(999)], game.state.turn)

    def test_sea_requires_explicit_policy_and_weather_is_applied_once_while_waiting(self):
        game = self.game(sea=True)
        self.fails(game, dict(source='xiangyang', target='nanjun', officers=[999], route_mode='fastest',
                             cargo=dict(gold=100, grain=200, reserves=300)))
        game.command('set_logistics', dict(city='xiangyang', policy=dict(allow_sea=True)), game.revision)
        draws = game.state.rng.draws
        self.dispatch(game, mode='fastest')
        game.state.cities['nanjun'].gold=logistics.LIMIT
        self.assertEqual(game.state.rng.draws, draws + 1)
        self.fill(game, 'nanjun', 99)
        self.advance_due(game)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['status'], 'waiting')
        self.assertLess(row['cargo']['reserves'], 300)
        self.assertTrue(all(r['applied'] for r in row['journeys'][0]['risks']))
        cargo, lost, rng = deepcopy(row['cargo']), game.state.soldiers['lost'], deepcopy(game.state.rng)
        game._complete_turn(game.state); game.command('arrivals', {}, game.revision)
        row = game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['cargo'], cargo); self.assertEqual(game.state.soldiers['lost'], lost)
        self.assertEqual(game.state.rng, rng)
        game.validate(game.state)

    def test_signed_cargo_quote_and_weather_tampering_reject_atomically(self):
        game = self.game()
        self.dispatch(game)
        saved = game.export_save()
        for field in ('cargo', 'quote', 'eta', 'id', 'ref'):
            modified = deepcopy(saved)
            row = modified['state']['extension']['logistics']['convoys'][0]
            if field == 'cargo': row['cargo']['gold'] += 1
            elif field == 'quote': row['journeys'][0]['quote']['days'] += 1
            elif field == 'eta': row['journeys'][0]['arrival_turn'] += 1
            elif field == 'id': modified['state']['extension']['logistics']['next_id'] = row['id']
            else: row['officers'] = [True]
            modified['checksum'] = digest({k: v for k, v in modified.items() if k != 'checksum'})
            before, revision = game.export_save(), game.revision
            with self.assertRaises(GameError): game.load_save(modified, revision)
            self.assertEqual(game.export_save(), before); self.assertEqual(game.revision, revision)

    def test_extinction_abandons_only_actual_cargo_and_preserves_soldier_balance(self):
        game = self.game()
        self.dispatch(game)
        lost = game.state.soldiers['lost']
        for city in game.state.cities.values():
            if city.owner == 'shu': city.owner = 'wei'
        # This models ownership loss independently of the battle's officer handling.
        logistics.synchronize(game, game.state)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(game.state.soldiers['lost'], lost + 300)
        self.assertFalse(logistics.in_transit_reserves(game.state))

    def test_generated_and_historical_escorts_share_one_real_convoy(self):
        game = self.game()
        candidate = game.state.extension['civil_staff']['cities']['nanjun']['candidate']['id']
        game.command('hire_staff', dict(city='nanjun', candidate=candidate), game.revision)
        game._complete_turn(game.state)
        game.command('transfer', dict(source='nanjun', target='xiangyang', officers=[candidate], route_mode='land'), game.revision)
        eta = game.state.extension['travel']['marches'][0]['arrival_turn']
        while game.state.turn < eta: game._complete_turn(game.state)
        game.command('arrivals', {}, game.revision)
        game._complete_turn(game.state)
        self.dispatch(game, ids=[999, candidate])
        self.assertEqual(set(logistics.marching_ids(game.state)), {999, candidate})
        saved = game.export_save()
        restored = Campaign(game.catalog); restored.load_save(saved, 0)
        self.assertEqual(saved, restored.export_save())
        self.advance_due(game)
        self.assertIn(999,game._march_ids(game.state))
        self.advance_due(game)
        self.assertIn(999, game.state.cities['xiangyang'].roster.officer_ids)
        self.assertIn(candidate, game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(game.state.officers[candidate].faction_id, 'shu')
        self.assertEqual(game.state.extension['civil_staff']['people'][candidate]['city'], 'xiangyang')
        game.validate(game.state)

    def test_blocked_intermediate_city_keeps_party_at_real_origin_without_duplicate_cargo(self):
        data = deepcopy(transport_catalog().data)
        data['initial_owners']['nanyang'] = 'neutral'
        data['initial_owners']['jiangxia'] = 'wei'
        data['factions'] = [r for r in data['factions'] if r['id'] != 'wu']
        data['faction_rulers'].pop('wu')
        next(r for r in data['factions'] if r['id'] == 'wei')['city'] = 'jiangxia'
        for row in data['initial_officers']:
            if row['city'] == 'nanyang': row['city'] = 'jiangxia'
            if row['person_id'] == 'san14-candidate-0179': row['ruler'] = False
        routes = data['travel_routes']
        routes[:] = [r for r in routes if {r['from'], r['to']} != {'xiangyang', 'nanjun'}]
        routes.append(dict(id='corridor:nanyang:nanjun', **{'from': 'nanyang', 'to': 'nanjun'},
            mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'corridor.json'; p.write_text(json.dumps(data))
            game = Campaign(Catalog(p)); game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('set_logistics', dict(city='xiangyang', policy=dict(target_city='nanjun')), game.revision)
        original=deepcopy(game.state.cities['xiangyang'])
        self.dispatch(game)
        self.assertEqual(game.state.extension['logistics']['convoys'][0]['journeys'][0]['quote']['path'],
                         ['xiangyang', 'nanyang', 'nanjun'])
        game.state.cities['nanyang'].owner = 'wei'; self.sync(game)
        self.advance_due(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(game.state.cities['xiangyang'].gold,original.gold)
        self.assertEqual(game.state.cities['xiangyang'].reserves,original.reserves)
        loaded=Campaign(game.catalog);loaded.load_save(game.export_save(),0)
        self.assertEqual(loaded.export_save(),game.export_save())


if __name__ == '__main__':
    unittest.main()
