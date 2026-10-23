"""Coherent saved-food forgeries must fail without altering a live campaign.

These fixtures re-sign the ordinary integrity checksum deliberately. They test
the domain receipt replay, rather than treating that checksum as authentication.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,digest
from remake.errors import GameError
import test_remake_segment_supply as fixtures


class SegmentSupplySecurityTests(unittest.TestCase):
    def game(self,**options):
        return fixtures.SegmentSupplyTests().game(**options)

    def queue(self,game):
        return fixtures.SegmentSupplyTests().queue(game)

    def step(self,game):
        return fixtures.SegmentSupplyTests().step(game)

    def reject(self,game,mutate):
        original=game.export_save();revision=game.revision
        bad=deepcopy(original)
        mutate(bad['state'])
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises((GameError,ValueError)):
            game.load_save(bad,revision)
        self.assertEqual(game.export_save(),original)
        self.assertEqual(game.revision,revision)

    @staticmethod
    def row(state):
        return state['extension']['travel']['marches'][0]

    @staticmethod
    def eta(state,row):
        remaining=row['quote']['days']-row['supply']['route_days']
        row['arrival_turn']=state['turn']+max(1,(remaining+9)//10) if remaining else state['turn']

    def returning(self):
        game=self.game(checkpoint_grain=0);self.queue(game)
        for _ in range(5):
            self.step(game)
            rows=game.state.extension['travel']['marches']
            if rows and rows[0]['history']:
                self.assertEqual(rows[0]['status'],'returning')
                return game
        self.fail('The real shortage never created the required return journey')

    def test_zero_meal_weights_cannot_refund_food_for_live_travellers(self):
        game=self.game();self.queue(game);self.step(game)
        for omit_initial in (False,True):
            def forge(state):
                bag=self.row(state)['supply']
                if omit_initial:
                    bag['ration_manifests']=[dict(tick=bag['start_tick']+1,troops={},reserves=0)]
                    start=0
                else:
                    bag['ration_manifests'].append(dict(tick=bag['start_tick']+2,troops={},reserves=0))
                    start=1
                meals=bag['periods'][0]['days']
                for index in range(start,len(meals)):
                    meals[index]=[0,0,meals[index][2],0]
                bag['consumed']=sum(meal[1] for meal in meals if meal is not None)
                bag['credit_units']=sum(meal[1]*1000-meal[0] for meal in meals if meal is not None)
                bag['remaining']=bag['loaded']+bag['received']-bag['consumed']
            with self.subTest(omit_initial=omit_initial):
                self.reject(game,forge)

    def test_negative_inventory_or_daily_payment_is_rejected(self):
        game=self.game();self.queue(game);self.step(game)
        self.reject(game,lambda state:self.row(state)['supply'].__setitem__('remaining',-1))
        self.reject(game,lambda state:self.row(state)['supply']['periods'][0]['days'][0].__setitem__(1,-1))

    def test_rewinding_the_whole_food_clock_cannot_restore_eaten_rations(self):
        game=self.game();self.queue(game);self.step(game)
        first=deepcopy(game.state.extension['travel']['marches'][0]['supply'])
        self.step(game)
        def forge(state):
            row=self.row(state);row['supply']=deepcopy(first)
            self.eta(state,row)
        self.reject(game,forge)

    def test_grain_delivered_at_day_twenty_cannot_pay_for_earlier_days(self):
        game=self.game();self.queue(game);self.step(game);self.step(game)
        bag=game.state.extension['travel']['marches'][0]['supply']
        self.assertEqual(bag['refills'][0]['tick'],10)
        self.assertEqual(bag['clock_tick'],20)
        def forge(state):
            supply=self.row(state)['supply']
            supply['refills'][0]['tick']=supply['clock_tick']
        self.reject(game,forge)

    def test_unfunded_outbound_column_cannot_leave_its_checkpoint_by_editing_move_bits(self):
        game=self.game(days=(5,20),checkpoint_grain=0);self.queue(game);self.step(game)
        row=game.state.extension['travel']['marches'][0]
        self.assertFalse(row['history'])
        self.assertEqual(row['supply']['route_days'],5)
        self.assertTrue(row['supply']['waiting'])
        def forge(state):
            row=self.row(state);bag=row['supply']
            for meal in bag['periods'][0]['days']:
                if meal is not None:meal[2]=1
            bag['route_days']=sum(meal[2] for period in bag['periods'] for meal in period['days'] if meal is not None)
            bag['waiting']=False
            self.eta(state,row)
        self.reject(game,forge)

    def test_waiting_another_full_period_cannot_be_rewritten_as_unused_arrival_days(self):
        game=self.game(days=(1,1));self.queue(game);self.step(game)
        # This is the same service flag set by a full destination. It does not
        # edit time, food, troops or the real daily service being tested.
        game.state.extension['travel']['marches'][0]['supply']['waiting']=True
        self.step(game)
        self.assertEqual(game.state.extension['travel']['marches'][0]['supply']['elapsed_days'],12)
        def forge(state):
            bag=self.row(state)['supply']
            first=[meal for meal in bag['periods'][0]['days'] if meal is not None]
            bag['periods'][1]['days']=[None]*10
            bag['elapsed_days']=len(first)
            bag['consumed']=sum(meal[1] for meal in first)
            bag['credit_units']=sum(meal[1]*1000-meal[0] for meal in first)
            bag['remaining']=bag['loaded']+bag['received']-bag['consumed']
        self.reject(game,forge)

    def test_outbound_convoy_cannot_bypass_the_same_checkpoint_food_boundary(self):
        game=self.game(days=(5,20),checkpoint_grain=0)
        ident=game.state.cities['xiangyang'].roster.officer_ids[1]
        game.command('set_logistics',dict(city='xiangyang',policy=dict(reserve_officers=0,
            reserve_gold=0,reserve_grain=0,reserve_reserves=0)),game.revision)
        game.command('dispatch_transport',dict(source='xiangyang',target='jiangxia',officers=[ident],
            cargo=dict(gold=0,grain=0,reserves=0),route_mode='land'),game.revision)
        self.step(game)
        actual=game.state.extension['logistics']['convoys'][0]['journeys'][0]['supply']
        self.assertEqual(actual['route_days'],5);self.assertTrue(actual['waiting'])
        def forge(state):
            journey=state['extension']['logistics']['convoys'][0]['journeys'][0]
            bag=journey['supply']
            for meal in bag['periods'][0]['days']:
                if meal is not None:meal[2]=1
            bag['route_days']=sum(meal[2] for period in bag['periods'] for meal in period['days'] if meal is not None)
            bag['waiting']=False
            journey['arrival_turn']=(bag['clock_tick']+journey['quote']['days']-bag['route_days']+9)//10+1
        self.reject(game,forge)

    def test_return_journey_cannot_create_a_grain_absent_from_its_closed_predecessor(self):
        game=self.returning()
        def forge(state):
            bag=self.row(state)['supply']
            bag['loaded']+=1;bag['remaining']+=1
        self.reject(game,forge)

    def test_return_journey_must_start_at_the_predecessors_actual_checkpoint(self):
        game=self.returning()
        original=game.state.extension['travel']['marches'][0]
        quote=game._travel_path(game.state,'jiangxia','xiangyang',original['owner'],'land')
        self.assertIsNotNone(quote)
        def forge(state):
            row=self.row(state);row['journey_source']='jiangxia';row['quote']=deepcopy(quote)
            self.eta(state,row)
        self.reject(game,forge)


if __name__=='__main__':unittest.main()
