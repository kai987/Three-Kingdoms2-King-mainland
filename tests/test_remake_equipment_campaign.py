"""Real campaign transactions cover equipment, identity, AI and saved effects."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import equipment,facilities,civil_staff
from remake.campaign import Campaign,Catalog,SeedRng,canonical
from remake.errors import GameError
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog
from test_remake_facility_campaign import facility_catalog
from test_remake_tactical_ai import successful_rng


def catalog(source=None,*,production=False):
    data=deepcopy(source.data if source else Catalog(ROOT/'game/data/campaigns/217-07.json').data)
    originals=json.loads((ROOT/'game/config/references/original-equipment-v1.json').read_text())['records']
    data['equipment_initial']=equipment.build_initials(data['people'],originals,{})
    data['equipment_rules']=deepcopy(equipment.RULES)
    if not production:
        # Production identities and equipment, controlled economic/seasonal
        # isolation so these transactions do not also depend on city weather.
        data.setdefault('facility_rules',{})['disasters_enabled']=False
        data['facility_ai_default']=False
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'equipment.json';path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


class EquipmentCampaignTests(unittest.TestCase):
    def new(self,source=None,owner='shu',backend='python'):
        game=Campaign(catalog(source))
        with using_backend(backend):game.command('new',dict(faction=owner,seed=2026),0)
        return game

    def command(self,game,kind,**payload):
        return game.command(kind,payload,game.revision)

    def restore(self,game):
        save=json.loads(json.dumps(game.export_save()))
        clone=Campaign(game.catalog);clone.load_save(save,0)
        self.assertEqual(clone.export_save(),save)
        return clone

    def rejects(self,game,kind,**payload):
        before=game.export_save();revision=game.revision;journal=deepcopy(game.journal)
        with self.assertRaises((GameError,ValueError,TypeError)):
            self.command(game,kind,**payload)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)
        self.assertEqual(game.journal,journal)

    def test_real_all_29_openings_hold_correct_initials_and_preview_does_not_reissue(self):
        paths=[p for p in sorted((ROOT/'game/data/campaigns').glob('*.json')) if p.name!='index.json']
        self.assertEqual(len(paths),29)
        for path in paths:
            with self.subTest(scenario=path.name):
                game=Campaign(catalog(Catalog(path),production=True))
                side=next(iter(game.catalog.factions))
                self.command(game,'new',faction=side,seed=2026)
                for officer in game.state.officers.values():
                    initial=game.catalog.data['equipment_initial'][officer.person_id]
                    self.assertEqual((officer.weapon_id,officer.armor_id),
                        (initial['weapon_id'],initial['armor_id']))
                before=game.export_save()
                view=equipment.view(game,game.state)
                self.assertEqual(len(view['officers']),len(game.state.officers))
                self.assertTrue(all(row['scope']=='current' for row in view['officers'].values()))
                self.assertEqual(game.export_save(),before)
                game.validate(game.state)

    def test_purchase_backup_change_effects_and_json_save_use_actual_city_and_profile(self):
        game=self.new();state=game.state;city=state.cities['nanjun']
        actor=next(i for i in city.roster.officer_ids if state.officers[i].weapon_id==0)
        profile=deepcopy(state.officers[actor].profile);money=city.gold;rng=deepcopy(state.rng)
        self.command(game,'buy_equipment',city='nanjun',actor=actor,officer=actor,slot='weapon',item=2)
        self.assertEqual(game.state.cities['nanjun'].gold,money-120)
        self.assertEqual(game.state.officers[actor].weapon_id,2)
        self.assertEqual(game.state.officers[actor].profile,profile)
        self.assertEqual(game.state.rng,rng)
        game=self.restore(game)
        game._complete_turn(game.state)
        money=game.state.cities['nanjun'].gold
        self.command(game,'equip_owned',city='nanjun',actor=actor,officer=actor,slot='weapon',item=0)
        self.assertEqual(game.state.cities['nanjun'].gold,money)
        self.assertEqual(game.state.officers[actor].weapon_id,0)
        self.assertIn(2,game.state.extension['equipment']['reserves'][game.state.officers[actor].person_id]['weapon'])
        self.assertEqual(game.state.officers[actor].profile,profile)
        self.restore(game)

    def test_initial_signature_unique_cannot_be_bought_twice_and_transfer_retains_identity(self):
        game=self.new();state=game.state
        guan=game.catalog.ids['san14-candidate-0147']
        self.assertEqual(state.officers[guan].weapon_id,15)
        row=equipment.view(game,state)['officers'][str(guan)]
        self.assertIn('青龍偃月刀',row['weapon']['name_tc'])
        self.assertEqual(state.extension['equipment']['uniques']['weapon:15']['holder'],state.officers[guan].person_id)
        self.rejects(game,'buy_equipment',city='nanjun',actor=guan,officer=guan,slot='weapon',item=15)
        self.command(game,'transfer',source='nanjun',target='wuling',officers=[guan],route_mode='land')
        clone=self.restore(game)
        self.assertEqual(clone.state.officers[guan].weapon_id,15)
        self.assertEqual(clone.state.extension['equipment']['uniques'],game.state.extension['equipment']['uniques'])

    def test_same_transactions_have_identical_python_rust_saves_and_no_view_rng(self):
        saves=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=self.new(backend=backend);city=game.state.cities['nanjun']
                actor=next(i for i in city.roster.officer_ids if game.state.officers[i].weapon_id==0)
                self.command(game,'buy_equipment',city=city.id,actor=actor,officer=actor,slot='weapon',item=2)
                before=game.export_save()
                for _ in range(3):game.view()
                self.assertEqual(game.export_save(),before)
                saves.append(self.restore(game).export_save())
        self.assertEqual(saves[0],saves[1])

    def test_generated_officer_receives_role_equipment_once_without_changing_historical_ids(self):
        from test_remake_civil_staff_campaign import staff_catalog
        game=self.new(staff_catalog())
        city=next(c for c in game.state.cities.values() if c.owner==game.state.player
            and game.state.extension['civil_staff']['cities'][c.id]['candidate'])
        candidate=game.state.extension['civil_staff']['cities'][city.id]['candidate']
        ident=candidate['id']
        self.command(game,'hire_staff',city=city.id,candidate=ident)
        officer=game.state.officers[ident];initial=equipment._normal(officer.profile)
        self.assertEqual((officer.weapon_id,officer.armor_id),(initial['weapon_id'],initial['armor_id']))
        self.assertIn(ident,game.state.extension['equipment']['initialized'])
        self.assertNotIn(ident,game.catalog.by_id)
        self.assertEqual(len(game.catalog.definitions),1027)
        self.restore(game)

    def test_actual_ai_equipment_turn_uses_same_price_eligibility_and_reserve_service(self):
        game=self.new(facility_catalog(),owner='shu')
        state=game.state;city=state.cities['nanyang']
        owner=city.owner;state.phase='ai'
        policy=state.extension['facilities']['factions'][owner]
        policy.update(enabled=True,gold_budget=500,gold_floor=0,auto_prevent=False,
            auto_treat=False,auto_trade=False,auto_equip=True,auto_develop=False,auto_study=False)
        before_gold=city.gold;before_rng=deepcopy(state.rng)
        receipts=facilities.auto_turn(game,state,owner)
        bought=[row for row in receipts if row['city']==city.id]
        self.assertEqual(len(bought),1)
        receipt=bought[0];officer=next(o for o in state.officers.values() if o.person_id==receipt['target'])
        self.assertEqual(city.gold,before_gold-receipt['gold'])
        self.assertEqual(getattr(officer,receipt['slot']+'_id'),receipt['item'])
        self.assertIn(receipt['previous'],state.extension['equipment']['reserves'][officer.person_id][receipt['slot']])
        self.assertEqual(state.rng,before_rng)
        game.validate(state)

    def test_real_weighted_duel_commands_save_and_change_order_miss_damage_without_base_mutation(self):
        game=self.new(facility_catalog());state=game.state
        actor=game.catalog.ids['san14-candidate-0952']
        profile=deepcopy(state.officers[actor].profile)
        game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],[actor])
        successful_rng(state)
        battle=state.battle;target=battle['defenders'][0]['id']
        self.command(game,'duel_start',battle_id=battle['id'],actor=actor,target=target)
        self.assertIsNotNone(game.state.battle['extended']['duel'])
        game.state.rng=SeedRng(2026)
        self.command(game,'duel_action',battle_id=battle['id'],move='strike')
        duel=game.state.battle['extended']['duel']
        self.assertIsNotNone(duel)
        self.assertTrue(any('先手' in line for line in duel['log']))
        self.assertTrue(any('命中' in line for line in duel['log']))
        self.assertEqual(game.state.officers[actor].profile,profile)
        clone=self.restore(game)
        self.command(game,'duel_action',battle_id=battle['id'],move='withdraw')
        self.command(clone,'duel_action',battle_id=battle['id'],move='withdraw')
        self.assertEqual(game.export_save(),clone.export_save())

    def test_real_ruler_defeat_awards_one_unique_and_preserves_old_signature_across_backends(self):
        results=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=self.new(facility_catalog(),backend=backend);state=game.state;actor=146
                self.assertEqual(state.officers[actor].weapon_id,15)
                game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],[actor])
                successful_rng(state)
                battle=state.battle;target=battle['defenders'][0]['id']
                self.command(game,'duel_start',battle_id=battle['id'],actor=actor,target=target)
                game.state.rng=SeedRng(3)
                for _ in range(20):
                    if not game.state.battle['extended']['duel']:break
                    self.command(game,'duel_action',battle_id=battle['id'],move='strike')
                self.assertEqual(game.state.battle['extended']['duel_history'][-1]['result'],'本方单挑胜出')
                officer=game.state.officers[actor];pool=game.state.extension['equipment']
                self.assertEqual(officer.weapon_id,14)
                self.assertIn(15,pool['reserves'][officer.person_id]['weapon'])
                self.assertEqual(pool['uniques']['weapon:15']['holder'],officer.person_id)
                self.assertEqual(pool['uniques']['weapon:14']['holder'],officer.person_id)
                self.assertEqual(len(pool['loot_receipts']),1)
                events=[row for row in game.state.extension['events']['items'] if row['kind']=='equipment_acquired']
                self.assertEqual(len(events),1)
                receipt=events[0]['details']
                self.assertEqual((receipt['chance'],receipt['item'],receipt['method']),(50,14,'duel'))
                self.assertTrue(0<=receipt['roll']<50)
                game=self.restore(game)
                self.rejects(game,'duel_action',battle_id=battle['id'],move='strike')
                self.command(game,'settle',battle_id=battle['id'])
                results.append(self.restore(game).export_save())
        self.assertEqual(results[0],results[1])

    def test_forged_unique_ownership_and_unknown_gear_save_rejection_is_atomic(self):
        game=self.new();before=game.export_save()
        for change in ('duplicate','unknown','ledger','receipt'):
            save=deepcopy(before)
            if change=='duplicate':
                other=next(key for key,p in save['state']['officers'].items() if p['weapon_id']!=15)
                save['state']['officers'][other]['weapon_id']=15
            elif change=='unknown':next(iter(save['state']['officers'].values()))['weapon_id']=999
            elif change=='ledger':save['state']['extension']['equipment']['uniques']['weapon:15']['holder']='unknown-person'
            else:save['state']['extension']['equipment']['loot_receipts'].append('forged:unknown-person:weapon:5')
            from remake.campaign import digest
            save['checksum']=digest({key:value for key,value in save.items() if key!='checksum'})
            with self.assertRaises((ValueError,GameError)):game.load_save(save,game.revision)
            self.assertEqual(game.export_save(),before)


if __name__=='__main__':unittest.main()
