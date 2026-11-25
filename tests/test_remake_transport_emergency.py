"""Physical exits, ordinary relief, resource ledgers and legacy save isolation."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from random import Random
from unittest.mock import patch
import unittest

from test_remake_convoy_rescue import rescue_catalog
import test_remake_winter_transport as winter_fixtures
from test_remake_winter_transport import Headless
from remake.campaign import Catalog
from remake import army_relief, convoy_relief, grain_units, logistics, logistics_rules, march_supply, staging_supply, treasures
from remake import transport_emergency as emergency, winter_travel, winter_weather
from remake.errors import GameError


class TransportEmergencyTests(unittest.TestCase):
    def game(self, *, level=3, weather=0, catalog=None):
        game=Headless(catalog or rescue_catalog(),record_journal=False)
        with emergency.experiment(level):
            game.command('new',dict(faction='shu',seed=2026,weather_rules_version=weather),0)
        for city in ('xiangyang','jiangxia'):
            game.command('set_logistics',dict(city=city,policy=dict(enabled=True,reserve_officers=0,reserve_reserves=0)),game.revision)
        game.state.cities['xiangyang'].grain=10_000
        return game

    def convoy(self,game,*,cargo=None,bag=None):
        cargo = cargo if cargo is not None else dict(gold=75,grain=0,reserves=1_000)
        game.command('dispatch_transport',dict(source='xiangyang',target='nanjun',officers=[999],
                                             cargo=cargo,route_mode='land'),game.revision)
        row=logistics._pool(game.state)['convoys'][0]
        if bag is not None:
            # A fixture for a previously depleted vehicle. Retain a balanced
            # opening ledger and execute its original route under the engine.
            supply=emergency.book(row)
            game.state.cities['xiangyang'].grain+=supply['loaded']-bag
            supply['loaded']=supply['remaining']=bag
        return row

    def blocked_node(self,game,row):
        state=game.state
        game._complete_turn(state)
        self.assertEqual(march_supply.current_city(row['journeys'][-1]),'nanjun')
        state.cities['nanjun'].gold=logistics.LIMIT
        self.assertEqual(logistics._receiving_blocker(game,state,row,state.cities['nanjun'],returning=True),
                         'resource_full')
        state.phase='city'
        return state

    def roundtrip(self,game):
        for compact in (False,True):
            saved=game.export_save(compact=compact)
            loaded=Headless(game.catalog,record_journal=False)
            loaded.load_save(saved,0)
            self.assertEqual(loaded.export_save(compact=compact),saved)
        return loaded

    def test_smaller_funded_exit_docks_and_closes_once(self):
        game=self.game()
        with grain_units.using(game.state):
            row=self.convoy(game,bag=230)
            state=self.blocked_node(game,row)
            grain=emergency.available(row)
            origin_book=deepcopy(emergency.book(row))
            self.assertTrue(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            self.assertEqual(row['target'],'jiangxia')
            details=row['emergency']
            self.assertGreater(details['full_budget'],grain)
            self.assertLessEqual(details['route_budget'],grain)
            self.assertEqual(row['cargo']['gold'],75)
            self.assertEqual(row['cargo']['reserves'],1_000)
            self.assertEqual(row['journeys'][0]['supply']['route_days'],origin_book['route_days'])
            self.roundtrip(game)
            # A repeated safety check at the same physical origin is not a
            # second journey or an extra withdrawal from either grain ledger.
            old=deepcopy(row); rng=deepcopy(state.rng)
            self.assertTrue(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            self.assertEqual(row['journeys'],old['journeys'])
            self.assertEqual(row['cargo_ledger'],old['cargo_ledger'])
            self.assertEqual(state.rng,rng)
            gold_before=state.cities['jiangxia'].gold
            game._complete_turn(state)
            logistics.process_arrivals(game,state)
            treasures.synchronize(game,state)
            self.assertNotIn(row,logistics._pool(state)['convoys'])
            self.assertIn(999,state.cities['jiangxia'].roster.officer_ids)
            self.assertEqual(state.cities['jiangxia'].gold,gold_before+75)
            received=game.export_save()
            logistics.process_arrivals(game,state)
            self.assertEqual(game.export_save(),received)
            self.roundtrip(game)

    def test_external_refill_uses_real_handoff_and_only_one_live_commitment(self):
        game=self.game()
        with grain_units.using(game.state):
            row=self.convoy(game,bag=148)
            state=self.blocked_node(game,row)
            self.assertFalse(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            self.assertEqual(row['emergency']['status'],'no_feasible_exit')
            need=convoy_relief.request(game,state,row)
            self.assertIsNotNone(need)
            self.assertEqual(emergency.convoy_units(state,row),state.officers[999].troops+1_100)
            self.roundtrip(game)
            donor=state.cities['jiangxia']
            planner=convoy_relief.Planner(game,state,'shu')
            option,reason=planner.quote(donor,row)
            self.assertIsNotNone(option,reason)
            origin_grain=donor.grain
            origin_book=emergency.book(row)['remaining']
            payload=dict(source=donor.id,target=need.city,target_convoy=row['id'],officers=option['officers'],
                route_mode=option['mode'],cargo=dict(gold=0,grain=option['grain'],reserves=0))
            relief=logistics.dispatch(game,state,payload,'shu')
            self.assertEqual(origin_grain-donor.grain,option['grain']+option['rations'])
            self.assertEqual(emergency.book(row)['remaining'],origin_book)
            self.assertIsNone(convoy_relief.request(game,state,relief))
            duplicate=convoy_relief.Planner(game,state,'shu').quote(state.cities['xiangyang'],row)
            self.assertIn(duplicate[1],{'same_request','already_assigned','active_late'})
            treasures.synchronize(game,state)
            self.roundtrip(game)
            before=state.cities['nanjun'].grain
            for tick in range(11,14):
                for unit in list(logistics._pool(state)['convoys']):
                    logistics.advance_supply(game,state,unit,absolute_tick=tick)
                logistics.rendezvous(game,state,tick=tick)
            self.assertTrue(relief['delivery_done'])
            self.assertEqual(state.cities['nanjun'].grain,before)
            matching=[r for r in emergency.book(row)['refills'] if r['source']==relief['id'] and r['kind']=='convoy']
            self.assertEqual(len(matching),1)
            self.assertEqual(matching[0]['grain'],relief['delivered']['grain'])
            self.assertGreater(matching[0]['grain'],0)
            logistics.rendezvous(game,state,tick=13)
            self.assertEqual(len([r for r in emergency.book(row)['refills'] if r['kind']=='convoy']),1)
            game._complete_turn(state)
            logistics.process_arrivals(game,state)
            treasures.synchronize(game,state)
            self.assertEqual((row['status'],row['target']),('returning','jiangxia'))
            self.assertGreaterEqual(emergency.book(row)['remaining'],row['emergency']['route_budget'])
            self.roundtrip(game)
            game._complete_turn(state)
            logistics.process_arrivals(game,state)
            treasures.synchronize(game,state)
            self.assertNotIn(row,logistics._pool(state)['convoys'])
            self.assertIn(999,state.cities['jiangxia'].roster.officer_ids)
            self.roundtrip(game)

    def test_late_expected_arrival_is_never_available_as_rations(self):
        game=self.game()
        with grain_units.using(game.state):
            row=self.convoy(game,bag=148)
            state=self.blocked_node(game,row)
            self.assertFalse(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            donor=state.cities['jiangxia']
            planner=convoy_relief.Planner(game,state,'shu')
            option,_=planner.quote(donor,row)
            relief=logistics.dispatch(game,state,dict(source=donor.id,target='nanjun',target_convoy=row['id'],
                officers=option['officers'],route_mode=option['mode'],
                cargo=dict(gold=0,grain=option['grain'],reserves=0)),'shu')
            relief['convoy_relief']['wait_until']=10
            due=convoy_relief.request(game,state,row)
            self.assertEqual(convoy_relief.outstanding(game,state,row,due),())
            bag=emergency.book(row)['remaining']
            self.assertFalse(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            self.assertEqual(emergency.book(row)['remaining'],bag)
            self.assertFalse(relief['delivery_done'])

    def test_small_risk_margin_waiver_keeps_the_real_travel_cost(self):
        game=self.game()
        with grain_units.using(game.state):
            row=self.convoy(game,bag=210)
            state=self.blocked_node(game,row)
            supply=emergency.book(row)
            supply['waiting']=True
            bag=supply['remaining']
            self.assertTrue(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            self.assertTrue(row['emergency']['risk_margin_waived'])
            self.assertGreater(row['emergency']['route_budget'],bag)
            self.assertEqual(emergency.book(row)['remaining'],bag)
            self.assertEqual(row['target'],'jiangxia')

    def test_staged_grain_is_not_reserved_or_drawn_before_arrival(self):
        data=deepcopy(rescue_catalog().data)
        first=data['travel_routes'][0]
        first.update(days=30,distance_km=900,land_km=900)
        data['travel_routes'].append(dict(id='rescue:jiangxia:nanyang',**{'from':'jiangxia','to':'nanyang'},
            mode='land',terrain='plain',distance_km=450,land_km=450,sea_km=0,days=15))
        data['links'].append(['jiangxia','nanyang'])
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'staged.json'
            path.write_text(json.dumps(data,ensure_ascii=False))
            game=self.game(catalog=Catalog(path))
        with grain_units.using(game.state):
            row=self.convoy(game,bag=1240)
            state=game.state
            for _ in range(3):
                game._complete_turn(state)
            self.assertEqual(march_supply.current_city(row['journeys'][-1]),'nanjun')
            state.cities['nanjun'].gold=state.cities['jiangxia'].gold=logistics.LIMIT
            state.cities['nanyang'].owner='shu'
            state.phase='city'
            dock_stock=state.cities['jiangxia'].grain
            original_bag=emergency.book(row)['remaining']
            self.assertTrue(emergency.withdraw(game,state,row,'nanjun','resource_full'))
            plan=row['emergency']
            self.assertEqual((plan['target'],plan['final']),('jiangxia','nanyang'))
            self.assertEqual(dock_stock,state.cities['jiangxia'].grain)
            self.assertEqual(emergency.book(row)['remaining'],original_bag)
            self.assertEqual(plan['stops'][0][0],'jiangxia')

    def test_v221_legal_endpoint_and_return_regressions_with_222(self):
        parent=winter_fixtures.WinterTransportTests
        for name in ('test_target_loss_at_a_city_keeps_escort_out_of_enemy_destination',
                     'test_same_return_route_keeps_journey_rations_and_rng'):
            with self.subTest(name=name), emergency.experiment(3):
                result=unittest.TestResult()
                parent(name).run(result)
                self.assertFalse(result.errors+result.failures,result.errors+result.failures)

    def test_relief_dependency_chain_shape_for_1000_generated_ids(self):
        game=self.game()
        rng=Random(2026222)
        state=game.state
        for _ in range(1000):
            base=rng.randrange(1,99_990)
            target=base
            deployed=base+rng.randrange(1,10)
            row=dict(id=deployed,owner='shu',original_target='nanjun',source='jiangxia',target_march=None,
                initial_cargo=dict(grain=10,gold=0,reserves=0,treasure=0),
                delivery_done=True,convoy_relief=dict(target=target,root=f'convoy:{target}',meeting='nanjun',
                    eta=2,wait_until=10,needed=3,net=3,return_city='jiangxia',return_weight=100_000,
                    outbound=3,waiting=2,returning=3,safety=1))
            pool=dict(next_id=deployed+1,convoys=[row])
            convoy_relief.validate(state,row,pool)
            row['convoy_relief'].update(target=deployed,root=f'convoy:{deployed}')
            with self.assertRaisesRegex(ValueError,'Convoy relief mission'):
                convoy_relief.validate(state,row,pool)

    def test_receiving_ledger_conserves_1000_opening_loads(self):
        game=self.game()
        basis=game.state
        with grain_units.using(basis):
            original=self.convoy(game)
            basis=game.state
            rng=Random(6222)
            for _ in range(1000):
                state=deepcopy(basis)
                row=logistics._pool(state)['convoys'][0]
                city=state.cities['xiangyang']
                cargo=dict(gold=rng.randrange(1000),grain=rng.randrange(1000),reserves=rng.randrange(1000),treasure=0)
                bag=rng.randrange(1000)
                row['cargo']=dict(cargo)
                row['initial_cargo']=dict(cargo)
                emergency.book(row).update(loaded=bag,remaining=bag)
                before={name:getattr(city,name) for name in ('gold','grain','reserves')}
                self.assertTrue(logistics._dock(game,state,row,city))
                self.assertFalse(logistics._dock(game,state,row,city))
                self.assertEqual(city.gold-before['gold'],cargo['gold'])
                self.assertEqual(city.grain-before['grain'],cargo['grain']+bag)
                self.assertEqual(city.reserves-before['reserves'],cargo['reserves'])
                self.assertIn(original['officers'][0],city.roster.officer_ids)

    def test_designated_supply_bookings_cannot_be_spent_again(self):
        game=self.game()
        state=game.state
        city=state.cities['jiangxia']
        with grain_units.using(state):
            before=emergency.stock(game,state,city)
            with patch.object(staging_supply,'held',return_value=city.grain-before//2):
                self.assertLessEqual(emergency.stock(game,state,city),before//2)
                self.assertEqual(city.grain,10_000)

    def test_enemy_or_transit_only_city_cannot_accept(self):
        game=self.game()
        row=self.convoy(game,bag=230)
        state=self.blocked_node(game,row)
        city=state.cities['nanjun']
        city.owner='wei'
        city.gold=0
        with patch('remake.historical_campaigns.transit_allowed',return_value=True):
            self.assertFalse(emergency.can_receive(game,state,row,city))
            self.assertFalse(logistics._dock(game,state,row,city))
        self.assertIn(row,logistics._pool(state)['convoys'])

    def test_full_ice_stays_physically_closed_and_never_docks_remotely(self):
        game=self.game(weather=221)
        row=self.convoy(game)
        state=game.state
        with patch.object(winter_weather,'movement',return_value=True), patch.object(
                winter_travel,'checkpoint_forecast',return_value=(None,1000,'fixture-reach')):
            review=emergency.Review(game,state)
            options=review.quotes('shu','nanjun',row['route_policy'])
            self.assertEqual(set(options),{'nanjun'})
        self.assertFalse(logistics._dock(game,state,row,state.cities['jiangxia']))
        self.assertIn(row,logistics._pool(state)['convoys'])

    def test_thirty_day_frozen_wait_does_not_remove_a_real_convoy(self):
        game=self.game(weather=221)
        row=self.convoy(game)
        state=self.blocked_node(game,row)
        state.cities['nanjun'].owner='wei'
        book=emergency.book(row)
        work=book['winter']['work']
        prior=book['clock_tick']
        with grain_units.using(state), patch.object(winter_weather,'movement',return_value=True), patch.object(
                winter_travel,'checkpoint_forecast',return_value=(None,1000,'closed-reach')):
            self.assertFalse(emergency.withdraw(game,state,row,'nanjun','route_blocked'))
            self.assertEqual(row['emergency']['status'],'waiting_for_thaw')
            for tick in range(prior+1,prior+32):
                logistics.advance_supply(game,state,row,absolute_tick=tick)
        self.assertIn(row,logistics._pool(state)['convoys'])
        self.assertEqual(book['winter']['work'],work)
        self.assertEqual(book['clock_tick'],prior+31)
        self.assertGreater(book['consumed'],0)
        self.assertIn(999,state.officers)

    def test_zero_escort_keeps_officer_cost_and_other_cargo(self):
        game=self.game()
        state=game.state
        old=state.officers[999].troops
        state.officers[999].troops=0
        state.cities['xiangyang'].reserves+=old
        row=self.convoy(game,cargo=dict(gold=75,grain=0,reserves=0),bag=18)
        self.assertEqual(emergency.convoy_units(state,row),100)
        self.assertEqual(row['cargo']['gold'],75)
        state.cities['xiangyang'].gold=logistics.LIMIT
        self.assertFalse(logistics._dock(game,state,row,state.cities['xiangyang']))
        self.assertIn(999,state.officers)
        self.assertEqual(row['cargo']['gold'],75)
        self.roundtrip(game)

    def test_version_and_opt_in_save_boundaries(self):
        for level,weather in ((0,0),(0,22),(0,221),(1,221),(2,221),(3,0),(3,22),(3,221)):
            with self.subTest(level=level,weather=weather):
                game=self.game(level=level,weather=weather)
                restored=self.roundtrip(game)
                self.assertEqual(emergency.stage(restored.state),level)
                self.assertEqual(restored.state.extension.get(winter_weather.FIELD,0),weather)
        game=self.game(level=0)
        with self.assertRaises(GameError):
            game.command('new',dict(faction='shu',seed=2026,transport_emergency_rules_version=1),game.revision)

    def test_observer_keeps_save_and_rng_identical(self):
        game=self.game()
        self.convoy(game)
        reference=self.roundtrip(game)
        observed=[]
        with winter_weather.experiment(0,observe=lambda kind,data:observed.append((kind,data)),detailed=True):
            game._complete_turn(game.state)
            logistics.process_arrivals(game,game.state)
        reference._complete_turn(reference.state)
        logistics.process_arrivals(reference,reference.state)
        self.assertEqual(game.export_save(),reference.export_save())
        self.assertTrue(observed)

    def test_fixed_point_budgets_cover_three_distinct_components(self):
        rng=Random(222)
        for _ in range(1000):
            units=rng.randint(0,30_000)
            out,wait,back=(rng.randrange(0,150)*logistics_rules.RATION_SCALE for _ in range(3))
            credit=rng.randrange(0,50*logistics_rules.RATION_SCALE)
            q=army_relief.ration_budget(units,out,wait,back,credit=credit)
            moved=army_relief.ration_budget(units,out,wait,0,credit=credit)
            actual_cost=max(0,logistics_rules.ceil_div(units*(out+wait+back)-credit,50*logistics_rules.RATION_SCALE))
            self.assertEqual(q.outbound+q.wait+q.returning,actual_cost)
            self.assertEqual(q.total,actual_cost+logistics_rules.ceil_div(actual_cost,10))
            self.assertLessEqual(moved.total,q.total)


if __name__=='__main__':
    unittest.main()
