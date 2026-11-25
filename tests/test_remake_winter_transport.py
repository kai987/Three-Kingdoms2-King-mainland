"""Weather transport execution, forecasts and save compatibility."""
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import test_remake_logistics as transportation
from remake.campaign import Campaign
from remake import grain_units, logistics, march_supply
from remake import winter_transport, winter_travel as travel, winter_weather as weather
from remake import logistics_rules as rules


class Headless(Campaign):
    def view(self):
        return {}


class WinterTransportTests(unittest.TestCase):
    def setUp(self):
        self.fixture=transportation.LogisticsTests()

    def game(self, *, version=221, **options):
        game=Headless(transportation.transport_catalog(**options),record_journal=False)
        game.command('new',dict(faction='shu',seed=2026,weather_rules_version=version),0)
        game.command('set_logistics',dict(city='xiangyang',policy=dict(target_city='nanjun')),game.revision)
        return game

    def test_target_loss_at_a_city_keeps_escort_out_of_enemy_destination(self):
        game=self.game(long=True)
        old=game.state.cities['xiangyang'].grain
        self.fixture.dispatch(game)
        game.state.cities['nanjun'].owner='wei'
        game._reconcile_factions(game.state)
        self.fixture.sync(game)
        game._complete_turn(game.state)
        self.assertFalse(logistics._pool(game.state)['convoys'])
        self.assertIn(999,game.state.cities['xiangyang'].roster.officer_ids)
        receipts=logistics._pool(game.state)['reports']
        self.assertFalse(any(entry['kind']=='transport_arrived' for entry in receipts))
        self.assertGreater(game.state.cities['xiangyang'].grain,old-1000)
        game.validate(game.state)

    def test_same_return_route_keeps_journey_rations_and_rng(self):
        game=self.game(long=True)
        self.fixture.dispatch(game)
        self.fixture.advance_due(game)
        row,=logistics._pool(game.state)['convoys']
        self.assertTrue(row['delivery_done'])
        self.assertEqual(row['return_leg'],1)
        journey=row['journeys'][-1]
        source=march_supply.current_city(journey)
        receipts=deepcopy(row['cargo_ledger'])
        supplies=deepcopy(journey['supply'])
        rng=deepcopy(game.state.rng)
        with grain_units.using(game.state):
            logistics._return(game,game.state,row,'retreat')
        self.assertEqual(len(row['journeys']),2)
        self.assertEqual(journey['supply'],supplies)
        self.assertEqual(row['cargo_ledger'],receipts)
        self.assertEqual(game.state.rng,rng)
        self.assertEqual(march_supply.current_city(journey),source)
        for compact in (False,True):
            restored=Headless(game.catalog,record_journal=False)
            restored.load_save(game.export_save(compact=compact),0)
            self.assertEqual(restored.to_dict(),game.to_dict())

    def test_cargo_can_be_reserved_for_real_return_before_delivery(self):
        game=self.game()
        self.fixture.dispatch(game,cargo=dict(grain=400,gold=0,reserves=0))
        row,=logistics._pool(game.state)['convoys']
        with grain_units.using(game.state):
            book=row['journeys'][-1]['supply']
            book['remaining']=0  # Isolate the settlement decision from the prior meals.
            initial=row['cargo']['grain']
            target=game.state.cities[row['target']]
            logistics._reserve_before_unload(game,game.state,row,target)
            reserved=book['remaining']
            self.assertGreater(reserved,0)
            self.assertEqual(cargo:=row['cargo']['grain'],initial-reserved)
            stock=target.grain
            with patch.object(logistics,'_reserve_before_unload',return_value=None):
                logistics._unload(game,game.state,row,target)
            self.assertEqual(target.grain,stock+cargo)
            self.assertEqual(row['delivered']['grain']+reserved,initial)

    def test_exact_day_work_for_1000_weather_transport_cases(self):
        game=self.game()
        state=game.state
        zone='liaodong'
        region=state.extension[weather.POOL]['regions'][zone]
        rng=random.Random(22101)
        for _ in range(1000):
            severity=rng.randrange(4)
            region.update(severity=severity,depth=rng.randrange(31))
            work=rng.randrange(1,travel.QUANTA*5)
            parts=(travel.Part('plain',work,zone,None),)
            position=rng.randrange(work)
            step=travel.day(state,parts,position,rest_region=zone)
            self.assertGreater(step.moved,0)
            self.assertLessEqual(step.moved,min(work-position,travel.QUANTA))
            self.assertEqual(work-position-step.moved,work-(position+step.moved))
            self.assertGreaterEqual(step.ration,rules.RATION_SCALE)

    def test_1000_real_ration_bag_and_cargo_protection_values(self):
        game=self.game()
        state=game.state
        rng=random.Random(22102)
        quote=game._travel_path(state,'xiangyang','nanjun','shu','land')
        with grain_units.using(state):
            for _ in range(1000):
                units=rng.randrange(100,100_001)
                q=rng.randrange(travel.QUANTA*quote['days'])
                credit=rng.randrange(5_000_000)
                forecast=winter_transport.protected_cost(game,state,quote,units,position=q,credit=credit)
                _,weight,_=travel.checkpoint_forecast(game,state,quote,position=q)
                expect=rules.ceil_div(max(0,units*weight-credit),5_000_000)
                self.assertEqual(forecast['meal'],expect)
                self.assertEqual(forecast['safety'],rules.ceil_div(expect,10))
                bag=rng.randrange(100_000); cargo=rng.randrange(100_000)
                shifted=min(cargo,max(0,expect+forecast['safety']-bag))
                self.assertEqual((bag+shifted)+(cargo-shifted),bag+cargo)
                self.assertGreaterEqual(cargo-shifted,0)

    def test_1000_checkpoint_ration_deadlines_and_public_forecast_reads(self):
        game=self.game()
        state=game.state
        quote=game._travel_path(state,'xiangyang','nanjun','shu','land')
        parts=travel.plan(game,quote)
        rng=random.Random(22103)
        end=quote['days']*travel.QUANTA
        region=game.catalog.climate.cities['nanjun']['climate_region_id']
        for _ in range(1000):
            snow=rng.randrange(4)
            for p in parts:
                state.extension[weather.POOL]['regions'][p.region].update(severity=snow,depth=7 if snow else 0)
            starts=rng.randrange(end)
            horizon=rng.randrange(1,6)
            first=travel.checkpoint_horizon_weight(game,state,quote,horizon,position=starts,stop=end)
            prior=travel.checkpoint_horizon_weight(game,state,quote,horizon-1,position=starts,stop=end)
            self.assertGreaterEqual(first-prior,rules.RATION_SCALE)
            if quote['days']==quote['routes'][0]['days']:
                today=travel.day(state,parts,starts,rest_region=region,stop=end)
                self.assertAlmostEqual(travel.checkpoint_horizon_weight(game,state,quote,1,position=starts,stop=end),
                                       today.ration,delta=1)
        original=deepcopy(state.extension[weather.POOL])
        rng_before=deepcopy(state.rng)
        game.state.month=12
        normal=travel.seasonal_forecast(game,state,quote)
        stress=travel.seasonal_forecast(game,state,quote,pressure=True)
        self.assertGreaterEqual(stress['extra_weight'],normal['extra_weight'])
        self.assertEqual(state.extension[weather.POOL],original)
        self.assertEqual(state.rng,rng_before)

    def test_arrival_hazard_strength_is_valid_only_after_completed_weather_work(self):
        original={'249':10000}
        reduced={'249':8000}
        risk=dict(applied=True,after=reduced)
        supplies=dict(start_tick=0,clock_tick=20,route_days=10,
                      winter=dict(work=10*travel.QUANTA),starvation=[],
                      periods=[dict(days=[[10100,0,travel.QUANTA,0]]*10),
                               dict(days=[[8100,0,0,0]]*10)],
                      ration_manifests=[dict(tick=1,troops=original,reserves=0),
                                        dict(tick=11,troops=reduced,reserves=0)])
        march_supply.validate_strength_manifests(supplies,original,[risk])
        supplies['ration_manifests'][1]['tick']=10
        with self.assertRaisesRegex(ValueError,'actual travelling manifest'):
            march_supply.validate_strength_manifests(supplies,original,[risk])

    def test_unchanged_weather_sequence_for_revision_22_and_221(self):
        old=self.game(version=22)
        new=self.game()
        self.assertEqual(old.state.extension[weather.POOL]['seed'],new.state.extension[weather.POOL]['seed'])
        for tick in range(1,1001):
            for game in (old,new):
                weather.advance(game,game.state,tick)
            for name in ('regions','ice'):
                self.assertEqual(old.state.extension[weather.POOL][name],new.state.extension[weather.POOL][name])


if __name__=='__main__':
    unittest.main()
