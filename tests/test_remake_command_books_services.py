"""Shared faction orders across real service transactions and automatic jobs."""
from copy import deepcopy
from pathlib import Path
import sys
import json
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import command_books,domestic,equipment,facilities
from remake.campaign import Campaign,Catalog
from remake.errors import GameError
from test_remake_facility_campaign import facility_catalog
from test_remake_civil_staff_campaign import staff_catalog


class SharedOrderServiceTests(unittest.TestCase):
    def game(self, *, one_city=False):
        catalog=facility_catalog()
        if one_city:
            data=deepcopy(catalog.data)
            data['initial_owners']['nanjun']='neutral'
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'orders.json'
                path.write_text(json.dumps(data,ensure_ascii=False))
                catalog=Catalog(path)
        game=Campaign(catalog)
        game.command('new',dict(faction='shu',seed=2026),0)
        return game

    def cmd(self,game,action,**payload):
        return game.command(action,payload,game.revision)

    def actor(self,game,city='xiangyang',exclude=()):
        return next(i for i in game.state.cities[city].roster.officer_ids
            if i not in exclude and game.state.officers[i].health>0)

    def rejects(self,game,action,**payload):
        before,revision=game.export_save(),game.revision
        with self.assertRaises((GameError,ValueError)):
            self.cmd(game,action,**payload)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)

    def test_same_city_and_same_actor_can_use_whole_faction_pool(self):
        game=self.game();actor=self.actor(game)
        for expected in (2,1,0):
            self.cmd(game,'trade_grain',city='xiangyang',actor=actor,direction='buy',batches=1)
            self.assertEqual(command_books.remaining(game.state,'shu'),expected)
            self.assertTrue(game.state.cities['xiangyang'].action_used)
            self.assertEqual(game.state.extension['officer_actions'][str(actor)],game.state.turn)
        self.rejects(game,'trade_grain',city='xiangyang',actor=actor,direction='buy',batches=1)
        orders=game.state.extension['command_books']['factions']['shu']['orders']
        self.assertEqual([row['city'] for row in orders],['xiangyang']*3)
        self.assertEqual([row['kind'] for row in orders],['trade_grain']*3)
        self.assertEqual(command_books.remaining(game.state,'wei'),3)

    def test_facility_convoy_and_transfer_share_one_pool_and_charge_once_each(self):
        game=self.game();source='xiangyang';actor=self.actor(game)
        self.cmd(game,'trade_grain',city=source,actor=actor,direction='buy',batches=1)
        self.cmd(game,'dispatch_transport',source=source,target='nanjun',officers=[actor],
            cargo=dict(gold=20,grain=30,reserves=0),route_mode='land')
        self.assertEqual(command_books.remaining(game.state,'shu'),1)
        self.rejects(game,'trade_grain',city=source,actor=actor,direction='buy',batches=1)
        other=self.actor(game,exclude=[actor])
        self.rejects(game,'dispatch_transport',source=source,target='nanjun',officers=[other],
            cargo=dict(gold=20,grain=30,reserves=0),route_mode='land')
        self.cmd(game,'transfer',source=source,target='nanjun',officers=[other],route_mode='land')
        self.assertEqual(command_books.remaining(game.state,'shu'),0)
        self.assertEqual(len(game.state.extension['logistics']['convoys']),1)
        self.assertEqual(len(game.state.extension['travel']['marches']),1)
        self.assertEqual(game.state.extension['command_books']['factions']['shu']['used'],3)
        game.validate(game.state)

    def test_search_failure_or_success_and_reward_use_same_actor_and_pool(self):
        game=self.game();actor=self.actor(game)
        self.cmd(game,'set_governor',city='xiangyang',officer=actor)
        self.assertEqual(command_books.remaining(game.state,'shu'),3)
        self.cmd(game,'trade_grain',city='xiangyang',actor=actor,direction='buy',batches=1)
        draws=game.state.rng.draws
        self.cmd(game,'search_treasure',city='xiangyang',actor=actor)
        self.assertEqual(game.state.rng.draws,draws+1)
        target=next(i for i in game.state.cities['xiangyang'].roster.officer_ids
            if i not in game.state.extension['leaders'].values() and game.state.officers[i].loyalty<100)
        self.cmd(game,'reward_officer',city='xiangyang',officer=target,kind='gold',amount=1)
        self.assertEqual(command_books.remaining(game.state,'shu'),0)
        game.validate(game.state)

    def test_automatic_recruitment_can_spend_all_books_in_one_city_once(self):
        game=self.game(one_city=True);ids=game.state.cities['xiangyang'].roster.officer_ids
        civil=ids[0];military=next(i for i in ids if i!=civil)
        self.cmd(game,'set_domestic',faction='shu',civil=civil,military=military,
            policy=dict(recruit_enabled=True,reserve_target=10000,recruit_budget=100,
                gold_floor=0,grain_floor=0,task_order=['recruit','personnel','transport']))
        self.cmd(game,'end_turn')
        orders=game.state.extension['command_books']['factions']['shu']['orders']
        self.assertEqual([r['kind'] for r in orders],['recruit']*3)
        self.assertEqual([r['city'] for r in orders],['xiangyang']*3)
        before=deepcopy(game.to_dict())
        domestic.run_automatic(game,game.state,'shu')
        self.assertEqual(game.to_dict(),before)
        game.validate(game.state)

    def test_actual_ai_hire_then_armory_purchase_keeps_new_clerks_equipment(self):
        # Controlled facilities/policies, unchanged real personnel and funds.
        # One public AI command performs both operations before its final sync.
        data=deepcopy(staff_catalog(free=False).data)
        data['city_profiles']['nanjun']['tier']='large'
        data.get('city_scale_rules',{}).get('cities',{}).pop('nanjun',None)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'same-turn-hiring.json'
            path.write_text(json.dumps(data,ensure_ascii=False))
            game=Campaign(Catalog(path))
        self.cmd(game,'new',faction='wu',seed=2026)
        self.assertEqual(game.state.extension['facilities']['cities']['nanjun']['town'],2)
        game.state.extension['facilities']['factions']['shu'].update(enabled=True,
            gold_budget=500,gold_floor=0,auto_prevent=False,auto_treat=False,
            auto_trade=False,auto_equip=True,auto_develop=False,auto_study=False)
        game.state.extension['treasury']['factions']['shu']['enabled']=False
        domestic.appointments(game.state,'shu')['policy']['reserve_target']=0
        self.cmd(game,'end_turn')
        self.cmd(game,'ai',turn=game.state.turn)
        self.assertEqual(game.state.turn,2)
        person=next(p for p in game.state.extension['civil_staff']['people'].values()
            if p['city']=='nanjun' and p['owner']=='shu')
        ident=person['id'];officer=game.state.officers[ident]
        buys=[e for e in game.state.extension['events']['items']
            if e['kind']=='equipment_bought' and e['turn']==1
            and e['city_ids']==['nanjun'] and e['details']['target']==ident]
        self.assertTrue(buys,'New clerk must actually buy gear in the hiring turn')
        for slot,receipt in {e['details']['slot']:e['details'] for e in buys}.items():
            self.assertEqual(getattr(officer,slot+'_id'),receipt['item'])
            self.assertIn(receipt['previous'],game.state.extension['equipment']['reserves'][ident][slot])
            self.assertNotIn(receipt['item'],game.state.extension['equipment']['reserves'][ident][slot])
        self.assertIn(ident,game.state.extension['equipment']['initialized'])
        self.assertEqual(game.state.extension['treasury']['cities']['nanjun']['governor'],ident)
        self.assertTrue(any(r['action']=='hire_staff' and r['city']=='nanjun'
            for r in game.state.extension['ai_reports']))
        saved=game.export_save()
        for _ in range(3):equipment.synchronize(game,game.state)
        self.assertEqual(game.export_save(),saved,'Later synchronization cannot reissue initial gear')
        clone=Campaign(game.catalog);clone.load_save(saved,0)
        self.assertEqual(clone.export_save(),saved)
        game.validate(game.state)

    def test_ai_automatic_facilities_repeat_legally_but_receipt_is_idempotent(self):
        game=self.game();self.cmd(game,'end_turn')
        state=game.state;city=state.cities['nanyang']
        state.extension['facilities']['cities'][city.id].update(preparedness=0,damage=0)
        policy=state.extension['facilities']['factions']['wei']
        policy.update(enabled=True,gold_budget=5000,gold_floor=0,auto_prevent=True,
            target_preparedness=99,auto_treat=False,auto_trade=False,auto_equip=False,
            auto_develop=False,auto_study=False)
        results=facilities.auto_turn(game,state,'wei')
        self.assertEqual(len(results),3)
        self.assertEqual(command_books.remaining(state,'wei'),0)
        self.assertEqual({r['city'] for r in results},{'nanyang'})
        before=deepcopy(game.to_dict())
        self.assertEqual(facilities.auto_turn(game,state,'wei'),[])
        self.assertEqual(game.to_dict(),before)
        game.validate(state)


if __name__=='__main__':unittest.main()
