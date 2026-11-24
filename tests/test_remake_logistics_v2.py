"""Versioned logistics arithmetic and replay checks."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))

from remake import logistics, logistics_rules as rules, march_supply
from test_remake_march_supply import supply_catalog
from remake.campaign import Campaign, Catalog
from remake.march_core import enabled, using_backend
from remake.route_hazards import evaluate_leg
from remake.transfer_supply import minimum_grain
from remake.travel import TravelCampaign


def land(days, terrain='plain'):
    return dict(id='a:b:land', mode='land', terrain=terrain, days=days,
                **{'from':'a', 'to':'b'})


def mixed():
    return dict(days=10, path=['a','b'], routes=[dict(
        id='a:b:river', mode='river', days=10,
        land_access_days=2, embark_days=1, water_days=7, **{'from':'a','to':'b'},
        river_segments=[
            dict(flow='downstream', distance_km=150, speed_km_per_day=50),
            dict(flow='upstream', distance_km=80, speed_km_per_day=20),
        ])])


class MarchRationTests(unittest.TestCase):
    def test_requested_standard_rations(self):
        cases = [('plain',7,1768),('plain',10,2525),('mountain',20,6060),
                 ('desert',22,6666),('river_downstream',7,1485),('river_still',10,2222),
                 ('river_upstream',12,2788),('sea',30,6666),('node_wait',10,2020)]
        for mode,days,expected in cases:
            with self.subTest(mode=mode,days=days):
                cost = rules.ceil_div(rules.charge(10100,[(mode,days*rules.DAY_TICKS)],0,days),
                                      50*rules.RATION_SCALE)
                self.assertEqual(cost,expected)
        self.assertEqual(march_supply.quote_supply(mixed(),10_000,1,version=rules.CURRENT),2293)

    def test_daily_weight_and_save_validation(self):
        state = SimpleNamespace(turn=1, extension={rules.FIELD:2},
            officers={1:SimpleNamespace(troops=979)}, cities={city:SimpleNamespace(owner='han') for city in ('a','b')})
        quote = mixed()
        book = march_supply.create(state,[1],quote)
        # The next battle need not discard a fractional unit or repeat a day.
        expected = march_supply.estimate(state,[1],quote)
        self.assertEqual(march_supply.consume(book,1,quote,2),expected)
        self.assertEqual(march_supply.consume(book,1,quote,2),0)
        self.assertEqual(book['consumed'],expected)
        self.assertEqual(book['credit_units'],expected * march_supply.book_denominator(book) -
                         rules.charge(1079,rules.plan(quote),0,10))
        march_supply.validate(book,quote,1,2,version=rules.CURRENT)
        changed = deepcopy(book)
        changed['credit_units'] += 1
        with self.assertRaises(ValueError):
            march_supply.validate(changed,quote,1,2,version=rules.CURRENT)
        old_state = SimpleNamespace(**dict(vars(state),extension={}))
        legacy = march_supply.create(old_state,[1],quote)
        march_supply.consume(legacy,1,quote,2)
        march_supply.validate(legacy,quote,1,2,version=rules.LEGACY)
        self.assertEqual(legacy['consumed'],216)

    def test_real_leg_backends_and_mixed_boundaries(self):
        catalog = Catalog(ROOT/'game/data/campaigns/208-10.json')
        route = next(row for row in catalog.data['travel_routes']
                     if row['id']=='xiangyang:jiangxia:river')
        directions = [('xiangyang','jiangxia'),('jiangxia','xiangyang')]
        def quotes(backend):
            with using_backend(backend):
                return [evaluate_leg(catalog.data,route,a,b,10) for a,b in directions]
        reference = quotes('python')
        if enabled():
            self.assertEqual(reference,quotes('rust'))
        for leg in reference:
            parts = rules.leg_parts(leg,catalog.data['travel_rules'])
            self.assertEqual(sum(value for _,value in parts),leg['days']*rules.DAY_TICKS)
            self.assertEqual(sum(rules.weight(parts,day,1) for day in range(leg['days'])),
                             rules.weight(parts))
            self.assertGreaterEqual(len({mode for mode,_ in parts if mode.startswith('river_')}),2)

    def test_seeded_ration_properties(self):
        randomizer = random.Random(20261124)
        modes = tuple(rules.MARCH_SUPPLY_PERCENT)
        divisor = 50 * rules.RATION_SCALE
        for _ in range(1000):
            parts = [(randomizer.choice(modes),randomizer.randint(1,5)*rules.DAY_TICKS)
                     for _ in range(randomizer.randint(1,8))]
            people = [randomizer.randint(0,110000) for _ in range(sum(t for _,t in parts)//rules.DAY_TICKS)]
            credits = total = 0
            independent = Fraction()
            for day, units in enumerate(people):
                charge = rules.charge(units,parts,day,1)
                self.assertGreaterEqual(charge,units*rules.RATION_SCALE)
                paid = rules.ceil_div(charge-credits,divisor)
                self.assertGreaterEqual(paid,0)
                credits += paid*divisor-charge
                total += paid
                independent += Fraction(charge,divisor)
            self.assertEqual(total,-(-independent.numerator//independent.denominator))
            self.assertIn(credits,range(divisor))

    def test_new_and_pre_logistics_save_round_trip(self):
        class PreLogisticsCampaign(Campaign):
            def _new(self,*args,**kwargs):
                state = super()._new(*args,**kwargs)
                del state.extension[rules.FIELD]
                return state
        source = Catalog(ROOT/'game/data/campaigns/208-10.json')
        for game_type,version in ((PreLogisticsCampaign,1),(Campaign,2)):
            game = game_type(source)
            game.command('new',dict(faction='shu',seed=2026),0)
            self.assertEqual(rules.version(game.state),version)
            for compact in (False,True):
                saved = game.export_save(compact=compact)
                restored = Campaign(source)
                restored.load_save(saved,0)
                self.assertEqual(restored.export_save(compact=compact),saved)
                self.assertEqual(rules.version(restored.state),version)


class CargoLossTests(unittest.TestCase):
    def test_requested_cargo_delivery_sizes(self):
        expected = dict(plain=86_039,mountain=73_970,desert=63_546,river_downstream=97_044,
                        river_still=95_597,river_upstream=94_171,sea=94_171,node_wait=100_000,embark=100_000)
        for terrain, amount in expected.items():
            parts = [(terrain,30*rules.DAY_TICKS)]
            self.assertEqual(rules.estimate_cargo(100_000,parts,30)[0],amount)
        parts=[('plain',250*rules.DAY_TICKS)]
        self.assertEqual(rules.estimate_cargo(1,parts,250)[0],0)
        self.assertEqual(rules.estimate_cargo(0,parts,250,remainder=3),(0,3))

    def test_one_thousand_seeded_cargo_flows(self):
        rng=random.Random(20261125)
        modes=tuple(rules.CARGO_GRAIN_LOSS_BPS)
        for _ in range(1000):
            dispatched=rng.randrange(100_001)
            remaining=dispatched
            received=unloaded=rations=weather=loss=credit=0
            for _ in range(rng.randrange(1,50)):
                mode=rng.choice(modes)
                share=rng.randint(0,rules.DAY_TICKS)
                rate=rules.CARGO_GRAIN_LOSS_BPS[mode]*share
                rations_now=min(remaining,rng.randrange(10))
                rations+=rations_now;remaining-=rations_now
                direct=Fraction(remaining*rate+credit,rules.LOSS_SCALE)
                lost,credit=rules.cargo_loss(remaining,rate,credit)
                self.assertEqual(lost,direct.numerator//direct.denominator)
                remaining-=lost;loss+=lost
                if rng.randrange(6)==0:
                    add=rng.randrange(500)
                    received+=add;remaining+=add
                    remaining,weather_now=divmod(remaining,2)[0],(remaining+1)//2
                    weather+=weather_now
                    out=remaining//4
                    remaining-=out;unloaded+=out
                self.assertGreaterEqual(remaining,0)
                self.assertEqual(dispatched+received,rations+weather+loss+unloaded+remaining)

    def test_real_dispatch_roundtrip_and_atomic_validation(self):
        game=Campaign(supply_catalog(transfer=True,days=25))
        game.command('new',dict(faction='shu',seed=2026),0)
        payload=dict(source='xiangyang',target='nanjun',officers=[999],
                     cargo=dict(grain=500,gold=0,reserves=0),route_mode='land')
        game.command('dispatch_transport',payload,game.revision)
        for _ in range(3):
            game._complete_turn(game.state)
            game.validate(game.state)
        convoy=game.state.extension['logistics']['convoys'][0]
        check=logistics.grain_receipt(convoy)
        expected,credit=rules.estimate_cargo(500,[('plain',25*rules.DAY_TICKS)],25)
        self.assertEqual((convoy['cargo']['grain'],convoy[logistics.LOSS_FIELD]),(expected,credit))
        self.assertEqual(check['cargo_route_loss'],500-expected)
        self.assertTrue(logistics.valid_grain_receipt(check))
        for compact in (False,True):
            data=game.export_save(compact=compact)
            restored=Campaign(game.catalog)
            restored.load_save(data,0)
            self.assertEqual(restored.export_save(compact=compact),data)
        old=game.export_save()
        game._process_march_supply(game.state)
        self.assertEqual(game.export_save(),old)
        game.state.phase='arrivals'
        game.command('arrivals',{},game.revision)
        received=next(report['details'] for report in game.state.extension['logistics']['reports']
                      if report['kind']=='transport_arrived')['grain_receipt']
        self.assertEqual(received['cargo_delivered'],expected)
        self.assertEqual(received['cargo_route_loss'],500-expected)
        self.assertTrue(logistics.valid_grain_receipt(received))


def route_case(*,plain_days=10,water_days=10,terrain='plain',stock=100_000,one_way=False):
    ground=land(plain_days,terrain)
    ground.update(distance_km=plain_days*30,land_km=plain_days*30)
    water=dict(id='a:b:river',mode='river',terrain='river',**{'from':'a','to':'b'},
               distance_km=water_days*50,land_km=0,one_way=one_way,
               river_segments=[dict(distance_km=water_days*50,downstream_from='a')])
    ruleset=dict(speeds={'plain':30},river_speeds={'downstream':50,'upstream':20},river_embark_days=0)
    data=dict(travel_rules=ruleset,travel_hazards={},travel_routes=[ground,water])
    class TestMap(TravelCampaign):
        catalog=SimpleNamespace(data=data)
        def _known_routes(self,state):
            return data['travel_routes']
    city=lambda name:SimpleNamespace(id=name,owner='shu',grain=stock)
    state=SimpleNamespace(extension={rules.FIELD:2},cities={key:city(key) for key in ('a','b')},
                          officers={1:SimpleNamespace(troops=10_000)},month=10)
    return TestMap(),state,ground,water


class CheapestRouteTests(unittest.TestCase):
    def test_select_longer_downstream_and_respect_directed_routes(self):
        game,state,ground,water=route_case(plain_days=8,terrain='mountain',one_way=True)
        result=minimum_grain(game,state,'a','b','shu',[1])
        self.assertEqual((result['days'],result['routes'][0]['mode']),(10,'river'))
        reverse=minimum_grain(game,state,'b','a','shu',[1])
        self.assertEqual(reverse['routes'][0]['id'],ground['id'])
        state.cities['b'].grain=0
        self.assertIsNone(minimum_grain(game,state,'b','a','shu',[1]))

    def test_similar_cost_route_switches_when_loading_cargo(self):
        game,state,ground,water=route_case(water_days=12)
        state.officers[1].troops=900
        self.assertEqual(minimum_grain(game,state,'a','b','shu',[1])['routes'][0]['id'],ground['id'])
        self.assertEqual(minimum_grain(game,state,'a','b','shu',[1],cargo=10_000)['routes'][0]['id'],water['id'])

    def test_one_thousand_seeded_routes_against_independent_direct_oracle(self):
        rng=random.Random(20261126)
        for _ in range(1000):
            days, water_days = rng.randint(1,30),rng.randint(1,30)
            terrain = rng.choice(('plain','mountain','desert'))
            stock = rng.randrange(26_000)
            cargo = rng.randrange(10_000)
            soldiers = rng.randrange(11_000)
            reserve = rng.randrange(1200)
            game,state,ground,water=route_case(plain_days=days,water_days=water_days,
                                               terrain=terrain,stock=stock)
            state.officers[1].troops=soldiers
            options=[]
            for raw,elapsed,percent,bps in ((ground,days,125 if terrain=='plain' else 150,
                                               {'plain':50,'mountain':100,'desert':150}[terrain]),
                                            (water,water_days,105,10)):
                required=-(-(soldiers+100+reserve)*elapsed*percent//5000)
                if required+cargo>stock:
                    continue
                delivered,carry=cargo,0
                for day in range(elapsed):
                    lost,carry=divmod(delivered*bps+carry,10_000)
                    delivered-=lost
                options.append((required+cargo-delivered,elapsed,raw['id']))
            found=minimum_grain(game,state,'a','b','shu',[1],cargo=cargo,reserves=reserve)
            self.assertEqual(found['routes'][0]['id'] if found else None,
                             min(options)[2] if options else None)


if __name__ == '__main__':
    unittest.main()
