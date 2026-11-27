"""Actual city transshipment orders on the existing Pearl River road graph."""
from pathlib import Path
from copy import deepcopy
from random import Random
import sys
import unittest

import test_remake_logistics as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))

from remake import command_books, grain_units, logistics, transport_capacity, transshipment, winter_weather
from remake import logistics_rules
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError


class Headless(Campaign):
    def view(self):
        return {}


FEEDERS = ('hepu','jiaozhi')
HUBS = ('yulin','cangwu')
TARGET = 'nanhai'


def world(*, capacity=True, granary=0, weather=False):
    catalog = Catalog(ROOT/'game/data/campaigns/227-02.json')
    game = Headless(catalog, record_journal=False)
    payload = dict(faction='wu', seed=2026, lifespan='none', transshipment_rules_version=304)
    if capacity:
        flags = dict.fromkeys(transport_capacity.FEATURES,False)
        payload.update(transport_capacity_rules_version=303,
                       transport_capacity_options=flags | {'concurrency':True,'physical_capacity':True})
    if granary:
        payload.update(strategic_granary_rules_version=granary)
    if weather:
        payload[winter_weather.FIELD] = winter_weather.CORRECTED
    game.command('new',payload,0)
    setup = fixtures.LogisticsTests()
    for city in (*FEEDERS,*HUBS,TARGET):
        current = game.state.cities[city]
        for _ in range(0 if city==TARGET else max(0,5-len(current.roster.officer_ids))):
            donor=max((place for place in game.state.cities.values()
                       if place.owner=='wu' and place.id not in (*FEEDERS,*HUBS,TARGET)),
                      key=lambda place:len(place.roster.officer_ids))
            ident=min(logistics._eligible(game,game.state,donor),key=lambda i:game.state.officers[i].troops)
            donor.roster.officer_ids.remove(ident)
            current.roster.officer_ids.append(ident)
            setup.sync(game)
        current = game.state.cities[city]
        current.grain = 10_000 if city==TARGET else 160_000
        game.command('set_logistics',dict(city=city,policy=dict(max_grain=100_000,reserve_grain=0,
                     reserve_officers=1,allow_sea=True)),game.revision)
    return game


def create(game, *, purpose='reserve', grain=130_000, hubs=HUBS, modes=('land','river','land'), target=TARGET):
    game.command(transshipment.COMMAND,dict(action='create',sources=list(FEEDERS),hubs=list(hubs),target=target,
        modes=list(modes),purpose=purpose,grain=grain,promise_turns=30),game.revision)


def plan(game, ident=1):
    return game.state.extension[transshipment.POOL]['plans'][str(ident)]


def offer(game,stage,source,ident=1):
    with grain_units.using(game.state):
        return transshipment._quote(game,game.state,plan(game,ident),stage,source)


def dispatch(game,stage,source,grain,*,officer=None,ident=1):
    raw = offer(game,stage,source,ident)
    if officer is None:
        officer = raw['officer']
    game.command(transshipment.COMMAND,dict(action='dispatch',plan=ident,stage=stage,source=source,
             grain=grain,officer=officer),game.revision)
    return plan(game,ident)['batches'][-1]


def advance(game,turns=1):
    for _ in range(turns):
        with grain_units.using(game.state):
            game._complete_turn(game.state)
            game._reconcile_factions(game.state)
        game.state.phase = 'arrivals'
        game.command('arrivals',{},game.revision)


def wait_for(game, condition, turns=16):
    for _ in range(turns):
        if condition():
            return
        advance(game)
    if not condition():
        raise AssertionError(f'Campaign turn {game.state.turn} did not reach the required state')


