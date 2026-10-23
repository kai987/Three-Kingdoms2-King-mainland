"""Actual daily checkpoints, hunger and physical retreat through both engines."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,Catalog,digest
from remake.errors import GameError
from remake import march_supply
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog


def segment_catalog(days=(10,20),checkpoint_grain=100):
    data=deepcopy(controlled_catalog().data)
    data['id']='controlled-segment-food'
    data['initial_owners'].update(nanjun='shu',jiangxia='shu')
    data['factions']=[row for row in data['factions'] if row['id']!='wu']
    data['faction_rulers'].pop('wu',None)
    data['city_income']={c:dict(gold=0,grain=0,reserves=0) for c in data['active_cities']}
    for city in data['active_cities']:
        data['initial_city_resources'][city]=dict(gold=0,grain=100,reserves=0)
    data['initial_city_resources']['nanjun']['grain']=checkpoint_grain
    for route in data['travel_routes']:
        for pair,number in [(frozenset(('xiangyang','nanjun')),days[0]),(frozenset(('nanjun','jiangxia')),days[1])]:
            if frozenset((route['from'],route['to']))==pair:
                route.update(days=number,distance_km=number*30,land_km=number*30)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'segment.json';path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


class SegmentSupplyTests(unittest.TestCase):
    def game(self,**options):
        game=Campaign(segment_catalog(**options));game.command('new',dict(faction='shu',seed=2026),0)
        return game

    def queue(self,game):
        ident=game.state.cities['xiangyang'].roster.officer_ids[1]
        game.command('transfer',dict(source='xiangyang',target='jiangxia',officers=[ident],route_mode='land'),game.revision)
        return ident,game.state.extension['travel']['marches'][0]

    def step(self,game):
        game._complete_turn(game.state);game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.validate(game.state)

    def restore(self,game):
        saved=game.export_save();copy=Campaign(game.catalog);copy.load_save(saved,0)
        self.assertEqual(copy.export_save(),saved)
        return copy

    def test_first_checkpoint_budget_actual_city_debit_and_subgrain_credit(self):
        for backend in ('python','rust'):
            with self.subTest(backend=backend),using_backend(backend):
                game=self.game();before=deepcopy(game.to_dict());ident,row=self.queue(game)
                units=game.state.officers[ident].troops+100
                first=march_supply.cost(units-100,1,10)
                self.assertEqual(row['supply']['loaded'],first)
                self.assertEqual(game.state.cities['xiangyang'].grain,100-first)
                self.step(game)
                row=game.state.extension['travel']['marches'][0]
                self.assertEqual(march_supply.current_city(row),'nanjun')
                self.assertEqual(row['supply']['route_days'],10)
                self.assertEqual(game.state.cities['nanjun'].grain,100,'No remote refill before the next real day')
                game=self.restore(game);self.step(game);self.step(game)
                row=game.state.extension['travel']['marches'][0]
                total=march_supply.cost(units-100,1,30)
                self.assertEqual(row['supply']['consumed'],total)
                self.assertEqual(row['supply']['received'],total-first)
                self.assertEqual(game.state.cities['nanjun'].grain,100-(total-first))
                self.assertEqual(row['supply']['shortage_days'],0)
                self.assertEqual(game.to_dict()['rng'],before['rng'])
                self.assertEqual(game.to_dict()['soldiers'],before['soldiers'])
                game.command('arrivals',{},game.revision)
                self.assertIn(ident,game.state.cities['jiangxia'].roster.officer_ids)

    def test_waiting_at_empty_checkpoint_eats_and_retreats_without_teleport_or_randomness(self):
        for backend in ('python','rust'):
            with self.subTest(backend=backend),using_backend(backend):
                game=self.game(checkpoint_grain=0);ident,row=self.queue(game)
                initial_troops=game.state.officers[ident].troops
                initial_soldiers=deepcopy(game.state.soldiers);rng=deepcopy(game.state.rng)
                self.step(game);self.step(game)
                row=game.state.extension['travel']['marches'][0]
                self.assertEqual(march_supply.current_city(row),'nanjun')
                food=row['history'][0]['supply'] if row['history'] else row['supply']
                self.assertTrue(food['waiting'])
                self.assertGreater(food['shortage_days'],0)
                self.assertLess(game.state.officers[ident].troops,initial_troops)
                # A tiny prepaid fraction of a grain can feed part of the first
                # waiting day; ten subsequent hungry days force a real route.
                if row['status']!='returning':self.step(game)
                row=game.state.extension['travel']['marches'][0]
                self.assertEqual(row['status'],'returning')
                self.assertEqual(row['journey_source'],'nanjun')
                self.assertEqual(row['target'],'xiangyang')
                self.assertEqual(row['supply']['route_days'],0)
                self.assertIn(ident,game.state.cities['xiangyang'].roster.officer_ids)
                self.assertIn(ident,game._march_ids(game.state),'Roster reservation is not arrival')
                self.assertGreater(row['history'][0]['supply']['lost'],0)
                game=self.restore(game);self.step(game)
                game.command('arrivals',{},game.revision)
                self.assertFalse(game.state.extension['travel']['marches'])
                self.assertEqual(game.state.rng,rng)
                current=sum(o.troops for o in game.state.officers.values())+sum(c.reserves for c in game.state.cities.values())
                self.assertEqual(current+game.state.soldiers['lost'],initial_soldiers['initial'])

    def test_subgrain_rounding_carries_through_two_short_checkpoints(self):
        game=self.game(days=(1,1));ident,row=self.queue(game)
        self.step(game);row=game.state.extension['travel']['marches'][0]
        self.assertEqual(row['supply']['elapsed_days'],2)
        self.assertEqual(row['supply']['consumed'],1)
        self.assertEqual(game.state.cities['nanjun'].grain,100)
        self.assertGreater(row['supply']['credit_units'],0)

    def test_arrived_full_city_waiting_is_fed_by_that_actual_city(self):
        for marked in (False,True):
            with self.subTest(explicit_wait=marked):
                game=self.game(days=(1,1));ident,row=self.queue(game);self.step(game)
                row=game.state.extension['travel']['marches'][0]
                row['supply']['waiting']=marked
                before=game.state.cities['jiangxia'].grain
                self.step(game);row=game.state.extension['travel']['marches'][0]
                self.assertEqual(row['supply']['route_days'],2)
                self.assertEqual(row['supply']['elapsed_days'],12)
                self.assertTrue(row['supply']['waiting'])
                self.assertLess(game.state.cities['jiangxia'].grain,before)
                self.assertEqual(row['supply']['shortage_days'],0)
                self.restore(game)

    def test_meal_clock_and_hunger_receipt_tampering_reject_atomically(self):
        game=self.game(checkpoint_grain=0);self.queue(game);self.step(game);self.step(game)
        original=game.export_save()
        for kind in ('clock','grain','hunger'):
            bad=deepcopy(original);row=bad['state']['extension']['travel']['marches'][0]
            s=row['history'][0]['supply'] if row['history'] else row['supply']
            if kind=='clock':s['clock_tick']-=10;s['periods'].pop()
            elif kind=='grain':s['remaining']+=1
            else:s['starvation'][0]['after'][next(iter(s['starvation'][0]['after']))]+=1
            bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            with self.assertRaises((GameError,ValueError)):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),original)

    def test_surplus_bag_waits_at_a_full_granary_instead_of_overflowing(self):
        game=self.game(days=(1,1));ident,row=self.queue(game)
        source=game.state.cities['xiangyang'];source.grain-=10
        march_supply.receive(row['supply'],10,'city',source.id,game.state.turn)
        target=game.state.cities['jiangxia'];target.grain=march_supply.LIMIT
        self.step(game);game.command('arrivals',{},game.revision)
        row=game.state.extension['travel']['marches'][0]
        self.assertTrue(row['supply']['waiting'])
        self.assertEqual(game.state.cities[target.id].grain,march_supply.LIMIT)
        self.assertIn(ident,game.state.cities[source.id].roster.officer_ids)
        self.restore(game)
        game.state.cities[target.id].grain-=100
        self.step(game);game.command('arrivals',{},game.revision)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertIn(ident,game.state.cities[target.id].roster.officer_ids)
        self.assertLessEqual(game.state.cities[target.id].grain,march_supply.LIMIT)


if __name__=='__main__':unittest.main()
