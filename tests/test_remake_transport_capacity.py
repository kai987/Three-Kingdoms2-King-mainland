"""Versioned convoy limits, route capacity and actual departure accounting."""
from copy import deepcopy
import json
from pathlib import Path
from random import Random
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from remake import command_books, grain_units, logistics, logistics_rules, transport_capacity as capacity
from remake.campaign import Campaign, Catalog
from remake.errors import GameError
from remake.transport_emergency import _hazard_risk
from remake import winter_weather
import test_remake_logistics as controlled
import test_remake_regional_market as regional

SOURCE, TARGET = 'xiangyang', 'nanjun'


def options(**features):
    return dict.fromkeys(capacity.FEATURES,False) | features


def land(terrain='plain'):
    return dict(id='a:b:land',mode='land',terrain=terrain,days=12,distance_km=360,**{'from':'a','to':'b'})


def river(*, access=0, flow='downstream'):
    return dict(id='b:c:river',mode='river',terrain='river',days=13+access,
        land_access_days=access,embark_days=2,water_days=11,**{'from':'b','to':'c'},
        river_segments=[dict(flow=flow,distance_km=330,speed_km_per_day=30,reach_id='test-river')])


def sea():
    return dict(id='c:d:sea',mode='sea',terrain='sea',**{'from':'c','to':'d'},
                days=27,embark_days=2,land_access_days=0)


def shape_state(*, features=None):
    extension={
        grain_units.FIELD:10,grain_units.RATION_FIELD:2,logistics_rules.FIELD:2,
        'logistics':dict(convoys=[],cities={'a':{'last_dispatch_turn':0}})
    }
    state=SimpleNamespace(extension=extension,cities={'a':SimpleNamespace(id='a',owner='shu')},turn=1)
    if features is not None:
        capacity.initialize(state,303,features)
    return state


