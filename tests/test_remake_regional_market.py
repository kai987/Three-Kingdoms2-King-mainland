"""Regional pricing, physical receipts, and stale-order boundaries."""
from collections import Counter
from copy import deepcopy
from random import Random
from unittest import TestCase
from unittest.mock import patch

from remake import battle_grid, battle_services, command_books, faction_economy, facilities
from remake import grain_market, logistics, market_pricing as pricing, treasures
from remake import regional_market as regional
from remake.campaign import Campaign
from remake.errors import GameError
from remake.regional_procurement import Planner, landed_cents, quota_left
from test_remake_convoy_rescue import rescue_catalog
import test_remake_battle_objectives as objectives

SOURCE, TARGET, OWNER = 'jiangxia', 'nanjun', 'shu'


def fill_market(state,key,stock,supply=10_000):
    row=grain_market._restock(max(0,stock-supply),supply,pricing.month_key(state))
    state.extension[grain_market.FIELD][key]=row
    if stock<supply:
        grain_market.transfer(state,key,'buy',supply-stock)
    return row


def controlled(stage=2,*,source_stock=25_000,target_stock=3_000):
    catalog=rescue_catalog()
    seller=next(row for row in catalog.data['initial_officers'] if row['person_id']=='san14-candidate-0440')
    seller['city']=TARGET
    game=Campaign(catalog)
    payload=dict(faction=OWNER,seed=2026)
    if stage>=2:
        payload[pricing.FIELD]=301
        if stage==3:
            payload[pricing.AUTOMATION]=True
    with pricing.experiment(stage):
        game.command('new',payload,0)
    game.command('set_logistics',dict(city=SOURCE,policy=dict(reserve_officers=0,max_officers=1,
        reserve_grain=0,max_grain=20_000)),game.revision)
    state=game.state
    state.cities[SOURCE].gold=200
    state.cities[SOURCE].grain=50_000
    state.cities[TARGET].gold=200
    state.cities[TARGET].grain=50_000
    fill_market(state,SOURCE,source_stock)
    fill_market(state,TARGET,target_stock)
    if stage:
        pricing.pool(state)['turn']=0
        pricing.refresh(state)
    return game


def offer(game,quantity=3000,purpose='trade'):
    found=regional.preview(game,game.state,OWNER,TARGET,quantity,purpose,SOURCE)
    return found['quotes'][0]


def buy(game,quote):
    payload=dict(action='buy',source=quote['source'],target=quote['target'],qty=quote['requested'],
                 purpose=quote['purpose'],token=quote['token'])
    return game.command(regional.COMMAND,payload,game.revision)


def advance(game):
    game._complete_turn(game.state)
    logistics.process_arrivals(game,game.state)
    game.state.phase='city'
    treasures.synchronize(game,game.state)
    game.validate(game.state)


def item(game):
    return pricing.pool(game.state)['orders']['1']


