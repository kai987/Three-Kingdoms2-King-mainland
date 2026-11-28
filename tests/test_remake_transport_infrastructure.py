"""Exercise the authored wharves through real campaign transactions."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))

from remake import (civil_staff, command_books, domestic, faction_economy, grain_units,
                    granary_demand, logistics, route_network, transport_capacity,
                    transport_infrastructure as wharf, winter_weather)
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError

ROUTE = 'fuling:badong:river'
SOURCE = 'fuling'
TARGET = 'badong'
D2 = dict.fromkeys(transport_capacity.FEATURES, False) | {'concurrency': True}


class Headless(Campaign):
    def view(self):
        return {}


def world(*, enabled=True, scenario='227-02', faction='shu', **settings):
    game = Headless(Catalog(ROOT/'game/data/campaigns'/f'{scenario}.json'), record_journal=False)
    game.command('new', dict(faction=faction, seed=2026, lifespan='none',
                             transport_infrastructure_rules_version=wharf.VERSION if enabled else 0,
                             **settings), 0)
    return game


def order(game, batches, *, route=ROUTE, origin=SOURCE, deadline=90):
    state = game.state
    with grain_units.using(state):
        offer=wharf.quote(game,state,state.player,route,origin,batches,deadline)
    if offer['blocked']:
        raise AssertionError(offer)
    ident=state.extension[wharf.POOL]['next_id']
    return dict(action='dispatch',id=ident,route=route,source=origin,batches=batches,deadline=deadline,
                escort=offer['escort']), offer


def current(game, ident=1):
    return game.state.extension[wharf.POOL]['jobs'][str(ident)]


def advance(game, turns=1):
    # Controlled runner only bypasses discretionary AI. It still calls the
    # published daily movement, food, changes of calendar, and settlement.
    for _ in range(turns):
        with grain_units.using(game.state):
            game._complete_turn(game.state)
            game._reconcile_factions(game.state)
            wharf.synchronize(game,game.state)
        if game.state.phase=='arrivals':
            game.command('arrivals',{},game.revision)
        game.validate(game.state)


def restore(game, compact):
    restored = Headless(game.catalog, record_journal=False)
    # Browser serialization is intentionally used on both envelope formats.
    data=json.loads(json.dumps(game.export_save(compact=compact),allow_nan=False))
    restored.load_save(data,0)
    assert restored.to_dict()==game.to_dict()
    return restored


def automatic_opening():
    game=world(faction='observer')
    state=game.state
    origin,target=state.cities[SOURCE],state.cities[TARGET]
    # Deliberately reserve the opening surplus at origin to create a known
    # future bill. Use only the actual faction's existing grain and roster.
    origin.grain+=target.grain-900
    target.grain=900
    with grain_units.using(state):
        logistics.prepare_ai(game,state,'shu')
        logistics._pool(state)['cities'][SOURCE]['policy']['enabled']=True
    state.phase='ai'
    return game


class InfrastructureTests(unittest.TestCase):
    def test_official_geometry_and_old_directions(self):
        with (ROOT/'game/config/river-network.json').open() as stream:
            river=json.load(stream)
        for node,(city,mark,xy,*_) in wharf.SITES.items():
            self.assertEqual(river['ports'][city]['node'],mark,node)
            self.assertEqual(river['nodes'][mark]['position'],list(xy),node)
        g=world()
        for edge,raw in g.catalog.infrastructure_routes.items():
            for origin, target in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                span=wharf.sections(g,edge,origin,g.state.month)
                old=g._travel_path(g.state,origin,target,g.state.cities[origin].owner,'river')
                self.assertEqual(sum(x.work for x in span), old['days']*wharf.winter_travel.QUANTA)
                self.assertEqual([x.mode for x in span],['land','river','land'])
                self.assertEqual(sum(p.mode=='embark' for x in span for p in x.parts),1)
        self.assertFalse(set(g.catalog.map_cities) & wharf.SITES.keys())

    def test_disabled_opening_and_unknown_geometry(self):
        g=world(enabled=False)
        snapshot=g.to_dict()
        self.assertNotIn(wharf.FIELD, snapshot['extension'])
        self.assertNotIn(wharf.POOL, restore(g,True).state.extension)
        with self.assertRaises(GameError):
            g.command(wharf.COMMAND,{},g.revision)
        self.assertEqual(g.to_dict(),snapshot)
        enabled=world()
        q=wharf.quote(enabled,enabled.state,'shu','jiangyang:bajun:river','jiangyang',[100],40)
        self.assertEqual(q,{'blocked':'no_facility'})

    def test_real_custody_per_batch_ledger_and_returns(self):
        g=world()
        before=g.to_dict()
        payload,q=order(g,[1000,1500])
        self.assertEqual(g.to_dict(),before)
        events=[]
        with wharf.observing(lambda kind,row: events.append(dict(kind=kind,**row))):
            g.command(wharf.COMMAND,payload,g.revision)
            s=g.state
            row=current(g)
            self.assertEqual(row['balances']['cargo'],2500)
            self.assertEqual(s.cities[SOURCE].grain,before['cities'][SOURCE]['grain']-2500-q['rations'])
            self.assertIn(payload['escort'],g._march_ids(s))
            self.assertEqual(transport_capacity.active_count(s,s.cities[SOURCE]),1)
            self.assertEqual(transport_capacity.dispatch_count(s,SOURCE),1)
            self.assertEqual(len({s['end'] for s in q['sections']}),3)
            for attempts in range(6):
                if not list(wharf.jobs(g.state)):
                    break
                uninterrupted=g
                g=restore(g,attempts%2==0)
                advance(uninterrupted)
                advance(g)
                self.assertEqual(g.to_dict(),uninterrupted.to_dict())
        terminal=g.state.extension[wharf.POOL]['history'][-1]
        self.assertEqual(terminal['terminal']['city'],SOURCE)
        self.assertEqual(terminal['paid'],[0,1,2])
        self.assertFalse(payload['escort'] in g._march_ids(g.state))
        self.assertGreater(terminal['balances']['delivery'],0)
        self.assertEqual(terminal['balances']['input'],sum(terminal['balances'][k] for k in wharf.BALANCES[1:]))
        self.assertGreater(max(len(row['parents']) for row in terminal['events'] if row['kind']=='unload'),1)
        self.assertFalse(terminal['balances']['bank0'] or terminal['balances']['bank1'])
        self.assertLess(terminal['arrival'],q['original_deadline'])

    def test_partial_loading_persists_and_cancellation_retraces(self):
        g=world()
        payload,_=order(g,[6500,6500])
        g.command(wharf.COMMAND,payload,g.revision)
        # The initial approach and partial handling take more than one旬.
        advance(g)
        row=current(g)
        self.assertEqual(row['at'],'wharf-fuling')
        self.assertEqual(row['phase'],'loading')
        self.assertGreater(row['balances']['bank0'],0)
        self.assertGreater(row['balances']['cargo'],0)
        restored=restore(restore(g,False),True)
        restored.command(wharf.COMMAND,{'action':'cancel','id':1},restored.revision)
        advance(restored,2)
        terminal=restored.state.extension[wharf.POOL]['history'][-1]
        self.assertEqual(terminal['terminal']['city'],SOURCE)
        self.assertEqual(terminal['balances']['delivery'],0)
        self.assertGreater(terminal['balances']['returned'],0)

    def test_command_retry_books_and_march_exclusion(self):
        g=world(transport_capacity_rules_version=303,transport_capacity_options=D2)
        payload,_=order(g,[2100])
        revision=g.revision
        origin=g.state.cities[SOURCE]
        g.command(wharf.COMMAND,payload,revision)
        state=g.to_dict()
        with self.assertRaises(GameError):
            g.command(wharf.COMMAND,payload,revision)
        with self.assertRaises(GameError):
            g.command(wharf.COMMAND,payload,g.revision)
        self.assertEqual(g.to_dict(),state)
        self.assertNotIn(payload['escort'],logistics._eligible(g,g.state,g.state.cities[SOURCE]))
        self.assertEqual(transport_capacity.dispatch_blocker(g.state,origin),'already_dispatched')
        remaining=command_books.remaining(g.state,'shu')
        self.assertEqual(remaining,state['extension']['command_books']['factions']['shu']['total']-1)

    def test_closed_route_holds_real_person_and_consumes_provisions(self):
        g=world()
        payload,_=order(g,[1100])
        g.command(wharf.COMMAND,payload,g.revision)
        with patch.object(route_network,'available',return_value=False):
            advance(g)
        row=current(g)
        self.assertEqual(row['offset'],0)
        self.assertEqual(row['at'],SOURCE)
        self.assertEqual(row['blocked'],'road_closed')
        self.assertGreater(row['balances']['meals'],0)
        self.assertIn(payload['escort'],g._march_ids(g.state))
        g=restore(g,True)
        advance(g,4)
        self.assertEqual(g.state.extension[wharf.POOL]['history'][-1]['terminal']['city'],SOURCE)

    def test_frozen_bank_rejects_without_any_debit(self):
        g=world(faction='wei',weather_rules_version=23)
        s=g.state
        raw=g.catalog.infrastructure_routes['wei:dongjun:river']
        reach=raw['river_segments'][0]['reach_id']
        ice=s.extension[winter_weather.POOL]['ice'][reach]
        ice.update(index=10_000,state=3)
        saved=deepcopy(g.to_dict())
        with grain_units.using(s):
            q=wharf.quote(g,s,'wei',raw['id'],'wei',[500],80)
        self.assertEqual(q['blocked'],'frozen')
        self.assertEqual(g.to_dict(),saved)

    def test_loading_rejects_tampered_custody_and_cursor(self):
        g=world()
        payload,_=order(g,[1500])
        g.command(wharf.COMMAND,payload,g.revision)
        for key,value in (('clock',10),('next_id',1)):
            with self.subTest(key=key):
                data=g.export_save()
                data['state']['extension'][wharf.POOL][key]=value
                data['checksum']=digest({k:v for k,v in data.items() if k!='checksum'})
                with self.assertRaises(GameError):
                    g.load_save(data,g.revision)

    def test_ai_uses_first_nonzero_grain_deadline(self):
        game=automatic_opening()
        state=game.state
        events=[]
        with grain_units.using(state), wharf.observing(lambda kind,row: events.append((kind,row))):
            plan=faction_economy.plan(game,state,'shu',granary=True)
            demand=granary_demand.for_city(game,state,plan,TARGET)
            self.assertEqual(demand.remaining[:2],[(1,0),(2,810)])
            self.assertTrue(wharf.consider_ai(game,state,'shu'))
            self.assertEqual(current(game)['deadline'],20)
            self.assertTrue(events[0][1]['selected'])
            self.assertEqual(events[0][1]['direct']['eta'],20)
            advance(game,4)
        paid=[row for kind,row in events if kind=='delivery']
        self.assertEqual([(row['tick'],row['grain'],row['timely']) for row in paid],[(17,786,True)])
        self.assertEqual(game.state.extension[wharf.POOL]['history'][0]['terminal']['city'],SOURCE)

    def test_parallel_chains_share_bank_reservations_and_real_escorts(self):
        game=world(transport_capacity_rules_version=303,transport_capacity_options=D2)
        outbound,_=order(game,[12000])
        game.command(wharf.COMMAND,outbound,game.revision)
        advance(game)
        snapshot=game.to_dict()
        with grain_units.using(game.state):
            refused=wharf.quote(game,game.state,'shu',ROUTE,TARGET,[4001],90)
        self.assertEqual(refused,{'blocked':'storage'})
        self.assertEqual(snapshot,game.to_dict())
        inbound,forecast=order(game,[4000],origin=TARGET)
        self.assertGreater(forecast['queue_days'],0)
        game.command(wharf.COMMAND,inbound,game.revision)
        self.assertNotEqual(outbound['escort'],inbound['escort'])
        self.assertEqual(transport_capacity.dispatch_count(game.state,TARGET),1)
        for compact in (False,True):
            game=restore(game,compact)
            advance(game,3)
        self.assertEqual(len(game.state.extension[wharf.POOL]['history']),2)

    def test_captured_partial_stock_is_not_restored_by_cancel_or_load(self):
        game=world()
        payload,_=order(game,[6500,6500])
        game.command(wharf.COMMAND,payload,game.revision)
        advance(game)
        deposited=current(game)['balances']['bank0']
        self.assertGreater(deposited,0)
        state=game.state
        source=state.cities[SOURCE]
        target=state.cities[TARGET]
        # Reproduce the post-conquest owner and administrative roster, with
        # the actual escort still physically held at the captured wharf.
        source.owner='wei'
        target.roster.officer_ids.extend(source.roster.officer_ids)
        source.roster.officer_ids.clear()
        with grain_units.using(state):
            logistics.synchronize(game,state)
            wharf.synchronize(game,state)
            domestic.synchronize(game,state)
            civil_staff.synchronize(game,state)
        advance(game)
        for compact in (False,True):
            game=restore(game,compact)
            row=current(game)
            self.assertEqual(row['balances']['captured'],deposited)
            self.assertEqual(row['phase'],'waiting_return')
            self.assertEqual(row['blocked'],'permission')
            self.assertIn(payload['escort'],game._march_ids(game.state))
            self.assertEqual(game.state.extension[wharf.POOL]['nodes']['wharf-fuling']['seized'],deposited)
            advance(game)

    def test_day_idempotent_and_berth_single_job(self):
        g=world()
        payload,_=order(g,[3000])
        g.command(wharf.COMMAND,payload,g.revision)
        with grain_units.using(g.state):
            routes=wharf.prepare_day(g,g.state)
            for tick in range(1,5):
                wharf.advance_day(g,g.state,tick,routes)
            stock=current(g)['balances']['bank0']
            snapshot=deepcopy(g.to_dict())
            wharf.advance_day(g,g.state,4,routes)
        self.assertGreater(stock,0)
        self.assertEqual(g.to_dict(),snapshot)


if __name__=='__main__':
    unittest.main()
