"""V3.0.2 stock, dated receipts, transaction safety and switch compatibility."""
from copy import deepcopy
from random import Random
from unittest import TestCase
from unittest.mock import patch

from remake import (command_books, faction_economy, facilities, granary_planning,
                    grain_market, grain_units, logistics, strategic_granary as granary,
                    transport_emergency)
from remake.campaign import Campaign
from remake.errors import GameError
from test_remake_regional_market import OWNER, SOURCE, TARGET, advance, controlled


def start(**options):
    with granary.experiment(**options):
        return controlled()


def preview(game, quantity=2400):
    with grain_units.using(game.state):
        return granary_planning.preview(game,game.state,OWNER,TARGET,quantity,SOURCE)


def command(game, action, **payload):
    return game.command(granary.COMMAND,dict(action=action,**payload),game.revision)


def book(game, quantity=2400):
    q = preview(game,quantity)['quotes'][0]
    command(game,'reserve',source=SOURCE,target=TARGET,quantity=quantity,token=q['token'])
    return q


class StrategicGranaryTests(TestCase):
    def test_forecast_is_read_only_and_path_batch_is_reused(self):
        g = start()
        before = g.export_save()
        self.assertEqual(preview(g),preview(g))
        self.assertEqual(g.export_save(),before)
        s = g.state
        with grain_units.using(s):
            plan = faction_economy.plan(g,s,OWNER,granary=True)
            planner = granary_planning.Network(g,s,OWNER,plan)
            one = planner.collect([TARGET],[SOURCE])
            other = planner.collect([TARGET],[SOURCE])
        self.assertEqual(one,other)
        self.assertGreaterEqual(planner.stats['route_cache_hits'],2)
        self.assertEqual(planner.stats['route_batches'],1)
        self.assertEqual(len(plan.cities[TARGET].timeline),9)
        self.assertEqual(g.export_save(),before)
        s.cities[SOURCE].grain = 0
        self.assertIn('source_safety',preview(g)['reasons'])

    def test_holding_releasing_and_selling_keep_real_resource_total(self):
        g = start()
        s = g.state
        before = (s.cities[SOURCE].grain,s.cities[SOURCE].gold, grain_market.row(s,SOURCE)['stock'])
        command(g,'hold',city=SOURCE,amount=600)
        self.assertEqual(granary.reserve_grain(g.state,g.state.cities[SOURCE]),600)
        command(g,'set_target',city=SOURCE,amount=650)
        command(g,'release',city=SOURCE,amount=200)
        s = g.state
        c = s.cities[SOURCE]
        self.assertEqual(granary.reserve_row(s,c)['grain'],400)
        self.assertEqual(granary.reserve_row(s,c)['manual_target'],650)
        self.assertEqual((c.grain,c.gold,grain_market.row(s,SOURCE)['stock']),before)
        granary.spending(s,c,c.grain-50,'civilian_and_garrison')
        c.grain=50
        self.assertEqual(granary.reserve_row(s,c)['grain'],50)
        with grain_units.using(s):
            self.assertEqual(facilities._trade_quote(g,s,c,1,'sell')['max_batches'],0)
        g.validate(s)

    def test_booking_cancellation_and_resaving_do_not_debit_or_mint(self):
        g = start()
        target, source = [g.state.cities[k].grain for k in (TARGET,SOURCE)]
        books = command_books.remaining(g.state,OWNER)
        q = book(g)
        s = g.state
        self.assertEqual(granary.committed(s,SOURCE),q['load']+q['rations'])
        self.assertEqual(granary.available(s,s.cities[SOURCE]),source-q['load']-q['rations'])
        self.assertEqual((s.cities[TARGET].grain,s.cities[SOURCE].grain),(target,source))
        self.assertEqual(command_books.remaining(s,OWNER),books)
        with self.assertRaises(GameError):
            command(g,'reserve',source=SOURCE,target=TARGET,quantity=2400,token=q['token'])
        for compact in (True,False,True):
            other = Campaign(g.catalog)
            other.load_save(g.export_save(compact=compact),0)
            self.assertEqual(other.to_dict(),g.to_dict())
            self.assertEqual(granary.committed(other.state,SOURCE),q['load']+q['rations'])
        command(g,'cancel',order=1)
        self.assertEqual(granary.committed(g.state,SOURCE),0)
        self.assertEqual(g.state.cities[SOURCE].grain,source)
        self.assertEqual(g.state.extension[granary.POOL]['history'][0]['status'],'cancelled')

    def test_one_real_departure_and_one_real_delivery_with_save(self):
        g = start()
        q = book(g)
        source = g.state.cities[SOURCE]
        before = (source.grain,source.gold,g.state.cities[TARGET].grain,command_books.remaining(g.state,OWNER))
        events = []
        with granary.observing(lambda kind,row:events.append((kind,row))):
            command(g,'dispatch',order=1)
            s = g.state
            self.assertEqual(s.cities[SOURCE].grain,before[0]-q['load']-q['rations'])
            self.assertEqual(s.cities[SOURCE].gold,before[1])
            self.assertEqual(s.cities[TARGET].grain,before[2])
            self.assertEqual(command_books.remaining(s,OWNER),before[3]-1)
            self.assertEqual(s.extension[granary.POOL]['orders']['1']['status'],'in_transit')
            self.assertEqual(granary.committed(s,SOURCE),0)
            with self.assertRaises(GameError):
                command(g,'dispatch',order=1)
            other = Campaign(g.catalog)
            other.load_save(g.export_save(compact=True),0)
            self.assertEqual(g.to_dict(),other.to_dict())
            for _ in range(4):
                advance(other)
                if not granary.pool(other.state)['orders']:
                    break
            history = granary.pool(other.state)['history']
            self.assertEqual(len(history),1)
            self.assertEqual(history[0]['status'],'returned')
            self.assertGreater(history[0]['delivered_grain'],0)
        self.assertEqual([name for name,_ in events].count('order_dispatched'),1)
        self.assertEqual([name for name,_ in events].count('order_delivered'),1)
        receipt = next(row for name,row in events if name=='escort_receipt')
        self.assertTrue(logistics.valid_grain_receipt({k:receipt[k] for k in logistics.RECEIPT_FIELDS}))
        self.assertEqual(receipt['cargo_delivered'],history[0]['delivered_grain'])

    def test_ownership_and_safety_preemption_unlock_orders(self):
        for city in (SOURCE,TARGET):
            g = start()
            book(g)
            s = g.state
            total = sum(c.grain for c in s.cities.values())
            s.cities[city].owner = 'wei'
            granary.synchronize(s)
            closed = granary.pool(s)['history'][-1]
            self.assertEqual((closed['status'],closed['reason']),('cancelled','ownership'))
            self.assertEqual(sum(c.grain for c in s.cities.values()),total)
        g = start()
        book(g)
        s = g.state
        s.cities[SOURCE].grain = 0
        granary.synchronize(s)
        self.assertEqual(granary.pool(s)['history'][-1]['reason'],'source_safety')
        g.validate(s)

    def test_forecast_counts_actual_arrival_once_after_installment(self):
        g = start()
        q = book(g)
        with grain_units.using(g.state):
            plan = faction_economy.plan(g,g.state,OWNER,granary=True)
        self.assertEqual(sum(plan.cities[TARGET].receipts.values()),0)
        command(g,'dispatch',order=1)
        with grain_units.using(g.state):
            plan = faction_economy.plan(g,g.state,OWNER,granary=True)
        self.assertEqual(sum(plan.cities[TARGET].receipts.values()),q['net'])
        gaps,balances,_ = faction_economy.balance(0,[(0,5,5),(0,5,0)])
        self.assertEqual((gaps,balances),([(1,5),(2,0)],[5,0]))

    def test_default_save_and_disabled_switch_match(self):
        g = controlled()
        other = Campaign(g.catalog)
        with granary.experiment(proactive=True,winter=True):
            other.load_save(g.export_save(compact=True),0)
        self.assertNotIn(granary.POOL,other.state.extension)
        self.assertEqual(g.to_dict(),other.to_dict())
        a,b = Campaign(g.catalog),Campaign(g.catalog)
        with granary.experiment(proactive=True,winter=True):
            a.command('new',dict(faction=OWNER,seed=2026,**{granary.FIELD:0}),0)
        b.command('new',dict(faction=OWNER,seed=2026),0)
        self.assertEqual(a.to_dict(),b.to_dict())
        with self.assertRaises(GameError):
            b.command('new',dict(faction=OWNER,seed=2026,**{granary.FIELD:True}),b.revision)

    def test_boundary_quotes_require_physical_food_officer_route_and_books(self):
        g = start()
        s = g.state
        roll = Random(302)
        with patch.object(logistics,'_supply_routes',return_value={}):
            self.assertIn('no_legal_route',preview(g)['reasons'])
        with patch.object(command_books,'can_spend',return_value=False):
            self.assertEqual(preview(g)['reasons'],{'no_command_books':1})
        s.cities[SOURCE].gold = 0
        self.assertTrue(preview(g)['quotes'])
        with patch.object(logistics, 'LIMIT', s.cities[TARGET].grain):
            self.assertFalse(preview(g)['quotes'])
        for stock in [0,*[roll.randrange(100) for _ in range(10)]]:
            s.cities[SOURCE].grain = stock
            q = preview(g)['quotes']
            self.assertTrue(all(item['load']+item['rations']<=stock for item in q))

    def test_local_return_refill_debits_only_legal_existing_stock(self):
        g = start()
        book(g)
        command(g,'dispatch',order=1)
        s = g.state
        row = s.extension['logistics']['convoys'][0]
        city = s.cities[SOURCE]
        old = (city.grain, transport_emergency.book(row)['remaining'])
        paid = transport_emergency._take_local(g,s,row,city,30)
        self.assertEqual(paid,30)
        self.assertEqual((city.grain,transport_emergency.book(row)['remaining']),(old[0]-30,old[1]+30))
        with patch.object(transport_emergency,'stock',return_value=0):
            self.assertEqual(transport_emergency._take_local(g,s,row,city,100),0)

    def test_winter_uses_regional_normals_without_consuming_draws(self):
        from pathlib import Path
        from remake.campaign import Catalog
        path = Path(__file__).resolve().parents[1]/'game/data/campaigns/208-10.json'
        catalog = Catalog(path)
        g = Campaign(catalog)
        g.command('new',dict(faction='wei',seed=2026,weather_rules_version=221,
                             strategic_granary_rules_version=302,strategic_granary_options={'winter':True}),0)
        self.assertFalse(granary.enabled(g.state,'proactive'))
        before = g.export_save()
        cities = g.view()['catalog']['strategic_granary']['cities']
        self.assertTrue(any(row['winter']>0 for row in cities.values()))
        self.assertGreater(len({row['winter'] for row in cities.values()}),2)
        self.assertEqual(g.export_save(),before)

    def _dispatch_relay(self):
        from remake import granary_relay
        final = 'xiangyang'
        g = start(relay=True,proactive=True)
        g.command('set_logistics',dict(city=TARGET,policy={'reserve_officers':0,'max_officers':1,
            'reserve_grain':0,'max_grain':25_000}),g.revision)
        s = g.state
        s.cities[final].grain = 0
        quote = preview(g,12000)['quotes'][0]
        first = granary.reserve_order(s,OWNER,quote,'relay')
        relay = dict(id=first['id'],owner=OWNER,source=SOURCE,hub=TARGET,target=final,
                     deadline=s.turn+8,received=0,received_turn=None)
        granary_relay.entries(s)[str(first['id'])]=relay
        with grain_units.using(s):
            granary.launch(g,s,first,quote)
        return g,relay

    def test_relay_requires_first_leg_receipt_and_spends_it_once(self):
        from remake import granary_relay
        g,relay=self._dispatch_relay()
        s=g.state
        final=relay['target']
        with grain_units.using(s):
            plan = faction_economy.plan(g,s,OWNER,granary=True)
            self.assertEqual(granary_relay.forward(g,s,OWNER,plan),[])
        self.assertEqual(s.cities[final].grain,0)
        advance(g)
        self.assertGreater(relay['received'],0)
        self.assertNotIn(final, [row['target'] for row in s.extension['logistics']['convoys']])
        saved = g.export_save(compact=True)
        other=Campaign(g.catalog);other.load_save(saved,0)
        self.assertEqual(other.to_dict(),g.to_dict())
        s = other.state
        with grain_units.using(s):
            plan = faction_economy.plan(other,s,OWNER,granary=True)
            before = s.cities[TARGET].grain,s.cities[final].grain
            receipts = granary_relay.forward(other,s,OWNER,plan)
            self.assertEqual(len(receipts),1)
            second = receipts[0]
            self.assertLessEqual(second['load']+second['rations'],relay['received'])
            self.assertEqual(before[0]-s.cities[TARGET].grain,second['load']+second['rations'])
            self.assertEqual(before[1],s.cities[final].grain)
            self.assertFalse(granary_relay.forward(other,s,OWNER,plan))
        advance(other)
        self.assertGreater(s.cities[final].grain,0)

    def test_relay_closes_when_first_delivery_has_no_grain(self):
        from remake import granary_relay, march_supply

        def reserve_all_for_return(game,state,convoy,target):
            bag=convoy['journeys'][-1]['supply']
            amount=convoy['cargo']['grain']
            tick=bag['clock_tick']
            logistics._cargo_change(convoy,'rations',dict(convoy['cargo'],grain=0),tick,
                                    dict(journey=len(convoy['journeys'])-1,tick=tick))
            march_supply.receive(bag,amount,'cargo',convoy['id'],state.turn)

        g,relay=self._dispatch_relay()
        events=[]
        with (patch.object(logistics,'_reserve_before_unload',side_effect=reserve_all_for_return),
              granary.observing(lambda event,row:events.append((event,row)))):
            advance(g)
        self.assertFalse(granary_relay.entries(g.state))
        self.assertEqual(g.state.cities[relay['target']].grain,0)
        self.assertEqual(next(row for event,row in events if event=='order_delivered')['delivered_grain'],0)
        self.assertEqual(next(row for event,row in events if event=='relay_cancelled')['reason'],'empty_receipt')
        self.assertFalse(any(event=='relay_second_leg' for event,_ in events))
        resumed=Campaign(g.catalog)
        resumed.load_save(g.export_save(compact=True),0)
        self.assertEqual(resumed.to_dict(),g.to_dict())
