"""Modern Qimen scores delayed enemy losses, never the legacy self shield."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid as grid,battle_services,tactical_ai as ai,tactic_effects
from remake.campaign import Campaign,Catalog,SeedRng
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from remake.officers import experience_tier
from campaign_fixtures import controlled_catalog
from test_remake_battle_grid import fixture,plain,position
from test_remake_chain_ai import defending_chain_battle
from test_remake_fire_supply_ai import command
from test_remake_tactical_ai import actors,kernel_battle


def qimen_fixture(attackers=1,defenders=1,*,source=1):
    game,state,battle=fixture(attackers,defenders)
    for ident,officer in state.officers.items():
        officer.person_id='san14-candidate-0440'if ident==source else'controlled-qimen-opponent-'+str(ident)
    return game,state,battle


def defending_qimen_battle():
    """Disclosed test assignment/tier/cells/10 remainingAP, actual shared commands.

    Real historical profiles, warehouses, the city field and production battle
    services stay intact. The current-catalog fixture explicitly assigns Zhuge
    Liang to the defending side, grants his valid learned tier6, and supplies
    the attacking ruler's1000 troops through public allocation. This is not a
    claim about historical Wei membership or natural opening deployment.
    """
    data=deepcopy(controlled_catalog().data)
    for row in data['initial_officers']:
        if row['person_id']=='san14-candidate-0440':row['city']='nanyang'
    data['appearance_locations']['san14-candidate-0440']='nanyang'
    with tempfile.TemporaryDirectory()as directory:
        path=Path(directory)/'controlled-qimen-ai.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        game=Campaign(Catalog(path))
    command(game,'new',faction='shu',seed=2026)
    command(game,'allocate',city='xiangyang',officer=951,troops=1000)
    state=game.state
    state.officers[439].experience=10000;state.officers[439].tier=6
    game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],
                               list(state.cities['xiangyang'].roster.officer_ids))
    battle=state.battle;row=battle['extended']['tactical']
    for ident,point in((439,(5,5)),(123,(20,0)),(951,(9,5)),(146,(9,6)),(999,(10,6))):
        position(battle,ident,*point)
    self_field=grid._field(battle)
    assert self_field['classes'][5][9]not in(3,5)
    row['side']='defenders';row['passed']['attackers']=True
    row['points']['defenders']=10
    game.validate(state)
    return game,next(unit for unit in battle['defenders']if unit['id']==439)


def prepare_actual_roll(state,chance,*,success):
    seed=next(seed for seed in range(1,10000)if(SeedRng(seed).next()%100<chance)==success)
    state.rng=SeedRng(seed)
    return deepcopy(state.rng)


class QimenAITests(unittest.TestCase):
    def test_modern_guard_uses_actual_general_gate_but_legacy_remains_certain(self):
        _,state,battle=qimen_fixture();actor,target=battle['attackers'][0],battle['defenders'][0]
        state.officers[actor['id']].profile.intellect=95
        state.officers[target['id']].profile.intellect=75
        self.assertEqual(ai._chance(state,actor,target,'guard',battle),.7)
        self.assertEqual(ai._chance(state,actor,target,'guard'),1)
        old=deepcopy(battle);old['extended'].pop('tactical')
        self.assertEqual(ai._chance(state,actor,target,'guard',old),1)
        self.assertEqual(ai._chance(state,actor,target,'ambush',battle),1)

    def test_each_duration_is_saturated_before_mean_and_never_uses_self_guard(self):
        _,state,battle=qimen_fixture();field=plain()
        actor,target=battle['attackers'][0],battle['defenders'][0]
        position(battle,1,5,5);position(battle,101,6,5)
        target['troops']=target['start']=800
        with patch.object(grid,'_field',return_value=field):
            value=ai._qimen_value(state,battle,target,'attackers','defenders')
            expected=sum(ai._loss_value(target,min(800,115*conditions.qimen_duration('attackers',roll)))for roll in range(4))/4
            self.assertEqual(value,expected)
            self.assertLess(value,ai._loss_value(target,800),
                            'Clamping after mean duration falsely assumes every outcome routes800')
            # Retained old flags are neither Qimen prerequisites nor armor
            # against its direct periodic troop loss.
            battle['extended']['support']['1']['guard']=2
            battle['extended']['support']['101']['guard']=2
            self.assertEqual(ai._qimen_value(state,battle,target,'attackers','defenders'),value)
            chance=ai._chance(state,actor,target,'guard',battle)
            score=ai._tactic_value(state,battle,actor,target,'attackers','defenders','plain',TACTICS[15],
                                   lambda a,t:ai.expected_attack(battle,a,t))
            self.assertEqual(score,value*chance-10*1.8)

    def test_defending_duration_keeps_same_day_damage_but_not_same_day_movement_turn(self):
        _,state,battle=qimen_fixture(source=101);field=plain()
        target=battle['attackers'][0]
        target['troops']=target['start']=1000
        position(battle,101,5,5);position(battle,1,10,5)
        with patch.object(grid,'_field',return_value=field):
            expected=[]
            for roll in range(4):
                count=conditions.qimen_duration('defenders',roll)
                expected.append(ai._loss_value(target,min(1000,115*count))
                                +ai._movement_lock_value(battle,target,'defenders','attackers',count))
            self.assertEqual(ai._qimen_value(state,battle,target,'defenders','attackers'),sum(expected)/4)

    def test_last_day_has_no_post_timeout_damage_and_defender_cannot_invent_a_later_turn(self):
        _,state,battle=qimen_fixture();field=plain()
        position(battle,1,5,5);position(battle,101,10,5)
        target=battle['defenders'][0]
        battle['round']=30
        with patch.object(grid,'_field',return_value=field):
            expected=sum(ai._movement_lock_value(battle,target,'attackers','defenders',
                          conditions.qimen_duration('attackers',roll))for roll in range(4))/4
            self.assertGreater(expected,0)
            self.assertEqual(ai._qimen_value(state,battle,target,'attackers','defenders'),expected)
            self.assertEqual(ai._qimen_value(state,battle,battle['attackers'][0],'defenders','attackers'),0)
            position(battle,101,6,5)
            self.assertEqual(ai._qimen_value(state,battle,target,'attackers','defenders'),0)
            battle['round']=29
            self.assertEqual(ai._qimen_value(state,battle,target,'attackers','defenders'),115)

    def test_source_may_be_in_either_army_and_zero_troops_hp1_do_not_disable_it(self):
        _,state,battle=qimen_fixture(defenders=2,source=102);field=plain()
        position(battle,1,5,5);position(battle,101,10,5);position(battle,102,20,10)
        source=next(unit for unit in battle['defenders']if unit['id']==102)
        source['troops']=0;battle['extended']['support']['102']['health']=1
        with patch.object(grid,'_field',return_value=field):
            self.assertEqual(conditions.qimen_source(state,battle),102)
            self.assertGreater(ai._qimen_value(state,battle,battle['defenders'][0],'attackers','defenders'),0)
            battle['extended']['surrenders']['102']=source['start']
            self.assertIsNone(conditions.qimen_source(state,battle))
            self.assertEqual(ai._qimen_value(state,battle,battle['defenders'][0],'attackers','defenders'),0)
            battle['extended']['surrenders'].clear();battle['defenders'].remove(source)
            self.assertIsNone(conditions.qimen_source(state,battle))
            self.assertEqual(ai._qimen_value(state,battle,battle['defenders'][0],'attackers','defenders'),0)

    def test_existing_qimen_is_not_recast_but_low_locks_still_have_damage_value(self):
        _,state,battle=qimen_fixture();field=plain()
        position(battle,1,5,5);position(battle,101,10,5)
        actor,target=battle['attackers'][0],battle['defenders'][0]
        with patch.object(grid,'_field',return_value=field):
            for kind in('phantom','chain'):
                if kind=='phantom':conditions.apply(battle,101,'attackers')
                else:conditions.apply_chain(battle,101,'attackers',1)
                self.assertGreater(ai._qimen_value(state,battle,target,'attackers','defenders'),0)
                self.assertTrue(any(row['kind']=='tactic'and row['tactic']==15
                                    for row in ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)))
            conditions.apply_qimen(battle,101,'attackers',3)
            before=deepcopy((battle,vars(state.rng)))
            self.assertIn(15,ai.legal_tactics(state,battle,actor,target,'attackers','defenders','plain',TACTICS))
            self.assertEqual(ai._qimen_value(state,battle,target,'attackers','defenders'),0)
            self.assertFalse(any(row['kind']=='tactic'and row['tactic']==15
                                 for row in ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)))
            self.assertEqual((battle,vars(state.rng)),before)

    def test_qimen_locked_actor_keeps_attack_tactics_and_retaliation_without_movement(self):
        _,state,battle=qimen_fixture();field=plain()
        position(battle,1,5,5);position(battle,101,6,5)
        actor,target=battle['attackers'][0],battle['defenders'][0]
        exchange=ai.expected_contact_exchange(battle,actor,target)
        conditions.apply_qimen(battle,1,'defenders',0)
        self.assertEqual(ai.expected_contact_exchange(battle,actor,target),exchange)
        self.assertTrue(grid.move_reason(battle,actor,'attackers'))
        self.assertEqual(grid.attack_reason(battle,actor,target,'attackers'),'')
        with patch.object(grid,'_field',return_value=field):
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
            self.assertTrue(any(row['kind']=='attack'for row in rows))
            self.assertTrue(any(row['kind']=='tactic'and row['tactic']==15 for row in rows))
            self.assertFalse(any(row['kind']=='move'for row in rows))

    def test_planning_twenty_units_is_read_only_without_per_target_paths_or_rng(self):
        _,state,battle=qimen_fixture(10,10);field=plain()
        for side,x in(('attackers',2),('defenders',7)):
            for index,unit in enumerate(battle[side]):position(battle,unit['id'],x+index//5,index%5)
        before=deepcopy((battle,vars(state.rng)))
        with patch.object(grid,'_field',return_value=field), \
                patch.object(grid,'_paths',wraps=grid._paths)as paths, \
                patch.object(SeedRng,'next',side_effect=AssertionError('No future Qimen rolls')):
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
        self.assertTrue(any(row['kind']=='tactic'and row['tactic']==15 for row in rows))
        self.assertLessEqual(paths.call_count,10)
        self.assertEqual((battle,vars(state.rng)),before)

    def test_public_wait_ai_cast_and_damage_share_three_actual_draws_and_real_supply_day(self):
        game,caster=defending_qimen_battle();state,battle=game.state,game.state.battle
        choice=ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['tactic'],choice['actor']),('tactic',15,439))
        target=next(unit for unit in battle['attackers']if unit['id']==choice['target'])
        chance=tactic_effects.general_chance(state.officers[439],state.officers[target['id']])
        expected=prepare_actual_roll(state,chance,success=True)
        expected.next();initial_count=conditions.qimen_duration('defenders',expected.next()%4)
        loss=min(target['troops'],80+expected.next()%71)
        before=deepcopy(state)
        row=battle['extended']['tactical'];row['side']='attackers';row['passed']['attackers']=False
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle;actual=next(unit for unit in current['attackers']if unit['id']==target['id'])
        self.assertEqual((game.state.phase,current['round']),('battle',2))
        self.assertEqual(game.state.rng,expected)
        self.assertEqual(actual['troops'],target['troops']-loss)
        self.assertEqual(conditions.kind(current,target['id']),'qimen')
        self.assertEqual(conditions.remaining(current,target['id']),initial_count-1)
        self.assertEqual(current['extended']['support'],before.battle['extended']['support'])
        self.assertEqual(current['extended']['tactical']['positions'],before.battle['extended']['tactical']['positions'])
        gain=(actual['troops']%256)//2
        zhuge=game.state.officers[439]
        self.assertEqual(zhuge.experience,min(49999,before.officers[439].experience+gain))
        self.assertEqual(zhuge.tier,experience_tier(zhuge.experience))
        self.assertEqual(zhuge.profile,before.officers[439].profile)
        self.assertEqual(game.state.officers[target['id']].troops,before.officers[target['id']].troops,
                         'Daily damage is reserved in the battle until actual settlement')
        self.assertEqual(game.state.soldiers,before.soldiers)
        self.assertEqual(game.state.cities,before.cities)
        self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(current['extended']['supply']['days'],1)
        game.validate(game.state)
        saved=game.export_save();loaded=Campaign(game.catalog);loaded.load_save(saved,loaded.revision)
        self.assertEqual(loaded.export_save(),saved)
        self.assertEqual(game.view()['catalog']['battle_tactical']['actors'][str(target['id'])]['reachable'],[])
        revision=game.revision
        with self.assertRaises(GameError):
            command(game,'battle_move',battle_id=current['id'],actor=target['id'],x=0,y=1)
        self.assertEqual((game.export_save(),game.revision),(saved,revision))

    def test_failed_actual_ai_cast_spends_ten_ap_but_no_duration_or_daily_damage_draw(self):
        game,_=defending_qimen_battle();state,battle=game.state,game.state.battle
        choice=ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual(choice['tactic'],15)
        target=next(unit for unit in battle['attackers']if unit['id']==choice['target'])
        expected=prepare_actual_roll(state,tactic_effects.general_chance(state.officers[439],state.officers[target['id']]),success=False)
        expected.next();before=deepcopy(state)
        row=battle['extended']['tactical'];row['side']='attackers';row['passed']['attackers']=False
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['round']),('battle',2))
        self.assertEqual(game.state.rng,expected)
        self.assertEqual(current['attackers'],before.battle['attackers'])
        self.assertEqual(current['extended']['support'],before.battle['extended']['support'])
        self.assertNotIn('conditions',current['extended'])
        self.assertEqual(game.state.officers[439].experience,before.officers[439].experience)
        self.assertEqual(current['extended']['tactical']['points']['defenders'],grid.daily_points(600))

    def test_qimen_locked_ai_can_still_treat_at_its_real_in_place_hospital(self):
        game,caster=defending_chain_battle();state,battle=game.state,game.state.battle
        site=next(site for site in grid._field(battle)['services']if site['kind']=='hospital')
        position(battle,caster['id'],site['x'],site['y'])
        battle['extended']['support'][str(caster['id'])]['health']=20
        conditions.apply_qimen(battle,caster['id'],'attackers',0)
        rows=ai.candidates(state,battle,'defenders','attackers','plain',TACTICS,depth=2,game=game)
        self.assertTrue(any(row['kind']=='facility'and row['actor']==caster['id']and row['action']=='treat'for row in rows))
        self.assertFalse(any(row['kind']=='move'and row['actor']==caster['id']for row in rows))
        state.player='wei'
        self.assertEqual(battle_services.quote(game,state,battle,caster,'defenders')['kind'],'hospital')
        command(game,'battle_facility',battle_id=battle['id'],actor=caster['id'],action='treat')
        self.assertGreater(game.state.battle['extended']['support'][str(caster['id'])]['health'],20)
        self.assertEqual(conditions.remaining(game.state.battle,caster['id']),6)

    def test_legacy_guard_still_grants_two_protections_without_any_draw_or_target_condition(self):
        game=kernel_battle('plain',three_enemies=False,spell=15);state=game.state
        battle,actor,target,own,foe=actors(game)
        before=deepcopy(state.rng)
        self.assertEqual(ai._chance(state,actor,target,'guard',battle),1)
        game._execute_tactic(state,actor,target,own,foe,15,finish=False)
        self.assertEqual(state.rng,before)
        self.assertEqual(battle['extended']['support'][str(actor['id'])]['guard'],2)
        self.assertEqual(battle['extended']['support'][str(target['id'])]['guard'],0)
        self.assertNotIn('conditions',battle['extended'])


if __name__=='__main__':unittest.main()
