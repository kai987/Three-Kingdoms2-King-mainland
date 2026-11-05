"""Real soldier commands can route around waiting friends and native walls."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign
from remake import siege
from campaign_fixtures import controlled_catalog, reach_battle
from test_remake_battle_siege import castle_contact


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def encounter(*,defending=False,stationary_enemy=True):
    game=Campaign(controlled_catalog())
    command(game,'new',faction='shu',seed=2026)
    command(game,'allocate',city='xiangyang',officer=146,troops=600)
    command(game,'depart',source='xiangyang',target='nanyang',officers=[146])
    reach_battle(game)
    # The controlled fixture places the actual two macro armies at the native
    # camp contact. All soldier deployment and moves below use real commands.
    battle,actor,target,_=castle_contact(game)
    if defending:
        game.state.player=battle['defender']
        tactical=battle['extended']['tactical']
        tactical['side']='defenders';tactical['passed']['attackers']=True
        actor,target=target,actor
    command(game,'attack',battle_id=battle['id'],actor=actor['id'],target=target['id'])
    command(game,'siege_form',battle_id=battle['id'],formation=0)
    current=game.state.battle['extended']['siege']
    own='defenders'if defending else'attackers'
    foe='attackers'if defending else'defenders'
    # A stationary opposing formation isolates pathfinding from battle damage.
    # These are legal existing commands, not edited geometry or extra units.
    if stationary_enemy:
        current['orders'][foe]={kind:'wait'for kind in siege.KINDS}
        current['piece_orders'][foe]={piece['id']:'wait'for piece in current['units']if piece['side']==foe}
    game.validate(game.state)
    return game,own


def cycle(game,own,chosen,action):
    battle=game.state.battle
    row=battle['extended']['siege']
    orders={piece['id']:(action if piece['id']==chosen else'wait')
            for piece in row['units']if piece['side']==own}
    command(game,'siege_orders',battle_id=battle['id'],piece_orders=orders)
    return command(game,'siege_step',battle_id=battle['id'])


class SoldierPathfindingTests(unittest.TestCase):
    def assert_legal_events(self,battle,row):
        walls=siege._walls(battle,row)
        for event in row['events']:
            if event['kind']not in('move','retreat','surround'):continue
            start,end=event['from'],event['to']
            self.assertLessEqual(abs(start['x']-end['x'])+abs(start['y']-end['y']),1)
            self.assertTrue(0<=end['x']<16 and 0<=end['y']<10)
            self.assertNotIn((end['x'],end['y']),walls)

    def test_long_snake_general_routes_around_a_waiting_friendly_squad(self):
        game,own=encounter(stationary_enemy=False)
        before=deepcopy(game.state)
        row=game.state.battle['extended']['siege']
        self.assertEqual([(p['id'],p['x'],p['y'])for p in row['units']if p['id']in('a0','a5')],
                         [('a0',1,5),('a5',3,5)])
        trail=[]
        for _ in range(2):
            cycle(game,own,'a0','advance')
            row=game.state.battle['extended']['siege']
            general=next(p for p in row['units']if p['id']=='a0')
            trail.append((general['x'],general['y']))
            self.assert_legal_events(game.state.battle,row)
            self.assertEqual((next(p for p in row['units']if p['id']=='a5')['x'],
                              next(p for p in row['units']if p['id']=='a5')['y']),(3,5))
            game.validate(game.state)
        self.assertNotEqual(trail[-1],(2,5),'The old two-axis steering stays blocked here forever')
        self.assertGreater(len(set(trail)),1)
        self.assertEqual(game.state.rng,before.rng,'Movement itself never draws attack randomness')
        self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(game.state.battle['extended']['supply'],before.battle['extended']['supply'])

    def test_native_castle_archer_retreats_around_the_wall_and_reaches_its_edge(self):
        game,own=encounter(defending=True)
        row=game.state.battle['extended']['siege']
        archer=next(p for p in row['units']if p['id']=='d5')
        self.assertEqual((archer['kind'],archer['x'],archer['y']),('archer',9,2))
        self.assertIn((11,2),siege._walls(game.state.battle,row))
        before=deepcopy(game.state);trail=[]
        for _ in range(16):
            cycle(game,own,'d5','retreat')
            row=game.state.battle['extended']['siege']
            archer=next(p for p in row['units']if p['id']=='d5')
            trail.append((archer['x'],archer['y']))
            self.assert_legal_events(game.state.battle,row)
            game.validate(game.state)
            if archer['withdrawn']:break
        self.assertTrue(archer['withdrawn'],'A reachable native exit must not hit the200-round fallback')
        self.assertEqual(archer['x'],15)
        self.assertTrue(any(y!=2 for _,y in trail),'Retreat must leave its old row to bypass the native wall')
        self.assertEqual(archer['troops'],80)
        self.assertEqual(game.state.rng,before.rng)

    def test_blocked_commander_path_can_first_move_away_without_crossing_any_unit(self):
        game,_=encounter();battle=game.state.battle;row=deepcopy(battle['extended']['siege'])
        piece=dict(id='a1',side='attackers',kind='infantry',x=5,y=3,troops=100,health=100,withdrawn=False)
        friend=dict(piece,id='a2',x=5,y=4)
        enemy=dict(piece,id='d0',side='defenders',kind='general',x=8,y=4,troops=0,health=80)
        row['units']=[piece,friend,enemy]
        self.assertIn((6,3),siege._walls(battle,row))
        self.assertTrue(siege._move_toward(battle,row,piece,(8,4)))
        self.assertEqual((piece['x'],piece['y']),(4,3),'Both closer axes are blocked; the valid path begins away')
        for _ in range(20):
            if siege._distance(piece,enemy)==1:break
            self.assertTrue(siege._move_toward(battle,row,piece,(8,4)))
            self.assertNotIn((piece['x'],piece['y']),siege._walls(battle,row)|{(5,4),(8,4)})
        self.assertEqual(siege._distance(piece,enemy),1)
        before=deepcopy(piece)
        self.assertFalse(siege._move_toward(battle,row,piece,(8,4)))
        self.assertEqual(piece,before,'Surrounding contact holds its cell and never enters the enemy')

    def test_field_has_no_native_walls_and_blocked_retreat_can_choose_another_exit(self):
        game,_=encounter();battle=game.state.battle;row=deepcopy(battle['extended']['siege'])
        piece=dict(id='d1',side='defenders',kind='archer',x=10,y=2,troops=100,health=100,withdrawn=False)
        blocker=dict(piece,id='a1',side='attackers',x=15,y=2)
        row['units']=[piece,blocker];row['mode']='field';row['fort']=None
        self.assertEqual(siege._walls(battle,row),frozenset())
        self.assertTrue(siege._move_toward(battle,row,piece,(15,2),retreat=True))
        self.assertEqual((piece['x'],piece['y']),(11,2),'The same native wall coordinate is open in field mode')
        for _ in range(10):
            if piece['x']==15:break
            self.assertTrue(siege._move_toward(battle,row,piece,(15,piece['y']),retreat=True))
            self.assertNotEqual((piece['x'],piece['y']),(15,2))
        self.assertEqual(piece['x'],15)

    def test_fully_surrounded_piece_does_not_move_or_cross_living_blockers(self):
        game,_=encounter();battle=game.state.battle;row=deepcopy(battle['extended']['siege'])
        piece=dict(id='a0',side='attackers',kind='general',x=2,y=5,troops=0,health=80,withdrawn=False)
        row['units']=[piece]+[dict(piece,id='a'+str(i+1),x=x,y=y)
                              for i,(x,y)in enumerate(((2,4),(1,5),(3,5),(2,6)))]
        before=deepcopy(row);rng=deepcopy(game.state.rng)
        self.assertFalse(siege._move_toward(battle,row,piece,(14,5)))
        self.assertEqual(row,before)
        self.assertEqual(game.state.rng,rng)

    def test_both_armies_block_steps_until_a_squad_dies_or_withdraws(self):
        game,_=encounter();battle=game.state.battle;row=deepcopy(battle['extended']['siege'])
        piece=dict(id='a1',side='attackers',kind='infantry',x=1,y=1,troops=100,health=100,withdrawn=False)
        friend=dict(piece,id='a2',x=2,y=1)
        enemy=dict(piece,id='d1',side='defenders',x=3,y=1)
        row.update(units=[piece,friend,enemy],mode='field',fort=None)
        self.assertTrue(siege._move_toward(battle,row,piece,(4,1)))
        self.assertEqual((piece['x'],piece['y']),(1,0))
        for _ in range(10):
            if (piece['x'],piece['y'])==(4,1):break
            self.assertTrue(siege._move_toward(battle,row,piece,(4,1)))
            self.assertNotIn((piece['x'],piece['y']),{(2,1),(3,1)})
        self.assertEqual((piece['x'],piece['y']),(4,1))
        piece.update(x=1,y=1);friend['withdrawn']=True;enemy.update(troops=0,health=0)
        self.assertTrue(siege._move_toward(battle,row,piece,(4,1)))
        self.assertEqual((piece['x'],piece['y']),(2,1),'New occupancy is read instead of retaining a stale detour')

    def test_reversed_castle_uses_mirrored_walls_when_retreating(self):
        game,_=encounter();battle=game.state.battle;row=deepcopy(battle['extended']['siege'])
        piece=dict(id='a1',side='attackers',kind='infantry',x=6,y=2,troops=100,health=100,withdrawn=False)
        row.update(units=[piece],fort=battle['attackers'][0]['id'])
        walls=siege._walls(battle,row)
        self.assertIn((4,2),walls);self.assertNotIn((11,2),walls)
        trail=[]
        for _ in range(20):
            if piece['x']==0:break
            self.assertTrue(siege._move_toward(battle,row,piece,(0,piece['y']),retreat=True))
            trail.append((piece['x'],piece['y']))
            self.assertNotIn(trail[-1],walls)
        self.assertEqual(piece['x'],0)
        self.assertTrue(any(y!=2 for _,y in trail))

    def test_saved_detour_resumes_identically_without_adding_rng_draws(self):
        game,own=encounter()
        for _ in range(2):cycle(game,own,'a0','advance')
        saved=game.export_save();clone=Campaign(game.catalog);clone.load_save(deepcopy(saved),0)
        self.assertEqual(clone.export_save(),saved)
        rng=deepcopy(game.state.rng)
        for _ in range(3):
            cycle(game,own,'a0','advance');cycle(clone,own,'a0','advance')
            self.assertEqual(game.export_save(),clone.export_save())
            self.assertEqual(game.state.rng,rng)

    def test_ai_and_player_advance_and_surround_share_the_same_one_step_kernel(self):
        for action in('advance','surround'):
            with self.subTest(action=action):
                game,own=encounter();ai_state=deepcopy(game.state);ai_state.player='wu'
                ai_row=ai_state.battle['extended']['siege']
                ai_row['piece_orders'][own]={p['id']:(action if p['id']=='a0'else'wait')
                                             for p in ai_row['units']if p['side']==own}
                ai_row['stage']='combat'
                # The AI's auto driver calls this same kernel; only policy
                # selection and player input differ, never path resolution.
                siege._step_turn(game,ai_state,ai_row)
                cycle(game,own,'a0',action)
                actual=game.state.battle['extended']['siege']
                self.assertEqual(actual['units'],ai_row['units'])
                self.assertEqual(actual['events'],ai_row['events'])
                self.assertEqual(game.state.rng,ai_state.rng)


if __name__=='__main__':unittest.main()
