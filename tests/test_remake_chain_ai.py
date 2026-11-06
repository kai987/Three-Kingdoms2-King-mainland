"""Modern chain AI values water movement locks without sampling future effects."""
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
from campaign_fixtures import arrange_tactic,controlled_catalog
from test_remake_battle_grid import fixture,plain,position
from test_remake_fire_supply_ai import command
from test_remake_tactical_ai import actors,kernel_battle


def water_group():
    game,state,battle=fixture(1,3);field=plain()
    position(battle,1,4,5)
    for ident,point in((101,(9,5)),(102,(9,6)),(103,(10,6))):
        position(battle,ident,*point);field['classes'][point[1]][point[0]]=3
    return game,state,battle,field


def defending_chain_battle():
    """Disclosed current-catalog test handoff, not historical Wei membership.

    Move the actual learned strategist's fixture opening assignment to Wei;
    retain profiles, source grid, resources and all production commands. His
    valid tier6, native river positions and9 remainingAP isolate one real AI
    chain cast after a public player wait. No effect or RNG is mocked.
    """
    data=deepcopy(controlled_catalog().data)
    for row in data['initial_officers']:
        if row['person_id']=='san14-candidate-0440':row['city']='nanyang'
    data['appearance_locations']['san14-candidate-0440']='nanyang'
    with tempfile.TemporaryDirectory()as directory:
        path=Path(directory)/'controlled-chain-ai.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        game=Campaign(Catalog(path))
    command(game,'new',faction='shu',seed=2026)
    state=game.state
    state.officers[439].experience=10000;state.officers[439].tier=6
    game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],
                               list(state.cities['xiangyang'].roster.officer_ids))
    battle=state.battle
    caster=next(unit for unit in battle['defenders']if unit['id']==439)
    arrange_tactic(game,10,caster,battle['attackers'][0])
    # Native original13: the water column11 has its plain bank at13,1.
    # Keep every affected enemy beyond contact so movement denial, rather
    # than an invented canceled retaliation, can justify this cast.
    position(battle,439,13,1)
    assert grid.tile_class(battle,caster)==2
    row=battle['extended']['tactical'];row['points']['defenders']=9
    row['passed']['attackers']=True
    game.validate(state)
    return game,caster


def actual_success_seed(chance,draws):
    for seed in range(1,10000):
        rng=SeedRng(seed)
        if rng.next()%100>=chance:continue
        rolls=[rng.next()%2 for _ in range(draws)]
        if len(set(rolls))>1:return seed
    raise AssertionError('No success seed with distinct independent duration rolls')


