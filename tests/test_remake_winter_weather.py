import json
import random
import sys
import unittest
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))

from remake import battle_reinforcements as reinforcements, logistics_rules as rules, march_supply, route_hazards
from remake import winter_travel as travel, winter_weather as weather
from remake.campaign import Campaign,Catalog
from remake.climate_regions import REGIONS
from remake.grain_units import using
from remake.march_core import using_backend


class Headless(Campaign):
    def view(self):
        return {}


class WinterWeather(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'game/data/campaigns/184-02.json')

    def game(self,stage=5,seed=2026,owner='observer'):
        game=Headless(self.catalog)
        with weather.experiment(stage):
            game.command('new',dict(faction=owner,seed=seed),0)
        return game

    def test_probability_and_duration_1000_regional_samples(self):
        seen=[0,0,0,0]
        for seed in range(1,1001):
            key=weather.seed_for(seed)
            row=weather.snowfall(key,'liaodong',200,1,0)
            strength,start,end=row
            seen[strength]+=1
            if strength:
                self.assertLessEqual(1,start)
                self.assertLessEqual(end,10)
                self.assertIn(end-start+1,range(weather.DURATION[strength][0],weather.DURATION[strength][1]+1))
            self.assertEqual(row,weather.snowfall(key,'liaodong',200,1,0))
            for zone in ('lingnan','southern_basins','tropical_islands'):
                self.assertEqual(weather.snowfall(key,zone,200,1,0),(0,0,0))
            self.assertEqual(weather.snowfall(key,'liaodong',200,4,0),(0,0,0))
        self.assertTrue(350 < seen[0] < 460)
        self.assertTrue(110 < seen[2] < 190)
        self.assertTrue(14 < seen[3] < 48)

    def test_1000_daily_accumulation_transitions_and_idempotence(self):
        game=self.game()
        state=game.state
        initial=deepcopy(state.rng)
        winter_starts=set()
        for tick in range(1,1001):
            previous=deepcopy(state.extension[weather.POOL]['regions'])
            weather.advance(game,state,tick)
            pool=state.extension[weather.POOL]
            year,month,day=weather.date_at(game.catalog.data,tick)
            for key,row in pool['regions'].items():
                expected=(min(30,previous[key]['depth']+weather.SNOWFALL[row['severity']]) if row['severity']
                          else max(0,previous[key]['depth']-weather.MELT[row['cold']]))
                self.assertEqual(row['depth'],expected)
                if month==3 and day==30 and REGIONS[key][3] and year>184:
                    self.assertTrue(row['snow_seen'])
                self.assertLessEqual(weather.road_weather(row),max(2,row['severity']))
                if month==1 and day==1 and key=='liaodong':
                    winter_starts.add(row['winter'])
            snapshot=deepcopy(pool)
            weather.advance(game,state,tick)
            weather.view(game,state)
            self.assertEqual(state.extension[weather.POOL],snapshot)
        self.assertEqual(state.rng,initial)
        self.assertGreaterEqual(len(winter_starts),2)

    def test_1000_dynamic_day_and_grain_conservation_samples(self):
        state=self.game().state
        random_source=random.Random(2201)
        region=state.extension[weather.POOL]['regions']['liaodong']
        mode_choices=('plain','mountain','desert','sea','river_downstream','embark')
        for _ in range(1000):
            strength=random_source.randrange(4)
            depth=random_source.randrange(31)
            region.update(severity=strength,depth=depth)
            mode=random_source.choice(mode_choices)
            road=weather.road_weather(region) if mode in ('plain','mountain','desert') else strength
            a=travel.Part(mode,travel.QUANTA*2,'liaodong',None)
            day=travel.day(state,(a,),0,rest_region='liaodong')
            expected=Fraction(weather.WARMTH[strength],100) * (
                1+Fraction(rules.MARCH_SUPPLY_PERCENT[mode]-100,100)*Fraction(weather.SURCHARGE[road],100))
            self.assertEqual(day.ration,int(expected*rules.RATION_SCALE))
            time_multiplier=weather.TIME_PERCENT[road] if mode in ('plain','mountain','desert') else 100
            self.assertEqual(day.moved,travel.QUANTA*100//time_multiplier)
            b=travel.Part('plain',travel.QUANTA,'lingnan',None)
            mixed=travel.day(state,(a._replace(work=travel.QUANTA//2),b),0,rest_region='lingnan')
            self.assertLessEqual(mixed.moved,travel.QUANTA)
            self.assertGreater(mixed.moved,0)
            load=random_source.randrange(1,1_000_000)
            carry=random_source.randrange(rules.LOSS_SCALE)
            lost,remainder=rules.cargo_loss(load,mixed.cargo,carry)
            self.assertTrue(0<=lost<=load and 0<=remainder<rules.LOSS_SCALE)
            self.assertEqual(load*mixed.cargo+carry,lost*rules.LOSS_SCALE+remainder)
            old=random_source.randrange(2_500_000)
            bag=dict(schema=march_supply.WEIGHTED_SCHEMA,credit_units=old,remaining=100000,consumed=0,
                     elapsed_days=0,shortage_days=0,shortage_streak=0,base_consumed=0)
            units=random_source.randrange(1,100_000)
            with using(state):
                used,missing=march_supply._meal(bag,units,mixed.ration)
                self.assertEqual(bag['remaining']+used,100000)
                self.assertEqual(bag['credit_units'],old+used*march_supply.book_denominator(bag)-units*mixed.ration+missing)

    def test_1000_ice_steps_and_hysteresis(self):
        random_source=random.Random(2202)
        for _ in range(1000):
            index=random_source.randrange(10001)
            old=weather.ice_state(index,random_source.randrange(4))
            cold=random_source.randrange(4)
            sensitivity=random_source.choice((0,50,100,150))
            new,status=weather.ice_step(index,old,cold,sensitivity)
            expected=min(10000,max(0,index+(-6,-2,3,5)[cold]*(sensitivity if cold>=2 else 100)))
            self.assertEqual(new,expected)
            if cold>=2:
                self.assertGreaterEqual(status,old)
            else:
                self.assertLessEqual(status,old)
            self.assertEqual(weather.ice_state(new,status),status)
        index=status=0
        reached=[]
        for _ in range(15):
            index,status=weather.ice_step(index,status,3,100)
            reached.append(status)
        self.assertEqual(set(reached),{0,1,2,3})
        self.assertEqual(weather.ice_state(5000,3),3)
        self.assertEqual(weather.ice_state(4999,3),2)
        for _ in range(18):
            index,status=weather.ice_step(index,status,0,100)
        self.assertEqual((index,status),(0,0))

    def test_mixed_reach_freeze_wait_and_resume(self):
        game=self.game()
        state=game.state
        route=next(raw for raw in self.catalog.climate.routes.values()
                   if any(p['reach_id']=='yellow:jincheng:shuofang' for p in raw.get('river_segments', ())))
        source,target=route['from'],route['to']
        if not route_hazards.route_allowed(self.catalog.data,route,source,target):
            source,target=target,source
        leg=route_hazards.evaluate_leg(self.catalog.data,route,source,target,2)
        quote=game._quote([source,target],[leg])
        parts=travel.plan(game,quote)
        reach='yellow:jincheng:shuofang'
        self.assertTrue(parts and any(part.reach==reach for part in parts))
        region=parts[-1].region
        weather_pool=state.extension[weather.POOL]
        weather_pool['ice'][reach].update(index=6500,state=3)
        self.assertTrue(weather.blocked(state,route))
        self.assertIsNone(travel.forecast(game,state,quote)[0])
        self.assertFalse(any(r['id']==route['id'] for r in game._known_routes(state)))
        sailed=0
        for part in parts:
            if part.mode.startswith('river_'):
                break
            sailed+=part.work
        position=sailed+travel.QUANTA//4
        today=travel.day(state,parts,position,rest_region=region,on_leg=True)
        self.assertEqual((today.moved,today.blocked),(0,reach))
        self.assertGreater(today.ration,0)
        weather_pool['ice'][reach].update(index=4000,state=2)
        thawed=travel.day(state,parts,position,rest_region=region,on_leg=True)
        self.assertEqual(thawed.moved,travel.QUANTA//2)
        self.assertIsNone(thawed.blocked)
        self.assertIn(route['id'],{raw['id'] for raw in game._known_routes(state)})
        south=[r for r in self.catalog.climate.reaches if r.startswith('yangtze:')]
        self.assertTrue(south)
        self.assertFalse(any(r in weather_pool['ice'] for r in south))

    def test_real_route_daily_ledger_keeps_cargo_and_people_separate_on_ice(self):
        game=self.game()
        state=game.state
        ident=next(i for i,o in state.officers.items() if o.alive and o.troops and o.faction_id)
        owner=state.officers[ident].faction_id
        reach='yellow:jincheng:shuofang'
        route=next(raw for raw in self.catalog.climate.routes.values() if raw['id']=='jincheng:shuofang:river')
        leg=route_hazards.evaluate_leg(self.catalog.data,route,'jincheng','shuofang',2)
        quote=game._quote(['jincheng','shuofang'],[leg])
        parts=travel.plan(game,quote)
        dock_work=next(sum(part.work for part in parts[:i]) for i,p in enumerate(parts)
                       if p.mode.startswith('river_'))
        pool=state.extension[weather.POOL]
        cargo={'grain':1500,'reserves':10}
        stock=cargo['grain']
        cargo_loss=carry=0
        def loss(rate,tick):
            nonlocal cargo_loss,carry
            lost,carry=rules.cargo_loss(cargo['grain'],rate,carry)
            cargo['grain']-=lost
            cargo_loss+=lost
        with using(state):
            bag=march_supply.create(state,[ident],quote,cargo['reserves'],game=game,initial_grain=100_000)
            row=dict(id=1,source='jincheng',target='shuofang',owner=owner,officers=[ident],quote=quote,supply=bag)
            tick=0
            def step():
                nonlocal tick
                tick+=1
                march_supply.advance_unit(game,state,row,row,absolute_tick=tick,cargo=cargo,on_cargo_day=loss)
            while travel.work(bag)<=dock_work:
                step()
            self.assertIsNone(march_supply.current_city(row))
            moved,paid=travel.work(bag),bag['consumed']
            pool['ice'][reach].update(index=6500,state=3)
            for _ in range(4):
                step()
            self.assertEqual(travel.work(bag),moved)
            self.assertEqual(bag['winter']['blocked'],reach)
            self.assertGreater(bag['consumed'],paid)
            pool['ice'][reach].update(index=4000,state=2)
            step()
            self.assertGreater(travel.work(bag),moved)
            self.assertIsNone(bag['winter']['blocked'])
            while tick%10:
                step()
            march_supply.validate(bag,quote,1,tick//10+1,game=game)
            self.assertEqual(stock,cargo['grain']+cargo_loss)
            self.assertEqual(bag['consumed']+bag['remaining'],bag['loaded'])

    def test_reinforcement_withdrawal_before_next_strategic_day(self):
        game=self.game()
        state=game.state
        for region in state.extension[weather.POOL]['regions'].values():
            region.update(severity=2,depth=8)
        for raw in game.catalog.climate.routes.values():
            source,target=raw['from'],raw['to']
            if (raw['mode']=='land' and state.cities[source].roster.officer_ids
                    and route_hazards.route_allowed(self.catalog.data, raw, source, target)
                    and route_hazards.route_allowed(self.catalog.data, raw, target, source)):
                leg=route_hazards.evaluate_leg(self.catalog.data,raw,source,target,state.month)
                if leg['days']>=8:
                    break
        else:
            self.fail('Expected a two-way reinforcement route')
        profile=reinforcements._profile(game,state,leg)
        reserve=100_000
        ident=state.cities[source].roster.officer_ids[0]
        book=dict(parts=[list(part) for part in rules.leg_parts(leg,march_supply.travel_rules(game))],
                  credit=0,remaining=reserve,meals=[])
        pending=dict(route=raw['id'],source=source,owner=state.cities[source].owner,officers=[ident],
                     departed=1,days=len(profile['meals']),grain=reserve,winter=profile,rations=book)
        battle=dict(target=target,round=8,extended={reinforcements.FIELD:{'pending':[pending]}})
        with using(state):
            reinforcements.withdraw(state,battle,game=game)
            row=state.extension[reinforcements.RETURNS][0]
            self.assertLess(row['remaining'],7)
            self.assertEqual(row['winter']['limit'],sum(work for work,_ in profile['meals'][:7]))
            self.assertEqual(row['grain'],book['remaining'])
            reinforcements.validate_returns(game,state)

    def test_normal_and_compact_resume_identical_weather(self):
        game=self.game(seed=2027)
        for _ in range(2):
            game.command('observe_turn',{},game.revision)
        for compact in (False,True):
            restored=Headless(self.catalog)
            data=json.loads(json.dumps(game.export_save(compact=compact)))
            restored.load_save(data,0)
            self.assertEqual(restored.to_dict(),game.to_dict())
            restored.command('observe_turn',{},restored.revision)
            probe=Headless(self.catalog)
            probe.load_save(data,0)
            probe.command('observe_turn',{},probe.revision)
            self.assertEqual(restored.export_save(compact=True)['checksum'],probe.export_save(compact=True)['checksum'])

    def test_high_intensity_winter_remains_replayable(self):
        original_draw=weather.draw

        def severe_winter(seed,region,year,month,index,field,limit):
            if month in REGIONS[region][0] and field in ('snow','severity','cold'):
                return 0 if field=='snow' else limit-1
            return original_draw(seed,region,year,month,index,field,limit)

        with patch.multiple(weather,draw=severe_winter,MELT=(2,1,0,0)):
            weather.snowfall.cache_clear()
            try:
                game=self.game(seed=22822)
                for _ in range(4):
                    game.command('observe_turn',{},game.revision)
                pool=game.state.extension[weather.POOL]
                self.assertTrue(any(row['depth']==weather.MAX_DEPTH for row in pool['regions'].values()))
                frozen={key for key,row in pool['ice'].items() if row['state']==3}
                self.assertTrue(frozen)
                for route in game.catalog.climate.routes.values():
                    if any(reach['reach_id'] in frozen for reach in route.get('river_segments',())):
                        self.assertTrue(weather.blocked(game.state,route))
                restored=Headless(self.catalog)
                restored.load_save(game.export_save(compact=True),0)
                for instance in (game,restored):
                    for _ in range(3):
                        instance.command('observe_turn',{},instance.revision)
                self.assertEqual(restored.export_save(compact=True),game.export_save(compact=True))
            finally:
                weather.snowfall.cache_clear()

    def test_weather_only_observer_is_read_only_and_backends_match(self):
        frames=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                try:
                    off,weather_only=self.game(0),self.game(1)
                    for _ in range(3):
                        off.command('observe_turn',{},off.revision)
                        with weather.experiment(1,observe=lambda kind,row:frames.append(row['tick']) if kind=='region' else None):
                            weather_only.command('observe_turn',{},weather_only.revision)
                    projected=weather_only.to_dict()
                    for key in (weather.POOL,weather.FIELD):
                        del projected['extension'][key]
                    self.assertEqual(off.to_dict(),projected)
                except Exception as error:
                    from remake.march_core import CoreUnavailable
                    if backend=='rust' and isinstance(error,CoreUnavailable):
                        self.skipTest('Run game/build_march_core.py for the native parity check')
                    raise
                if backend=='python':
                    canonical=weather_only.to_dict()
                else:
                    self.assertEqual(weather_only.to_dict(),canonical)
        self.assertEqual(len(frames),2*30*len(REGIONS))

    def test_active_winter_backend_and_weather_budget_breakdown(self):
        catalog=Catalog(ROOT/'game/data/campaigns/190-01.json')
        states=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=Headless(catalog)
                game.command('new',dict(faction='observer',seed=2027,weather_rules_version=22),0)
                for _ in range(3):
                    game.command('observe_turn',{},game.revision)
                states.append(game.to_dict())
        self.assertEqual(*states)
        self.assertTrue(any(row['snow_seen'] for row in states[0]['extension'][weather.POOL]['regions'].values()))
        state=game.state
        route=next(r for r in game._known_routes(state) if r['mode']=='land' and
                   weather.stage(state) and catalog.climate.cities[r['from']]['snow_enabled'])
        source,target=route['from'],route['to']
        if not route_hazards.route_allowed(catalog.data,route,source,target):
            source,target=target,source
        leg=route_hazards.evaluate_leg(catalog.data,route,source,target,state.month)
        quote=game._quote([source,target],[leg])
        with using(state):
            view=travel.preview(game,state,quote,units=10100,cargo=1500)
        self.assertEqual(view['extra_grain'],view['winter_warmth']+view['winter_route_overhead']+view['winter_delay_grain'])
        self.assertEqual(view['normal_days'],leg['days'])


if __name__=='__main__':
    unittest.main()
