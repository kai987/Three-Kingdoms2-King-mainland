"""Modern phantom denies movement; AI never invents a canceled counterattack."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid as grid,tactical_ai as ai,tactic_effects
from remake.campaign import SeedRng
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from campaign_fixtures import arrange_contact
from test_remake_battle_grid import fixture,plain,position
from test_remake_fire_supply_ai import arrived,command,enemy_turn
from test_remake_tactical_ai import actors,kernel_battle


def forest_pair(game,*,own='defenders'):
    """Legal partial-turn fixture on the real city grid, not a deployment rule."""
    battle=game.state.battle;row=battle['extended']['tactical']
    foe='attackers'if own=='defenders'else'defenders'
    actor,target=battle[own][0],battle[foe][0]
    # Original13 has a plain approach beside forest. Keep the source off
    # facilities/camp and isolate the cheapest legal tactic with4 remainingAP.
    source,destination=(4,0),(6,0)
    field=grid._field(battle)
    assert field['classes'][source[1]][source[0]]==2
    assert field['classes'][destination[1]][destination[0]]==0
    position(battle,actor['id'],*source);position(battle,target['id'],*destination)
    return actor,target


def set_roll(state,chance,*,success):
    seed=next(i for i in range(1,10000)if(SeedRng(i).next()%100<chance)==success)
    state.rng=SeedRng(seed)
    expected=deepcopy(state.rng);expected.next()
    return expected


class PhantomAITests(unittest.TestCase):
    def test_public_player_pass_ai_cast_and_daily_tick_use_only_the_actual_success_draw(self):
        game,_,_=arrived(battle_grain=80);actor,target=forest_pair(game)
        state,battle=game.state,game.state.battle;row=battle['extended']['tactical']
        # A legal remainder after earlier actions; no extraAP or free command.
        row['points']['defenders']=4
        enemy_turn(game)
        choice=ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['tactic']),('tactic',2))
        self.assertGreater(choice['score'],0)
        row['side']='attackers';row['passed']['attackers']=False
        chance=tactic_effects.success_chance(state,battle,actor,target)
        expected=set_roll(state,chance,success=True)
        stocks={key:(c.gold,c.grain,c.reserves)for key,c in state.cities.items()}
        books=deepcopy(state.extension['command_books'])
        troops=[unit['troops']for side in grid.SIDES for unit in battle[side]]
        positions=deepcopy(row['positions'])
        game.validate(state)
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['round']),('battle',2))
        self.assertEqual(conditions.remaining(current,target['id']),1,
                         'Defender writes2; the immediate full-day scan consumes one')
        self.assertEqual(game.state.rng,expected)
        self.assertEqual([u['troops']for side in grid.SIDES for u in current[side]],troops)
        self.assertTrue(all(s['stunned']==0 for s in current['extended']['support'].values()))
        self.assertEqual(current['extended']['tactical']['positions'],positions)
        self.assertEqual(stocks,{key:(c.gold,c.grain,c.reserves)for key,c in game.state.cities.items()})
        self.assertEqual(game.state.extension['command_books'],books)
        game.validate(game.state)

    def test_public_locked_move_rejects_atomically_and_ai_has_no_move_candidates(self):
        game,_,_=arrived(battle_grain=80);_,target=forest_pair(game)
        state,battle=game.state,game.state.battle
        conditions.apply(battle,target['id'],'defenders')
        source,distances,_=grid._paths(state,battle,target)
        destination=next(point for point,cost in distances.items()if point!=source and cost<=4)
        before=game.export_save();revision=game.revision
        with self.assertRaises(GameError):
            command(game,'battle_move',battle_id=battle['id'],actor=target['id'],x=destination[0],y=destination[1])
        self.assertEqual((game.export_save(),game.revision),(before,revision))
        rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2,game=game)
        self.assertFalse(any(row['kind']=='move'for row in rows))
        self.assertEqual(game.export_save(),before)

    def test_public_locked_distant_ai_waits_without_rng_or_illegal_movement(self):
        game,actor,_=arrived(battle_grain=80);state,battle=game.state,game.state.battle
        # The attacker is beyond all tactic ranges; neither unit occupies a
        # facility. This forces the real AI loop to choose its legal wait.
        position(battle,actor['id'],4,0)
        position(battle,battle['attackers'][0]['id'],20,0)
        conditions.apply(battle,actor['id'],'attackers')
        before_positions=deepcopy(battle['extended']['tactical']['positions'])
        before_rng=deepcopy(state.rng)
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['round']),('battle',2))
        self.assertEqual(conditions.remaining(current,actor['id']),2)
        self.assertEqual(current['extended']['tactical']['positions'],before_positions)
        self.assertEqual(game.state.rng,before_rng)
        self.assertNotIn('siege',current['extended'])

    def test_phantom_actor_keeps_legal_attack_and_actual_soldier_contact(self):
        game,_,_=arrived(battle_grain=80);state,battle=game.state,game.state.battle
        actor,target=battle['attackers'][0],battle['defenders'][0]
        arrange_contact(game,actor=actor['id'],target=target['id'])
        before_exchange=ai.expected_contact_exchange(battle,actor,target)
        conditions.apply(battle,actor['id'],'defenders')
        self.assertEqual(ai.expected_contact_exchange(battle,actor,target),before_exchange)
        self.assertEqual(grid.attack_reason(battle,actor,target,'attackers'),'')
        self.assertTrue(grid.move_reason(battle,actor,'attackers'))
        rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
        self.assertTrue(any(row['kind']=='attack'for row in rows))
        self.assertFalse(any(row['kind']=='move'for row in rows))
        ap=battle['extended']['tactical']['points']['attackers']
        command(game,'attack',battle_id=battle['id'],actor=actor['id'],target=target['id'])
        current=game.state.battle
        self.assertEqual(current['extended']['siege']['stage'],'formation')
        self.assertEqual(conditions.remaining(current,actor['id']),2)
        self.assertEqual(current['extended']['tactical']['points']['attackers'],ap-grid.ATTACK_COST)

    def test_phantom_actor_can_still_cast_using_public_tactic_command(self):
        game,_,_=arrived(battle_grain=80);actor,target=forest_pair(game,own='attackers')
        state,battle=game.state,game.state.battle
        conditions.apply(battle,actor['id'],'defenders')
        self.assertIn(2,ai.legal_tactics(state,battle,actor,target,'attackers','defenders','plain',TACTICS))
        ap=battle['extended']['tactical']['points']['attackers']
        chance=tactic_effects.success_chance(state,battle,actor,target)
        expected=set_roll(state,chance,success=True)
        command(game,'tactic',battle_id=battle['id'],actor=actor['id'],target=target['id'],tactic=2)
        current=game.state.battle
        self.assertEqual(conditions.remaining(current,actor['id']),2)
        self.assertEqual(conditions.remaining(current,target['id']),3)
        self.assertEqual(current['extended']['tactical']['points']['attackers'],ap-4)
        self.assertEqual(game.state.rng,expected)

    def test_phantom_actor_can_still_accept_public_adjacent_duel(self):
        game,_,_=arrived(battle_grain=80);state,battle=game.state,game.state.battle
        actor,target=battle['attackers'][0],battle['defenders'][0]
        arrange_contact(game,actor=actor['id'],target=target['id'])
        conditions.apply(battle,actor['id'],'defenders')
        expected=set_roll(state,15,success=True)
        command(game,'duel_start',battle_id=battle['id'],actor=actor['id'],target=target['id'])
        current=game.state.battle
        self.assertEqual(current['extended']['duel']['actor'],actor['id'])
        self.assertEqual(conditions.remaining(current,actor['id']),2)
        self.assertEqual(game.state.rng,expected)

    def test_ai_waits_instead_of_harmful_repeat_but_player_can_pay_for_failed_repeat(self):
        game,_,_=arrived(battle_grain=80);actor,target=forest_pair(game)
        state,battle=game.state,game.state.battle;row=battle['extended']['tactical']
        enemy_turn(game);row['points']['defenders']=4
        conditions.apply(battle,target['id'],'defenders')
        conditions.apply(battle,actor['id'],'attackers')
        self.assertIn(2,ai.legal_tactics(state,battle,actor,target,'defenders','attackers','plain',TACTICS))
        before=game.export_save()
        with patch.object(SeedRng,'next',side_effect=AssertionError('No AI pre-roll')):
            choice=ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual(choice['kind'],'wait')
        self.assertEqual(game.export_save(),before)
        # The same modern command remains legal to a defending human.8AP keeps
        # the paid failure on this half-turn so no unrelated AI action occurs.
        state.player='wei';row['points']['defenders']=8
        chance=tactic_effects.general_chance(state.officers[actor['id']],state.officers[target['id']])
        expected=set_roll(state,chance,success=False)
        books=deepcopy(state.extension['command_books'])
        troops=[u['troops']for side in grid.SIDES for u in battle[side]]
        command(game,'tactic',battle_id=battle['id'],actor=actor['id'],target=target['id'],tactic=2)
        current=game.state.battle
        self.assertEqual(current['extended']['tactical']['points']['defenders'],4)
        self.assertEqual(conditions.remaining(current,target['id']),0)
        self.assertEqual(conditions.remaining(current,actor['id']),3)
        self.assertEqual(game.state.extension['command_books'],books)
        self.assertEqual([u['troops']for side in grid.SIDES for u in current[side]],troops)
        self.assertEqual(game.state.rng,expected)

    def test_valuation_uses_directional_scans_and_remaining_days_not_fake_counter_damage(self):
        _,_,battle=fixture(1,1);field=plain()
        position(battle,1,5,5);position(battle,101,10,5)
        a,d=battle['attackers'][0],battle['defenders'][0]
        with patch.object(grid,'_field',return_value=field):
            attack_value=ai._phantom_mobility_value(battle,d,'attackers','defenders')
            defend_value=ai._phantom_mobility_value(battle,a,'defenders','attackers')
            self.assertAlmostEqual(attack_value,3*defend_value)
            self.assertGreater(defend_value,0)
            battle['round']=30
            self.assertEqual(ai._phantom_mobility_value(battle,a,'defenders','attackers'),0)
            self.assertGreater(ai._phantom_mobility_value(battle,d,'attackers','defenders'),0)
            position(battle,101,6,5)
            self.assertEqual(ai._phantom_mobility_value(battle,d,'attackers','defenders'),0,
                             'Adjacent opponents can attack normally while movement is locked')

    def test_empty_camp_entry_is_a_move_threat_even_beside_a_fighting_opponent(self):
        _,_,battle=fixture(1,1);field=plain()
        position(battle,1,27,9);position(battle,101,27,10)
        with patch.object(grid,'_field',return_value=field):
            target=battle['attackers'][0]
            self.assertGreater(ai._phantom_mobility_value(battle,target,'defenders','attackers'),0)
            position(battle,101,*field['camp'])
            self.assertEqual(ai._phantom_mobility_value(battle,target,'defenders','attackers'),0)

    def test_no_escape_cell_or_existing_phantom_has_no_new_movement_value(self):
        _,_,battle=fixture(4,1);field=plain()
        position(battle,101,5,5)
        for unit,point in zip(battle['attackers'],((4,5),(6,5),(5,4),(5,6))):
            position(battle,unit['id'],*point)
        target=battle['defenders'][0]
        with patch.object(grid,'_field',return_value=field):
            self.assertEqual(ai._phantom_mobility_value(battle,target,'attackers','defenders'),0)
            position(battle,1,1,1)
            conditions.apply(battle,target['id'],'attackers')
            self.assertEqual(ai._phantom_mobility_value(battle,target,'attackers','defenders'),0)

    def test_full_rosters_score_without_rng_mutation_or_per_target_dijkstra(self):
        game,state,battle=fixture(10,10)
        field=plain();field['classes']=[[0]*grid.COLUMNS for _ in range(grid.ROWS)]
        field['classes'][field['camp'][1]][field['camp'][0]]=5
        for side,x in(('attackers',2),('defenders',6)):
            for index,unit in enumerate(battle[side]):
                position(battle,unit['id'],x+index//5,index%5)
        before=deepcopy((battle,vars(state.rng)))
        with patch.object(grid,'_field',return_value=field), \
                patch.object(grid,'_paths',wraps=grid._paths)as paths, \
                patch.object(SeedRng,'next',side_effect=AssertionError('No phantom lookahead draw')):
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
        self.assertTrue(any(row['kind']=='tactic'and row['tactic']==2 for row in rows))
        self.assertLessEqual(paths.call_count,10,'At most the existing once-per-actor movement search')
        self.assertEqual((battle,vars(state.rng)),before)

    def test_legacy_confuse_candidate_and_old_stunned_skip_are_preserved(self):
        game=kernel_battle('plain',three_enemies=False,spell=2)
        state=game.state;b,actor,target,own,foe=actors(game)
        self.assertNotIn('tactical',b['extended'])
        row=next(row for row in ai.candidates(state,b,own,foe,'plain',TACTICS,depth=2)
                 if row['kind']=='tactic'and row['tactic']==2)
        self.assertGreater(row['score'],0)
        expected=set_roll(state,5,success=True)
        game._execute_tactic(state,actor,target,own,foe,2,finish=False)
        self.assertEqual(b['extended']['support'][str(target['id'])]['stunned'],1)
        self.assertNotIn('conditions',b['extended'])
        self.assertEqual(ai.expected_contact_exchange(b,target,actor),(0,0))
        self.assertEqual(state.rng,expected)


if __name__=='__main__':unittest.main()