class CapacityArithmeticTests(TestCase):
    def test_standard_loads_and_ice(self):
        self.assertEqual(capacity.effective_cargo(50_000,8_000,50_000,70_000,10**8),42_000)
        self.assertEqual(capacity.effective_cargo(100_000,6_000,100_000,120_000,10**8),94_000)
        self.assertEqual(capacity.effective_cargo(100_000,6_000,50_000,120_000,10**8),50_000)
        self.assertEqual(capacity.effective_cargo(40_000,5_000,100_000,120_000,10**8),35_000)
        self.assertEqual(capacity.effective_cargo(100_000,10_000,100_000,30_000,10**8),20_000)
        state=shape_state(features=options(physical_capacity=True))
        quote={'routes':[river()]}
        self.assertTrue(logistics.safe_capacity_route(None,state,quote))
        state.extension[winter_weather.POOL]={'ice':{'test-river':{'state':3}}}
        self.assertFalse(logistics.safe_capacity_route(None,state,quote))
        self.assertTrue(logistics.safe_capacity_route(None,state,{'routes':[land()]}))

    def test_route_capacity_is_physical_and_embark_has_no_load_ceiling(self):
        game=SimpleNamespace(catalog=SimpleNamespace(data={}))
        state=shape_state()
        for flow in ('downstream','still','upstream'):
            self.assertEqual(capacity.physical(game,state,{'routes':[river(flow=flow)]})['physical_capacity'],100_000)
        self.assertEqual(capacity.physical(game,state,{'routes':[sea()]})['physical_capacity'],150_000)
        self.assertEqual(capacity.physical(game,state,{'routes':[river(access=1)]})['physical_capacity'],50_000)
        mixed=capacity.physical(game,state,{'routes':[river(),land('mountain'),sea()]})
        self.assertEqual((mixed['mode'],mixed['physical_capacity'],mixed['bottleneck']['mode']),
                         ('mixed',40_000,'mountain'))
        self.assertEqual(_hazard_risk(dict(hazard=dict(loss_percent_max=45,survival_numerator=None))),45)

    def test_one_thousand_directional_routes_use_one_denominated_bottleneck(self):
        game=SimpleNamespace(catalog=SimpleNamespace(data={}))
        random=Random(3030)
        choices = [(land(),5_000),(land('mountain'),4_000),(land('desert'),3_500),
                   (river(),10_000),(river(flow='upstream'),10_000),(river(access=1),5_000),(sea(),15_000)]
        state=shape_state()
        for _ in range(1_000):
            group=random.choices(choices,k=random.randint(1,8))
            scale=random.choice((1,10))
            if scale==1:
                state.extension.pop(grain_units.FIELD,None)
            else:
                state.extension[grain_units.FIELD]=scale
            calculated=capacity.physical(game,state,{'routes':[row for row,_ in group]})
            self.assertEqual(calculated['physical_capacity'],min(n for _,n in group)*scale)

    def test_one_thousand_actual_load_boundaries_and_conserved_pending_loads(self):
        game=SimpleNamespace(catalog=SimpleNamespace(data={}))
        state=shape_state(features=options(physical_capacity=True))
        random=Random(3031)
        for _ in range(1_000):
            quote={'routes':[random.choice((land('desert'),land('mountain'),river(),sea()))]}
            maximum=capacity.physical(game,state,quote)['physical_capacity']
            bag,available,policy,destination=(random.randrange(180_000) for _ in range(4))
            cargo=capacity.effective_cargo(maximum,bag,policy,available,destination)
            expected=max(0,min(maximum-bag,available-bag,policy,destination))
            self.assertEqual(cargo,expected)
            row=dict(cargo={'grain':cargo},journeys=[{'quote':dict(quote,path=['a','b']),
                                                       'supply':{'remaining':bag}}])
            before=deepcopy(row)
            self.assertEqual(capacity.fits(game,state,row,quote),cargo+bag<=maximum)
            self.assertEqual(capacity.refill_room(game,state,row,'a'),max(0,maximum-bag-cargo))
            self.assertEqual(row,before)

    def test_one_thousand_competing_origin_and_captured_city_slot_states(self):
        random=Random(3032)
        for _ in range(1_000):
            concurrency,doubling=(bool(random.getrandbits(1)) for _ in range(2))
            states=shape_state(features=options(concurrency=concurrency,double_dispatch=concurrency and doubling))
            city=states.cities['a']
            city.owner=random.choice(('shu','wei'))
            pool=states.extension['logistics']['convoys']
            for _ in range(random.randrange(5)):
                pool.append(dict(source='a',owner=random.choice(('shu','wei'))))
            started=random.randrange(capacity.dispatch_limit(states)+1)
            for _ in range(started):
                capacity.record_dispatch(states,'a')
            same_owner=sum(row['owner']==city.owner for row in pool)
            expected=('already_dispatched' if started>=capacity.dispatch_limit(states) else
                      'in_transit' if (same_owner if concurrency else len(pool)) >= (2 if concurrency else 1) else None)
            self.assertEqual(capacity.dispatch_blocker(states,city,capacity.activity(states)),expected)

    def test_one_thousand_versioned_and_legacy_dispatch_record_roundtrips(self):
        random=Random(3033)
        for _ in range(1_000):
            flags=random.choice((None,options(concurrency=True),options(concurrency=True,double_dispatch=True),
                                 options(physical_capacity=True)))
            state=shape_state(features=flags)
            state.turn=random.randrange(1,720)
            turn=state.turn
            for _ in range(random.randrange(capacity.dispatch_limit(state)+1)):
                capacity.record_dispatch(state,'a')
            state.turn+=random.randrange(2)
            restored=SimpleNamespace(extension=json.loads(json.dumps(state.extension)),
                                     turn=state.turn,cities=state.cities)
            capacity.validate(restored)
            self.assertEqual(capacity.dispatch_count(restored,'a'),capacity.dispatch_count(state,'a'))
            self.assertEqual(capacity.enabled(restored),flags is not None)
            if flags is not None and capacity.dispatch_count(restored,'a'):
                restored.extension[capacity.POOL]['dispatches']['a']=[turn,capacity.dispatch_limit(restored)+1]
                with self.assertRaises(ValueError):
                    capacity.validate(restored)


