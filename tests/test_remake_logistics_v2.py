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

from remake import logistics_rules as rules, march_supply
from remake.campaign import Campaign, Catalog
from remake.march_core import enabled, using_backend
from remake.route_hazards import evaluate_leg


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


if __name__ == '__main__':
    unittest.main()
