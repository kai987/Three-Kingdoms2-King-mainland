"""Real campaigns exercise facility profiles, saves, disasters and combat.

Small calendars/rosters isolate practical boundaries; they are controlled game
fixtures and do not assert historical deployment, weather or city facilities.
"""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
import tempfile
from time import perf_counter
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import civil_staff,facilities,treasures
from remake.campaign import Campaign,Catalog,SeedRng,digest,canonical
from remake.city_economy import income_at,tier_at
from remake.errors import GameError
from remake.march_core import using_backend,invoke,CoreUnavailable
from remake.session import CampaignSession
from remake.view_transport import ViewTransport
from campaign_fixtures import controlled_catalog
from test_remake_civil_staff_campaign import staff_catalog
from test_remake_tactical_ai import successful_rng


def facility_catalog(*,month=4,disasters=False):
    data=deepcopy(controlled_catalog().data)
    data.update(id='controlled-facility-campaign',start_month=month,facility_ai_default=False,
        facility_rules=deepcopy(facilities.RULES),
        facility_disaster_cities=dict(flood=['xiangyang'],drought=['xiangyang']))
    data['facility_rules'].update(disasters_enabled=disasters)
    data['rules']['persuade_officer_gold']=100000000
    data['initial_owners']['nanjun']='shu'
    for key in data['active_cities']:
        data['city_profiles'][key]['tier']='giant'
        data.get('city_scale_rules',{}).get('cities',{}).pop(key,None)
        data['initial_city_resources'][key]=dict(gold=5000,grain=100000,reserves=5000)
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'facilities.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