class CapacityGameTests(TestCase):
    def game(self, flags=None):
        game=Campaign(controlled.transport_catalog(long=True))
        payload=dict(faction='shu',seed=2026)
        if flags is not None:
            payload.update({capacity.FIELD:303,capacity.OPTIONS:flags})
        game.command('new',payload,0)
        controlled.LogisticsTests().fill(game,SOURCE,6)
        game.command('set_logistics',dict(city=SOURCE,policy=dict(
            enabled=True,target_city=TARGET,reserve_grain=0,reserve_officers=2,max_grain=100_000)),game.revision)
        game.state.cities[SOURCE].grain=150_000
        return game

    def ids(self,game):
        return logistics._eligible(game,game.state,game.state.cities[SOURCE])

    def send(self,game,ident,grain=10_000):
        game.command('dispatch_transport',dict(source=SOURCE,target=TARGET,route_mode='land',
            officers=[ident],cargo=dict(gold=0,grain=grain,reserves=0)),game.revision)
        return logistics._pool(game.state)['convoys'][-1]

    def advance(self,game):
        game._complete_turn(game.state)
        logistics.process_arrivals(game,game.state)
        game.state.phase='city'

    def assert_rejected(self,game,ident,grain=10_000):
        before=game.export_save()
        with self.assertRaises(GameError):
            self.send(game,ident,grain)
        self.assertEqual(before,game.export_save())

    def test_returning_first_escort_allows_an_independent_second_convoy_and_saves(self):
        game=self.game(options(concurrency=True,physical_capacity=True))
        first,second,third,*_=self.ids(game)
        first_row=self.send(game,first)
        self.assertEqual(first_row['journeys'][0][capacity.LOAD_FIELD]['total'],
                         10_000+first_row['journeys'][0]['supply']['loaded'])
        self.assert_rejected(game,second)
        until=first_row['journeys'][0]['arrival_turn']
        while game.state.turn<until:
            self.advance(game)
        first_row,=logistics._pool(game.state)['convoys']
        self.assertTrue(first_row['delivery_done'])
        self.assertEqual(first_row['status'],'returning')
        self.assert_rejected(game,first)
        books=command_books.remaining(game.state,'shu')
        payments=[]
        dispatch=logistics.dispatch
        def call(engine,state,payload,owner,**kwargs):
            stock=state.cities[SOURCE].grain
            row=dispatch(engine,state,payload,owner,**kwargs)
            payments.append(stock-state.cities[SOURCE].grain)
            return row
        with patch.object(logistics,'dispatch',side_effect=call):
            second_row=self.send(game,second)
        self.assertEqual(payments,[10_000+second_row['journeys'][0]['supply']['loaded']])
        self.assertEqual(command_books.remaining(game.state,'shu'),books-1)
        for compact in (False,True):
            data=game.export_save(compact=compact)
            restored=Campaign(game.catalog)
            restored.load_save(data,0)
            self.assertEqual(restored.export_save(compact=compact),data)
            self.assertEqual(len(logistics._pool(restored.state)['convoys']),2)
            self.assertEqual(capacity.dispatch_count(restored.state,SOURCE),1)
        self.advance(game)
        self.assert_rejected(game,third)
        last=first_row['journeys'][-1]['arrival_turn']
        while game.state.turn<last:
            self.advance(game)
        self.assertNotIn(1,[row['id'] for row in logistics._pool(game.state)['convoys']])

    def test_legacy_capacity_and_opt_in_two_per_turn_are_distinct(self):
        old=self.game()
        first,second,*_=self.ids(old)
        self.send(old,first)
        self.advance(old)
        self.assert_rejected(old,second)
        self.assertNotIn(capacity.FIELD,old.state.extension)
        candidate=self.game(options(concurrency=True,double_dispatch=True))
        first,second,third,*_=self.ids(candidate)
        self.send(candidate,first)
        self.assert_rejected(candidate,first)
        self.send(candidate,second)
        self.assert_rejected(candidate,third)
        self.assertEqual(capacity.dispatch_count(candidate.state,SOURCE),2)

    def test_capture_preserves_dispatches_but_frees_new_owners_origin_slot(self):
        game=self.game(options(concurrency=True))
        self.send(game,self.ids(game)[0])
        state=game.state
        source=state.cities[SOURCE]
        source.owner='wei'
        logistics.synchronize(game,state)
        self.assertEqual(capacity.active_count(state,source),0)
        self.assertEqual(capacity.dispatch_blocker(state,source),'already_dispatched')
        self.assertEqual(logistics._pool(state)['convoys'][0]['owner'],'shu')
        state.turn+=1
        self.assertIsNone(capacity.dispatch_blocker(state,source))

    def test_illegal_load_or_reroute_changes_neither_resources_nor_rng(self):
        game=self.game(options(physical_capacity=True))
        ident=self.ids(game)[0]
        self.assert_rejected(game,ident,50_000)
        row=self.send(game,ident,20_000)
        # A synthetic quote models a later lower-capacity link. Direct
        # invocation checks that the same authority leaves the carried goods.
        quote=game._quote([SOURCE,TARGET],[land('mountain')])
        cargo=row['cargo']
        supply=row['journeys'][0]['supply']
        cargo['grain']=43_000
        before=(deepcopy(cargo),deepcopy(supply),game.state.rng.draws,game.state.cities[SOURCE].grain)
        self.assertFalse(logistics._begin_journey(game,game.state,row,SOURCE,TARGET,'land',quote,
                                                  status='returning',reason='route_blocked'))
        self.assertEqual((cargo,{**supply,'waiting':before[1]['waiting']},game.state.rng.draws,
                          game.state.cities[SOURCE].grain),before)
        self.assertEqual(row['reason'],'route_capacity')

    def test_real_chibi_river_quote_and_departure_share_a_land_bottleneck(self):
        game=Campaign(Catalog(Path(__file__).resolve().parents[1]/'game/data/campaigns/208-10.json'))
        game.command('new',dict(faction='wu',seed=2026,transport_capacity_rules_version=303),0)
        source,target=(game.state.cities[key] for key in ('lujiang','danyang'))
        ident=logistics._eligible(game,game.state,source)[0]
        game.command('set_logistics',dict(city=source.id,policy=dict(
            enabled=True,target_city=target.id,reserve_grain=0,max_grain=100_000)),game.revision)
        quote=logistics._safe_path(game,game.state,source.id,target.id,source.owner,'river',
                                  logistics._pool(game.state)['cities'][source.id]['policy'])
        expected=capacity.physical(game,game.state,quote)
        self.assertEqual((expected['mode'],expected['physical_capacity'],expected['bottleneck']['mode']),
                         ('mixed',50_000,'plain'))
        game.command('dispatch_transport',dict(source=source.id,target=target.id,route_mode='river',
            officers=[ident],cargo=dict(gold=0,grain=2_000,reserves=0)),game.revision)
        row,=logistics._pool(game.state)['convoys']
        self.assertEqual(row['journeys'][0][capacity.LOAD_FIELD]['limit'],expected['physical_capacity'])
        self.assertEqual(row['journeys'][0]['quote']['routes'],quote['routes'])

    def test_observation_does_not_change_rng_or_state_or_repeat_receipts(self):
        controls=(self.game(options(concurrency=True,physical_capacity=True)) for _ in range(2))
        observed,plain=controls
        events=[]
        with capacity.observing(lambda event,row:events.append((event,deepcopy(row)))):
            self.send(observed,self.ids(observed)[0])
            for _ in range(14):
                self.advance(observed)
        self.send(plain,self.ids(plain)[0])
        for _ in range(14):
            self.advance(plain)
        self.assertEqual(observed.export_save(),plain.export_save())
        self.assertEqual([event for event,_ in events].count('departure'),1)
        self.assertEqual([event for event,_ in events].count('delivery'),1)
        self.assertEqual([event for event,_ in events].count('terminal'),1)
        terminal=next(row for event,row in events if event=='terminal')
        self.assertTrue(logistics.valid_grain_receipt(terminal['cargo_receipt']))

    def test_regional_purchase_can_complete_its_own_single_compound_order(self):
        game=regional.controlled()
        capacity.initialize(game.state,303,options(concurrency=True,physical_capacity=True))
        quote=regional.offer(game,purpose='procurement')
        self.assertGreater(quote['capacity']['max_cargo'],0)
        before=command_books.remaining(game.state,regional.OWNER)
        regional.buy(game,quote)
        self.assertEqual(regional.item(game)['status'],'dispatched')
        self.assertEqual(command_books.remaining(game.state,regional.OWNER),before-2)
