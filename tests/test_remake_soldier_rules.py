"""Pinned original6502 arithmetic and independently commanded soldier squads."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake import siege
from remake.campaign import Campaign,digest
from remake.errors import GameError
from test_remake_tactical_ai import battle,actors
from test_remake_battle_siege import castle_contact


class NativeSoldierArithmeticTests(unittest.TestCase):
    def test_original_cpu_witness_seed_and_damage_boundaries(self):
        path=ROOT/'tools/siege-original/soldier-rules-reference.json'
        raw=path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'3120cfc4fedc24baf87dc52f986a23823220a55960891dcdd3a24940ee9bc0b2')
        source=json.loads(raw)
        self.assertEqual(source['runner_sha256'],hashlib.sha256((ROOT/'tools/siege-original/extract_soldier_rules.py').read_bytes()).hexdigest())
        self.assertEqual(len(source['seed_cases']),126)
        self.assertEqual(len(source['damage_cases']),2080)
        for martial,roll,expected in source['seed_cases']:
            with self.subTest(martial=martial,roll=roll):
                self.assertEqual(siege.attack_base(martial,roll),expected)
        for row in source['damage_cases']:
            with self.subTest(native=row):
                self.assertEqual(siege.soldier_damage(*row[:-1]),row[-1])

    def test_zero_people_do_not_attack_and_armor_can_stop_all_damage(self):
        for kind in siege.KINDS:
            self.assertEqual(siege.soldier_damage(78,0,kind,'infantry',20,12),0)
        self.assertEqual(siege.soldier_damage(20,100,'infantry','general',0,12),0)
        self.assertEqual(siege.soldier_damage(78,100,'infantry','cavalry'),58)
        self.assertEqual(siege.soldier_damage(78,100,'archer','infantry',ranged=False),46)
        self.assertEqual(siege.soldier_damage(78,100,'archer','infantry',ranged=True),54)
        self.assertEqual(siege.soldier_damage(78,100,'general','general',20,12),37)

    def test_general_equipment_is_not_a_bonus_for_every_soldier(self):
        for kind in ('infantry','archer','cavalry'):
            self.assertEqual(siege.soldier_damage(45,100,kind,'infantry',0,0),siege.soldier_damage(45,100,kind,'infantry',20,12))
        self.assertGreater(siege.soldier_damage(45,100,'general','infantry',20),siege.soldier_damage(45,100,'general','infantry',0))

    def test_invalid_original_formula_inputs_rejected(self):
        for martial,roll in [(0,0),(100,0),(True,0),(50,-1),(50,9),(50,True)]:
            with self.assertRaises(ValueError):siege.attack_base(martial,roll)
        for kwargs in [dict(troops=101),dict(troops=-1),dict(troops=True),dict(base=0),dict(base=79),dict(kind='ship'),dict(ranged=1)]:
            value=dict(base=45,troops=100,kind='infantry',target_kind='infantry');value.update(kwargs)
            with self.assertRaises(ValueError):siege.soldier_damage(**value)


class IndividualSoldierCommandTests(unittest.TestCase):
    def start(self,total=1000,field=False):
        game=battle(three_enemies=False);b,a,t,context=castle_contact(game)
        change=total-game.state.officers[a['id']].troops
        city=next(c for c in game.state.cities.values()if a['id']in c.roster.officer_ids)
        city.reserves-=change
        a['troops']=a['start']=total
        game.state.officers[a['id']]=replace(game.state.officers[a['id']],troops=total)
        if field:
            b['extended']['tactical']['positions'][str(a['id'])]=dict(x=0,y=0)
            b['extended']['tactical']['positions'][str(t['id'])]=dict(x=1,y=0)
        game.command('attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
        game.command('siege_form',dict(battle_id=b['id'],formation=3),game.revision)
        return game,b['id']

    def test_thousand_people_are_ten_full_squads_and_remainder_is_last(self):
        for total in (1,99,100,101,999,1000):
            game,ident=self.start(total)
            row=game.state.battle['extended']['siege'];ours=[p for p in row['units']if p['side']=='attackers'and p['kind']!='general']
            self.assertEqual([p['troops']for p in ours],[min(100,total-index*100)for index in range((total+99)//100)])
            self.assertEqual([p['id']for p in ours],['a'+str(i+1)for i in range(len(ours))])
            self.assertEqual(sum(p['troops']for p in ours),total)

    def test_individual_orders_only_move_the_selected_squad(self):
        game,ident=self.start();row=game.state.battle['extended']['siege']
        for side in siege.SIDES:
            row['orders'][side]={kind:'wait'for kind in siege.KINDS}
            row['piece_orders'][side]={p['id']:'wait'for p in row['units']if p['side']==side}
        before=deepcopy(row);rng=game.state.rng.draws
        orders=dict(row['piece_orders']['attackers']);orders['a1']='advance'
        game.command('siege_orders',dict(battle_id=ident,piece_orders=orders),game.revision)
        self.assertEqual(game.state.rng.draws,rng)
        committed=deepcopy(game.state.battle['extended']['siege'])
        result=game.command('siege_step',dict(battle_id=ident),game.revision)
        row=game.state.battle['extended']['siege'];changed=[p['id']for p,q in zip(row['units'],before['units'])if (p['x'],p['y'])!=(q['x'],q['y'])]
        self.assertEqual(changed,['a1']);self.assertEqual(game.state.rng.draws,rng)
        self.assertEqual(row['events'][0]['kind'],'move');self.assertEqual(row['events'][0]['actor'],'a1')
        scene=next(s for s in result['presentation']['scenes']if s['kind']=='soldier_step')
        self.assertEqual(scene['soldiers']['before'],committed)
        self.assertEqual(scene['soldiers']['after'],row)
        save=game.export_save();clone=Campaign(game.catalog);clone.load_save(save,clone.revision);self.assertEqual(clone.export_save(),save)
        self.assertNotIn('presentation',save)

    def test_original_contact_kernel_seeds_once_and_does_not_use_macro_damage(self):
        game,ident=self.start();row=game.state.battle['extended']['siege'];a=next(p for p in row['units']if p['id']=='a1');d=next(p for p in row['units']if p['id']=='d1')
        rng=game.state.rng.draws
        with patch.object(game,'_damage',side_effect=AssertionError('macro formula must not run')):
            siege._hit(game,game.state,row,a,d)
            self.assertEqual(game.state.rng.draws,rng+2);bases=deepcopy(row['attack_bases'])
            siege._hit(game,game.state,row,a,d)
        self.assertEqual(game.state.rng.draws,rng+2);self.assertEqual(row['attack_bases'],bases)
        self.assertTrue(all(e['kind']=='melee'and e['loss']>=0 for e in row['events']))

    def test_field_encounters_have_no_fort_or_castle_walls(self):
        game,ident=self.start(field=True);row=game.state.battle['extended']['siege']
        self.assertEqual(row['mode'],'field');self.assertIsNone(row['fort']);self.assertFalse(siege._walls(game.state.battle,row))
        saved=game.export_save();clone=Campaign(game.catalog);clone.load_save(saved,clone.revision);self.assertEqual(clone.export_save(),saved)

    def test_foreign_missing_and_unknown_piece_orders_rollback(self):
        game,ident=self.start();row=game.state.battle['extended']['siege'];valid=dict(row['piece_orders']['attackers'])
        wrong=[{**valid,'d1':'advance'},{k:v for k,v in valid.items()if k!='a0'},{**valid,'a1':'teleport'},{**valid,'a1':True}]
        for value in wrong:
            saved=game.export_save();revision=game.revision
            with self.assertRaises(GameError):game.command('siege_orders',dict(battle_id=ident,piece_orders=value),revision)
            self.assertEqual(game.export_save(),saved);self.assertEqual(game.revision,revision)

    def test_old_group_only_siege_save_remains_exact_and_can_resume(self):
        game,ident=self.start(999);row=game.state.battle['extended']['siege']
        for field in siege.OPTIONAL_FIELDS:row.pop(field,None)
        saved=game.export_save();clone=Campaign(game.catalog);clone.load_save(saved,clone.revision);self.assertEqual(clone.export_save(),saved)
        clone.command('siege_orders',dict(battle_id=ident,orders={k:'wait'for k in siege.KINDS}),clone.revision)
        clone.command('siege_step',dict(battle_id=ident),clone.revision)
        self.assertIn('siege',clone.state.battle['extended'])


if __name__=='__main__':unittest.main()
