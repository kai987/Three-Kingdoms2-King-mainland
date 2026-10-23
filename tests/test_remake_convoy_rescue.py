"""Real checkpoint rendezvous, returning escorts and auditable food custody."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,Catalog,digest
from remake import logistics,march_supply
from remake.errors import GameError
from remake.march_core import using_backend
from test_remake_domestic import domestic_catalog
from test_remake_logistics import transport_catalog


def rescue_catalog():
    data=deepcopy(domestic_catalog().data)
    data['id']='controlled-real-node-rescue'
    data['initial_owners']['jiangxia']='shu'
    data['factions']=[r for r in data['factions'] if r['id']!='wu']
    data['faction_rulers'].pop('wu')
    for row in data['initial_officers']:
        if row['city']=='jiangxia':row.update(ruler=False,troops=100)
        if row['person_id']=='san14-candidate-0147':row['troops']=300
    data['initial_city_resources']['xiangyang']['grain']=5
    data['initial_city_resources']['nanjun']['grain']=0
    data['initial_city_resources']['jiangxia']=dict(gold=100,grain=1000,reserves=0)
    data['city_income']={key:dict(gold=0,grain=0,reserves=0) for key in data['active_cities']}
    pairs=[('xiangyang','nanjun',5),('nanjun','jiangxia',2)]
    data['links']=[[a,b] for a,b,_ in pairs]
    data['travel_routes']=[dict(id=f'rescue:{a}:{b}',**{'from':a,'to':b},mode='land',terrain='plain',
        distance_km=days*30,land_km=days*30,sea_km=0,days=days) for a,b,days in pairs]
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'rescue.json';path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


class ConvoyRescueTests(unittest.TestCase):
    def game(self):
        game=Campaign(rescue_catalog())
        game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_logistics',dict(city='jiangxia',policy=dict(reserve_officers=0,max_officers=1)),game.revision)
        game.command('transfer',dict(source='xiangyang',target='jiangxia',officers=[146],route_mode='land'),game.revision)
        return game

    def dispatch(self,game,grain=20):
        proposed=logistics.rescue_targets(game,game.state,'jiangxia')[0]
        self.assertTrue(proposed['can_dispatch'])
        self.assertEqual(proposed['city'],'nanjun')
        game.command('dispatch_transport',dict(source='jiangxia',target=proposed['city'],
            target_march=proposed['march_id'],officers=proposed['officers'],
            cargo=dict(gold=0,grain=grain,reserves=0),route_mode=proposed['route_mode']),game.revision)
        return game.state.extension['logistics']['convoys'][0]

    def day(self,game,tick):
        for army in list(game.state.extension['travel']['marches']):
            march_supply.advance_unit(game,game.state,army,army,absolute_tick=tick)
        for convoy in list(game.state.extension['logistics']['convoys']):
            logistics.advance_supply(game,game.state,convoy,absolute_tick=tick)
        logistics.rendezvous(game,game.state,tick=tick)

    def test_parties_meet_on_same_actual_day_and_escorts_make_the_real_return(self):
        for backend in ('python','rust'):
            with self.subTest(backend=backend),using_backend(backend):
                game=self.game();self.dispatch(game)
                army=game.state.extension['travel']['marches'][0]
                convoy=game.state.extension['logistics']['convoys'][0]
                baseline=game.state.rng.draws
                for tick in range(1,5):
                    self.day(game,tick)
                    self.assertFalse(convoy['delivery_done'])
                    self.assertFalse(any(r['kind']=='convoy' for r in army['supply']['refills']))
                self.assertEqual(march_supply.current_city(convoy['journeys'][-1]),'nanjun')
                self.assertIsNone(march_supply.current_city(army))
                self.day(game,5)
                self.assertTrue(convoy['delivery_done'])
                self.assertEqual(march_supply.current_city(army),'nanjun')
                self.assertEqual(army['supply']['clock_tick'],convoy['journeys'][-1]['supply']['clock_tick'])
                receipt=next(r for r in army['supply']['refills'] if r['kind']=='convoy')
                self.assertGreater(receipt['grain'],0)
                self.assertEqual(receipt['grain'],convoy['delivered']['grain'])
                game._complete_turn(game.state)
                self.assertEqual(game.state.rng.draws,baseline)
                game.validate(game.state)
                saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
                self.assertEqual(loaded.export_save(),saved)
                game.command('arrivals',{},game.revision)
                row=game.state.extension['logistics']['convoys'][0]
                self.assertEqual(row['status'],'returning')
                self.assertIn(row['officers'][0],game._march_ids(game.state))
                self.assertEqual(row['journeys'][-1]['quote']['path'],['nanjun','jiangxia'])
                game._complete_turn(game.state);game.command('arrivals',{},game.revision)
                self.assertFalse(game.state.extension['logistics']['convoys'])
                self.assertFalse(logistics.marching_ids(game.state))
                game.validate(game.state)

    def test_cancelled_target_keeps_cargo_and_does_not_remote_supply_another_army(self):
        game=self.game();self.dispatch(game)
        army=game.state.extension['travel']['marches'].pop()
        for ident in army['officers']:game.state.extension['officer_actions'][str(ident)]=game.state.turn
        convoy=game.state.extension['logistics']['convoys'][0]
        cargo=deepcopy(convoy['cargo'])
        logistics.rendezvous(game,game.state,tick=0)
        self.assertFalse(convoy['delivery_done']);self.assertEqual(convoy['cargo'],cargo)
        self.assertEqual(convoy['reason'],'army_missing')
        game._complete_turn(game.state)
        self.assertFalse(any(e['kind']=='army_supply' for e in convoy['cargo_ledger']))
        if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
        game.validate(game.state)

    def test_invalid_or_foreign_target_and_over_budget_payloads_are_atomic(self):
        game=self.game()
        proposed=logistics.rescue_targets(game,game.state,'jiangxia')[0]
        base=dict(source='jiangxia',target=proposed['city'],target_march=proposed['march_id'],
            officers=proposed['officers'],cargo=dict(gold=0,grain=20,reserves=0),route_mode='land')
        for patch in (dict(target_march=True),dict(target_march=999),dict(target='nanyang'),
                      dict(cargo=dict(gold=1,grain=20,reserves=0)),
                      dict(cargo=dict(gold=0,grain=1000,reserves=0))):
            before=game.export_save()
            with self.assertRaises((ValueError,GameError)):
                game.command('dispatch_transport',dict(base,**patch),game.revision)
            self.assertEqual(game.export_save(),before)

    def test_ai_support_uses_the_same_real_supply_party_before_normal_cargo(self):
        game=self.game()
        # The column is already holding at the friendly intermediate checkpoint
        # after its first real period; the source has no gold/reserve surplus.
        game._complete_turn(game.state)
        army=game.state.extension['travel']['marches'][0]
        self.assertEqual(march_supply.current_city(army),'nanjun')
        self.assertTrue(army['supply']['waiting'])
        game.command('set_logistics',dict(city='jiangxia',policy=dict(enabled=True)),game.revision)
        self.assertTrue(logistics.auto_dispatch_city(game,game.state,'jiangxia'))
        row=game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['target_march'],army['id'])
        self.assertEqual(row['cargo']['gold'],0);self.assertEqual(row['cargo']['reserves'],0)
        self.assertGreater(row['cargo']['grain'],0)
        game.validate(game.state)

    def test_cargo_delivery_and_manifest_forgery_reject_without_side_effects(self):
        game=self.game();self.dispatch(game)
        game._complete_turn(game.state)
        saved=game.export_save()
        for kind in ('cargo','delivered','manifest'):
            bad=deepcopy(saved)
            row=bad['state']['extension']['logistics']['convoys'][0]
            if kind=='cargo':row['cargo']['grain']+=1
            elif kind=='delivered':row['delivered']['grain']+=1
            else:
                journey=row['journeys'][0];supply=journey['supply']
                journey['departure_troops']={k:0 for k in journey['departure_troops']}
                supply['troops']=0
            bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            with self.assertRaises((ValueError,GameError)):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),saved)

    def test_coherent_zero_troop_meal_rewrite_still_cannot_recreate_food(self):
        game=self.game();self.dispatch(game);game._complete_turn(game.state)
        saved=game.export_save();bad=deepcopy(saved)
        journey=bad['state']['extension']['logistics']['convoys'][0]['journeys'][0]
        supply=journey['supply'];self.assertFalse(supply['starvation'])
        journey['departure_troops']={key:0 for key in journey['departure_troops']}
        supply['troops']=0
        for packet in supply['ration_manifests']:
            packet['troops']={key:0 for key in packet['troops']}
        credit=used_total=0
        for period in supply['periods']:
            for meal in period['days']:
                if meal is None:continue
                units=100*len(journey['departure_troops'])
                used=max(0,(units-credit+999)//1000)
                credit=credit+used*1000-units;used_total+=used
                meal[:]=[units,used,meal[2],0]
        supply['credit_units']=credit;supply['consumed']=used_total
        supply['remaining']=supply['loaded']+supply['received']-used_total-supply['returned_to_cargo']
        # It is a self-consistent food calculation; actual officer strength is
        # the independent anchor which must still reject the rewritten save.
        march_supply.validate(supply,journey['quote'],journey['departure_turn'],game.state.turn)
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises((ValueError,GameError)):game.load_save(bad,game.revision)
        self.assertEqual(game.export_save(),saved)

    def test_full_warehouse_waiting_keeps_eating_and_losses_match_cargo_and_personnel(self):
        game=Campaign(transport_catalog());game.command('new',dict(faction='shu',seed=2026),0)
        game.command('dispatch_transport',dict(source='xiangyang',target='nanjun',officers=[999],
            cargo=dict(gold=100,grain=0,reserves=300),route_mode='land'),game.revision)
        game.state.cities['nanjun'].gold=logistics.LIMIT
        game.state.cities['nanjun'].grain=0
        game._complete_turn(game.state);game.command('arrivals',{},game.revision)
        row=game.state.extension['logistics']['convoys'][0]
        self.assertEqual(row['reason'],'resource_full');self.assertTrue(row['journeys'][0]['supply']['waiting'])
        elapsed=row['journeys'][0]['supply']['elapsed_days'];lost=game.state.soldiers['lost']
        rng=deepcopy(game.state.rng)
        game._complete_turn(game.state)
        row=game.state.extension['logistics']['convoys'][0];bag=row['journeys'][0]['supply']
        self.assertEqual(bag['elapsed_days'],elapsed+10)
        self.assertGreater(bag['shortage_days'],0)
        self.assertLess(row['cargo']['reserves'],300)
        self.assertEqual(game.state.soldiers['lost']-lost,sum(r['lost'] for r in bag['starvation']))
        self.assertEqual(game.state.rng,rng)
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        game.validate(game.state)

    def test_maximum_resource_cargo_meal_also_counts_escorts_without_expanding_inventory_limits(self):
        game=Campaign(transport_catalog(long=True));game.command('new',dict(faction='shu',seed=2026),0)
        source=game.state.cities['xiangyang']
        recruited=logistics.LIMIT-source.reserves
        source.reserves=logistics.LIMIT;source.grain=logistics.LIMIT
        game.state.soldiers['recruited']+=recruited
        game.validate(game.state)
        game.command('set_logistics',dict(city=source.id,policy=dict(reserve_grain=0,
            reserve_reserves=0,max_reserves=logistics.LIMIT,max_officers=1)),game.revision)
        troops=game.state.officers[999].troops
        game.command('dispatch_transport',dict(source=source.id,target='nanjun',officers=[999],
            cargo=dict(gold=0,grain=0,reserves=logistics.LIMIT),route_mode='land'),game.revision)
        game._complete_turn(game.state)
        row=game.state.extension['logistics']['convoys'][0]
        meal=row['journeys'][0]['supply']['periods'][0]['days'][0]
        self.assertEqual(meal[0],logistics.LIMIT+troops+100)
        self.assertGreater(meal[0],logistics.LIMIT)
        self.assertEqual(row['cargo']['reserves'],logistics.LIMIT)
        game.validate(game.state)
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)

    def test_return_to_full_home_warehouse_waits_without_zero_day_overflow(self):
        from remake import civil_staff,domestic
        data=deepcopy(transport_catalog(long=True).data)
        data['initial_city_resources']['xiangyang']=dict(gold=logistics.LIMIT-100,grain=6,reserves=0)
        data['city_income']={key:dict(gold=100 if key=='xiangyang' else 0,grain=0,reserves=0)
                             for key in data['active_cities']}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'full-home.json';path.write_text(json.dumps(data,ensure_ascii=False))
            game=Campaign(Catalog(path))
        game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_logistics',dict(city='xiangyang',policy=dict(reserve_gold=0,
            reserve_grain=0,reserve_reserves=0,reserve_officers=1,max_gold=100,
            max_grain=0,max_reserves=0)),game.revision)
        game.command('dispatch_transport',dict(source='xiangyang',target='nanjun',officers=[999],
            cargo=dict(gold=100,grain=0,reserves=0),route_mode='land'),game.revision)
        game.state.cities['nanjun'].owner='wei'
        civil_staff.synchronize(game,game.state,checks=False)
        logistics.synchronize(game,game.state);domestic.synchronize(game,game.state)
        game.validate(game.state)
        for _ in range(6):
            game._complete_turn(game.state)
            game._spawn_eligible(game.state);game._reconcile_factions(game.state)
            game.validate(game.state)
            if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
        row=game.state.extension['logistics']['convoys'][0]
        self.assertEqual(game.state.cities['xiangyang'].gold,logistics.LIMIT)
        self.assertEqual(march_supply.current_city(row['journeys'][-1]),'xiangyang')
        self.assertEqual(row['reason'],'resource_full')
        self.assertTrue(row['journeys'][-1]['supply']['waiting'])
        self.assertEqual(row['cargo']['gold'],100)
        # A zero-day return is not another journey and still retains all cargo.
        self.assertEqual(len(row['journeys']),2)
        self.assertTrue(all(j['quote']['days']>0 for j in row['journeys']))
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)
        game.state.cities['xiangyang'].gold-=100
        logistics.resolve_supply_retreats(game,game.state)
        self.assertFalse(game.state.extension['logistics']['convoys'])
        self.assertEqual(game.state.cities['xiangyang'].gold,logistics.LIMIT)
        game.validate(game.state)

    def test_blocked_zero_day_docking_preserves_the_existing_route_target(self):
        game=Campaign(transport_catalog(long=True));game.command('new',dict(faction='shu',seed=2026),0)
        game.command('dispatch_transport',dict(source='xiangyang',target='nanjun',officers=[999],
            cargo=dict(gold=100,grain=0,reserves=0),route_mode='land'),game.revision)
        game.state.cities['xiangyang'].gold=logistics.LIMIT
        row=game.state.extension['logistics']['convoys'][0]
        self.assertEqual(march_supply.current_city(row['journeys'][-1]),'xiangyang')
        logistics._return(game,game.state,row,'retreat')
        self.assertEqual(row['reason'],'resource_full')
        self.assertEqual(row['target'],'nanjun')
        self.assertEqual(row['target'],row['journeys'][-1]['target'])
        self.assertTrue(row['journeys'][-1]['supply']['retreat_requested'])
        self.assertEqual(len(row['journeys']),1)
        game.validate(game.state)
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)

    def test_actual_retreating_column_receives_real_convoy_without_cancelling_return(self):
        data=deepcopy(rescue_catalog().data)
        data['active_cities'].append('shujun')
        data['initial_owners']['shujun']='shu'
        data['initial_city_resources']['shujun']=dict(gold=0,grain=0,reserves=0)
        data['city_income']['shujun']=dict(gold=0,grain=0,reserves=0)
        pairs=[('xiangyang','nanjun',5),('nanjun','jiangxia',2),
               ('xiangyang','jiangxia',2),('nanjun','shujun',5)]
        data['links']=[[a,b] for a,b,_ in pairs]
        data['travel_routes']=[dict(id=f'return-rescue:{a}:{b}',**{'from':a,'to':b},
            mode='land',terrain='plain',distance_km=days*30,land_km=days*30,sea_km=0,days=days)
            for a,b,days in pairs]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'return-rescue.json';path.write_text(json.dumps(data,ensure_ascii=False))
            game=Campaign(Catalog(path))
        game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_logistics',dict(city='xiangyang',policy=dict(reserve_grain=0,
            reserve_officers=1,max_officers=1)),game.revision)
        game.command('transfer',dict(source='xiangyang',target='shujun',officers=[146],route_mode='land'),game.revision)
        for _ in range(2):game._complete_turn(game.state)
        army=game.state.extension['travel']['marches'][0]
        self.assertEqual(army['status'],'returning')
        self.assertTrue(army['history'][-1]['supply']['retreat_requested'])
        self.assertEqual(army['quote']['path'],['nanjun','jiangxia','xiangyang'])
        if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
        proposal=next(r for r in logistics.rescue_targets(game,game.state,'xiangyang') if r['march_id']==army['id'])
        self.assertTrue(proposal['can_dispatch'])
        self.assertEqual(proposal['city'],'jiangxia')
        game.command('dispatch_transport',dict(source='xiangyang',target=proposal['city'],
            target_march=army['id'],officers=[999],cargo=dict(gold=0,grain=2,reserves=0),
            route_mode=proposal['route_mode']),game.revision)
        army=game.state.extension['travel']['marches'][0]
        convoy=game.state.extension['logistics']['convoys'][0]
        goal=army['target'];retreat_flag=army['supply']['retreat_requested']
        self.day(game,21)
        self.assertFalse(convoy['delivery_done'])
        self.day(game,22)
        self.assertTrue(convoy['delivery_done'])
        self.assertEqual(march_supply.current_city(army),'jiangxia')
        self.assertEqual(march_supply.current_city(convoy['journeys'][-1]),'jiangxia')
        self.assertEqual(army['status'],'returning')
        self.assertEqual(army['target'],goal)
        self.assertEqual(army['supply']['retreat_requested'],retreat_flag)
        self.assertEqual(convoy['delivered']['grain'],2)
        self.assertTrue(any(r['kind']=='convoy' and r['grain']==2 for r in army['supply']['refills']))
        game._complete_turn(game.state)
        game.validate(game.state)
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,0)
        self.assertEqual(loaded.export_save(),saved)


if __name__=='__main__':unittest.main()