class TransshipmentTests(unittest.TestCase):
    def test_two_real_land_feeders_merge_at_pure_river_and_split_into_two_land_convoys(self):
        for granary in (0,302,3021):
            with self.subTest(granary=granary):
                self.exercise_chain(granary)

    def exercise_chain(self,granary):
        game = world(capacity=granary!=0, granary=granary)
        create(game)
        blocked = offer(game,1,'yulin')
        self.assertEqual(blocked['blocked'],'waiting_for_stock')
        receipts = []
        for city in FEEDERS:
            quote = offer(game,0,city)
            self.assertIsNone(quote['blocked'])
            self.assertLessEqual(quote['capacity'],50_000)
            books = command_books.remaining(game.state,'wu')
            stock = game.state.cities[city].grain
            row = dispatch(game,0,city,quote['max_cargo'])
            self.assertEqual(command_books.remaining(game.state,'wu'),books-1)
            self.assertEqual(game.state.cities[city].grain,stock-row['grain']-row['rations'])
            self.assertEqual(row['available'],0)
            receipts.append(row['convoy'])
        wait_for(game,lambda: all(b['receipt'] is not None for b in plan(game)['batches']))
        for compact in (False,True):
            save = game.export_save(compact=compact)
            restored = Headless(game.catalog,record_journal=False)
            restored.load_save(save,0)
            self.assertEqual(restored.export_save(compact=compact),save)
        advance(game)
        water = offer(game,1,'yulin')
        self.assertEqual(water['capacity'],100_000)
        self.assertGreater(water['max_cargo'],50_000)
        sail = dispatch(game,1,'yulin',water['max_cargo'])
        self.assertEqual([pair[0] for pair in sail['parents']],receipts)
        self.assertEqual(sum(pair[1] for pair in sail['parents']),sail['grain']+sail['rations'])
        wait_for(game,lambda: plan(game)['batches'][2]['receipt'] is not None)
        self.assertEqual(offer(game,2,'cangwu')['blocked'],'waiting_for_stock')
        advance(game)
        for _ in range(2):
            wait_for(game,lambda: offer(game,2,'cangwu')['blocked'] is None)
            land = offer(game,2,'cangwu')
            self.assertLessEqual(land['capacity'],50_000)
            dispatch(game,2,'cangwu',land['max_cargo'])
        receipt_stock = game.state.cities[TARGET].grain
        wait_for(game, lambda: any(p['id']==1 for p in game.state.extension[transshipment.POOL]['history']))
        closed = next(p for p in game.state.extension[transshipment.POOL]['history'] if p['id']==1)
        self.assertEqual(len(closed['batches']),5)
        self.assertTrue(all(b['receipt'] is not None and b['terminal'] for b in closed['batches']))
        self.assertGreater(transshipment._final_grain(closed),50_000)
        self.assertGreater(game.state.cities[TARGET].grain,receipt_stock)
        self.assertEqual(sum(b['books'] for b in closed['batches']),5)
        self.assertNotEqual(closed['batches'][3]['convoy'],closed['batches'][4]['convoy'])
        self.assertEqual(transshipment.credit(game.state,'cangwu'),0)

    def test_cancel_after_first_arrival_preserves_existing_grain_and_returns_inflight_cargo(self):
        game = world()
        create(game)
        dispatch(game,0,'hepu',25_000)
        advance(game)
        self.assertGreater(transshipment.credit(game.state,'yulin'),0)
        stock = game.state.cities['yulin'].grain
        game.command(transshipment.COMMAND,dict(action='cancel',plan=1),game.revision)
        self.assertEqual(game.state.cities['yulin'].grain,stock)
        self.assertEqual(transshipment.credit(game.state,'yulin'),0)
        self.assertTrue(logistics._pool(game.state)['convoys'])

    def test_local_priority_preempts_warehouse_tags_and_tampered_balance_fails_atomically(self):
        game = world()
        create(game)
        dispatch(game,0,'hepu',30_000)
        advance(game)
        before = game.export_save()
        bad = game.export_save()
        bad['state']['extension']['transshipment']['plans']['1']['batches'][0]['available'] += 1
        bad['checksum'] = digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(GameError):
            game.load_save(bad,game.revision)
        self.assertEqual(game.export_save(),before)
        city = game.state.cities['yulin']
        tagged = transshipment.credit(game.state,city.id)
        city.grain = 1000  # Actual priority debit, isolated from the payroll amounts.
        with grain_units.using(game.state):
            transshipment.synchronize(game,game.state)
        self.assertEqual(city.grain,1000)
        self.assertLessEqual(transshipment.credit(game.state,city.id),1000)
        self.assertGreater(tagged,1000)
        self.assertGreater(plan(game)['batches'][0]['released']['priority'],0)
        game.validate(game.state)

    def test_version_is_opt_in_and_full_compact_saves_keep_303_fields(self):
        game = Headless(Catalog(ROOT/'game/data/campaigns/227-02.json'),record_journal=False)
        game.command('new',dict(faction='wu',seed=2026,transport_capacity_rules_version=303),0)
        old = game.export_save(compact=True)
        self.assertNotIn(transshipment.POOL,game.state.extension)
        self.assertNotIn(transshipment.FIELD,old['state']['extension'])
        game.load_save(old,game.revision)
        self.assertEqual(game.export_save(compact=True),old)

    def test_real_city_unload_funds_no_free_grain_and_opens_a_legal_land_route(self):
        game = world()
        create(game)
        for city in FEEDERS:
            dispatch(game,0,city,offer(game,0,city)['max_cargo'])
        wait_for(game,lambda: all(b['receipt'] is not None for b in plan(game)['batches']))
        advance(game)
        batch = dispatch(game,1,'yulin',offer(game,1,'yulin')['max_cargo'])
        ident = batch['convoy']
        convoy = next(row for row in logistics._pool(game.state)['convoys'] if row['id']==ident)
        # Controlled blocked departure at its actual city, before any movement.
        convoy.update(status='waiting',reason='route_capacity')
        convoy['journeys'][-1]['supply']['waiting'] = True
        bag = convoy['journeys'][0]['supply']['remaining']
        previous = convoy['cargo']['grain'] + bag
        stock = game.state.cities['yulin'].grain
        books = command_books.remaining(game.state,'wu')
        wrong = dict(action='unload',convoy=ident,city='hepu',target='cangwu',mode='land')
        before = game.export_save()
        with self.assertRaises(GameError):
            game.command(transshipment.COMMAND,wrong,game.revision)
        self.assertEqual(game.export_save(),before)
        game.command(transshipment.COMMAND,dict(wrong,city='yulin'),game.revision)
        row = next(row for row in logistics._pool(game.state)['convoys'] if row['id']==ident)
        new = row['journeys'][-1]
        unloaded = game.state.extension[transshipment.POOL]['unloads'][-1]
        self.assertEqual(unloaded['grain'],previous-new[transport_capacity.LOAD_FIELD]['limit'])
        self.assertEqual(game.state.cities['yulin'].grain-stock,unloaded['grain'])
        self.assertEqual(command_books.remaining(game.state,'wu'),books)
        self.assertLessEqual(row['cargo']['grain']+new['supply']['remaining'],unloaded['capacity'])
        self.assertEqual(new['quote']['path'][0],'yulin')
        self.assertGreaterEqual(new['supply']['remaining'],bag)
        self.assertTrue(logistics.valid_grain_receipt(logistics.grain_receipt(row)))
        saved = game.export_save(compact=True)
        game.load_save(saved,game.revision)
        self.assertEqual(game.export_save(compact=True),saved)

    def test_capture_releases_tag_leaving_stock_and_existing_convoy_in_place(self):
        game = world()
        create(game)
        dispatch(game,0,'hepu',20_000)
        advance(game)
        state = game.state
        hub = state.cities['yulin']
        previous = hub.grain
        self.assertGreater(transshipment.credit(state,hub.id),0)
        hub.owner = 'wei'  # Isolate the result of a normal ownership change.
        with grain_units.using(state):
            transshipment.synchronize(game,state)
        self.assertEqual(plan(game)['reason'],'ownership')
        self.assertEqual(transshipment.credit(state,hub.id),0)
        self.assertEqual(hub.grain,previous)
        self.assertEqual(logistics._pool(state)['convoys'][0]['owner'],'wu')

    def test_full_hub_and_shortage_already_covered(self):
        game = world()
        create(game)
        game.state.cities['yulin'].grain = logistics.LIMIT
        self.assertEqual(offer(game,0,'hepu')['blocked'],'grain_or_room')
        game.command(transshipment.COMMAND,dict(action='cancel',plan=1),game.revision)
        with self.assertRaises(GameError):
            create(game,purpose='shortage',grain=1_000)

    def test_frozen_pure_river_stays_waiting_without_debit(self):
        game = world(weather=True)
        create(game)
        for city in FEEDERS:
            dispatch(game,0,city,24_000)
        wait_for(game,lambda: all(b['receipt'] is not None for b in plan(game)['batches']))
        advance(game)
        water = offer(game,1,'yulin')
        reach = water['quote']['routes'][0]['river_segments'][0]['reach_id']
        ice = game.state.extension[winter_weather.POOL]['ice'].setdefault(reach,{})
        stock = game.state.cities['yulin'].grain
        ice['state'] = 3
        self.assertEqual(offer(game,1,'yulin')['blocked'],'route')
        self.assertEqual(game.state.cities['yulin'].grain,stock)

    def test_1000_allocations_and_1000_route_ownership_save_checks(self):
        # Reuse actual two-feeder evidence, then exercise independent copies
        # with varied lots and generation order. A checksum never substitutes
        # for the semantic validation exercised below.
        game = world()
        create(game)
        for city in FEEDERS:
            dispatch(game,0,city,25_000)
        wait_for(game,lambda: all(b['receipt'] is not None for b in plan(game)['batches']))
        advance(game)
        dispatch(game,1,'yulin',offer(game,1,'yulin')['max_cargo'])
        game.validate(game.state)
        original = deepcopy(game.state.extension[transshipment.POOL])
        rng = Random(3041)
        for _ in range(1_000):
            ledger = deepcopy(original)
            item=ledger['plans']['1']
            lot = item['batches'][rng.randrange(2)]
            lot['available'] += rng.randrange(1,1000)
            game.state.extension[transshipment.POOL] = ledger
            with self.assertRaisesRegex(ValueError,'warehouse balance'):
                transshipment.validate(game,game.state)
        for index in range(1_000):
            ledger = deepcopy(original)
            item = ledger['plans']['1']
            if index % 2:
                item['batches'][2]['path'][0] = item['target']
            else:
                item['owner'] = 'wei'
            game.state.extension[transshipment.POOL] = ledger
            with self.assertRaises(ValueError):
                transshipment.validate(game,game.state)
        game.state.extension[transshipment.POOL]=original
        game.validate(game.state)

    def test_1000_physical_loads_split_after_preserving_weighted_route_work(self):
        game = world()
        create(game)
        initial = offer(game,0,'hepu')['quote']
        with grain_units.using(game.state):
            river = game._travel_path(game.state,'yulin','cangwu','wu','river')
        rng = Random(3042)
        for _ in range(1_000):
            quotes = rng.choices((initial,river),k=rng.randrange(1,5))
            legs = [leg for quote in quotes for leg in quote['routes']]
            rules = game.catalog.data['travel_rules']
            original = [part for leg in legs for part in logistics_rules.leg_parts(leg,rules)]
            split = [part for quote in quotes for part in logistics_rules.plan(quote,rules)]
            self.assertEqual(original,split)
            self.assertEqual(sum(ticks for _,ticks in split),sum(leg['days'] for leg in legs)*1000)
            grain = rng.randrange(100_000)
            rations = rng.randrange(100_000)
            cap = rng.choice((35_000,40_000,50_000,100_000,150_000))
            allowed = transport_capacity.effective_cargo(cap,rations,100_000,grain,100_000)
            self.assertEqual(allowed, max(0,min(grain-rations,cap-rations)))
