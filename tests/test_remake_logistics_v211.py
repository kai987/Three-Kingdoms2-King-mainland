"""Round-trip relief and recovery are deterministic services on live commands."""
from copy import deepcopy
from fractions import Fraction
from random import Random
from unittest import TestCase

from browser_resupply_fixture import resupply_catalog
from remake import army_relief, grain_units, logistics, logistics_rules as rules, march_supply, war_recovery
from remake import logistics_strategy as strategy
from remake.campaign import Campaign
from remake.errors import GameError


class Headless(Campaign):
    def view(self):
        return {}


class LogisticsV211Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=resupply_catalog()

    def game(self):
        game=Headless(self.catalog,record_journal=False)
        game.command('new',dict(faction='shu',seed=2026),0)
        game.command('set_domestic',dict(faction='shu',civil=None),game.revision)
        return game

    def advance(self,game):
        game.command('end_turn',{},game.revision)
        game.command('ai',dict(turn=game.state.turn),game.revision)
        if game.state.phase=='arrivals':
            game.command('arrivals',{},game.revision)

    def stranded(self,game):
        city=game.state.cities['nanyang']
        officer=city.roster.officer_ids[1]
        game.command('transfer',dict(source=city.id,target='bajun',officers=[officer],route_mode='land'),game.revision)
        self.advance(game)
        target,=game.state.extension['travel']['marches']
        self.assertEqual(march_supply.current_city(target),'nanjun')
        self.assertEqual(target['supply']['remaining'],0)
        return target['id']

    def roundtrip(self,game,compact):
        save=game.export_save(compact=compact)
        result=Headless(self.catalog,record_journal=False)
        result.load_save(save,0)
        self.assertEqual(result.export_save(compact=compact),save)
        return result

    def test_actual_command_funds_courier_and_returns_it(self):
        game=self.game()
        ident=self.stranded(game)
        state=game.state
        donor=state.cities['jiangxia']
        old_grain=donor.grain
        with grain_units.using(state):
            before=game.export_save()
            box=next(row for row in logistics.rescue_targets(game,state,donor.id) if row['march_id']==ident)
            self.assertEqual(before,game.export_save())
        self.assertTrue(box['can_dispatch'],box)
        self.assertEqual(box['city'],'nanjun')
        self.assertGreater(box['relief']['outbound'],0)
        self.assertGreater(box['relief']['returning'],0)
        self.assertGreater(box['relief']['wait'],0)
        self.assertGreater(box['relief']['safety'],0)
        game.command('dispatch_transport',dict(source=donor.id,target=box['city'],target_march=ident,
            officers=box['officers'],cargo=dict(gold=0,grain=box['max_grain'],reserves=0),
            route_mode=box['route_mode']),game.revision)
        convoy,=game.state.extension['logistics']['convoys']
        self.assertEqual(old_grain-game.state.cities[donor.id].grain,
                         convoy['initial_cargo']['grain']+convoy['journeys'][0]['supply']['loaded'])
        game=self.roundtrip(game,False)
        game=self.roundtrip(game,True)
        self.advance(game)
        convoy,=game.state.extension['logistics']['convoys']
        self.assertTrue(convoy['delivery_done'],convoy['reason'])
        self.assertGreater(convoy['delivered']['grain'],0)
        self.assertTrue(logistics.valid_grain_receipt(logistics.grain_receipt(convoy)))
        self.assertTrue(all(j['supply']['lost']==0 for j in convoy['journeys']))
        self.assertEqual(convoy['target'],donor.id)
        self.assertEqual(convoy['status'],'returning')
        self.assertFalse(any(entry['kind']=='city' for j in convoy['journeys']
                             for entry in j['supply']['refills']))
        game=self.roundtrip(game,True)
        self.advance(game)
        self.assertFalse(game.state.extension['logistics']['convoys'])

    def test_old_policy_does_not_change_when_loaded_by_new_engine(self):
        with strategy.experiment(strategy.WAR):
            game=self.game()
            self.stranded(game)
            before=game.export_save()
        self.assertEqual(before['state']['extension'][strategy.FIELD],strategy.V21)
        loaded=self.roundtrip(game,True)
        self.assertFalse(strategy.army_relief(loaded.state))
        self.assertFalse(strategy.war_recovery(loaded.state))
        with strategy.experiment(strategy.WAR):
            self.advance(game)
        self.advance(loaded)
        self.assertEqual(game.export_save(),loaded.export_save())

    def test_cannot_spend_unavailable_round_trip_grain(self):
        game=self.game()
        ident=self.stranded(game)
        with grain_units.using(game.state):
            quote,=logistics.rescue_targets(game,game.state,'jiangxia')
        game.state.cities['jiangxia'].grain=quote['cost_grain']
        before=game.export_save()
        with self.assertRaises(GameError):
            game.command('dispatch_transport',dict(source='jiangxia',target=quote['city'],target_march=ident,
                officers=quote['officers'],cargo=dict(gold=0,grain=1,reserves=0),
                route_mode=quote['route_mode']),game.revision)
        self.assertEqual(before,game.export_save())

    def test_light_eligible_escort_beats_an_equally_safe_full_garrison(self):
        game=self.game()
        army=self.stranded(game)
        state=game.state
        donor=state.cities['jiangxia']
        first, light, *_=donor.roster.officer_ids
        for ident, troops in ((first,10000),(light,0)):
            state.soldiers['initial']+=troops-state.officers[ident].troops
            state.officers[ident].troops=troops
        state.extension['logistics']['cities'][donor.id]['policy']['reserve_officers']=0
        with grain_units.using(state):
            choices,_=army_relief.Planner(game,state,'shu').candidates(donor)
        self.assertTrue(choices)
        self.assertEqual(choices[0]['march_id'],army)
        self.assertIn(light,choices[0]['officers'])
        self.assertNotIn(first,choices[0]['officers'])
        self.assertEqual(state.officers[first].troops,10000)

    def test_existing_timely_cargo_and_late_cargo_have_different_effect(self):
        game=self.game()
        ident=self.stranded(game)
        state=game.state
        with grain_units.using(state):
            planner=army_relief.Planner(game,state,'shu')
            need=planner.demands[ident]
            self.assertGreater(need.required,0)
            before=state.rng.draws
            option,_=planner.candidates(state.cities['jiangxia'])
            self.assertTrue(option)
            chosen=option[0]
            self.assertEqual(state.rng.draws,before)
            grain=chosen['relief']['estimated_net']
            self.assertEqual(army_relief.net_requirement(need.required,[(need.deadline+1,grain)],need.deadline),
                             need.required)
            self.assertEqual(army_relief.net_requirement(need.required,[(need.deadline,grain)],need.deadline),
                             max(0,need.required-grain))

    def test_reroute_when_meeting_city_changes_and_keep_the_army_cargo(self):
        game=self.game()
        ident=self.stranded(game)
        with grain_units.using(game.state):
            box,=logistics.rescue_targets(game,game.state,'jiangxia')
        game.command('dispatch_transport',dict(source='jiangxia',target=box['city'],target_march=ident,
            officers=box['officers'],cargo=dict(gold=0,grain=box['max_grain'],reserves=0),
            route_mode=box['route_mode']),game.revision)
        state=game.state
        convoy,=state.extension['logistics']['convoys']
        original,bag=convoy['cargo']['grain'],convoy['journeys'][0]['supply']['loaded']
        state.cities['nanjun'].owner='wei'
        logistics.synchronize(game,state)
        before=state.cities['jiangxia'].grain
        with grain_units.using(state):
            self.assertEqual(army_relief.hold_reason(game,state,convoy,11),'target_changed')
            self.assertTrue(army_relief.settle(game,state,convoy))
        self.assertEqual(state.cities['jiangxia'].grain,before+original+bag)
        self.assertFalse(state.extension['logistics']['convoys'])
        self.assertEqual(convoy['delivered']['grain'],0)
        self.assertTrue(logistics.valid_grain_receipt(logistics.grain_receipt(convoy,returned=True)))

    def test_replanned_convoy_keeps_a_still_valid_meeting(self):
        game=self.game()
        ident=self.stranded(game)
        with grain_units.using(game.state):
            box,=logistics.rescue_targets(game,game.state,'jiangxia')
        game.command('dispatch_transport',dict(source='jiangxia',target=box['city'],target_march=ident,
            officers=box['officers'],cargo=dict(gold=0,grain=box['max_grain'],reserves=0),
            route_mode=box['route_mode']),game.revision)
        state=game.state
        convoy,=state.extension['logistics']['convoys']
        convoy['reason']='rendezvous_replanned'
        prior=deepcopy(convoy['journeys'])
        with grain_units.using(state):
            self.assertTrue(army_relief.settle(game,state,convoy))
        self.assertEqual(state.extension['logistics']['convoys'],[convoy])
        self.assertEqual(convoy['journeys'],prior)

    def test_war_recovery_uses_receipted_losses_then_releases_reserves(self):
        game=self.game()
        state=game.state
        city=state.cities['nanyang']
        city.reserves=500
        war_recovery.record(state,'shu',city.id,'battle',450)
        war_recovery.record(state,'shu',city.id,'march',80)
        war_recovery.record(state,'shu',city.id,'convoy',25)
        war_recovery.record(state,'shu',city.id,'allocation',200)
        self.assertEqual(war_recovery.burden(state,'shu',city.id),355)
        with grain_units.using(state):
            view=war_recovery.Forecast(game,state,'shu')
            # Both prospective columns draw on the same physical reserve.
            quote=view.assess(((city.id,1000,100),(city.id,4000,50)),target='xiangyang')
            self.assertEqual(quote['prospective_losses'],1000)
            self.assertLessEqual(quote['reserves_assigned'],500)
            self.assertEqual(war_recovery.loss_budget(350,500,18,300),(350,0,0,0))
            self.assertIsNone(war_recovery.months_for(100,25,[(6,90)],-10))
        self.assertEqual(state.extension[war_recovery.FIELD]['shu'][city.id],[[1,450,80,25,200]])
        state.turn+=war_recovery.RECENT_TURNS
        self.assertEqual(war_recovery.burden(state,'shu',city.id),0)

    def test_five_opening_load_shapes_and_thirty_day_reference(self):
        scale=rules.RATION_SCALE
        self.assertEqual([army_relief.ration_budget(troop+100,30*125*scale//100,0,0,safety=0).total
                          for troop in (0,100,500,1000,3000,5000,10000)],
                         [75,150,450,825,2325,3825,7575])
        # Recorded departure conditions from E4 207-09 seed 2027.
        observed=[(5394,836,9901),(10000,1909,22120),(10000,505,30796),
                  (10000,2839,4668),(10000,505,5678)]
        self.assertTrue(all(first_leg<full for _,first_leg,full in observed))
        downstream,upstream=12*105*scale//100,12*115*scale//100
        bag=army_relief.ration_budget(1100,downstream,0,upstream,safety=0)
        self.assertGreater(bag.returning,bag.outbound)

    def test_1000_budgets_total_credit_and_cargo_conservation(self):
        rng=Random(2112026)
        divisor=grain_units.denominator()*rules.RATION_SCALE
        for _ in range(1000):
            units=rng.randrange(100,100000)
            weights=[rng.randrange(0,15000000) for _ in range(3)]
            credit=rng.randrange(divisor)
            bag=army_relief.ration_budget(units,*weights,credit=credit)
            expected=rules.ceil_div(max(0,units*sum(weights)-credit),divisor)
            self.assertEqual(bag.total,expected+rules.ceil_div(expected,10))
            self.assertGreaterEqual(min(bag),0)
            cargo=rng.randrange(20000)
            rations=rng.randrange(cargo+1)
            lost,remainder=rules.cargo_loss(cargo-rations,rng.randrange(150001),0)
            following=cargo-rations-lost
            self.assertGreaterEqual(following,0)
            receipt=dict(cargo_dispatched=cargo,cargo_received=0,cargo_rations=rations,
                cargo_route_loss=lost,cargo_weather_loss=0,cargo_delivered=following,cargo_returned=0,
                cargo_remaining=0,cargo_abandoned=0,cargo_loss_remainder=remainder,
                escort_base_grain=0,escort_extra_grain=0)
            self.assertTrue(logistics.valid_grain_receipt(receipt))

    def test_1000_meeting_windows_and_deadline_deduplication(self):
        rng=Random(2112027)
        for _ in range(1000):
            now=rng.randrange(0,2000)
            start=now+rng.randrange(100)
            close=start+rng.randrange(10)
            travel=rng.randrange(100)
            actual=army_relief.timing(army_relief.Window('node',start,close),now,travel)
            if now+travel>close:
                self.assertIsNone(actual)
            else:
                eta,wait=actual
                self.assertLessEqual(start,eta)
                self.assertLessEqual(eta,close)
                self.assertGreaterEqual(wait,eta-(now+travel)+army_relief.WAIT_DAYS)
            grain=rng.randrange(10000)
            on_time=rng.randrange(10000)
            late=rng.randrange(10000)
            commitments=[(start+1,late),(start,on_time)]
            self.assertEqual(army_relief.net_requirement(grain,commitments,start),max(0,grain-on_time))
            self.assertEqual(army_relief.net_requirement(grain,commitments,start),
                             army_relief.net_requirement(grain,reversed(commitments),start))

    def test_1000_recovery_budgets_share_reserves_and_keep_defence_legal(self):
        rng=Random(2112028)
        for _ in range(1000):
            columns=[rng.randrange(100000) for _ in range(3)]
            reserves=rng.randrange(100000)
            gold,grain=rng.randrange(21),rng.randrange(301)
            allocated,draft,money,food=war_recovery.loss_budget(sum(columns),reserves,gold,grain)
            self.assertLessEqual(allocated,reserves)
            self.assertEqual(allocated+draft,sum(columns))
            self.assertEqual(money,rules.ceil_div(draft*gold,100))
            self.assertEqual(food,rules.ceil_div(draft*grain,100))
            self.assertIsNone(war_recovery.recovery_time(1,0))
            self.assertIsNone(war_recovery.recovery_time(1,-300))
            self.assertEqual(war_recovery.months_for(100,0,[(6,100)],0),Fraction(2))
            self.assertIsNone(war_recovery.months_for(100,0,[(6,99)],0))
            attack,prepare=war_recovery.action_score(0,10000,35,4,123,necessary=True)
            self.assertGreater(attack,prepare)
            attack,prepare=war_recovery.action_score(0,10000,35,4,123)
            self.assertLess(attack,prepare)
