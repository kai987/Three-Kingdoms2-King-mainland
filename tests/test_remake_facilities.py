"""Shared facility services, bounded quotes, saved learning and disaster state."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import facilities, civil_staff, facility_equipment, equipment
from remake.campaign import SeedRng
from remake.errors import GameError
from remake.officers import GameRules, OfficerProfile, RuntimeOfficer


class FixtureGame:
    def __init__(self):
        self.catalog = SimpleNamespace(rules=GameRules(99,10,1200),
            factions={'one':{},'two':{}}, data=dict(start_year=217,start_month=4,
                city_profiles={'capital':dict(tier='giant'),'border':dict(tier='normal'),
                    'enemy':dict(tier='large'),'neutral':dict(tier='normal')},
                facility_rules={}),
            map_cities={'capital':dict(terrain='plain'),'border':dict(terrain='mountain'),
                'enemy':dict(terrain='water'),'neutral':dict(terrain='plain')},profiles={})

    def _march_ids(self,state):
        return {ident for row in state.extension['travel']['marches'] for ident in row['officers']}

    def _emit_event(self,state,kind,**values):
        state.events.append(deepcopy(dict(kind=kind,**values)))


def fixture(seed=2026):
    game=FixtureGame()
    officers={}
    for ident,intellect,owner in ((1,90,'one'),(2,20,'one'),(3,60,'one'),
            (4,79,'one'),(5,80,'one'),(6,50,'two'),(7,40,'one')):
        profile=OfficerProfile(99,70,intellect,75,0)
        game.catalog.profiles[ident]=profile
        officers[ident]=RuntimeOfficer(ident,f'person-{ident}',profile,80,80,300,faction_id=owner)
    clerk=dict(id='clerk-000001',name='王安',working=True,
        profile=dict(health_max=80,martial_strength=50,intellect=50,virtue=60))
    profile=civil_staff.officer_profile(clerk)
    officers[clerk['id']]=RuntimeOfficer(clerk['id'],clerk['id'],profile,60,80,300,faction_id='one')
    cities={key:SimpleNamespace(id=key,owner=owner,gold=1000,grain=10000,reserves=1000,
        action_used=False,roster=SimpleNamespace(officer_ids=ids))
        for key,owner,ids in [('capital','one',[1,2,3,4,5,7]),('border','one',[clerk['id']]),
            ('enemy','two',[6]),('neutral','neutral',[])]}
    state=SimpleNamespace(year=217,month=4,day=1,turn=1,phase='city',player='one',
        rng=SeedRng(seed),battle=None,cities=cities,officers=officers,events=[],
        soldiers=dict(initial=6400,recruited=0,lost=0),extension=dict(
            civil_staff=dict(people={clerk['id']:clerk}),officer_actions={},leaders=dict(one=1,two=6),
            ended_factions=[],pending_succession={},travel=dict(marches=[])))
    state.extension['facilities']=facilities.empty(game,state)
    # Keep these facility transactions focused on their original baseline.
    # Source-based equipment and signature acquisition have a separate suite.
    game.catalog.data['equipment_initial']={o.person_id:dict(weapon_id=0,armor_id=0,
        basis='controlled_facility_baseline') for o in state.officers.values()}
    state.extension['equipment']=equipment.empty(game,state)
    equipment.synchronize(game,state)
    facilities.validate(game,state)
    return game,state


class FacilityTests(unittest.TestCase):
    def fails(self,game,state,service,payload,owner='one'):
        before=deepcopy(state)
        with self.assertRaises((GameError,ValueError,TypeError)):
            service(game,state,payload,owner)
        self.assertEqual(state,before,'Refused services cannot spend, draw RNG, mark actions or emit events')

    def reset(self,state):
        state.turn+=1
        for city in state.cities.values():city.action_used=False

    def test_opening_towns_ownership_and_views_are_pure(self):
        game,state=fixture()
        pool=state.extension['facilities']
        self.assertEqual({k:r['town'] for k,r in pool['cities'].items()},
            dict(capital=3,border=1,enemy=2,neutral=1))
        self.assertTrue(all(r['preparedness']==40 and r['damage']==0 for r in pool['cities'].values()))
        before=deepcopy(state)
        for _ in range(3):
            view=facilities.view(game,state)
            self.assertEqual(view['cities']['border']['services'],['hospital','market'])
            self.assertFalse(view['cities']['enemy']['can_manage'])
            self.assertTrue(view['cities']['capital']['can_act'])
        view['factions']['one']['policy']['enabled']=True
        view['cities']['capital']['stock']['weapon'][0]['eligible_targets'].clear()
        self.assertEqual(state,before)
        row=pool['cities']['capital'];row.update(preparedness=90,damage=30)
        state.cities['capital'].owner='two'
        facilities.synchronize(game,state)
        self.assertEqual(row,dict(owner='two',town=3,preparedness=90,damage=30))
        state.cities['new']=SimpleNamespace(owner='one')
        facilities.synchronize(game,state)
        self.assertEqual(pool['cities']['new'],dict(owner='one',town=1,preparedness=40,damage=0))

    def test_develop_opens_real_services_once_without_free_resources(self):
        game,state=fixture();city=state.cities['border'];actor='clerk-000001'
        before=deepcopy(state.rng)
        for expected in (2,3):
            self.reset(state)
            old_gold=city.gold
            receipt=facilities.develop(game,state,dict(city=city.id,actor=actor),'one')
            self.assertEqual(receipt['to_town'],expected)
            self.assertEqual(city.gold,old_gold-100*expected)
            self.assertTrue(city.action_used)
            self.assertEqual(state.extension['officer_actions'][actor],state.turn)
        self.assertEqual(state.rng,before)
        self.reset(state)
        self.fails(game,state,facilities.develop,dict(city=city.id,actor=actor))
        facilities.validate(game,state)

    def test_hospital_uses_one_saved_roll_and_respects_health_cap(self):
        game,state=fixture();state.officers[2].health=0
        expected=deepcopy(state.rng);gain=35+expected.next()%11
        receipt=facilities.treat(game,state,dict(city='capital',actor=1,officer=2),'one')
        self.assertEqual((receipt['before'],receipt['after']),(0,gain))
        self.assertEqual(state.rng,expected)
        self.assertEqual(state.cities['capital'].gold,950)
        self.assertEqual(state.extension['officer_actions'],{'1':1,'2':1})
        self.reset(state);state.officers[2].health=98
        facilities.treat(game,state,dict(city='capital',actor=1,officer=2),'one')
        self.assertEqual(state.officers[2].health,99)
        self.reset(state)
        self.fails(game,state,facilities.treat,dict(city='capital',actor=1,officer=2))
        state.officers[2].health=50;state.cities['capital'].gold=49
        self.fails(game,state,facilities.treat,dict(city='capital',actor=1,officer=2))

    def test_unpaid_or_exhausted_patient_can_be_treated_by_another_valid_actor(self):
        game,state=fixture();clerk='clerk-000001'
        state.cities['border'].roster.officer_ids.remove(clerk)
        state.cities['capital'].roster.officer_ids.append(clerk)
        state.extension['civil_staff']['people'][clerk]['working']=False
        state.extension['officer_actions'][clerk]=state.turn
        self.fails(game,state,facilities.treat,dict(city='capital',actor=clerk,officer=2))
        facilities.treat(game,state,dict(city='capital',actor=1,officer=clerk),'one')
        self.assertGreater(state.officers[clerk].health,60)

    def test_school_all_three_knowledge_bands_have_exact_cost_and_one_draw(self):
        for ident,cost,low,high in ((2,30,5,9),(3,20,8,12),(4,10,6,10)):
            with self.subTest(officer=ident):
                game,state=fixture();before=state.officers[ident].profile.intellect
                expected=deepcopy(state.rng);after=min(89,before+low+expected.next()%(high-low+1))
                receipt=facilities.study(game,state,dict(city='capital',actor=1,officer=ident),'one')
                self.assertEqual((receipt['gold'],receipt['after']),(cost,after))
                self.assertEqual(state.rng,expected)
                self.assertEqual(state.officers[ident].profile.intellect,after)
                self.assertEqual(game.catalog.profiles[ident].intellect,before)
                self.assertEqual(facilities.learned_profile(state,ident,game.catalog.profiles[ident]),state.officers[ident].profile)
                original=game.catalog.profiles[ident]
                effective=facilities.learned_profile(state,ident,original)
                self.assertEqual(effective.basis['intellect'],'source_initial_plus_campaign_school_learning')
                self.assertNotIn('intellect',original.basis)
                self.assertEqual(effective.source_stats,original.source_stats)
                effective.basis['test_only']='changed'
                self.assertNotIn('test_only',original.basis)
                facilities.validate(game,state)
        game,state=fixture()
        self.fails(game,state,facilities.study,dict(city='capital',actor=1,officer=5))
        for _ in range(20):
            self.reset(state)
            if state.officers[2].profile.intellect>=80:break
            facilities.study(game,state,dict(city='capital',actor=1,officer=2),'one')
        self.assertLessEqual(state.officers[2].profile.intellect,89)
        self.assertGreaterEqual(state.officers[2].profile.intellect,80)
        facilities.validate(game,state)

    def test_generated_learning_uses_independent_base_profile(self):
        game,state=fixture();clerk='clerk-000001'
        state.extension['facilities']['cities']['border']['town']=2
        base=civil_staff.officer_profile(state.extension['civil_staff']['people'][clerk])
        facilities.study(game,state,dict(city='border',actor=clerk,officer=clerk),'one')
        self.assertEqual(base.intellect,50)
        self.assertGreater(state.officers[clerk].profile.intellect,50)
        self.assertEqual(state.extension['civil_staff']['people'][clerk]['profile']['intellect'],50)
        facilities.validate(game,state)

    def test_market_limits_no_arbitrage_and_resource_maxima(self):
        for town in (1,2,3):
            game,state=fixture();pool=state.extension['facilities'];pool['cities']['capital']['town']=town
            before=deepcopy(state.rng);city=state.cities['capital'];initial=(city.gold,city.grain)
            bought=facilities.trade(game,state,dict(city='capital',actor=1,direction='buy',batches=5),'one')
            self.reset(state)
            sold=facilities.trade(game,state,dict(city='capital',actor=1,direction='sell',batches=5),'one')
            self.assertEqual(city.grain,initial[1]);self.assertLessEqual(city.gold,initial[0])
            self.assertLessEqual(sold['gold'],bought['gold']);self.assertEqual(state.rng,before)
        game,state=fixture();city=state.cities['capital']
        for patch in (dict(batches=0),dict(batches=True),dict(batches=1001),dict(direction='gift')):
            payload=dict(city='capital',actor=1,direction='buy',batches=1);payload.update(patch)
            self.fails(game,state,facilities.trade,payload)
        city.grain=facilities.LIMIT-99
        self.fails(game,state,facilities.trade,dict(city='capital',actor=1,direction='buy',batches=1))
        city.grain=100;city.gold=facilities.LIMIT-8
        self.fails(game,state,facilities.trade,dict(city='capital',actor=1,direction='sell',batches=1))

    def test_armory_real_items_slots_affordability_and_special_unsold_items(self):
        game,state=fixture();before=deepcopy(state.rng);city=state.cities['capital']
        target=state.officers[2];old_pid=target.person_id
        target.person_id='san14-candidate-0656'
        state.extension['equipment']['initialized'].remove(old_pid)
        game.catalog.data['equipment_initial'][target.person_id]=dict(weapon_id=0,armor_id=0,basis='controlled')
        equipment.synchronize(game,state)
        def relocate(name):
            old=city.id
            state.cities.pop(old);city.id=name;state.cities[name]=city
            state.extension['facilities']['cities'][name]=state.extension['facilities']['cities'].pop(old)
            game.catalog.map_cities[name]=game.catalog.map_cities.pop(old)
        relocate('fuling')
        receipt=facilities.buy(game,state,dict(city=city.id,actor=1,officer=2,slot='weapon',item=23),'one')
        self.assertEqual(state.officers[2].weapon_id,23)
        self.assertEqual(city.gold,1000-facility_equipment.item('weapon',23)['price'])
        self.assertEqual(receipt['previous'],0);self.assertEqual(state.rng,before)
        self.reset(state)
        for item in (23,5,7,99,True):
            self.fails(game,state,facilities.buy,dict(city=city.id,actor=1,officer=2,slot='weapon',item=item))
        relocate('yongchang')
        state.officers[2].profile=replace(state.officers[2].profile,virtue=90)
        facilities.buy(game,state,dict(city=city.id,actor=1,officer=2,slot='armor',item=6),'one')
        self.assertEqual(state.officers[2].armor_id,6)
        self.assertEqual(city.gold,1000-400-350)
        self.reset(state);state.extension['facilities']['cities'][city.id]['town']=2
        self.fails(game,state,facilities.buy,dict(city=city.id,actor=1,officer=3,slot='weapon',item=23))
        equipment.validate(game,state)

    def test_prevention_exact_two_rolls_quote_range_zero_gain_and_max_guard(self):
        game,state=fixture();city=state.cities['capital'];row=state.extension['facilities']['cities']['capital']
        row['damage']=20;before=deepcopy(row);expected=deepcopy(state.rng)
        gold=16+expected.next()%4;effect=6+expected.next()%5;raw=(gold*90//100)*effect//10
        receipt=facilities.prevent(game,state,dict(city='capital',actor=1),'one')
        self.assertEqual((receipt['gold'],receipt['gain'],receipt['repair']),(gold,raw,raw//2))
        self.assertEqual(row['preparedness'],before['preparedness']+raw);self.assertEqual(state.rng,expected)
        self.reset(state);city.gold=18
        self.fails(game,state,facilities.prevent,dict(city='capital',actor=1))
        city.gold=1000;row.update(preparedness=99,damage=0)
        self.fails(game,state,facilities.prevent,dict(city='capital',actor=1))
        row['damage']=1;facilities.prevent(game,state,dict(city='capital',actor=1),'one')
        self.assertEqual(row['preparedness'],99);self.assertEqual(row['damage'],0)
        self.reset(state);row.update(preparedness=40,damage=0)
        state.officers[2].profile=replace(state.officers[2].profile,intellect=1)
        before=deepcopy(row);receipt=facilities.prevent(game,state,dict(city='capital',actor=2),'one')
        self.assertEqual(receipt['gain'],0);self.assertEqual(row,before)

    def test_actor_ownership_phase_marching_battle_and_shared_action_rejections(self):
        game,state=fixture()
        for payload in (dict(city='enemy',actor=6),dict(city='neutral',actor=1),
                dict(city='capital',actor=6),dict(city='capital',actor=True),
                dict(city='capital',actor='1'),dict(city='capital',actor=1,unknown=True)):
            self.fails(game,state,facilities.prevent,payload)
        for modifier in ('march','battle','health','action','pending','phase'):
            game,state=fixture()
            if modifier=='march':state.extension['travel']['marches']=[dict(officers=[1])]
            elif modifier=='battle':state.battle=dict(attackers=[dict(id=1)],defenders=[])
            elif modifier=='health':state.officers[1].health=0
            elif modifier=='action':state.extension['officer_actions']['1']=state.turn
            elif modifier=='pending':state.extension['pending_succession']['one']={}
            else:state.phase='ai'
            if modifier=='pending':state.extension['pending_succession']['one']={'candidates':[1]}
            self.fails(game,state,facilities.prevent,dict(city='capital',actor=1))
        game,state=fixture();facilities.prevent(game,state,dict(city='capital',actor=1),'one')
        self.fails(game,state,facilities.trade,dict(city='capital',actor=2,direction='buy',batches=1))

    def test_monthly_disasters_are_bounded_once_and_do_not_touch_officers_or_cargo(self):
        for kind,month in (('flood',5),('drought',8)):
            game,state=fixture();game.catalog.data['facility_rules'].update(
                flood_plain_chance=100,flood_mountain_chance=100,drought_chance=100)
            game.catalog.data['facility_disaster_cities']={kind:['capital']}
            row=state.extension['facilities']['cities']['capital'];row['preparedness']=0
            before=deepcopy(state);state.month=month
            result=facilities.month_rollover(game,state)
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['rate'],10)
            self.assertEqual(state.cities['capital'].grain,9000)
            self.assertEqual(state.cities['capital'].gold,900 if kind=='flood' else 1000)
            self.assertEqual(state.cities['capital'].reserves,900 if kind=='drought' else 1000)
            self.assertEqual(state.soldiers['lost'],100 if kind=='drought' else 0)
            self.assertEqual(state.officers,before.officers)
            self.assertEqual(state.extension['travel'],before.extension['travel'])
            committed=deepcopy(state)
            self.assertEqual(facilities.month_rollover(game,state),[]);self.assertEqual(state,committed)
            facilities.validate(game,state)

    def test_full_preparedness_cancels_resource_loss_but_consumes_defenses(self):
        game,state=fixture();game.catalog.data['facility_rules'].update(flood_plain_chance=100)
        game.catalog.data['facility_disaster_cities']={'flood':['capital']}
        state.extension['facilities']['cities']['capital']['preparedness']=99
        before=deepcopy(state);state.month=5;expected=deepcopy(state.rng);expected.next();expected.next()
        event=facilities.month_rollover(game,state)[0]
        self.assertEqual((event['gold'],event['grain'],event['reserves'],event['rate']),(0,0,0,0))
        self.assertLess(state.extension['facilities']['cities']['capital']['preparedness'],99)
        self.assertEqual(state.rng,expected)
        self.assertEqual(state.soldiers,before.soldiers)
        self.assertEqual(facilities.adjusted_income(state,'capital',dict(gold=35,grain=90)),dict(gold=35,grain=90))
        state.extension['facilities']['cities']['capital']['damage']=50
        self.assertEqual(facilities.adjusted_income(state,'capital',dict(gold=35,grain=90)),dict(gold=17,grain=45))

    def test_policy_limits_auto_budget_idempotency_and_manual_service_parity(self):
        game,state=fixture();state.player='two';state.phase='ai'
        facilities.set_policy(game,state,dict(faction='one',policy=dict(enabled=True,gold_budget=30,gold_floor=100)), 'one')
        same=deepcopy(state);expected=facilities.auto_turn(game,state,'one')
        for row in expected:
            city=row['city'];actors=[i for i in same.cities[city].roster.officer_ids
                if facilities._resident(game,same,same.cities[city],i,working=True,unused=True,healthy=True)]
            actor=min(actors,key=lambda i:(-same.officers[i].profile.intellect,-same.officers[i].profile.virtue,facilities.ref_sort_key(i)))
            facilities.prevent(game,same,dict(city=city,actor=actor),'one')
        same.extension['facilities']['auto_turns']['one']=same.turn
        self.assertEqual(state,same)
        self.assertLessEqual(sum(row['gold'] for row in expected),30)
        before=deepcopy(state);self.assertEqual(facilities.auto_turn(game,state,'one'),[]);self.assertEqual(state,before)
        state.phase='city';state.player='one'
        for patch in (dict(enabled=1),dict(gold_budget=-1),dict(heal_below=100),dict(grain_floor=3000,grain_target=1000)):
            self.fails(game,state,facilities.set_policy,dict(faction='one',policy=patch))
        self.fails(game,state,facilities.set_policy,dict(faction='two',policy=dict(enabled=True)))

    def test_ai_healing_trading_equipment_development_and_study_all_use_services(self):
        for task in ('treat','trade','equip','develop','study'):
            with self.subTest(task=task):
                game,state=fixture();state.player='two';state.phase='ai'
                policy=state.extension['facilities']['factions']['one']
                policy.update(enabled=True,auto_prevent=False,auto_treat=False,gold_budget=1000,gold_floor=100)
                if task=='treat':policy['auto_treat']=True;state.officers[2].health=0
                elif task=='trade':policy['auto_trade']=True;state.cities['capital'].grain=0
                elif task=='equip':policy['auto_equip']=True
                elif task=='develop':policy['auto_develop']=True
                else:policy['auto_study']=True
                before=deepcopy(state)
                receipts=facilities.auto_turn(game,state,'one')
                self.assertTrue(receipts)
                self.assertTrue(all(state.cities[row['city']].action_used for row in receipts))
                if task=='treat':self.assertGreater(state.officers[2].health,0)
                elif task=='trade':self.assertGreater(state.cities['capital'].grain,0)
                elif task=='equip':self.assertNotEqual(state.officers[1].weapon_id,0)
                elif task=='develop':self.assertEqual(state.extension['facilities']['cities']['border']['town'],2)
                else:self.assertGreater(state.officers[2].profile.intellect,20)
                self.assertGreaterEqual(before.cities['capital'].gold,state.cities['capital'].gold)
                facilities.validate(game,state)

    def test_saved_schema_learning_domains_and_policy_tampering_fail(self):
        game,state=fixture()
        changes=[lambda p:p.update(schema='old'),lambda p:p['cities']['capital'].update(town=4),
            lambda p:p['cities']['capital'].update(preparedness=True),
            lambda p:p['cities']['capital'].update(damage=51),
            lambda p:p['factions']['one'].update(heal_below=0),
            lambda p:p['study'].update({'2':70}),lambda p:p['study'].update({'5':1}),
            lambda p:p['study'].update({'unknown':1}),lambda p:p['study'].update({'2':True}),
            lambda p:p.update(last_disaster_month=999999),lambda p:p['auto_turns'].update(one=2)]
        for change in changes:
            bad=deepcopy(state);change(bad.extension['facilities'])
            with self.assertRaises((ValueError,TypeError)):facilities.validate(game,bad)

    def test_rule_boundaries_and_regions_cannot_silently_accept_booleans_or_bad_ranges(self):
        for patch in (dict(disaster_base_rate=True),dict(flood_plain_chance=101),
                dict(drought_chance=-1),dict(disaster_base_rate=101),dict(unknown_rule=1),
                dict(medical_heal_min=46,medical_heal_max=45),dict(town_cap=True),
                dict(flood_months=[5,5]),dict(flood_months=[5],drought_months=[5]),
                dict(study_bands=[[30,30,9,5],[60,20,8,12],[79,10,6,10]]),
                dict(prevention_cost_bands=[[50,10,13],[80,13,16],[98,16,19]]),
                dict(market_buy_rates={'1':11,'2':10,'3':True}),
                dict(trade_batch_grain=101),dict(trade_max_batches=1001),
                dict(market_sell_rates={'1':7,'2':8,'3':101}),
                dict(study_bands=[[30,30,5,10],[60,20,8,12],[79,10,6,10]]),
                dict(market_sell_rates={'1':12,'2':8,'3':9})):
            with self.subTest(patch=patch):
                game,state=fixture();game.catalog.data['facility_rules']=patch
                with self.assertRaises((ValueError,TypeError)):facilities.validate(game,state)
        for regions in (dict(flood=['missing']),dict(flood=['capital','capital']),
                dict(fire=['capital']),dict(drought=[True])):
            game,state=fixture();game.catalog.data['facility_disaster_cities']=regions
            with self.assertRaises((ValueError,TypeError)):facilities.validate(game,state)
        game,state=fixture();game.catalog.data['facility_rules']['initial_preparedness']=0
        state.extension['facilities']=facilities.empty(game,state)
        self.assertTrue(all(row['preparedness']==0 for row in state.extension['facilities']['cities'].values()))
        state.cities['new']=SimpleNamespace(owner='one')
        facilities.synchronize(game,state)
        self.assertEqual(state.extension['facilities']['cities']['new']['preparedness'],0)


if __name__=='__main__':
    unittest.main()