class RegionalMarketTests(TestCase):
    def test_price_vectors_and_properties(self):
        values=(0,2000,2499,2500,4999,5000,9999,10000,15000,19999,20000,24999,25000,27000)
        expected=(4,4,4,3,3,1,1,0,0,0,-1,-1,-2,-2)
        self.assertEqual([pricing.ADJUSTMENTS[pricing.inventory_band(n,10_000)] for n in values],list(expected))
        rng=Random(301)
        for _ in range(1000):
            stock,supply,base_buy,base_sell,season=(rng.randrange(n) for n in (100_000,50_000,121,121,6))
            adjustment=pricing.ADJUSTMENTS[pricing.inventory_band(stock,supply)]
            buy_price,sell_price=pricing.prices(base_buy,base_sell,season-3,adjustment)
            self.assertTrue(1<=sell_price<buy_price<=100)
            self.assertLessEqual(pricing.inventory_band(stock,supply),pricing.inventory_band(stock+1,supply))
        self.assertEqual(landed_cents(80,500,10,9000),944)
        self.assertIsNone(landed_cents(80,500,10,0))

    def test_normal_emergency_regional_orders_share_live_stock_with_stable_price(self):
        game=controlled(source_stock=1000)
        state=game.state
        quote=pricing.snapshot(game,state,SOURCE)
        actor=facilities.view(game,state)['cities'][SOURCE]['eligible_actors'][0]
        command_books_before=command_books.remaining(state,OWNER)
        with pricing.observing(lambda *_: None):
            game.command('trade_grain',dict(city=SOURCE,actor=actor,direction='buy',batches=1,
                                           price_token=quote['token']),game.revision)
        state=game.state
        self.assertEqual(command_books.remaining(state,OWNER),command_books_before-1)
        self.assertEqual(pricing.snapshot(game,state,SOURCE),quote)
        self.assertEqual(facilities.emergency_quote(game,state,state.cities[SOURCE],500)['grain'],0)
        result=regional.preview(game,state,OWNER,TARGET,1000,'procurement',SOURCE)
        self.assertEqual(result['reasons'],{'source_stock':1})
        safe=game.export_save()
        with self.assertRaises(GameError):
            game.command('trade_grain',dict(city=SOURCE,actor=actor,direction='buy',batches=1,
                                           price_token='outdated'),game.revision)
        self.assertEqual(game.export_save(),safe)
        advance(game)
        self.assertNotEqual(pricing.snapshot(game,game.state,SOURCE)['token'],quote['token'])
        self.assertEqual(grain_market.row(game.state,SOURCE)['stock'],0)

    def test_failed_dispatch_is_exactly_one_committed_market_purchase(self):
        game=controlled()
        selected=offer(game,purpose='procurement')
        s=game.state
        stock=grain_market.row(s,SOURCE)['stock']
        gold,grain=s.cities[SOURCE].gold,s.cities[SOURCE].grain
        books=command_books.remaining(s,OWNER)
        with patch.object(logistics,'dispatch',side_effect=GameError('forced resource conflict')):
            buy(game,selected)
        s=game.state
        self.assertEqual((item(game)['status'],item(game)['convoy']),('failed',None))
        self.assertEqual((s.cities[SOURCE].gold,s.cities[SOURCE].grain),(gold-selected['gold'],grain+selected['cargo']))
        self.assertEqual(grain_market.row(s,SOURCE)['stock'],stock-selected['cargo'])
        self.assertEqual(command_books.remaining(s,OWNER),books-1)
        safe=game.export_save()
        with self.assertRaises(GameError):
            buy(game,selected)
        self.assertEqual(game.export_save(),safe)

    def test_order_arrival_sale_and_save_custody(self):
        game=controlled()
        quote=offer(game)
        before_delivery=grain_market.row(game.state,TARGET)['stock']
        before_source=game.state.cities[SOURCE].grain
        draw=game.state.rng.draws
        captures=[]
        with pricing.observing(lambda key,row:captures.append((key,row))):
            buy(game,quote)
            self.assertEqual(game.state.cities[SOURCE].grain,before_source-quote['escort_rations'])
            self.assertEqual(game.state.rng.draws,draw)
            for compact in (False, True):
                restored=Campaign(game.catalog)
                restored.load_save(game.export_save(compact=compact),0)
                self.assertEqual(restored.to_dict(),game.to_dict())
            advance(game)
            self.assertEqual(item(game)['status'],'awaiting_sale')
            self.assertEqual(grain_market.row(game.state,TARGET)['stock'],before_delivery)
            self.assertGreater(item(game)['delivered'],1000)
            for _ in range(2):
                if item(game)['closed'] is None:
                    advance(game)
            original=item(game)
            self.assertLess(original['delivered'],original['purchased'])
            self.assertGreaterEqual(original['actual_extra_rations'],0)
            stock=grain_market.row(game.state,TARGET)['stock']
            city=game.state.cities[TARGET]
            # A price change or capacity change after departure uses actual terms.
            grain_market.transfer(game.state,TARGET,'sell',grain_market.row(game.state,TARGET)['capacity']-stock-1000)
            offer_sale=regional.sale_quote(game,game.state,original)
            self.assertEqual(offer_sale['batches'],1)
            before=city.gold,city.grain,grain_market.row(game.state,TARGET)['stock']
            seller=facilities.view(game,game.state)['cities'][TARGET]['eligible_actors'][0]
            payload=dict(action='sell',order=1,actor=seller,batches=1,token=offer_sale['price_token'])
            game.command(regional.COMMAND,payload,game.revision)
            city=game.state.cities[TARGET]
            self.assertEqual((city.gold,city.grain,grain_market.row(game.state,TARGET)['stock']),
                (before[0]+offer_sale['rate'],before[1]-1000,before[2]+1000))
            self.assertEqual(item(game)['sale_rate'],offer_sale['rate'])
            safe=game.export_save()
            with self.assertRaises(GameError):
                game.command(regional.COMMAND,payload,game.revision)
            self.assertEqual(game.export_save(),safe)
        self.assertEqual(Counter(name for name,_ in captures if name.startswith('regional_')),
            Counter(regional_purchase=1,regional_dispatch=1,regional_delivery=1,regional_transport_closed=1,regional_sale=1))

    def test_ownership_eligibility_and_cancellation(self):
        game=controlled()
        forecast=offer(game)
        s=game.state
        s.cities[SOURCE].gold=0
        self.assertEqual(regional.preview(game,s,OWNER,TARGET,3000,'trade',SOURCE)['reasons'],{'source_gold':1})
        s.cities[SOURCE].gold=200
        policy=logistics._pool(s)['cities'][SOURCE]['policy']
        minimum=policy['reserve_officers']
        policy['reserve_officers']=len(s.cities[SOURCE].roster.officer_ids)
        self.assertEqual(regional.preview(game,s,OWNER,TARGET,3000,'trade',SOURCE)['reasons'],{'no_escorts':1})
        policy['reserve_officers']=minimum
        buy(game,forecast)
        advance(game)
        row=item(game)
        t=game.state.cities[TARGET]
        t.owner='wei'
        self.assertIsNone(regional.sale_quote(game,game.state,row))
        t.owner=OWNER
        gold,grain,stock=t.gold,t.grain,grain_market.row(game.state,TARGET)['stock']
        game.command(regional.COMMAND,dict(action='cancel',order=1),game.revision)
        t=game.state.cities[TARGET]
        self.assertEqual((item(game)['status'],t.gold,t.grain,grain_market.row(game.state,TARGET)['stock']),
            ('cancelled',gold,grain,stock))

    def test_preview_does_not_change_random_state_and_reuses_route_work(self):
        game=controlled()
        st=game.state
        before=deepcopy(st)
        planner=Planner(game,st,OWNER)
        first=planner.options(st.cities[TARGET],1200,source=SOURCE)
        second=planner.options(st.cities[TARGET],1200,source=SOURCE)
        self.assertEqual(first,second)
        self.assertEqual((planner.work['route_searches'],planner.work['cache_hits']),(1,1))
        self.assertEqual(st,before)
        legacy=controlled(0)
        self.assertNotIn('regional_market',legacy.view()['catalog'])
        restored=Campaign(legacy.catalog)
        restored.load_save(legacy.export_save(compact=True),0)
        self.assertEqual(restored.to_dict(),legacy.to_dict())

    def test_battle_uses_target_snapshot_and_competes_for_the_last_batch(self):
        game, _, player=objectives.CoalitionBattleTests().ready()
        state,battle=game.state,game.state.battle
        target=battle['target']
        src=battle['source']
        market=fill_market(state,target,1000)
        fill_market(state,src,27000)
        pricing.initialize(state,pricing.PROCUREMENT)
        unit=next(row for row in battle['attackers'] if row['id']==player)
        site=next(row for row in battle_grid._field(battle)['services'] if row['kind']=='market')
        objectives.place(game,unit,(site['x'],site['y']))
        battle['extended']['tactical']['side']='attackers'
        town=max(2,facilities._pool(state)['cities'][target]['town'])
        price=pricing.snapshot(game,state,target,town)
        quote=battle_services.quote(game,state,battle,unit,'attackers')['trade']
        self.assertEqual((quote['rate'],quote['max_batches']),(price['buy'],1))
        self.assertEqual(price['adjustment'],4)
        self.assertEqual(pricing.snapshot(game,state,src)['adjustment'],-2)
        battle_services.execute(game,state,dict(battle_id=battle['id'],actor=player,
                                 action='buy_grain',batches=1),side='attackers')
        self.assertEqual(market['stock'],0)
        self.assertEqual(facilities.emergency_quote(game,state,state.cities[target],1000)['grain'],0)
        state.battle,state.phase,state.player=None,'city',state.cities[target].owner
        actor=battle['defenders'][0]['id']
        with self.assertRaises(GameError):
            facilities.trade(game,state,dict(city=target,actor=actor,direction='buy',batches=1),
                             state.player)

    def test_automatic_trade_needs_its_own_flag_and_honors_the_monthly_quota(self):
        for level in (2,3):
            with self.subTest(level=level):
                game=controlled(level)
                state=game.state
                state.player,state.phase='observer','ai'
                for city in state.cities.values():
                    if city.owner==OWNER:
                        city.gold,city.grain=40_000,500_000
                fill_market(state,SOURCE,280_000,100_000)
                fill_market(state,TARGET,0,100_000)
                facilities._pool(state)['cities'][SOURCE]['town']=3
                facilities._pool(state)['cities'][TARGET]['town']=1
                pricing.pool(state)['turn']=0
                pricing.refresh(state)
                regional.automatic_trade(game,state,OWNER,{TARGET:'actual_shortage'})
                self.assertFalse(pricing.pool(state)['orders'])
                regional.automatic_trade(game,state,OWNER,[])
                if level==2:
                    self.assertFalse(pricing.pool(state)['orders'])
                    continue
                row=item(game)
                self.assertEqual((row['purchased'],row['purchase_gold']),(20_000,120))
                self.assertEqual(quota_left(state,SOURCE,'buy'),5000)
                advance(game)
                self.assertEqual(item(game)['status'],'awaiting_sale')
                state.phase='ai'
                forecast=faction_economy.plan(game,state,OWNER).cities[TARGET]
                old_rate=regional.sale_quote(game,state,item(game),automatic=True,forecast=forecast)['rate']
                stock=grain_market.row(state,TARGET)
                grain_market.transfer(state,TARGET,'sell',stock['capacity']-stock['stock'])
                regional.automatic_trade(game,state,OWNER,[])
                self.assertEqual(item(game)['status'],'awaiting_sale')
                self.assertEqual(quota_left(state,TARGET,'sell'),25_000)
                grain_market.transfer(state,TARGET,'buy',stock['stock'])
                regional.automatic_trade(game,state,OWNER,[])
                self.assertEqual(item(game)['status'],'sold')
                self.assertEqual(item(game)['sale_rate'],old_rate)
                self.assertEqual(quota_left(state,TARGET,'sell'),25_000-item(game)['sold'])
                state.phase='city'
                restored=Campaign(game.catalog)
                restored.load_save(game.export_save(compact=True),0)
                self.assertEqual(pricing.pool(restored.state)['quotas'],pricing.pool(state)['quotas'])

    def test_commitment_and_transfer_properties(self):
        rng=Random(2026)
        game=controlled(stage=3)
        state=game.state
        for _ in range(1000):
            supply=rng.randrange(4000,80_000)
            initial=rng.randrange(supply*3+1)
            row=fill_market(state,SOURCE,initial,supply)
            for direction in ('buy','sell'):
                committed=rng.randrange(0,supply//4+1)
                pricing.pool(state)['quotas']={SOURCE:{direction:committed}}
                available=min(quota_left(state,SOURCE,direction),grain_market.available(state,SOURCE,direction))
                requested=rng.randrange(1,supply)
                settled=min(available,requested)
                if settled:
                    grain_market.transfer(state,SOURCE,direction,settled)
                    regional._use_quota(state,SOURCE,direction,settled)
                self.assertEqual(quota_left(state,SOURCE,direction),supply//4-committed-settled)
                self.assertEqual(row['opening_stock']+row['restocked']+row['sold']-row['purchased']-row['overflow'],
                    row['stock'])
                self.assertTrue(0<=row['stock']<=row['capacity'])

    def test_tagged_transport_properties(self):
        rng=Random(222)
        for _ in range(1000):
            purchased=rng.randrange(1,100_000)
            draw=rng.randrange(purchased+1)
            spent=rng.randrange(draw+1)
            row={'regional':dict(id=1,cargo=purchased,bag=0,consumed=0)}
            regional.track_cargo(row,'rations',purchased,purchased-draw)
            regional.track_meals(row,draw-spent)
            regional.track_cargo(row,'bag_return',purchased-draw,purchased-spent)
            self.assertEqual((row['regional']['cargo'],row['regional']['bag'],row['regional']['consumed']),
                (purchased-spent,0,spent))
            loss=rng.randrange(purchased-spent+1)
            regional.track_cargo(row,'weather',purchased-spent,purchased-spent-loss)
            self.assertEqual(row['regional']['cargo']+row['regional']['consumed']+loss,purchased)
