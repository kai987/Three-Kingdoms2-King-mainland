"""Original castle deployments and real persistent, saveable soldier encounters."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import battle_grid, presentation
from remake.campaign import Campaign
from remake.errors import GameError
from test_remake_tactical_ai import battle, actors


def castle_contact(game, *, fort_side='defenders'):
    b, actor, target, _, _ = actors(game)
    field = battle_grid._field(b)
    x, y = field['camp']
    assert field['classes'][y][x] == 5
    neighbor = next((nx, ny) for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                    if 0 <= nx < battle_grid.COLUMNS and 0 <= ny < battle_grid.ROWS)
    fort, outside = (target, actor) if fort_side == 'defenders' else (actor, target)
    positions = b['extended']['tactical']['positions']
    positions[str(fort['id'])] = dict(x=x, y=y)
    positions[str(outside['id'])] = dict(x=neighbor[0], y=neighbor[1])
    return b, actor, target, dict(fort=fort['id'], map_id=b['extended']['tactical']['map_id'], cell=dict(x=x,y=y))


class SiegePresentationTests(unittest.TestCase):
    def test_declarative_runtime_tables_match_pinned_original_asset_evidence(self):
        from remake import siege
        tables=json.loads((ROOT/'game/assets/siege-original/index.json').read_text())['tables']
        self.assertEqual(siege.FORMATIONS,tuple((tuple(r['x']),tuple(r['y']))for r in tables['formations']))
        raw=tables['ratios_B7AC']
        expected=tuple(tuple(tuple(raw[level*8+band*2:level*8+band*2+2])for band in range(3))for level in range(8))
        self.assertEqual(siege.THRESHOLDS,expected)
        castle=tables['castle_layout'];walls={(i%16,i//16)for i,tile in enumerate(castle['raw'])if castle['terrain_class_lut'][tile]!=0}
        self.assertEqual(siege.WALLS,walls)

    def test_all_thirty_native_castles_use_actual_cell_and_target_identity(self):
        game = battle(three_enemies=False)
        b, actor, target, _, _ = actors(game)
        saved = deepcopy(b)
        for map_id, field in battle_grid._library()[0].items():
            with self.subTest(map_id=map_id):
                b['extended']['tactical']['map_id'] = map_id
                x, y = field['camp']
                self.assertEqual(field['classes'][y][x], 5)
                b['extended']['tactical']['positions'][str(target['id'])] = dict(x=x,y=y)
                outside = next((nx,ny) for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                               if 0 <= nx < 31 and 0 <= ny < 19 and field['classes'][ny][nx] != 5)
                b['extended']['tactical']['positions'][str(actor['id'])] = dict(x=outside[0],y=outside[1])
                before = deepcopy(b)
                context = battle_grid.siege_context(b,actor,target)
                self.assertEqual(context,dict(fort=target['id'],map_id=map_id,cell=dict(x=x,y=y)))
                self.assertEqual(b,before)
                context['cell']['x'] = -1
                self.assertEqual(b,before)
        b.clear(); b.update(saved)

    def start(self, *, fort_side='defenders'):
        game=battle(three_enemies=False)
        b,actor,target,context=castle_contact(game,fort_side=fort_side)
        game.command('attack',dict(battle_id=b['id'],actor=actor['id'],target=target['id']),game.revision)
        return game,b['id'],actor['id'],target['id'],context

    def cycle(self,game,ident,order='advance'):
        from remake import siege
        game.command('siege_orders',dict(battle_id=ident,orders={k:order for k in siege.KINDS}),game.revision)
        return game.command('siege_step',dict(battle_id=ident),game.revision)

    def test_castle_attack_enters_persistent_formation_before_any_damage_or_rng(self):
        game=battle(three_enemies=False)
        b,a,t,context=castle_contact(game)
        before=deepcopy(game.state);books=deepcopy(before.extension['command_books'])
        result=game.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
        row=game.state.battle['extended']['siege']
        self.assertEqual(row['stage'],'formation');self.assertIsNone(row['formations']['attackers'])
        self.assertEqual({k:row[k]for k in ('fort','map_id','cell')},context)
        self.assertEqual(game.state.rng,before.rng)
        self.assertEqual(game.state.battle['attackers'],before.battle['attackers'])
        self.assertEqual(game.state.battle['defenders'],before.battle['defenders'])
        self.assertEqual(game.state.battle['extended']['tactical']['points']['attackers'],before.battle['extended']['tactical']['points']['attackers']-2)
        self.assertEqual(game.state.extension['command_books'],books)
        self.assertNotIn('presentation',result)
        self.assertTrue(row['units'])

    def test_four_original_formations_rearrange_real_pieces_without_rng(self):
        from remake import siege
        layouts=[]
        for formation in range(4):
            game,ident,a,t,_=self.start()
            before=game.export_save();game.command('siege_form',dict(battle_id=ident,formation=formation),game.revision)
            row=game.state.battle['extended']['siege'];self.assertEqual(row['stage'],'orders')
            self.assertEqual(game.state.rng.draws,before['state']['rng']['draws'])
            pieces=[p for p in row['units']if p['side']=='attackers']
            self.assertEqual(sum(p['troops']for p in pieces),game.state.battle['attackers'][0]['troops'])
            self.assertEqual([(p['x'],p['y'])for p in pieces],list(zip(siege.FORMATIONS[formation][0],siege.FORMATIONS[formation][1]))[:len(pieces)])
            layouts.append([(p['x'],p['y'])for p in pieces])
        self.assertEqual(len({tuple(row)for row in layouts}),4)

    def test_original_hundred_soldier_division_thresholds_and_fort_bows(self):
        from remake import siege
        for total in (1,99,100,101,599,600,999):
            game=battle(three_enemies=False);b,a,t,context=castle_contact(game)
            a['troops']=a['start']=total
            row=siege.begin(game,game.state,a,t,context)
            ours=[p for p in row['units']if p['side']=='attackers'and p['kind']!='general']
            self.assertEqual(len(ours),(total+99)//100)
            self.assertEqual(sum(p['troops']for p in ours),total)
            self.assertLessEqual(max(p['troops']for p in ours)-min(p['troops']for p in ours),1)
            self.assertTrue(all(p['kind']!='infantry'for p in row['units']if p['side']=='defenders'))

    def test_steps_move_and_exchange_real_losses_then_return_without_extra_ap(self):
        game,ident,actor,fort,_=self.start()
        game.command('siege_form',dict(battle_id=ident,formation=2),game.revision)
        original=deepcopy(game.state.battle);positions=deepcopy(original['extended']['siege']['units'])
        saw_move=saw_loss=False
        for _ in range(60):
            if 'siege'not in game.state.battle['extended']:break
            self.cycle(game,ident)
            b=game.state.battle
            saw_loss|=any(u['troops']<next(v['troops']for v in original[side]if v['id']==u['id'])for side in ('attackers','defenders')for u in b[side])
            if 'siege'in b['extended']:saw_move|=b['extended']['siege']['units']!=positions
        self.assertTrue(saw_move);self.assertTrue(saw_loss)
        self.assertNotIn('siege',game.state.battle['extended'])
        self.assertEqual(game.state.battle['extended']['tactical']['points'],original['extended']['tactical']['points'])

    def test_wait_has_no_movement_or_remote_archer_damage_and_withdraw_preserves_troops(self):
        game,ident,actor,fort,_=self.start()
        game.command('siege_form',dict(battle_id=ident,formation=0),game.revision)
        b=game.state.battle;row=b['extended']['siege']
        row['orders']['defenders']={k:'wait'for k in ('infantry','archer','cavalry','general')}
        before=game.export_save();self.cycle(game,ident,'wait')
        current=game.state.battle['extended']['siege']
        self.assertEqual(current['units'],before['state']['battle']['extended']['siege']['units'])
        self.assertEqual(game.state.rng.draws,before['state']['rng']['draws'])
        game.command('siege_withdraw',dict(battle_id=ident),game.revision)
        self.assertNotIn('siege',game.state.battle['extended'])
        self.assertEqual(game.state.battle['attackers'],before['state']['battle']['attackers'])
        self.assertEqual(game.state.battle['defenders'],before['state']['battle']['defenders'])

    def test_save_load_each_stage_roundtrips_exact_state_and_rng(self):
        game,ident,_,_,_=self.start()
        for operation,payload in [(None,None),('siege_form',{'formation':1}),('siege_orders',{'orders':{k:'advance'for k in ('infantry','archer','cavalry','general')}}),('siege_step',{})]:
            if operation:game.command(operation,dict(battle_id=ident,**payload),game.revision)
            saved=game.export_save();reference=Campaign(game.catalog);reference.load_save(deepcopy(saved),reference.revision)
            self.assertEqual(reference.export_save(),saved)
        # Reload does not redeploy or refill the tactical AP.
        self.assertEqual(reference.state.battle['extended']['siege']['round'],2)

    def test_invalid_commands_and_cross_tactical_actions_rollback_everything(self):
        game,ident,a,t,_=self.start()
        for kind,payload in [('siege_form',{'formation':True}),('siege_form',{'formation':4}),('siege_step',{}),('siege_orders',{'orders':{}}),('battle_wait',{}),('attack',{'actor':a,'target':t}),('retreat',{})]:
            before=game.export_save();revision=game.revision
            with self.subTest(kind=kind,payload=payload),self.assertRaises(GameError):
                game.command(kind,dict(battle_id=ident,**payload),revision)
            self.assertEqual(game.export_save(),before);self.assertEqual(game.revision,revision)

    def test_corrupt_siege_save_cannot_forge_units_occupancy_or_formations(self):
        from remake.campaign import digest
        game,ident,a,t,_=self.start()
        good=game.export_save()
        for change in [lambda s:s.update(siege=None),lambda s:s['siege'].update(actor=True),lambda s:s['siege'].update(round=201),lambda s:s['siege']['units'][0].update(x=16),lambda s:s['siege']['units'][1].update(troops=101),lambda s:s['siege']['units'][1].update(id='z1'),lambda s:s['siege']['formations'].update(defenders=None)]:
            bad=deepcopy(good);change(bad['state']['battle']['extended']);bad['checksum']=digest({k:v for k,v in bad.items()if k!='checksum'})
            with self.assertRaises(GameError):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),good)

    def test_original_wall_collision_and_arrow_ray_do_not_share_blocking_rule(self):
        from remake import siege
        game,ident,_,_,_=self.start();row=game.state.battle['extended']['siege']
        friendly=dict(id='a1',side='attackers',kind='archer',x=5,y=3,troops=100,health=100,withdrawn=False)
        foe=dict(id='d1',side='defenders',kind='archer',x=8,y=3,troops=100,health=100,withdrawn=False)
        row['units']=[friendly,foe]
        self.assertFalse(siege._move_toward(game.state.battle,row,friendly,(8,3)))
        self.assertIs(siege._ray_target(row,friendly,[foe]),foe)

    def test_advance_and_surround_head_for_commander_through_the_central_passage(self):
        for action in ('advance','surround'):
            with self.subTest(action=action):
                game,ident,_,_,_=self.start()
                game.command('siege_form',dict(battle_id=ident,formation=0),game.revision)
                row=game.state.battle['extended']['siege']
                infantry=next(p for p in row['units']if p['id']=='a1')
                infantry.update(x=5,y=2)
                row['orders']['defenders']={k:'wait'for k in ('infantry','archer','cavalry','general')}
                # A closer archer stands at7,2 behind the wall6,2. The real
                # commander at14,5 instead leads through the central opening.
                nearby=next(p for p in row['units']if p['side']=='defenders'and p['x']==7 and p['y']==2)
                self.assertEqual(nearby['kind'],'archer')
                points=[]
                for _ in range(3):
                    orders={k:'wait'for k in ('infantry','archer','cavalry','general')};orders['infantry']=action
                    game.command('siege_orders',dict(battle_id=ident,orders=orders),game.revision)
                    game.command('siege_step',dict(battle_id=ident),game.revision)
                    infantry=next(p for p in game.state.battle['extended']['siege']['units']if p['id']=='a1')
                    points.append((infantry['x'],infantry['y']))
                self.assertEqual(points,[(5,3),(5,4),(6,4)])

    def test_general_retreat_and_finite_wait_bound_finish_without_restarting(self):
        from remake import siege
        game,ident,_,_,_=self.start();game.command('siege_form',dict(battle_id=ident,formation=0),game.revision)
        self.cycle(game,ident,'retreat');self.assertNotIn('siege',game.state.battle['extended'])
        game,ident,_,_,_=self.start();game.command('siege_form',dict(battle_id=ident,formation=0),game.revision)
        row=game.state.battle['extended']['siege'];row['round']=siege.MAX_ROUNDS
        self.cycle(game,ident,'wait');self.assertNotIn('siege',game.state.battle['extended'])

    def test_fort_occupant_and_ai_initiator_use_same_pending_service(self):
        from remake import siege
        for fort_side in ('attackers','defenders'):
            game=battle(three_enemies=False);b,a,t,expected=castle_contact(game,fort_side=fort_side)
            game.state.player='wei' # Explicit controlled player-defender input.
            game._execute_attack(game.state,a,t,'attackers','defenders',finish=False)
            row=game.state.battle['extended']['siege'];self.assertIsNone(row['formations']['defenders'])
            game.command('siege_form',dict(battle_id=b['id'],formation=3),game.revision)
            self.cycle(game,b['id'])
            self.assertTrue('siege'in game.state.battle['extended'])

    def test_plain_contact_and_legacy_kernel_do_not_gain_siege_state(self):
        for tactical in (True,False):
            game=battle(three_enemies=False,tactical=tactical);b,a,t,_,_=actors(game)
            self.assertIsNone(battle_grid.siege_context(b,a,t))
            if tactical:result=game.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
            else:game._execute_attack(game.state,a,t,'attackers','defenders',finish=False)
            self.assertNotIn('siege',game.state.battle['extended'])

    def test_general_contact_enters_existing_duel_and_resumes_without_extra_ap(self):
        game,ident,_,_,_=self.start();game.command('siege_form',dict(battle_id=ident,formation=0),game.revision)
        row=game.state.battle['extended']['siege']
        generals=[p for p in row['units']if p['kind']=='general']
        generals[0].update(x=4,y=5);generals[1].update(x=5,y=5)
        before=deepcopy(game.state.battle['extended']['tactical']['points'])
        orders={k:'wait'for k in ('infantry','archer','cavalry','general')};orders['general']='advance'
        game.command('siege_orders',dict(battle_id=ident,orders=orders),game.revision)
        game.command('siege_step',dict(battle_id=ident),game.revision)
        self.assertIsNotNone(game.state.battle['extended']['duel'])
        game.command('duel_action',dict(battle_id=ident,move='strike'),game.revision)
        saved=game.export_save();clone=Campaign(game.catalog);clone.load_save(deepcopy(saved),0);self.assertEqual(clone.export_save(),saved)
        if game.state.battle['extended']['duel']:
            game.command('duel_action',dict(battle_id=ident,move='withdraw'),game.revision)
        self.assertIsNone(game.state.battle['extended']['duel'])
        self.assertEqual(game.state.battle['extended']['siege']['stage'],'orders')
        self.assertEqual(game.state.battle['extended']['tactical']['points'],before)

    def test_full_battle_log_stays_bounded_at_entry_formation_and_duel_return(self):
        game=battle(three_enemies=False);b,a,t,_=castle_contact(game)
        b['log']=['既有戰報。']*80
        game.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
        self.assertEqual(len(game.state.battle['log']),80)
        game.command('siege_form',dict(battle_id=b['id'],formation=0),game.revision)
        self.assertEqual(len(game.state.battle['log']),80)
        generals=[p for p in game.state.battle['extended']['siege']['units']if p['kind']=='general']
        generals[0].update(x=4,y=5);generals[1].update(x=5,y=5)
        orders={k:'wait'for k in ('infantry','archer','cavalry','general')};orders['general']='advance'
        game.command('siege_orders',dict(battle_id=b['id'],orders=orders),game.revision)
        game.command('siege_step',dict(battle_id=b['id']),game.revision)
        self.assertEqual(len(game.state.battle['log']),80)
        game.command('duel_action',dict(battle_id=b['id'],move='withdraw'),game.revision)
        self.assertEqual(len(game.state.battle['log']),80)
        game.validate(game.state)

    def test_ai_only_auto_reuses_the_same_deployment_and_per_piece_damage(self):
        from remake import siege
        human=battle(three_enemies=False);b,a,t,context=castle_contact(human)
        machine=Campaign(human.catalog);machine.load_save(deepcopy(human.export_save()),0);machine.state.player='wu'
        human.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),human.revision)
        human.command('siege_form',dict(battle_id=b['id'],formation=3),human.revision)
        for _ in range(siege.MAX_ROUNDS):
            if 'siege'not in human.state.battle['extended']:break
            self.cycle(human,b['id'])
        mb=machine.state.battle
        machine._execute_attack(machine.state,mb['attackers'][0],mb['defenders'][0],'attackers','defenders',finish=False)
        self.assertNotIn('siege',machine.state.battle['extended'])
        self.assertEqual(machine.state.battle['attackers'],human.state.battle['attackers'])
        self.assertEqual(machine.state.battle['defenders'],human.state.battle['defenders'])
        self.assertEqual(machine.state.rng,human.state.rng)

    def test_stunned_castle_attack_retains_the_existing_skip_without_damage(self):
        game=battle(three_enemies=False);b,a,t,_=castle_contact(game)
        b['extended']['support'][str(a['id'])]['stunned']=1
        before=game.export_save();result=game.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
        self.assertNotIn('siege',game.state.battle['extended']);self.assertEqual(game.state.rng.draws,before['state']['rng']['draws'])
        self.assertTrue(result['presentation']['scenes'][0]['skipped'])


if __name__=='__main__':unittest.main()
