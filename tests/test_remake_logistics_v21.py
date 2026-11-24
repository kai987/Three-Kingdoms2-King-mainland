"""Transactional relief, sustainable forces, and deterministic V2.1 strategy replay."""
from pathlib import Path
from random import Random
from unittest import TestCase

from test_remake_diplomacy import diplomacy_catalog

from remake import battle_supply, city_economy, command_books, domestic, facilities
from remake import faction_economy as economy
from remake import grain_dispatch, grain_market, logistics, logistics_strategy as strategy, military_budget
from remake.campaign import Campaign, Catalog
from remake.strategic_ai import StrategicAI

ROOT = Path(__file__).resolve().parents[1]


class Headless(Campaign):
    def view(self):
        return {}


class LogisticsV21Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        def configure(data):
            data['logistics_granary_cities'] = ['xiangyang']
            data['links'].append(['xiangyang','jiangxia'])
            data['travel_routes'].append(dict(id='v21:xiangyang:jiangxia',mode='land',terrain='plain',
                **{'from':'xiangyang','to':'jiangxia'},distance_km=22,land_km=22,sea_km=0,days=1))
            data['city_income']['jiangxia']['reserves'] = 10
        cls.catalog = diplomacy_catalog(configure=configure)

    def start(self, *, player='observer'):
        game = Headless(self.catalog)
        game.command('new', dict(faction=player, seed=2026), 0)
        game.state.phase = 'ai'
        domestic.prepare_ai(game, game.state, 'shu')
        domestic.appointments(game.state, 'shu')['military'] = 951
        pool = game.state.extension['logistics']
        pool['cities']['xiangyang']['policy']['reserve_officers'] = 0
        return game

    def test_granary_supplies_a_city_using_one_physical_convoy(self):
        game = self.start()
        state = game.state
        source, target = state.cities['xiangyang'], state.cities['jiangxia']
        source.grain, target.grain = 300000, 1
        old_books = command_books.remaining(state, 'shu')
        plan = economy.plan(game, state, 'shu')
        self.assertEqual(plan.budgets[source.id]['months'], 12)
        self.assertIn(target.id, plan.shortages(state))
        requests = grain_dispatch.dispatch(game, state, 'shu', plan=plan)
        delivery, = next(row['allocations'] for row in requests if row['target'] == target.id)
        convoy, = state.extension['logistics']['convoys']
        self.assertEqual(delivery['convoy_id'], convoy['id'])
        self.assertEqual(source.grain, 300000-convoy['cargo']['grain']-delivery['escort_rations'])
        self.assertEqual(target.grain, 1)
        self.assertEqual(command_books.remaining(state, 'shu'), old_books-1)
        logistics.validate(game, state)

    def test_emergency_releases_below_strategy_without_emptying_donor(self):
        game = self.start()
        state = game.state
        source, target = state.cities['xiangyang'], state.cities['jiangxia']
        original = economy.plan(game, state, 'shu').budgets[source.id]
        source.grain, target.grain = original['fixed']*11, 0
        self.assertLess(source.grain, original['target'])
        plan = economy.plan(game, state, 'shu')
        result = grain_dispatch.dispatch(game, state, 'shu', plan=plan)
        allocations = [a for row in result for a in row['allocations'] if a['source']==source.id]
        self.assertTrue(allocations)
        self.assertTrue(all(row['released_reserve'] > 0 for row in allocations))
        self.assertGreaterEqual(source.grain, plan.budgets[source.id]['minimum_export_floor'])

    def test_ineligible_escorts_leave_no_ghost_convoy_and_market_can_help(self):
        game = self.start()
        state = game.state
        source, target = state.cities['xiangyang'], state.cities['jiangxia']
        source.grain, target.grain = 300000, 0
        policy = state.extension['logistics']['cities'][source.id]['policy']
        policy['reserve_officers'] = len(source.roster.officer_ids)
        plan = economy.plan(game, state, 'shu')
        requests = grain_dispatch.dispatch(game, state, 'shu', plan=plan)
        issue = next(row for row in requests if row['target']==target.id)
        self.assertIn('no_eligible_escort', issue['failures'])
        self.assertFalse(state.extension['logistics']['convoys'])
        self.assertTrue(any(row['bought'] > 0 for row in grain_dispatch.recover(game, state, 'shu', plan)))

    def test_late_receipt_cannot_pay_today_and_only_home_receives_rerouted_grain(self):
        game = self.start()
        state = game.state
        source, target = state.cities['xiangyang'], state.cities['jiangxia']
        source.grain, target.grain = 300000, 0
        grain_dispatch.dispatch(game, state, 'shu')
        row, = state.extension['logistics']['convoys']
        row['journeys'][-1]['arrival_turn'] = state.turn+3
        plan = economy.plan(game, state, 'shu')
        self.assertGreater(plan.budgets[target.id]['inbound'], 0)
        self.assertEqual(plan.budgets[target.id]['timely_grain'], 0)
        self.assertGreater(plan.cities[target.id].first_missing, 0)
        self.assertTrue(grain_dispatch.recover(game, state, 'shu', plan)[0]['bought'])
        replacement = state.cities['runan']
        quote = game._travel_path(state, source.id, replacement.id, 'shu', 'land')
        self.assertTrue(logistics._begin_journey(game, state, row, source.id, replacement.id,
            'land', quote, status='outbound', reason='waiting'))
        changed = economy.plan(game, state, 'shu')
        self.assertFalse(changed.budgets[target.id]['inbound'])
        self.assertGreater(changed.budgets[replacement.id]['inbound'], 0)

    def test_reservations_have_no_claim_on_already_dispatched_cargo(self):
        book = economy.Commitments()
        item = lambda ident, amount: economy.Commitment(str(ident), 'shu', 'source','dest',
                                                       amount, 2, 1, 1)
        first = item(1,8000)
        self.assertTrue(book.reserve(first,10000))
        self.assertFalse(book.reserve(item(2,8000),10000))
        self.assertFalse(book.reserve(first,10000))
        book.release(first)
        self.assertEqual(book.amount('source'),0)
        self.assertFalse(book.reserve(item(2,8000),2000))

    def test_supply_formula_and_garrison_composition(self):
        self.assertEqual(economy.sustainable(20000,3000,0,10000,18,9), 89444)
        self.assertEqual(economy.sustainable(20000,3000,0,10000,30,30), 46666)
        game = Headless(Catalog(ROOT/'game/data/campaigns/217-07.json'))
        game.command('new',dict(faction='observer',seed=2026),0)
        state = game.state
        city = state.cities['shuofang']
        budget = dict(regular=20000, residents=3000, wage_grain=0, active=100000, minimum_reserve=0)
        city.reserves = 10000
        cap = economy.capacity(game,state,city,budget)
        self.assertEqual(cap['sustainable_local'],46666)
        self.assertEqual(cap['excess_troops'],53334)

    def test_natural_reserves_cover_planned_recruitment(self):
        game = self.start()
        state = game.state
        city = state.cities['jiangxia']
        domestic.appointments(state,city.owner)['policy']['reserve_target'] = city.reserves+100
        budget = dict(threatened=False, next_natural_reserves=100, sustainable_combined=100000, active=0)
        self.assertEqual(economy.recruitment_limit(state,city,budget,200),0)
        self.assertEqual(economy.recruitment_limit(state,city,dict(budget,threatened=True),200),200)

    def test_hard_budget_and_valid_retreat(self):
        game = self.start()
        state = game.state
        source,target = state.cities['xiangyang'],state.cities['nanyang']
        ids = [source.roster.officer_ids[0]]
        quote = game._travel_path(state,source.id,target.id,'shu','fastest',adjacent=True)
        self.assertIsNotNone(quote)
        back = game._travel_path(state,target.id,source.id,'shu','fastest')
        self.assertIsNotNone(back)
        source.gold = 0
        plan = military_budget.sortie(game,state,source,target,ids,quote,back)
        source.grain = plan['hard_grain']
        exact = military_budget.sortie(game,state,source,target,ids,quote,back)
        self.assertTrue(exact['can_depart'])
        self.assertGreater(exact['planning_gold_gap'],0)
        self.assertEqual(exact['required_gold'],0)
        self.assertFalse(military_budget.sortie(game,state,source,target,ids,quote,None)['can_depart'])
        source.grain -= 1
        self.assertFalse(military_budget.sortie(game,state,source,target,ids,quote,back)['can_depart'])

    def test_adaptive_days_boundaries_and_manual_default(self):
        self.assertEqual([military_budget.battle_days(n) for n in (10000,10001,30000,30001,50000,50001,100000,100001)],
                         [7,10,10,15,15,20,20,30])
        self.assertEqual(military_budget.battle_days(100000, defenders=100000, incoming=True, limited_market=True),30)
        game = self.start(player='shu')
        state = game.state
        source,target=state.cities['xiangyang'],state.cities['nanyang']
        quote = game._travel_path(state,source.id,target.id,'shu','fastest',adjacent=True)
        self.assertEqual(battle_supply.departure_quote(state,[source.roster.officer_ids[0]],quote,game=game)
                         ['battle_days_budget'],30)

    def test_gold_rich_city_consumes_real_market_stock(self):
        game = self.start()
        state = game.state
        city = state.cities['jiangxia']
        city.grain,city.gold = 0,10000
        row = grain_market.row(state,city.id)
        row['stock'] = min(row['capacity'],12000)
        initial_cash, initial_market = city.gold,row['stock']
        plan = economy.plan(game,state,'shu')
        purchase = next(row for row in grain_dispatch.recover(game,state,'shu',plan) if row['target']==city.id)
        self.assertGreater(purchase['bought'],0)
        self.assertEqual(city.grain, purchase['bought'])
        self.assertEqual(row['stock'], initial_market-city.grain)
        self.assertLess(city.gold, initial_cash)
        self.assertEqual(state.extension['command_books']['factions']['shu']['orders'][-1]['kind'],'trade_grain')

    def test_peaceful_faction_does_not_accrue_blocked_turns(self):
        game = self.start()
        state = game.state
        for city in state.cities.values():
            if city.owner=='shu':
                city.grain=900000
        for _ in range(12):
            self.assertEqual(StrategicAI(game,state).record_pressure('shu'),0)
            state.turn += 1
        self.assertNotIn(strategy.PRESSURE,state.extension)

    def test_restore_strategy_receipt_and_continue_legacy_deterministically(self):
        game = self.start()
        state = game.state
        source, target = state.cities['xiangyang'], state.cities['nanyang']
        state.extension['ai_strategy']['shu'] = dict(target=target.id,created_turn=state.turn,
            last_turn=state.turn,review_turn=state.turn+2,arrival_turn=state.turn+2,
            orders=[dict(source=source.id,target=target.id,mode='fastest',departure_turn=state.turn+1,
                         arrival_turn=state.turn+2,officers=[source.roster.officer_ids[0]],march_id=None,provision=1000)])
        self.assertEqual(economy.pending(state,'shu').amount(source.id),1000)
        state.phase = 'city'
        for compact in (False,True):
            raw=game.export_save(compact=compact)
            restored=Headless(self.catalog)
            restored.load_save(raw,0)
            self.assertEqual(restored.export_save(compact=compact),raw)
            self.assertEqual(economy.pending(restored.state,'shu').amount(source.id),1000)
            restored.state.extension['ai_strategy']['shu']['orders'].clear()
            self.assertEqual(economy.pending(restored.state,'shu').amount(source.id),0)
        with strategy.experiment(0):
            legacy = Headless(self.catalog)
            legacy.command('new',dict(faction='observer',seed=2026),0)
            old = legacy.export_save(compact=True)
            legacy.command('observe_turn',{},legacy.revision)
        migrated=Headless(self.catalog)
        migrated.load_save(old,0)
        migrated.command('observe_turn',{},migrated.revision)
        self.assertEqual(migrated.export_save(compact=True),legacy.export_save(compact=True))

    def test_1000_random_commitment_batches(self):
        rng=Random(401)
        for sample in range(1000):
            book=economy.Commitments()
            stock=rng.randrange(0,100000)
            available=stock
            for ident in range(rng.randrange(1,9)):
                requested=rng.randrange(1,10000)
                item=economy.Commitment(str(ident),'shu','s','t',requested,4,1,2)
                accepted=book.reserve(item,stock)
                self.assertEqual(accepted,requested<=available)
                if accepted:
                    available-=requested
                self.assertEqual(book.amount('s'),stock-available)
                self.assertGreaterEqual(available,0)

    def test_1000_random_delivery_and_forecast_cases(self):
        rng=Random(402)
        game=self.start()
        state=game.state
        quote=game._travel_path(state,'xiangyang','jiangxia','shu','land')
        for sample in range(1000):
            stock, cost, harvest, cargo = (rng.randrange(0,100000) for _ in range(4))
            timeline=((0,cost,0),(0,cost,0),(harvest,cost,0))
            timely=economy.balance(stock,timeline,[(1,cargo)])
            with_late=economy.balance(stock,timeline,[(2,cargo)])
            self.assertEqual(timely[0][0],(1,max(0,cost-stock)))
            self.assertGreaterEqual(sum(gap for _,gap in with_late[0]),sum(gap for _,gap in timely[0]))
            self.assertTrue(all(balance>=0 for balance in timely[1]))
            demand=rng.randrange(0,100000)
            gross=logistics.gross_shipment(game,quote,demand,cargo)
            net=logistics.projected_grain(game,quote,gross)
            self.assertLessEqual(gross,cargo)
            self.assertGreaterEqual(net,min(demand,logistics.projected_grain(game,quote,cargo)))

    def test_1000_random_hard_budgets_and_garrison_capacity(self):
        rng=Random(403)
        game=self.start()
        state=game.state
        home,target=state.cities['xiangyang'],state.cities['nanyang']
        ident=home.roster.officer_ids[0]
        outward=game._travel_path(state,home.id,target.id,'shu','fastest',adjacent=True)
        back=game._travel_path(state,target.id,home.id,'shu','fastest')
        for sample in range(1000):
            troops,grain,reserves=rng.randrange(1,10001),rng.randrange(0,10000),rng.randrange(0,10000)
            state.officers[ident].troops=troops
            home.grain,home.reserves=grain,reserves
            budget=military_budget.sortie(game,state,home,target,[ident],outward,back)
            self.assertEqual(budget['can_depart'],grain>=budget['hard_grain'])
            self.assertEqual(budget['hard_grain'],budget['home_next']+budget['immediate'])
            self.assertEqual(budget, military_budget.sortie(game,state,home,target,[ident],outward,back))
            value=economy.sustainable(grain,0,0,reserves,18,9)
            self.assertEqual(value,max(0,(grain*100-9*reserves)//18))