class FacilityCampaignTests(unittest.TestCase):
    def new(self,**options):
        game=Campaign(facility_catalog(**options))
        game.command('new',dict(faction='shu',seed=2026),0)
        return game

    def cmd(self,game,kind,**payload):
        return game.command(kind,payload,game.revision)

    def advance(self,game,count=1):
        for _ in range(count):
            game._complete_turn(game.state)
            game._reconcile_factions(game.state)
            civil_staff.synchronize(game,game.state,monthly=game.state.day==1)
            treasures.synchronize(game,game.state)
            facilities.synchronize(game,game.state)
            game.validate(game.state)

    def restore(self,game):
        saved=game.export_save();other=Campaign(game.catalog)
        other.load_save(json.loads(json.dumps(saved)),0)
        self.assertEqual(other.export_save(),saved)
        return other

    def fails(self,game,kind,**payload):
        before,revision,journal=game.export_save(),game.revision,deepcopy(game.journal)
        with self.assertRaises((GameError,ValueError,TypeError)):
            self.cmd(game,kind,**payload)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)
        self.assertEqual(game.journal,journal)

    def test_all_29_openings_and_city_previews_keep_initial_facilities_and_rng_pure(self):
        paths=[path for path in sorted((ROOT/'game/data/campaigns').glob('*.json')) if path.name!='index.json']
        self.assertEqual(len(paths),29)
        session=CampaignSession(paths)
        for path in paths:
            catalog=session.catalogs[json.loads(path.read_text())['id']]
            game=Campaign(catalog)
            player=next(iter(catalog.factions))
            game.command('new',dict(faction=player,seed=2026),0)
            before=game.export_save()
            result=game.view()['catalog']['facilities']
            self.assertEqual(set(result['cities']),set(game.state.cities))
            for key,city in game.state.cities.items():
                with self.subTest(scenario=catalog.data['id'],city=key):
                    row=result['cities'][key]
                    self.assertEqual(row['town'],{'normal':1,'large':2,'giant':3}[
                        tier_at(catalog.data,key,game.state.year,game.state.month)])
                    self.assertEqual((row['preparedness'],row['damage']),(40,0))
                    preview=session.preview_city(catalog.data['id'],key)
                    self.assertEqual(preview['city']['owner'],city.owner)
            self.assertEqual(game.export_save(),before)
            self.assertEqual(session.game.state,None,'Opening city previews cannot start a campaign')
            self.assertFalse(result['factions'][player]['policy']['enabled'])
            self.assertTrue(all(row['policy']['enabled'] for key,row in result['factions'].items() if key!=player))

    def test_historical_school_profile_survives_cache_save_transfer_and_same_next_rng(self):
        game=self.new();ident=146;actor=439
        original=deepcopy(game.catalog.profiles[ident]);before=game.state.officers[ident].profile.intellect
        transport=ViewTransport();first=transport.pack(game.view(),game.catalog.sha256)
        known=first['catalog_token']+':'+first['quote_token']
        self.cmd(game,'study_officer',city='xiangyang',actor=actor,officer=ident)
        officer=game.state.officers[ident]
        self.assertGreater(officer.profile.intellect,before)
        self.assertEqual(game.catalog.profiles[ident],original)
        self.assertEqual(officer.profile.basis['intellect'],'source_initial_plus_campaign_school_learning')
        changed=transport.pack(game.view(),game.catalog.sha256,known)
        self.assertNotIn('static_catalog',changed)
        row=next(row for row in changed['view']['catalog']['library'] if row['id']==ident)
        self.assertEqual(row['intellect'],officer.profile.intellect)
        self.assertEqual(row['study_gain'],officer.profile.intellect-before)
        saved=game.export_save();loaded=self.restore(game)
        self.advance(game);self.advance(loaded)
        self.cmd(game,'improve_prevention',city='xiangyang',actor=actor)
        self.cmd(loaded,'improve_prevention',city='xiangyang',actor=actor)
        self.assertEqual(game.export_save(),loaded.export_save())
        self.assertEqual(game.state.rng,loaded.state.rng)
        self.assertEqual(saved['state']['officers'][str(ident)]['profile']['intellect'],officer.profile.intellect)
        for current in (game,loaded):
            self.advance(current)
            self.cmd(current,'transfer',source='xiangyang',target='nanjun',officers=[ident],route_mode='land')
            self.advance(current)
            self.cmd(current,'arrivals')
            self.assertIn(ident,current.state.cities['nanjun'].roster.officer_ids)
            self.assertNotIn(ident,current.state.cities['xiangyang'].roster.officer_ids)
            self.assertEqual(current.state.officers[ident].profile.intellect,officer.profile.intellect)
        self.assertEqual(game.export_save(),loaded.export_save())

    def test_generated_student_retains_base_identity_through_learning_and_save(self):
        game=Campaign(staff_catalog())
        self.cmd(game,'new',faction='shu',seed=2026)
        city='nanjun';ident=game.state.extension['civil_staff']['cities'][city]['candidate']['id']
        self.cmd(game,'hire_staff',city=city,candidate=ident)
        self.advance(game)
        game.state.extension['facilities']['cities'][city]['town']=2
        base=deepcopy(game.state.extension['civil_staff']['people'][ident]['profile'])
        before=game.state.officers[ident].profile.intellect
        self.cmd(game,'study_officer',city=city,actor=ident,officer=ident)
        self.assertGreater(game.state.officers[ident].profile.intellect,before)
        self.assertEqual(game.state.extension['civil_staff']['people'][ident]['profile'],base)
        self.assertNotIn(ident,game.catalog.by_id)
        restored=self.restore(game)
        self.assertEqual(restored.state.officers[ident].profile,game.state.officers[ident].profile)
        self.assertEqual(restored.person_profile(restored.state,ident),restored.state.officers[ident].profile)

    def test_backend_changes_keep_real_facility_rolls_actions_and_save_bytes_equal(self):
        try:
            with using_backend('rust'):
                invoke('allocate',troops=[],numerator=1,denominator=1)
        except CoreUnavailable as error:
            if os.environ.get('MARCH_CORE_BACKEND')=='rust':raise
            self.skipTest(str(error))
        catalog=facility_catalog();saved=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=Campaign(catalog);self.cmd(game,'new',faction='shu',seed=2026)
                self.cmd(game,'study_officer',city='xiangyang',actor=439,officer=146)
                self.advance(game)
                self.cmd(game,'improve_prevention',city='xiangyang',actor=439)
                self.advance(game)
                self.cmd(game,'buy_equipment',city='xiangyang',actor=439,officer=146,slot='weapon',item=21)
                saved.append(game.export_save())
        self.assertEqual(saved[0],saved[1])

    def test_actual_month_disaster_has_one_receipt_actual_resource_loss_and_no_military_teleport(self):
        game=self.new(month=7,disasters=True)
        game.catalog.data['facility_rules']['drought_chance']=100
        source=game.state.cities['xiangyang'];row=game.state.extension['facilities']['cities'][source.id]
        row.update(preparedness=0,damage=0)
        game.state.officers[146].health=0
        self.advance(game,2)
        before=deepcopy(game.state);income=income_at(game.catalog.data,source.id,before.year,8)
        self.advance(game)
        events=[event for event in game.state.extension['events']['items'] if event['kind']=='city_disaster']
        self.assertEqual(len(events),1)
        receipt=events[0]['details'];current=game.state.cities[source.id]
        self.assertEqual(receipt['disaster'],'drought');self.assertEqual(receipt['rate'],10)
        self.assertEqual(current.gold,before.cities[source.id].gold+income['gold'])
        self.assertEqual(current.grain,before.cities[source.id].grain+income['grain']-receipt['grain'])
        self.assertEqual(current.reserves,before.cities[source.id].reserves+income['reserves']-receipt['reserves'])
        self.assertEqual(game.state.soldiers['lost']-before.soldiers['lost'],receipt['reserves'])
        self.assertEqual(game.state.officers[146].health,8,'Only established monthly healing changes the wounded officer')
        self.assertEqual({i:o.troops for i,o in game.state.officers.items()},
            {i:o.troops for i,o in before.officers.items()})
        self.assertEqual(game.state.extension['travel'],before.extension['travel'])
        committed=game.export_save()
        self.assertEqual(facilities.month_rollover(game,game.state),[])
        self.assertEqual(game.export_save(),committed)
        self.restore(game)

    def test_repair_restores_later_month_production_and_preparedness_99_prevents_losses(self):
        game=self.new(month=4,disasters=True)
        game.catalog.data['facility_rules'].update(flood_plain_chance=100,flood_mountain_chance=100)
        row=game.state.extension['facilities']['cities']['xiangyang']
        row.update(preparedness=99,damage=50)
        self.advance(game,3)
        disaster=[e for e in game.state.extension['events']['items'] if e['kind']=='city_disaster'][-1]['details']
        self.assertEqual((disaster['gold'],disaster['grain'],disaster['reserves']),(0,0,0))
        base=income_at(game.catalog.data,'xiangyang',game.state.year,game.state.month)
        income_before=facilities.adjusted_income(game.state,'xiangyang',base)
        self.cmd(game,'improve_prevention',city='xiangyang',actor=439)
        income_after=facilities.adjusted_income(game.state,'xiangyang',base)
        self.assertGreater(income_after['gold'],income_before['gold'])
        self.assertGreater(income_after['grain'],income_before['grain'])
        self.advance(game,2)
        row=game.state.extension['facilities']['cities']['xiangyang'];row['preparedness']=99
        before=deepcopy(game.state.cities['xiangyang'])
        base=income_at(game.catalog.data,'xiangyang',game.state.year,6)
        expected=facilities.adjusted_income(game.state,'xiangyang',base)
        self.advance(game)
        current=game.state.cities['xiangyang']
        self.assertEqual(current.gold,before.gold+expected['gold'])
        self.assertEqual(current.grain,before.grain+expected['grain'])
        self.assertEqual(current.reserves,before.reserves+expected['reserves'])
        self.restore(game)

    def test_actual_ai_turn_treats_using_shared_fee_rng_and_local_actions(self):
        game=self.new();city=game.state.cities['nanyang'];ident=city.roster.officer_ids[0]
        officer=game.state.officers[ident]
        city.reserves+=officer.troops;officer.troops=0;officer.health=20
        other=game.state.cities['jiangxia']
        for other_id in other.roster.officer_ids:
            other.reserves+=game.state.officers[other_id].troops;game.state.officers[other_id].troops=0
        game.state.extension['facilities']['factions']['wei'].update(enabled=True,
            auto_prevent=False,auto_treat=True,auto_trade=False,auto_equip=False,auto_develop=False,auto_study=False)
        expected_rng=deepcopy(game.state.rng);healing=35+expected_rng.next()%11
        before_troops=deepcopy(game.state.soldiers)
        self.cmd(game,'end_turn');self.cmd(game,'ai',turn=game.state.turn)
        receipts=[e for e in game.state.extension['events']['items'] if e['kind']=='officer_treated' and e['city_ids']==['nanyang']]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]['details']['gold'],50)
        self.assertEqual(receipts[0]['details']['after']-receipts[0]['details']['before'],healing)
        self.assertEqual(game.state.rng,expected_rng)
        self.assertEqual(game.state.soldiers,before_troops)
        self.assertEqual(game.state.extension['officer_actions'][str(ident)],1)
        self.assertEqual(game.state.phase,'city');self.assertEqual(game.state.turn,2)
        self.restore(game)

    def test_bought_weapon_changes_real_duel_damage_without_extra_rng(self):
        bare=self.new();armed=self.restore(bare)
        self.cmd(armed,'buy_equipment',city='xiangyang',actor=439,officer=146,slot='weapon',item=21)
        losses=[];rng=[]
        for game in (bare,armed):
            self.advance(game)
            state=game.state
            game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],[146])
            successful_rng(state)
            battle=state.battle;target=battle['defenders'][0]['id']
            self.cmd(game,'duel_start',battle_id=battle['id'],actor=146,target=target)
            self.assertIsNotNone(game.state.battle['extended']['duel'])
            game.state.rng=SeedRng(2026)
            before=game.state.battle['extended']['support'][str(target)]['health']
            self.cmd(game,'duel_action',battle_id=game.state.battle['id'],move='strike')
            losses.append(before-game.state.battle['extended']['support'][str(target)]['health'])
            rng.append(deepcopy(game.state.rng))
            game.validate(game.state)
        self.assertGreater(losses[1],losses[0]);self.assertEqual(rng[0],rng[1])

    def test_foreign_actors_policy_and_saved_learning_or_rule_tampering_fail_atomically(self):
        game=self.new()
        for kind,payload in [('treat_officer',dict(city='nanyang',actor=123,officer=123)),
                ('study_officer',dict(city='xiangyang',actor=123,officer=146)),
                ('buy_equipment',dict(city='xiangyang',actor=439,officer=123,slot='weapon',item=21)),
                ('improve_prevention',dict(city='xiangyang',actor=True)),
                ('set_facility_policy',dict(faction='wei',policy=dict(enabled=True)))]:
            self.fails(game,kind,**payload)
        self.cmd(game,'study_officer',city='xiangyang',actor=439,officer=146)
        original=game.export_save()
        for mutate in (lambda p:p['state']['extension']['facilities']['study'].update({'146':100}),
                lambda p:p['state']['officers']['146']['profile'].update(intellect=99),
                lambda p:p['state']['extension']['facilities']['cities']['xiangyang'].update(damage=51),
                lambda p:p['state']['extension']['facilities']['factions']['shu'].update(enabled=1)):
            bad=deepcopy(original);mutate(bad)
            bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            with self.assertRaises(GameError):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),original)


if __name__=='__main__':unittest.main()
