"""Actual tactical occupation, immediate allegiance and native village services."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake import battle_grid, battle_services, battle_allegiance, officer_relations
from remake.campaign import Campaign, digest
from remake.errors import GameError
from remake.officers import recruitment_loyalty, year_state, YearState
from remake.tactical_ai import choose_action
from remake.campaign_expansion import TACTICS
from campaign_fixtures import controlled_catalog, arrange_contact
from test_remake_tactical_ai import battle, actors, successful_rng


def command(game,kind,**values):
    return game.command(kind,values,game.revision)


def place(game,unit,point):
    """Explicit legal fixture placement; subsequent behavior uses real commands."""
    b=game.state.battle;positions=b['extended']['tactical']['positions']
    used={(row['x'],row['y']) for key,row in positions.items() if key!=str(unit['id'])}
    for key,row in positions.items():
        if key!=str(unit['id']) and (row['x'],row['y'])==point:
            replacement=next((x,y)for y in range(19)for x in range(31)
                if (x,y) not in used and (x,y)!=point)
            row.update(x=replacement[0],y=replacement[1]);used.add(replacement)
    positions[str(unit['id'])]=dict(x=point[0],y=point[1])


class BattleObjectiveTests(unittest.TestCase):
    def test_empty_enemy_castle_ends_battle_without_destroying_defenders(self):
        game=battle(three_enemies=False);b,a,t,_,_=actors(game)
        field=battle_grid._field(b);camp=field['camp']
        place(game,t,(0,18))
        adjacent=next((x,y)for x,y in ((camp[0]-1,camp[1]),(camp[0]+1,camp[1]),(camp[0],camp[1]-1),(camp[0],camp[1]+1))if 0<=x<31 and 0<=y<19)
        place(game,a,adjacent);before=deepcopy(game.state)
        command(game,'battle_move',battle_id=b['id'],actor=a['id'],x=camp[0],y=camp[1])
        result=game.state.battle
        self.assertEqual((game.state.phase,result['outcome']),('result','victory'))
        self.assertEqual(result['defenders'],before.battle['defenders'])
        self.assertEqual(game.state.rng,before.rng)
        self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
        restored=Campaign(game.catalog);restored.load_save(game.export_save(),0)
        self.assertEqual(restored.export_save(),game.export_save())

        command(game,'settle',battle_id=b['id'])
        self.assertEqual(game.state.cities[b['target']].owner,b['attacker'])
        game.validate(game.state)

    def test_ruler_and_full_friendly_cities_cannot_be_converted(self):
        game=battle(spell=8);b,a,t,own,foe=actors(game)
        from remake.tactical_ai import tactic_reason
        arrange_contact(game,actor=a,target=t)
        reason=tactic_reason(game.state,b,a,t,own,foe,'plain',TACTICS[8])
        self.assertIn('君主',reason)
        before=game.export_save()
        with self.assertRaises(GameError):command(game,'tactic',battle_id=b['id'],actor=a['id'],target=t['id'],tactic=8)
        self.assertEqual(game.export_save(),before)
        # Full-roster detection is read-only and rejects before payment or RNG.
        t=next(u for u in b[foe]if u['id'] not in game.state.extension['leaders'].values())
        from unittest.mock import patch
        with patch('remake.battle_allegiance.home',return_value=None):
            self.assertIn('滿員',battle_allegiance.reason(game.state,b,t,own))
        self.assertEqual(game.export_save(),before)

    def test_occupied_enemy_castle_and_spoofed_occupation_are_atomic(self):
        game=battle(three_enemies=False);b,a,t,_,_=actors(game)
        camp=battle_grid._field(b)['camp'];place(game,t,camp)
        before=game.export_save()
        with self.assertRaises(GameError):command(game,'battle_move',battle_id=b['id'],actor=a['id'],x=camp[0],y=camp[1])
        self.assertEqual(game.export_save(),before)
        invalid=deepcopy(before);body=invalid['state']['battle'];body['outcome']='victory';invalid['state']['phase']='result'
        body['extended']['occupation']=dict(actor=a['id'],side='attackers',x=camp[0],y=camp[1])
        invalid['checksum']=digest({k:v for k,v in invalid.items()if k!='checksum'})
        with self.assertRaises(GameError):game.load_save(invalid,game.revision)
        self.assertEqual(game.export_save(),before)

    def test_surrender_changes_side_immediately_preserving_soldiers_and_cell(self):
        game=battle(spell=8);b,a,_,own,foe=actors(game)
        t=next(u for u in b[foe]if u['id'] not in game.state.extension['leaders'].values())
        arrange_contact(game,actor=a,target=t);game.state.officers[t['id']].loyalty=30
        successful_rng(game.state);before=deepcopy(game.state)
        point=deepcopy(b['extended']['tactical']['positions'][str(t['id'])])
        leader=before.extension['leaders'][b['attacker']]
        expected=recruitment_loyalty(before.officers[leader].profile.virtue,30)
        relation=officer_relations.relation(before.officers[leader].person_id,
            before.officers[t['id']].person_id,before.year)
        if relation and not relation['blocked']:
            expected=max(expected,relation['floor'])
        command(game,'tactic',battle_id=b['id'],actor=a['id'],target=t['id'],tactic=8)
        state=game.state;b=state.battle
        converted=next(unit for unit in b[own]if unit['id']==t['id'])
        self.assertEqual(converted,t)
        self.assertNotIn(t['id'],[u['id']for u in b[foe]])
        self.assertEqual(state.officers[t['id']].faction_id,b['attacker'])
        self.assertEqual(state.officers[t['id']].loyalty,expected)
        self.assertEqual(b['extended']['tactical']['positions'][str(t['id'])],point)
        self.assertTrue(game.view()['catalog']['battle_tactical']['actors'][str(t['id'])]['can_act'])
        self.assertEqual(sum(u['troops']for side in battle_grid.SIDES for u in b[side]),
                         sum(u['troops']for side in battle_grid.SIDES for u in before.battle[side]))
        self.assertEqual(state.rng.draws,before.rng.draws+1)
        restored=Campaign(game.catalog);restored.load_save(game.export_save(),0)
        self.assertEqual(restored.export_save(),game.export_save())

        saved=game.export_save()
        for patch in (dict(side='defenders'),dict(home='nanyang'),dict(original_side='bogus'),dict(home=[])):
            bad=deepcopy(saved)
            bad['state']['battle']['extended']['defections'][str(t['id'])].update(patch)
            bad['checksum']=digest({key:value for key,value in bad.items()if key!='checksum'})
            with self.assertRaises(GameError):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),saved)

    def test_defection_can_join_ten_deployed_units_and_victory_preserves_ownership(self):
        catalog=controlled_catalog();existing={r['person_id']for r in catalog.data['initial_officers']}
        extra=[p for p in catalog.definitions.values()if p.person_id not in existing
            and year_state(p,217)in {YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW}
            and not catalog.profiles[catalog.ids[p.person_id]].missing][:10]
        for index,p in enumerate(extra):
            city='xiangyang'if index<9 else 'nanyang'
            catalog.data['initial_officers'].append(dict(person_id=p.person_id,city=city,troops=100,ruler=False))
            catalog.data['appearance_locations'][p.person_id]=city
        game=Campaign(catalog);game.state=game._new('shu',2026)
        state=game.state;actor=catalog.ids['san14-candidate-0440']
        state.officers[actor].experience=10000;state.officers[actor].tier=6
        selected=[actor]+[catalog.ids[p.person_id]for p in extra[:9]]
        game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],selected)
        b=state.battle;a=b['attackers'][0];t=next(u for u in b['defenders']if u['id']==catalog.ids[extra[-1].person_id])
        arrange_contact(game,actor=a,target=t);state.officers[t['id']].loyalty=20;successful_rng(state)
        command(game,'tactic',battle_id=b['id'],actor=a['id'],target=t['id'],tactic=8)
        self.assertEqual(len(game.state.battle['attackers']),11)
        self.assertEqual(len({u['id']for side in battle_grid.SIDES for u in game.state.battle[side]}),12)
        game.validate(game.state)
        restored=Campaign(catalog);restored.load_save(game.export_save(),0)
        self.assertEqual(restored.export_save(),game.export_save())
        b=game.state.battle;camp=battle_grid._field(b)['camp']
        place(game,b['defenders'][0],(0,18));place(game,b['attackers'][0],(camp[0]-1,camp[1]))
        command(game,'battle_move',battle_id=b['id'],actor=a['id'],x=camp[0],y=camp[1])
        command(game,'settle',battle_id=b['id'])
        self.assertEqual(len(game.state.cities['nanyang'].roster.officer_ids),11)
        self.assertEqual(game.state.officers[t['id']].faction_id,'shu')
        self.assertNotIn(t['id'],game.state.cities['xiangyang'].roster.officer_ids)
        game.validate(game.state)

    def test_one_thousand_troops_allocate_march_save_and_cap_are_valid(self):
        game=Campaign(controlled_catalog());command(game,'new',faction='shu',seed=2026)
        before=deepcopy(game.state)
        command(game,'allocate',city='xiangyang',officer=146,troops=1000,flow=None)
        self.assertEqual(game.state.officers[146].troops,1000)
        self.assertEqual(game.state.cities['xiangyang'].reserves,before.cities['xiangyang'].reserves-(1000-before.officers[146].troops))
        flow=game.state.extension['command_books']['factions']['shu']['allocation']['active']['id']
        command(game,'allocation_close',city='xiangyang',flow=flow)
        saved=game.export_save()
        with self.assertRaises((GameError,ValueError)):command(game,'allocate',city='xiangyang',officer=146,troops=1001)
        self.assertEqual(game.export_save(),saved)
        command(game,'depart',source='xiangyang',target='nanyang',officers=[146])
        game.validate(game.state)
        restored=Campaign(game.catalog);restored.load_save(game.export_save(),0)
        self.assertEqual(restored.export_save(),game.export_save())
        self.assertEqual(battle_grid.point_cap(20000),60)


class BattleServiceTests(unittest.TestCase):
    def ready(self,kind,*,side='attackers'):
        game=battle(three_enemies=False);b,a,t,_,_=actors(game)
        actor=a if side=='attackers'else t
        site=next(row for row in battle_grid._field(b)['services']if row['kind']==kind)
        place(game,actor,(site['x'],site['y']))
        if side=='defenders':
            b['extended']['tactical']['side']=side;b['extended']['tactical']['passed']['attackers']=True
        game.validate(game.state)
        return game,b,actor

    def test_all_native_service_coordinates_are_exposed_without_draws(self):
        for map_id,row in battle_grid._library()[0].items():
            for site in row['services']:
                self.assertIn(site['kind'],{'hospital','market','armory'})
                self.assertTrue(0<=site['x']<31 and 0<=site['y']<19)
        game,b,a=self.ready('hospital');before=game.export_save()
        offered=game.view()['catalog']['battle_tactical']
        self.assertEqual(offered['actors'][str(a['id'])]['facility']['kind'],'hospital')
        self.assertEqual(len(offered['facilities']),3)
        self.assertEqual(game.export_save(),before)

    def test_hospital_real_healing_and_one_draw_without_orders_or_ap(self):
        game,b,a=self.ready('hospital');b['extended']['support'][str(a['id'])]['health']=10
        before=deepcopy(game.state);payer=b['source']
        command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='treat')
        state=game.state
        self.assertEqual(state.cities[payer].gold,before.cities[payer].gold-50)
        self.assertGreater(state.battle['extended']['support'][str(a['id'])]['health'],10)
        self.assertEqual(state.rng.draws,before.rng.draws+1)
        self.assertEqual(state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(state.battle['extended']['tactical']['points'],before.battle['extended']['tactical']['points'])
        game.validate(state)

    def test_market_and_armory_charge_and_persist_actual_resources_and_equipment(self):
        game,b,a=self.ready('market');before=deepcopy(game.state);offer=battle_services.quote(game,before,b,a,'attackers')
        command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='buy_grain',batches=2)
        self.assertEqual(game.state.cities[b['source']].grain,before.cities[b['source']].grain+200)
        self.assertEqual(game.state.cities[b['source']].gold,before.cities[b['source']].gold-2*offer['trade']['rate'])
        self.assertEqual(game.state.rng,before.rng)
        game,b,a=self.ready('armory');offer=battle_services.quote(game,game.state,b,a,'attackers')
        item=next(row for row in offer['stock']['weapon']if row['eligible'])
        gold=game.state.cities[b['source']].gold;rng=deepcopy(game.state.rng)
        command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='buy_equipment',slot='weapon',item=item['id'])
        self.assertEqual(game.state.officers[a['id']].weapon_id,item['id'])
        self.assertEqual(game.state.cities[b['source']].gold,gold-item['price'])
        self.assertEqual(game.state.rng,rng)
        restored=Campaign(game.catalog);restored.load_save(game.export_save(),0)
        self.assertEqual(restored.export_save(),game.export_save())

    def test_wrong_village_insufficient_funds_and_bad_quantity_are_atomic(self):
        game,b,a=self.ready('market')
        for payload in [dict(action='treat'),dict(action='buy_grain',batches=0),dict(action='buy_grain',batches=True),dict(action='buy_grain',batches=100000000)]:
            before=game.export_save()
            with self.assertRaises(GameError):command(game,'battle_facility',battle_id=b['id'],actor=a['id'],**payload)
            self.assertEqual(game.export_save(),before)
        game,b,a=self.ready('hospital');game.state.cities[b['source']].gold=0;b['extended']['support'][str(a['id'])]['health']=10
        before=game.export_save()
        with self.assertRaises(GameError):command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='treat')
        self.assertEqual(game.export_save(),before)
        game,b,a=self.ready('armory')
        for slot,item in [([],1),('weapon',True),('bad',1),('weapon',999999)]:
            before=game.export_save()
            with self.assertRaises(GameError):command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='buy_equipment',slot=slot,item=item)
            self.assertEqual(game.export_save(),before)
        for actor in (True,[],None,'001'):
            before=game.export_save()
            with self.assertRaises(GameError):command(game,'battle_facility',battle_id=b['id'],actor=actor,action='buy_equipment',slot='weapon',item=1)
            self.assertEqual(game.export_save(),before)

    def test_ai_uses_same_hospital_quote_payment_and_healing_service(self):
        game,b,a=self.ready('hospital',side='defenders')
        b['extended']['support'][str(a['id'])]['health']=5;state=game.state
        choice=choose_action(state,b,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['action']),('facility','treat'))
        before=deepcopy(state)
        game._perform_battle_action(state,choice,'defenders','attackers')
        self.assertEqual(state.cities[b['target']].gold,before.cities[b['target']].gold-50)
        self.assertEqual(state.rng.draws,before.rng.draws+1)
        self.assertGreater(state.battle['extended']['support'][str(a['id'])]['health'],5)
        game.validate(state)

    def test_ai_actively_seeks_an_affordable_hospital_and_then_treats(self):
        game=battle(three_enemies=False);b,a,t,_,_=actors(game)
        site=next(row for row in battle_grid._field(b)['services']if row['kind']=='hospital')
        place(game,t,battle_grid._field(b)['camp'])
        place(game,a,(site['x']-1,site['y']))
        b['extended']['support'][str(a['id'])]['health']=5
        before=game.export_save()
        choice=choose_action(game.state,b,'attackers','defenders','plain',TACTICS,game=game)
        self.assertEqual(choice['kind'],'move')
        self.assertEqual(choice['service_goal']['kind'],'hospital')
        self.assertEqual(game.export_save(),before,'The service route preview cannot change state or RNG')
        command(game,'battle_move',battle_id=b['id'],actor=a['id'],x=choice['x'],y=choice['y'])
        current=game.state.battle
        choice=choose_action(game.state,current,'attackers','defenders','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['action']),('facility','treat'))
        gold=game.state.cities[b['source']].gold
        command(game,'battle_facility',battle_id=b['id'],actor=a['id'],action='treat')
        self.assertEqual(game.state.cities[b['source']].gold,gold-50)
        game.validate(game.state)

    def test_ai_takes_reachable_empty_enemy_castle_before_ordinary_combat(self):
        game=battle(three_enemies=False);b,a,t,_,_=actors(game)
        camp=battle_grid._field(b)['camp']
        place(game,t,(0,18));place(game,a,(camp[0]-1,camp[1]))
        before=game.export_save()
        choice=choose_action(game.state,b,'attackers','defenders','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice.get('capture')),('move',True))
        self.assertEqual((choice['x'],choice['y']),camp)
        self.assertEqual(game.export_save(),before)
        game._perform_battle_action(game.state,choice,'attackers','defenders')
        self.assertEqual((game.state.phase,b['outcome']),('result','victory'))
        game.validate(game.state)


if __name__=='__main__':unittest.main()