class ChainAITests(unittest.TestCase):
    def test_directional_duration_means_and_day_horizon_are_movement_estimates(self):
        _,_,battle,field=water_group();target=battle['defenders'][0]
        with patch.object(grid,'_field',return_value=field):
            value=ai._chain_mobility_value(battle,[target],'attackers','defenders')
            expected=ai._loss_value(target,target['troops'])*4.5/4
            self.assertEqual(value,min(expected,ai._loss_value(target,target['troops'])))
            position(battle,101,10,5)
            value=ai._chain_mobility_value(battle,[target],'attackers','defenders')
            self.assertEqual(value,ai._loss_value(target,target['troops'])*4.5/5)
            # Both hypothetical defending duration outcomes lose their first
            # scan before the affected attacker reaches its next turn.
            actor=battle['attackers'][0]
            defense=ai._chain_mobility_value(battle,[actor],'defenders','attackers')
            distance=min(abs(4-p['x'])+abs(5-p['y'])for key,p in
                         battle['extended']['tactical']['positions'].items()if key!='1')
            self.assertEqual(defense,ai._loss_value(actor,actor['troops'])*min(1,2.5/(distance-1)))
            battle['round']=30
            self.assertEqual(ai._chain_mobility_value(battle,[actor],'defenders','attackers'),0)
            self.assertGreater(ai._chain_mobility_value(battle,[target],'attackers','defenders'),0)

    def test_connected_water_scoring_is_order_independent_and_excludes_nonwater_bridges(self):
        _,state,battle,field=water_group()
        # The non-water middle recipient still conducts the area search.
        field['classes'][6][9]=2
        with patch.object(grid,'_field',return_value=field):
            victims=grid.affected_units(battle,battle['defenders'][0],10,'defenders')
            self.assertEqual([u['id']for u in victims],[101,103])
            first=ai._chain_mobility_value(battle,victims,'attackers','defenders')
            self.assertEqual(first,ai._chain_mobility_value(battle,list(reversed(victims)),'attackers','defenders'))
            self.assertEqual(first,sum(ai._chain_mobility_value(battle,[unit],'attackers','defenders')for unit in victims))
            before=deepcopy((battle,vars(state.rng)))
            with patch.object(SeedRng,'next',side_effect=AssertionError('No preview draw')):
                self.assertEqual(ai._chain_mobility_value(battle,victims,'attackers','defenders'),first)
            self.assertEqual((battle,vars(state.rng)),before)

    def test_mixed_existing_locks_have_zero_value_but_unlocked_area_member_still_counts(self):
        _,state,battle,field=water_group()
        targets=battle['defenders']
        conditions.apply(battle,101,'attackers')
        conditions.apply_chain(battle,102,'attackers',1)
        with patch.object(grid,'_field',return_value=field):
            expected=ai._chain_mobility_value(battle,[targets[2]],'attackers','defenders')
            self.assertGreater(expected,0)
            self.assertEqual(ai._chain_mobility_value(battle,targets,'attackers','defenders'),expected)
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
            # A locked primary target is still a useful route to other water
            # recipients. Do not apply phantom's single-target filter here.
            selected=next(row for row in rows if row['kind']=='tactic'and row['tactic']==10 and row['target']==101)
            chance=ai._chance(state,battle['attackers'][0],targets[0],'chain')
            self.assertAlmostEqual(selected['score'],expected*chance-9*1.8)

    def test_all_locked_has_no_ai_chain_candidate_but_player_repeat_stays_legal(self):
        _,state,battle,field=water_group()
        conditions.apply(battle,101,'attackers')
        conditions.apply_chain(battle,102,'attackers',0)
        conditions.apply_chain(battle,103,'attackers',1)
        actor=battle['attackers'][0];before=deepcopy((battle,vars(state.rng)))
        with patch.object(grid,'_field',return_value=field):
            self.assertIn(10,ai.legal_tactics(state,battle,actor,battle['defenders'][0],
                                            'attackers','defenders','plain',TACTICS))
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
            self.assertFalse(any(row['kind']=='tactic'and row['tactic']==10 for row in rows))
        self.assertEqual((battle,vars(state.rng)),before)

    def test_adjacent_chain_has_no_fictitious_canceled_attack_or_counter_bonus(self):
        _,state,battle=fixture(1,1);field=plain()
        position(battle,1,5,5);position(battle,101,6,5);field['classes'][5][6]=3
        actor,target=battle['attackers'][0],battle['defenders'][0]
        exchange=ai.expected_contact_exchange(battle,actor,target)
        conditions.apply_chain(battle,101,'attackers',1)
        conditions.apply_chain(battle,1,'defenders',0)
        self.assertEqual(ai.expected_contact_exchange(battle,actor,target),exchange)
        self.assertEqual(grid.attack_reason(battle,actor,target,'attackers'),'')
        self.assertTrue(grid.move_reason(battle,actor,'attackers'))
        with patch.object(grid,'_field',return_value=field):
            self.assertEqual(ai._chain_mobility_value(battle,[target],'attackers','defenders'),0)
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
            self.assertTrue(any(row['kind']=='attack'for row in rows))
            self.assertTrue(any(row['kind']=='tactic'and row['tactic']==4 for row in rows))
            self.assertFalse(any(row['kind']=='move'for row in rows))

    def test_unlocked_adjacent_enemy_also_has_zero_denied_movement_value(self):
        _,_,battle=fixture(1,1);field=plain()
        position(battle,1,5,5);position(battle,101,6,5)
        with patch.object(grid,'_field',return_value=field):
            self.assertEqual(ai._chain_mobility_value(battle,battle['defenders'],'attackers','defenders'),0)

    def test_full_rosters_keep_rng_and_at_most_one_existing_path_search_per_actor(self):
        _,state,battle=fixture(10,10);field=plain()
        for side,x in(('attackers',2),('defenders',6)):
            for index,unit in enumerate(battle[side]):
                point=(x+index//5,index%5)
                position(battle,unit['id'],*point)
                if side=='defenders':field['classes'][point[1]][point[0]]=3
        before=deepcopy((battle,vars(state.rng)))
        with patch.object(grid,'_field',return_value=field), \
                patch.object(grid,'_paths',wraps=grid._paths)as paths, \
                patch.object(SeedRng,'next',side_effect=AssertionError('No chain lookahead draw')):
            rows=ai.candidates(state,battle,'attackers','defenders','plain',TACTICS,depth=2)
        self.assertTrue(any(row['kind']=='tactic'and row['tactic']==10 for row in rows))
        self.assertLessEqual(paths.call_count,10)
        self.assertEqual((battle,vars(state.rng)),before)

    def test_public_wait_ai_casts_chain_with_one_success_and_each_water_duration_draw(self):
        game,caster=defending_chain_battle();state,battle=game.state,game.state.battle
        row=battle['extended']['tactical']
        choice=ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game)
        self.assertEqual((choice['kind'],choice['tactic'],choice['actor']),('tactic',10,439))
        target=next(unit for unit in battle['attackers']if unit['id']==choice['target'])
        victims=grid.affected_units(battle,target,10,'attackers')
        self.assertEqual(len(victims),3)
        chance=tactic_effects.general_chance(state.officers[439],state.officers[target['id']])
        state.rng=SeedRng(actual_success_seed(chance,len(victims)))
        expected=deepcopy(state.rng);expected.next()
        counts=[dict(id=str(unit['id']),remaining=conditions.chain_duration('defenders',expected.next()%2))for unit in victims]
        before=deepcopy(state)
        # Restore the actual player phase. Its public wait is what activates
        # the real enemy9AP loop and the subsequent full-day condition scan.
        row['side']='attackers';row['passed']['attackers']=False
        game.validate(state)
        with patch.object(SeedRng,'next',side_effect=AssertionError('AI planning must be pure')):
            row['side']='defenders';row['passed']['attackers']=True
            self.assertEqual(ai.choose_action(state,battle,'defenders','attackers','plain',TACTICS,game=game),choice)
            row['side']='attackers';row['passed']['attackers']=False
        command(game,'battle_wait',battle_id=battle['id'])
        current=game.state.battle
        self.assertEqual((game.state.phase,current['round']),('battle',2))
        self.assertEqual(game.state.rng,expected)
        self.assertEqual(current['attackers'],before.battle['attackers'])
        self.assertEqual(current['defenders'],before.battle['defenders'])
        self.assertEqual(current['extended']['support'],before.battle['extended']['support'])
        self.assertEqual(current['extended']['tactical']['positions'],before.battle['extended']['tactical']['positions'])
        for item in counts:
            self.assertEqual(conditions.kind(current,item['id']),'chain')
            self.assertEqual(conditions.remaining(current,item['id']),item['remaining']-1)
        self.assertEqual(game.state.extension['events']['items'][-1]['details'],
                         dict(tactic=10,success=True,condition='chain',condition_counts=counts))
        self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(game.state.cities,before.cities)
        game.validate(game.state)
        # The now-player army receives the same authoritative movement lock.
        affected=victims[0]['id'];board=game.view()['catalog']['battle_tactical']['actors'][str(affected)]
        self.assertEqual(board['reachable'],[])
        original=game.export_save();revision=game.revision
        with self.assertRaises(GameError):
            command(game,'battle_move',battle_id=current['id'],actor=affected,x=0,y=1)
        self.assertEqual((game.export_save(),game.revision),(original,revision))

    def test_chain_locked_ai_keeps_real_in_place_hospital_action(self):
        game,caster=defending_chain_battle();state,battle=game.state,game.state.battle
        site=next(site for site in grid._field(battle)['services']if site['kind']=='hospital')
        position(battle,caster['id'],site['x'],site['y'])
        battle['extended']['support'][str(caster['id'])]['health']=20
        conditions.apply_chain(battle,caster['id'],'attackers',1)
        rows=ai.candidates(state,battle,'defenders','attackers','plain',TACTICS,depth=2,game=game)
        self.assertTrue(any(row['kind']=='facility'and row['actor']==caster['id']and row['action']=='treat'for row in rows))
        self.assertFalse(any(row['kind']=='move'and row['actor']==caster['id']for row in rows))
        state.player='wei'
        offer=battle_services.quote(game,state,battle,caster,'defenders')
        self.assertEqual(offer['kind'],'hospital')
        command(game,'battle_facility',battle_id=battle['id'],actor=caster['id'],action='treat')
        self.assertGreater(game.state.battle['extended']['support'][str(caster['id'])]['health'],20)
        self.assertEqual(conditions.remaining(game.state.battle,caster['id']),5)

    def test_legacy_chain_keeps_one_gate_draw_and_old_stunned_behavior(self):
        game=kernel_battle('water',spell=10);state=game.state
        battle,actor,target,own,foe=actors(game)
        selected=next(row for row in ai.candidates(state,battle,own,foe,'water',TACTICS,depth=2)
                      if row['kind']=='tactic'and row['tactic']==10)
        self.assertGreater(selected['score'],0)
        chance=tactic_effects.general_chance(state.officers[actor['id']],state.officers[target['id']])
        state.rng=SeedRng(next(seed for seed in range(1,1000)if SeedRng(seed).next()%100<chance))
        expected=deepcopy(state.rng);expected.next()
        game._execute_tactic(state,actor,target,own,foe,10,finish=False)
        self.assertEqual(state.rng,expected)
        self.assertNotIn('conditions',battle['extended'])
        self.assertTrue(all(battle['extended']['support'][str(unit['id'])]['stunned']==1 for unit in battle[foe]))
        self.assertEqual(ai.expected_contact_exchange(battle,target,actor),(0,0))


if __name__=='__main__':unittest.main()
