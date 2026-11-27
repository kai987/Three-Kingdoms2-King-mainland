"""Deterministic logistics policy, inventory and recovery regressions."""
from fractions import Fraction
from pathlib import Path
from random import Random
from types import SimpleNamespace
import sys
from unittest import TestCase

import test_remake_logistics_v211 as previous
from remake import army_relief, command_books, escort_planning, grain_units, logistics
from remake import logistics_strategy as strategy, march_supply, occupation_budget, staging_supply, treasures, war_recovery
from remake.errors import GameError
from remake.faction_economy import Commitment, Commitments
from remake.officers import OFFICER_TROOP_CAP
from remake.strategic_ai import StrategicAI

TOOLS = Path(__file__).resolve().parents[1] / 'tools' / 'economy-balance'
sys.path.insert(0,str(TOOLS))
from observer_v212 import Episode, availability

SETTINGS = dict(occupation=True, after_six=60, no_source=55)


class LogisticsV212Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=previous.resupply_catalog()

    advance=previous.LogisticsV211Tests.advance
    stranded=previous.LogisticsV211Tests.stranded
    roundtrip=previous.LogisticsV211Tests.roundtrip

    def game(self,new=True):
        game=previous.Headless(self.catalog,record_journal=False)
        with strategy.experiment(4,army=True,recovery=True,candidate=SETTINGS if new else None):
            game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_domestic',dict(faction='shu',civil=None),game.revision)
        return game

    def set_troops(self,state,ident,troops):
        state.soldiers['initial']+=troops-state.officers[ident].troops
        state.officers[ident].troops=troops

    def test_staging_grain_stays_in_city_until_march_reaches_the_node(self):
        game=self.game()
        state=game.state
        city,target,node=(state.cities[key] for key in ('nanyang','bajun','nanjun'))
        grain=2000
        node.grain=grain
        budget=dict(minimum_export_floor=0,safety_reserve=0,next_installment=0,reserved_grain=0)
        ident=city.roster.officer_ids[1]
        with grain_units.using(state):
            game._queue_march(state,city,target,[ident],'transfer','land',staging_budgets={node.id:budget})
        row,=state.extension['travel']['marches']
        reservation,=state.extension[staging_supply.FIELD]
        self.assertEqual(node.grain,grain)
        self.assertGreater(reservation['reserved'],0)
        self.assertEqual(staging_supply.available(state,node),grain-reservation['reserved'])
        self.assertFalse(row['supply']['refills'])
        game=self.roundtrip(game,False)
        game=self.roundtrip(game,True)
        state=game.state
        row,=state.extension['travel']['marches']
        with grain_units.using(state):
            march_supply.advance_unit(game,state,row,row,absolute_tick=10)
            self.assertEqual(state.cities[node.id].grain,grain)
            march_supply.advance_unit(game,state,row,row,absolute_tick=11)
        receipt,=row['supply']['refills']
        self.assertEqual(receipt['source'],node.id)
        self.assertEqual(state.cities[node.id].grain+receipt['grain'],grain)
        self.assertEqual(staging_supply.held(state,node.id),0)

    def test_competing_columns_cannot_spend_the_same_checkpoint_grain(self):
        game=self.game()
        state=game.state
        source,target,node=(state.cities[key] for key in ('nanyang','bajun','nanjun'))
        # Controlled, equal-strength detachments competing for one node.
        first,second=source.roster.officer_ids[1:3]
        for ident in (first,second):
            self.set_troops(state,ident,1000)
        source.grain=3000
        node.grain=3000
        rule=dict(minimum_export_floor=0,safety_reserve=0,next_installment=0,reserved_grain=0)
        budgets={node.id:rule}
        with grain_units.using(state):
            quote=game._travel_path(state,source.id,target.id,source.owner,'land',officers=[first])
            _,booking=staging_supply.assess(game,state,source,[first],quote,budgets)
            need=booking[0]['required']
            node.grain=need+need//2
            game._queue_march(state,source,target,[first],'transfer','land',staging_budgets=budgets)
            before=game.export_save()
            with self.assertRaises(GameError):
                game._queue_march(state,source,target,[second],'transfer','land',staging_budgets=budgets)
            self.assertEqual(game.export_save(),before)
        self.assertEqual(staging_supply.held(state,node.id),need)
        self.assertEqual(node.grain,need+need//2)

    def test_node_ownership_and_retreat_release_unused_budget(self):
        game=self.game()
        state=game.state
        city,target,node=(state.cities[key] for key in ('nanyang','bajun','nanjun'))
        node.grain=2000
        budget=dict(minimum_export_floor=0,safety_reserve=0,next_installment=0,reserved_grain=0)
        with grain_units.using(state):
            game._queue_march(state,city,target,[city.roster.officer_ids[1]],'transfer','land',
                              staging_budgets={node.id:budget})
        self.assertGreater(staging_supply.held(state,node.id),0)
        node.owner='wei'
        staging_supply.synchronize(state)
        self.assertNotIn(staging_supply.FIELD,state.extension)
        self.assertEqual(node.grain,2000)

    def test_paid_light_escort_keeps_every_soldier_and_dispatches_a_valid_ledger(self):
        game=self.game()
        march=self.stranded(game)
        state=game.state
        city=state.cities['jiangxia']
        policy=logistics._pool(state)['cities'][city.id]['policy']
        policy['reserve_officers']=0
        city.grain=6000
        ids=escort_planning.eligible(game,state,city)
        self.assertTrue(ids)
        for ident in ids:
            self.set_troops(state,ident,OFFICER_TROOP_CAP)
        chosen=ids[0]
        start=sum(state.officers[i].troops for i in city.roster.officer_ids)+city.reserves
        stock=city.grain
        books=command_books.remaining(state,city.owner)
        with grain_units.using(state):
            plan=army_relief.Planner(game,state,city.owner)
            changes=escort_planning.can_change(game,state,city,None,chosen)
            self.assertIsNotNone(changes)
            options,_=plan.candidates(city,loads={chosen:500})
            route,=options[:1]
            self.assertEqual(route['march_id'],march)
            logistics.dispatch(game,state,dict(source=city.id,target=route['city'],target_march=march,
                officers=[chosen],cargo=dict(gold=0,grain=route['max_grain'],reserves=0),
                route_mode=route['route_mode']),city.owner,relief_planner=plan,allocation=changes)
        result,=state.extension['logistics']['convoys']
        self.assertEqual(sum(state.officers[i].troops for i in city.roster.officer_ids)+city.reserves,start)
        self.assertEqual(state.officers[chosen].troops,500)
        self.assertEqual(books-command_books.remaining(state,city.owner),
                         command_books.cost('allocate')+command_books.cost('dispatch_transport'))
        self.assertEqual(stock-city.grain,result['initial_cargo']['grain']+result['journeys'][0]['supply']['loaded'])
        treasures.synchronize(game,state)
        self.roundtrip(game,True)

    def test_reserved_war_officer_and_current_transport_receipts(self):
        game=self.game()
        city=game.state.cities['jiangxia']
        state=game.state
        broker=escort_planning.eligible(game,state,city)[0]
        state.extension['ai_strategy'][city.owner]=dict(orders=[
            dict(source=city.id,target='xiangyang',march_id=None,departure_turn=state.turn,officers=[broker])])
        self.assertNotIn(broker,escort_planning.eligible(game,state,city))
        logistics._pool(state)['receipts'][str(broker)]=state.turn+1
        data=availability(game,state,city,'no_spare_officer',[])
        self.assertIn('officer_busy',data['officer_exclusions'][str(broker)])
        self.assertNotIn(broker,logistics._eligible(game,state,city))

    def test_occupation_is_based_on_active_guard_then_cleared(self):
        game=self.game()
        state=game.state
        city=state.cities['xiangyang']
        state.player='observer'
        with grain_units.using(state):
            occupation_budget.captured(state,city)
            city.grain=0
            ai=StrategicAI(game,state)
            rows=occupation_budget.record(ai,city.owner,ai.economy_plan(city.owner))
            self.assertEqual(len(rows),1)
            self.assertGreater(rows[0]['local_risk'],0)
            city.grain=1_000_000
            city.owner='shu'
            occupation_budget.prune(state)
            self.assertNotIn(occupation_budget.FIELD,state.extension)

    def test_troop_eligibility_and_reassignment_1000_seeded_cases(self):
        rng=Random(21201)
        cap=OFFICER_TROOP_CAP
        for _ in range(1000):
            current=rng.randint(0,cap)
            capacity=rng.randint(0,cap)
            stock=rng.randint(0,capacity)
            original={i:rng.randint(0,cap) for i in range(rng.randint(0,6))}
            plan=escort_planning.arrange(current,stock,list(original.items()),capacity=capacity)
            lawful=500<current<=500+capacity-stock+sum(cap-n for n in original.values())
            self.assertEqual(plan is not None,lawful)
            if plan is None:
                continue
            after=original | plan
            reserves=stock+(current-500)-sum(after[i]-original[i] for i in original)
            self.assertEqual(sum(original.values())+current+stock,sum(after.values())+500+reserves)
            self.assertTrue(stock<=reserves<=capacity)
            self.assertTrue(all(original[i]<=n<=cap for i,n in after.items()))

    def test_episode_and_inventory_conservation_1000_seeded_cases(self):
        rng=Random(21202)
        for idx in range(1000):
            stock=rng.randint(0,20000)
            required=rng.randint(1,20000)
            demands=Episode(idx,'shu',1,1,21,21,required)
            book=Commitments()
            for n in range(4):
                amount=rng.randint(1,20000)
                item=Commitment(str(n),'shu','depot','army',amount,1,1,2)
                accepted=book.reserve(item,stock)
                if accepted:
                    self.assertFalse(book.reserve(item,stock))
                self.assertLessEqual(book.amount('depot'),stock)
                demands.update(required,21)
            first=min(book.amount('depot'),required)
            demands.deliver(first,20,'city','depot')
            demands.update(required-first,21)
            demands.deliver(2*required,22,'convoy',idx)
            row=demands.row(24)
            self.assertEqual(row['original_required_grain']+row['additional_required_grain'],required)
            self.assertEqual(row['timely_delivered_grain']+row['late_delivered_grain'],required)
            self.assertEqual(row['remaining_unmet_grain'],0)

    def test_recovery_stock_and_defence_1000_seeded_cases(self):
        rng=Random(21203)
        policy=dict(after_six=60,no_source=55)
        game=self.game()
        state=game.state
        state.player='observer'
        city=state.cities['xiangyang']
        occupation_budget.captured(state,city)
        with grain_units.using(state):
            planner=StrategicAI(game,state)
            plan=planner.economy_plan(city.owner)
        base=plan.budgets[city.id]
        economy=SimpleNamespace(budgets={city.id:dict(base)},cities={city.id:SimpleNamespace(first_missing=0)})
        threat=[0]
        ai=SimpleNamespace(state=state,threat=lambda _:threat[0])
        for _ in range(1000):
            losses,stock=(rng.randrange(40000) for _ in range(2))
            reserve,draft,gold,grain=war_recovery.loss_budget(losses,stock,8,15)
            self.assertEqual(reserve+draft,losses)
            self.assertLessEqual(reserve,stock)
            loss=war_recovery.months_for(grain,grain,[],rng.randint(-1000,0))
            self.assertEqual(loss,Fraction(0))
            no_supply=war_recovery.months_for(grain+1,grain,[],rng.randint(-1000,0))
            self.assertIsNone(no_supply)
            self.assertEqual(war_recovery.multiplier(no_supply,policy),55)
            self.assertEqual(war_recovery.multiplier(Fraction(7),policy),60)
            attack,alternative=war_recovery.action_score(0,100,55,rng.randint(0,8),gold,necessary=True)
            self.assertGreater(attack,alternative)
            threat[0]=rng.randrange(20000)
            economy.budgets[city.id]['active']=rng.randrange(20000)
            short=rng.randrange(400) if rng.randrange(2) else 0
            economy.cities[city.id].first_missing=short
            city.grain=stock
            before=city.grain,city.gold,city.reserves,state.rng.draws
            row,=occupation_budget.assess(ai,city.owner,economy)
            self.assertEqual(row['status']=='secured',not short and row['garrison']>=row['defense'])
            self.assertTrue(0<=row['local_risk']<=20)
            self.assertEqual(before,(city.grain,city.gold,city.reserves,state.rng.draws))

    def test_unchanged_211_default_and_212_policy_save(self):
        self.assertEqual(self.game(False).state.extension[strategy.FIELD],211)
        game=self.game()
        self.assertEqual(game.state.extension[strategy.POLICY],SETTINGS)
        for compact in (False,True):
            self.roundtrip(game,compact)
