"""Author-adapted food-pressure AI uses actual rations, never sampled effects."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,SeedRng
from remake import battle_supply,tactical_ai,tactic_effects
from remake.campaign_expansion import TACTICS
from campaign_fixtures import controlled_catalog,reach_battle


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def arrived(*,troops=1000,battle_grain=3,all_officers=False):
    game=Campaign(controlled_catalog());command(game,'new',faction='shu',seed=2026)
    command(game,'allocate',city='xiangyang',officer=439,troops=troops)
    ids=[439,146,999,951]if all_officers else[439]
    command(game,'depart',source='xiangyang',target='nanyang',officers=ids,battle_grain=battle_grain)
    reach_battle(game)
    battle=game.state.battle;row=battle['extended']['tactical']
    actor,target=battle['defenders'][0],battle['attackers'][0]
    # Keep actual carried bags and fractional credit. This controlled contact
    # is four cells apart, so a regular attack cannot replace the fire tactic.
    row['positions'][str(actor['id'])]=dict(x=5,y=5)
    row['positions'][str(target['id'])]=dict(x=9,y=5)
    game.validate(game.state)
    return game,actor,target


def enemy_turn(game):
    row=game.state.battle['extended']['tactical']
    row['side']='defenders';row['passed']['attackers']=True;row['passed']['defenders']=False


def fire_candidate(game,actor,target,own='defenders',foe='attackers'):
    return next(row for row in tactical_ai.candidates(game.state,game.state.battle,own,foe,'plain',TACTICS,depth=2)
                if row['kind']=='tactic'and row['tactic']==5
                and row['actor']==actor['id']and row['target']==target['id'])


class FireSupplyAITests(unittest.TestCase):
    def test_real_player_pass_makes_ai_burn_three_bags_and_force_a_thousand_troop_retreat(self):
        game,actor,target=arrived();state,battle=game.state,game.state.battle
        carried=battle['extended']['supply']['sides']['attackers']
        self.assertEqual((target['troops'],carried['remaining'],carried['credit_units']),(1000,3,900))
        self.assertEqual(battle['extended']['tactical']['points']['defenders'],10)
        enemy_turn(game)
        choice=tactical_ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['tactic']),('tactic',5))
        self.assertGreater(choice['score'],0)
        # Execute the real public player-pass -> AI -> daily-rations chain,
        # retaining the native opening10AP rather than granting extra AP.
        battle['extended']['tactical']['side']='attackers'
        battle['extended']['tactical']['passed']['attackers']=False
        chance=tactic_effects.general_chance(state.officers[actor['id']],state.officers[target['id']])
        seed=next(i for i in range(1,1000)if SeedRng(i).next()%100<chance)
        state.rng=SeedRng(seed);expected=deepcopy(state.rng)
        expected.next();expected.next()
        stocks={key:(c.gold,c.grain,c.reserves)for key,c in state.cities.items()}
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['outcome'],current['extended']['withdrawn']),
                         ('result','retreat','attackers'))
        self.assertEqual(current['attackers'][0]['troops'],1000)
        self.assertEqual(game.state.rng,expected,'Only the real success and fire-percentage draws are consumed')
        row=current['extended']['supply']['sides']['attackers']
        self.assertEqual(row['journal'][0],dict(kind='fire',day=0,grain=3))
        self.assertEqual(row['journal'][1]['missing'],200)
        self.assertEqual(stocks,{key:(c.gold,c.grain,c.reserves)for key,c in game.state.cities.items()})
        game.validate(game.state)

    def test_zero_bags_and_already_hungry_army_do_not_gain_duplicate_fire_value(self):
        game,actor,target=arrived();state,battle=game.state,game.state.battle
        battle_supply.destroy(state,battle,'attackers',3)
        enemy_turn(game);before=game.export_save()
        self.assertEqual(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60),0)
        self.assertLessEqual(fire_candidate(game,actor,target)['score'],0)
        choice=tactical_ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS)
        self.assertFalse(choice['kind']=='tactic'and choice['tactic']==5)
        self.assertEqual(game.export_save(),before)

    def test_twenty_carried_ap_do_not_make_ai_start_a_fight_after_a_winning_fire(self):
        game,actor,target=arrived();state,battle=game.state,game.state.battle
        battle['extended']['tactical']['points']['defenders']=20
        original=deepcopy(battle['extended']['tactical']['positions'])
        chance=tactic_effects.general_chance(state.officers[actor['id']],state.officers[target['id']])
        state.rng=SeedRng(next(i for i in range(1,1000)if SeedRng(i).next()%100<chance))
        before=deepcopy(state.rng);expected=deepcopy(before);expected.next();expected.next()
        game.validate(state)
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['outcome'],current['extended']['withdrawn']),
                         ('result','retreat','attackers'))
        self.assertNotIn('siege',current['extended'],'The AI must close the won day instead of entering formation')
        self.assertEqual(current['extended']['tactical']['positions'],original)
        self.assertEqual(current['attackers'][0]['troops'],1000)
        self.assertEqual(game.state.rng,expected)

    def test_edible_fractional_credit_prevents_a_false_next_day_rout_bonus(self):
        for troops,credit in((120,780),(400,500)):
            with self.subTest(troops=troops,credit=credit):
                game,actor,target=arrived(troops=troops);state,battle=game.state,game.state.battle
                enemy_turn(game)
                row=battle['extended']['supply']['sides']['attackers']
                self.assertEqual((row['remaining'],row['credit_units']),(3,credit))
                units=battle_supply.daily_units(battle,'attackers')
                self.assertGreaterEqual(row['credit_units'],units)
                army=sum(tactical_ai._loss_value(unit,unit['troops'])for unit in battle['attackers'])
                expected=army*(3*1000/units)/30
                self.assertAlmostEqual(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60),expected)

    def test_food_remaining_beyond_the_whole_battle_has_no_artificial_burn_bonus(self):
        game,actor,target=arrived();state,battle=game.state,game.state.battle
        battle_supply.receive(state,battle,'attackers',10000)
        enemy_turn(game)
        before=game.export_save()
        self.assertEqual(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',99),0)
        self.assertLessEqual(fire_candidate(game,actor,target)['score'],0)
        self.assertEqual(game.export_save(),before)

    def test_remaining_battle_days_cap_food_pressure_at_round_thirty(self):
        game,actor,target=arrived(troops=120);state,battle=game.state,game.state.battle
        # Pure horizon calculation: even a successful total bag burn still
        # leaves780 credit, enough to feed this220-unit army for the last day.
        battle['round']=30
        enemy_turn(game)
        self.assertEqual(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60),0)

    def test_unplayed_enemy_turn_receives_pressure_discount_not_a_forced_win(self):
        game,_,_=arrived();state,battle=game.state,game.state.battle
        enemy_turn(game)
        passed=tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60)
        battle['extended']['tactical']['passed']['attackers']=False
        unplayed=tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60)
        army=sum(tactical_ai._loss_value(unit,unit['troops'])for unit in battle['attackers'])
        self.assertAlmostEqual(passed-unplayed,army*.65)
        self.assertGreater(unplayed,0)

    def test_both_hungry_awards_no_false_attacker_victory_but_respects_defender_hold(self):
        game,defender,attacker=arrived();state,battle=game.state,game.state.battle
        battle_supply.destroy(state,battle,'attackers',3)
        battle_supply.destroy(state,battle,'defenders',battle_supply.available(state,battle,'defenders')-1)
        self.assertEqual(tactical_ai._fire_supply_value(state,battle,'attackers','defenders',99),0)
        row=battle['extended']['tactical'];row['side']='attackers';row['passed']['defenders']=True
        self.assertLessEqual(fire_candidate(game,attacker,defender,'attackers','defenders')['score'],0)
        battle_supply.destroy(state,battle,'defenders',1)
        self.assertFalse(tactical_ai._wins_by_waiting(state,battle,'attackers','defenders'))
        enemy_turn(game)
        self.assertTrue(tactical_ai._wins_by_waiting(state,battle,'defenders','attackers'))
        # Reverse the food boundary: a hungry defender still holds if it makes
        # the already-passed attacker hungry too, by the established tie rule.
        battle_supply.receive(state,battle,'attackers',3)
        enemy_turn(game)
        self.assertGreater(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',60),0)

    def test_wait_requires_current_modern_turn_and_no_unfinished_subfight(self):
        game,_,_=arrived();state,battle=game.state,game.state.battle
        battle_supply.destroy(state,battle,'attackers',3);enemy_turn(game)
        self.assertTrue(tactical_ai._wins_by_waiting(state,battle,'defenders','attackers'))
        for change in('phase','outcome','duel','siege','other_turn','own_passed','foe_unplayed','no_grid'):
            with self.subTest(change=change):
                copy=deepcopy(state);b=copy.battle;row=b['extended']['tactical']
                if change=='phase':copy.phase='result'
                elif change=='outcome':b['outcome']='retreat'
                elif change=='duel':b['extended']['duel']={'round':1}
                elif change=='siege':b['extended']['siege']={'stage':'formation'}
                elif change=='other_turn':row['side']='attackers'
                elif change=='own_passed':row['passed']['defenders']=True
                elif change=='foe_unplayed':row['passed']['attackers']=False
                else:b['extended'].pop('tactical')
                before=deepcopy(copy)
                self.assertFalse(tactical_ai._wins_by_waiting(copy,b,'defenders','attackers'))
                self.assertEqual(copy,before)
        # Even zero bags are not hunger if the preserved fractional credit
        # exactly covers the next meal:500 units are enough for this army.
        game,_,_=arrived(troops=400);state,battle=game.state,game.state.battle
        battle_supply.destroy(state,battle,'attackers',3);enemy_turn(game)
        self.assertFalse(tactical_ai._wins_by_waiting(state,battle,'defenders','attackers'))

    def test_each_percentage_roll_is_evaluated_before_the_nonlinear_starvation_bonus(self):
        game,actor,_=arrived(battle_grain=15,all_officers=True);state,battle=game.state,game.state.battle
        enemy_turn(game)
        row=battle['extended']['supply']['sides']['attackers']
        units=battle_supply.daily_units(battle,'attackers')
        intellect=state.officers[actor['id']].profile.intellect
        losses=[min(row['remaining'],tactic_effects.fire_arrow_requested(row['remaining'],intellect,r))for r in range(5)]
        hungry=[(row['remaining']-loss)*1000+row['credit_units']<units for loss in losses]
        self.assertEqual(hungry,[False,False,False,False,True])
        army=sum(tactical_ai._loss_value(unit,unit['troops'])for unit in battle['attackers'])
        pressure=army*(sum(losses)*1000/5/units)/30
        self.assertAlmostEqual(tactical_ai._fire_supply_value(state,battle,'defenders','attackers',intellect),
                               pressure+army/5)

    def test_scoring_is_read_only_and_never_consumes_the_future_fire_rng(self):
        game,actor,target=arrived();enemy_turn(game);before=game.export_save()
        with patch.object(SeedRng,'next',side_effect=AssertionError('AI must not pre-roll a fire')):
            fire_candidate(game,actor,target)
            tactical_ai.choose_action(game.state,game.state.battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual(game.export_save(),before)


if __name__=='__main__':unittest.main()
