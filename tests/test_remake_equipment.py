"""Equipment identities, eligibility and conserved unique acquisitions."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import equipment,facilities
from remake.campaign import SeedRng
from remake.errors import GameError
from test_remake_facilities import fixture as facility_fixture


def fixture():
    game,state=facility_fixture()
    game.catalog.data['equipment_initial']={officer.person_id:dict(weapon_id=0,armor_id=0,
        basis='controlled_original_equipment') for officer in state.officers.values()}
    state.battle_counter=0;state.settled_battles=[]
    state.extension['equipment']=equipment.empty(game,state)
    equipment.synchronize(game,state)
    equipment.validate(game,state)
    return game,state


def shop_city(game,state,name):
    city=state.cities.pop('capital');city.id=name;state.cities[name]=city
    row=state.extension['facilities']['cities'].pop('capital')
    state.extension['facilities']['cities'][name]=row
    game.catalog.map_cities[name]=game.catalog.map_cities.pop('capital')
    return city


class EquipmentTests(unittest.TestCase):
    def fails(self,game,state,call,*args):
        before=deepcopy(state)
        with self.assertRaises((GameError,ValueError,KeyError,TypeError)):
            call(game,state,*args)
        self.assertEqual(state,before)

    def reset(self,state):
        state.turn+=1
        for city in state.cities.values():city.action_used=False

    def test_original_223_identity_mapping_and_signature_overrides_preserve_profiles(self):
        data=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        source=json.loads((ROOT/'game/config/references/original-equipment-v1.json').read_text())['records']
        before=deepcopy(data['people'])
        initials=equipment.build_initials(data['people'],source,{})
        self.assertEqual(len(initials),1023)
        self.assertEqual(sum('source' in row for row in initials.values()),223)
        for pid,ident in equipment.SIGNATURES.items():
            self.assertEqual(initials[pid]['weapon_id'],ident)
            self.assertEqual(initials[pid]['basis'],'explicit_requested_novel_signature_override')
        self.assertEqual(initials['san14-candidate-0521']['weapon_id'],3)
        self.assertEqual(initials['san14-candidate-0952']['source']['weapon_id'],2)
        self.assertEqual(initials['san14-candidate-0147']['source']['weapon_id'],12)
        self.assertEqual(data['people'],before)
        unbound=[row for row in initials.values() if 'source' not in row and 'signature' not in row]
        self.assertTrue(all(row['weapon_id'] in (0,2,16) and row['armor_id'] in (0,1,2) for row in unbound))

    def test_first_appearance_applies_once_and_preview_is_pure(self):
        game,state=fixture()
        person=state.officers[1]
        old_profile=person.profile
        state.cities['capital'].gold=1000
        q=equipment.purchase_quote(game,state,state.cities['capital'],person,'weapon',2)
        self.assertEqual(q['price'],120)
        equipment.claim_purchase(game,state,state.cities['capital'],person,'weapon',2)
        before=deepcopy(state)
        for _ in range(3):
            equipment.synchronize(game,state)
            visible=equipment.view(game,state)
            self.assertEqual(visible['officers']['1']['weapon']['id'],2)
            visible['items']['weapon'][0]['power']=99
        self.assertEqual(state,before)
        self.assertIs(person.profile,old_profile)
        # A later generated or historical person receives the current catalog
        # initial only once; no claim replay on transfer or repeat synchronize.
        new=replace(person,runtime_id=20,person_id='late-person',weapon_id=0,armor_id=0)
        state.officers[20]=new;state.cities['capital'].roster.officer_ids.append(20)
        game.catalog.data['equipment_initial']['late-person']=dict(weapon_id=16,armor_id=2,basis='controlled')
        equipment.synchronize(game,state)
        self.assertEqual((new.weapon_id,new.armor_id),(16,2))
        new.weapon_id=1
        equipment.synchronize(game,state)
        self.assertEqual(new.weapon_id,1)
        equipment.validate(game,state)

    def test_unique_purchase_real_city_person_and_ability_conditions(self):
        for slot,ident,where,target_pid,martial,virtue,price in (
            ('weapon',15,'danyang','san14-candidate-0147',70,75,400),
            ('weapon',23,'fuling','san14-candidate-0656',70,75,400),
            ('weapon',22,'wuwei','person-2',90,75,350),
            ('armor',6,'yongchang','person-2',70,90,350)):
            with self.subTest(slot=slot,item=ident):
                game,state=fixture();target=state.officers[2]
                # Rename before synchronize so the identity ledger is exact.
                old_pid=target.person_id;target.person_id=target_pid
                game.catalog.data['equipment_initial'][target_pid]=dict(weapon_id=0,armor_id=0,basis='controlled')
                state.extension['equipment']['initialized'].remove(old_pid)
                equipment.synchronize(game,state)
                target.profile=replace(target.profile,martial_strength=martial,virtue=virtue)
                city=shop_city(game,state,where)
                before=deepcopy(state)
                q=equipment.purchase_quote(game,state,city,target,slot,ident)
                self.assertEqual(q['price'],price)
                self.assertEqual(state,before)
                city.gold-=price
                previous=equipment.claim_purchase(game,state,city,target,slot,ident)
                self.assertEqual(previous,0)
                self.assertEqual(getattr(target,slot+'_id'),ident)
                ledger=state.extension['equipment']['uniques'][f'{slot}:{ident}']
                self.assertEqual((ledger['holder'],ledger['method']),(target_pid,'purchase'))
                self.fails(game,state,equipment.purchase_quote,city,state.officers[3],slot,ident)
                equipment.validate(game,state)

    def test_specials_never_leak_into_ordinary_stock_and_rejections_do_not_spend(self):
        game,state=fixture();city=state.cities['capital'];target=state.officers[2]
        ordinary={(slot,row['id']) for slot in ('weapon','armor') for row in equipment.stock(3,slot)}
        self.assertFalse(ordinary & equipment.UNIQUE)
        for slot,ident in equipment.UNIQUE:
            self.fails(game,state,equipment.purchase_quote,city,target,slot,ident)
        city=shop_city(game,state,'wuwei')
        target.profile=replace(target.profile,martial_strength=89)
        self.fails(game,state,equipment.purchase_quote,city,target,'weapon',22)
        target.profile=replace(target.profile,martial_strength=90)
        city.gold=349
        self.fails(game,state,equipment.purchase_quote,city,target,'weapon',22)
        self.assertEqual(state.rng.draws,0)

    def test_backup_re_equips_without_money_and_unique_is_never_destroyed(self):
        game,state=fixture();city=shop_city(game,state,'wuwei');target=state.officers[2]
        target.profile=replace(target.profile,martial_strength=90)
        equipment.claim_purchase(game,state,city,target,'weapon',22)
        equipment.claim_purchase(game,state,city,target,'weapon',2)
        self.assertIn(22,state.extension['equipment']['reserves'][target.person_id]['weapon'])
        before_gold=city.gold;before_rng=deepcopy(state.rng)
        receipt=equipment.equip_owned(game,state,
            dict(city=city.id,actor=1,officer=2,slot='weapon',item=22),'one')
        self.assertEqual(receipt['method'],'owned')
        self.assertEqual(city.gold,before_gold)
        self.assertEqual(state.rng,before_rng)
        self.assertTrue(city.action_used)
        self.assertEqual(state.extension['officer_actions'],{'1':1,'2':1})
        self.assertEqual(target.weapon_id,22)
        self.assertNotIn(22,state.extension['equipment']['reserves'][target.person_id]['weapon'])
        self.assertIn(2,state.extension['equipment']['reserves'][target.person_id]['weapon'])
        equipment.validate(game,state)
        self.fails(game,state,equipment.equip_owned,
            dict(city=city.id,actor=1,officer=3,slot='weapon',item=22),'one')

    def test_gear_projections_match_shop_preview_and_do_not_change_base_attributes(self):
        game,state=fixture();city=state.cities['capital'];person=state.officers[2]
        before=deepcopy(state)
        offers=equipment.shop_stock(game,state,city,'weapon')
        row=next(row for row in offers if row['id']==4)
        projected=row['preview_by_officer']['2']
        self.assertEqual(projected['before'],equipment._numbers(person))
        self.assertEqual(projected['after'],equipment._numbers(replace(person,weapon_id=4)))
        self.assertEqual(state,before)
        self.assertEqual(projected['before']['base_martial'],projected['after']['base_martial'])
        equipment.claim_purchase(game,state,city,person,'weapon',4)
        self.assertEqual(equipment._numbers(person),projected['after'])

    def test_full_99_person_roster_has_bounded_scalar_previews_and_no_view_mutation(self):
        game,state=fixture();city=state.cities['capital']
        for ident in range(20,113):
            officer=replace(state.officers[2],runtime_id=ident,person_id=f'full-roster-{ident}')
            state.officers[ident]=officer;city.roster.officer_ids.append(ident)
        self.assertEqual(len(city.roster.officer_ids),99)
        equipment.synchronize(game,state)
        before=deepcopy(state)
        offers=equipment.shop_stock(game,state,city,'weapon')
        self.assertLessEqual(len(offers),29)
        for offer in offers:
            self.assertEqual(len(offer['preview_by_officer']),99)
            for value in offer['preview_by_officer'].values():
                self.assertNotIn('weapon',value['before'])
                self.assertNotIn('armor',value['after'])
                self.assertTrue(all(type(number) is int for number in value['after'].values()))
        self.assertEqual(state,before)
        equipment.validate(game,state)

    def test_weight_changes_hit_evasion_initiative_and_bounded_retreat(self):
        game,state=fixture();person=state.officers[2]
        light=replace(person,weapon_id=7,armor_id=0)
        heavy=replace(person,weapon_id=4,armor_id=5)
        low=replace(heavy,profile=replace(person.profile,martial_strength=20))
        self.assertGreater(equipment.combat_stats(heavy)['total_weight'],equipment.combat_stats(light)['total_weight'])
        self.assertLess(equipment.duel_initiative(heavy,5),equipment.duel_initiative(light,5))
        self.assertGreater(equipment.combat_stats(low)['hit_penalty'],equipment.combat_stats(heavy)['hit_penalty'])
        self.assertLess(equipment.duel_hit_chance(low,light),equipment.duel_hit_chance(light,light))
        self.assertEqual(equipment.duel_initiative(light,0),
            (light.health+light.profile.martial_strength)//10-5+20)
        self.assertEqual(equipment.retreat_cost(heavy,0),equipment.combat_stats(heavy)['retreat_health_max'])
        self.assertEqual(equipment.retreat_cost(light,99),0)
        exhausted=replace(heavy,health=1)
        self.assertEqual(equipment.combat_stats(exhausted)['retreat_health_max'],0)
        self.assertEqual(equipment.retreat_cost(exhausted,0),0)
        self.assertTrue(all(10<=equipment.duel_hit_chance(a,b)<=95 for a in (light,heavy,low) for b in (light,heavy,low)))
        self.assertEqual(state.rng.draws,0)

    def duel(self,*,loser='san14-candidate-0771',tier=0,seed=2026):
        game,state=fixture();winner,foe=state.officers[2],state.officers[6]
        original=foe.person_id;foe.person_id=loser
        state.extension['equipment']['initialized'].remove(original)
        equipment.synchronize(game,state)
        winner.tier=tier;state.rng=SeedRng(seed)
        state.phase='battle';state.battle_counter=1
        battle=dict(id='battle-1',target='capital')
        state.battle=battle
        return game,state,battle,winner,foe

    def test_guaranteed_duel_loot_no_rng_and_receipt_blocks_repeat(self):
        game,state,battle,winner,loser=self.duel()
        receipt=equipment.duel_loot(game,state,battle,2,6)
        self.assertEqual((winner.weapon_id,receipt['chance'],receipt['roll']),(5,100,-1))
        self.assertEqual(state.rng.draws,0)
        before=deepcopy(state)
        self.assertIsNone(equipment.duel_loot(game,state,battle,2,6))
        self.assertEqual(state,before)
        equipment.validate(game,state)

    def test_conditional_duel_rng_once_even_on_failure_and_other_holder_blocks_drop(self):
        for pid,chance,ident in [('san14-candidate-0521',30,6),('ordinary-lord',50,14)]:
            for seed in (1,2026):
                with self.subTest(pid=pid,seed=seed):
                    game,state,battle,winner,loser=self.duel(loser=pid,seed=seed)
                    expected=deepcopy(state.rng);roll=expected.next()%100
                    receipt=equipment.duel_loot(game,state,battle,2,6)
                    self.assertEqual(state.rng,expected)
                    self.assertEqual(receipt is not None,roll<chance)
                    if receipt:self.assertEqual(winner.weapon_id,ident)
                    before=deepcopy(state)
                    self.assertIsNone(equipment.duel_loot(game,state,battle,2,6))
                    self.assertEqual(state,before)
                    equipment.validate(game,state)
        game,state,battle,winner,loser=self.duel()
        equipment._give(state,state.officers[3],'weapon',5,'duel')
        before=deepcopy(state.rng)
        self.assertIsNone(equipment.duel_loot(game,state,battle,2,6))
        self.assertEqual(state.rng,before)
        equipment.validate(game,state)

    def test_dong_zhuo_level_condition_and_non_rulers_cannot_drop(self):
        game,state,battle,winner,loser=self.duel(loser='san14-candidate-0736',tier=2)
        self.assertIsNone(equipment.duel_loot(game,state,battle,2,6))
        self.assertEqual((winner.weapon_id,state.rng.draws),(0,0))
        winner.tier=1
        self.assertEqual(equipment.duel_loot(game,state,battle,2,6)['item'],7)
        game,state,battle,winner,loser=self.duel()
        state.extension['leaders']['two']=100
        before=deepcopy(state)
        self.assertIsNone(equipment.duel_loot(game,state,battle,2,6))
        self.assertEqual(state,before)

    def test_existing_unique_is_transferred_out_of_equipped_or_reserved_loser(self):
        for reserved in (False,True):
            game,state,battle,winner,loser=self.duel()
            equipment._give(state,loser,'weapon',5,'duel')
            if reserved:equipment._give(state,loser,'weapon',2,'purchase')
            receipt=equipment.duel_loot(game,state,battle,2,6)
            self.assertEqual(receipt['item'],5)
            self.assertEqual(winner.weapon_id,5)
            self.assertNotEqual(loser.weapon_id,5)
            self.assertNotIn(5,state.extension['equipment']['reserves'].get(loser.person_id,{}).get('weapon',[]))
            self.assertEqual(state.extension['equipment']['uniques']['weapon:5']['holder'],winner.person_id)
            equipment.synchronize(game,state)
            self.assertNotEqual(loser.weapon_id,5,'Synchronizing cannot re-create looted equipment')
            equipment.validate(game,state)

    def test_save_domains_unique_duplicates_bad_receipts_and_bad_ids_are_rejected(self):
        mutations=[lambda s:s.extension['equipment']['initialized'].append('unknown-person'),
            lambda s:s.extension['equipment']['reserves'].update(unknown=dict(weapon=[],armor=[])),
            lambda s:s.extension['equipment']['reserves'].update({'person-2':dict(weapon=[0],armor=[])}),
            lambda s:setattr(s.officers[2],'weapon_id',True),
            lambda s:s.extension['equipment']['loot_receipts'].append('forged:person-2:weapon:5')]
        for mutate in mutations:
            game,state=fixture();mutate(state)
            with self.assertRaises((ValueError,KeyError,TypeError)):equipment.validate(game,state)
        game,state=fixture();equipment._give(state,state.officers[2],'weapon',5,'duel')
        state.officers[3].weapon_id=5
        with self.assertRaises(ValueError):equipment.validate(game,state)


if __name__=='__main__':unittest.main()
